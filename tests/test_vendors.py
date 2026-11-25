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
