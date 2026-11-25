"""
Scan parameter tables distributed with FCON1000 datasets (CoRR, ABIDE):
one row per parameter, one column per scan::

                        Anatomical     Rest        DTI
    Manufacturer         Siemens      Siemens     Siemens
    Echo Time (TE) [ms]   3.39          30          89
"""
from __future__ import annotations

import re
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any, Iterable

from .. import values as V
from ..model import Entry, Missing, Protocol
from ..pdf.layout import make_lines
from ..pdf.words import Page, load_pages
from ..utils.nii2axes import nii2axes

LOGGER = getLogger(__name__)

SCAN_NAMES = re.compile(
    r'^(Anatomical|Rest|Rest\s*\d+|DTI|Diffusion|Field\s*map|Fieldmap|'
    r'Functional|Task|T1|T2|ASL|.*Rest.*|.*Anat.*)$', re.I)
ROW_NAMES = ('Manufacturer', 'Echo Time', 'Repetition Time', 'Flip Angle')


def sniff(pages: list[Page]) -> bool:
    text = ' '.join(w.text for p in pages[:1] for w in p.words)
    return (sum(k in text for k in ROW_NAMES) >= 3 and
            ('Anatomical' in text or 'Rest' in text))


def read_table(
    path: str | PathLike,
    pages: Iterable[int] | None = None,
    ocr: bool | str = 'auto',
) -> list[Protocol]:
    allpages = load_pages(path, ocr=ocr)
    if pages is not None:
        pages = set(pages)
        allpages = [p for p in allpages if p.index in pages]
    protocols: list[Protocol] = []
    for page in allpages:
        lines = make_lines(page, gap=1.0)
        header = None
        title = ''
        for i, line in enumerate(lines):
            names = [s for s in line.segments if SCAN_NAMES.match(s.text)]
            if len(names) >= 2 and len(names) == len(line.segments):
                header = i
                break
            if len(line.segments) >= 2 and line.segments[0].text in (
                    'Manufacturer',):
                break
            title = title or line.text
        if header is None:
            continue
        cols = lines[header].segments
        centers = [0.5 * (s.x0 + s.x1) for s in cols]
        first = cols[0].x0
        prots = [Protocol(name=s.text, vendor='', format='table',
                          header={'site': title}, pages=[page.index])
                 for s in cols]
        for line in lines[header + 1:]:
            keysegs = [s for s in line.segments if s.x1 < first - 2]
            valsegs = [s for s in line.segments if s.x1 >= first - 2]
            if not keysegs or not valsegs:
                continue
            key = ' '.join(s.text for s in keysegs)
            for seg in valsegs:
                xc = 0.5 * (seg.x0 + seg.x1)
                icol = min(range(len(centers)),
                           key=lambda k: abs(centers[k] - xc))
                value = seg.text.strip()
                if value in ('-', '--', 'n/a', 'N/A'):
                    continue
                prots[icol].entries.append(
                    Entry(key, value, 'Table', page=page.index))
        for prot in prots:
            manu = prot.get('Manufacturer', default='') or ''
            prot.vendor = manu.strip()
            prot.scanner = {'Manufacturer': manu.strip()}
            prot.name = f'{title} {prot.name}'.strip() if title else prot.name
        protocols.extend(p for p in prots if p.entries)
    return protocols


# ----------------------------------------------------------------------
#   BIDS
# ----------------------------------------------------------------------

def _find(prot: Protocol, *patterns: str) -> str:
    for pattern in patterns:
        for e in prot.entries:
            if re.match(pattern, e.key, re.I) and e.value:
                return e.value
    raise Missing(patterns[0])


