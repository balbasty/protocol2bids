"""
Siemens protocol -> BIDS sidecar.

Each rule is a small function that reads protocol parameters through a
`Context` and writes one or more sidecar keys. When a needed parameter is
absent, the rule raises `Missing` (directly or through `Context.get`) and
is skipped. Any *other* exception is a bug: it is raised in strict mode
and logged otherwise.

Formulas follow the notes in `notes/` (siemens_dicom.md, mprage.md,
turboflash.md, phase_encoding.md, frequency_encoding.md).

Keys are of three kinds (see `KEY_KINDS`):
* BIDS keys (https://bids-specification.readthedocs.io)
* dcm2niix keys that are not part of BIDS but are commonly found in
  sidecars (`AcquisitionMatrixPE`, `ReconMatrixPE`, `PhaseEncodingSteps`...)
* protocol2bids-specific helper keys (`DirectionPE`,
  `OversampledAcquisitionMatrixPE`...), only written if `extra=True`.
"""
from __future__ import annotations

import re
from logging import getLogger
from math import ceil
from typing import Any, Callable

from ... import values as V
from ...model import Missing, Protocol
from ...utils.nii2axes import nii2axes

LOGGER = getLogger(__name__)


# ----------------------------------------------------------------------
#   Context
# ----------------------------------------------------------------------

class Context:

    def __init__(self, prot: Protocol, nii: dict | None = None):
        self.prot = prot
        self.bids: dict[str, Any] = {}
        self.extra: dict[str, Any] = {}
        self.used: dict[str, list[str]] = {}
        self._current: str | None = None
        nii = dict(nii or {})
        if 'file' in nii or ('affine' in nii and 'shape' in nii):
            self.vox2anat, self.anat2vox, self.shape = nii2axes(**nii)
        else:
            self.vox2anat = self.anat2vox = self.shape = None

    # protocol access -------------------------------------------------
    def get(self, key, card=None, group=None):
        value = self.prot.get(key, card=card, group=group)
        if self._current:
            where = f'{card}//' if isinstance(card, str) else ''
            self.used.setdefault(self._current, []).append(where + key)
        if value is None:
            raise Missing(key)
        return value

    def opt(self, key, card=None, group=None, default=None):
        try:
            return self.get(key, card, group)
        except Missing:
            return default

    def has(self, key, card=None, group=None) -> bool:
        return self.prot.has(key, card=card, group=group)

    def getall(self, pattern: str, card=None) -> list[tuple[str, str]]:
        """All (key, value) whose key matches a glob pattern."""
        return [(e.key, e.value) for e in self.prot.find(pattern, card)
                if e.value is not None]

    # output access ---------------------------------------------------
    def __getitem__(self, key):
        if key in self.bids:
            return self.bids[key]
        if key in self.extra:
            return self.extra[key]
        raise Missing(key)

    def __contains__(self, key):
        return key in self.bids or key in self.extra

    def set(self, key, value):
        if value is None:
            return
        if KEY_KINDS.get(key, 'extra') == 'extra':
            self.extra[key] = value
        else:
            self.bids[key] = value


RULES: list[Callable[[Context], None]] = []


def rule(func):
    RULES.append(func)
    return func


# ----------------------------------------------------------------------
#   Key kinds (order of this dict = order of keys in the output)
# ----------------------------------------------------------------------

_BIDS = """
Manufacturer ManufacturersModelName SoftwareVersions MagneticFieldStrength
ReceiveCoilActiveElements MatrixCoilMode CoilCombinationMethod
PulseSequenceType ScanningSequence SequenceVariant ScanOptions SequenceName
PulseSequenceDetails MRAcquisitionType MTState SpoilingState SpoilingType
SpoilingRFPhaseIncrement B0ShimmingTechnique B1ShimmingTechnique
NumberShots ParallelReductionFactorInPlane ParallelReductionFactorOutOfPlane
ParallelAcquisitionTechnique PartialFourier PartialFourierDirection
PhaseEncodingDirection EffectiveEchoSpacing TotalReadoutTime
EchoTime EchoTime1 EchoTime2 InversionTime SliceTiming
SliceEncodingDirection DwellTime FlipAngle MultibandAccelerationFactor
RepetitionTime RepetitionTimeExcitation RepetitionTimePreparation
ArterialSpinLabelingType
""".split()

_DCM2NIIX = """
Modality ProtocolName SeriesDescription ImageType ImagingFrequency
BaseResolution AcquisitionMatrixPE ReconMatrixPE PercentPhaseFOV
PercentSampling PhaseResolution PhaseEncodingSteps EchoTrainLength
PixelBandwidth BandwidthPerPixelPhaseEncode DerivedVendorReportedEchoSpacing
SliceThickness SpacingBetweenSlices NumberOfAverages
""".split()

KEY_KINDS = {**{k: 'bids' for k in _BIDS}, **{k: 'dcm2niix' for k in _DCM2NIIX}}


