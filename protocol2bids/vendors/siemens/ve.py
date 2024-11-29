import pymupdf
import re
from os import PathLike
from typing import Literal, Iterator, Iterable
from logging import getLogger

from .utils import peekable
from .common import siemens_to_bids


LOGGER = getLogger(__name__)


def _find_alignment(doc: pymupdf.Document) -> dict[Literal['L', 'R'], float]:
    """
    Find the left-most position of content within each column
    """
    colx = {'L': float('inf'), 'R': float('inf')}
    for text, box in _iter_blocks(doc):
        if text.startswith('-') and text.endswith('-'):
            continue
        if box[0] < doc[0].bound()[2] / 2:
            colx['L'] = min(colx['L'], box[0])
        else:
            colx['R'] = min(colx['R'], box[0])
    return colx


def _parse_model(doc: pymupdf.Document) -> tuple[str, str]:
    """
    Parse scanner model and software version
    """
    for text, _ in _iter_blocks(doc):
        if text.startswith('SIEMENS MAGNETOM'):
            break
    pattern = r'SIEMENS MAGNETOM (?P<model>\w+)'
    match = re.fullmatch(pattern, text)
    if match:
        return match.group('model'), 'syngo MR E11'
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
        if text.startswith('TA:'):
            break
        path += [text]
    path = ' '.join(path)
    title = dict(path=path)
    # Parse tags
    pattern = (
        r'TA:\s*(?P<TA>\S+)\s+'
        r'PM:\s*(?P<PM>\S+)\s+'
        r'Voxel size:\s*'
        r'(?P<vx>[\d\.]+)\s*×\s*(?P<vy>[\d\.]+)\s*×\s*(?P<vz>[\d\.]+)\s*mm'
        # no space between mm and PAT !
        r'PAT:\s*(?P<PAT>\S+)\s+'
        r'Rel. SNR:\s*(?P<SNR>\S+)\s+'
        r':\s*(?P<SeqName>\S+)'
    )
    match = re.fullmatch(pattern, text)
    if match:
        PAT = match.group('PAT')
        title.update({
            'TA': match.group('TA'),
            'PM': match.group('PM'),
            'Voxel size': [float(match.group('vx')),
                           float(match.group('vy')),
                           float(match.group('vz'))],
            'PAT': int(PAT) if PAT != 'Off' else 'Off',
            'Rel. SNR': float(match.group('SNR')),
            'SequenceName': match.group('SeqName'),
        })
    return title


def _iter_blocks(doc: pymupdf.Document) -> Iterator[tuple[str, dict]]:
    has_toc = False
    for page in doc:

        text = page.get_text()
        if 'Table of contents' in text:
            has_toc = True
            continue
        if has_toc:
            if '\\\\' in text and 'TA:' in text:
                # found the start of a protocol, we're passed the TOC
                has_toc = False
            else:
                continue

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
    last_key: str | None = None               # Last parsed key (never erased)

    if skip_pages is not None:
        if isinstance(skip_pages, int):
            skip_pages = [skip_pages]
        skip_pages = list(skip_pages)
        doc = [page for i, page in enumerate(doc) if i not in skip_pages]

    colx = _find_alignment(doc)
    pagewidth = doc[0].bound()[2]

    model_name, software_version = _parse_model(doc)

    iter_bocks = peekable(_iter_blocks(doc))
    while True:
        try:
            text, box = iter_bocks.peek()
        except StopIteration:
            if prot is not None:
                prot['Header'] = title
                prots.append(prot)
            break

        if set(text) in ({'-'}, {'-', ' '}):
            # skip line separator
            iter_bocks.next()
            continue

        if text.startswith('SIEMENS MAGNETOM'):
            # skip line header
            iter_bocks.next()
            continue

        if re.fullmatch(r'- \d+ -', text):
            # skip page number
            iter_bocks.next()
            continue

        if text.startswith('\\\\'):
            # Start of a new protocol (paths start with \\)
            if prot is not None:
                prot['Header'] = title
                prots.append(prot)
            title = _parse_title(iter_bocks)
            title['ModelName'] = model_name
            title['SoftwareVersions'] = software_version
            prot = dict()
            continue

        iter_bocks.next()

        # Find which column we're on and compute indentation size
        column = 'L' if box[0] < pagewidth / 2 else 'R'
        indent = abs(colx[column] - box[0])

        if indent < 1:
            # Section header
            header = text
            prot.setdefault(header, {})
            group = key = None
        elif indent < 10:
            # A key inside a section
            # May happen to be opening a group but we'll only know later.
            CAPITAL = tuple('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            if (
                not text.startswith(CAPITAL) and
                prot[header].get(group, prot[header]).get(last_key, '') is None
            ):
                # Sometimes keys span two lines, which we must reconcile
                del prot[header].get(group, prot[header])[last_key]
                key = last_key = last_key + ' ' + text
                prot[header].get(group, prot[header])[last_key] = None
            else:
                key = last_key = text
                prot[header].setdefault(key, None)
            # If a group was opened, close it
            group = None
        elif indent < 50:
            # A key inside a group
            # - If group is None, this is the first element in the group
            #   and we know now that the previous key was a group.
            #   If group is None _and_ key is None, it's a bit weird...
            if group is None:
                if last_key is None:
                    LOGGER.warning(
                        "Found an element that should be within a group, "
                        "but no opened group. Let's assume it's just a "
                        "normal key: " + text
                    )
                else:
                    group = last_key
                    prot[header].setdefault(group, {})
                    # In VE, group-opening keys can have values
                    # (it was not the case in VD/VB). If it's key case
                    # we edit the group name so that it's "{name} {value}".
                    if not isinstance(prot[header][group], dict):
                        if prot[header][group] is not None:
                            old_group = group
                            group = group + ' ' + prot[header][group]
                            del prot[header][old_group]
                        prot[header][group] = {}
            key = last_key = text
            prot[header][group].setdefault(key, None)
        else:
            # A value.
            # Note that sometime a value is split across multiple lines.
            if last_key is None:
                LOGGER.warning(
                    "Found a value without key... Let's skip it: " + text
                )
                continue
            _group = prot[header].get(group, prot[header])
            if key is None:
                _group[last_key] += ' ' + text
            else:
                if _group[key] is not None:
                    LOGGER.warning(
                        f"Key \"{key}\" was already filled with value "
                        f"\"{prot[header][group][key]}\". Ignoring new "
                        f"value \"{text}\"."
                    )
                else:
                    _group[key] = text
            key = None

    return prots


def sniff(path: str):
    doc = pymupdf.open(str(path))
    try:
        model, version = _parse_model(doc[0])
        if version.startswith('syngo MR E'):
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
