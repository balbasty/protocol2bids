"""
Vendor-agnostic layout analysis.

    words -> lines -> segments -> (bands x columns) -> rows

* A *line* is a set of words sharing the same baseline.
* A *segment* is a run of words within a line separated by small gaps.
  Large horizontal gaps separate keys from values and page columns.
* A *band* is a horizontal slice of a page delimited by full-width lines
  (titles, banners). Within a band, text flows column by column.
* A *row* is the content of one line within one column: an optional key
  segment and an optional value segment, with the key indentation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median
from typing import Callable, Iterable

from .words import Page, Word


# ----------------------------------------------------------------------
#   Lines and segments
# ----------------------------------------------------------------------

@dataclass
class Segment:
    words: list[Word]

    @property
    def text(self) -> str:
        return ' '.join(w.text for w in self.words)

    @property
    def x0(self) -> float:
        return self.words[0].x0

    @property
    def x1(self) -> float:
        return self.words[-1].x1

    @property
    def size(self) -> float:
        return max(w.size for w in self.words)

    @property
    def bold(self) -> bool:
        return all(w.bold for w in self.words)

    def __repr__(self) -> str:
        return f'Segment({self.text!r}, x={self.x0:.1f}..{self.x1:.1f})'


@dataclass
class Line:
    page: int
    y: float
    segments: list[Segment]

    @property
    def text(self) -> str:
        return '  '.join(s.text for s in self.segments)

    @property
    def x0(self) -> float:
        return self.segments[0].x0

    @property
    def x1(self) -> float:
        return self.segments[-1].x1

    @property
    def words(self) -> list[Word]:
        return [w for s in self.segments for w in s.words]

    def __repr__(self) -> str:
        return f'Line(p{self.page}, y={self.y:.1f}, {self.text!r})'


def make_lines(page: Page, gap: float = 1.2) -> list[Line]:
    """
    Group words into lines and split lines into segments.

    Parameters
    ----------
    page : Page
    gap : float
        Horizontal gap (in units of font size) above which two consecutive
        words belong to different segments.
    """
    words = sorted(page.words, key=lambda w: (w.baseline, w.x0))
    rows: list[list[Word]] = []
    for word in words:
        tol = 0.35 * max(word.size, 1)
        if rows and abs(rows[-1][0].baseline - word.baseline) <= tol:
            rows[-1].append(word)
        else:
            rows.append([word])
    # A second pass is needed because sorting by baseline then x may
    # interleave lines whose baselines differ by less than the tolerance.
    lines = []
    for row in rows:
        row.sort(key=lambda w: w.x0)
        segments = [[row[0]]]
        for prev, word in zip(row[:-1], row[1:]):
            size = max(prev.size, word.size, 1)
            if word.x0 - prev.x1 > gap * size:
                segments.append([word])
            else:
                segments[-1].append(word)
        y = median(w.baseline for w in row)
        lines.append(Line(page.index, y, [Segment(s) for s in segments]))
    return lines


# ----------------------------------------------------------------------
#   Columns
# ----------------------------------------------------------------------

def _coverage_gutters(
    segments: list[Segment], xmin: float, xmax: float, minwidth: float,
    maxcount: int,
) -> list[tuple[float, float]]:
    """Find x-intervals in [xmin, xmax] covered by at most `maxcount`
    segments and wider than `minwidth`."""
    step = 1.0
    nbins = int((xmax - xmin) / step) + 1
    counts = [0] * nbins
    for seg in segments:
        i0 = max(0, int((seg.x0 - xmin) / step))
        i1 = min(nbins - 1, int((seg.x1 - xmin) / step))
        for i in range(i0, i1 + 1):
            counts[i] += 1
    gutters = []
    start = None
    for i, c in enumerate(counts + [maxcount + 1]):
        if c <= maxcount:
            if start is None:
                start = i
        elif start is not None:
            if (i - start) * step >= minwidth:
                gutters.append((xmin + start * step, xmin + i * step))
            start = None
    return gutters


def find_columns(
    lines: list[Line],
    width: float,
    exclude: Callable[[Line], bool] | None = None,
    max_columns: int = 4,
) -> list[float]:
    """
    Estimate column boundaries (x positions) from a set of lines that
    share the same page geometry.

    A candidate gutter is a vertical strip that (almost) no segment
    crosses. A gutter is accepted as a column separator if the content on
    its right side looks like an independent key/value table, i.e., a
    substantial fraction of lines have at least two segments on the right
    of the gutter (otherwise, it is just the gap between keys and values
    of a single-column table).

    Returns
    -------
    bounds : list[float]
        Sorted list of separator positions (empty if single column).
    """
    lines = [ln for ln in lines if not (exclude and exclude(ln))]
    segments = [s for ln in lines for s in ln.segments]
    if not segments:
        return []
    maxcount = max(1, len(lines) // 50)
    gutters = _coverage_gutters(
        segments, 0.15 * width, 0.85 * width, minwidth=4,
        maxcount=maxcount,
    )

    def is_separator(x: float, left: float, right: float) -> bool:
        nright = nleft = nmulti_right = nmulti_left = 0
        for ln in lines:
            segs = [s for s in ln.segments if left <= s.x0 < right]
            if not segs:
                continue
            r = [s for s in segs if s.x0 >= x]
            l_ = [s for s in segs if s.x0 < x]
            if r:
                nright += 1
                nmulti_right += len(r) >= 2
            if l_:
                nleft += 1
                nmulti_left += len(l_) >= 2
        if nright < 5 or nleft < 5:
            return False
        # both sides must contain their own key/value pairs
        return (nmulti_right >= 0.3 * nright and
                nmulti_left >= 0.3 * nleft)

    bounds: list[float] = []
    # Greedy: try gutters from widest to narrowest
    candidates = sorted(gutters, key=lambda g: g[0] - g[1])
    for g0, g1 in candidates:
        x = 0.5 * (g0 + g1)
        edges = [0.0] + sorted(bounds) + [width + 1]
        for left, right in zip(edges[:-1], edges[1:]):
            if left < x < right:
                break
        if is_separator(x, left, right):
            bounds.append(x)
        if len(bounds) + 1 >= max_columns:
            break
    return sorted(bounds)


# ----------------------------------------------------------------------
#   Rows
# ----------------------------------------------------------------------

@dataclass
class Row:
    """Content of one line within one column."""
    page: int
    column: int
    y: float
    segments: list[Segment]
    full: bool = False          # full-width line (title, banner...)
    meta: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return '  '.join(s.text for s in self.segments)

    @property
    def x0(self) -> float:
        return self.segments[0].x0

    @property
    def x1(self) -> float:
        return self.segments[-1].x1

    @property
    def size(self) -> float:
        return self.segments[0].size

    @property
    def bold(self) -> bool:
        return self.segments[0].bold

    def __repr__(self) -> str:
        flag = 'F' if self.full else f'c{self.column}'
        return f'Row(p{self.page} {flag} y={self.y:.1f} ' \
               f'x={self.x0:.1f}, {[s.text for s in self.segments]})'


def split_columns(line: Line, bounds: list[float]) -> list[list[Segment]]:
    cols: list[list[Segment]] = [[] for _ in range(len(bounds) + 1)]
    for seg in line.segments:
        icol = sum(seg.x0 >= b for b in bounds)
        cols[icol].append(seg)
    return cols


def _straddles(line: Line, bounds: list[float], margin: float = 5) -> bool:
    """True if a segment of the line crosses a column boundary."""
    return any(
        s.x0 < b - margin and s.x1 > b + margin and
        not is_separator_text(s.text)
        for s in line.segments for b in bounds
    )


def make_rows(
    pages: Iterable[Page],
    is_full: Callable[[Line], bool] | None = None,
    skip: Callable[[Line], bool] | None = None,
    bounds: list[float] | None = None,
    gap: float = 1.2,
) -> list[Row]:
    """
    Convert pages into a sequence of rows in reading order.

    Parameters
    ----------
    pages : list[Page]
    is_full : callable(Line) -> bool
        Identifies full-width lines (titles, banners). They are emitted
        as rows with `full=True` and split the page into bands, each band
        being read column by column.
    skip : callable(Line) -> bool
        Identifies lines to drop (page numbers, footers...).
    bounds : list[float], optional
        Column boundaries. Estimated from all pages if not provided.
    """
    pages = list(pages)
    lines_per_page = [make_lines(p, gap=gap) for p in pages]
    if skip:
        lines_per_page = [[ln for ln in lines if not skip(ln)]
                          for lines in lines_per_page]
    if bounds is None:
        width = max((p.width for p in pages), default=0)
        all_lines = [ln for lines in lines_per_page for ln in lines]
        bounds = find_columns(all_lines, width, exclude=is_full)

    rows: list[Row] = []
    for lines in lines_per_page:
        band: list[Line] = []

        def flush_band():
            percol: list[list[Row]] = [[] for _ in range(len(bounds) + 1)]
            for ln in band:
                for icol, segs in enumerate(split_columns(ln, bounds)):
                    if segs:
                        percol[icol].append(Row(ln.page, icol, ln.y, segs))
            for colrows in percol:
                rows.extend(colrows)
            band.clear()

        for ln in lines:
            if (is_full and is_full(ln)) or _straddles(ln, bounds):
                flush_band()
                rows.append(Row(ln.page, -1, ln.y, ln.segments, full=True))
            else:
                band.append(ln)
        flush_band()
    return rows


# ----------------------------------------------------------------------
#   Indentation levels
# ----------------------------------------------------------------------

def cluster_1d(values: Iterable[float], tol: float) -> list[float]:
    """Simple 1D clustering: sorted values separated by > tol start a new
    cluster. Returns cluster centers (medians)."""
    values = sorted(values)
    if not values:
        return []
    clusters = [[values[0]]]
    for v in values[1:]:
        if v - clusters[-1][-1] > tol:
            clusters.append([v])
        else:
            clusters[-1].append(v)
    return [median(c) for c in clusters]


def nearest(centers: list[float], x: float) -> int:
    return min(range(len(centers)), key=lambda i: abs(centers[i] - x))


_SEPARATOR = re.compile(r'^[-_=!~.\s]{6,}$')


def is_separator_text(text: str) -> bool:
    return bool(_SEPARATOR.match(text))