# ----------------------------------------------------------------------
#   Helpers
# ----------------------------------------------------------------------

def sequence_name(ctx: Context) -> str:
    name = ctx.prot.header.get('SequenceName')
    if name:
        return name
    return ctx.get('Sequence Name', card='Sequence')


def base_sequence(name: str) -> str:
    """Strip user prefixes and suffixes: 'cmrr_mbep2d_bold' -> 'mbep2d_bold',
    'ep2d_bold_PMU' -> 'ep2d_bold'"""
    return name.split('\\')[-1].strip().lstrip('*')


def is_cmrr(name: str) -> bool:
    """CMRR (or HCP) multiband sequences."""
    return bool(re.search(r'cmrr|mbep2d|hcp_', name.lower()))


def is_3d(ctx: Context) -> bool:
    dim = ctx.opt('Dimension', card='Sequence')
    if dim:
        return dim.strip().upper().startswith('3')
    if ctx.has('Slices per slab') or ctx.has('Slabs'):
        return True
    if ctx.has('Slices', card=['Routine', 'Geometry']):
        return False
    raise Missing('Dimension')


def phase_oversampling(ctx: Context) -> float:
    return V.percent(ctx.opt('Phase oversampling', default='0')) / 100


def slice_oversampling(ctx: Context) -> float:
    return V.percent(ctx.opt('Slice oversampling', default='0')) / 100


def accel_pe(ctx: Context) -> int:
    mode = ctx.opt('PAT mode', card='Resolution')
    if mode is not None and V.is_off(mode):
        return 1
    try:
        return V.integer(ctx.get('Accel. factor PE', card='Resolution'))
    except Missing:
        return 1


def accel_3d(ctx: Context) -> int:
    mode = ctx.opt('PAT mode', card='Resolution')
    if mode is not None and V.is_off(mode):
        return 1
    try:
        return V.integer(ctx.get('Accel. factor 3D', card='Resolution'))
    except Missing:
        return 1


def multiband(ctx: Context) -> int:
    try:
        return V.integer(ctx.get('Multi-band accel. factor'))
    except Missing:
        return 1


def echo_times(ctx: Context) -> list[float]:
    """All echo times (seconds), in order."""
    tes = ctx.getall('TE', card=['Routine', 'Contrast'])
    if tes:
        return [V.seconds(tes[0][1])]
    multi = ctx.getall('TE *', card=['Routine', 'Contrast'])
    multi = [(int(V.number(k[2:])), v) for k, v in multi
             if re.fullmatch(r'TE\s*\d+', k)]
    if not multi:
        raise Missing('TE')
    seen = {}
    for i, v in multi:
        seen.setdefault(i, V.seconds(v))
    return [seen[i] for i in sorted(seen)]


def numbered(ctx: Context, key: str, card=None) -> list[str]:
    """Values of `key` or of `key 1`, `key 2`, ..."""
    try:
        return [ctx.get(key, card=card)]
    except Missing:
        pass
    items = ctx.getall(f'{key} *', card=card)
    items = [(int(V.number(k[len(key):])), v) for k, v in items
             if re.fullmatch(re.escape(key) + r'\s*\d+', k, re.I)]
    if not items:
        raise Missing(key)
    seen = {}
    for i, v in items:
        seen.setdefault(i, v)
    return [seen[i] for i in sorted(seen)]


def scalar_or_list(x: list):
    return x[0] if len(x) == 1 else x


# ----------------------------------------------------------------------
#   Sequence classification
# ----------------------------------------------------------------------

# (regex on sequence name, family, pulse sequence type)
SEQUENCES = [
    (r'ep2d_diff|epse|ep_?seg_?se|ep2d_se|mbep2d_se|mbep2d_diff|'
     r'ep2d_.*diff|resolve|ep3d_se|epi_se|diff',
     'SE-EPI', 'Spin Echo EPI'),
    (r'ep2d_pasl|ep2d_pcasl|pcasl|pasl|ep2d_tra_pasl',
     'GRE-EPI', 'Gradient Echo EPI'),
    (r'ep2d|epfid|mbep2d|ep3d|epi|ep_seg|bold',
     'GRE-EPI', 'Gradient Echo EPI'),
    (r'tgse|grase', 'GRASE', 'Gradient And Spin Echo'),
    (r'mp2rage|memprage|tfl|mprage|t1map',
     'TFL', 'MPRAGE'),
    (r'tfi|trufi|ciss|fisp|psif', 'TFI', 'bSSFP'),
    (r'fl_tof|tof', 'FLASH', 'Spoiled Gradient Echo'),
    (r'swi|fl_r|fl3d|fl2d|^fl|flash|vibe|fm_r|mtflash|b1map',
     'FLASH', 'Spoiled Gradient Echo'),
    (r'gre|field_?mapping|fme', 'GRE', 'Gradient Echo'),
    (r'spcir|spc_ir', 'SPACE', 'FLAIR'),
    (r'spc', 'SPACE', 'T2-SPACE'),
    (r'tir|qtir', 'TSE', 'Turbo Inversion Recovery'),
    (r'haste', 'TSE', 'Single-shot Fast Spin Echo'),
    (r'tse', 'TSE', 'Fast Spin Echo'),
    (r'(^|_)se($|_)|seste|^se\d', 'SE', 'Spin Echo'),
]


