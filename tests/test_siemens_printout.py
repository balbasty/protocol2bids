"""Siemens printouts: hand-checked values from the example corpus."""
import pytest

from protocol2bids import read_protocols

from conftest import pdf, requires_ocr


def test_vb17_single():
    prots = read_protocols(pdf('datasets/pdf/CoRR/BNU_1/rest.pdf'))
    assert len(prots) == 1
    p = prots[0]
    assert p.name == 'ge_func_31x31x35_200_RS'
    assert p.scanner == {'Manufacturer': 'Siemens',
                         'ManufacturersModelName': 'TrioTim',
                         'SoftwareVersions': 'syngo MR B17'}
    assert p.header['SequenceName'] == 'ep2d_bold'
    assert p.header['TA'] == '6:46'
    assert p.header['VoxelSize'] == [3.1, 3.1, 3.5]
    assert p.get('Slices', group='Slice group') == '33'
    assert p.get('TR', card='Routine') == '2000 ms'
    assert p.get('TE', card='Routine') == '30 ms'
    assert p.get('Bandwidth', card='Sequence') == '2520 Hz/Px'
    assert p.get('Echo spacing', card='Sequence') == '0.46 ms'
    assert p.get('EPI factor', card='Sequence') == '64'
    # wrapped key
    assert p.get('Start measurement without further preparation') == 'On'
    # right column continues the "System" card of the left column
    assert p.get('Coil Combine Mode', card='System') == 'Sum of Squares'
    # group in the right column
    assert p.get('F >> H', group='Adjust volume') == '138 mm'


def test_va_2004a():
    p, = read_protocols(pdf('datasets/pdf/ABIDE1/NYU/rest.pdf'))
    assert p.name == 'Rest_TR2_4mm'
    assert p.scanner['SoftwareVersions'] == 'syngo MR 2004A'
    assert p.header['SequenceFolder'] == 'USER'
    assert p.header['SequenceName'] == 'cbi_seg_epi_gre'
    assert p.get('Orientation', group='Slice group') == 'T > C-23.0'
    assert p.get('Bandwidth', card='Sequence') == '3906 [Hz/Px]'
    assert p.get('TR', card='Routine') == '2000 [ms]'
    assert p.get('Spoil Phase Step') == '123.0'


def test_vd13_retypeset():
    p, = read_protocols(pdf('datasets/pdf/ABIDE2/ONRC_2/T1w.pdf'))
    assert p.name == 'MPRAGE_3min'
    assert p.scanner['SoftwareVersions'] == 'syngo MR D13'
    assert p.header['SequenceName'] == 'tfl'
    assert p.get('TI', card='Contrast') == '794 ms'
    assert p.get('TR', card='Routine') == '2200.0 ms'
    assert p.get('Accel. factor PE', card='Resolution') == '3'
    assert p.get('Phase enc. dir.', card='Routine') == 'R >> L'


def test_vd13_toc_at_end():
    prots = read_protocols(
        pdf('examples/pdf/siemens/Siemens_VD13_tfi_tse_epse.pdf'))
    assert len(prots) == 7
    p = prots[-1]
    assert p.name == 'Dif_tra_2_5mm_b2000_bipolar_NOdfc_fPS'
    # last protocol is followed by the TOC on the same page
    assert p.get('Bandwidth', card='Sequence') == '1446 Hz/Px'
    assert p.get('Diffusion mode') == '3-Scan Trace'


def test_ve11_toc_at_start():
    prots = read_protocols(
        pdf('examples/pdf/siemens/Siemens_VE11_DSI_fl_tfl_epse.pdf'))
    assert len(prots) == 6
    assert prots[4].name == 'dMRI_dir258_1_HDFT_Siemens_noGR'  # wrapped
    p = prots[0]
    assert p.scanner['ManufacturersModelName'] == 'Prisma_fit'
    assert p.header['SequenceName'] == 'fl'
    assert p.header['PM'] == 'REF'
    # value spanning two lines
    assert p.get('Filter', card='Routine') == \
        'Prescan Normalize, Elliptical filter'
    assert p.get('Orientation', card='Routine', group='Slice group 3') == \
        'Coronal'
    assert p.get('Bandwidth', card='Sequence') == '320 Hz/Px'


def test_xa20():
    prots = read_protocols(pdf(
        'examples/pdf/siemens/'
        'Siemens_XA20_ADNI_fl_spcir_fl-r_epse_tgse_fm-r_epfid_tse.pdf'))
    assert len(prots) == 10
    p = prots[1]
    assert p.name == 'Accelerated Sagittal MPRAGE'
    assert p.scanner['SoftwareVersions'] == 'Numaris/X VA20A-04ML'
    assert p.get('Sequence Name', card='Sequence') == 'tfl'
    assert p.get('TI', card='Contrast') == '900 ms'
    # Title-case keys and renamed keys through synonyms
    assert p.get('Accel. factor PE', card='Resolution') == '2'
    assert p.get('Dist. factor', card='Routine') == '50 %'


def test_reprinted_with_annotations():
    prots = read_protocols(pdf('datasets/pdf/ABIDE1/CMU_a/rest.pdf'))
    # annotations ("Rest_a", "!") are dropped
    assert [p.name for p in prots] == ['ep2d_bold_PMU_resting'] * 2
    assert prots[1].get('Bandwidth', card='Sequence') == '1628 Hz/Px'


def test_multi_echo_fieldmap():
    p, = read_protocols(pdf('datasets/pdf/CoRR/Utah_1/fieldmap.pdf'))
    assert p.header['SequenceName'] == 'gre_field_mapping'
    assert p.get('TE 1') == '10.00 ms'
    assert p.get('TE 2') == '12.46 ms'


def test_multiband_7t():
    prots = read_protocols(pdf(
        'examples/pdf/siemens/'
        'Siemens_VB17_HCP-diff_gre_mbep2d-bold_mbep2d-se_mbep2d-diff_'
        'gre-fmap.pdf'))
    assert len(prots) == 15
    p = prots[3]
    assert p.name == 'BOLD_REST3_PA'
    assert p.get('Multi-band accel. factor') == '5'


def test_select_pages():
    prots = read_protocols(
        pdf('examples/pdf/corr/siemens/ipcas_wei_all.pdf'), pages=[4, 5])
    assert [p.name for p in prots] == ['t1_mprage_sag']


@requires_ocr
def test_garbled_title_ocr():
    prots = read_protocols(
        pdf('examples/pdf/siemens/Siemens_XA20_VidaXQ_epfid_tfl-r.pdf'))
    assert len(prots) == 2
    assert prots[0].header['VoxelSize'] == [3.0, 3.0, 3.0]
    assert prots[0].get('TR', card='Routine') == '2000.0 ms'


@requires_ocr
@pytest.mark.slow
def test_scanned_pdf_ocr():
    prots = read_protocols(
        pdf('examples/unparsable/siemens/Siemens_VB17_CBS_mp2rage.pdf'))
    assert len(prots) == 1
    assert prots[0].name == 'mp2rage_0.5iso'
    assert prots[0].get('Base resolution', card='Resolution') == '448'
