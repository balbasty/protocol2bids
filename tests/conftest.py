import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
HAS_TESSERACT = shutil.which('tesseract') is not None


def pdf(path: str) -> str:
    return str(ROOT / path)


requires_ocr = pytest.mark.skipif(
    not HAS_TESSERACT, reason='tesseract is not installed'
)


def pytest_addoption(parser):
    parser.addoption(
        '--update-snapshots', action='store_true', default=False,
        help='Regenerate the JSON snapshots in tests/snapshots',
    )