def classify(name: str) -> tuple[str, str]:
    base = base_sequence(name).lower()
    for pattern, family, label in SEQUENCES:
        if re.search(pattern, base):
            return family, label
    raise Missing(f'Unknown sequence {name}')


def inversion(ctx: Context) -> bool:
    prep = ctx.opt('Magn. preparation', card='Contrast')
    if prep is not None:
        return 'IR' in prep.upper() or 'INV' in prep.upper()
    family, _ = classify(sequence_name(ctx))
    if family in ('TFL',):
        return ctx.has('TI', card='Contrast') or ctx.has('TI *')
    if ctx.has('TI', card='Contrast'):
        return True
    return False


def rf_spoiled(ctx: Context) -> bool:
    value = ctx.opt('RF spoiling', card='Sequence')
    if value is not None:
        return not V.is_off(value)
    family, _ = classify(sequence_name(ctx))
    if family in ('FLASH', 'TFL'):
        return True     # FLASH sequences are RF-spoiled by default
    raise Missing('RF spoiling')


# ----------------------------------------------------------------------
#   Hardware
# ----------------------------------------------------------------------

FIELD_STRENGTH = [
    # (normalised model prefix, field)
    ('terra', 7.0), ('7t', 7.0), ('investigational', 7.0),
    ('trio', 3.0), ('allegra', 3.0), ('verio', 3.0), ('skyra', 3.0),
    ('prisma', 3.0), ('vida', 3.0), ('lumina', 3.0), ('spectra', 3.0),
    ('biograph', 3.0), ('connectom', 3.0), ('cimax', 3.0),
    ('cima', 3.0), ('seara', 3.0),
    ('avanto', 1.5), ('aera', 1.5), ('sonata', 1.5), ('symphony', 1.5),
    ('espree', 1.5), ('essenza', 1.5), ('amira', 1.5), ('sola', 1.5),
    ('altea', 1.5), ('sempra', 1.5), ('mica', 1.5), ('vision', 1.5),
    ('magnetomflow', 1.5), ('flow', 1.5),
    ('harmony', 1.0), ('freemax', 0.55), ('freestar', 0.55),
    ('concerto', 0.2), ('c!', 0.35),
]


@rule
def hardware(ctx: Context):
    ctx.set('Manufacturer', 'Siemens')
    model = ctx.prot.scanner.get('ManufacturersModelName')
    ctx.set('ManufacturersModelName', model)
    ctx.set('SoftwareVersions', ctx.prot.scanner.get('SoftwareVersions'))


@rule
def field_strength(ctx: Context):
    model = ctx.prot.scanner.get('ManufacturersModelName') or ''
    norm = re.sub(r'[^a-z0-9!]', '', model.lower())
    for prefix, field in FIELD_STRENGTH:
        if norm.startswith(prefix):
            ctx.set('MagneticFieldStrength', field)
            return
    # Fallback: Larmor frequency
    freq = V.number(ctx.get('Frequency 1H', card='System'))
    ctx.set('MagneticFieldStrength', round(freq / 42.577 * 2) / 2)


@rule
def imaging_frequency(ctx: Context):
    freq = V.number(ctx.get('Frequency 1H', card='System'))
    if freq > 0:
        ctx.set('ImagingFrequency', freq)


@rule
def coils(ctx: Context):
    ctx.set('ReceiveCoilActiveElements',
            ctx.opt('Coil elements', card=['Routine', 'Sequence']))
    ctx.set('MatrixCoilMode', ctx.opt('Matrix Coil Mode'))
    mode = ctx.opt('Coil Combine Mode', card='System')
    if mode:
        ctx.set('CoilCombinationMethod', {
            'sum of squares': 'rSOS',
            'adaptive combine': 'Adaptive Combine',
        }.get(mode.lower(), mode))


@rule
def shimming(ctx: Context):
    ctx.set('B0ShimmingTechnique', ctx.opt('B0 Shim mode') or
            ctx.opt('Shim mode', card='System'))
    ctx.set('B1ShimmingTechnique', ctx.opt('B1 Shim mode'))


# ----------------------------------------------------------------------
#   Names
# ----------------------------------------------------------------------

@rule
def names(ctx: Context):
    ctx.set('Modality', 'MR')
    if ctx.prot.name:
        ctx.set('ProtocolName', ctx.prot.name)
        ctx.set('SeriesDescription', ctx.prot.name)
    ctx.set('ImageType', ['ORIGINAL', 'PRIMARY'])


