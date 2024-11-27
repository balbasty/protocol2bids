"""
Parse Summary sheets from some FCON1000 (One Thousand Functional Connectoms)
datasets (ABIDE2, CoRR, ...)
"""
import pymupdf
from typing import Mapping
from pathlib import Path
from nibabel import Nifti1Header, Nifti2Header


def _error(*a, **k):
    raise RuntimeError(*a, **k)


_fcon_mapper_common = {
    'Manufacturer': 'Manufacturer',
    'ManufacturerModelName': 'Model',
    'MagneticFieldStrength': {
        'args': ['Field Strength'],
        'formula': lambda x: float(x[:-1])
    },
    'PulseSequenceType': {
        'args': ['Sequence'],
        'formula': lambda x: x.upper().split()[-1],
    },
    'EchoTime': {
        'args': ['Echo Time (TE) [ms]'],
        'formula': lambda x: float(x) * 1e-3
    },
    'FlipAngle': {
        'args': ['Flip Angle [Deg]'],
        'formula': float
    },
    'ParallelReductionFactorInPlane': {
        'args': ['Parallel Acquisition'],
        'formula': lambda x:
            float(x.upper().split('X')[-1].split('/')[0].strip())
    },
    'ParallelReductionFactorOutOfPlane': {
        'args': ['Parallel Acquisition'],
        'formula': lambda x:
            float(x.upper().split('X')[-1].split('/')[1].strip())
    },
    'ParallelAcquisitionTechnique': {
        'args': ['Parallel Acquisition'],
        'formula': lambda x: x.upper().split('X')[0].strip()
    },
    'PartialFourier': {
        'args': ['Partial Fourier'],
        'formula': lambda x: float(x.split('/')[0]) / float(x.split('/')[1])
    },
    'PhaseEncodingDirection': {
        'args': ['Slice Phase Encoding Direction'],
        'formula': lambda x: x.split()[0][0] + x.split()[-1][0]
        # needs to be fixed based on nifti affine later
    },
    'SliceEncodingDirection': {
        'args': ['Slice Orientation'],
        'formula': lambda x: x[0],
        # needs to be fixed based on nifti affine later
    },
    'SliceThickness': {
        # Not a BIDS field, but ==> DICOM 0018,0050 SliceThickness
        'args': ['Slice Thickness [mm]'],
        'formula': float,
    },
    'SliceTiming': 'Slice Acquisition Order',
    # ^ needs to be fixed later
    'FatSaturation': {
        # Not a BIDS field, but ==> DICOM 0018,0022 == FS
        'args': ['Fat Suppression'],
        'formula': lambda x: (
            True if x.lower() == 'yes' else
            False if x.lower() in ('no', 'none') else
            _error(x, 'is not a boolean')
        )
    },
    'AcquisitionMatrixSE': {
        'args': ['Number of Slices'],
        'formula': int
    },
    'ReconMatrixSE': {
        'args': ['Number of Slices'],
        'formula': int
    }
}

_fcon_mapper_3d = {
    'RepetitionTimePreparation': {
        'args': ['Repetition Time (TR) [ms]'],
        'formula': lambda x: float(x) * 1e-3
    },
    'InversionTime': {
        'args': ['Inversion Time (TI) [ms]'],
        'formula': lambda x: float(x) * 1e-3
    },
    'PixelBandwidth': 'Bandwidth per Voxel (Readout) [Hz]',
    'DwellTime': {
        'args': [
            'Bandwidth per Voxel (Readout) [Hz]',
            'Acquisition Matrix',
        ],
        'formula': (
            lambda bw, mat:
                1 / (max(map(int, mat.upper().split('X'))) * float(bw))
        )
    },
    'MRAcquisitionType': {
        'args': ['Sequence'],
        'formula': lambda x: (
            x.upper().split()[0]
            if x.upper().split()[0] in ('2D', '3D')
            else '3D'
        )
    },
}

_fcon_mapper_epi = {
    'RepetitionTimeExcitation': {
        'args': ['Repetition Time (TR) [ms]'],
        'formula': lambda x: float(x) * 1e-3
    },
    'MRAcquisitionType': {
        'args': [],
        'formula': lambda x:
            x.upper().split()[0]
            if x.upper().split()[0] in ('2D', '3D')
            else '2D'
    },
    'BandwidthPerPixelPhaseEncode': 'Bandwidth per Voxel (Readout) [Hz]',
    'EffectiveEchoSpacing': {
        'args': [
            'Bandwidth per Voxel (Readout) [Hz]',
            'Acquisition Matrix',
        ],
        'formula': (
            lambda bw, mat:
                1 / (min(map(int, mat.upper().split('X'))) * float(bw))
        )
    },
}


def _parse_fcon_summary(input: dict, mapper: dict | None = None) -> dict:
    # Choose appropriate mapper(s)
    if mapper is None:
        output = _parse_fcon_summary(input, _fcon_mapper_common)
        if 'EPI' in output['PulseSequenceType']:
            output.update(_parse_fcon_summary(input, _fcon_mapper_epi))
        else:
            output.update(_parse_fcon_summary(input, _fcon_mapper_3d))
        return output
    # Common logic with provided mapper
    output = {}
    for key, keymap in mapper.items():
        try:
            if isinstance(keymap, str):
                value = input[keymap]
            else:
                args = [input[arg] for arg in keymap['args']]
                value = keymap['formula'](*args)
            if value not in ('-', '--'):
                output[key] = value
        except Exception as e:
            print(key, type(e), e)
            pass
    return output


def parse_fcon_summary(path: str | Path) -> Mapping[str, Mapping]:
    """
    Parse "scan_param" summary PDFs available in some fcon1000 datasets
    (ABIDE, CoRR)

    Parameters
    ----------
    path : str | Path
        Path to PDF file

    Returns
    -------
    sidecars : dict
        JSON sidecars, each column has its own key.
    """
    pdf = pymupdf.open(str(path))
    page = pdf[0]
    content = page.get_text()
    content = list(map(lambda x: x.strip(), content.split('\n')))

    # First non-header row starts with "Manufacturer", so that's how
    # we guess the number of columns
    ncol = content.index('Manufacturer')
    cols = content[1:ncol]
    # Read each column and build a key-value mapping from it
    keys = content[ncol::ncol]
    summaries = dict()
    for i, col in enumerate(cols):
        values = content[ncol+i+1::ncol]
        summaries[col] = {key: value for key, value in zip(keys, values)}

    # Convert each mapping
    sidecars = dict()
    for col, summary in summaries.items():
        sidecars[col] = _parse_fcon_summary(summary)

    return sidecars


def fix_fcon_sidecar(sidecar: dict, header: Nifti1Header | Nifti2Header):
    """
    Fix fcon1000 sidecar using information found in nifti header
    """
    pass
