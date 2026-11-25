"""
Philips ExamCard -> BIDS sidecar.

Conventions follow dcm2niix where it has one (see
notes/conversion_rules.md):

* Philips does not store the phase-encoding polarity: only
  `PhaseEncodingAxis` is written.
* Echo spacing / readout time are derived from the water-fat shift and
  written as `EstimatedEffectiveEchoSpacing` / `EstimatedTotalReadoutTime`
  (dcm2niix never writes `EffectiveEchoSpacing` for Philips).
* Slice timing follows the Philips slice orders (single package only).
"""
from __future__ import annotations

import re
from logging import getLogger
from math import sqrt
from typing import Any

from ... import values as V
from ...model import Missing, Protocol
from ...utils.nii2axes import nii2axes

LOGGER = getLogger(__name__)

GYRO = 42.576          # MHz/T
FAT_WATER_PPM = 3.4    # as in dcm2niix


class Context:
    def __init__(self, prot: Protocol, nii: dict | None):
        self.prot = prot
        self.out: dict[str, Any] = {}
        nii = dict(nii or {})
        if 'file' in nii or ('affine' in nii and 'shape' in nii):
            self.vox2anat, self.anat2vox, self.shape = nii2axes(**nii)
        else:
            self.vox2anat = self.anat2vox = self.shape = None

    def get(self, key, group=None):
        value = self.prot.get(key, group=group)
        if value is None:
            raise Missing(key)
        return value

    def opt(self, key, group=None, default=None):
        try:
            return self.get(key, group)
        except Missing:
            return default

    def __getitem__(self, key):
        if key not in self.out:
            raise Missing(key)
        return self.out[key]

    def __contains__(self, key):
        return key in self.out

    def set(self, key, value):
        if value is not None:
            self.out[key] = value


RULES = []


def rule(func):
    RULES.append(func)
    return func


