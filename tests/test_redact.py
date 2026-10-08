from collections import Counter

import pytest

from benchmark.extern.redact import convert, convert_record
from benchmark.schema.validate import validate_record

TEXT = "Anna Berg (850315-4172) är sjukskriven för astma. Hon har aldrig dömts för stöld. Lön: 41 000 kr."


def entity(etype: str, surface: str, disclosed: bool = True, **override) -> dict:
    start = TEXT.index(surface)
    return {
        "entity_type": etype,
        "entity_string": surface,
        "start": start,
        "end": start + len(surface),
        "disclosed": disclosed,
        **override,
    }


def raw_record(entities: list[dict], language: str = "SV", code_switching: str = "none") -> dict:
    return {
        "record_id": 7,
        "text": TEXT,
        "behavioral_frame": "isolation",
        "axes": {
            "language": language,
            "domain": "HR",
            "format": "plain_text",
            "difficulty": "easy",
            "code_switching": code_switching,
        },
        "entities": entities,
    }


def surfaces(spans: list[dict]) -> list[str]:
    return [TEXT[s["start"] : s["end"]] for s in spans]


def test_maps_labels_and_builds_valid_record():
    stats = Counter()
    rec = convert_record(
        42,
        raw_record(
            [
                entity("Full_Name", "Anna Berg"),
                entity("National_Identification_Number", "850315-4172"),
                entity("Sickness_Day_Records", "sjukskriven för astma"),
                entity("Crime", "stöld", disclosed=False),
                entity("Compensation_and_Salary", "41 000 kr"),
            ]
        ),
        stats,
    )
    assert validate_record(rec) == []
    assert rec["id"] == "redact-00042"
    assert rec["source"]["record_id"] == 7
    assert [(TEXT[s["start"] : s["end"]], s["type"]) for s in rec["identifiers"]] == [
        ("Anna Berg", "PERSON"),
        ("850315-4172", "PERSONNUMMER"),
    ]
    health, crime = rec["sensitive"]
    assert health == {**health, "category": "HEALTH", "expression": "explicit", "subject": None}
    assert "ignore" not in health
    assert crime["category"] == "CRIMINAL" and crime["ignore"] is True
    assert stats["omappad: Compensation_and_Salary"] == 1


def test_drops_spans_nested_in_same_label_but_keeps_other_labels():
    stats = Counter()
    rec = convert_record(
        0,
        raw_record(
            [
                entity("First_Given_Name", "Anna"),
                entity("Last_Family_Name", "Berg"),
                entity("Full_Name", "Anna Berg"),
                entity("Sickness_Day_Records", "sjukskriven för astma"),
                entity("Medical_Information", "astma"),
                # Samma kategori men annan ignore-status ska inte slås ihop.
                entity("Allergy_Information", "sjukskriven", disclosed=False),
            ]
        ),
        stats,
    )
    assert surfaces(rec["identifiers"]) == ["Anna Berg"]
    assert [(TEXT[s["start"] : s["end"]], s.get("ignore", False)) for s in rec["sensitive"]] == [
        ("sjukskriven för astma", False),
        ("sjukskriven", True),
    ]
    assert stats["sammanslagna: inuti spann med samma etikett"] == 3


def test_drops_entities_that_are_not_in_the_text():
    stats = Counter()
    rec = convert_record(
        0,
        raw_record(
            [
                entity("Full_Name", "Anna Berg", start=None, end=None),
                entity("Medical_Information", "astma", entity_string="eksem"),
                entity("Crime", "stöld"),
            ]
        ),
        stats,
    )
    assert rec["identifiers"] == []
    assert surfaces(rec["sensitive"]) == ["stöld"]
    assert stats["bortfall: spannet finns inte i texten"] == 2


def test_unknown_entity_type_is_an_error():
    with pytest.raises(ValueError, match="Okänd entitetstyp"):
        convert_record(0, raw_record([entity("Blood_Type", "astma")]), Counter())


def test_convert_filters_language_and_keeps_raw_index_as_id():
    raws = [
        raw_record([], language="DA"),
        raw_record([entity("Medical_Information", "astma")]),
        raw_record([entity("Crime", "stöld", disclosed=False)], code_switching="heavy"),
    ]
    records, summary = convert(raws)
    assert [r["id"] for r in records] == ["redact-00001", "redact-00002"]
    assert summary["alla"]["dokument med känsliga uppgifter"] == 1
    assert summary["alla"]["kategorier"]["CRIMINAL"] == {
        "spann": 0,
        "dokument": 0,
        "dokument med bara ignore-spann": 1,
    }
    assert summary["helt svenska"]["dokument"] == 1
