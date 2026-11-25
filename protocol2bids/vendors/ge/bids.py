"""
GE protocol -> BIDS sidecar.

* Scan parameter sheets and LX scripts are mapped through a common set
  of canonical parameters (`CANONICAL`).
* DICOM dumps are mapped tag by tag, like dcm2niix.

See notes/conversion_rules.md for the conventions and their sources.
"""
from __future__ import annotations

import re
from logging import getLogger
from math import ceil
from typing import Any

from ... import values as V
from ...model import Missing, Protocol
from ...utils.nii2axes import nii2axes

LOGGER = getLogger(__name__)

# canonical name -> candidate keys (sheets: several layouts; LX: tcl names)
CANONICAL = {
    'TR': ('TR', 'Repetition Time'),
    'TE': ('TE', 'Echo Time'),
    'TI': ('TI', 'Prep Time', 'Inversion Time'),
    'FlipAngle': ('Flip Angle', 'FLIP Angle', 'FLIPANG'),
    'FOV': ('FOV', 'Field of View'),
    'PhaseFOV': ('Phase FOV', 'PHASEFOV'),
    'SliceThickness': ('Slice Thickness', 'SLTHICK'),
    'SliceSpacing': ('Slice Spacing', 'Spacing', 'SPC'),
    'Freq': ('Freq', 'Frequency', 'MATRIXX'),
    'Phase': ('Phase', 'MATRIXY'),
    'FreqDir': ('Freq DIR', 'Frequency DIR', 'Freq. Dir', 'SWAPPF'),
    'Plane': ('Plane', 'Scan Plane', 'PLANE'),
    'NEX': ('NEX', '# of Excitations', 'NEX'),
    'Bandwidth': ('Bandwidth', 'Receive Bandwidth', 'RBW'),
    'PulseSequence': ('Pulse Sequence', 'Pulse Seq', 'PSEQ'),
    'Options': ('Imaging Options', 'IOPT'),
    'Mode': ('Imaging Mode', 'Mode', 'IMODE'),
    'Shots': ('Number of Shots', 'NUMSHOTS'),
    'Slices': ('# of Slices', 'Slices', 'NOSLC'),
    'LocsPerSlab': ('Locs per Slab',),
    'Asset': ('Acceleration Factor', 'Phase Acceleration', 'PHASEASSET'),
    'SliceOrder': ('Slice Order', 'SLICEORDER'),
    'Echoes': ('Number of Echoes', '# of Echoes', '# of TE(s) per Scan',
               'NECHO'),
    'Coil': ('Coil Configuration', 'Coil', 'COIL'),
}


class Context:
    def __init__(self, prot: Protocol, nii: dict | None):
        self.prot = prot
        self.out: dict[str, Any] = {}
        nii = dict(nii or {})
        if 'file' in nii or ('affine' in nii and 'shape' in nii):
            self.vox2anat, self.anat2vox, self.shape = nii2axes(**nii)
        else:
            self.vox2anat = self.anat2vox = self.shape = None

    def get(self, name: str) -> str:
        for key in CANONICAL.get(name, (name,)):
            value = self.prot.get(key, default=None)
            if value not in (None, ''):
                return value
        raise Missing(name)

    def opt(self, name, default=None):
        try:
            return self.get(name)
        except Missing:
            return default

    def tag(self, tag: str) -> str:
        value = self.prot.header.get('tags', {}).get(tag)
        if value in (None, ''):
            raise Missing(tag)
        return value

    def __getitem__(self, key):
        if key not in self.out:
            raise Missing(key)
        return self.out[key]

    def __contains__(self, key):
        return key in self.out

    def set(self, key, value):
        if value is not None:
            self.out[key] = value


def _ms(value: str) -> float:
    """Times in seconds. GE sheets print ms by default, sometimes with a
    unit ('2 sec', '5.9 ms', '1.8 msecs')."""
    unit = (V.unit(value) or 'ms').lower().rstrip('.')
    scale = {'ms': 1e-3, 'msec': 1e-3, 'msecs': 1e-3, 's': 1.0,
             'sec': 1.0, 'secs': 1.0, 'us': 1e-6}.get(unit, 1e-3)
    return V.number(value) * scale


# ----------------------------------------------------------------------
#   Sheets / LX
# ----------------------------------------------------------------------

SHEET_RULES = []


def sheet_rule(func):
    SHEET_RULES.append(func)
    return func


@sheet_rule
def s_hardware(ctx: Context):
    ctx.set('Manufacturer', 'GE')
    ctx.set('ManufacturersModelName',
            ctx.prot.scanner.get('ManufacturersModelName'))
    ctx.set('MagneticFieldStrength',
            ctx.prot.scanner.get('MagneticFieldStrength'))
    ctx.set('ReceiveCoilName', ctx.opt('Coil'))
    ctx.set('Modality', 'MR')
    ctx.set('ProtocolName', ctx.prot.name or None)
    ctx.set('SeriesDescription', ctx.prot.name or None)


