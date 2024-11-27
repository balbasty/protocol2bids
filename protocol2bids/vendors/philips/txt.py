from pathlib import Path


def parse_philipps_txt(path: str | Path, field_strength: float) -> dict:
    """
    Parse a Philipps protocol in txt format
    """
    def count_indent(line):
        count = 0
        while line[count] == ' ':
            count += 1
        return count

    def collapse_spaces(key):
        return ' '.join(filter(bool, key.split(' ')))

    def convert(value):
        if ',' in value:
            return list(map(convert, map(str.strip, value.split(','))))
        # repeat
        if value.startswith('('):
            value = value[1:]
            n, value = value.split(')')
            n = int(n.strip())
            value = value.strip()
            return [convert(value)] * n
        # string
        if value.startswith('"'):
            value = value[1:]
            if value.endswith('"'):
                value = value[:-1]
            return value.strip()
        # number
        try:
            return int(value)
        except Exception:
            return float(value)

    # parse key/value pairs and store them in a dict
    prot = dict()
    last_key = None
    with Path(path).open('rt') as f:
        lines = iter(f)
        while True:
            try:
                line = next(lines)
            except StopIteration:
                break
            if not line.strip():
                continue
            line = line.rstrip()
            while not line.endswith(';'):
                line += next(lines).rstrip()
            line = line.rstrip(';').rstrip()
            *key, value = line.split('=')
            key = '='.join(key)
            key = key.rstrip()
            # Sometimes, there are "groups of keys" marked by the use
            # of indentation. If this is detected, we prepend part of
            # the previous key to the parsed key
            indent = count_indent(key)
            if indent and last_key is not None:
                prefix = last_key[:indent]
                i = indent
                while i < len(last_key) and prefix[-1] != ' ':
                    prefix += last_key[i]
                    i += 1
                if prefix[-1] != ' ':
                    prefix += ' '
                key = prefix + key[indent:]
            prot[key] = value.strip()
            last_key = key

    # simplify keys by ensuring that consecutive spaces are collapsed
    # we also convert numbers to float/int and remove quotes around strings
    prot = {
        collapse_spaces(key): convert(collapse_spaces(value))
        for key, value in prot.items()
    }

    # TODO: Converstion to BIDS
    if 'FLAIR' in prot.get('Fast 3D VIEW', ''):
        return _parse_philips_txt_flair(prot, field_strength)
    if prot.get('Diffusion mode', 'no') != 'no':
        return _parse_philips_txt_dwi(prot, field_strength)
    if prot.get('Fast Imaging mode', '') == 'EPI':
        return _parse_philips_txt_epi(prot, field_strength)
    if prot.get('Scan mode', '') == '3D':
        return _parse_philips_txt_3d(prot, field_strength)
    raise NotImplementedError


