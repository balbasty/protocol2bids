"""
Parsing of protocol values (as printed) into python values.

All functions raise `ValueError` when the value cannot be interpreted.
"""
from __future__ import annotations

import re

_NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
RE_NUMBER = re.compile(_NUMBER)

UNITS = {
    # time -> seconds
    'ms': 1e-3, 's': 1.0, 'sec': 1.0, 'us': 1e-6, 'µs': 1e-6, 'min': 60.0,
    # length -> mm
    'mm': 1.0, 'cm': 10.0, 'm': 1e3,
    # angle -> deg
    'deg': 1.0, '°': 1.0,
    # frequency -> Hz
    'hz': 1.0, 'khz': 1e3, 'mhz': 1e6,
    'hz/px': 1.0, 'hz/pixel': 1.0,
    # percentage -> percent
    '%': 1.0,
}


def _clean(value) -> str:
    if value is None:
        raise ValueError('None')
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).replace(' ', ' ').strip()


def number(value) -> float:
    """First number in a string: '2000 ms' -> 2000.0, '0 [%]' -> 0.0"""
    text = _clean(value).replace(',', '.') if re.fullmatch(
        r'\s*\d+,\d+\s*\S*', _clean(value)) else _clean(value)
    match = RE_NUMBER.search(text)
    if not match:
        raise ValueError(f'No number in {value!r}')
    return float(match.group())


def integer(value) -> int:
    x = number(value)
    if abs(x - round(x)) > 1e-6:
        raise ValueError(f'Not an integer: {value!r}')
    return int(round(x))


def numbers(value) -> list[float]:
    return [float(x) for x in RE_NUMBER.findall(_clean(value))]


def unit(value) -> str | None:
    """Unit following the first number: '2000 ms' -> 'ms',
    '240 [mm]' -> 'mm'"""
    text = _clean(value)
    match = re.match(rf'\s*{_NUMBER}\s*\[?([^\]\s\d][^\]\s]*)\]?', text)
    return match.group(1) if match else None


def quantity(value, to: str | None = None) -> float:
    """
    Number with unit, optionally converted.

    quantity('2000 ms', 's') -> 2.0
    quantity('240 [mm]', 'mm') -> 240.0
    """
    x = number(value)
    if to is None:
        return x
    u = (unit(value) or to).lower()
    if u not in UNITS or to.lower() not in UNITS:
        raise ValueError(f'Unknown unit {u!r} or {to!r}')
    return x * UNITS[u] / UNITS[to.lower()]


def seconds(value) -> float:
    """'2000 ms' -> 2.0 ; values without unit are assumed in ms."""
    return quantity(value, 's') if unit(value) else number(value) * 1e-3


def percent(value) -> float:
    """'20 %' -> 20.0"""
    return number(value)


TRUE = {'on', 'yes', 'true', '1', 'enabled', 'allowed'}
FALSE = {'off', 'no', 'false', '0', 'none', 'disabled', '---'}


def boolean(value) -> bool:
    text = _clean(value).lower()
    if text in TRUE:
        return True
    if text in FALSE:
        return False
    raise ValueError(f'Not a boolean: {value!r}')


def is_off(value) -> bool:
    try:
        return not boolean(value)
    except ValueError:
        return False


def fraction(value) -> float:
    """
    Partial Fourier factors: '6/8' -> 0.75, 'Off' -> 1.0, '75 %' -> 0.75
    """
    text = _clean(value)
    if is_off(text):
        return 1.0
    match = re.fullmatch(r'\s*(\d+)\s*/\s*(\d+)\s*', text)
    if match:
        return int(match.group(1)) / int(match.group(2))
    if '%' in text:
        return number(text) / 100
    x = number(text)
    return x if x <= 1 else x / 100


_ANAT = {
    'R': 'R', 'L': 'L', 'A': 'A', 'P': 'P',
    'F': 'I', 'H': 'S', 'I': 'I', 'S': 'S',
}


def direction(value) -> str:
    """
    Siemens direction strings to anatomical codes:
    'A >> P' -> 'AP', 'R>>L' -> 'RL', 'F >> H' -> 'IS', 'H >> F' -> 'SI'
    """
    text = _clean(value).upper()
    match = re.fullmatch(r'\s*([RLAPFHIS])\s*>+\s*([RLAPFHIS])\s*', text)
    if not match:
        raise ValueError(f'Not a direction: {value!r}')
    a, b = _ANAT[match.group(1)], _ANAT[match.group(2)]
    if {a, b} not in ({'R', 'L'}, {'A', 'P'}, {'I', 'S'}):
        raise ValueError(f'Not a direction: {value!r}')
    return a + b


_ORIENT = {
    'tra': 'T', 'transversal': 'T', 'transverse': 'T', 'axial': 'T',
    't': 'T', 'ax': 'T',
    'sag': 'S', 'sagittal': 'S', 's': 'S',
    'cor': 'C', 'coronal': 'C', 'c': 'C',
}


def orientation(value) -> tuple[str, list[tuple[str, float]]]:
    """
    Slice orientation: main plane in {'T', 'S', 'C'} and oblique tilts.

    'Transversal' -> ('T', [])
    'T > C-23.0' -> ('T', [('C', -23.0)])
    'Sag>Cor(-10.2)>Tra(3.1)' -> ('S', [('C', -10.2), ('T', 3.1)])
    """
    text = _clean(value)
    parts = [p.strip() for p in re.split(r'>', text) if p.strip()]
    if not parts:
        raise ValueError(f'Not an orientation: {value!r}')
    main = re.match(r'[A-Za-z]+', parts[0])
    if not main or main.group().lower() not in _ORIENT:
        raise ValueError(f'Not an orientation: {value!r}')
    out = _ORIENT[main.group().lower()]
    tilts = []
    for part in parts[1:]:
        m = re.match(r'([A-Za-z]+)\s*\(?\s*(' + _NUMBER + r')', part)
        if m and m.group(1).lower() in _ORIENT:
            tilts.append((_ORIENT[m.group(1).lower()], float(m.group(2))))
    return out, tilts


def position(value) -> dict[str, float]:
    """'L0.0 A20.0 H0.0 mm' -> {'L': 0.0, 'A': 20.0, 'H': 0.0};
    'Isocenter' -> {}"""
    text = _clean(value)
    if text.lower().startswith('iso'):
        return {}
    out = {}
    for m in re.finditer(r'([RLAPFH])\s*(' + _NUMBER + ')', text):
        out[m.group(1)] = float(m.group(2))
    if not out:
        raise ValueError(f'Not a position: {value!r}')
    return out


def matrix(value) -> list[int]:
    """'256x192' / '256 × 192' -> [256, 192]"""
    text = _clean(value)
    parts = re.split(r'\s*[x×*]\s*', text)
    return [int(round(number(p))) for p in parts if p]