@rule
def sequence(ctx: Context):
    name = sequence_name(ctx)
    ctx.set('SequenceName', name)
    folder = (ctx.prot.header.get('SequenceFolder') or '').upper()
    if folder == 'SIEMENS':
        ctx.set('PulseSequenceDetails', f'%SiemensSeq%\\{name}')
    elif folder in ('USER', 'CUSTOMER'):
        ctx.set('PulseSequenceDetails', f'%CustomerSeq%\\{name}')


@rule
def acquisition_type(ctx: Context):
    ctx.set('MRAcquisitionType', '3D' if is_3d(ctx) else '2D')


@rule
def sequence_type(ctx: Context):
    name = sequence_name(ctx)
    family, label = classify(name)
    mb = multiband(ctx)
    epi = family.endswith('EPI')
    ir = inversion(ctx)
    try:
        spoiled = rf_spoiled(ctx)
    except Missing:
        spoiled = False

    # ScanningSequence (as written by Siemens in DICOM)
    if epi:
        scanning = ['EP']
    elif family in ('SE', 'TSE', 'SPACE'):
        scanning = ['SE']
    elif family == 'GRASE':
        scanning = ['GR', 'SE']
    else:
        scanning = ['GR']
    if ir:
        scanning.append('IR')

    # SequenceVariant (as found in dcm2niix sidecars of Siemens data,
    # see notes/conversion_rules.md)
    base = base_sequence(name).lower()
    diffusion = 'diff' in base or ctx.has('Diffusion mode')
    variant = []
    segmented = epi or family in ('TSE', 'SPACE', 'TFL', 'GRASE', 'TFI')
    if segmented:
        variant.append('SK')
    if family == 'TFI' or (family == 'GRE-EPI' and is_cmrr(name)):
        variant.append('SS')
    if (
        family in ('FLASH', 'TFL', 'GRE', 'TSE', 'SPACE')
        or (family == 'SE-EPI' and diffusion) or (spoiled and not epi)
    ):
        variant.append('SP')
    if ir or family == 'TFL':
        variant.append('MP')
    mtc = ctx.opt('MTC', card='Contrast')
    if mtc is not None and not V.is_off(mtc):
        variant.append('MTC')
    if phase_oversampling(ctx) > 0:
        variant.append('OSP')
    if not variant:
        variant = ['NONE']

    # ScanOptions
    options = []
    if ir:
        options.append('IR')
    pf = ctx.opt('Phase partial Fourier', card='Resolution')
    if pf is not None and V.fraction(pf) < 1:
        options.append('PFP')
    asym = ctx.opt('Asymmetric echo')
    if asym is not None and asym.strip().lower() in ('on', 'weak', 'strong'):
        options.append('PFF')
    fat = ctx.opt('Fat suppr.', card='Contrast')
    if fat is not None and 'sat' in fat.lower():
        options.append('FS')
    flow = ctx.opt('Flow comp.')
    if flow is not None and flow.strip().lower() not in (
            'no', 'none', 'off', '0'):
        options.append('FC')
    physio = (ctx.opt('1st Signal/Mode', card='Physio') or '').upper()
    if 'ECG' in physio:
        options.append('CG')
    elif 'PULSE' in physio:
        options.append('PPG')
    elif 'RESP' in physio:
        options.append('RG')

    if mb > 1:
        label = 'Multiband ' + label
    ctx.set('PulseSequenceType', label)
    ctx.set('ScanningSequence', scanning)
    ctx.set('SequenceVariant', variant)
    ctx.set('ScanOptions', options)
    ctx.set('EchoPlanarPulseSequence', epi)
    ctx.set('SequenceFamily', family)


@rule
def asl(ctx: Context):
    name = base_sequence(sequence_name(ctx)).lower()
    if 'pcasl' in name:
        ctx.set('ArterialSpinLabelingType', 'PCASL')
    elif 'pasl' in name:
        ctx.set('ArterialSpinLabelingType', 'PASL')


@rule
def magnetization_transfer(ctx: Context):
    mtc = ctx.get('MTC', card='Contrast')
    ctx.set('MTState', not V.is_off(mtc))


@rule
def spoiling(ctx: Context):
    family, _ = classify(sequence_name(ctx))
    if family.endswith('EPI') or family in ('SE', 'TSE', 'SPACE', 'GRASE'):
        return
    if family == 'TFI':
        ctx.set('SpoilingState', False)
        return
    rf = rf_spoiled(ctx)
    gradient = family in ('FLASH', 'TFL')
    ctx.set('SpoilingState', rf or gradient)
    if rf and gradient:
        ctx.set('SpoilingType', 'COMBINED')
    elif rf:
        ctx.set('SpoilingType', 'RF')
    elif gradient:
        ctx.set('SpoilingType', 'GRADIENT')
    # Explicit phase increment (some user sequences print it)
    step = ctx.opt('Spoil Phase Step') or ctx.opt('RF spoil phase')
    if rf and step:
        ctx.set('SpoilingRFPhaseIncrement', V.number(step))
    elif rf and (ctx.prot.header.get('SequenceFolder') or '') == 'SIEMENS':
        # Siemens product default (see notes/rfspoil_increment.md)
        ctx.set('SpoilingRFPhaseIncrement', 50.0)