@sheet_rule
def s_timing(ctx: Context):
    ctx.set('RepetitionTime', _ms(ctx.get('TR')))


@sheet_rule
def s_echo(ctx: Context):
    ctx.set('EchoTime', _ms(ctx.get('TE')))


@sheet_rule
def s_inversion(ctx: Context):
    ti = _ms(ctx.get('TI'))
    if ti > 0:
        ctx.set('InversionTime', ti)


@sheet_rule
def s_flip(ctx: Context):
    ctx.set('FlipAngle', V.number(ctx.get('FlipAngle')))


@sheet_rule
def s_acquisition_type(ctx: Context):
    mode = (ctx.opt('Mode') or '').upper()
    if mode in ('2D', '3D'):
        ctx.set('MRAcquisitionType', mode)
    elif ctx.prot.has('Locs per Slab') or ctx.prot.has('# of Slabs'):
        ctx.set('MRAcquisitionType', '3D')


@sheet_rule
def s_sequence(ctx: Context):
    seq = ctx.get('PulseSequence').upper()
    options = [o.strip().upper() for o in
               re.split(r'[,;]', ctx.opt('Options') or '') if o.strip()]
    epi = 'EPI' in options or 'EPI' in seq
    scanning = []
    if epi:
        scanning.append('EP')
    if 'SPIN' in seq or seq in ('SE', 'FSE', 'FRFSE') or 'FSE' in seq:
        scanning.append('SE')
    else:
        scanning.append('GR')
    if 'IR' in seq or 'IRP' in options or 'IR' in options:
        scanning.append('IR')
    ctx.set('ScanningSequence', scanning)
    label = ('Gradient Echo EPI' if epi and 'GR' in scanning else
             'Spin Echo EPI' if epi else
             'Spoiled Gradient Echo' if 'SPGR' in seq else
             'Fast Spin Echo' if 'FSE' in seq else
             ctx.get('PulseSequence'))
    if 'IR' in scanning and 'SPGR' in seq:
        label = 'Inversion Recovery Fast Spoiled Gradient Echo'
    ctx.set('PulseSequenceType', label)
    ctx.set('EchoPlanarPulseSequence', epi)
    if 'ASSET' in options:
        ctx.set('ParallelAcquisitionTechnique', 'ASSET')


@sheet_rule
def s_asset(ctx: Context):
    if ctx.out.get('ParallelAcquisitionTechnique') != 'ASSET':
        return
    r = V.number(ctx.get('Asset'))
    if r < 1:
        r = 1 / r   # stored as 1/R in some places
    ctx.set('ParallelReductionFactorInPlane', round(r, 3))


@sheet_rule
def s_matrix(ctx: Context):
    freq = V.integer(ctx.get('Freq'))
    phase = V.integer(ctx.get('Phase'))
    ctx.set('AcquisitionMatrixFE', freq)
    ctx.set('AcquisitionMatrixPE', phase)
    pfov = ctx.opt('PhaseFOV')
    if pfov:
        ctx.set('PercentPhaseFOV', round(V.number(pfov) * 100, 3))


@sheet_rule
def s_bandwidth(ctx: Context):
    """GE bandwidth is +/- kHz (half of the total receive bandwidth)."""
    bw = V.number(ctx.get('Bandwidth'))
    ctx.set('PixelBandwidth', round(2 * bw * 1000 / ctx['AcquisitionMatrixFE'],
                                    3))


@sheet_rule
def s_averages(ctx: Context):
    nex = V.number(ctx.get('NEX'))
    ctx.set('NumberOfAverages', nex)
    if nex < 1:
        # fractional NEX = partial Fourier
        ctx.set('PartialFourierEnabled', 'YES')


@sheet_rule
def s_geometry(ctx: Context):
    thick = V.number(ctx.get('SliceThickness'))
    ctx.set('SliceThickness', thick)
    if ctx.out.get('MRAcquisitionType') == '3D':
        return
    gap = V.number(ctx.opt('SliceSpacing') or '0')
    ctx.set('SpacingBetweenSlices', round(thick + gap, 6))


@sheet_rule
def s_shots(ctx: Context):
    ctx.set('NumberShots', V.integer(ctx.get('Shots')))


_PLANES = {'AXIAL': 'z', 'SAGITTAL': 'x', 'CORONAL': 'y'}
_FREQ = {'R/L': 'x', 'L/R': 'x', 'A/P': 'y', 'P/A': 'y', 'S/I': 'z',
         'I/S': 'z'}
_INPLANE = {'z': ('x', 'y'), 'y': ('x', 'z'), 'x': ('y', 'z')}


