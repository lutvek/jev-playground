import json

import pytest

from benchmark.eval.score import evaluate, format_report, main, resolve_subject, slice_name
from benchmark.schema.validate import validate_prediction, validate_record


def span(text: str, surface: str, **fields) -> dict:
    start = text.index(surface)
    return {"start": start, "end": start + len(surface), **fields}


A = "Erik Lund går i moskén. Han är sjukskriven. Anna Berg är muslim."
B = "Moskén ligger vid torget."
C = "Han har aldrig dömts för stöld."
D = "Karin är med i Kommunal."

GOLD = [
    {
        "id": "a",
        "part": "synthetic",
        "source": {"generator": "modell-a"},
        "text": A,
        "entities": [
            {"id": "P1", "role": "SUBJECT", "mentions": [span(A, "Erik Lund", type="PERSON")]},
            {"id": "P2", "role": "OTHER", "mentions": [span(A, "Anna Berg", type="PERSON")]},
        ],
        "sensitive": [
            span(A, "går i moskén", category="RELIGION", expression="implicit", subject="P1"),
            span(A, "sjukskriven", category="HEALTH", expression="explicit", subject="P1"),
            span(A, "muslim", category="RELIGION", expression="explicit", subject="P2"),
        ],
    },
    {
        "id": "b",
        "part": "synthetic",
        "source": {"generator": "modell-b"},
        "text": B,
        "entities": [],
        "identifiers": [span(B, "torget", type="LOCATION")],
        "sensitive": [],
    },
    {
        "id": "c",
        "part": "redact",
        "source": {"code_switching": "none"},
        "text": C,
        "entities": [],
        "sensitive": [span(C, "stöld", category="CRIMINAL", expression="explicit", subject=None, ignore=True)],
    },
    {
        "id": "d",
        "part": "synthetic",
        "source": {"generator": "modell-a"},
        "text": D,
        "entities": [{"id": "P1", "role": "SUBJECT", "mentions": [span(D, "Karin", type="PERSON")]}],
        "sensitive": [span(D, "Kommunal", category="TRADE_UNION", expression="explicit", subject="P1")],
    },
]

PREDS = {
    "a": {
        "id": "a",
        "sensitive": [
            span(A, "moskén", category="RELIGION", subject="Erik Lund"),
            span(A, "muslim", category="RELIGION", subject="Erik"),
        ],
        "identifiers": [span(A, "Erik", type="PERSON"), span(A, "Lund", type="LOCATION")],
    },
    "b": {"id": "b", "sensitive": [span(B, "Moskén", category="RELIGION")], "identifiers": []},
    "c": {"id": "c", "sensitive": [span(C, "stöld", category="CRIMINAL")], "identifiers": []},
    "d": {"id": "d", "sensitive": [], "identifiers": []},
}


def perfect(gold: list[dict]) -> dict[str, dict]:
    return {
        rec["id"]: {
            "id": rec["id"],
            "sensitive": [
                {"start": s["start"], "end": s["end"], "category": s["category"], "subject": s["subject"]}
                for s in rec["sensitive"]
                if not s.get("ignore")
            ],
            "identifiers": [m for e in rec["entities"] for m in e["mentions"]] + rec.get("identifiers", []),
        }
        for rec in gold
    }


def fractions(report: dict, slice_: str = "alla") -> dict[tuple[str, str, str], tuple[int, int]]:
    return {
        (r["level"], r["label"], r["metric"]): (r["num"], r["den"])
        for r in report["rows"]
        if r["slice"] == slice_ and "den" in r
    }


def values(report: dict, slice_: str = "alla") -> dict[tuple[str, str, str], float]:
    return {(r["level"], r["label"], r["metric"]): r["value"] for r in report["rows"] if r["slice"] == slice_}


def test_fixtures_are_valid():
    assert [validate_record(rec) for rec in GOLD] == [[]] * len(GOLD)
    texts = {rec["id"]: rec["text"] for rec in GOLD}
    assert [validate_prediction(p, texts) for p in PREDS.values()] == [[]] * len(PREDS)


def test_document_level():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert got[("doc", "RELIGION", "recall")] == (1, 1)
    assert got[("doc", "RELIGION", "recall_explicit")] == (1, 1)
    assert got[("doc", "RELIGION", "recall_implicit")] == (1, 1)
    assert got[("doc", "RELIGION", "precision")] == (1, 2)
    assert got[("doc", "HEALTH", "recall")] == (0, 1)
    assert got[("doc", "HEALTH", "recall_explicit")] == (0, 1)
    assert got[("doc", "TRADE_UNION", "recall")] == (0, 1)
    assert got[("doc", "ANY", "recall")] == (1, 2)
    assert got[("doc", "ANY", "precision")] == (1, 2)
    # Inget underlag ger ingen rad: ingen metod flaggade HEALTH, och facit saknar implicit HEALTH.
    assert ("doc", "HEALTH", "precision") not in got
    assert ("doc", "HEALTH", "recall_implicit") not in got


