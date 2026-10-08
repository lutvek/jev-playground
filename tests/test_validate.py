import copy
import json

import pytest

from benchmark.schema.validate import validate_file, validate_prediction, validate_record

TEXT = (
    "Jag skriver angående min granne Erik Lund. Han går i moskén varje fredag "
    "men har sedan i våras slutat äta och verkar mycket nedstämd."
)


def span(surface: str, **fields) -> dict:
    start = TEXT.index(surface)
    return {"start": start, "end": start + len(surface), **fields}


@pytest.fixture
def record() -> dict:
    return {
        "id": "syn-000123",
        "part": "synthetic",
        "source": {"generator": "modell-a", "scenario_id": "scn-0042"},
        "text": TEXT,
        "entities": [
            {"id": "P0", "role": "REPORTER", "mentions": []},
            {"id": "P1", "role": "SUBJECT", "mentions": [span("Erik Lund", type="PERSON")]},
        ],
        "sensitive": [
            span("går i moskén varje fredag", category="RELIGION", expression="implicit", subject="P1"),
            span("slutat äta och verkar mycket nedstämd", category="HEALTH", expression="implicit", subject="P1"),
        ],
    }


def test_valid_record(record):
    assert validate_record(record) == []


def test_identifiers_and_ignore_are_optional_fields(record):
    record["identifiers"] = [span("fredag", type="DATE")]
    record["sensitive"][0]["ignore"] = True
    assert validate_record(record) == []


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda r: r.pop("text"), "'text' is a required property"),
        (lambda r: r.update(part="annat"), "is not one of"),
        (lambda r: r["sensitive"][0].update(category="RELIGON"), "is not one of"),
        (lambda r: r["sensitive"][0].update(end=len(TEXT) + 1), "utanför texten"),
        (lambda r: r["sensitive"][0].update(end=r["sensitive"][0]["start"]), "mindre än end"),
        (lambda r: r["sensitive"][0].update(start=r["sensitive"][0]["start"] - 1), "blanktecken"),
        (lambda r: r["sensitive"][0].update(subject="P7"), "finns inte i entities"),
        (lambda r: r["sensitive"][0].update(expression=None), "expression krävs"),
        (lambda r: r["sensitive"][0].update(subject=None), "subject krävs"),
        (lambda r: r["entities"].append(copy.deepcopy(r["entities"][1])), "flera gånger"),
        (lambda r: r["entities"][1]["mentions"][0].update(type="NAMN"), "is not one of"),
    ],
)
def test_invalid_record(record, mutate, expected):
    mutate(record)
    errors = validate_record(record)
    assert any(expected in e for e in errors), errors


def test_external_parts_may_lack_expression_and_subject(record):
    record["part"] = "redact"
    record["entities"] = []
    for s in record["sensitive"]:
        s["expression"] = None
        s["subject"] = None
    assert validate_record(record) == []


def test_prediction():
    pred = {"id": "a", "categories": ["HEALTH"], "sensitive": [{"start": 0, "end": 3, "category": "HEALTH"}]}
    assert validate_prediction(pred, {"a": "sjuk igen"}) == []
    assert validate_prediction({"id": "a"}, {"a": "sjuk igen"}) == []
    assert "finns inte i facit" in validate_prediction(pred, {"b": "sjuk igen"})[0]
    assert "utanför texten" in validate_prediction(pred, {"a": "sj"})[0]
    assert validate_prediction({"id": "a", "categories": ["SJUK"]})


def test_file_reports_line_numbers_and_duplicate_ids(tmp_path, record):
    broken = copy.deepcopy(record)
    broken["sensitive"][0]["subject"] = "P7"
    path = tmp_path / "data.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in (record, broken)) + "\n", encoding="utf-8")
    errors = validate_file(path)
    assert len(errors) == 2
    assert all(e.startswith(f"{path}:2: ") for e in errors)
    assert any("finns redan på rad 1" in e for e in errors)
