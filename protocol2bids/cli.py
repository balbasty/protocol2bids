import json
from ast import literal_eval
from logging import getLogger, basicConfig, INFO, DEBUG, WARNING
from os import PathLike
from pathlib import Path
from typing import Iterable, Literal

import cyclopts

from .api import protocol_to_bids, read_protocols, select_protocols
from .utils.prettify import JSONs


LOGGER = getLogger(__name__)

app = cyclopts.App("protocol2bids", help_format="markdown")

Hint = Literal[
    'siemens',
    'siemens.va',
    'siemens.vb',
    'siemens.vd',
    'siemens.ve',
    'siemens.xa',
]


def _setup_logging(verbose: int = 0):
    level = {0: WARNING, 1: INFO}.get(verbose, DEBUG)
    basicConfig(format="%(levelname)s | %(message)s", level=level)


def _pages(path: str | PathLike, skip_pages: Iterable[int] | None):
    if not skip_pages:
        return None
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        n = len(doc)
    skip = set(skip_pages)
    return [i for i in range(n) if i not in skip]


def _parse_dict(value, name):
    if not value:
        return {}
    if isinstance(value, str):
        value = literal_eval(value)
    if not isinstance(value, dict):
        raise TypeError(f'--{name} must be a dictionary')
    return value


@app.default
def protocol2bids(
    inp: str | PathLike,
    out: str | PathLike | None = None,
    *,
    hints: Iterable[str] | None = None,
    select: Iterable[str] | None = None,
    nii: Iterable[str | PathLike] | None = None,
    defaults: str | dict | None = None,
    assigns: str | dict | None = None,
    skip_pages: Iterable[int] | None = None,
    bids_only: bool = False,
    explain: bool = False,
    ocr: Literal['auto', 'always', 'never'] = 'auto',
    verbose: int = 0,
):
    """
    protocol2bids : Convert protocol printouts to BIDS sidecars
    ===========================================================

    Parameters
    ----------
    inp
        Path to input protocol file
    out
        Path to output JSON file. If several protocols are converted,
        one file per protocol is written (suffixed with an index).
        Defaults to the input path with a `.json` extension.
    hints
        Protocol hints (ex: "siemens")
    select
        Protocols to convert: 0-based indices or glob patterns matched
        against protocol names (see `protocol2bids list`).
        Default: all protocols.
    nii
        Path(s) to nifti file(s) (to read shape/affine from), one per
        selected protocol.
    defaults
        Dictionary of default BIDS metadata
    assigns
        Dictionary of BIDS metadata to assign
    skip_pages
        List of (0-based) pages to ignore in the protocol
    bids_only
        Only write BIDS and dcm2niix keys (no protocol2bids helper keys)
    explain
        Write the protocol parameters used for each key (`_provenance`)
    ocr
        OCR policy for pages without readable text
    verbose
        Verbosity level (0: warnings, 1: info, 2: debug)

    Returns
    -------
    sidecars : dict{str, JSON}
        JSON sidecars
    """
    _setup_logging(verbose)
    ocr = {'auto': 'auto', 'always': True, 'never': False}[ocr]

    prots = read_protocols(inp, hints=hints, pages=_pages(inp, skip_pages),
                           ocr=ocr)
    if not prots:
        raise ValueError(f'No protocol found in {inp}')
    prots = select_protocols(prots, select)

    nii = list(nii or [])
    nii += [None] * max(0, len(prots) - len(nii))

    defaults = _parse_dict(defaults, 'defaults')
    assigns = _parse_dict(assigns, 'assigns')

    sidecars = {}
    for i, (prot, nifti) in enumerate(zip(prots, nii)):
        sidecar = protocol_to_bids(prot, nifti or None, extra=not bids_only,
                                   explain=explain)
        sidecar = {**defaults, **sidecar, **assigns}
        key = prot.path or prot.name or f'protocol{i+1}'
        if key in sidecars:
            key = f'{key} ({i+1})'
        sidecars[key] = sidecar

    if out is None:
        out = Path(inp).with_suffix('.json')
    out = Path(out)
    if not out.suffix:
        out = out / 'protocol.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    for i, sidecar in enumerate(sidecars.values()):
        opath = out
        if len(sidecars) > 1:
            opath = out.with_stem(out.stem + f'{i+1}')
        with opath.open('w') as f:
            json.dump(sidecar, f, indent=4)

    return JSONs(sidecars)


@app.command(name='list')
def list_protocols(
    inp: str | PathLike,
    *,
    ocr: Literal['auto', 'always', 'never'] = 'auto',
    verbose: int = 0,
):
    """
    List the protocols contained in a printout.

    Parameters
    ----------
    inp
        Path to input protocol file
    ocr
        OCR policy for pages without readable text
    verbose
        Verbosity level
    """
    _setup_logging(verbose)
    ocr = {'auto': 'auto', 'always': True, 'never': False}[ocr]
    prots = read_protocols(inp, ocr=ocr)
    for i, prot in enumerate(prots):
        seq = prot.header.get('SequenceName') or \
            prot.get('Sequence Name', default='?')
        pages = f'{min(prot.pages)}-{max(prot.pages)}' if prot.pages else '?'
        print(f'[{i:2d}] {prot.name or "<unnamed>":40s} '
              f'seq={seq:20s} pages={pages}')


@app.command
def dump(
    inp: str | PathLike,
    out: str | PathLike | None = None,
    *,
    select: Iterable[str] | None = None,
    ocr: Literal['auto', 'always', 'never'] = 'auto',
    verbose: int = 0,
):
    """
    Dump the raw content of a printout (all parameters) as JSON.

    Parameters
    ----------
    inp
        Path to input protocol file
    out
        Path to output JSON file (default: stdout)
    select
        Protocols to dump (indices or name patterns)
    ocr
        OCR policy for pages without readable text
    verbose
        Verbosity level
    """
    _setup_logging(verbose)
    ocr = {'auto': 'auto', 'always': True, 'never': False}[ocr]
    prots = select_protocols(read_protocols(inp, ocr=ocr), select)
    data = [p.to_dict() for p in prots]
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out is None:
        print(text)
    else:
        Path(out).write_text(text)