def _parse_philips_txt_common(prot: dict, field_strength: float) -> dict:
    sidecar = dict()
    sidecar['Manufacturer'] = 'Philips'
    sidecar['MagneticFieldStrength'] = field_strength
    # Matrix size
    sidecar['ReconMatrixPE'] = prot['Reconstruction matrix']
    sidecar['ReconMatrixFE'] = prot['Reconstruction matrix']
    sidecar['ReconMatrixSE'] = prot['Stacks slices']
    sidecar['AcquisitionMatrixSE'] = prot['Stacks slices']
    sidecar['AcquisitionMatrixFE'], sidecar['AcquisitionMatrixPE'] = (
        map(int, map(str.strip,
            prot['ACQ matrix M x P'].upper().split('X')
        ))
    )
    if 'Stacks slice gap' in prot:
        sidecar['SpacingBetweenSlices'] = prot['Stacks slice gap (mm)']
    # Spatial encoding
    SliceEncodingDirection = (
        'RL' if prot['Stacks slice orientation'] == 'sagittal' else
        'SI' if prot['Stacks slice orientation'] == 'transverse' else
        'AP'
    )
    FreqEncodingDirection = prot['Stacks fold-over direction']
    PhaseEncodingDirection = (
        'RL'
        if (FreqEncodingDirection == 'AP' and SliceEncodingDirection == 'SI')
        or (FreqEncodingDirection == 'SI' and SliceEncodingDirection == 'AP')
        else
        'AP'
        if (FreqEncodingDirection == 'RL' and SliceEncodingDirection == 'SI')
        or (FreqEncodingDirection == 'SI' and SliceEncodingDirection == 'RL')
        else
        'SI'
    )
    sidecar['FreqEncodingDirection'] = FreqEncodingDirection
    sidecar['SliceEncodingDirection'] = SliceEncodingDirection
    sidecar['PhaseEncodingDirection'] = PhaseEncodingDirection
    if prot.get('SENSE', 'no') == 'yes':
        sidecar['ParallelAcquisitionTechnique'] = 'SENSE'
        for key, value in prot.items():
            if key.startswith('SENSE P reduction'):
                sidecar['ParallelReductionFactorInPlane'] = value
            if key.startswith('SENSE S reduction'):
                sidecar['ParallelReductionFactorOutOfPlane'] = value
    # readout polarity may be obtained from "Stacks fat shift direction"
    # (it has value "F" in the 3D scans I have, and "P" in the EPIs, so
    # maybe it's just phase vs frequency, which would not help)

    # Sequence type
    if prot['Scan mode'] == '3D':
        sidecar['MRAcquisitionType'] = '3D'
    elif prot['Scan mode'] == 'MS':
        # Multi-slice EPI?
        sidecar['MRAcquisitionType'] = '2D'
    # Contrast
    if prot['Scan technique'] == 'FFE':
        sequence = 'Gradient Echo'
    elif prot['Scan technique'] == 'SE':
        sequence = 'Spin Echo'
    elif prot['Scan technique'] == 'IR':
        sequence = 'Inversion Recovery'
    # Fast mode
    if prot['Fast Imaging mode'] == 'TFE':
        sequence = 'Fast Spoiled ' + sequence
    elif prot['Fast Imaging mode'] == 'TSE':
        sequence = 'Fast ' + sequence
    elif prot['Fast Imaging mode'] == 'EPI':
        sequence += ' EPI'
    sidecar['PulseSequenceType'] = sequence
    # Parameters
    if 'Flip angle (deg)' in prot:
        sidecar['FlipAngle'] = prot['Flip angle (deg)']
    if 'TE (ms)' in prot:
        sidecar['EchoTime'] = prot['TE (ms)'] * 1e-3
    elif 'Act. TE (ms)' in prot:
        sidecar['EchoTime'] = float(prot['Act. TE (ms)']) * 1e-3
    elif 'Act. TR/TE (ms)' in prot:
        sidecar['EchoTime'] = float(
            prot['Act. TR/TE (ms)'].split('/')[-1]
        ) * 1e-3
    if prot.get('TFE prepulse', '') == 'invert' and 'TFE delay (ms)' in prot:
        sidecar['InversionTime'] = prot['TFE delay (ms)'] * 1e-3
    elif 'IR  delay (ms)' in prot:
        sidecar['InversionTime'] = prot['IR delay (ms)'] * 1e-3
    # Bandwidth
    if 'WFS (pix) / BW (Hz)' in prot:
        wfs_bw = prot['WFS (pix) / BW (Hz)']
        sidecar['PixelBandwidth'] = float(wfs_bw.split('/')[1])
    elif 'Act. WFS (pix) / BW (Hz)' in prot:
        wfs_bw = prot['Act. WFS (pix) / BW (Hz)']
        sidecar['PixelBandwidth'] = float(wfs_bw.split('/')[1])
    if 'PixelBandwidth' in sidecar:
        sidecar['DwellTime'] = (
            (sidecar['AcquisitionMatrixFE'] / sidecar['ReconMatrixFE'])
            / sidecar['PixelBandwidth']
        )
    # Water-fat shift
    if prot.get('Water-fat shift', 'no') == 'user defined':
        sidecar['WaterFatShift'] = prot['Water-fat (pixels)']
    elif 'WFS (pix) / BW (Hz)' in prot:
        wfs_bw = prot['WFS (pix) / BW (Hz)']
        sidecar['WaterFatShift'] = float(wfs_bw.split('/')[0])
    else:
        wfs_bw = prot['Act. WFS (pix) / BW (Hz)']
        sidecar['WaterFatShift'] = float(wfs_bw.split('/')[0])
    # FatSat
    sidecar['FatSaturation'] = prot.get('Fat suppression', 'no') != 'no'
    return sidecar


