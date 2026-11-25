"""
High-level API.

>>> from protocol2bids import read_protocols, protocol_to_bids
>>> prots = read_protocols('printout.pdf')
>>> sidecar = protocol_to_bids(prots[0], nii='image.nii.gz')
"""
from __future__ import annotations

import fnmatch
from logging import getLogger
from os import PathLike
from typing import Iterable

from .model import Protocol

LOGGER = getLogger(__name__)


READERS = ('table', 'ge.dicom', 'ge.lx', 'siemens', 'philips', 'ge.sheet')


def detect_format(path: str | PathLike) -> str | None:
    """Guess the format of a printout (see `READERS`)."""
    from .pdf.words import load_pages, looks_garbled
    from .vendors import tables
    from .vendors.ge import readers as ge
    from .vendors.philips import examcard
    from .vendors.siemens import printout

    pages = load_pages(path, ocr=False)
    if not any(p.words for p in pages) or looks_garbled(pages):
        return 'siemens'      # needs OCR; only Siemens seen so far
    if tables.sniff(pages):
        return 'table'
    if ge.sniff_dicom(pages):
        return 'ge.dicom'
    if ge.sniff_lx(pages):
        return 'ge.lx'
    if printout.sniff(pages):
        return 'siemens'
    if examcard.sniff(pages):
        return 'philips'
    if ge.sniff_sheet(pages):
        return 'ge.sheet'
    return None


def read_protocols(
    path: str | PathLike,
    hints: Iterable[str] | None = None,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    """
    Read all protocols contained in a printout.

    Parameters
    ----------
    path : path-like
        Protocol printout (PDF).
    hints : list[str], optional
        Format hints, among `READERS` ("siemens", "philips", "ge.sheet",
        "ge.lx", "ge.dicom", "table"); "ge" and "siemens.vb" etc. are
        accepted. If not provided, the format is detected.
    pages : list[int], optional
        Only read these pages (0-indexed).
    ocr : {'auto', True, False}
        OCR policy for pages without (readable) text.
    """
    from .vendors import tables
    from .vendors.ge import readers as ge
    from .vendors.philips import examcard
    from .vendors.siemens import printout

    functions = {
        'table': tables.read_table,
        'ge.dicom': ge.read_dicom_dump,
        'ge.lx': ge.read_lx,
        'ge.sheet': ge.read_sheet,
        'siemens': printout.read_printout,
        'philips': examcard.read_examcard,
    }
    formats = []
    for hint in hints or []:
        hint = hint.lower()
        formats += [f for f in READERS
                    if f.startswith(hint) or hint.startswith(f)]
    if not formats:
        detected = detect_format(path)
        if detected is None:
            LOGGER.warning(f'Unknown printout format: {path}')
            return []
        formats = [detected]
    for fmt in formats:
        prots = functions[fmt](path, pages=pages, ocr=ocr)
        if prots:
            return prots
    return []


def select_protocols(
    protocols: list[Protocol],
    select: Iterable[int | str] | None = None,
) -> list[Protocol]:
    """
    Select protocols by index (0-based int, negative allowed) or by name
    (glob pattern matched against the protocol name or path).
    """
    if not select:
        return list(protocols)
    out = []
    for sel in select:
        if isinstance(sel, str) and sel.lstrip('-').isdigit():
            sel = int(sel)
        if isinstance(sel, int):
            if not -len(protocols) <= sel < len(protocols):
                raise ValueError(f'Protocol index {sel} out of range '
                                 f'({len(protocols)} protocols)')
            out.append(protocols[sel])
            continue
        matches = [
            p for p in protocols
            if fnmatch.fnmatch(p.name, sel) or fnmatch.fnmatch(p.path, sel)
        ]
        if not matches:
            raise ValueError(f'No protocol matches {sel!r}')
        out.extend(m for m in matches if m not in out)
    return out


def protocol_to_bids(
    protocol: Protocol,
    nii: str | PathLike | dict | None = None,
    extra: bool = True,
    strict: bool = False,
    explain: bool = False,
) -> dict:
    """
    Convert a protocol to a BIDS sidecar.

    Parameters
    ----------
    protocol : Protocol
    nii : path or dict, optional
        NIfTI file (or `{'affine': ..., 'shape': ...}`) used to map
        anatomical directions to voxel axes.
    extra : bool
        Include protocol2bids-specific keys.
    strict : bool
        Raise on unexpected errors.
    explain : bool
        Include provenance information.
    """
    if nii is not None and not isinstance(nii, dict):
        nii = {'file': nii}
    kwargs = dict(extra=extra, strict=strict, explain=explain)
    if protocol.format == 'table':
        from .vendors.tables import table_to_bids
        return table_to_bids(protocol, nii, **kwargs)
    vendor = protocol.vendor.lower()
    if vendor == 'siemens':
        from .vendors.siemens.bids import siemens_to_bids
        return siemens_to_bids(protocol, nii, **kwargs)
    if vendor == 'philips':
        from .vendors.philips.bids import philips_to_bids
        return philips_to_bids(protocol, nii, **kwargs)
    if vendor == 'ge':
        from .vendors.ge.bids import ge_to_bids
        return ge_to_bids(protocol, nii, **kwargs)
    raise NotImplementedError(f'No BIDS converter for {protocol.vendor}')
