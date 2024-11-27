import pymupdf
import math


_dicom2bids = {
    'Manufacturer': '0008,0070',
    'ManufacturersModelName': '0008,1090',
    'DeviceSerialNumber': '0018,1000',
    'StationName': '0008,1010',
    'SoftwareVersions': '0018,1020',
    'MagneticFieldStrength': {'args': ['0018,0087'], 'formula': float},
    'ReceiveCoilName': '0018,1250',
    'MRTransmitCoilSequence': '0018,9049',
    'InstitutionName': '0008,0080',
    'InstitutionAddress': '0008,0081',
    'InstitutionalDepartmentName': '0008,1040',
    'ScanningSequence': '0018,0020',
    'SequenceVariant': '0018,0021',
    'ScanOptions': '0018,0022',
    'SequenceName': '0018,0024',
    'MRAcquisitionType': '0018,0023',
    'MTState': '0018,9020',
    'ParallelReductionFactorInPlane': {
        'args': ['0018,9069'], 'formula': float
    },
    'ParallelReductionFactorOutOfPlane': {
        'args': ['0018,9155'], 'formula': float
    },
    'ParallelAcquisitionTechnique': '0018,9078',
    'PartialFourier': '0018,9081',
    'PartialFourierDirection': '0018,9036',
    'RepetitionTimeExcitation': {
        'args': ['0018,0080'], 'formula': lambda x: float(x) * 1e-3
    },
    'EchoTime': {'args': ['0018,0081'], 'formula': lambda x: float(x) * 1e-3},
    'InversionTime': {
        'args': ['0018,0082'], 'formula': lambda x: float(x) * 1e-3
    },
    'DwellTime': {'args': ['0019,1018'], 'formula': lambda x: float(x) * 1e-3},
    'FlipAngle': {'args': ['0018,1314'], 'formula': float},
    'Modality': '0008,1060',
    'PatientPosition': '0020,0032',
    'ProcedureStepDescription': '0040,0254',
    'SeriesDescription': '0008,103e',
    'ProtocolName': '0018,1030',
    'ImageType': '0008,0008',
    'AcquisitionTime': '0008,0032',
    'AcquisitionNumber': {'args': ['0020,0012'], 'formula': int},
    'ImageComments': '0020,4000',
    'VariableFlipAngleFlag': {'args': ['0018,1315'], 'formula': bool},
    'ImageOrientationPatientDICOM': '0020,0037',
    'ImagingFrequency': ['0018,0084', '0018,9098'],
    'InPlanePhaseEncodingDirectionDICOM': '0018,1312',
    'NumberOfAverages': {'args': ['0018,0083'], 'formula': int},
    'PercentPhaseFOV': {'args': ['0018,0094'], 'formula': float},
    'PercentSampling': {'args': ['0018,0093'], 'formula': float},
    'FrequencyEncodingSteps': {'args': ['0018,9058'], 'formula': int},
    'PhaseEncodingSteps': [
        {'args': ['0018,0089'], 'formula': int},
        {'args': ['0018,9231'], 'formula': int},
    ],
    'PhaseEncodingStepsOutOfPlane': {'args': ['0018,9232'], 'formula': int},
    'PixelBandwidth': {'args': ['0018,0095'], 'formula': float},
    'AcquisitionMatrixFE': {
        'args': ['0018,1310'],
        'formula': lambda x: max(map(int, x.split('\\')[:2]))
    },
    'AcquisitionMatrixPE': {
        'args': ['0018,1310'],
        'formula': lambda x: max(map(int, x.split('\\')[2:]))
    },
    'ReconMatrixFE': {
        'args': [
            '0018,1310',  # AcquisitionMatrix
            '0028,0010',  # Rows
            '0028,0011',  # Columns
        ],
        'formula': lambda acq, row, col:
            int(col) if int(acq.split('\\')[0]) == 0 else int(row)
    },
    'ReconMatrixPE': {
        'args': [
            '0018,1310',  # AcquisitionMatrix
            '0028,0010',  # Rows
            '0028,0011',  # Columns
        ],
        'formula': lambda acq, row, col:
            int(row) if int(acq.split('\\')[0]) == 0 else int(col)
    },
}


