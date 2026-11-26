"""
Low-level text extraction: PDF -> words with geometry and font information.

Everything downstream (layout analysis, vendor parsers) only relies on the
`Word` and `Page` containers defined here, so that the PDF backend can be
swapped (pymupdf, pdfplumber, OCR) without touching the parsers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from logging import getLogger
from os import PathLike
from typing import Callable, Iterable

LOGGER = getLogger(__name__)

# Characters that are typographic variants of ASCII characters
_NORMALIZE = str.maketrans({
    ' ': ' ',   # no-break space
    ' ': ' ',   # thin space
    ' ': ' ',   # narrow no-break space
    '‐': '-',   # hyphen
    '‑': '-',   # non-breaking hyphen
    '‒': '-',   # figure dash
    '–': '-',   # en dash
    '−': '-',   # minus sign
    '­': '',    # soft hyphen
    'ﬁ': 'fi',  # ligature
    'ﬂ': 'fl',  # ligature
})


@dataclass
class Word:
    """A word (maximal run of non-blank characters) on a page."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float = 0.0
    bold: bool = False
    font: str = ''
    baseline: float = 0.0

    @property
    def xc(self) -> float:
        return 0.5 * (self.x0 + self.x1)

    @property
    def yc(self) -> float:
        return 0.5 * (self.y0 + self.y1)

    def __repr__(self) -> str:
        return f'Word({self.text!r}, x={self.x0:.1f}..{self.x1:.1f}, ' \
               f'y={self.baseline:.1f})'


@dataclass
class Page:
    """All words of a page, plus page geometry."""
    index: int
    width: float
    height: float
    words: list[Word] = field(default_factory=list)
    ocr: bool = False

    @property
    def text(self) -> str:
        return ' '.join(w.text for w in self.words)


def _is_bold(span: dict) -> bool:
    return bool(span.get('flags', 0) & 16) or 'bold' in span['font'].lower()


def _span_words(span: dict) -> Iterable[Word]:
    """Split a pymupdf "rawdict" span into words, using char geometry."""
    size = span['size']
    font = span['font']
    bold = _is_bold(span)
    baseline = span['origin'][1]
    current: list[dict] = []

    def flush():
        if not current:
            return None
        text = ''.join(c['c'] for c in current).translate(_NORMALIZE)
        text = text.strip()
        if not text:
            return None
        x0 = min(c['bbox'][0] for c in current)
        x1 = max(c['bbox'][2] for c in current)
        y0 = min(c['bbox'][1] for c in current)
        y1 = max(c['bbox'][3] for c in current)
        return Word(text, x0, y0, x1, y1, size, bold, font, baseline)

    prev = None
    for char in span['chars']:
        c = char['c']
        is_blank = (not c.strip()) or c in ' '
        # Also break words when there is a large gap between two glyphs
        # (some generators place each column with absolute positioning
        #  inside a single span).
        gap = (
            prev is not None and
            char['bbox'][0] - prev['bbox'][2] > 0.6 * size
        )
        if is_blank or gap:
            word = flush()
            if word:
                yield word
            current = []
        if not is_blank:
            current.append(char)
        prev = char
    word = flush()
    if word:
        yield word


