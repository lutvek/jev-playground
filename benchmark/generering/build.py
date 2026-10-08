"""Bygger benchmarkposter av LLM-svar och sorterar bort dem som inte klarar kontrollerna.

    python -m benchmark.generering.build --specs benchmark/data/synthetic/pilot.specs.jsonl \\
        --responses benchmark/data/synthetic/pilot.responses.jsonl

Svarsfilen har en rad per försök: {"scenario_id": ..., "generator": ..., "response": ...}.
Ett scenario får ha flera försök, i samma fil eller i flera filer efter --responses. Det första
godkända försöket används och senare försök för samma scenario hoppas över.

Godkända poster skrivs till --out, bortsorterade försök med skäl till <out>.rejected.jsonl och
statistik till <out>.stats.json. Specarna för scenarier som saknar ett godkänt försök skrivs till
<out>.retry.specs.jsonl, så att de kan skickas till modellen igen.
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


def process(spec: dict, response: object, generator: str) -> tuple[dict | None, list[Problem]]:
    """Posten och problemen med den. Posten är None om svaret är tomt eller taggarna inte gick att tolka."""
    if not isinstance(response, str) or not response.strip():
        return None, [Problem("tomt-svar", "svaret är tomt")]
    try:
        record = build_record(spec, response, generator)
    except TagError as e:
        return None, [Problem("taggar", str(e))]
    if errors := validate_record(record):
        return record, [Problem("format", e) for e in errors]
    return record, check(spec, record)


def summarize(specs: dict[str, dict], attempts: list[tuple[str, str, list[Problem]]]) -> dict:
    """Statistik över en omgång. attempts är (scenario_id, generator, problem) per bearbetat försök.

    Andelen bortsorterade räknas per försök och visar hur svår en kategori är att generera.
    Godkända är lika med antalet texter som fick ett godkänt försök.
    """

    def name(fact: dict) -> str:
        return f"{fact['category']} {fact['expression']}"

    def groups(spec: dict, generator: str | None = None) -> list[tuple[str, str]]:
        keys = [("per cell", name(f)) for f in spec["facts"]] or [("per cell", "negativa")]
        keys.append(("per typ", spec["report_type"]))
        if generator is not None:
            keys.append(("per generator", generator))
        return keys

    totals: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for spec in specs.values():
        for key in groups(spec):
            totals[key]["specar"] += 1
    reasons: Counter = Counter()
    for scenario_id, generator, problems in attempts:
        outcome = "bortsorterade" if problems else "godkända"
        reasons.update({p.code for p in problems})
        for key in [("totalt", "")] + groups(specs[scenario_id], generator):
            totals[key]["försök"] += 1
            totals[key][outcome] += 1

    def counts(c: Counter, with_specs: bool = True) -> dict:
        share = round(c["bortsorterade"] / c["försök"], 3) if c["försök"] else None
        result = {"specar": c["specar"]} if with_specs else {}
        return result | {
            "försök": c["försök"],
            "godkända": c["godkända"],
            "bortsorterade": c["bortsorterade"],
            "andel bortsorterade": share,
        }

    answered = {scenario_id for scenario_id, _, _ in attempts}
    cell_names = [f"{c} {e}" for c, e in CELLS] + ["negativa"]
    return {
        "specar": len(specs),
        "utan svar": len(specs.keys() - answered),
        **counts(totals[("totalt", "")], with_specs=False),
        "skäl (antal försök)": dict(reasons.most_common()),
        "per cell": {n: counts(totals[("per cell", n)]) for n in cell_names},
        "per typ": {key: counts(c) for (group, key), c in sorted(totals.items()) if group == "per typ"},
        "per generator": {
            key: counts(c, with_specs=False)
            for (group, key), c in sorted(totals.items())
            if group == "per generator"
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bygg benchmarkposter av LLM-svar och kontrollera dem.")
    parser.add_argument("--specs", type=Path, required=True, help="specar från benchmark.generering.spec")
    parser.add_argument(
        "--responses", type=Path, nargs="+", required=True, help="LLM-svar i en eller flera filer"
    )
    parser.add_argument("--out", type=Path, help="standard: specfilen med .jsonl i stället för .specs.jsonl")
    args = parser.parse_args(argv)

    specs = {spec["scenario_id"]: spec for _, spec in read_jsonl(args.specs)}
    out = args.out or args.specs.with_name(args.specs.name.removesuffix(".specs.jsonl") + ".jsonl")

    accepted: dict[str, dict] = {}
    rejected, attempts, skipped = [], [], 0
    for path in args.responses:
        for lineno, line in read_jsonl(path):
            scenario_id, generator = line.get("scenario_id"), line.get("generator")
            if scenario_id not in specs:
                raise SystemExit(f"{path}:{lineno}: scenario {scenario_id!r} finns inte i {args.specs}")
            if not isinstance(generator, str) or not generator:
                raise SystemExit(f"{path}:{lineno}: generator saknas")
            if scenario_id in accepted:
                skipped += 1
                continue
            record, problems = process(specs[scenario_id], line.get("response"), generator)
            attempts.append((scenario_id, generator, problems))
            if problems:
                problem_list = [{"code": p.code, "message": p.message} for p in problems]
                rejected.append({**line, "file": str(path), "line": lineno, "problems": problem_list})
            else:
                accepted[scenario_id] = record

    # Godkända poster i samma ordning som specarna, oavsett i vilken ordning försöken kom.
    write_jsonl(out, (accepted[i] for i in specs if i in accepted))
    write_jsonl(out.with_suffix(".rejected.jsonl"), rejected)
    retry = [spec for i, spec in specs.items() if i not in accepted]
    write_jsonl(out.with_suffix(".retry.specs.jsonl"), retry)
    summary = summarize(specs, attempts) | {"överflödiga försök": skipped}
    stats = json.dumps(summary, ensure_ascii=False, indent=2)
    out.with_suffix(".stats.json").write_text(stats + "\n", encoding="utf-8")
    print(stats)
    print(
        f"Skrev {len(accepted)} godkända poster till {out}. {len(retry)} scenarier saknar ett godkänt "
        f"försök och står i {out.with_suffix('.retry.specs.jsonl')}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
