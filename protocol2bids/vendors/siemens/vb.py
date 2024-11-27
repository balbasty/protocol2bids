import pymupdf
import re
from os import PathLike
from typing import Literal, Iterator, Iterable

from .utils import peekable
from .common import siemens_to_bids


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
    title = dict(path=traces.next()[0])
    text = ''
    for i in range(5):
        # there's something weird with the multiplication signs, with
        # a repeated block, so we only use even components
        text1 = traces.next()[0]
        if i % 2:
            continue
        text += text1
    text = text.strip()
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
            yield text, trace


def _parse_printout_content(path: str | PathLike):
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

    colx = _find_alignment(doc[0])
    pagewidth = doc[0].bound()[2]

    model_name, software_version = _parse_model(doc[0])

    iter_traces = peekable(_iter_traces(doc))
    while True:
        try:
            text, trace = iter_traces.peek()
        except StopIteration:
            if prot is not None:
                prot['Header'] = title
                prots.append(prot)
            break

        if set(text) in ({'-'}, {'-', ' '}):
            # skip line separator
            iter_traces.next()
            continue

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

        iter_traces.next()

        box = trace['bbox']
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
            if group is not None:
                prot[header][group][key] = text
            else:
                prot[header][key] = text
            key = None

    return prots


def sniff(path: str):
    doc = pymupdf.open(str(path))
    try:
        model, version = _parse_model(doc[0])
        if version.startswith('syngo MR B'):
            return True
    finally:
        return False


def parse(path: str | PathLike, nii: Iterable[str | dict] | None = None):
    prots = _parse_printout_content(path)
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