# ----------------------------------------------------------------------
#   Timing / contrast
# ----------------------------------------------------------------------

@rule
def repetition_time(ctx: Context):
    trs = [V.seconds(x) for x in numbered(ctx, 'TR', card='Routine')]
    ctx.set('RepetitionTime', scalar_or_list(trs))
    family, _ = classify(sequence_name(ctx))
    if family == 'TFL':
        # MPRAGE: TR is the time between two inversions
        ctx.set('RepetitionTimePreparation', trs[0])
        es = ctx.opt('Echo spacing', card='Sequence')
        if es:
            ctx.set('RepetitionTimeExcitation', V.seconds(es))
    elif family in ('FLASH', 'GRE', 'TFI') and len(trs) == 1:
        ctx.set('RepetitionTimeExcitation', trs[0])


@rule
def echo_time(ctx: Context):
    tes = echo_times(ctx)
    ctx.set('EchoTime', scalar_or_list(tes))
    if len(tes) == 2:
        ctx.set('EchoTime1', tes[0])
        ctx.set('EchoTime2', tes[1])


@rule
def inversion_time(ctx: Context):
    tis = [V.seconds(x) for x in numbered(ctx, 'TI', card='Contrast')]
    ctx.set('InversionTime', scalar_or_list(tis))


@rule
def flip_angle(ctx: Context):
    fas = [V.number(x) for x in numbered(ctx, 'Flip angle', card='Contrast')]
    ctx.set('FlipAngle', scalar_or_list(fas))


@rule
def averages(ctx: Context):
    ctx.set('NumberOfAverages', V.integer(ctx.get('Averages')))


@rule
def multiband_factor(ctx: Context):
    mb = V.integer(ctx.get('Multi-band accel. factor'))
    ctx.set('MultibandAccelerationFactor', mb)


# ----------------------------------------------------------------------
#   Geometry
# ----------------------------------------------------------------------

_SYSTEM_DEFAULTS = {'S': 'R >> L', 'C': 'A >> P', 'T': 'F >> H'}
_SYSTEM_KEYS = {'S': 'Sagittal', 'C': 'Coronal', 'T': 'Transversal'}


def main_orientation(ctx: Context) -> str:
    value = ctx.get('Orientation', card=['Routine', 'Geometry'],
                    group='Sl')
    return V.orientation(value)[0]


@rule
def directions(ctx: Context):
    """Anatomical directions of the slice/phase/frequency axes."""
    orient = main_orientation(ctx)
    convention = ctx.opt(_SYSTEM_KEYS[orient], card='System',
                         default=_SYSTEM_DEFAULTS[orient])
    try:
        se = V.direction(convention)
    except ValueError:
        se = V.direction(_SYSTEM_DEFAULTS[orient])
    ctx.set('DirectionSE', se)
    pe = V.direction(ctx.get('Phase enc. dir.', card=['Routine', 'Geometry'],
                             group='Sl'))
    ctx.set('DirectionPE', pe)
    axes = {'RL': 'x', 'LR': 'x', 'AP': 'y', 'PA': 'y', 'IS': 'z', 'SI': 'z'}
    remaining = ({'x', 'y', 'z'} - {axes[se], axes[pe]})
    if len(remaining) == 1:
        fe_axis = remaining.pop()
        # polarity of the readout is not printed: use Siemens display
        # conventions
        fe = {'x': V.direction(ctx.opt('Sagittal', card='System',
                                       default='R >> L')),
              'y': V.direction(ctx.opt('Coronal', card='System',
                                       default='A >> P')),
              'z': V.direction(ctx.opt('Transversal', card='System',
                                       default='F >> H'))}[fe_axis]
        ctx.set('DirectionFE', fe)


def _is_3d_non_epi(ctx: Context) -> bool:
    try:
        return is_3d(ctx) and not classify(sequence_name(ctx))[0].endswith(
            'EPI')
    except Missing:
        return False


@rule
def nifti_directions(ctx: Context):
    if ctx.anat2vox is None:
        raise Missing('nifti')
    shape = ctx.shape
    for name, key, dirkey in [
        ('PhaseEncodingDirection', 'PE', 'DirectionPE'),
        ('SliceEncodingDirection', 'SE', 'DirectionSE'),
        ('FrequencyEncodingDirection', 'FE', 'DirectionFE'),
    ]:
        if dirkey not in ctx:
            continue
        axis = ctx.anat2vox[ctx[dirkey]]
        if name == 'PhaseEncodingDirection' and _is_3d_non_epi(ctx):
            # dcm2niix does not report a PE polarity for 3D sequences
            # (polarity is meaningless when there is no EPI distortion)
            ctx.set('PhaseEncodingAxis', axis[0])
        else:
            ctx.set(name, axis)
        ctx.set(f'ReconMatrix{key}', int(shape['ijk'.index(axis[0])]))


