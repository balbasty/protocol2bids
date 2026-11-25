"""
Generic parser for "key / value" tables (Philips ExamCards, GE scan
parameter sheets, text dumps rendered as PDF...).

It relies on the layout engine (`layout.make_rows`) for column detection
and reading order, and returns a flat list of `Entry` objects:

* a row made of a single segment that matches `is_header` opens a new
  card (section);
* in a row with several segments, the last segment is the value and the
  other ones are (nested) keys: ``FOV   RL (mm)   230`` -> key ``RL (mm)``
  in group ``FOV``;
* with `hierarchy=True`, a key that is more indented than the previous
  key becomes its child (``Coil selection`` / ``element selection``);
* a row made of a single segment located in the value zone continues the
  previous value; a key-only row starting with a lowercase letter
  continues the previous key.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable

from ..model import Entry
from .layout import Row, Segment, is_separator_text, make_rows
from .words import Page


def clean_key(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s*[=:]\s*$', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_value(text: str) -> str:
    text = text.strip()
    text = re.sub(r';\s*$', '', text).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    text = re.sub(r'^[=:]\s*', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _key_max(rows: list[Row]) -> dict[int, float]:
    """Per column: right-most x0 of key segments (98th percentile)."""
    out = {}
    for col in {r.column for r in rows if not r.full}:
        xs = sorted(r.segments[0].x0 for r in rows
                    if r.column == col and not r.full
                    and len(r.segments) >= 2)
        if xs:
            out[col] = xs[int(0.98 * (len(xs) - 1))]
    return out


def _value_min(rows: list[Row]) -> dict[int, float]:
    """Per column: typical left edge of the value zone (only meaningful
    for left-aligned values; returns the 10th percentile)."""
    out = {}
    for col in {r.column for r in rows if not r.full}:
        xs = sorted(r.segments[-1].x0 for r in rows
                    if r.column == col and not r.full
                    and len(r.segments) >= 2)
        if len(xs) >= 5:
            out[col] = xs[int(0.1 * (len(xs) - 1))]
    return out


def _resplit(row: Row, vx: float | None) -> Row:
    """Split a segment that straddles the start of the value zone
    (key and value too close to be separated by the gap rule)."""
    if vx is None or row.full:
        return row
    segs = []
    for seg in row.segments:
        words = seg.words
        cut = next((i for i, w in enumerate(words)
                    if i > 0 and abs(w.x0 - vx) < 2
                    and words[i - 1].x1 < vx), None)
        if cut is None:
            segs.append(seg)
        else:
            segs += [Segment(words[:cut]), Segment(words[cut:])]
    row.segments = segs
    return row


def read_kv(
    pages: Iterable[Page],
    is_header: Callable[[str], bool] = lambda text: False,
    hierarchy: bool = True,
    skip: Callable[[str], bool] | None = None,
    key_filter: Callable[[str], str] = lambda key: key,
    gap: float = 1.2,
) -> tuple[list[Entry], list[str]]:
    """
    Parse key/value tables.

    Parameters
    ----------
    pages : list[Page]
    is_header : callable(str) -> bool
        Whether a single-segment row is a section header.
    hierarchy : bool
        Use indentation to nest keys.
    skip : callable(str) -> bool
        Rows to drop (page numbers, titles...).
    key_filter : callable(str) -> str
        Applied to every key (e.g., to fix broken ligatures).
    gap : float
        Horizontal gap (in font size units) that separates segments.

    Returns
    -------
    entries : list[Entry]
    full : list[str]
        Text of full-width rows (titles...), in reading order.
    """
    rows = make_rows(
        pages,
        skip=(lambda ln: skip(ln.text)) if skip else None,
        gap=gap,
    )
    kmax = _key_max(rows)
    vmin = _value_min(rows)
    rows = [_resplit(r, vmin.get(r.column)) for r in rows]
    entries: list[Entry] = []
    full: list[str] = []
    card: str | None = None
    stack: list[tuple[float, str]] = []   # (x0, key) of open parents
    last: Entry | None = None
    last_x: float = 0.0
    last_col: int | None = None

    for row in rows:
        text = row.text.strip()
        if row.full:
            full.append(text)
            continue
        if not text or is_separator_text(text):
            continue
        if row.column != last_col:
            stack = []
            last_col = row.column
        segs = row.segments
        if len(segs) == 1 and is_header(text):
            card = key_filter(clean_key(text))
            stack, last = [], None
            continue
        x0 = segs[0].x0
        if len(segs) == 1 and x0 > kmax.get(row.column, x0) + 3:
            # value continuation
            if last is not None:
                value = clean_value(text)
                last.value = value if last.value is None else \
                    f'{last.value} {value}'
            continue
        if len(segs) == 1:
            keys, value = [segs[0]], None
        else:
            keys, value = list(segs[:-1]), clean_value(segs[-1].text)
        names = [key_filter(clean_key(k.text)) for k in keys]
        names = [n for n in names if n]
        if not names:
            continue
        # key continuation (wrapped key)
        if (
            value is None and last is not None and len(names) == 1 and (
                (names[0][:1].islower() and abs(x0 - last_x) < 3) or
                (names[0].startswith('(') and abs(x0 - last_x) < 15)
            )
        ):
            last.key = f'{last.key} {names[0]}'
            continue
        if not hierarchy:
            group: tuple[str, ...] = tuple(names[:-1])
        else:
            while stack and stack[-1][0] >= x0 - 1.5:
                stack.pop()
            parents = [name for _, name in stack]
            # extra leading key segments are parents of the last one
            for k, name in zip(keys[:-1], names[:-1]):
                stack.append((k.x0, name))
            group = tuple(parents + names[:-1])
        entry = Entry(names[-1], value, card, None, group, row.page,
                      (row.x0, row.y, row.x1, row.y))
        entries.append(entry)
        last, last_x = entry, keys[-1].x0
        if hierarchy:
            stack.append((keys[-1].x0, names[-1]))
    return entries, full


def fix_ti_ligature(text: str) -> str:
    """
    Some Word-generated PDFs map the "ti" ligature to a random glyph
    ("Pa[ent", "Pa3ent", "PaSent", "Res6ng" for "Patient", "Resting").
    """
    return re.sub(r'(?<=[a-z])([\[\]\d]|S)(?=[a-z])', 'ti', text)
