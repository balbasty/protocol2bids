"""Philips, GE and scan tables: hand-checked values."""
import pytest

from protocol2bids import protocol_to_bids, read_protocols
from protocol2bids.api import detect_format
from protocol2bids.vendors.philips.bids import philips_slice_order

from conftest import pdf


def _one(path, index=0):
    prots = read_protocols(pdf(path))
    return prots[index], protocol_to_bids(prots[index], strict=True)


@pytest.mark.parametrize('path,fmt', [
    ('datasets/pdf/ABIDE2/KKI_1/bold.pdf', 'philips'),
    ('datasets/pdf/ABIDE1/Leuven_1/rest.pdf', 'philips'),
    ('datasets/pdf/ABIDE1/SBL/rest.pdf', 'philips'),
    ('datasets/pdf/ABIDE2/IP_1/bold.pdf', 'philips'),
    ('datasets/pdf/ABIDE1/SDSU/rest.pdf', 'ge.sheet'),
    ('datasets/pdf/ABIDE1/UM_1/anat.pdf', 'ge.sheet'),
    ('datasets/pdf/ABIDE2/SU_2/T1w.pdf', 'ge.sheet'),
    ('datasets/pdf/CoRR/IACAS/rest.pdf', 'ge.lx'),
    ('datasets/pdf/ABIDE2/EMC_1/bold.pdf', 'ge.dicom'),
    ('examples/pdf/corr/BNU_1_scantable.pdf', 'table'),
    ('datasets/pdf/CoRR/BNU_1/rest.pdf', 'siemens'),
])
def test_detect(path, fmt):
    assert detect_format(pdf(path)) == fmt


def test_philips_examcard_epi():
    p, b = _one('datasets/pdf/ABIDE2/KKI_1/bold.pdf')
    assert p.get('slices', group='Stacks') == '47'
    assert b['RepetitionTime'] == pytest.approx(2.5)
    assert b['EchoTime'] == pytest.approx(0.030)
    assert b['FlipAngle'] == 75
    assert b['ParallelReductionFactorInPlane'] == 3
    assert b['MagneticFieldStrength'] == 3.0     # from WFS x BW
    assert b['PhaseEncodingAxis'] == 'j'
    assert 'PhaseEncodingDirection' not in b    # no polarity on Philips
    assert b['EchoTrainLength'] == 29
    # dcm2niix: ES = WFS / (f0 * 3.4 * (EPI factor + 1)); TRT = ES * EPIf
    es = 7.681 / (3.0 * 42.576 * 3.4 * 30)
    assert b['EstimatedTotalReadoutTime'] == pytest.approx(es * 29)
    assert b['EstimatedEffectiveEchoSpacing'] == pytest.approx(es * 29 / 95)
    # ascend, equidistant
    assert b['SliceTiming'][1] == pytest.approx(2.5 / 47, abs=1e-5)


def test_philips_text_export():
    p, b = _one('datasets/pdf/ABIDE1/Trinity/rest.pdf')
    assert p.get('slices', group='Stacks') == '38'
    assert p.get('AP (mm)', group='FOV') == '240'
    assert b['RepetitionTime'] == pytest.approx(2.0)


def test_philips_tfe_inversion():
    _, b = _one('datasets/pdf/ABIDE1/KKI/anat.pdf')
    assert b['ScanningSequence'] == ['GR', 'IR']
    assert b['InversionTime'] == pytest.approx(1.0)
    assert b['RepetitionTimePreparation'] == pytest.approx(3.5)
    assert b['MRAcquisitionType'] == '3D'


def test_philips_slice_orders():
    assert philips_slice_order('default', 5) == [0, 2, 4, 1, 3]
    assert philips_slice_order('default', 6) == [0, 2, 4, 1, 3, 5]
    assert philips_slice_order('interleaved', 9) == [0, 3, 6, 1, 4, 7,
                                                     2, 5, 8]
    assert philips_slice_order('descend', 3) == [2, 1, 0]


def test_ge_sheet():
    _, b = _one('datasets/pdf/ABIDE2/MIA_1/bold.pdf')
    assert b['RepetitionTime'] == pytest.approx(2.0)
    assert b['EchoTime'] == pytest.approx(0.030)
    assert b['ScanningSequence'] == ['EP', 'GR']
    assert b['PhaseEncodingAxis'] == 'j'        # axial, freq R/L
    # number of slices not printed: needs the nifti
    assert 'SliceTiming' not in b
    prot = read_protocols(pdf('datasets/pdf/ABIDE2/MIA_1/bold.pdf'))[0]
    b = protocol_to_bids(prot, {'affine': __import__('numpy').eye(4),
                                'shape': (64, 64, 5)}, strict=True)
    # interleaved: odd slices (1-based) first, for any number of slices
    assert b['SliceTiming'] == pytest.approx([0, 1.2, 0.4, 1.6, 0.8])