@rule
def slice_geometry(ctx: Context):
    thickness = V.quantity(ctx.get('Slice thickness', card='Routine'), 'mm')
    ctx.set('SliceThickness', thickness)
    if is_3d(ctx):
        # dcm2niix writes no SpacingBetweenSlices for single-slab 3D
        # Siemens data; "Dist. factor" is the gap between *slabs*.
        ctx.set('SliceGap', 0.0)
        return
    dist = ctx.opt('Dist. factor', card=['Routine', 'Geometry'], group='Sl')
    dist = V.percent(dist) / 100 if dist else 0.0
    ctx.set('SpacingBetweenSlices', round(thickness * (1 + dist), 6))
    ctx.set('SliceGap', round(thickness * dist, 6))


# ----------------------------------------------------------------------
#   k-space / matrices
# ----------------------------------------------------------------------

@rule
def matrices(ctx: Context):
    base = V.integer(ctx.get('Base resolution', card='Resolution'))
    phase_res = V.percent(ctx.get('Phase resolution',
                                  card='Resolution')) / 100
    fov_phase = V.percent(ctx.get('FoV phase', card=['Routine',
                                                     'Resolution'])) / 100
    fov_read = V.quantity(ctx.get('FoV read', card=['Routine',
                                                    'Resolution']), 'mm')
    po = phase_oversampling(ctx)

    acq_fe = base
    acq_pe = int(round(base * phase_res * fov_phase))
    ctx.set('BaseResolution', base)
    ctx.set('PhaseResolution', phase_res)
    ctx.set('PercentSampling', phase_res * 100)
    ctx.set('PercentPhaseFOV', fov_phase * 100)
    ctx.set('AcquisitionMatrixFE', acq_fe)
    ctx.set('AcquisitionMatrixPE', acq_pe)
    ctx.set('OversampledAcquisitionMatrixFE', 2 * acq_fe)
    ctx.set('OversampledAcquisitionMatrixPE', int(round(acq_pe * (1 + po))))
    ctx.set('FieldOfViewFE', fov_read)
    ctx.set('FieldOfViewPE', fov_read * fov_phase)

    pf_pe = V.fraction(ctx.opt('Phase partial Fourier', card='Resolution',
                               default='Off'))
    ctx.set('PartialFourierPE', pf_pe)
    ctx.set('PhaseEncodingSteps', int(round(acq_pe * (1 + po) * pf_pe)))


@rule
def slice_matrix(ctx: Context):
    if is_3d(ctx):
        slabs = V.integer(ctx.opt('Slabs', group='Sl', default='1'))
        per_slab = V.integer(ctx.get('Slices per slab'))
        n = slabs * per_slab
        os_ = slice_oversampling(ctx)
        ctx.set('AcquisitionMatrixSE', n)
        ctx.set('OversampledAcquisitionMatrixSE', int(round(n * (1 + os_))))
        pf = V.fraction(ctx.opt('Slice partial Fourier', card='Resolution',
                                default='Off'))
        ctx.set('PartialFourierSE', pf)
    else:
        n = V.integer(ctx.get('Slices', card=['Routine', 'Geometry'],
                              group='Sl'))
        ctx.set('AcquisitionMatrixSE', n)
        ctx.set('OversampledAcquisitionMatrixSE', n)
    spacing = (ctx['SpacingBetweenSlices'] if 'SpacingBetweenSlices' in ctx
               else ctx['SliceThickness'])
    ctx.set('FieldOfViewSE', n * spacing)


@rule
def recon_matrix(ctx: Context):
    """Fallback when no nifti is available."""
    interp = ctx.opt('Interpolation', card='Resolution', default='Off')
    factor = 1 if V.is_off(interp) else 2
    for key in ('FE', 'PE'):
        if f'ReconMatrix{key}' not in ctx:
            ctx.set(f'ReconMatrix{key}', ctx[f'AcquisitionMatrix{key}'] *
                    factor)
    if 'ReconMatrixSE' not in ctx:
        ctx.set('ReconMatrixSE', ctx['AcquisitionMatrixSE'])


@rule
def parallel_imaging(ctx: Context):
    mode = ctx.get('PAT mode', card='Resolution')
    if V.is_off(mode):
        return
    ctx.set('ParallelAcquisitionTechnique', mode)
    ctx.set('ParallelReductionFactorInPlane', accel_pe(ctx))
    if is_3d(ctx):
        ctx.set('ParallelReductionFactorOutOfPlane', accel_3d(ctx))


