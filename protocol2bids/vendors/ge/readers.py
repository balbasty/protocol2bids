"""
Readers for GE protocol documents:

* scan parameter sheets (printed from the console or retyped);
* LX protocol scripts (tcl: ``set TR "2000.0"``);
* DICOM header dumps (``RepetitionTime  0018,0080  2000``).
"""
from __future__ import annotations

import re
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Iterable

from ...model import Entry, Protocol
from ...pdf.kvtable import fix_ti_ligature, read_kv
from ...pdf.layout import make_lines
from ...pdf.words import Page, load_pages

LOGGER = getLogger(__name__)


# ----------------------------------------------------------------------
#   Sniffing
# ----------------------------------------------------------------------

RE_TAG = re.compile(r'^[0-9A-Fa-f]{4},[0-9A-Fa-f]{4}$')
SHEET_VOCABULARY = (
    'Pulse Seq', 'Freq DIR', 'Frequency DIR', 'Freq. Dir', 'NEX',
    'Phase FOV', 'Imaging Options', 'Imaging Op', 'Patient Entry',
    'Auto Shim', 'Autoshim', '# of Excitations', 'Locs per Slab',
)


def _text(pages: list[Page]) -> str:
    return ' '.join(w.text for p in pages for w in p.words)


def sniff_dicom(pages: list[Page]) -> bool:
    words = [w.text for p in pages[:3] for w in p.words]
    return sum(bool(RE_TAG.match(w)) for w in words) >= 20


def sniff_lx(pages: list[Page]) -> bool:
    return bool(re.search(r'\bset\s+PROTNAME\b', _text(pages[:2])))


def sniff_sheet(pages: list[Page]) -> bool:
    text = _text(pages[:3])
    if sum(v in text for v in SHEET_VOCABULARY) >= 3:
        return True
    # short, retyped sheets: "GE SIGNA 3T" + a few timing parameters
    return bool(re.search(r'\bGE\b|SIGNA', text)) and sum(
        bool(re.search(rf'\b{k}\b', text, re.I))
        for k in ('TR', 'TE', 'Flip', 'FOV|Field of View')) >= 3


# ----------------------------------------------------------------------
#   Scan parameter sheets
# ----------------------------------------------------------------------

def _is_section(text: str) -> bool:
    text = fix_ti_ligature(text.strip())
    if re.fullmatch(r'[A-Z0-9/\- ]{3,}', text) and re.search('[A-Z]{3}', text):
        return True
    return text in (
        'Patient Position', 'Imaging Parameters', 'Scan Timing',
        'Acquisition Timing', 'Scanning Range', 'User Control Variables',
    )


def read_sheet(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    allpages = load_pages(path, ocr=ocr)
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    entries, full = read_kv(
        allpages, is_header=_is_section, hierarchy=False,
        key_filter=fix_ti_ligature,
    )
    if entries and all(e.value is None for e in entries):
        # keys and values separated by a few spaces only
        entries, full = read_kv(
            allpages, is_header=_is_section, hierarchy=False,
            key_filter=fix_ti_ligature, gap=0.6,
        )
    # Split into protocols when the first section header repeats
    protocols: list[Protocol] = []
    unset = object()
    first_card = unset
    for e in entries:
        if first_card is unset:
            first_card = e.card
        if not protocols or (
            e.card == first_card and protocols[-1].entries
            and protocols[-1].entries[-1].card != first_card
        ):
            protocols.append(Protocol(vendor='GE', format='sheet'))
        protocols[-1].entries.append(e)
        if e.page not in protocols[-1].pages:
            protocols[-1].pages.append(e.page)
    for i, prot in enumerate(protocols):
        name = (prot.get('Series Description', default=None) or
                prot.get('Protocol', default=None))
        if not name:
            name = Path(path).stem + (f'_{i+1}' if len(protocols) > 1
                                      else '')
        prot.name = name
        prot.scanner = {'Manufacturer': 'GE'}
        scanner = prot.get('Scanner', default=None) or ''
        m = re.search(r'(\d(?:\.\d)?)\s*T\b', scanner)
        if m:
            prot.scanner['MagneticFieldStrength'] = float(m.group(1))
        m = re.search(r'GE\s+(.*?)\s*\d(?:\.\d)?\s*T\b', scanner)
        if m and m.group(1):
            prot.scanner['ManufacturersModelName'] = m.group(1)
    return protocols


# ----------------------------------------------------------------------
#   LX protocol scripts (tcl)
# ----------------------------------------------------------------------

RE_SET = re.compile(r'^\s*set\s+(?P<key>\w+)\s+"(?P<value>[^"]*)"?')
RE_PROC = re.compile(r'^\s*proc\s+(?P<name>\w+)\s*\{')


def read_lx(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    allpages = load_pages(path, ocr=ocr)
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    header: dict[str, str] = {}
    protocols: list[Protocol] = []
    current: Protocol | None = None
    for page in allpages:
        for line in make_lines(page):
            text = ' '.join(w.text for w in line.words)
            m = RE_PROC.match(text)
            if m:
                if m.group('name').startswith('series'):
                    current = Protocol(vendor='GE', format='lx',
                                       name=m.group('name'))
                    protocols.append(current)
                else:
                    current = None
                continue
            m = RE_SET.match(text)
            if not m:
                continue
            key, value = m.group('key'), m.group('value').strip()
            if current is None:
                header[key] = value
            elif value:
                current.entries.append(Entry(key, value, 'LX', page=line.page))
                if line.page not in current.pages:
                    current.pages.append(line.page)
    for prot in protocols:
        prot.header = dict(header)
        desc = prot.get('SEDESC', default=None)
        if desc:
            prot.name = desc.strip()
        prot.scanner = {'Manufacturer': 'GE'}
        fs = header.get('FIELDSTRENGTH')
        if fs:
            prot.scanner['MagneticFieldStrength'] = float(fs) / 10000
    return [p for p in protocols if p.entries]


# ----------------------------------------------------------------------
#   DICOM dumps
# ----------------------------------------------------------------------

def read_dicom_dump(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    """One protocol per dump (repeated tags: the first value is kept)."""
    allpages = load_pages(path, ocr=ocr)
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    prot = Protocol(vendor='GE', format='dicom')
    seen = set()
    for page in allpages:
        for line in make_lines(page):
            words = [w.text for w in line.words]
            itag = next((i for i, w in enumerate(words) if RE_TAG.match(w)),
                        None)
            if itag is None:
                continue
            tag = words[itag].lower()
            name = ' '.join(words[:itag]) or tag
            value = ' '.join(words[itag + 1:])
            if tag in seen:
                continue
            seen.add(tag)
            key = tag if name.lower() == 'unknown' else name
            prot.entries.append(Entry(key, value or None, 'DICOM', tag,
                                      page=line.page))
            if line.page not in prot.pages:
                prot.pages.append(line.page)
    by_tag = {e.subcard: e.value for e in prot.entries}
    prot.header = {'tags': by_tag}
    prot.name = by_tag.get('0008,103e') or by_tag.get('0018,1030') or \
        Path(path).stem
    prot.scanner = {
        'Manufacturer': 'GE',
        'ManufacturersModelName': by_tag.get('0008,1090'),
        'SoftwareVersions': by_tag.get('0018,1020'),
    }
    return [prot] if prot.entries else []