def load_pages(
    path: str | PathLike,
    ocr: bool | str = 'auto',
    recoder: Callable[[str], str] | None = None,
) -> list[Page]:
    """
    Extract words from every page of a PDF.

    Parameters
    ----------
    path : path-like
        PDF file.
    ocr : {'auto', True, False}
        Use OCR on pages that contain no text ('auto'), on all pages (True)
        or never (False). OCR requires tesseract to be installed.
    recoder : callable, optional
        Function applied to the text of every word (used for PDFs whose
        fonts lack a proper unicode mapping).
    """
    import pymupdf

    if str(path).lower().endswith('.txt'):
        return load_text_pages(path)

    pages = []
    with pymupdf.open(str(path)) as doc:
        for index, pdfpage in enumerate(doc):
            rect = pdfpage.rect
            page = Page(index, rect.width, rect.height)
            textpage = None
            want_ocr = ocr is True
            if ocr == 'auto' and not pdfpage.get_text('text').strip():
                want_ocr = True
            if want_ocr:
                try:
                    textpage = pdfpage.get_textpage_ocr(full=True, dpi=300)
                    page.ocr = True
                except Exception as e:  # tesseract not available
                    LOGGER.warning(
                        f'Page {index} has no text layer and OCR is not '
                        f'available ({e}). Skipping it.'
                    )
                    pages.append(page)
                    continue
            if textpage is None:
                # Do not clip to the mediabox: some printouts contain
                # glyphs whose boxes are (partly) outside of it, and which
                # are rendered by most viewers.
                flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_MEDIABOX_CLIP
                textpage = pdfpage.get_textpage(flags=flags)
            raw = pdfpage.get_text('rawdict', textpage=textpage)
            for block in raw['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        for word in _span_words(span):
                            if recoder:
                                word.text = recoder(word.text)
                            page.words.append(word)
            page.words = _dedup(page.words)
            pages.append(page)
    return pages


def _dedup(words: list[Word]) -> list[Word]:
    """Remove words printed twice at the same position (fake bold)."""
    seen = set()
    out = []
    for w in words:
        key = (w.text, round(w.x0), round(w.baseline))
        near = {(w.text, round(w.x0) + dx, round(w.baseline) + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        if seen & near:
            continue
        seen.add(key)
        out.append(w)
    return out


_GARBLED = re.compile(r'[A-Za-z]{3,}')


def looks_garbled(pages: list[Page], min_words: int = 20) -> bool:
    """Heuristic: most words contain no ASCII letter run at all."""
    words = [w.text for p in pages for w in p.words]
    if len(words) < min_words:
        return False
    ascii_like = sum(bool(_GARBLED.search(w)) for w in words)
    return ascii_like < 0.2 * len(words)


def is_garbled_text(text: str) -> bool:
    """Text made of control / private-use characters (font without a
    unicode mapping)."""
    if not text:
        return False
    bad = sum(
        ord(c) < 32 or 0xE000 <= ord(c) <= 0xF8FF or c == '\ufffd'
        for c in text
    )
    return bad > 0.3 * len(text)


def ocr_garbled_lines(path: str | PathLike, pages: list[Page]) -> int:
    """
    Replace lines made of garbled words by their OCR transcription.

    Only the bounding box of each garbled line is rendered and OCRed, so
    that the rest of the page keeps its (exact) embedded text.

    Returns the number of lines that were OCRed.
    """
    import pymupdf

    todo = {
        page.index: [w for w in page.words if is_garbled_text(w.text)]
        for page in pages
    }
    if not any(todo.values()):
        return 0
    count = 0
    with pymupdf.open(str(path)) as doc:
        for page in pages:
            garbled = todo[page.index]
            if not garbled:
                continue
            # group garbled words by baseline
            groups: list[list[Word]] = []
            for w in sorted(garbled, key=lambda w: w.baseline):
                if groups and abs(groups[-1][0].baseline - w.baseline) < \
                        0.5 * max(w.size, 1):
                    groups[-1].append(w)
                else:
                    groups.append([w])
            pdfpage = doc[page.index]
            for group in groups:
                rect = pymupdf.Rect(
                    min(w.x0 for w in group) - 2,
                    min(w.y0 for w in group) - 1,
                    max(w.x1 for w in group) + 2,
                    max(w.y1 for w in group) + 1,
                )
                ids = {id(w) for w in group}
                if rect.width < 8 or rect.height < 4:
                    # too small to be OCRed (isolated glyph): drop it
                    page.words = [w for w in page.words if id(w) not in ids]
                    continue
                try:
                    pix = pdfpage.get_pixmap(dpi=400, clip=rect)
                    ocr = pymupdf.open('pdf', pix.pdfocr_tobytes())
                    text = ocr[0].get_text('text')
                except Exception as e:
                    LOGGER.warning(f'OCR unavailable ({e}).')
                    return count
                text = ' '.join(text.split()).translate(_NORMALIZE)
                page.words = [w for w in page.words if id(w) not in ids]
                if text:
                    ref = group[0]
                    page.words.append(Word(
                        text, rect.x0 + 2, rect.y0 + 1, rect.x1 - 2,
                        rect.y1 - 1, ref.size, ref.bold, ref.font,
                        ref.baseline,
                    ))
                count += 1
    return count


def load_text_pages(
    path: str | PathLike,
    char_width: float = 6.0,
    line_height: float = 12.0,
    tabsize: int = 8,
) -> list[Page]:
    """
    Load a plain-text export (e.g. Philips ExamCard "Key = value;" files)
    as a single page of positioned words: column -> x, line -> y. This
    lets the layout-based parsers handle text files like PDFs.
    """
    raw = open(path, 'rb').read().decode('utf-8', errors='replace')
    lines = raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    size = 10.0
    page = Page(0, 0.0, 0.0)
    width = 0
    for iline, line in enumerate(lines):
        line = line.expandtabs(tabsize).translate(_NORMALIZE)
        width = max(width, len(line))
        baseline = (iline + 1) * line_height
        for m in re.finditer(r'\S+', line):
            x0 = m.start() * char_width
            x1 = m.end() * char_width
            page.words.append(Word(m.group(), x0, baseline - size, x1,
                                   baseline, size, False, 'text', baseline))
    page.width = max(width * char_width, 1.0)
    page.height = (len(lines) + 1) * line_height
    return [page]