@rule
def partial_fourier(ctx: Context):
    pe = ctx['PartialFourierPE'] if 'PartialFourierPE' in ctx else 1.0
    se = ctx['PartialFourierSE'] if 'PartialFourierSE' in ctx else 1.0
    if pe < 1:
        ctx.set('PartialFourier', pe)
    elif se < 1:
        ctx.set('PartialFourier', se)
    if pe < 1 and se < 1:
        ctx.set('PartialFourierDirection', 'COMBINATION')
    elif pe < 1:
        ctx.set('PartialFourierDirection', 'PHASE')
    elif se < 1:
        ctx.set('PartialFourierDirection', 'SLICE_SELECT')


@rule
def bandwidth(ctx: Context):
    bw = V.number(numbered(ctx, 'Bandwidth', card='Sequence')[0])
    ctx.set('PixelBandwidth', bw)
    # Siemens bandwidth is per pixel of the (non-oversampled) readout,
    # while DwellTime (DICOM RealDwellTime, in ns) includes the default
    # 2x readout oversampling.
    dwell = 1 / (bw * ctx['AcquisitionMatrixFE'] * 2)
    ctx.set('DwellTime', round(dwell * 1e9) * 1e-9)


# ----------------------------------------------------------------------
#   EPI
# ----------------------------------------------------------------------

def _is_epi(ctx: Context) -> bool:
    family, _ = classify(sequence_name(ctx))
    return family.endswith('EPI')


@rule
def epi_timing(ctx: Context):
    if not _is_epi(ctx):
        return
    es = V.seconds(ctx.get('Echo spacing', card='Sequence'))
    ctx.set('DerivedVendorReportedEchoSpacing', es)
    po = phase_oversampling(ctx)
    r = accel_pe(ctx)
    # Time between two adjacent lines of the (full, oversampled) k-space
    # grid, see notes/siemens_dicom.md
    eff = es * (1 + po) / r
    recon = ctx['ReconMatrixPE']
    ctx.set('EffectiveEchoSpacing', eff)
    ctx.set('BandwidthPerPixelPhaseEncode', 1 / (eff * recon))
    ctx.set('TotalReadoutTime', eff * (recon - 1))


@rule
def echo_train(ctx: Context):
    family, _ = classify(sequence_name(ctx))
    if family.endswith('EPI'):
        steps = ctx['PhaseEncodingSteps']
        r = accel_pe(ctx)
        try:
            shots = V.integer(ctx.get('Segments', card='Sequence'))
        except Missing:
            shots = 1
        ctx.set('EchoTrainLength', int(ceil(steps / r / shots)))
        ctx.set('NumberShots', shots)
    elif family in ('TSE', 'SPACE', 'GRASE'):
        etl = V.integer(ctx.get('Turbo factor'))
        ctx.set('EchoTrainLength', etl)
        if family != 'SPACE':
            steps = ctx['PhaseEncodingSteps']
            ctx.set('NumberShots', int(ceil(steps / accel_pe(ctx) / etl)))


def cmrr_interleaved(nshots: int) -> list[int]:
    """
    Excitation order of CMRR multiband interleaved acquisitions
    (CMRR_MB_Slice_Order.pdf): always starts with slice 0; special orders
    for an even number of shots > 4 to avoid exciting adjacent slices
    in a row.
    """
    from math import gcd
    if nshots % 2 or nshots <= 4:
        return list(range(0, nshots, 2)) + list(range(1, nshots, 2))
    if nshots == 6:
        return [0, 2, 4, 1, 5, 3]
    inc = nshots // 2 - 1
    if inc % 2 == 0:
        inc -= 1
    if gcd(inc, nshots) != 1:
        raise Missing('CMRR order')
    return [(k * inc) % nshots for k in range(nshots)]


def software_generation(version: str | None) -> tuple[str, int] | None:
    """
    'syngo MR E11' / 'syngo_MR_E11' -> ('VE', 11); 'syngo MR XA30' ->
    ('XA', 30); 'Numaris/X VA20A-04ML' -> ('XA', 20); 'syngo MR B17' ->
    ('VB', 17); 'syngo MR 2004A' -> ('VA', 25).
    """
    v = (version or '').replace('_', ' ')
    m = re.search(r'Numaris/X\s*VA(\d\d)', v) or re.search(r'XA(\d\d)', v)
    if m:
        return ('XA', int(m.group(1)))
    m = re.search(r'syngo\s*MR\s*([ABDE])(\d\d)', v)
    if m:
        return ('V' + m.group(1), int(m.group(2)))
    if re.search(r'syngo\s*MR\s*200\d', v):
        return ('VA', 25)
    return None