def test_ignore_spans_count_neither_as_hit_nor_as_false_alarm():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert not [key for key in got if key[1] == "CRIMINAL"]
    # Prediktionen på ignore-spannet räknas inte. Kvar är tre prediktioner, varav två är rätt.
    assert got[("span", "ANY", "precision")] == (2, 3)


def test_span_level():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert got[("span", "RELIGION", "recall")] == (2, 2)
    assert got[("span", "RELIGION", "recall_implicit")] == (1, 1)
    assert got[("span", "RELIGION", "recall_explicit")] == (1, 1)
    assert got[("span", "RELIGION", "precision")] == (2, 3)
    assert got[("span", "HEALTH", "recall")] == (0, 1)
    assert got[("span", "ANY", "recall")] == (2, 4)


def test_iou_threshold_requires_tighter_overlap():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0, min_iou=0.9))
    assert got[("span", "RELIGION", "recall")] == (1, 2)
    assert got[("span", "RELIGION", "precision")] == (1, 3)


def test_attribution():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert got[("attribution", "RELIGION", "accuracy")] == (1, 2)
    assert got[("attribution", "RELIGION", "recall_with_subject")] == (1, 2)
    assert got[("attribution", "ANY", "accuracy")] == (1, 2)
    assert got[("attribution", "ANY", "recall_with_subject")] == (1, 4)


