import pymupdf
import re
from os import PathLike
from typing import Literal, Iterator, Iterable
from logging import getLogger

from .utils import peekable
from .common import siemens_to_bids


LOGGER = getLogger(__name__)


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
    # skip page number
    traces = traces[:-2]
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
    first_element = page.get_texttrace()[0]
    text = page.get_textbox(first_element['bbox'])
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
    # title = dict(path=traces.next()[0])
    # text = ''
    # for i in range(5):
    #     # there's something weird with the multiplication signs, with
    #     # a repeated block, so we only use even components
    #     text1 = traces.next()[0]
    #     if i % 2:
    #         continue
    #     text += text1
    # text = text.strip()

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
        r'PAT:\s*(?P<PAT>\S+)\s+'
        r'Voxel size:\s*'
        r'(?P<vx>[\d\.]+)\s*×\s*(?P<vy>[\d\.]+)\s*×\s*(?P<vz>[\d\.]+)\s*mm\s*'
        r'Rel. SNR:\s*(?P<SNR>\S+)\s+'
        r'(?P<SeqFolder>(SIEMENS|USER)):\s*(?P<SeqName>\S+)'
    )
    match = re.fullmatch(pattern, text)
    if match:
        PAT = match.group('PAT')
        title.update({
            'TA': match.group('TA'),
            'PAT': int(PAT) if PAT != 'Off' else 'Off',
            'Voxel size': [float(match.group('vx')),
                           float(match.group('vy')),
                           float(match.group('vz'))],
            'Rel. SNR': float(match.group('SNR')),
            'SequenceFolder': match.group('SeqFolder'),
            'SequenceName': match.group('SeqName'),
        })
    return title


def _iter_traces(doc: pymupdf.Document) -> Iterator[tuple[str, dict]]:
    """
    Iterator aver all traces in the document.
    Returns the corresponding text and trace object.
    """
    for page in doc:
        traces = page.get_texttrace()
        # Skip header and footer
        traces = traces[1:-1]
        for trace in traces:
            text = page.get_textbox(trace['bbox'])
            yield text, trace['bbox']


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
                text = text.rstrip()
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

    colx = _find_alignment(doc[0])
    pagewidth = doc[0].bound()[2]

    model_name, software_version = _parse_model(doc[0])

    iter_traces = peekable(_iter_blocks(doc))
    while True:
        try:
            text, box = iter_traces.peek()
        except StopIteration:
            if prot is not None:
                prot['Header'] = title
                prots.append(prot)
            break

        if text.startswith('\\\\'):
            # Start of a new protocol (paths start with \\)
            if prot is not None:
                prot['Header'] = title
                prots.append(prot)
            title = _parse_title(iter_traces)
            title['ModelName'] = model_name
            title['SoftwareVersions'] = software_version
            prot = dict()
            continue

        # move iterator
        iter_traces.next()

        if set(text) in ({'-'}, {'-', ' '}, {'!'}):
            # skip line separator
            continue

        if text.startswith('SIEMENS MAGNETOM'):
            # skip line header
            continue

        if re.fullmatch(r'\d+/(-|\+)', text):
            # skip page number
            continue

        # if prot is None:
        #     # weird stuff before protocol was opened
        #     continue

        # Find which column we're on and compute indentation size
        column = 'L' if box[0] < pagewidth / 2 else 'R'
        indent = abs(colx[column] - box[0])

        if indent < 1:
            header = text
            prot.setdefault(header, {})
            group = key = None

        elif indent < 15:
            if text.startswith(' '):
                text = text.strip()

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
                # A key inside a section
                # May happen to be opening a group but we'll only know later.
                CAPITAL = tuple('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                _group = prot[header].get(group, prot[header])
                if (
                    not text.startswith(CAPITAL) and
                    _group.get(last_key, '') is None
                ):
                    # Sometimes keys span two lines, which we must reconcile
                    del _group[last_key]
                    key = last_key = last_key + ' ' + text
                    _group[last_key] = None
                else:
                    key = last_key = text
                    prot[header].setdefault(key, None)
                # If a group was opened, close it
                group = None

        # elif indent < 50:
        #     if not text.startswith(' '):
        #         key = last_key = text
        #         if key is not None:
        #             _group = prot[header].get(group, prot[header])
        #             _group[key] = None
        #         group = None
        #     else:
        #         text = text.strip()
        #         if group is None and key is not None:
        #             group = key
        #             prot[header].setdefault(group, {})
        #         key = last_key = text
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
                        f"\"{_group[key]}\". Ignoring new value \"{text}\"."
                    )
                else:
                    _group[key] = text
            key = None

    return prots


def sniff(path: str) -> bool:
    doc = pymupdf.open(str(path))
    try:
        model, version = _parse_model(doc[0])
        if version.startswith('syngo MR B'):
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

    if isinstance(nii, str):
        nii = [nii]
    nii = list(nii or [])
    nii += max(0, len(prots)-len(nii)) * [{}]
    nii = [dict(file=x) if isinstance(x, str) else x for x in nii]

    sidecars = {}
    for prot, info in zip(prots, nii):
        # Convert to BIDS
        sidecar = {**base, **siemens_to_bids(prot, **info)}
        # Save BIDS sidecar
        sidecars[prot['Header']['path']] = sidecar
    return sidecars