def test_ge_word_summary():
    prots = read_protocols(pdf('datasets/pdf/ABIDE1/UM_1/anat.pdf'))
    assert [p.name for p in prots] == ['3mm AX overlay', '3d spgr IR sag']
    assert prots[0].cards[0] == 'Patient Position'  # broken ligature fixed
    b = protocol_to_bids(prots[0], strict=True)
    # +/- 15.63 kHz over 256 samples
    assert b['PixelBandwidth'] == pytest.approx(2 * 15630 / 256, abs=1e-3)


def test_ge_lx():
    _, b = _one('datasets/pdf/CoRR/IACAS/rest.pdf')
    assert b['MagneticFieldStrength'] == 3.0
    assert b['RepetitionTime'] == pytest.approx(2.0)
    assert b['SpacingBetweenSlices'] == pytest.approx(4.6)


def test_ge_dicom_dump():
    _, b = _one('datasets/pdf/ABIDE2/EMC_1/bold.pdf')
    assert b['ManufacturersModelName'] == 'DISCOVERY MR750'
    assert b['PixelBandwidth'] == 7812.5
    # dcm2niix: lines = ceil(64/1/2)*2 = 64; EES = 63 * 520us / 63
    assert b['EffectiveEchoSpacing'] == pytest.approx(520e-6)
    assert b['TotalReadoutTime'] == pytest.approx(520e-6 * 63)


def test_scan_table():
    prots = read_protocols(pdf('examples/pdf/corr/BNU_1_scantable.pdf'))
    assert [p.name for p in prots] == ['BNU 1 Anatomical', 'BNU 1 Rest',
                                       'BNU 1 DTI']
    b = protocol_to_bids(prots[2], strict=True)
    assert b['ParallelAcquisitionTechnique'] == 'GRAPPA'
    assert b['ParallelReductionFactorInPlane'] == 2
    assert b['PartialFourier'] == 0.75


def test_ge_hyperband_order():
    from protocol2bids.vendors.ge.bids import ge_is_r03, ge_slice_ranks
    assert ge_is_r03('27\\LX\\MR Software release:RX27.0_R03') is True
    assert ge_is_r03('DV26.0_R02') is False
    assert ge_is_r03('') is None
    # RX28 (R03+), N=32, HB4: nexc 8 -> 1,3,5,7,2,4,8,6 (ds003858)
    ranks, nslots = ge_slice_ranks(32, 4, r03=True)
    assert nslots == 8
    assert sorted(range(8), key=lambda g: ranks[g]) == \
        [0, 2, 4, 6, 1, 3, 7, 5]
    # before 27.0 R03: even nexc gets a dummy slot (60 slices HB6 -> 11)
    _, nslots = ge_slice_ranks(60, 6, r03=False)
    assert nslots == 11


def test_ge_dcm2niix_rule():
    from protocol2bids.vendors.ge.bids import (
        ge_is_r03, ge_slice_timing, ge_version)
    # version strings (dcm2niix readSoftwareVersionsGE examples)
    assert ge_version('27\\LX\\MR Software release:RX27.0_R02_1831.a') == \
        (27.0, 27, 2)
    assert ge_version('28\\LX\\MR29.1_EA_2039.g') == (29.1, 29, 0)
    assert ge_version('30\\LX\\SIGNA_LX1.MR30.0_R01_2236.d') == \
        (30.0, 30, 1)
    assert ge_is_r03('28\\LX\\MR29.1_EA_2039.g') is True     # >= 27.1
    # sequential vs interleaved
    assert ge_slice_timing(4, 2.0, interleaved=False) == [0, 0.5, 1.0, 1.5]
    assert ge_slice_timing(4, 2.0) == [0, 1.0, 0.5, 1.5]
    # epiRT (FMRI): times spread over TR - group delay
    assert ge_slice_timing(4, 2.0, kind='fmri', group_delay=0.4) == \
        pytest.approx([0, 0.8, 0.4, 1.2])
    # HyperBand: needs the version, unsupported before 26.0
    assert ge_slice_timing(8, 2.0, mb=2) is None
    assert ge_slice_timing(8, 2.0, mb=2, version='DV25.0_R02') is None
    # diffusion: cycling off (non-cycling systems) -> pre-R03 dummy slot
    t = ge_slice_timing(8, 2.0, mb=2, version='RX28.0_R04', kind='diff',
                        model='DISCOVERY MR750')
    # (dcm2niix maps slices modulo the enlarged number of slots)
    assert len(set(t)) == 5 and max(t) == pytest.approx(2.0 * 4 / 5)
    # diffusion on cycling systems: mode unknown -> None
    assert ge_slice_timing(8, 2.0, mb=2, version='RX28.0_R04', kind='diff',
                           model='SIGNA Premier') is None
    # unsupported sequences
    assert ge_slice_timing(8, 2.0, kind='other') is None


