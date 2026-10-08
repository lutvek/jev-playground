"""Formatvalidering av benchmarkposter och prediktioner.

    python -m benchmark.schema.validate benchmark/data/redact/redact_sv.jsonl
    python -m benchmark.schema.validate --predictions pred.jsonl --gold benchmark/data/redact/redact_sv.jsonl

JSON-schemat kontrollerar strukturen. Det schemat inte kan uttrycka kontrolleras här:
att spannen ligger inom texten, att id:n är unika och att hänvisningar till personer går att följa.
"""

import argparse
import json
import sys
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from benchmark.jsonl import read_jsonl
from benchmark.schema.labels import SCHEMA_DIR


@cache
def _validator(name: str) -> Draft202012Validator:
    schemas = {
        p.name: json.loads(p.read_text(encoding="utf-8")) for p in SCHEMA_DIR.glob("*.schema.json")
    }
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    return Draft202012Validator(schemas[name], registry=registry)


def _schema_errors(obj: object, schema_name: str) -> list[str]:
    errors = sorted(_validator(schema_name).iter_errors(obj), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(roten)'}: {e.message}" for e in errors]


def _span_errors(span: dict, where: str, text: str | None) -> list[str]:
    start, end = span["start"], span["end"]
    if start >= end:
        return [f"{where}: start ({start}) måste vara mindre än end ({end})"]
    if text is None:
        return []
    if end > len(text):
        return [f"{where}: end ({end}) ligger utanför texten (längd {len(text)})"]
    surface = text[start:end]
    if surface != surface.strip():
        return [f"{where}: spannet börjar eller slutar med blanktecken: {surface!r}"]
    return []


def validate_record(rec: object) -> list[str]:
    """Fel i en benchmarkpost. Tom lista betyder att posten är giltig."""
    errors = _schema_errors(rec, "record.schema.json")
    if errors:
        return errors

    text = rec["text"]
    entity_ids = [e["id"] for e in rec["entities"]]
    for entity_id in {i for i in entity_ids if entity_ids.count(i) > 1}:
        errors.append(f"entities: id {entity_id!r} förekommer flera gånger")

    for i, entity in enumerate(rec["entities"]):
        for j, mention in enumerate(entity["mentions"]):
            errors += _span_errors(mention, f"entities/{i}/mentions/{j}", text)
    for i, span in enumerate(rec.get("identifiers", [])):
        errors += _span_errors(span, f"identifiers/{i}", text)

    for i, span in enumerate(rec["sensitive"]):
        where = f"sensitive/{i}"
        errors += _span_errors(span, where, text)
        if span["subject"] is not None and span["subject"] not in entity_ids:
            errors.append(f"{where}: subject {span['subject']!r} finns inte i entities")
        # I den syntetiska delen kommer etiketterna från konstruktionen och ska därför vara fullständiga.
        if rec["part"] == "synthetic":
            if span["expression"] is None:
                errors.append(f"{where}: expression krävs i den syntetiska delen")
            if span["subject"] is None:
                errors.append(f"{where}: subject krävs i den syntetiska delen")
    return errors


def validate_prediction(pred: object, gold_texts: dict[str, str] | None = None) -> list[str]:
    """Fel i en prediktion. Med gold_texts (id -> text) kontrolleras också id och spann mot facit."""
    errors = _schema_errors(pred, "prediction.schema.json")
    if errors:
        return errors

    text = None
    if gold_texts is not None:
        if pred["id"] not in gold_texts:
            return [f"id {pred['id']!r} finns inte i facit"]
        text = gold_texts[pred["id"]]
    for field in ("sensitive", "identifiers"):
        for i, span in enumerate(pred.get(field, [])):
            errors += _span_errors(span, f"{field}/{i}", text)
    return errors


def validate_file(
    path: str | Path, *, predictions: bool = False, gold_texts: dict[str, str] | None = None
) -> list[str]:
    """Fel i en JSONL-fil, vart och ett med radnummer."""
    errors = []
    seen: dict[str, int] = {}
    try:
        for lineno, obj in read_jsonl(path):
            found = validate_prediction(obj, gold_texts) if predictions else validate_record(obj)
            errors += [f"{path}:{lineno}: {msg}" for msg in found]
            if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                if obj["id"] in seen:
                    errors.append(
                        f"{path}:{lineno}: id {obj['id']!r} finns redan på rad {seen[obj['id']]}"
                    )
                seen.setdefault(obj["id"], lineno)
    except json.JSONDecodeError as e:
        errors.append(f"{path}:{e.lineno}: ogiltig JSON: {e.msg}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validera benchmarkposter eller prediktioner (JSONL).")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--predictions", action="store_true", help="filerna innehåller prediktioner")
    parser.add_argument(
        "--gold", nargs="+", type=Path, default=[], help="facit att kontrollera prediktionerna mot"
    )
    parser.add_argument("--max-errors", type=int, default=50, help="antal fel som skrivs ut per fil")
    args = parser.parse_args(argv)

    gold_texts = None
    if args.gold:
        gold_texts = {rec["id"]: rec["text"] for path in args.gold for _, rec in read_jsonl(path)}

    failed = False
    for path in args.files:
        errors = validate_file(path, predictions=args.predictions, gold_texts=gold_texts)
        if errors:
            failed = True
            for msg in errors[: args.max_errors]:
                print(msg, file=sys.stderr)
            if len(errors) > args.max_errors:
                print(f"... och {len(errors) - args.max_errors} fel till", file=sys.stderr)
            print(f"{path}: {len(errors)} fel", file=sys.stderr)
        else:
            print(f"{path}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
