"""Bygger benchmarkposter av LLM-svar och sorterar bort dem som inte klarar kontrollerna.

    python -m benchmark.generering.build --specs benchmark/data/synthetic/pilot.specs.jsonl \\
        --responses benchmark/data/synthetic/pilot.responses.jsonl

Svarsfilen har en rad per text: {"scenario_id": ..., "generator": ..., "response": ...}.
Godkända poster skrivs till --out, bortsorterade med skäl till <out>.rejected.jsonl och
statistik till <out>.stats.json.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from benchmark.generering.checks import Problem, check
from benchmark.generering.spec import CELLS
from benchmark.generering.tags import TagError, parse
from benchmark.jsonl import read_jsonl, write_jsonl
from benchmark.schema.labels import CATEGORIES
from benchmark.schema.validate import validate_record

FENCE = re.compile(r"```[^\n]*\n(.*)\n```", re.DOTALL)


def normalize_response(response: str) -> str:
    """Tar bort blanktecken runt svaret och ett kodblock runt hela svaret."""
    text = response.strip()
    if fence := FENCE.fullmatch(text):
        text = fence.group(1).strip()
    return text


def build_record(spec: dict, response: str, generator: str) -> dict:
    """Posten som svaret ger. Kastar TagError om taggarna inte går att tolka."""
    text, spans = parse(normalize_response(response))
    person_ids = [p["id"] for p in spec["persons"]]
    for span in spans:
        if span.person is not None and span.person not in person_ids:
            raise TagError(f"<{span.label}> gäller {span.person}, som inte finns i specen")

    record = {"id": f"syn-{spec['scenario_id']}", "part": "synthetic"}
    if "split" in spec:
        record["split"] = spec["split"]
    record |= {
        "source": {
            "generator": generator,
            "scenario_id": spec["scenario_id"],
            "report_type": spec["report_type"],
            "placeholders": spec["placeholders"],
        },
        "text": text,
        "entities": [
            {
                "id": p["id"],
                "role": p["role"],
                "mentions": [
                    {"start": s.start, "end": s.end, "type": s.label}
                    for s in spans
                    if s.person == p["id"] and s.label not in CATEGORIES
                ],
            }
            for p in spec["persons"]
        ],
        "identifiers": [
            {"start": s.start, "end": s.end, "type": s.label}
            for s in spans
            if s.person is None and s.label not in CATEGORIES
        ],
        "sensitive": [
            {
                "start": s.start,
                "end": s.end,
                "category": s.label,
                "expression": s.expression,
                "subject": s.person,
            }
            for s in spans
            if s.label in CATEGORIES
        ],
    }
    return record


def process(spec: dict, response: str, generator: str) -> tuple[dict | None, list[Problem]]:
    """Posten och problemen med den. Posten är None om taggarna inte gick att tolka."""
    try:
        record = build_record(spec, response, generator)
    except TagError as e:
        return None, [Problem("taggar", str(e))]
    if errors := validate_record(record):
        return record, [Problem("format", e) for e in errors]
    return record, check(spec, record)


def summarize(specs: dict[str, dict], results: list[tuple[str, str, list[Problem]]]) -> dict:
    """Statistik över en omgång. results är (scenario_id, generator, problem) per svar."""
    answered = {scenario_id for scenario_id, _, _ in results}
    reasons: Counter = Counter()
    cells: dict[str, Counter] = defaultdict(Counter)
    generators: dict[str, Counter] = defaultdict(Counter)
    for scenario_id, generator, problems in results:
        outcome = "bortsorterade" if problems else "godkända"
        reasons.update({p.code for p in problems})
        generators[generator][outcome] += 1
        facts = specs[scenario_id]["facts"]
        for name in [f"{f['category']} {f['expression']}" for f in facts] or ["negativa"]:
            cells[name][outcome] += 1

    def counts(c: Counter) -> dict:
        total = c["godkända"] + c["bortsorterade"]
        share = round(c["bortsorterade"] / total, 3) if total else None
        return {"godkända": c["godkända"], "bortsorterade": c["bortsorterade"], "andel bortsorterade": share}

    return {
        "specar": len(specs),
        "utan svar": len(specs.keys() - answered),
        **counts(sum(generators.values(), Counter())),
        "skäl (antal texter)": dict(reasons.most_common()),
        "per cell": {name: counts(cells[name]) for name in [f"{c} {e}" for c, e in CELLS] + ["negativa"]},
        "per generator": {g: counts(c) for g, c in sorted(generators.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bygg benchmarkposter av LLM-svar och kontrollera dem.")
    parser.add_argument("--specs", type=Path, required=True, help="specar från benchmark.generering.spec")
    parser.add_argument("--responses", type=Path, required=True, help="LLM-svar, en rad per text")
    parser.add_argument("--out", type=Path, help="standard: specfilen med .jsonl i stället för .specs.jsonl")
    args = parser.parse_args(argv)

    specs = {spec["scenario_id"]: spec for _, spec in read_jsonl(args.specs)}
    out = args.out or args.specs.with_name(args.specs.name.removesuffix(".specs.jsonl") + ".jsonl")

    accepted, rejected, results, seen = [], [], [], set()
    for lineno, line in read_jsonl(args.responses):
        scenario_id = line["scenario_id"]
        if scenario_id not in specs:
            raise SystemExit(f"{args.responses}:{lineno}: scenario {scenario_id!r} finns inte i {args.specs}")
        if scenario_id in seen:
            raise SystemExit(f"{args.responses}:{lineno}: scenario {scenario_id!r} har redan ett svar")
        seen.add(scenario_id)
        record, problems = process(specs[scenario_id], line["response"], line["generator"])
        results.append((scenario_id, line["generator"], problems))
        if problems:
            rejected.append({**line, "problems": [{"code": p.code, "message": p.message} for p in problems]})
        else:
            accepted.append(record)

    write_jsonl(out, accepted)
    write_jsonl(out.with_suffix(".rejected.jsonl"), rejected)
    summary = summarize(specs, results)
    stats = json.dumps(summary, ensure_ascii=False, indent=2)
    out.with_suffix(".stats.json").write_text(stats + "\n", encoding="utf-8")
    print(stats)
    print(f"Skrev {len(accepted)} godkända poster till {out}, {len(rejected)} bortsorterade", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
