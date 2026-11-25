"""Layout engine tests on synthetic PDFs."""
import pymupdf

from protocol2bids.pdf.layout import find_columns, make_lines, make_rows
from protocol2bids.pdf.words import load_pages
from protocol2bids.vendors.siemens.printout import read_printout


def _write(path, pages):
    """pages: list of list of (x, y, text, fontsize)"""
    doc = pymupdf.open()
    for items in pages:
        page = doc.new_page(width=595, height=842)
        for x, y, text, size in items:
            page.insert_text((x, y), text, fontsize=size)
    doc.save(str(path))


def _table(x0, y0, rows, keyx=0, valx=120, dy=11, size=9):
    out = []
    for i, row in enumerate(rows):
        indent, key, value = row
        out.append((x0 + keyx + indent, y0 + i * dy, key, size))
        if value is not None:
            out.append((x0 + valx, y0 + i * dy, value, size))
    return out


def test_two_columns(tmp_path):
    left = [(0, 'Card A', None)] + [(10, f'Key {i}', f'Val {i}')
                                     for i in range(30)]
    right = [(0, 'Card B', None)] + [(10, f'Other {i}', f'{i} ms')
                                      for i in range(30)]
    path = tmp_path / 'two.pdf'
    _write(path, [_table(40, 100, left) + _table(310, 100, right)])
    pages = load_pages(path, ocr=False)
    lines = make_lines(pages[0])
    bounds = find_columns(lines, pages[0].width)
    assert len(bounds) == 1 and 200 < bounds[0] < 310
    rows = make_rows(pages)
    # reading order: whole left column first
    texts = [r.segments[0].text for r in rows]
    assert texts.index('Key 29') < texts.index('Card B')


def test_single_column_right_aligned(tmp_path):
    items = []
    for i in range(30):
        items.append((60, 100 + 12 * i, f'Parameter number {i}', 9))
        value = 'x' * (1 + i % 7)
        items.append((450 - 5 * len(value), 100 + 12 * i, value, 9))
    path = tmp_path / 'one.pdf'
    _write(path, [items])
    pages = load_pages(path, ocr=False)
    lines = make_lines(pages[0])
    assert find_columns(lines, pages[0].width) == []


def _siemens_page(path_text, rows_left, rows_right=()):
    items = [
        (180, 40, 'SIEMENS MAGNETOM TestScanner syngo MR B17', 12),
        (100, 70, path_text, 11),
        (80, 85, 'TA: 1:00   PAT: Off   Voxel size: 1.0×1.0×1.0 mm   '
                 'Rel. SNR: 1.00   SIEMENS: fl', 10),
    ]
    items += _table(36, 120, rows_left, valx=136)
    if rows_right:
        items += _table(310, 120, rows_right, valx=136)
    return items


def test_siemens_structure(tmp_path):
    left = [
        (0, 'Routine', None),
        (11, 'Slice group 1', None),
        (14, 'Slices', '33'),
        (14, 'Dist. factor', '20 %'),
        (11, 'TR', '2000 ms'),
        (11, 'TE', '30 ms'),
        (11, 'Start measurement without', 'On'),
        (11, 'further preparation', None),
        (11, 'Filter', 'Prescan Normalize,'),
        (11, '', None),
        (0, 'Contrast', None),
        (11, 'Flip angle', '90 deg'),
    ] + [(11, f'Pad {i}', 'Off') for i in range(10)]
    # value continuation line
    right = [
        (0, 'Sequence', None),
        (11, 'Bandwidth', '2520 Hz/Px'),
    ] + [(11, f'More {i}', 'On') for i in range(20)]
    items = _siemens_page('\\\\USER\\test\\my protocol', left, right)
    items.append((36 + 136, 120 + 9 * 11, 'Elliptical filter', 9))
    path = tmp_path / 'siemens.pdf'
    _write(path, [items])
    prots = read_printout(path, ocr=False)
    assert len(prots) == 1
    p = prots[0]
    assert p.name == 'my protocol'
    assert p.scanner['ManufacturersModelName'] == 'TestScanner'
    assert p.header['SequenceName'] == 'fl'
    assert p.get('Slices', group='Slice group') == '33'
    assert p.get('TR', card='Routine') == '2000 ms'
    assert p.get('Start measurement without further preparation') == 'On'
    assert p.get('Filter') == 'Prescan Normalize, Elliptical filter'
    assert p.get('Flip angle', card='Contrast') == '90 deg'
    assert p.get('Bandwidth', card='Sequence') == '2520 Hz/Px'


def test_siemens_multipage_multiprotocol(tmp_path):
    rows = [(0, 'Routine', None)] + [(11, f'Key {i}', f'{i}')
                                     for i in range(40)]
    pages = [
        _siemens_page('\\\\USER\\a\\first', rows),
        _siemens_page('\\\\USER\\a\\second', rows),
    ]
    path = tmp_path / 'multi.pdf'
    _write(path, pages)
    prots = read_printout(path, ocr=False)
    assert [p.name for p in prots] == ['first', 'second']
    assert all(len(p.entries) == 40 for p in prots)