@sheet_rule
def s_phase_axis(ctx: Context):
    """Polarity is not printed on GE sheets: only the axis."""
    plane = _PLANES[ctx.get('Plane').strip().upper()]
    freq = _FREQ[ctx.get('FreqDir').strip().upper().replace(' ', '')]
    inplane = _INPLANE[plane]
    if freq not in inplane:
        return
    pe = inplane[1 - inplane.index(freq)]
    ctx.set('PhaseEncodingAnatomicalAxis', {'x': 'RL', 'y': 'AP',
                                            'z': 'SI'}[pe])
    if ctx.anat2vox is not None:
        code = {'x': 'LR', 'y': 'PA', 'z': 'IS'}[pe]
        ctx.set('PhaseEncodingAxis', ctx.anat2vox[code][0])
    else:
        ctx.set('PhaseEncodingAxis', 'ij'[inplane.index(pe)])


def ge_slice_ranks(n: int, mb: int = 1, interleaved: bool = True,
                   descending: bool = False,
                   r03: bool = True) -> tuple[list[int], int]:
    """
    Acquisition rank of each slice, following dcm2niix `sliceTimeGE`
    (which dcm2niix uses to *compute* GE SliceTiming):

    * nexc = ceil(N / MB) excitations; interleaved = odd slices first;
    * HyperBand with an even nexc: before software 27.0 R03 a dummy
      excitation is added (nexc + 1 slots); from 27.0 R03 on, the last
      and third-to-last slots are swapped;
    * descending = mirror image over all N slices.

    Returns the ranks and the number of time slots.
    """
    nexc = -(-n // mb)
    if mb > 1 and not r03 and nexc % 2 == 0:
        nexc += 1
    if interleaved:
        nodd = (nexc - 1) // 2
        t = [i // 2 if i % 2 == 0 else nodd + (i + 1) // 2
             for i in range(nexc)]
        if mb > 1 and r03 and nexc > 2 and nexc % 2 == 0:
            t[nexc - 1], t[nexc - 3] = t[nexc - 3], t[nexc - 1]
    else:
        t = list(range(nexc))
    ranks = [t[i % nexc] for i in range(n)]
    if descending:
        ranks = ranks[::-1]
    return ranks, nexc


def ge_is_r03(version: str | None) -> bool | None:
    """Is the software at least 27.0 R03? (None if unknown)"""
    m = re.search(r'(\d\d)\.(\d)_?R?(\d\d)', version or '')
    if not m:
        return None
    major, minor, rel = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (major, minor, rel) >= (27, 0, 3)


@sheet_rule
def s_slice_timing(ctx: Context):
    """GE interleaved: odd slices first (1, 3, 5, ..., 2, 4, ...)."""
    if ctx.out.get('MRAcquisitionType') == '3D':
        return
    order = ctx.get('SliceOrder').strip().lower()
    if order != 'interleaved':  # LX SLICEORDER codes are undocumented
        return
    try:
        n = V.integer(ctx.get('Slices'))
    except Missing:
        if ctx.shape is None:
            raise
        n = int(ctx.shape[2])   # 2D acquisitions: slices along k
    tr = ctx['RepetitionTime']
    mb = 1
    for key in ('Slice Acceleration Factor', 'HyperBand Factor',
                'Multiband Factor'):
        value = ctx.prot.get(key, default=None)
        if value:
            mb = int(round(V.number(value)))
            break
    r03 = True
    if mb > 1:
        r03 = ge_is_r03(ctx.prot.scanner.get('SoftwareVersions'))
        if r03 is None:
            return   # HyperBand order depends on the software version
        ctx.set('MultibandAccelerationFactor', mb)
    ranks, nslots = ge_slice_ranks(n, mb, interleaved=True, r03=r03)
    ctx.set('SliceTiming', [round(r * tr / nslots, 6) for r in ranks])


# ----------------------------------------------------------------------
#   DICOM dumps
# ----------------------------------------------------------------------

DICOM_RULES = []


def dicom_rule(func):
    DICOM_RULES.append(func)
    return func


def _split(value: str) -> list[str]:
    return [v for v in value.split('\\') if v != '']


_DIRECT = [
    # (BIDS key, tag, converter)
    ('Manufacturer', '0008,0070', lambda x: 'GE'),
    ('ManufacturersModelName', '0008,1090', str),
    ('SoftwareVersions', '0018,1020', str),
    ('MagneticFieldStrength', '0018,0087', float),
    ('ReceiveCoilName', '0018,1250', str),
    ('ScanningSequence', '0018,0020', _split),
    ('SequenceVariant', '0018,0021', _split),
    ('ScanOptions', '0018,0022', _split),
    ('SequenceName', '0018,0024', str),
    ('PulseSequenceName', '0019,109c', str),
    ('MRAcquisitionType', '0018,0023', str),
    ('SeriesDescription', '0008,103e', str),
    ('ProtocolName', '0018,1030', str),
    ('ImageType', '0008,0008', _split),
    ('Modality', '0008,0060', str),
    ('RepetitionTime', '0018,0080', lambda x: float(x) * 1e-3),
    ('EchoTime', '0018,0081', lambda x: float(x) * 1e-3),
    ('FlipAngle', '0018,1314', float),
    ('ImagingFrequency', '0018,0084', float),
    ('PixelBandwidth', '0018,0095', float),
    ('SliceThickness', '0018,0050', float),
    ('SpacingBetweenSlices', '0018,0088', float),
    ('EchoTrainLength', '0018,0091', int),
    ('PercentSampling', '0018,0093', float),
    ('PercentPhaseFOV', '0018,0094', float),
    ('NumberOfAverages', '0018,0083', float),
    ('PatientPosition', '0018,5100', str),
    ('InPlanePhaseEncodingDirectionDICOM', '0018,1312', str),
    ('ImageOrientationPatientDICOM', '0020,0037',
     lambda x: [float(v) for v in _split(x)]),
    ('SAR', '0018,1316', float),
]


@dicom_rule
def d_direct(ctx: Context):
    for key, tag, conv in _DIRECT:
        try:
            ctx.set(key, conv(ctx.tag(tag)))
        except (Missing, ValueError):
            pass


@dicom_rule
def d_inversion(ctx: Context):
    ti = float(ctx.tag('0018,0082'))
    if ti > 0:
        ctx.set('InversionTime', ti * 1e-3)


@dicom_rule
def d_matrix(ctx: Context):
    acq = [int(v) for v in _split(ctx.tag('0018,1310'))]
    ctx.set('AcquisitionMatrixPE', max(acq[2:]))
    ctx.set('AcquisitionMatrixFE', max(acq[:2]))
    try:
        rows, cols = int(ctx.tag('0028,0010')), int(ctx.tag('0028,0011'))
        direction = ctx.tag('0018,1312')
        ctx.set('ReconMatrixPE', rows if direction == 'COL' else cols)
    except Missing:
        pass
    direction = ctx.out.get('InPlanePhaseEncodingDirectionDICOM')
    if direction:
        ctx.set('PhaseEncodingAxis', 'j' if direction == 'COL' else 'i')


@dicom_rule
def d_asset(ctx: Context):
    """(0043,1083) stores 1/R (in-plane, through-plane)."""
    values = [float(v) for v in _split(ctx.tag('0043,1083'))]
    if values and values[0] > 0 and values[0] != 1:
        ctx.set('ParallelReductionFactorInPlane', round(1 / values[0], 4))
    if len(values) > 1 and values[1] > 0 and values[1] != 1:
        ctx.set('ParallelReductionFactorOutOfPlane', round(1 / values[1], 4))


@dicom_rule
def d_epi(ctx: Context):
    """
    dcm2niix (GE/README.md#total-readout-time):
    lines = ceil(AcqPE / R / RF) * RF   (RF = 4 if PFF else 2)
    EES = (lines - 1) * ESP / (AcqPE - 1);  TRT = EES * (ReconPE - 1)
    """
    if 'EP' not in ctx.out.get('ScanningSequence', []):
        return
    esp = float(ctx.tag('0043,102c')) * 1e-6
    r = ctx.out.get('ParallelReductionFactorInPlane', 1)
    rf = 4 if 'PFF' in ctx.out.get('ScanOptions', []) else 2
    acq = ctx['AcquisitionMatrixPE']
    lines = ceil(acq / r / rf) * rf
    ees = (lines - 1) * esp / (acq - 1)
    ctx.set('EffectiveEchoSpacing', ees)
    recon = ctx.out.get('ReconMatrixPE', acq)
    ctx.set('TotalReadoutTime', ees * (recon - 1))


# ----------------------------------------------------------------------
#   Driver
# ----------------------------------------------------------------------

def ge_to_bids(prot: Protocol, nii: dict | None = None, extra: bool = True,
               strict: bool = False, explain: bool = False) -> dict:
    ctx = Context(prot, nii)
    rules = DICOM_RULES if prot.format == 'dicom' else SHEET_RULES
    for func in rules:
        try:
            func(ctx)
        except (Missing, ValueError, KeyError, IndexError) as e:
            LOGGER.debug(f'{func.__name__}: skipped ({e})')
        except Exception as e:
            if strict:
                raise
            LOGGER.warning(f'{func.__name__}: {type(e).__name__}: {e}')
    out = ctx.out
    if not extra:
        out = {k: v for k, v in out.items() if k not in (
            'EchoPlanarPulseSequence', 'PhaseEncodingAnatomicalAxis',
            'AcquisitionMatrixFE')}
    return out
