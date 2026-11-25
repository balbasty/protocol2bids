from pathlib import Path

from protocol2bids.cli import output_paths


def test_output_paths():
    assert output_paths('a/x.pdf', None, ['p']) == [Path('a/x.json')]
    assert output_paths('x.pdf', 'o/s.json', ['p']) == [Path('o/s.json')]
    assert output_paths('x.pdf', 'o', ['my prot']) == [Path('o/my_prot.json')]
    assert output_paths('x.pdf', 'o/s.json', ['loc', 'T1/w', 'loc']) == [
        Path('o/s_loc.json'), Path('o/s_T1_w.json'), Path('o/s_loc_2.json')]
    assert output_paths('x.pdf', 'o', ['a', 'b']) == [
        Path('o/a.json'), Path('o/b.json')]