def sms_interleaved(nslices: int, mb: int,
                    version: str | None = None) -> list[int]:
    """
    Excitation order of Siemens *product* SMS interleaved acquisitions
    (empirical rule, matching the scanner-reported times of 374 dcm2niix
    sidecars, VE11 to XA61; see notes/conversion_rules.md):

    * even number of excitations (nexc = N / MB): even groups first, then
      odd groups, with group `nexc` moved to position floor(nexc/4) of the
      even half (and group 1 to the same position of the odd half), so
      that the two adjacent groups nexc and 1 are excited half a TR apart:
      nexc=8 -> 2,4,8,6,3,5,1,7 (1-based);
    * odd nexc: single-band parity rule, applied to the total number of
      slices N on VB/VD/VE/XA1x/XA20, and to nexc on XA30 and later.
    """
    nexc = nslices // mb
    if nexc % 2 == 0:
        p = nexc // 4
        evens = [2 * i for i in range(1, p + 1)] + [nexc] + \
            list(range(2 * p + 2, nexc - 1, 2))
        odds = [(e % nexc) + 1 for e in evens]
        return [g - 1 for g in evens + odds]
    gen = software_generation(version)
    if gen is None and mb % 2 == 0:
        # parity of N and nexc differ: depends on the (unknown) version
        raise Missing('software version (SMS slice order)')
    parity = nexc if (gen and gen >= ('XA', 30)) else nslices
    odd, even = list(range(0, nexc, 2)), list(range(1, nexc, 2))
    return odd + even if parity % 2 else even + odd


@rule
def slice_timing(ctx: Context):
    """Slice timing for 2D multi-slice acquisitions (Siemens ordering)."""
    if is_3d(ctx):
        return
    nslices = ctx['AcquisitionMatrixSE']
    tr = ctx['RepetitionTime']
    if isinstance(tr, list):
        return
    concat = V.integer(ctx.opt('Concatenations', default='1'))
    if concat != 1:
        return
    mode = (ctx.opt('Multi-slice mode') or '').lower()
    if mode and not mode.startswith(('interleaved', 'single shot')):
        return    # sequential: one slice at a time
    order = ctx.get('Series', card='Geometry').lower()
    delay = V.seconds(ctx.opt('Delay in TR', default='0 ms'))
    mb = multiband(ctx)
    if nslices % mb:
        return
    nexc = nslices // mb
    cmrr = is_cmrr(sequence_name(ctx))
    if order.startswith('interleaved'):
        if mb > 1 and cmrr:
            exc_order = cmrr_interleaved(nexc)
        elif mb > 1:
            exc_order = sms_interleaved(
                nslices, mb, ctx.prot.scanner.get('SoftwareVersions'))
        elif nexc % 2:
            exc_order = list(range(0, nexc, 2)) + list(range(1, nexc, 2))
        else:
            exc_order = list(range(1, nexc, 2)) + list(range(0, nexc, 2))
    elif order.startswith('ascending'):
        exc_order = list(range(nexc))
    elif order.startswith('descending'):
        exc_order = list(range(nexc))[::-1]
    else:
        return
    dt = (tr - delay) / nexc
    exc_time = {e: i * dt for i, e in enumerate(exc_order)}
    timing = [round(exc_time[s % nexc], 6) for s in range(nslices)]
    ctx.set('SliceTiming', timing)
    ctx.set('SliceOrder', order.capitalize())


# ----------------------------------------------------------------------
#   Diffusion
# ----------------------------------------------------------------------

@rule
def diffusion(ctx: Context):
    if not ctx.has('Diffusion mode') and not ctx.has('b-value*'):
        return
    mode = ctx.opt('Diffusion mode')
    if mode:
        ctx.set('DiffusionMode', mode)
    ndir = ctx.opt('Diff. directions')
    if ndir:
        ctx.set('DiffusionNumberOfDirections', V.integer(ndir))
    bvals = [V.number(v) for k, v in ctx.getall('b-value*')
             if re.fullmatch(r'b-value\s*\d*', k, re.I)]
    if bvals:
        ctx.set('DiffusionBValues', bvals)


# ----------------------------------------------------------------------
#   Driver
# ----------------------------------------------------------------------

def siemens_to_bids(
    prot: Protocol,
    nii: dict | None = None,
    extra: bool = True,
    strict: bool = False,
    explain: bool = False,
) -> dict:
    """
    Convert a parsed Siemens protocol into a BIDS sidecar.

    Parameters
    ----------
    prot : Protocol
    nii : dict, optional
        `{'file': path}` or `{'affine': array, 'shape': list}`
    extra : bool
        Include protocol2bids-specific keys.
    strict : bool
        Raise on unexpected errors (bugs) instead of logging them.
    explain : bool
        Add a `_provenance` key listing the protocol parameters used by
        each rule.
    """
    ctx = Context(prot, nii)
    for func in RULES:
        ctx._current = func.__name__
        try:
            func(ctx)
        except (Missing, ValueError) as e:
            LOGGER.debug(f'{func.__name__}: skipped ({e})')
        except Exception as e:
            if strict:
                raise
            LOGGER.warning(f'{func.__name__}: {type(e).__name__}: {e}')
    ctx._current = None
    order = {k: i for i, k in enumerate(KEY_KINDS)}
    out = dict(sorted(ctx.bids.items(), key=lambda kv: order[kv[0]]))
    if extra:
        out.update(ctx.extra)
    if explain:
        out['_provenance'] = ctx.used
    return out
