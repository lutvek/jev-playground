"""Automatiska kontroller av en genererad text mot sin spec.

Motsvarar kontroll 1 och 2 i avsnitt 5 i PLAN_BENCHMARK.md: att alla uppgifter i specen finns med
och är rätt märkta, och att implicita uttryck inte namnger sin kategori. Kontroll 3, verifiering
med en LLM från en annan modellfamilj, kräver en modell och ligger inte här.

Formatet kontrolleras separat med benchmark.schema.validate.
"""

import re
from dataclasses import dataclass

from benchmark.generering.categories import forbidden_matches
from benchmark.schema.labels import CATEGORIES

# Personnummer med eller utan sekel och bindestreck.
PERSONNUMMER = re.compile(r"(?<!\d)(?:\d{2})?\d{6}[-+]?\d{4}(?!\d)")


@dataclass(frozen=True)
class Problem:
    code: str
    message: str


def _covered(start: int, end: int, spans: list[dict]) -> bool:
    return any(s["start"] <= start and end <= s["end"] for s in spans)


def _identifier_spans(record: dict) -> list[dict]:
    """Alla identifierare, både personers omnämnanden och de som inte är knutna till en person."""
    return [m for e in record["entities"] for m in e["mentions"]] + record["identifiers"]


def _mentions(record: dict, kind: str) -> dict[str, list[dict]]:
    return {e["id"]: [m for m in e["mentions"] if m["type"] == kind] for e in record["entities"]}


def _facts(spec: dict, record: dict) -> list[Problem]:
    wanted = {(f["category"], f["expression"], f["subject"]) for f in spec["facts"]}
    found = {(s["category"], s["expression"], s["subject"]) for s in record["sensitive"]}
    problems = []
    for c, e, p in sorted(wanted - found):
        problems.append(Problem("saknad-uppgift", f"{c} {e} om {p} är inte märkt"))
    for c, e, p in sorted(found - wanted):
        problems.append(Problem("oväntad-uppgift", f"{c} {e} om {p} finns inte i specen"))
    return problems


def _category_words(spec: dict, record: dict) -> list[Problem]:
    """Ord som namnger en kategori får bara stå i explicita spann.

    I ett implicit spann i samma kategori är de förbjudna. Utanför de explicita spannen tyder de
    på en uppgift som LLM:en har skrivit men inte märkt. Ett explicit spann i en annan kategori
    räcker, eftersom ord som "sexualbrott" och "judisk" hör till två kategorier. Ord med andra
    vanliga betydelser, som "hälsa på", räknas bara i implicita spann. Undantaget är
    distraktorerna i negativa texter, som ska likna kategorin utan att avslöja något.
    """
    text, problems = record["text"], []
    explicit = [s for s in record["sensitive"] if s["expression"] == "explicit"]
    for category in CATEGORIES:
        if category in spec["distractors"]:
            continue
        implicit = [s for s in record["sensitive"] if s["category"] == category and s not in explicit]
        unambiguous = set(forbidden_matches(category, text, ambiguous=False))
        for start, end in forbidden_matches(category, text):
            word = text[start:end]
            if _covered(start, end, implicit):
                problems.append(Problem("förbjudet-ord", f"{word!r} namnger {category} i ett implicit spann"))
            elif (start, end) in unambiguous and not _covered(start, end, explicit):
                message = f"{word!r} namnger {category} men står utanför de explicita spannen"
                problems.append(Problem("omärkt-kategoriord", message))
    return problems


def _name_part(token: str, names: set[str]) -> str:
    """Namnet utan genitiv-s, om token är ett av namnen."""
    if token not in names and token.endswith("s") and token[:-1] in names:
        return token[:-1]
    return token


def _names(spec: dict, record: dict) -> list[Problem]:
    text, problems = record["text"], []
    mentions = _mentions(record, "PERSON")

    for person in spec["persons"]:
        pid, name, found = person["id"], person["name"], mentions[person["id"]]
        if not name:
            if found:
                problems.append(Problem("fel-namn", f"{pid} har inget namn i specen men är märkt som namn"))
            continue
        if not found:
            problems.append(Problem("namn-saknas", f"namnet på {pid}, {name}, står inte i texten"))
        parts = set(name.split())
        for m in found:
            surface = text[m["start"] : m["end"]]
            if not any(_name_part(t, parts) in parts for t in re.findall(r"\w+", surface)):
                problems.append(Problem("fel-namn", f"{surface!r} är märkt som {pid}, som heter {name}"))

    # Namnen ur specen måste vara märkta där de står. Andra identifierare räknas också som
    # märkning, så att efternamnet i till exempel en gatuadress inte ger falsklarm.
    all_parts = {part for p in spec["persons"] if p["name"] for part in p["name"].split()}
    marked = _identifier_spans(record)
    for m in re.finditer(r"\w+", text):
        part = _name_part(m.group(), all_parts)
        # Genitiv-s får stå utanför taggen: <PERSON P1>Erik</PERSON>s.
        if part in all_parts and not _covered(m.start(), m.start() + len(part), marked):
            problems.append(Problem("omärkt-namn", f"{m.group()!r} på position {m.start()} är inte märkt"))
    return problems


def _personnummer(spec: dict, record: dict) -> list[Problem]:
    text, problems = record["text"], []
    mentions = _mentions(record, "PERSONNUMMER")

    for person in spec["persons"]:
        pid, found = person["id"], mentions[person["id"]]
        if not person["personnummer"]:
            if found:
                problems.append(Problem("personnummer", f"{pid} har inget personnummer i specen"))
            continue
        if not found:
            problems.append(Problem("personnummer", f"personnumret för {pid} är inte märkt"))
        wanted = re.sub(r"\D", "", person["personnummer"])
        for m in found:
            surface = text[m["start"] : m["end"]]
            if re.sub(r"\D", "", surface)[-10:] != wanted:
                problems.append(Problem("personnummer", f"{surface!r} är inte personnumret för {pid}"))

    # Ett nummer som är märkt som en annan identifierare, till exempel ett ärendenummer, är märkt.
    marked = _identifier_spans(record)
    for m in PERSONNUMMER.finditer(text):
        if not _covered(m.start(), m.end(), marked):
            problems.append(Problem("personnummer", f"{m.group()!r} är inte märkt som personnummer"))
    return problems


def check(spec: dict, record: dict) -> list[Problem]:
    """Problemen med en post byggd från spec. Tom lista betyder att posten godkänns."""
    return [
        *_facts(spec, record),
        *_category_words(spec, record),
        *_names(spec, record),
        *_personnummer(spec, record),
    ]
