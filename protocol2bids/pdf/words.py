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
            raw = pdfpage.get_text('rawdict', textpage=textpage)
            for block in raw['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        for word in _span_words(span):
                            if recoder:
                                word.text = recoder(word.text)
                            page.words.append(word)
            pages.append(page)
    return pages


_GARBLED = re.compile(r'[A-Za-z]{3,}')


def looks_garbled(pages: list[Page], min_words: int = 20) -> bool:
    """Heuristic: most words contain no ASCII letter run at all."""
    words = [w.text for p in pages for w in p.words]
    if len(words) < min_words:
        return False
    ascii_like = sum(bool(_GARBLED.search(w)) for w in words)
    return ascii_like < 0.2 * len(words)
