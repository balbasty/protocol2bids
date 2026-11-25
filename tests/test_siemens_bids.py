"""Siemens -> BIDS: formulas checked by hand against the printouts."""
import numpy as np
import pytest

from protocol2bids import protocol_to_bids, read_protocols
from protocol2bids.model import Entry, Protocol
from protocol2bids.utils.nii2axes import nii2axes

from conftest import pdf


def _bids(path, index=0, nii=None, **kw):
    prot = read_protocols(pdf(path))[index]
    return protocol_to_bids(prot, pdf(nii) if nii else None, strict=True,
                            **kw)


def test_nii2axes_polarity():
    # LAS affine: i -> L, j -> A, k -> S
    aff = np.diag([-2.0, 2.0, 2.0, 1.0])
    vox2anat, anat2vox, _ = nii2axes(affine=aff, shape=(2, 3, 4))
    assert vox2anat == ['RL', 'PA', 'IS']
    assert anat2vox['AP'] == 'j-' and anat2vox['PA'] == 'j'
    assert anat2vox['RL'] == 'i' and anat2vox['IS'] == 'k'


def test_epi_bold_vb17():
    b = _bids('datasets/pdf/CoRR/BNU_1/rest.pdf',
              nii='datasets/nii/CoRR/BNU_1/rest.nii')
    assert b['Manufacturer'] == 'Siemens'
    assert b['MagneticFieldStrength'] == 3.0
    assert b['SequenceName'] == 'ep2d_bold'
    assert b['PulseSequenceType'] == 'Gradient Echo EPI'
    assert b['ScanningSequence'] == ['EP']
    assert b['SequenceVariant'] == ['SK']
    assert b['ScanOptions'] == ['FS']
    assert b['MRAcquisitionType'] == '2D'
    assert b['DwellTime'] == pytest.approx(3.1e-6, abs=1e-9)
    assert b['RepetitionTime'] == pytest.approx(2.0)
    assert b['EchoTime'] == pytest.approx(0.030)
    assert b['FlipAngle'] == 90
    # "A >> P" with a LAS nifti -> j-
    assert b['PhaseEncodingDirection'] == 'j-'
    assert b['SliceEncodingDirection'] == 'k'
    # 64x64, no PAT, no oversampling: ES = 0.46 ms
    assert b['EffectiveEchoSpacing'] == pytest.approx(0.46e-3)
    assert b['TotalReadoutTime'] == pytest.approx(0.46e-3 * 63)
    assert b['EchoTrainLength'] == 64
    assert b['AcquisitionMatrixPE'] == 64
    assert b['SliceThickness'] == 3.5
    assert b['SpacingBetweenSlices'] == pytest.approx(4.2)   # 20 % gap
    # 33 slices, interleaved (odd: 0, 2, 4, ... then 1, 3, ...)
    st = b['SliceTiming']
    assert len(st) == 33
    assert st[0] == 0 and st[2] == pytest.approx(2 / 33, abs=1e-5)
    assert st[1] == pytest.approx(17 * 2 / 33, abs=1e-5)
    assert max(st) < 2.0


def test_mprage_vb17():
    b = _bids('datasets/pdf/CoRR/BNU_1/anat.pdf',
              nii='datasets/nii/CoRR/BNU_1/anat.nii')
    assert b['PulseSequenceType'] == 'MPRAGE'
    assert b['ScanningSequence'] == ['GR', 'IR']
    assert 'MP' in b['SequenceVariant'] and 'SP' in b['SequenceVariant']
    assert b['MRAcquisitionType'] == '3D'
    assert b['InversionTime'] == pytest.approx(1.1)
    assert b['RepetitionTime'] == pytest.approx(2.53)
    assert b['RepetitionTimePreparation'] == pytest.approx(2.53)
    assert b['RepetitionTimeExcitation'] == pytest.approx(7.8e-3)
    # 3D: like dcm2niix, no SpacingBetweenSlices and no PE polarity
    assert 'SpacingBetweenSlices' not in b
    assert 'PhaseEncodingDirection' not in b
    assert b['PhaseEncodingAxis'] == 'j'
    assert 'SliceTiming' not in b
    assert b['SequenceVariant'] == ['SK', 'SP', 'MP']
    # DwellTime includes the 2x readout oversampling (RealDwellTime)
    assert b['DwellTime'] == pytest.approx(1 / (190 * 256 * 2), abs=1e-9)


def test_grappa_vd13():
    b = _bids('datasets/pdf/ABIDE2/ONRC_2/T1w.pdf')
    assert b['ParallelAcquisitionTechnique'] == 'GRAPPA'
    assert b['ParallelReductionFactorInPlane'] == 3
    # base 320, phase res 100 %, FoV phase 68.8 % -> 220
    assert b['AcquisitionMatrixPE'] == 220
    assert b['MagneticFieldStrength'] == 3.0