def test_identifiers():
    got = fractions(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert got[("identifiers", "PERSON", "recall")] == (1, 3)
    assert got[("identifiers", "PERSON", "precision")] == (1, 1)
    assert got[("identifiers", "LOCATION", "recall")] == (0, 1)
    assert got[("identifiers", "LOCATION", "precision")] == (0, 1)
    assert got[("identifiers", "ANY", "recall")] == (1, 4)
    assert got[("identifiers", "ANY", "precision")] == (2, 2)


def test_macro_is_mean_over_labels_with_support():
    got = values(evaluate(GOLD, PREDS, slices=("",), replicates=0))
    assert got[("doc", "MACRO", "recall")] == pytest.approx(1 / 3, abs=1e-4)
    assert got[("identifiers", "MACRO", "recall")] == pytest.approx((1 / 3 + 0) / 2, abs=1e-4)


def test_levels_without_predictions_are_not_scored():
    doc_only = {rec["id"]: {"id": rec["id"], "categories": ["RELIGION"]} for rec in GOLD}
    report = evaluate(GOLD, doc_only, slices=("",), replicates=0)
    assert {r["level"] for r in report["rows"]} == {"doc"}
    assert fractions(report)[("doc", "RELIGION", "precision")] == (1, 4)

    without_subjects = {i: {**p, "sensitive": [{**s, "subject": None} for s in p["sensitive"]]} for i, p in PREDS.items()}
    report = evaluate(GOLD, without_subjects, slices=("",), replicates=0)
    assert {r["level"] for r in report["rows"]} == {"doc", "span", "identifiers"}


def test_categories_field_overrides_spans_on_document_level():
    preds = {**PREDS, "a": {**PREDS["a"], "categories": ["HEALTH"]}}
    got = fractions(evaluate(GOLD, preds, slices=("",), replicates=0))
    assert got[("doc", "HEALTH", "recall")] == (1, 1)
    assert got[("doc", "RELIGION", "recall")] == (0, 1)
    assert got[("span", "RELIGION", "recall")] == (2, 2)


def test_missing_prediction_counts_as_empty():
    preds = {i: p for i, p in PREDS.items() if i != "a"}
    got = fractions(evaluate(GOLD, preds, slices=("",), replicates=0))
    assert got[("doc", "RELIGION", "recall")] == (0, 1)
    assert got[("span", "ANY", "recall")] == (0, 4)


def test_perfect_predictions_score_one_everywhere():
    report = evaluate(GOLD, perfect(GOLD), slices=("",), replicates=200)
    assert report["rows"]
    for row in report["rows"]:
        assert (row["value"], row["ci_low"], row["ci_high"]) == (1.0, 1.0, 1.0), row


def test_bootstrap_interval_brackets_estimate_and_is_reproducible():
    gold = [{**rec, "id": f"{rec['id']}{i}"} for i in range(25) for rec in GOLD]
    preds = {f"{i_}{i}": {**p, "id": f"{i_}{i}"} for i in range(25) for i_, p in PREDS.items()}
    report = evaluate(gold, preds, slices=("",), replicates=500, seed=1)
    for row in report["rows"]:
        assert row["ci_low"] <= row["value"] <= row["ci_high"], row
    row = next(r for r in report["rows"] if (r["level"], r["label"], r["metric"]) == ("doc", "ANY", "recall"))
    assert row["ci_low"] < row["value"] == 0.5 < row["ci_high"]
    assert report == evaluate(gold, preds, slices=("",), replicates=500, seed=1)


def test_slices():
    assert slice_name(GOLD[0], "part") == "part=synthetic"
    assert slice_name(GOLD[0], "part,source.generator") == "part=synthetic, generator=modell-a"
    assert slice_name(GOLD[2], "part,source.generator") is None
    assert slice_name(GOLD[2], "") == "alla"

    report = evaluate(GOLD, PREDS, replicates=0)
    assert report["slices"] == {
        "part=redact": 1,
        "part=redact, code_switching=none": 1,
        "part=synthetic": 3,
        "part=synthetic, generator=modell-a": 2,
        "part=synthetic, generator=modell-b": 1,
    }
    assert fractions(report, "part=synthetic, generator=modell-b")[("doc", "RELIGION", "precision")] == (0, 1)
    assert fractions(report, "part=synthetic, generator=modell-a")[("doc", "RELIGION", "precision")] == (1, 1)


def test_paired_comparison():
    same = evaluate(GOLD, PREDS, PREDS, slices=("",), replicates=200)
    assert same["comparison"]
    for row in same["comparison"]:
        assert (row["diff"], row["ci_low"], row["ci_high"], row["p"]) == (0.0, 0.0, 0.0, 1.0)

    gold = [{**rec, "id": f"{rec['id']}{i}"} for i in range(25) for rec in GOLD]
    preds = {f"{i_}{i}": {**p, "id": f"{i_}{i}"} for i in range(25) for i_, p in PREDS.items()}
    better = evaluate(gold, perfect(gold), preds, slices=("",), replicates=500)
    row = next(
        r for r in better["comparison"] if (r["level"], r["label"], r["metric"]) == ("doc", "ANY", "recall")
    )
    assert row["value"] == 1.0 and row["baseline"] == 0.5 and row["diff"] == 0.5
    assert 0 < row["ci_low"] <= 0.5 <= row["ci_high"]
    assert row["p"] == 0.0


def test_resolve_subject():
    gold = GOLD[0]
    assert resolve_subject("P2", gold) == "P2"
    assert resolve_subject("subject", gold) == "P1"
    assert resolve_subject("Erik Lund", gold) == "P1"
    assert resolve_subject("lund", gold) == "P1"
    assert resolve_subject("grannen Anna Berg", gold) == "P2"
    assert resolve_subject("Eriksson", gold) is None
    assert resolve_subject("REPORTER", gold) is None
    assert resolve_subject(None, gold) is None

    two_eriks = {
        "text": "Erik Lund och Erik Ek",
        "entities": [
            {"id": "P1", "role": "SUBJECT", "mentions": [{"start": 0, "end": 9, "type": "PERSON"}]},
            {"id": "P2", "role": "SUBJECT", "mentions": [{"start": 14, "end": 21, "type": "PERSON"}]},
        ],
    }
    assert resolve_subject("Erik", two_eriks) is None
    assert resolve_subject("Erik Ek", two_eriks) == "P2"
    assert resolve_subject("SUBJECT", two_eriks) is None


def test_cli(tmp_path, capsys):
    gold_path, pred_path, out_path = tmp_path / "gold.jsonl", tmp_path / "pred.jsonl", tmp_path / "r" / "report.json"
    gold_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in GOLD), encoding="utf-8")
    pred_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in PREDS.values()), encoding="utf-8")

    args = ["--gold", str(gold_path), "--pred", str(pred_path), "--bootstrap", "50"]
    assert main([*args, "--baseline", str(pred_path), "--out", str(out_path)]) == 0
    printed = capsys.readouterr().out
    assert "## part=synthetic (3 dokument)" in printed
    assert "### Dokumentnivå" in printed and "## Jämförelse mot baslinjen" in printed
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert format_report(report) + "\n" == printed

    pred_path.write_text(json.dumps(PREDS["a"], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="prediktion saknas för 3 av 4"):
        main(args)
    assert main([*args, "--allow-missing"]) == 0

    pred_path.write_text(json.dumps({"id": "finns-inte"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="finns inte i facit"):
        main(args)