def _pair(value: str) -> list[float]:
    """'2500 / 30' -> [2500., 30.]"""
    return [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', value)]


@rule
def hardware(ctx: Context):
    ctx.set('Manufacturer', 'Philips')
    ctx.set('ManufacturersModelName',
            ctx.prot.scanner.get('ManufacturersModelName'))
    field = ctx.prot.scanner.get('MagneticFieldStrength')
    if field is None:
        # water-fat shift (pix) x bandwidth (Hz/pix) = water-fat
        # difference in Hz = 3.4 ppm x gamma x B0
        wfs, bw = _pair(ctx.get('Act. WFS (pix) / BW (Hz)'))[:2]
        estimate = wfs * bw / (FAT_WATER_PPM * GYRO)
        field = min((0.5, 1.0, 1.5, 3.0, 7.0), key=lambda b: abs(b - estimate))
    ctx.set('MagneticFieldStrength', field)
    ctx.set('ImagingFrequency', round(field * GYRO, 4))


@rule
def names(ctx: Context):
    ctx.set('Modality', 'MR')
    ctx.set('ProtocolName', ctx.prot.name or None)


@rule
def coil(ctx: Context):
    ctx.set('ReceiveCoilName', ctx.opt('Coil selection') or
            ctx.opt('Coil selection 1'))


@rule
def timing(ctx: Context):
    tr, te = _pair(ctx.get('Act. TR/TE (ms)'))[:2]
    ctx.set('RepetitionTime', tr * 1e-3)
    ctx.set('EchoTime', te * 1e-3)


@rule
def flip(ctx: Context):
    ctx.set('FlipAngle', V.number(ctx.get('Flip angle (deg)')))


def _inverted(ctx: Context) -> bool:
    prep = (ctx.opt('TFE prepulse') or '').lower()
    technique = (ctx.opt('technique') or '').upper()
    return 'inv' in prep or 'IR' in technique


@rule
def inversion(ctx: Context):
    """
    TFE inversion: the prepulse delay as printed (time from the inversion
    to the first excitation, "To Exc"), which is what Philips stores in
    DICOM InversionTime. Note: with a linear profile order, the effective
    TI (to the k-space centre) is longer.
    """
    if not _inverted(ctx):
        return
    for key, group in (('To Exc (ms)', 'TFE prepulse'),
                       ('(ms)', 'TFE prepulse'), ('TI (ms)', None),
                       ('IR delay (ms)', None)):
        value = ctx.opt(key, group=group)
        if value is not None:
            try:
                ctx.set('InversionTime', V.number(value) * 1e-3)
                break
            except ValueError:
                pass
    interval = ctx.opt('(ms)', group='TFE factor')
    if interval is not None:
        try:
            ctx.set('RepetitionTimePreparation', V.number(interval) * 1e-3)
        except ValueError:
            pass


@rule
def sequence(ctx: Context):
    mode = (ctx.opt('Scan mode') or '').upper()
    technique = (ctx.opt('technique') or '').upper()
    fast = (ctx.opt('Fast Imaging mode') or '').upper()
    if mode:
        ctx.set('MRAcquisitionType', '3D' if mode.startswith('3D') else '2D')
    epi = fast == 'EPI'
    scanning = []
    if epi:
        scanning.append('EP')
    if technique.startswith(('FFE', 'T1FFE', 'T2FFE', 'B-FFE', 'BFFE')):
        scanning.append('GR')
    elif 'SE' in technique:
        scanning.append('SE')
    if _inverted(ctx):
        scanning.append('IR')
    if scanning:
        ctx.set('ScanningSequence', scanning)
    label = {
        ('FFE', 'EPI'): 'Gradient Echo EPI',
        ('SE', 'EPI'): 'Spin Echo EPI',
        ('FFE', 'TFE'): 'Turbo Field Echo',
        ('FFE', 'NONE'): 'Fast Field Echo',
        ('SE', 'TSE'): 'Turbo Spin Echo',
        ('IR', 'TSE'): 'Inversion Recovery Turbo Spin Echo',
    }.get((technique.split('-')[0], fast or 'NONE'))
    if 'IR' in scanning and label == 'Turbo Field Echo':
        label = 'Inversion Recovery Turbo Field Echo (MPRAGE-like)'
    ctx.set('PulseSequenceType', label)
    ctx.set('EchoPlanarPulseSequence', epi)
    if fast == 'TFE':
        ctx.set('RepetitionTimeExcitation', ctx['RepetitionTime'])


@rule
def parallel(ctx: Context):
    if V.is_off(ctx.get('SENSE')):
        return
    ctx.set('ParallelAcquisitionTechnique', 'SENSE')
    for e in ctx.prot.find('P reduction*'):
        ctx.set('ParallelReductionFactorInPlane', round(V.number(e.value), 3))
    for e in ctx.prot.find('S reduction*'):
        ctx.set('ParallelReductionFactorOutOfPlane',
                round(V.number(e.value), 3))


@rule
def multiband(ctx: Context):
    value = ctx.get('MB Factor') if ctx.prot.has('MB Factor') else \
        ctx.get('multiband factor')
    ctx.set('MultibandAccelerationFactor', V.integer(value))


@rule
def matrix(ctx: Context):
    m, p = [int(x) for x in _pair(ctx.get('ACQ matrix M x P'))[:2]]
    ctx.set('AcquisitionMatrixFE', m)
    ctx.set('AcquisitionMatrixPE', p)
    recon = ctx.opt('reconstruction', group='Matrix scan') or \
        ctx.opt('Reconstruction matrix') or ctx.opt('reconstruction')
    if recon:
        ctx.set('ReconMatrixPE', V.integer(recon))


@rule
def halfscan(ctx: Context):
    if V.is_off(ctx.get('Halfscan')):
        return
    ctx.set('PartialFourierEnabled', 'YES')
    factor = ctx.opt('factor', group='Halfscan')
    if factor:
        ctx.set('PartialFourier', V.number(factor))


@rule
def geometry(ctx: Context):
    ctx.set('SliceThickness', V.number(ctx.get('Slice thickness (mm)')))
    gap = ctx.opt('gap (mm)')
    if gap is not None:
        try:
            ctx.set('SpacingBetweenSlices',
                    round(ctx['SliceThickness'] + V.number(gap), 6))
        except ValueError:
            pass


_ORIENT_AXES = {'transverse': 'z', 'sagittal': 'x', 'coronal': 'y'}
_ANAT_AXES = {'RL': 'x', 'LR': 'x', 'AP': 'y', 'PA': 'y', 'FH': 'z',
              'HF': 'z'}
# in-plane image axes of a DICOM image, per orientation: (rows, cols)
_INPLANE = {'z': ('x', 'y'), 'y': ('x', 'z'), 'x': ('y', 'z')}


@rule
def phase_encoding(ctx: Context):
    """Fold-over direction == phase-encoding axis (no polarity)."""
    fold = ctx.get('fold-over direction').upper().replace(' ', '')
    axis = _ANAT_AXES[fold]
    ctx.set('PhaseEncodingAnatomicalAxis', fold)
    if ctx.anat2vox is not None:
        code = {'x': 'LR', 'y': 'PA', 'z': 'IS'}[axis]
        ctx.set('PhaseEncodingAxis', ctx.anat2vox[code][0])
        return
    orient = (ctx.opt('slice orientation') or '').lower()
    if orient in _ORIENT_AXES:
        inplane = _INPLANE[_ORIENT_AXES[orient]]
        if axis in inplane:
            ctx.set('PhaseEncodingAxis', 'ij'[inplane.index(axis)])


@rule
def epi_readout(ctx: Context):
    """dcm2niix (issue #377) estimates from the water-fat shift."""
    if not ctx.out.get('EchoPlanarPulseSequence'):
        return
    wfs = _pair(ctx.get('Act. WFS (pix) / BW (Hz)'))[0]
    epi_factor = V.integer(ctx.get('EPI factor'))
    freq = ctx['ImagingFrequency']
    ctx.set('WaterFatShift', wfs)
    ctx.set('EchoTrainLength', epi_factor)
    actual_es = wfs / (freq * FAT_WATER_PPM * (epi_factor + 1))
    trt = actual_es * epi_factor
    ctx.set('EstimatedTotalReadoutTime', trt)
    recon = ctx['ReconMatrixPE'] if 'ReconMatrixPE' in ctx else \
        ctx['AcquisitionMatrixPE']
    ctx.set('EstimatedEffectiveEchoSpacing', trt / (recon - 1))


def philips_slice_order(order: str, n: int) -> list[int]:
    """
    Time-ordered slice indices (0-based) for a single package
    (G. Gilbert, Philips, fMRISliceOrder_R531 script).
    """
    order = order.lower().strip()
    if order in ('ascend', 'fh', 'ascending'):
        return list(range(n))
    if order in ('descend', 'hf', 'descending'):
        return list(range(n))[::-1]
    if order == 'default':
        return list(range(0, n, 2)) + list(range(1, n, 2))
    if order == 'interleaved':
        step = int(round(sqrt(n)))
        return [i for start in range(step) for i in range(start, n, step)]
    if order.startswith('rev'):
        out = []
        lo, hi = 0, n - 1
        while lo <= hi:
            out.append(lo)
            if hi != lo:
                out.append(hi)
            lo, hi = lo + 1, hi - 1
        return out
    raise Missing(f'slice order {order}')


@rule
def slice_timing(ctx: Context):
    if ctx.out.get('MRAcquisitionType') == '3D':
        return
    if V.integer(ctx.opt('Packages') or ctx.opt('Minimum number of packages')
                 or '1') != 1:
        return
    if 'MultibandAccelerationFactor' in ctx:
        return
    spacing = (ctx.opt('Temporal slice spacing') or '').lower()
    if spacing != 'equidistant':
        return
    n = V.integer(ctx.get('slices', group='Stacks'))
    order = philips_slice_order(ctx.get('Slice scan order'), n)
    dt = ctx['RepetitionTime'] / n
    timing = [0.0] * n
    for rank, s in enumerate(order):
        timing[s] = round(rank * dt, 6)
    ctx.set('SliceTiming', timing)


def philips_to_bids(prot: Protocol, nii: dict | None = None,
                    extra: bool = True, strict: bool = False,
                    explain: bool = False) -> dict:
    ctx = Context(prot, nii)
    for func in RULES:
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
