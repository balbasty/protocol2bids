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
        Vendor/format hints (e.g. "siemens"). Currently only Siemens
        printouts are supported by the new engine.
    pages : list[int], optional
        Only read these pages (0-indexed).
    ocr : {'auto', True, False}
        OCR policy for pages without (readable) text.
    """
    from .vendors.siemens.printout import read_printout
    return read_printout(path, pages=pages, ocr=ocr)


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
    if protocol.vendor.lower() == 'siemens':
        from .vendors.siemens.bids import siemens_to_bids
        return siemens_to_bids(protocol, nii, extra=extra, strict=strict,
                               explain=explain)
    raise NotImplementedError(f'No BIDS converter for {protocol.vendor}')