def test_multiband():
    b = _bids('examples/pdf/siemens/Siemens_VB17_HCP-diff_gre_mbep2d-bold_'
              'mbep2d-se_mbep2d-diff_gre-fmap.pdf', index=3)
    assert b['MultibandAccelerationFactor'] == 5
    assert b['PulseSequenceType'].startswith('Multiband')
    assert b['MagneticFieldStrength'] == 7.0
    assert b['RepetitionTime'] == pytest.approx(1.0)
    st = b['SliceTiming']
    # slices excited together share the same time
    n = len(st)
    assert n % 5 == 0
    assert st[0] == st[n // 5]


def test_fieldmap_two_echoes():
    b = _bids('datasets/pdf/CoRR/Utah_1/fieldmap.pdf')
    assert b['EchoTime1'] == pytest.approx(0.010)
    assert b['EchoTime2'] == pytest.approx(0.01246)


def test_xa_sequence_name_from_card():
    b = _bids('examples/pdf/siemens/Siemens_XA20_ADNI_fl_spcir_fl-r_epse_'
              'tgse_fm-r_epfid_tse.pdf', index=1)
    assert b['SequenceName'] == 'tfl'
    assert b['InversionTime'] == pytest.approx(0.9)
    assert b['ParallelReductionFactorInPlane'] == 2


def test_epi_with_acceleration_and_oversampling():
    p = Protocol(vendor='Siemens', header={'SequenceName': 'ep2d_bold',
                                           'SequenceFolder': 'SIEMENS'})
    p.entries = [
        Entry('Slices', '10', 'Routine', None, ('Slice group 1',)),
        Entry('Orientation', 'Transversal', 'Routine', None,
              ('Slice group 1',)),
        Entry('Phase enc. dir.', 'A >> P', 'Routine', None,
              ('Slice group 1',)),
        Entry('Phase oversampling', '20 %', 'Routine'),
        Entry('FoV read', '200 mm', 'Routine'),
        Entry('FoV phase', '100 %', 'Routine'),
        Entry('Slice thickness', '3 mm', 'Routine'),
        Entry('TR', '1000 ms', 'Routine'),
        Entry('TE', '30 ms', 'Routine'),
        Entry('Base resolution', '100', 'Resolution'),
        Entry('Phase resolution', '100 %', 'Resolution'),
        Entry('Phase partial Fourier', '6/8', 'Resolution'),
        Entry('PAT mode', 'GRAPPA', 'Resolution'),
        Entry('Accel. factor PE', '2', 'Resolution'),
        Entry('Echo spacing', '0.5 ms', 'Sequence'),
        Entry('Bandwidth', '2000 Hz/Px', 'Sequence'),
        Entry('Series', 'Ascending', 'Geometry'),
    ]
    b = protocol_to_bids(p, strict=True)
    eff = 0.5e-3 * 1.2 / 2
    assert b['EffectiveEchoSpacing'] == pytest.approx(eff)
    assert b['TotalReadoutTime'] == pytest.approx(eff * 99)
    assert b['BandwidthPerPixelPhaseEncode'] == pytest.approx(1 / (eff * 100))
    assert b['PhaseEncodingSteps'] == 90          # 100 * 1.2 * 6/8
    assert b['EchoTrainLength'] == 45             # 90 / 2
    assert b['PartialFourier'] == 0.75
    assert b['PartialFourierDirection'] == 'PHASE'
    assert 'PFP' in b['ScanOptions'] and 'OSP' in b['SequenceVariant']
    assert b['SliceTiming'] == pytest.approx([i * 0.1 for i in range(10)])


def test_cmrr_order():
    from protocol2bids.vendors.siemens.bids import cmrr_interleaved
    # odd number of shots: same as single band (starts with slice 0)
    assert cmrr_interleaved(11) == [0, 2, 4, 6, 8, 10, 1, 3, 5, 7, 9]
    # even number of shots: CMRR always starts with slice 0
    assert cmrr_interleaved(4) == [0, 2, 1, 3]
    assert cmrr_interleaved(6) == [0, 2, 4, 1, 5, 3]
    # measured on dcm_qa fMRI_MB_int_26 (36 slices, MB2)
    assert cmrr_interleaved(18) == [0, 7, 14, 3, 10, 17, 6, 13, 2, 9, 16,
                                    5, 12, 1, 8, 15, 4, 11]


def test_sms_product_order():
    from protocol2bids.vendors.siemens.bids import sms_interleaved

    def one_based(order):
        return [g + 1 for g in order]
    # even number of excitations (measured, VE11 to XA60)
    assert one_based(sms_interleaved(64, 8)) == [2, 4, 8, 6, 3, 5, 1, 7]
    assert one_based(sms_interleaved(60, 6)) == [2, 4, 10, 6, 8,
                                                  3, 5, 1, 7, 9]
    assert one_based(sms_interleaved(64, 4)) == [
        2, 4, 6, 8, 16, 10, 12, 14, 3, 5, 7, 9, 1, 11, 13, 15]
    # odd nexc, even N: VE11 uses the parity of N (group 2 first) ...
    assert one_based(sms_interleaved(72, 8, 'syngo MR E11'))[:5] == \
        [2, 4, 6, 8, 1]
    assert one_based(sms_interleaved(6, 2, 'syngo MR XA10')) == [2, 1, 3]
    # ... XA30+ uses the parity of nexc (group 1 first)
    assert one_based(sms_interleaved(10, 2, 'syngo MR XA60')) == \
        [1, 3, 5, 2, 4]
    assert one_based(sms_interleaved(60, 4, 'Numaris/X VA31A')) [:3] == \
        [1, 3, 5]
    # odd N: both rules agree, version not needed
    assert one_based(sms_interleaved(51, 3))[:3] == [1, 3, 5]
    # even MB, odd nexc, unknown version: undecidable
    with pytest.raises(Exception):
        sms_interleaved(72, 8)
