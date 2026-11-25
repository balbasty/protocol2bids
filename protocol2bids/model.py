"""
Vendor-agnostic representation of a parsed protocol.

A `Protocol` is a flat list of `Entry` objects. Each entry knows which
card (tab), sub-card and group it belongs to. Lookups are tolerant to the
many ways vendors and software versions name the same parameter
(case, abbreviations, card renames) through `normalize_key` and a
synonyms table.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator


class Missing(KeyError):
    """Raised when a protocol parameter is not available."""


_MISSING = object()


# ----------------------------------------------------------------------
#   Key normalisation
# ----------------------------------------------------------------------

# Each tuple lists names that refer to the same parameter. The first
# element is the canonical (normalised) name.
SYNONYMS: list[tuple[str, ...]] = [
    ('dist. factor', 'distance factor'),
    ('phase enc. dir.', 'phase encoding dir.', 'phase encoding direction'),
    ('accel. factor pe', 'acceleration factor pe'),
    ('accel. factor 3d', 'acceleration factor 3d', 'accel. factor slice',
     'acceleration factor slice'),
    ('pat mode', 'acceleration mode'),
    ('ref. lines pe', 'reference lines pe'),
    ('ref. lines 3d', 'reference lines 3d'),
    ('multi-band accel. factor', 'multi-band acceleration factor',
     'slice accel. factor', 'slice acceleration factor', 'mb factor'),
    ('epi factor',),
    ('turbo factor',),
    ('flow comp.', 'flow compensation'),
    ('fat suppr.', 'fat suppression'),
    ('water suppr.', 'water suppression'),
    ('magn. preparation', 'magnetization preparation'),
    ('rf spoiling',),
    ('coil combine mode', 'coil combination', 'coil combination mode'),
    ('frequency 1h', 'frequency'),
    ('distortion corr.', 'distortion correction'),
    ('multi-slice mode', 'multi slice mode'),
    ('ref. amplitude 1h', 'reference amplitude 1h'),
    ('free echo spacing',),
]

_SYNONYM_MAP: dict[str, str] = {}
for group in SYNONYMS:
    for name in group:
        _SYNONYM_MAP[name] = group[0]


def normalize_key(key: str) -> str:
    """Normalise a parameter name for matching."""
    key = key.replace(' ', ' ').strip().casefold()
    key = re.sub(r'\s+', ' ', key)
    key = key.rstrip(':').strip()
    return _SYNONYM_MAP.get(key, key)


def normalize_card(card: str) -> str:
    card = card.replace(' ', ' ').strip().casefold()
    return re.sub(r'\s*-\s*', ' - ', re.sub(r'\s+', ' ', card))


# ----------------------------------------------------------------------
#   Data model
# ----------------------------------------------------------------------

@dataclass
class Entry:
    key: str
    value: str | None = None
    card: str | None = None
    subcard: str | None = None
    group: tuple[str, ...] = ()
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    @property
    def nkey(self) -> str:
        return normalize_key(self.key)

    @property
    def ncard(self) -> str:
        return normalize_card(self.card or '')

    def to_list(self) -> list:
        return [self.card, self.subcard, list(self.group), self.key,
                self.value]

    def __repr__(self) -> str:
        loc = '/'.join(x for x in (self.card, self.subcard, *self.group)
                       if x)
        return f'Entry({loc}//{self.key} = {self.value!r})'


@dataclass
class Protocol:
    name: str = ''
    path: str = ''
    header: dict[str, Any] = field(default_factory=dict)
    scanner: dict[str, Any] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    vendor: str = ''
    format: str = ''

    # ------------------------------------------------------------------
    #   Lookup
    # ------------------------------------------------------------------
    def find(
        self,
        key: str,
        card: str | Iterable[str] | None = None,
        group: str | None = None,
    ) -> Iterator[Entry]:
        """
        Iterate over all entries matching a key.

        Parameters
        ----------
        key : str
            Parameter name (case-insensitive, synonyms allowed).
            Glob patterns are accepted.
        card : str or list[str], optional
            Card name prefix(es), e.g. "Resolution" matches
            "Resolution", "Resolution - Common", "Resolution - iPAT".
        group : str, optional
            Group name prefix ("Slice group" matches "Slice group 1").
            If None, entries from any group (or no group) match.
            Use "" to only match entries outside of any group.
        """
        nkey = normalize_key(key)
        is_glob = any(c in nkey for c in '*?[')
        if isinstance(card, str):
            card = [card]
        cards = [normalize_card(c) for c in card] if card else None
        ngroup = normalize_key(group) if group else group
        for entry in self.entries:
            ekey = entry.nkey
            if is_glob:
                if not fnmatch.fnmatchcase(ekey, nkey):
                    continue
            elif ekey != nkey:
                continue
            if cards is not None:
                ecard = entry.ncard
                if not any(ecard == c or ecard.startswith(c + ' ')
                           for c in cards):
                    continue
            if ngroup is not None:
                if ngroup == '':
                    if entry.group:
                        continue
                elif not entry.group or not normalize_key(
                        entry.group[0]).startswith(ngroup):
                    continue
            yield entry

    def get(
        self,
        key: str,
        card: str | Iterable[str] | None = None,
        group: str | None = None,
        default: Any = _MISSING,
    ) -> str | None:
        """
        Return the value of the first entry matching a key.
        Entries outside of groups are preferred over grouped entries,
        and the first group is preferred over others.
        """
        entries = list(self.find(key, card, group))
        if entries and group is None:
            ungrouped = [e for e in entries if not e.group]
            entries = ungrouped or entries
        if not entries:
            if default is _MISSING:
                where = f' (card={card})' if card else ''
                raise Missing(f'{key}{where}')
            return default
        return entries[0].value

    def getall(self, key: str, card=None, group=None) -> list[str | None]:
        return [e.value for e in self.find(key, card, group)]

    def has(self, key: str, card=None, group=None) -> bool:
        return next(iter(self.find(key, card, group)), None) is not None

    @property
    def cards(self) -> list[str]:
        seen = []
        for e in self.entries:
            if e.card not in seen:
                seen.append(e.card)
        return seen

    # ------------------------------------------------------------------
    #   Export
    # ------------------------------------------------------------------
    def tree(self) -> dict:
        """
        Nested dictionary representation:
        {card: {key: value, group: {key: value}}}.
        Sub-cards are merged into the card name ("Resolution - Common").
        Duplicated keys are turned into lists.
        """
        out: dict = {}
        for e in self.entries:
            card = e.card or ''
            if e.subcard:
                card = f'{card} - {e.subcard}'
            node = out.setdefault(card, {})
            for g in e.group:
                child = node.get(g)
                if not isinstance(child, dict):
                    child = {} if child is None else {'': child}
                    node[g] = child
                node = child
            if e.key in node:
                if isinstance(node[e.key], dict):
                    node[e.key][''] = e.value
                    continue
                if not isinstance(node[e.key], list):
                    node[e.key] = [node[e.key]]
                node[e.key].append(e.value)
            else:
                node[e.key] = e.value
        return out

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'path': self.path,
            'vendor': self.vendor,
            'format': self.format,
            'scanner': self.scanner,
            'header': self.header,
            'pages': self.pages,
            'parameters': self.tree(),
        }

    def __repr__(self) -> str:
        return (f'Protocol({self.path or self.name!r}, '
                f'{len(self.entries)} entries)')
