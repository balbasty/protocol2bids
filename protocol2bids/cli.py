import cyclopts
import json
from typing import Iterable, Literal
from pathlib import Path
from os import PathLike
from ast import literal_eval
from logging import getLogger, basicConfig, INFO

from .register import REGISTER
from .utils.nii2axes import nii2shape
from .utils.prettify import JSONs


LOGGER = getLogger(__name__)

app = cyclopts.App("protocol2bids", help_format="markdown")

Hint = Literal[
    'siemens.va',
    'siemens.vb',
    'siemens.vd',
    'siemens.ve',
]


@app.default
def protocol2bids(
    inp: str | PathLike,
    out: str | PathLike | None,
    *,
    hints: Iterable[str] | None = None,
    nii: Iterable[str | PathLike] | None = None,
    defaults: str | dict | None = None,
    assigns: str | dict | None = None,
    skip_pages: Iterable[int] | None = None,
):
    """
    protocol2bids : Convert protocol printouts to BIDS sidecars
    ===========================================================

    Parameters
    ----------
    inp
        Path to input protocol file
    out
        Path to output JSON file
    hints
        Protocol hints (ex: "siemens.vb")
    nii
        Path(s) to nifti file(s) (to read shape/affine from)
    defaults
        Dictionary of default BIDS metadata
    assigns
        Dictionary of BIDS metadata to assign
    skip_pages
        List of pages to ignore in the protocol

    Returns
    -------
    sidecars : dict{str, JSON}
        JSON sidecars
    """
    basicConfig(format="%(message)s", level=INFO)

    sidecars = None
    tried = set()

    volinfo = []
    if nii is not None:
        for path in nii:
            if not path:
                volinfo.append({})
            else:
                affine, shape = nii2shape(path)
                volinfo.append(dict(affine=affine, shape=shape))

    opt = dict(nii=volinfo, skip_pages=skip_pages)

    # Use hints
    for hint in (hints or []):
        for path in reversed(sorted(REGISTER)):
            if not path.startswith(hint):
                continue
            tried.add(path)
            parse = getattr(REGISTER[path], 'parse')
            try:
                LOGGER.info(f'parse: {path}')
                sidecars = parse(inp, **opt)
                break
            except Exception as e:
                LOGGER.warning(f'Failed to parse with parser {path}: {e}')
                raise e

    # Use sniff
    if sidecars is None:
        for path, module in REGISTER.items():
            if path in tried:
                continue
            LOGGER.info(f'sniff: {path}')
            sniff = getattr(module, 'sniff')
            parse = getattr(module, 'parse')
            if sniff(inp):
                tried.add(path)
                try:
                    LOGGER.info(f'parse: {path}')
                    sidecars = parse(inp, **opt)
                    break
                except Exception as e:
                    LOGGER.warning(f'Failed to parse with parser {path}: {e}')
                    raise e

    # Try all remaining
    if sidecars is None:
        for path, module in REGISTER.items():
            if path in tried:
                continue
            tried.add(path)
            parse = getattr(module, 'parse')
            try:
                LOGGER.info(f'parse: {path}')
                sidecars = parse(inp, **opt)
                break
            except Exception as e:
                LOGGER.warning(f'Failed to parse with parser {path}: {e}')

    # Set defaults
    if defaults:
        if isinstance(defaults, str):
            defaults = literal_eval(defaults)
        if not isinstance(defaults, dict):
            raise TypeError('--defaults must be a dictionary')
        sidecars = {**defaults, **sidecars}

    # Set forced values
    if assigns:
        if isinstance(assigns, str):
            assigns = literal_eval(assigns)
        if not isinstance(defaults, dict):
            raise TypeError('--assigns must be a dictionary')
        sidecars.update(assigns)

    # Write JSON file
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