def _parse_philips_txt_3d(prot: dict, field_strength: float) -> dict:
    sidecar = _parse_philips_txt_common(prot, field_strength)
    # RepetitionTime
    if 'TR (ms)' in prot:
        sidecar['RepetitionTimePreparation'] = prot['TR (ms)'] * 1e-3
    elif 'Act. TR (ms)' in prot:
        sidecar['RepetitionTimePreparation'] = float(
            prot['Act. TE (ms)']
        ) * 1e-3
    elif 'Act. TR/TE (ms)' in prot:
        sidecar['RepetitionTimePreparation'] = float(
            prot['Act. TR/TE (ms)'].split('/')[0]
        ) * 1e-3
    return sidecar


def _parse_philips_txt_epi(prot: dict, field_strength: float) -> dict:
    sidecar = _parse_philips_txt_common(prot, field_strength)
    # RepetitionTime
    if 'TR (ms)' in prot:
        sidecar['RepetitionTimeExcitation'] = prot['TR (ms)'] * 1e-3
    elif 'Act. TR (ms)' in prot:
        sidecar['RepetitionTimeExcitation'] = float(
            prot['Act. TE (ms)']
        ) * 1e-3
    elif 'Act. TR/TE (ms)' in prot:
        sidecar['RepetitionTimeExcitation'] = float(
            prot['Act. TR/TE (ms)'].split('/')[0]
        ) * 1e-3
    # Bandwidth across PE
    sidecar['BandwidthPerPixelPhaseEncode'] = float(
        prot['BW in EPI freq. dir. (Hz)']
    )
    # Distortion correction
    EffectiveEchoSpacing, TotalReadoutTime = philips_echospacing(
        sidecar['WaterFatShift'],
        field_strength * 42.576,
        prot['EPI factor'],
        sidecar['ReconMatrixPE']
    )
    sidecar['EffectiveEchoSpacing'] = EffectiveEchoSpacing
    sidecar['TotalReadoutTime'] = TotalReadoutTime
    return sidecar


def _parse_philips_txt_dwi(prot: dict, field_strength: float) -> dict:
    sidecar = _parse_philips_txt_epi(prot, field_strength)
    deltas = prot['Diffusion gradient timing DELTA / delta (ms)']
    sidecar['DiffusionDelta'] = list(
        map(float, map(str.strip, deltas.split('/')))
    )
    return sidecar


def _parse_philips_txt_flair(prot: dict, field_strength: float) -> dict:
    sidecar = _parse_philips_txt_3d(prot, field_strength)
    sidecar['PulseSequenceType'] = 'FLAIR'
    return sidecar


def philips_echospacing(
        WaterFatShift, ImagingFrequency, EPI_Factor, ReconMatrixPE
):
    """
    https://osf.io/xvguw/wiki/home/
    WaterFatShift = 2001,1022
    ImagingFrequency = 0018,0084
    EPI_Factor = 0018,0091 or 2001,1013
    ReconMatrixPE = 0028,0010 or 0028,0011 depending on 0018,1312
    """
    ActualEchoSpacing = WaterFatShift / (
        ImagingFrequency * 3.4 * (EPI_Factor + 1)
    )
    TotalReadoutTime = ActualEchoSpacing * EPI_Factor
    EffectiveEchoSpacing = TotalReadoutTime / (ReconMatrixPE - 1)
    return EffectiveEchoSpacing, TotalReadoutTime
