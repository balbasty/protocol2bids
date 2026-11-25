"""
Snapshot (regression) tests.

For every PDF of the corpus, the parsed protocols (all parameters) and the
BIDS sidecars are compared against reference JSON files stored in
`tests/snapshots/`. OCR is disabled so that results do not depend on the
installed tesseract version.

After an intended change, regenerate the snapshots with

    pytest tests/test_snapshots.py --update-snapshots

and review the diff (`git diff tests/snapshots`) before committing.
"""
import json
import logging
import math
from pathlib import Path

import pytest

from protocol2bids import protocol_to_bids, read_protocols

from conftest import ROOT

SNAPSHOTS = ROOT / 'tests' / 'snapshots'

CORPUS = sorted(
    str(p.relative_to(ROOT))
    for folder in ('examples', 'datasets')
    for p in (ROOT / folder).rglob('*.pdf')
)


def snapshot_path(pdf: str) -> Path:
    return SNAPSHOTS / (pdf.replace('/', '__')[:-4] + '.json')


def make_snapshot(pdf: str) -> list[dict]:
    logging.disable(logging.WARNING)
    try:
        prots = read_protocols(ROOT / pdf, ocr=False)
        out = []
        for prot in prots:
            data = prot.to_dict()
            data['bids'] = protocol_to_bids(prot, strict=True)
            out.append(data)
        # round-trip through JSON (tuples -> lists, etc.)
        return json.loads(json.dumps(out, ensure_ascii=False))
    finally:
        logging.disable(logging.NOTSET)


def _diff(ref, new, path=''):
    """First difference between two JSON-like objects (or None)."""
    if isinstance(ref, float) or isinstance(new, float):
        if isinstance(ref, (int, float)) and isinstance(new, (int, float)) \
                and math.isclose(ref, new, rel_tol=1e-9, abs_tol=1e-12):
            return None
        return f'{path}: {ref!r} != {new!r}'
    if isinstance(ref, dict) and isinstance(new, dict):
        for key in list(ref) + [k for k in new if k not in ref]:
            if key not in new:
                return f'{path}/{key}: removed (was {ref[key]!r})'
            if key not in ref:
                return f'{path}/{key}: added ({new[key]!r})'
            d = _diff(ref[key], new[key], f'{path}/{key}')
            if d:
                return d
        return None
    if isinstance(ref, list) and isinstance(new, list):
        if len(ref) != len(new):
            return f'{path}: length {len(ref)} != {len(new)}'
        for i, (a, b) in enumerate(zip(ref, new)):
            d = _diff(a, b, f'{path}[{i}]')
            if d:
                return d
        return None
    return None if ref == new else f'{path}: {ref!r} != {new!r}'


@pytest.mark.parametrize('pdf', CORPUS)
def test_snapshot(pdf, request):
    new = make_snapshot(pdf)
    path = snapshot_path(pdf)
    if request.config.getoption('--update-snapshots'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(new, indent=1, ensure_ascii=False) + '\n')
        return
    if not path.exists():
        pytest.fail(f'No snapshot for {pdf}: run with --update-snapshots')
    ref = json.loads(path.read_text())
    diff = _diff(ref, new)
    assert diff is None, f'{pdf}: {diff}'
