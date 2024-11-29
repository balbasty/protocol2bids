import pymupdf
import re
from os import PathLike
from typing import Literal, Iterator, Iterable
from logging import getLogger

from .utils import peekable
from .common import siemens_to_bids

LOGGER = getLogger(__name__)

# NOTE
# * The main difference between VA and VB printouts is that it seems
#   that the headers
#       - SIEMENS MAGNETOM Sonata syngo MR 2004A
#       - \\\USER\\ADNI\\MAIN-PHASE\\Human Protocol\\Localizer
#   are inserted (and therefore listed by pymupdf) after the content
#   of the protocol.
# * However, protocols always start on a new page, so if we can find a
#   sequence title box in a page, it means that a new protocol has started


def _merge_dicts(prots):

    def _merge1(out, inp):
        if isinstance(inp, dict):
            for key, value in inp.items():
                out.setdefault(key, {})
                if isinstance(value, dict):
                    _merge1(out[key], value)
                else:
                    out[key] = value
        else:
            raise TypeError

    out = {}
    for prot in prots:
        _merge1(out, prot)
    return out


def _find_alignment(page: pymupdf.Page) -> dict[Literal['L', 'R'], float]:
    """
    Find the left-most position of content within each column
    """
    traces = page.get_texttrace()
    # Skip the first element (Scanner and Software versions)
    traces = traces[1:]
    # Skip title elements:
    # [0] Protocol path
    # [1..5] General stuff (PAT, voxel size, etc)
    traces = traces[6:]
    # Find column alignment
    colx = {'L': float('inf'), 'R': float('inf')}
    for trace in traces[:-1]:
        box = trace['bbox']
        text = page.get_textbox(box)
        if text.startswith('-') and text.endswith('-'):
            continue
        if box[0] < page.bound()[2] / 2:
            colx['L'] = min(colx['L'], box[0])
        else:
            colx['R'] = min(colx['R'], box[0])
    return colx


def _parse_model(page: pymupdf.Page) -> tuple[str, str]:
    """
    Parse scanner model and software version
    """
    for element in page.get_texttrace():
        text = page.get_textbox(element['bbox']).strip()
        if text.startswith('SIEMENS MAGNETOM'):
            break
    pattern = r'SIEMENS MAGNETOM (?P<model>\w+) (?P<version>.+)'
    match = re.fullmatch(pattern, text)
    if match:
        return match.group('model'), match.group('version')
    else:
        return None, None


def _parse_title(traces: peekable) -> dict:
    """
    Parse the title box of a protocol
    """
    # Parse sequence path
    path = []
    while True:
        text = traces.next()[0]
        if text.startswith(('Scan Time', '+ Scan Time')):
            break
        path += [text]
    path = ' '.join(path)
    title = dict(path=path)
    # Parse tags
    text = text.strip()
    pattern = (
        r'\+?\s*Scan Time:\s*(?P<TA>\S+)\s*(\[[^\]]+\])?\s+'
        r'Voxel size:\s*'
        r'(?P<vx>[\d\.]+)\s*×\s*(?P<vy>[\d\.]+)\s*×\s*(?P<vz>[\d\.]+)\s*(\[[^\]]+\])?\s*'  # noqa: E501
        r'Rel. SNR:\s*(?P<SNR>\S+)\s+'
        r'(?P<SeqFolder>(SIEMENS|USER)):\s*(?P<SeqName>\S+)'
    )
    match = re.fullmatch(pattern, text)
    if match:
        title.update({
            'TA': match.group('TA'),
            'Voxel size': [float(match.group('vx')),
                           float(match.group('vy')),
                           float(match.group('vz'))],
            'Rel. SNR': float(match.group('SNR')),
            'SequenceFolder': match.group('SeqFolder'),
            'SequenceName': match.group('SeqName'),
        })
    return title


NEWPAGE = object()


def _iter_blocks(doc: pymupdf.Document) -> Iterator[tuple[str, dict]]:
    for page in doc:
        yield NEWPAGE
        blocks = page.get_textpage().extractDICT(sort=False)['blocks']
        for block in blocks:
            lines = [[]]
            boxes = [[]]
            x = None
            for line in block['lines']:
                if x is None:
                    x = line['bbox'][1]
                text = ''.join([span['text'] for span in line['spans']])
                text = text.strip()
                if abs(line['bbox'][1] - x) < 1:
                    lines[-1].append(text)
                    boxes[-1].append(line['bbox'])
                else:
                    lines.append([text])
                    boxes.append([line['bbox']])
                x = line['bbox'][1]
            for line, cellboxes in zip(lines, boxes):
                for cell, bbox in zip(line, cellboxes):
                    yield cell, bbox


