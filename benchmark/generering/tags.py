"""Tolkning av LLM:ens taggar till spann.

    Han <RELIGION implicit P1>går i moskén</RELIGION>.  ->  "Han går i moskén." och spannet (4, 16)

En tagg är <ETIKETT attribut ...>…</ETIKETT>, där ETIKETT är en känslig kategori eller en
identifierartyp, med versaler eller gemener. Känsliga kategorier tar uttryckstyp och person, i
valfri ordning. Identifierare tar valfritt en person. Taggar får ligga inuti varandra men inte
korsa varandra. Allt annat som ser ut som en tagg, till exempel <br>, är ett fel.
"""

import re
from dataclasses import dataclass

from benchmark.schema.labels import CATEGORIES, EXPRESSIONS, IDENTIFIER_TYPES

TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z_]*)([^<>]*)>")
PERSON_ID = re.compile(r"P\d+")


class TagError(ValueError):
    """Taggarna går inte att tolka."""


@dataclass(frozen=True)
class TaggedSpan:
    start: int
    end: int
    label: str
    expression: str | None = None
    person: str | None = None


def _attributes(label: str, tag: str, attrs: list[str]) -> tuple[str | None, str | None]:
    expressions = [a.casefold() for a in attrs if a.casefold() in EXPRESSIONS]
    persons = [a.upper() for a in attrs if PERSON_ID.fullmatch(a.upper())]
    if len(expressions) + len(persons) != len(attrs) or len(expressions) > 1 or len(persons) > 1:
        raise TagError(f"{tag}: okända eller dubbla attribut")
    if label in CATEGORIES and not (expressions and persons):
        raise TagError(f"{tag}: en känslig uppgift behöver både uttryckstyp och person")
    if label in IDENTIFIER_TYPES and expressions:
        raise TagError(f"{tag}: en identifierare har ingen uttryckstyp")
    return (expressions or [None])[0], (persons or [None])[0]


def parse(tagged: str) -> tuple[str, list[TaggedSpan]]:
    """Ger texten utan taggar och spannen, sorterade på start. Blanktecken i kanten av en tagg
    hamnar utanför spannet."""
    pieces: list[str] = []
    length = last = 0
    stack: list[tuple[str, str, str | None, str | None, int]] = []
    raw: list[tuple[str, str | None, str | None, int, int]] = []

    for m in TAG.finditer(tagged):
        piece = tagged[last : m.start()]
        pieces.append(piece)
        length += len(piece)
        last = m.end()

        tag, closing, label, attrs = m.group(), m.group(1) == "/", m.group(2).upper(), m.group(3).split()
        if label not in CATEGORIES and label not in IDENTIFIER_TYPES:
            raise TagError(f"okänd tagg {tag}")
        if not closing:
            expression, person = _attributes(label, tag, attrs)
            stack.append((label, tag, expression, person, length))
            continue
        if attrs:
            raise TagError(f"sluttaggen {tag} har attribut")
        if not stack:
            raise TagError(f"{tag} saknar starttagg")
        open_label, open_tag, expression, person, start = stack.pop()
        if open_label != label:
            raise TagError(f"{tag} stänger {open_tag}")
        raw.append((label, expression, person, start, length))

    if stack:
        raise TagError(f"{stack[-1][1]} stängs aldrig")
    pieces.append(tagged[last:])
    text = "".join(pieces)

    spans = []
    for label, expression, person, start, end in raw:
        surface = text[start:end]
        start += len(surface) - len(surface.lstrip())
        end -= len(surface) - len(surface.rstrip())
        if start >= end:
            raise TagError(f"<{label}> är tom")
        spans.append(TaggedSpan(start, end, label, expression, person))
    return text, sorted(spans, key=lambda s: (s.start, -s.end))
