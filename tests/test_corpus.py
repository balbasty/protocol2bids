"""Every Siemens printout of the corpus parses and converts without error."""

import pytest

from protocol2bids import protocol_to_bids, read_protocols

from conftest import ROOT

SIEMENS = sorted(
    str(p.relative_to(ROOT))
    for p in (ROOT / 'examples' / 'pdf').rglob('*.pdf')
    if 'scantable' not in p.name and 'fcon_summary' not in p.name
    and 'ge_dicom' not in p.name
    and 'unknown' not in p.parts
) + sorted(
    str(p.relative_to(ROOT))
    for p in (ROOT / 'datasets' / 'pdf').rglob('*.pdf')
    if p.parent.name in {
        'BMB_1', 'BNU_1', 'BNU_2', 'BNU_3', 'IPCAS_5', 'NKI_TRT', 'NYU_2',
        'UM', 'Utah_1', 'Utah_2', 'XHCUMS', 'CMU_a', 'CMU_b', 'Caltech',
        'MaxMun_a', 'MaxMun_b', 'MaxMun_c', 'MaxMun_d', 'NYU', 'OHSU',
        'Olin', 'Pitt', 'UCLA_1', 'UCLA_2', 'USM', 'Yale', 'GU_1', 'IU_1',
        'NYU_1', 'OHSU_1', 'ONRC_2', 'UCD_1', 'UCLA_Long', 'UPSM_Long',
        'USM_1',
    } and 'scantable' not in p.name
)


@pytest.mark.parametrize('path', SIEMENS)
def test_parse_and_convert(path):
    prots = read_protocols(ROOT / path, ocr=False)
    assert prots, 'no protocol found'
    for prot in prots:
        assert prot.entries
        sidecar = protocol_to_bids(prot, strict=True)
        assert sidecar['Manufacturer'] == 'Siemens'