def _parse_printout_content(
    path: str | PathLike,
    skip_pages: int | Iterable[int] | None = None
):
    """
    Parse the content in a protocol printout

    Returns
    -------
    model_name : str
        Name of the scanner
    software_version : str
        Version of the software
    protocols : list[(dict, dict)]
        A list of protocol, where each protocol contains
        a "title" dictionary, with keys "path" and a few others,
        and a "key-value" dictionary that contains all parameters
        in the protocol.
    """
    doc = pymupdf.open(str(path))

    prots: list = []                          # All protocols in the doc
    title: dict | None = None                 # Current protocol title object
    prot: dict | None = None                  # Current protocol content
    column: Literal['L', 'R'] | None = None   # Current column
    header: str | None = None                 # Current header
    group: str | None = None                  # Current group
    key: str | None = None                    # Last parsed key

    if skip_pages is not None:
        if isinstance(skip_pages, int):
            skip_pages = [skip_pages]
        skip_pages = list(skip_pages)
        doc = [page for i, page in enumerate(doc) if i not in skip_pages]

    colx = _find_alignment(doc[0])
    pagewidth = doc[0].bound()[2]

    model_name, software_version = _parse_model(doc[0])

    iter_traces = peekable(_iter_blocks(doc))
    prots_buffer = []
    while True:
        try:
            elem = iter_traces.peek()
            if elem is NEWPAGE:
                iter_traces.next()
                if prot is not None:
                    prots_buffer.append(prot)
                prot = dict()
                continue
            else:
                text, box = elem
        except StopIteration:
            if prot is not None:
                prots_buffer.append(prot)
            if prots_buffer:
                prots.append(_merge_dicts(prots_buffer))
            prots_buffer = []
            break

        if text.startswith('SIEMENS MAGNETOM'):
            # skip header
            iter_traces.next()
            continue

        if set(text) in ({'-'}, {'-', ' '}):
            # skip line separator
            iter_traces.next()
            continue

        if text.endswith(('/-', '/+')):
            # skip page number
            iter_traces.next()
            continue

        if text.startswith('\\\\'):
            # a new protocol was started on this page (paths start with \\)
            # 1. combine all protocols from previous pages and append them
            if prots_buffer:
                prots.append(_merge_dicts(prots_buffer))
            prots_buffer = []
            # 2. parse header and insert in last protocol (current page)
            title = _parse_title(iter_traces)
            title['ModelName'] = model_name
            title['SoftwareVersions'] = software_version
            prot['Header'] = title
            continue

        iter_traces.next()

        # Find which column we're on and compute indentation size
        column = 'L' if box[0] < pagewidth / 2 else 'R'
        indent = abs(colx[column] - box[0])

        if indent < 1:
            header = text
            prot.setdefault(header, {})
            group = key = None
        elif indent < 50:
            if not text.startswith(' '):
                if key is not None:
                    if group is not None:
                        prot[header][group][key] = None
                    else:
                        prot[header][key] = None
                key = text
                group = None
            else:
                text = text.strip()
                if group is None and key is not None:
                    group = key
                    prot[header].setdefault(group, {})
                key = text
        else:
            assert key is not None, key
            prot.setdefault(header, {})
            if group is not None:
                prot[header].setdefault(group, {})
                prot[header][group][key] = text
            else:
                prot[header][key] = text
            key = None

    return prots


def sniff(path: str):
    doc = pymupdf.open(str(path))
    try:
        model, version = _parse_model(doc)
        if version.startswith('syngo MR 20'):
            return True
    except Exception:
        ...
    return False


def parse(
    path: str | PathLike,
    nii: Iterable[str | dict] | None = None,
    skip_pages: int | Iterable[int] | None = None,
):
    prots = _parse_printout_content(path, skip_pages=skip_pages)
    base = {
        'Manufacturer': 'Siemens',
        'ManufacturersModelName': prots[0]['Header']['ModelName'],
        'SoftwareVersions': prots[0]['Header']['SoftwareVersions'],
    }
    nii = nii or []
    nii += max(0, len(prots)-len(nii)) * [{}]
    nii = [dict(file=x) if isinstance(x, str) else x for x in nii]
    sidecars = {}
    for prot, info in zip(prots, nii):
        # Convert to BIDS
        sidecar = {**base, **siemens_to_bids(prot, **info)}
        # Save BIDS sidecar
        sidecars[prot['Header']['path']] = sidecar
    return sidecars