def _ge_EffectiveEchoSpacing_TotalReadoutTime(
    EchoSpacing,
    ParallelReductionFactorInPlane,
    AcquisitionMatrixPE,
    PartialFourierRoundFactor,
    Rows,
    Columns,
):
    # https://github.com/rordenlab/dcm2niix/blob/master/GE/README.md#total-readout-time
    EchoSpacing = float(EchoSpacing)
    ParallelReductionFactorInPlane = 1/float(
        ParallelReductionFactorInPlane.split('\\')[0]
    )
    RowsIsPE = int(AcquisitionMatrixPE.split('\\')[0]) == 0
    AcquisitionMatrixPE = max(map(int, AcquisitionMatrixPE.split('\\')[2:]))
    PartialFourierRoundFactor = (
        4 if 'PFF' in PartialFourierRoundFactor else 2
    )
    ReconMatrixPE = int(Rows) if RowsIsPE else int(Columns)

    NotPhysicalNumberOfAcquiredPELinesGE = (
        math.ceil(
            (1/PartialFourierRoundFactor)
            * AcquisitionMatrixPE
            / ParallelReductionFactorInPlane
        ) * PartialFourierRoundFactor
    )
    NotPhysicalTotalReadOutTimeGE = (
        (NotPhysicalNumberOfAcquiredPELinesGE - 1) * EchoSpacing * 1E-6
    )
    EffectiveEchoSpacing = (
        NotPhysicalTotalReadOutTimeGE / (AcquisitionMatrixPE - 1)
    )
    TotalReadoutTime = EffectiveEchoSpacing * (ReconMatrixPE - 1)
    return EffectiveEchoSpacing, TotalReadoutTime


# GE-specific tricks
_dicom2bids.update({
    'ParallelReductionFactorInPlane': {
        'args': ['0043,1083'],
        'formula': lambda x: 1/float(x.split('\\')[0]),
    },
    'ParallelReductionFactorOutOfPlane': {
        'args': ['0043,1083'],
        'formula': lambda x: 1/float(x.split('\\')[1]),
    },
    'MultibandAccelerationFactor': {
        'args': ['0043,10b6'],
        'formula': lambda x: float(x.split('\\')[0]),
    },
    'PolarityPE': [
        {
            'args': ['0018,9034'],
            'formula': lambda x: {'LINEAR': +1, 'REVERSE_LINEAR': -1}[x],
        },
        {
            'args': ['0043,102a'],
            'formula': lambda x: {'LINEAR': +1, 'REVERSE_LINEAR': -1}[x],
        },
    ],
    'EffectiveEchoSpacing': {
        'args': [
            '0043,102c',  # GE's EffectiveEchoSpacing
            '0043,1083',  # GE's in-plane acceleration
            '0018,1310',  # AcquisitionMatrix
            '0018,0022',  # ScanOption -> PFF
            '0028,0010',  # Rows
            '0028,0011',  # Columns
        ],
        'formula': lambda *x: _ge_EffectiveEchoSpacing_TotalReadoutTime(*x)[0],
    },
    'TotalReadoutTime': {
        'args': [
            '0043,102c',  # GE's EffectiveEchoSpacing
            '0043,1083',  # GE's in-plane acceleration
            '0018,1310',  # Acquisition matrix
            '0018,0022',  # ScanOption -> PFF
            '0028,0010',  # Rows
            '0028,0011',  # Columns
        ],
        'formula': lambda *x: _ge_EffectiveEchoSpacing_TotalReadoutTime(*x)[1],
    },
})


def is_code(elem):
    if len(elem) != 9:
        return False
    if elem[4] != ',':
        return False
    try:
        int(elem[:4], 16)
        int(elem[5:], 16)
    except Exception:
        return False
    return True


def parse_ge_dicom(path):
    doc = pymupdf.open(str(path))

    # Parse content
    keys, codes, values = [], [], []
    buffer = []
    for i, page in enumerate(doc):
        text = page.get_text().split('\n')
        if i == 0:
            text = text[1:]
        for elem in text:
            if is_code(elem):
                codes += [elem]
                keys += [buffer.pop(-1)]
                if len(keys) > 1:
                    if buffer:
                        values += [buffer.pop(-1)]
                    else:
                        values += ['']
            else:
                buffer += [elem]

    # dcm_keys = {key: value for key, value in zip(keys, values)}
    dcm_codes = {code: value for code, value in zip(codes, values)}

    # Convert to BIDS
    sidecar = {}
    for key, code in _dicom2bids.items():
        if not isinstance(code, list):
            code = [code]
        codes = code
        for code in codes:
            try:
                if isinstance(code, dict):
                    args = []
                    for code1 in code['args']:
                        args.append(dcm_codes[code1])
                    sidecar[key] = code['formula'](*args)
                else:
                    sidecar[key] = dcm_codes[code]
            except Exception as e:
                print(key, type(e), e)
                continue

    return sidecar
