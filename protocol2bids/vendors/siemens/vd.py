import pymupdf
import re
from os import PathLike
from typing import Iterator, Iterable
from .utils import peekable
from .common import siemens_to_bids


def _find_alignment(page: pymupdf.Page) -> float:
    """
    Find the left-most position of content within the page
    """
    traces = page.get_texttrace()
    # Skip page number and date
    traces = traces[1:-1]
    # Skip title elements:
    # [0] Protocol path
    # [1..5] General stuff (PAT, voxel size, etc)
    traces = traces[6:]
    # Find column alignment
    colx = float('inf')
    for trace in traces[:-1]:
        box = trace['bbox']
        text = page.get_textbox(box).strip()
        # skip non header/key components
        if not text:
            continue
        if '\n' in text:
            continue
        if text.startswith('\\\\'):
            continue
        # update left alignment
        colx = min(colx, box[0])
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


def _parse_title(blocks: peekable) -> dict:
    """
    Parse the title box of a protocol
    """
    *path, text = blocks.next()[0]
    path = ''.join([''.join(subpath) for subpath in path])
    text = ' '.join(text)
    title = dict(path=path)
    text = text.strip()
    pattern = (
        r'TA:\s*(?P<TA>\S+)\s+'
        r'PAT:\s*(?P<PAT>\S+)\s+'
        r'Voxel size:\s*'
        r'(?P<vx>[\d\.]+)\s*×\s*(?P<vy>[\d\.]+)\s*×\s*(?P<vz>[\d\.]+)\s*mm\s*'
        r'Rel. SNR:\s*(?P<SNR>\S+)\s+'
        r':\s*(?P<SIEMENS>\S+)'
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
            'SequenceName': match.group('SeqName'),
        })
    return title


def _iter_blocks(doc: pymupdf.Document) -> Iterator[tuple[list, dict]]:
    """
    Iterator over all blocks in the document.
    Returns the corresponding text and block object.
    The returnted text is a list of list
    - outer loop: rows
    - inner loop: cells
    """
    for page in doc:
        blocks = page.get_textpage().extractDICT(sort=True)['blocks']
        for block in blocks:
            lines = [[]]
            x = None
            for line in block['lines']:
                if x is None:
                    x = line['bbox'][1]
                text = '.'.join([span['text'] for span in line['spans']])
                if abs(line['bbox'][1] - x) < 1:
                    lines[-1].append(text)
                else:
                    lines.append([text])
                x = line['bbox'][1]
            yield lines, block


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

    prots: list = []                    # All protocols in the doc
    title: dict | None = None           # Current protocol title object
    prot: dict | None = None            # Current protocol content
    header: str | None = None           # Current header

    colx = _find_alignment(doc[0])

    model_name, software_version = _parse_model(doc[0])

    iter_blocks = peekable(_iter_blocks(doc))
    while True:
        try:
            lines, block = iter_blocks.peek()
        except StopIteration:
            if prot is not None:
                prots.append(prot)
            break

        first_line = lines[0]
        first_span = first_line[0]

        if first_span.startswith('\\\\'):
            if first_span.strip() == '\\\\USER':
                # we're in the table of contents somehow...
                break

            # Start of a new protocol (paths start with \\)
            if prot is not None:
                prots.append(prot)
            title = _parse_title(iter_blocks)
            prot = dict(Header=title)
            continue

        iter_blocks.next()

        if not ''.join(first_line).strip():
            continue
        if first_span.startswith('SIEMENS MAGNETOM'):
            # Separation between protocols
            continue
        if first_span.startswith('Page'):
            # Page number (header)
            continue
        if re.fullmatch(r'\d\d/\d\d/\d\d\d\d', first_span):
            # Date (footer)
            continue
        if first_span == 'Table of contents':
            # Table of contents is always at the end, we can stop here
            if prot is not None:
                prots.append([title, prot])
            break

        # Compute indentation size
        box = block['bbox']
        indent = abs(colx - box[0])

        for line in lines:
            if len(line) == 1 and indent < 10:
                header = line[0]
                prot.setdefault(header, {})
            elif len(line) > 1:
                prot[header][line[0]] = ''.join(line[1:]).strip()
            else:
                prot[header][line[0]] = None

    return model_name, software_version, prots


def sniff(path: str):
    doc = pymupdf.open(str(path))
    try:
        model, version = _parse_model(doc[0])
        if version.startswith('syngo MR D'):
            return True
    finally:
        return False


def parse(path: str | PathLike, nii: Iterable[str | dict] | None = None):
    model, software, prots = _parse_printout_content(path)
    base = {
        'Manufacturer': 'Siemens',
        'ManufacturersModelName': model,
        'SoftwareVersions': software,
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
