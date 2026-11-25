import pytest

from protocol2bids.model import Entry, Missing, Protocol


def make():
    p = Protocol(name='test')
    p.entries = [
        Entry('Slices', '33', 'Routine', None, ('Slice group 1',)),
        Entry('Dist. factor', '20 %', 'Routine', None, ('Slice group 1',)),
        Entry('Slices', '1', 'Routine', None, ('Slice group 2',)),
        Entry('FoV Read', '256 mm', 'Resolution', 'Common'),
        Entry('Acceleration Factor PE', '2', 'Resolution', 'Acceleration'),
        Entry('TR', '2000 ms', 'Routine'),
        Entry('TR', '2000 ms', 'Contrast', 'Common'),
        Entry('TE 1', '10 ms', 'Contrast'),
        Entry('TE 2', '12 ms', 'Contrast'),
    ]
    return p


def test_lookup():
    p = make()
    assert p.get('TR') == '2000 ms'
    assert p.get('Slices') == '33'
    assert p.get('Slices', group='Slice group 2') == '1'
    assert p.get('Distance factor') == '20 %'            # synonym
    assert p.get('fov read', card='Resolution') == '256 mm'  # case
    assert p.get('Accel. factor PE', card='Resolution') == '2'
    assert p.getall('TE *') == ['10 ms', '12 ms']
    with pytest.raises(Missing):
        p.get('TI')
    assert p.get('TI', default=None) is None


def test_tree():
    t = make().tree()
    assert t['Routine']['Slice group 1']['Slices'] == '33'
    assert t['Resolution - Common']['FoV Read'] == '256 mm'
