"""
Parser for Siemens protocol printouts (syngo MR 2002B/2004A/A30 (VA),
B15/B17/B19 (VB), D11/D13 (VD), E11 (VE), Numaris/X (XA)).

All versions share the same logical structure:

    SIEMENS MAGNETOM <model> <software>          <- banner (every page)
    \\\\USER\\folder\\...\\protocol name            <- path (protocol start)
    TA: 6:46 PAT: Off Voxel size: ... SIEMENS: ep2d_bold   <- title
    Card                                         <- card header
      Key                     Value
      Group
        Key                   Value

but the layout differs (one or two columns, left- or right-aligned
values, indentation through leading spaces or through absolute
positioning, bold headers or not...). This parser relies on the generic
layout engine (`protocol2bids.pdf.layout`) and on document-wide
statistics (indentation levels per column) rather than on the order of
text objects in the PDF stream.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from logging import getLogger
from os import PathLike
from statistics import median
from typing import Iterable

from ...model import Entry, Protocol
from ...pdf.layout import (
    Line, Row, cluster_1d, is_separator_text, make_rows, nearest,
)
from ...pdf.words import Page, load_pages

LOGGER = getLogger(__name__)


# ----------------------------------------------------------------------
#   Regular expressions
# ----------------------------------------------------------------------

RE_BANNER = re.compile(
    r'^SIEMENS\s+MAGNETOM\s*(?P<model>.*?)\s*'
    r'(?P<version>(?:syngo\s*MR|Numaris/X)\s*\S+)?\s*$'
)
RE_PATH = re.compile(r'^\\\\')
RE_TITLE = re.compile(r'^\+?\s*(TA|Scan\s*Time)\s*:')
RE_PAGENUM = re.compile(
    r'^(-\s*\d+\s*-|\d+\s*/\s*[-+\d]+|Page\s*\d+\s*of\s*\d+|'
    r'\d{1,2}[/.]\d{1,2}[/.]\d{2,4}|\d+)$'
)
RE_TOC = re.compile(r'^Table\s+of\s+contents$', re.I)
KNOWN_CARDS = (
    'Properties', 'Routine', 'Contrast', 'Resolution', 'Geometry',
    'System', 'Physio', 'Diff', 'Diffusion', 'BOLD', 'Angio', 'Inline',
    'Sequence', 'Perfusion', 'ASL', 'Spectro', 'Spectroscopy', 'Dixon',
    'Cardiac', 'Neuro', 'MR Elastography', 'Elastography', 'Interactive',
    'Special', 'Post-Processing', 'Postproc', 'Tim CT', 'fMRI', 'MRS',
)
RE_CARD = re.compile(
    r'^(?P<card>' + '|'.join(map(re.escape, KNOWN_CARDS)) + r')'
    r'(\s*-\s*(?P<subcard>.+))?$'
)


def _is_garbled(text: str) -> bool:
    if not text:
        return False
    bad = sum(ord(c) < 32 or 0xE000 <= ord(c) <= 0xF8FF for c in text)
    return bad > 0.3 * len(text)


def _is_full(line: Line) -> bool:
    text = line.text
    return bool(
        RE_BANNER.match(text) or RE_PATH.match(text) or RE_TITLE.match(text)
    )


def _is_noise(line: Line) -> bool:
    text = line.text.strip()
    return bool(RE_PAGENUM.match(text))


# ----------------------------------------------------------------------
#   Title
# ----------------------------------------------------------------------

_TITLE_LABELS = re.compile(
    r'(?P<label>\+?\s*Scan\s*Time|TA|PAT|PM|Voxel\s*[Ss]ize|Rel\.\s*SNR|'
    r'Acc\.?:?|Coil\s*Selection)\s*:\s*'
)
_TITLE_SEQ = re.compile(
    r'(?:(?P<folder>SIEMENS|USER|CUSTOMER)\s*|(?<=\s)):\s*'
    r'(?P<seq>[^\s:]+)\s*$'
)


def parse_title(text: str) -> dict:
    """
    Parse the title line of a Siemens protocol, e.g.

    * ``TA: 6:46 PAT: Off Voxel size: 3.1×3.1×3.5 mm Rel. SNR: 1.00
      SIEMENS: ep2d_bold``
    * ``Scan Time: 6:00 Voxel size: 3.0×3.0×4.0 [mm] Rel. SNR: 1.00
      USER: cbi_seg_epi_gre``
    * ``TA: 0:12 PM: REF Voxel size: 0.5×0.5×7.0 mmPAT: Off
      Rel. SNR: 1.00 : fl``
    * ``TA: 35 sec Coil Selection: Auto Voxel Size: 1.5×1.5×8.0 mm³
      Acc:: None Rel. SNR: 1.00``
    """
    text = re.sub(r'\s+', ' ', text.replace('×', '×')).strip()
    # Some printouts glue "mm" to the next label ("mmPAT:")
    text = re.sub(r'(mm³?|\])(?=[A-Z])', r'\1 ', text)
    out: dict = {}
    match = _TITLE_SEQ.search(text)
    if match:
        out['SequenceFolder'] = match.group('folder')
        out['SequenceName'] = match.group('seq')
        text = text[:match.start()].strip()
    parts = []
    last = None
    pos = 0
    for match in _TITLE_LABELS.finditer(text):
        if last is not None:
            parts.append((last, text[pos:match.start()].strip()))
        last = re.sub(r'\s+', ' ', match.group('label').strip('+ '))
        pos = match.end()
    if last is not None:
        parts.append((last, text[pos:].strip()))
    for label, value in parts:
        value = value.strip(': ')
        lab = label.lower().rstrip(':.')
        if lab in ('ta', 'scan time'):
            out['TA'] = re.sub(r'\s*\[.*?\]', '', value)
        elif lab == 'pat':
            out['PAT'] = value
        elif lab == 'pm':
            out['PM'] = value
        elif lab.startswith('acc'):
            out['Acc'] = value
        elif lab == 'coil selection':
            out['CoilSelection'] = value
        elif lab.startswith('voxel'):
            m = re.match(
                r'([\d.]+)\s*[×x*!]\s*([\d.]+)\s*[×x*!]\s*([\d.]+)', value)
            if m:
                out['VoxelSize'] = [float(v) for v in m.groups()]
        elif lab.startswith('rel'):
            try:
                out['RelSNR'] = float(value.split()[0])
            except (ValueError, IndexError):
                pass
    return out


def parse_banner(text: str) -> dict:
    match = RE_BANNER.match(text.strip())
    if not match:
        return {}
    out = {'Manufacturer': 'Siemens'}
    model = match.group('model').strip()
    if model:
        out['ManufacturersModelName'] = model
    version = match.group('version')
    if version:
        out['SoftwareVersions'] = re.sub(r'\s+', ' ', version).strip()
    return out


# ----------------------------------------------------------------------
#   Document statistics
# ----------------------------------------------------------------------

@dataclass
class ColumnStats:
    levels: list[float]          # x positions of indentation levels
    key_max: float               # right-most x0 of key segments
    body_size: float             # most common font size


def _column_stats(rows: list[Row]) -> dict[int, ColumnStats]:
    stats = {}
    columns = sorted({r.column for r in rows if not r.full})
    for col in columns:
        crows = [r for r in rows if r.column == col and not r.full
                 and not is_separator_text(r.text)]
        # Rows with >= 2 segments: first segment is a key
        keyx = [r.segments[0].x0 for r in crows if len(r.segments) >= 2]
        if not keyx:
            keyx = [r.segments[0].x0 for r in crows]
        if not keyx:
            continue
        # robust upper bound on key positions
        keyx_sorted = sorted(keyx)
        key_max = keyx_sorted[int(0.98 * (len(keyx_sorted) - 1))]
        # Indentation levels: cluster x0 of all key-like segments
        keylike = [r.segments[0].x0 for r in crows
                   if r.segments[0].x0 <= key_max + 3]
        levels = cluster_1d(keylike, tol=1.5)
        # drop levels supported by very few rows (noise)
        counts = Counter(nearest(levels, x) for x in keylike)
        levels = [lv for i, lv in enumerate(levels) if counts[i] >= 2] \
            or levels
        sizes = Counter(round(r.size, 1) for r in crows)
        body = sizes.most_common(1)[0][0] if sizes else 0
        stats[col] = ColumnStats(levels, key_max, body)
    return stats


# ----------------------------------------------------------------------
#   Parser
# ----------------------------------------------------------------------

@dataclass
class _Item:
    """A classified row."""
    kind: str                    # banner|path|title|header|key|value|sep
    row: Row
    level: int = 0
    key: str | None = None
    value: str | None = None


def _classify(rows: list[Row], stats: dict[int, ColumnStats]) -> list[_Item]:
    items: list[_Item] = []
    for row in rows:
        text = row.text.strip()
        if row.full:
            if RE_BANNER.match(text):
                items.append(_Item('banner', row, value=text))
            elif RE_PATH.match(text):
                items.append(_Item('path', row, value=text))
            elif RE_TITLE.match(text):
                items.append(_Item('title', row, value=text))
            elif _is_garbled(text):
                items.append(_Item('garbled', row, value=text))
            else:
                # Full width line that is not a known element: can be a
                # wrapped path, or a long value. Decided later.
                items.append(_Item('full', row, value=text))
            continue
        if is_separator_text(text):
            items.append(_Item('sep', row))
            continue
        st = stats.get(row.column)
        if st is None:
            continue
        first = row.segments[0]
        rest = row.segments[1:]
        if first.x0 > st.key_max + 3:
            # value-only row (continuation of previous value)
            items.append(_Item('value', row, value=row.text))
            continue
        level = nearest(st.levels, first.x0)
        key = first.text
        value = ' '.join(s.text for s in rest) if rest else None
        is_header = False
        if value is None:
            if first.bold or first.size > st.body_size + 0.5:
                is_header = True
            elif level == 0 and len(st.levels) > 1 and \
                    st.levels[1] - st.levels[0] > 1.5:
                is_header = True
            elif RE_CARD.match(key) and level == 0:
                is_header = True
        if is_header:
            items.append(_Item('header', row, level, key=key))
        else:
            items.append(_Item('key', row, level, key=key, value=value))
    return items


def _next_key(items: list[_Item], i: int) -> _Item | None:
    for item in items[i + 1:]:
        if item.kind in ('sep', 'banner', 'garbled'):
            continue
        if item.kind == 'key':
            return item
        return None
    return None


def _build(items: list[_Item], scanner: dict) -> list[Protocol]:
    protocols: list[Protocol] = []
    prot: Protocol | None = None
    card: str | None = None
    subcard: str | None = None
    groups: list[tuple[int, str]] = []
    last: Entry | None = None
    last_level: int = 0
    expect: str | None = None      # 'path' continuation / 'title'
    page_has_content = False
    current_page = -1

    def new_protocol(path: str = '') -> Protocol:
        nonlocal card, subcard, groups, last
        p = Protocol(path=path, vendor='Siemens', format='printout')
        p.scanner = dict(scanner)
        protocols.append(p)
        card = subcard = last = None
        groups = []
        return p

    has_path = any(it.kind in ('path', 'title') for it in items)
    title_seen = False
    pending: str | None = None     # value printed just above its key

    for i, item in enumerate(items):
        if item.row.page != current_page:
            current_page = item.row.page
            page_has_content = False

        if item.kind == 'banner':
            info = parse_banner(item.value)
            for k, v in info.items():
                scanner.setdefault(k, v)
            if prot is not None:
                for k, v in info.items():
                    prot.scanner.setdefault(k, v)
            continue

        if item.kind == 'path':
            prot = new_protocol(item.value)
            expect, title_seen = 'head', False
            continue

        if item.kind == 'garbled':
            # Unreadable title/path (font without unicode mapping)
            if not page_has_content and expect is None:
                prot = new_protocol('')
                expect, title_seen = 'head', False
            continue

        if item.kind == 'title':
            if prot is None or expect != 'head':
                prot = new_protocol('')
                expect = 'head'
            title_seen = True
            # path fragments that ended up on the title line
            text = []
            for seg in item.row.segments:
                if '\\' in seg.text and ':' not in seg.text:
                    prot.path += ' ' + seg.text
                else:
                    text.append(seg.text)
            prot.header.update(parse_title(' '.join(text)))
            continue

        if expect == 'head' and item.kind not in ('header', 'sep'):
            # Everything between the path and the first card belongs to
            # the protocol header (wrapped path, wrapped title).
            if item.kind == 'full' or item.kind == 'title' or title_seen:
                if title_seen and item.kind in ('full', 'title'):
                    prot.header.update(parse_title(item.row.text))
                    continue
                if not title_seen:
                    prot.path += ' ' + item.row.segments[0].text
                    continue
            elif not title_seen:
                # (possibly corrupted) wrapped path
                prot.path += ' ' + item.row.segments[0].text
                continue

        if item.kind == 'full':
            if last is not None and last.value is not None:
                last.value += ' ' + item.value
            continue

        expect = None
        if prot is None:
            if has_path:
                # Annotations before the first protocol: ignore
                continue
            prot = new_protocol('')
        page_has_content = True
        if item.row.page not in prot.pages:
            prot.pages.append(item.row.page)

        if item.kind == 'sep':
            groups = []
            continue

        if item.kind == 'header':
            match = RE_CARD.match(item.key)
            if match:
                card = match.group('card')
                subcard = match.group('subcard')
            elif ' - ' in item.key:
                card, subcard = item.key.split(' - ', 1)
            else:
                card, subcard = item.key, None
            groups = []
            last = None
            continue

        if item.kind == 'value':
            # Some re-typeset printouts place the value of a wrapped key
            # slightly above the key's first line.
            nxt = items[i + 1] if i + 1 < len(items) else None
            if (
                nxt is not None and nxt.kind == 'key' and nxt.value is None
                and nxt.row.column == item.row.column
                and 0 < nxt.row.y - item.row.y < 0.9 * item.row.size
            ):
                pending = item.value
                continue
            if last is None:
                LOGGER.debug(f'Orphan value: {item.value!r}')
                continue
            if last.value is None:
                last.value = item.value
            else:
                last.value += ' ' + item.value
            continue

        # --- key ------------------------------------------------------
        level = item.level
        if pending is not None:
            item.value, pending = pending, None
        nxt = _next_key(items, i)
        opens_group = nxt is not None and nxt.level > level

        # Key continuation: lowercase word at the same level, no value
        if (
            item.value is None and last is not None and not opens_group
            and level == last_level and item.key[:1].islower()
        ):
            last.key += ' ' + item.key
            continue

        while groups and groups[-1][0] >= level:
            groups.pop()

        if opens_group:
            name = item.key
            if item.value is not None:
                if re.fullmatch(r'\d+', item.value.strip()):
                    name = f'{item.key} {item.value.strip()}'
                else:
                    entry = Entry(item.key, item.value, card, subcard,
                                  tuple(g for _, g in groups),
                                  item.row.page)
                    prot.entries.append(entry)
            groups.append((level, name))
            last = None
            last_level = level
            continue

        entry = Entry(
            item.key, item.value, card, subcard,
            tuple(g for _, g in groups), item.row.page,
            (item.row.x0, item.row.y, item.row.x1, item.row.y),
        )
        prot.entries.append(entry)
        last = entry
        last_level = level

    return [p for p in protocols if p.entries]


def _toc_pages(pages: list[Page]) -> set[int]:
    """Pages that belong to a table of contents."""
    toc = set()
    in_toc = False
    for page in pages:
        texts = [w.text for w in page.words]
        joined = ' '.join(texts)
        if re.search(r'Table\s+of\s+contents', joined, re.I):
            in_toc = True
        elif in_toc:
            # TOC ends when a protocol title is found
            if re.search(r'(^|\s)(TA|Scan\s*Time)\s*:', joined):
                in_toc = False
        if in_toc:
            toc.add(page.index)
    return toc


def read_printout(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    """
    Parse all protocols contained in a Siemens printout.

    Parameters
    ----------
    path : path-like
        PDF file
    pages : list[int], optional
        Only use these pages (0-indexed).
    ocr : {'auto', True, False}
        OCR policy for pages without text layer.

    Returns
    -------
    protocols : list[Protocol]
    """
    allpages = load_pages(path, ocr=ocr)
    for page in allpages:
        # Some re-printed PDFs contain spurious "!" glyphs in the margins
        page.words = [w for w in page.words if w.text.strip('!')]
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    toc = _toc_pages(allpages)
    usepages = [p for p in allpages if p.index not in toc]
    rows = make_rows(usepages, is_full=_is_full, skip=_is_noise)
    stats = _column_stats(rows)
    items = _classify(rows, stats)
    scanner: dict = {}
    protocols = _build(items, scanner)
    for prot in protocols:
        prot.name = prot.path.split('\\')[-1].strip() if prot.path else ''
    return protocols


def sniff(pages: list[Page]) -> bool:
    for page in pages[:3]:
        text = ' '.join(w.text for w in page.words[:200])
        if re.search(r'SIEMENS\s+MAGNETOM', text):
            return True
    return False