def table_to_bids(prot: Protocol, nii: dict | None = None,
                  extra: bool = True, strict: bool = False,
                  explain: bool = False) -> dict:
    out: dict[str, Any] = {}

    def attempt(func):
        try:
            func()
        except (Missing, ValueError, KeyError, IndexError) as e:
            LOGGER.debug(f'{func.__name__}: skipped ({e})')

    vendor = prot.vendor.lower()
    out['Manufacturer'] = prot.vendor or None

    def hardware():
        out['ManufacturersModelName'] = _find(prot, r'Model')
    attempt(hardware)

    def field():
        out['MagneticFieldStrength'] = V.number(_find(prot, r'Field Strength'))
    attempt(field)

    def coil():
        out['ReceiveCoilName'] = _find(prot, r'Head\s*coil', r'Coil')
    attempt(coil)

    def sequence():
        seq = _find(prot, r'Sequence')
        out['PulseSequenceType'] = seq
        up = seq.upper()
        out['MRAcquisitionType'] = '3D' if '3D' in up else '2D'
        if 'EPI' in up:
            out['ScanningSequence'] = ['EP']
    attempt(sequence)

    def times():
        out['RepetitionTime'] = V.number(_find(prot, r'Repetition Time')) * 1e-3
    attempt(times)

    def echo():
        out['EchoTime'] = V.number(_find(prot, r'Echo Time')) * 1e-3
    attempt(echo)

    def inversion():
        out['InversionTime'] = V.number(_find(prot, r'Inversion Time')) * 1e-3
    attempt(inversion)

    def flip():
        out['FlipAngle'] = V.number(_find(prot, r'Flip Angle'))
    attempt(flip)

    def bandwidth():
        bw = V.number(_find(prot, r'Bandwidth'))
        if vendor == 'philips' and 'EP' in out.get('ScanningSequence', []):
            # Philips EPI "bandwidth" is usually the (water-fat shift
            # based) bandwidth along the phase-encoding direction
            out['PhilipsReportedBandwidth'] = bw
            return
        out['PixelBandwidth'] = bw
    attempt(bandwidth)

    def pat():
        value = _find(prot, r'Parallel Acquisition')
        m = re.match(r'\s*([A-Za-z]+)\s*[xX×]\s*([\d.]+)', value)
        if m:
            out['ParallelAcquisitionTechnique'] = m.group(1).upper()
            out['ParallelReductionFactorInPlane'] = float(m.group(2))
    attempt(pat)

    def pf():
        value = _find(prot, r'Partial Fourier')
        f = V.fraction(value)
        if f < 1:
            out['PartialFourier'] = f
    attempt(pf)

    def geometry():
        thick = V.number(_find(prot, r'Slice Thickness'))
        out['SliceThickness'] = thick
        if out.get('MRAcquisitionType') == '2D':
            gap = V.number(_find(prot, r'Slice Gap'))
            out['SpacingBetweenSlices'] = round(thick + gap, 6)
    attempt(geometry)

    def matrix():
        mat = V.matrix(_find(prot, r'Acquisition Matrix'))
        out['AcquisitionMatrixPE'] = mat[1]
    attempt(matrix)

    def direction():
        text = _find(prot, r'.*Phase Encoding Direction').lower()
        m = re.match(r'(\w+)\s+to\s+(\w+)', text)
        letters = {'anterior': 'A', 'posterior': 'P', 'right': 'R',
                   'left': 'L', 'superior': 'S', 'inferior': 'I',
                   'head': 'S', 'foot': 'I', 'feet': 'I'}
        code = letters[m.group(1)] + letters[m.group(2)]
        if extra:
            out['DirectionPE'] = code
        info = dict(nii or {})
        # Polarity follows the Siemens convention ("A >> P" = "j-"),
        # only trusted for Siemens data.
        if vendor == 'siemens' and ('file' in info or 'affine' in info):
            _, anat2vox, _ = nii2axes(**info)
            out['PhaseEncodingDirection'] = anat2vox[code]
    attempt(direction)

    def slice_timing():
        if vendor != 'siemens' or out.get('MRAcquisitionType') != '2D':
            return
        order = _find(prot, r'Slice Acquisition Order').lower()
        n = V.integer(_find(prot, r'Number of Slices'))
        tr = out['RepetitionTime']
        if 'interleaved' in order:
            if n % 2:
                seq = list(range(0, n, 2)) + list(range(1, n, 2))
            else:
                seq = list(range(1, n, 2)) + list(range(0, n, 2))
            if 'descending' in order:
                seq = [n - 1 - s for s in seq]
        elif 'ascending' in order:
            seq = list(range(n))
        elif 'descending' in order:
            seq = list(range(n))[::-1]
        else:
            return
        timing = [0.0] * n
        for rank, s in enumerate(seq):
            timing[s] = round(rank * tr / n, 6)
        out['SliceTiming'] = timing
    attempt(slice_timing)

    return {k: v for k, v in out.items() if v is not None}