def test_ge_lx_slice_timing():
    # LX script: SLICEORDER "1" (interleaved), IOPT "EPI, FMRI", 32 slices
    _, b = _one('datasets/pdf/CoRR/IACAS/rest.pdf')
    st = b['SliceTiming']
    assert len(st) == 32
    assert st[0] == 0 and st[2] == pytest.approx(2.0 / 32)
    assert st[1] == pytest.approx(16 * 2.0 / 32)


def test_philips_text_export_file():
    # ExamCard "Key = value;" text export (.txt), MPRAGE-like TFE
    p, b = _one('datasets/pdf/ABIDE2/BNI_1/T1w.txt')
    assert detect_format(pdf('datasets/pdf/ABIDE2/BNI_1/T1w.txt')) == \
        'philips'
    assert b['MRAcquisitionType'] == '3D'
    assert b['InversionTime'] == pytest.approx(0.9)
    # RepetitionTime = inversion TR (shot interval), not the excitation TR
    assert b['RepetitionTime'] == pytest.approx(2.5)
    assert b['RepetitionTimePreparation'] == pytest.approx(2.5)
    assert b['RepetitionTimeExcitation'] == pytest.approx(0.0067)
    # 3D SENSE: P = in-plane, S = through-plane
    assert b['ParallelReductionFactorInPlane'] == 1
    assert b['ParallelReductionFactorOutOfPlane'] == pytest.approx(1.8)


def test_philips_dwi_separate_tr_te():
    _, b = _one('datasets/pdf/ABIDE2/BNI_1/dwi.txt')
    assert b['RepetitionTime'] == pytest.approx(7.85)
    assert b['EchoTime'] == pytest.approx(0.101)
    assert b['MagneticFieldStrength'] == 3.0


def test_philips_shortest_ti_delay():
    _, b = _one('datasets/pdf/ABIDE1/Trinity/anat.pdf')
    assert b['InversionTime'] == pytest.approx(1.06017468)


def test_ge_phase_acceleration_and_mprage_tr():
    _, b = _one('datasets/pdf/ABIDE1/SDSU/rest.pdf')
    assert b['ParallelReductionFactorInPlane'] == 2     # Phase Acc. Factor
    _, b = _one('datasets/pdf/ABIDE2/EMC_1/T1w.pdf')
    # IR-FSPGR: DICOM TR is the excitation TR
    assert 'RepetitionTime' not in b
    assert b['RepetitionTimeExcitation'] == pytest.approx(0.01026)
    assert 'IR' in b['ScanningSequence']


def test_scan_table_mprage():
    prots = read_protocols(pdf('datasets/pdf/ABIDE2/TCD_1/scantable.pdf'))
    b = protocol_to_bids(prots[0], strict=True)
    assert b['MRAcquisitionType'] == '3D'
    assert 'RepetitionTime' not in b          # 8.4 ms = excitation TR
    assert b['RepetitionTimeExcitation'] == pytest.approx(0.0084)


def test_fill_from(tmp_path):
    import json
    from protocol2bids.cli import protocol2bids
    out = tmp_path / 'T1w.json'
    protocol2bids(pdf('datasets/pdf/ABIDE2/SDSU_1/T1w.pdf'), out,
                  fill_from=pdf('datasets/pdf/ABIDE2/SDSU_1/scantable.pdf'),
                  fill_select='0')
    b = json.loads(out.read_text())
    # the sheet prints "TE: Min Full"; the scan table gives the value
    assert b['EchoTime'] == pytest.approx(0.003172)
    # values from the printout are not overridden
    assert b['InversionTime'] == pytest.approx(0.6)
