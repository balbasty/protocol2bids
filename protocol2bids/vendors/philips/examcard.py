"""
Parser for Philips ExamCard printouts.

Two layouts are found in the wild, both handled by the generic key/value
table parser:

* the "ExamCard" view, with 3-4 columns of sections (INFO PAGE, GEOMETRY,
  CONTRAST, MOTION, DYN/ANG, POSTPROC, OFFC/ANG...);
* the text export (`Key = "value";`), possibly rendered as a PDF.

In both cases, sub-parameters are indented below their parent
(``Stacks`` / ``slices``, ``FOV`` / ``AP (mm)``).
"""
from __future__ import annotations

import re
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Iterable

from ...model import Entry, Protocol
from ...pdf.kvtable import read_kv
from ...pdf.words import Page, load_pages

LOGGER = getLogger(__name__)

SECTIONS = (
    'INFO PAGE', 'GEOMETRY', 'CONTRAST', 'MOTION', 'DYN/ANG', 'POSTPROC',
    'OFFC/ANG', 'SAR', 'CONFLICTS', 'INITIAL', 'COIL', 'DIFFUSION',
)
RE_SECTION = re.compile(
    r'^(' + '|'.join(re.escape(s) for s in SECTIONS) + r')$', re.I)

# Typical Philips keys, used for sniffing
VOCABULARY = (
    'Act. TR/TE', 'Fold-over suppression', 'Coil selection', 'EPI factor',
    'WFS', 'Scan percentage', 'Halfscan', 'Fast Imaging mode', 'SENSE',
    'Slice scan order', 'fat shift direction', 'Recon voxel size',
)

RE_SCANNER = re.compile(
    r'PHILIPS\s+(?P<model>(?:[A-Za-z]+\s*){1,3}?)\s*(?P<field>\d(?:\.\d)?)\s*T\b',
    re.I,
)

# "FOV RL (mm)", "Stack Offc. AP (P=+mm)", "Ang. AP (deg)"...
RE_DIRKEY = re.compile(
    r'^(?P<parent>.+?)\s+(?P<key>(?:RL|AP|FH|LR|PA|HF|M|P|S)\s*\(.*)$')


def sniff(pages: list[Page]) -> bool:
    text = ' '.join(w.text for p in pages[:3] for w in p.words)
    if re.search(r'\bPhilips\b', text, re.I):
        return True
    hits = sum(v in text for v in VOCABULARY)
    return hits >= 4


def _split_dirkey(name: str) -> tuple[str, ...]:
    match = RE_DIRKEY.match(name)
    if match and not match.group('parent').endswith(('/', 'x')):
        return (match.group('parent'), match.group('key'))
    return (name,)


RE_SUBVALUES = re.compile(
    r'(?P<key>(?:RL|AP|FH|LR|PA|HF)\s*\([^)]*\))\s*(?P<value>-?[\d.]+)')


def _normalize(entries: list[Entry]) -> list[Entry]:
    """
    * Turn "FOV RL (mm)" into group "FOV" + key "RL (mm)" so that the first
      sub-key is a sibling of the following ones ("AP (mm)", "FH (mm)").
    * Explode "FOV = RL (mm) 230 AP (mm) 230" into sub-keys.
    * Fix doubled hyphens ("fold--over").
    """
    exploded = []
    for e in entries:
        e.key = re.sub(r'-{2,}', '-', e.key)
        if e.value and e.value != '---':
            e.value = re.sub(r'-{2,}', '-', e.value)
        subs = list(RE_SUBVALUES.finditer(e.value or ''))
        if subs and RE_SUBVALUES.sub('', e.value).strip() == '':
            for m in subs:
                exploded.append(Entry(m.group('key'), m.group('value'),
                                      e.card, e.subcard, e.group + (e.key,),
                                      e.page, e.bbox))
        else:
            exploded.append(e)
    entries = exploded
    for e in entries:
        group = []
        for g in e.group:
            group.extend(_split_dirkey(g))
        *parents, key = _split_dirkey(e.key)
        # do not split keys that have no siblings / children
        e.group = tuple(group + parents)
        e.key = key
    # Remove duplicated parents created by the splitting:
    # ("FOV", "FOV") -> ("FOV",)
    for e in entries:
        dedup = []
        for g in e.group:
            if not dedup or dedup[-1] != g:
                dedup.append(g)
        e.group = tuple(dedup)
    return entries


def _scanner(texts: Iterable[str]) -> dict:
    for text in texts:
        match = RE_SCANNER.search(text)
        if match:
            model = re.sub(r'\s+', ' ', match.group('model')).strip()
            return {
                'Manufacturer': 'Philips',
                'ManufacturersModelName': model.title(),
                'MagneticFieldStrength': float(match.group('field')),
            }
    return {'Manufacturer': 'Philips'}


def read_examcard(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    allpages = load_pages(path, ocr=ocr)
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    entries, full = read_kv(
        allpages,
        is_header=lambda t: bool(RE_SECTION.match(t.strip())),
        hierarchy=True,
        skip=lambda t: bool(re.fullmatch(r'\s*(Page\s*)?\d+(\s*of\s*\d+)?\s*',
                                         t)),
    )
    entries = _normalize(entries)
    # Title lines: full-width rows and the first rows of the first page
    first = [w.text for w in allpages[0].words[:40]] if allpages else []
    texts = full + [' '.join(first)]
    prot = Protocol(vendor='Philips', format='examcard')
    prot.scanner = _scanner(texts)
    # Entries that hold the scanner name (e.g. "PHILIPS Intera Achieva")
    prot.entries = [e for e in entries
                    if not RE_SCANNER.search(f'{e.key} {e.value or ""}')]
    name = None
    for text in full:
        m = re.search(r'([\w\-]+)\.txt\b', text)
        if m:
            name = m.group(1)
            break
    prot.name = name or Path(path).stem
    prot.pages = [p.index for p in allpages]
    return [prot] if prot.entries else []
