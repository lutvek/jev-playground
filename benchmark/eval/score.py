"""Poängsättning av en metods prediktioner mot facit.

    python -m benchmark.eval.score --gold benchmark/data/redact/redact_sv.jsonl --pred pred.jsonl
    python -m benchmark.eval.score --gold ... --pred ny.jsonl --baseline gammal.jsonl

Nivåer:

    doc           finns kategorin i texten? Primärt mått är recall, uppdelat på explicit och implicit.
    span          var står uppgiften? Ett spann är hittat om en prediktion med samma kategori överlappar det.
    attribution   gäller uppgiften rätt person? Bara där facit anger vem.
    identifiers   namn, personnummer med mera, per typ.

En nivå poängsätts bara om metoden har lämnat de fält som behövs. Alla mått är kvoter av summor
över dokument, och konfidensintervallen kommer från bootstrap över dokument.
"""

import argparse
import json
import re
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from benchmark.jsonl import read_jsonl
from benchmark.schema.labels import CATEGORIES, EXPRESSIONS, IDENTIFIER_TYPES, ROLES
from benchmark.schema.validate import validate_prediction

# Rader utöver de enskilda etiketterna.
ANY = "ANY"  # något känsligt över huvud taget, oavsett kategori (ren detektion)
MACRO = "MACRO"  # medelvärde över de etiketter som förekommer i facit

DEFAULT_SLICES = ("part", "part,source.generator", "part,source.code_switching")

Key = tuple[str, str, str]  # (nivå, etikett, mått)


def _overlaps(a: dict, b: dict, min_iou: float = 0.0) -> bool:
    intersection = min(a["end"], b["end"]) - max(a["start"], b["start"])
    if intersection <= 0:
        return False
    union = max(a["end"], b["end"]) - min(a["start"], b["start"])
    return intersection / union >= min_iou


def _tokens(s: str) -> list[str]:
    return re.findall(r"\w+", s.casefold())


def _contains(haystack: list[str], needle: list[str]) -> bool:
    return any(haystack[i : i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1))


def resolve_subject(subject: str | None, gold: dict) -> str | None:
    """Översätter en prediktions subject till ett person-id i facit.

    Godtar ett person-id, en roll som bara en person har, eller ett namn som matchar exakt en
    persons omnämnanden. Allt annat, även tvetydiga namn, ger None.
    """
    if not subject:
        return None
    entities = gold["entities"]
    if any(e["id"] == subject for e in entities):
        return subject
    if subject.upper() in ROLES:
        with_role = [e["id"] for e in entities if e["role"] == subject.upper()]
        return with_role[0] if len(with_role) == 1 else None

    wanted = _tokens(subject)
    if not wanted:
        return None
    matches = set()
    for entity in entities:
        for mention in entity["mentions"]:
            if mention["type"] != "PERSON":
                continue
            surface = _tokens(gold["text"][mention["start"] : mention["end"]])
            if surface and (_contains(surface, wanted) or _contains(wanted, surface)):
                matches.add(entity["id"])
    return matches.pop() if len(matches) == 1 else None


def _span_counts(
    gold: list[dict], ignored: list[dict], pred: list[dict], min_iou: float
) -> tuple[list[bool], int, int]:
    """Ger (hittad per facitspann, antal korrekta prediktioner, antal räknade prediktioner).

    En prediktion som bara träffar ett ignore-spann räknas inte alls.
    """
    found = [any(_overlaps(g, p, min_iou) for p in pred) for g in gold]
    correct = counted = 0
    for p in pred:
        if any(_overlaps(g, p, min_iou) for g in gold):
            correct += 1
            counted += 1
        elif not any(_overlaps(i, p) for i in ignored):
            counted += 1
    return found, correct, counted


@dataclass
class Counts:
    """Täljare och nämnare per dokument för varje mått."""

    keys: list[Key]
    num: np.ndarray  # dokument x mått
    den: np.ndarray


def count(gold: list[dict], preds: dict[str, dict], min_iou: float = 0.0) -> Counts:
    """Räknar täljare och nämnare per dokument för alla mått som prediktionerna stöder."""
    has_spans = any("sensitive" in p for p in preds.values())
    has_subjects = any(s.get("subject") for p in preds.values() for s in p.get("sensitive", []))
    has_identifiers = any("identifiers" in p for p in preds.values())

    cells: dict[Key, list[np.ndarray]] = defaultdict(lambda: [np.zeros(len(gold)), np.zeros(len(gold))])

    def add(d: int, level: str, label: str, metric: str, num: float, den: float) -> None:
        cell = cells[(level, label, metric)]
        cell[0][d] += num
        cell[1][d] += den

    for d, rec in enumerate(gold):
        pred = preds.get(rec["id"], {"id": rec["id"]})
        pred_spans = pred.get("sensitive", [])
        pred_categories = set(pred.get("categories", {s["category"] for s in pred_spans}))
        scored = [s for s in rec["sensitive"] if not s.get("ignore")]
        ignored = [s for s in rec["sensitive"] if s.get("ignore")]

        # Dokumentnivå. Ett dokument där kategorin bara finns i ignore-spann räknas inte för den kategorin.
        for label in (*CATEGORIES, ANY):
            in_label = (lambda s: True) if label == ANY else (lambda s: s["category"] == label)
            positive = any(in_label(s) for s in scored)
            if not positive and any(in_label(s) for s in ignored):
                continue
            predicted = bool(pred_categories) if label == ANY else label in pred_categories
            add(d, "doc", label, "recall", positive and predicted, positive)
            add(d, "doc", label, "precision", positive and predicted, predicted)
            for expression in EXPRESSIONS:
                has = any(in_label(s) and s["expression"] == expression for s in scored)
                add(d, "doc", label, f"recall_{expression}", has and predicted, has)

        if has_spans:
            for label in (*CATEGORIES, ANY):
                in_label = (lambda s: True) if label == ANY else (lambda s: s["category"] == label)
                g = [s for s in scored if in_label(s)]
                p = [s for s in pred_spans if in_label(s)]
                found, correct, counted = _span_counts(g, [s for s in ignored if in_label(s)], p, min_iou)
                add(d, "span", label, "recall", sum(found), len(g))
                add(d, "span", label, "precision", correct, counted)
                for expression in EXPRESSIONS:
                    hits = [f for f, s in zip(found, g) if s["expression"] == expression]
                    add(d, "span", label, f"recall_{expression}", sum(hits), len(hits))

        if has_subjects:
            for s in scored:
                if s["subject"] is None:
                    continue
                matching = [
                    p for p in pred_spans if p["category"] == s["category"] and _overlaps(s, p, min_iou)
                ]
                right = any(resolve_subject(p.get("subject"), rec) == s["subject"] for p in matching)
                for label in (s["category"], ANY):
                    # accuracy: rätt person bland de hittade. recall_with_subject: hittad och rätt person.
                    add(d, "attribution", label, "accuracy", right, bool(matching))
                    add(d, "attribution", label, "recall_with_subject", right, 1)

        if has_identifiers:
            gold_ids = [m for e in rec["entities"] for m in e["mentions"]] + rec.get("identifiers", [])
            pred_ids = pred.get("identifiers", [])
            for label in (*IDENTIFIER_TYPES, ANY):
                in_label = (lambda s: True) if label == ANY else (lambda s: s["type"] == label)
                g = [s for s in gold_ids if in_label(s)]
                found, correct, counted = _span_counts(g, [], [s for s in pred_ids if in_label(s)], min_iou)
                add(d, "identifiers", label, "recall", sum(found), len(g))
                add(d, "identifiers", label, "precision", correct, counted)

    keys = list(cells)
    if not keys:
        return Counts([], np.zeros((len(gold), 0)), np.zeros((len(gold), 0)))
    return Counts(
        keys,
        np.stack([cells[k][0] for k in keys], axis=1),
        np.stack([cells[k][1] for k in keys], axis=1),
    )


def _ratios(num: np.ndarray, den: np.ndarray, keys: list[Key]) -> tuple[list[Key], np.ndarray]:
    """Kvoter per mått (sista axeln), plus MACRO-rader. Nämnare 0 ger nan."""
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.where(den > 0, num / den, np.nan)

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, (level, label, metric) in enumerate(keys):
        if label != ANY:
            groups[(level, metric)].append(i)
    macro_keys = [(level, MACRO, metric) for level, metric in groups]
    if not macro_keys:
        return list(keys), values
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # medelvärde över enbart nan
        macro = np.stack([np.nanmean(values[..., idx], axis=-1) for idx in groups.values()], axis=-1)
    return [*keys, *macro_keys], np.concatenate([values, macro], axis=-1)


def _resample_weights(n: int, replicates: int, rng: np.random.Generator) -> np.ndarray:
    """Antal gånger varje dokument dras i varje bootstrapdragning (dragningar x dokument)."""
    return rng.multinomial(n, np.full(n, 1 / n), size=replicates).astype(np.float64)


def slice_name(rec: dict, spec: str) -> str | None:
    """Namnet på den delmängd posten hör till, eller None om posten saknar något av fälten."""
    parts = []
    for path in filter(None, spec.split(",")):
        value: object = rec
        for step in path.split("."):
            value = value.get(step) if isinstance(value, dict) else None
        if value is None:
            return None
        parts.append(f"{path.split('.')[-1]}={value}")
    return ", ".join(parts) or "alla"


def _num(x: float) -> float | None:
    return None if np.isnan(x) else round(float(x), 4)


def evaluate(
    gold: list[dict],
    preds: dict[str, dict],
    baseline: dict[str, dict] | None = None,
    *,
    slices: tuple[str, ...] = DEFAULT_SLICES,
    replicates: int = 1000,
    seed: int = 0,
    min_iou: float = 0.0,
) -> dict:
    """Poängsätter preds mot gold och ger en rapport med en rad per delmängd, nivå, etikett och mått.

    Med baseline jämförs de två metoderna parvis på samma bootstrapdragningar.
    """
    counts = count(gold, preds, min_iou)
    base_counts = count(gold, baseline, min_iou) if baseline is not None else None

    members: dict[str, list[int]] = defaultdict(list)
    for spec in slices:
        for d, rec in enumerate(gold):
            if (name := slice_name(rec, spec)) is not None:
                members[name].append(d)

    rng = np.random.default_rng(seed)
    rows, comparison = [], []
    for name in sorted(members):
        idx = np.array(members[name])
        weights = _resample_weights(len(idx), replicates, rng) if replicates else None

        def score(c: Counts) -> tuple[list[Key], np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
            num, den = c.num[idx], c.den[idx]
            keys, point = _ratios(num.sum(axis=0), den.sum(axis=0), c.keys)
            boot = None if weights is None else _ratios(weights @ num, weights @ den, c.keys)[1]
            return keys, point, boot, num.sum(axis=0), den.sum(axis=0)

        keys, point, boot, num, den = score(counts)
        low, high = _percentiles(boot, len(keys))
        for i, (level, label, metric) in enumerate(keys):
            if np.isnan(point[i]):
                continue
            row = {
                "slice": name,
                "level": level,
                "label": label,
                "metric": metric,
                "value": _num(point[i]),
                "ci_low": _num(low[i]),
                "ci_high": _num(high[i]),
            }
            if label != MACRO:
                row["num"], row["den"] = int(num[i]), int(den[i])
            rows.append(row)

        if base_counts is not None:
            base_keys, base_point, base_boot, _, _ = score(base_counts)
            base_index = {k: i for i, k in enumerate(base_keys)}
            for i, key in enumerate(keys):
                j = base_index.get(key)
                if j is None or np.isnan(point[i]) or np.isnan(base_point[j]):
                    continue
                row = {
                    "slice": name,
                    "level": key[0],
                    "label": key[1],
                    "metric": key[2],
                    "value": _num(point[i]),
                    "baseline": _num(base_point[j]),
                    "diff": _num(point[i] - base_point[j]),
                }
                if boot is not None:
                    diffs = boot[:, i] - base_boot[:, j]
                    diffs = diffs[~np.isnan(diffs)]
                    if len(diffs):
                        row["ci_low"], row["ci_high"] = (_num(x) for x in np.percentile(diffs, [2.5, 97.5]))
                        # Tvåsidigt: hur ofta skillnaden byter tecken mellan dragningarna.
                        row["p"] = _num(min(1.0, 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())))
                comparison.append(row)

    report = {
        "documents": len(gold),
        "settings": {"replicates": replicates, "seed": seed, "min_iou": min_iou, "slices": list(slices)},
        "slices": {name: len(idx) for name, idx in sorted(members.items())},
        "rows": rows,
    }
    if baseline is not None:
        report["comparison"] = comparison
    return report


def _percentiles(boot: np.ndarray | None, n_keys: int) -> tuple[np.ndarray, np.ndarray]:
    if boot is None:
        return np.full(n_keys, np.nan), np.full(n_keys, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # mått utan underlag i någon dragning
        low, high = np.nanpercentile(boot, [2.5, 97.5], axis=0)
    return low, high


LEVEL_TITLES = {
    "doc": "Dokumentnivå",
    "span": "Spannivå",
    "attribution": "Attribution",
    "identifiers": "Identifierare",
}
METRIC_ORDER = (
    "recall",
    "recall_explicit",
    "recall_implicit",
    "precision",
    "accuracy",
    "recall_with_subject",
)


def format_report(report: dict) -> str:
    """Rapporten som Markdown-tabeller, en per delmängd och nivå."""
    grouped: dict[tuple[str, str], dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for row in report["rows"]:
        grouped[(row["slice"], row["level"])][row["label"]][row["metric"]] = row

    label_order = [*CATEGORIES, *IDENTIFIER_TYPES, ANY, MACRO]
    lines = []
    for name, n_docs in report["slices"].items():
        lines.append(f"## {name} ({n_docs} dokument)")
        for level, title in LEVEL_TITLES.items():
            table = grouped.get((name, level))
            if not table:
                continue
            metrics = [m for m in METRIC_ORDER if any(m in cells for cells in table.values())]
            lines += ["", f"### {title}", "", "| | " + " | ".join(metrics) + " |", "|---" * (len(metrics) + 1) + "|"]
            for label in sorted(table, key=label_order.index):
                cells = [_format_cell(table[label].get(m)) for m in metrics]
                lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines.append("")

    if report.get("comparison"):
        lines += [
            "## Jämförelse mot baslinjen",
            "",
            "| delmängd | nivå | etikett | mått | metod | baslinje | skillnad | 95 % KI | p |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for row in report["comparison"]:
            interval = f"{row['ci_low']:+.3f} till {row['ci_high']:+.3f}" if "ci_low" in row else ""
            p = f"{row['p']:.3f}" if "p" in row else ""
            lines.append(
                f"| {row['slice']} | {row['level']} | {row['label']} | {row['metric']} | {row['value']:.3f} "
                f"| {row['baseline']:.3f} | {row['diff']:+.3f} | {interval} | {p} |"
            )
        lines.append("")
    return "\n".join(lines)


def _format_cell(row: dict | None) -> str:
    if row is None:
        return "–"
    text = f"{row['value']:.3f}"
    if row["ci_low"] is not None:
        text += f" [{row['ci_low']:.2f}–{row['ci_high']:.2f}]"
    if "den" in row:
        text += f" (n={row['den']})"
    return text


def load_gold(paths: list[Path]) -> list[dict]:
    gold = [rec for path in paths for _, rec in read_jsonl(path)]
    ids = [rec["id"] for rec in gold]
    if len(set(ids)) != len(ids):
        raise SystemExit("Facit innehåller samma id flera gånger.")
    return gold


def load_predictions(path: Path, gold: list[dict], allow_missing: bool = False) -> dict[str, dict]:
    texts = {rec["id"]: rec["text"] for rec in gold}
    preds: dict[str, dict] = {}
    for lineno, pred in read_jsonl(path):
        if errors := validate_prediction(pred, texts):
            raise SystemExit(f"{path}:{lineno}: {errors[0]}")
        if pred["id"] in preds:
            raise SystemExit(f"{path}:{lineno}: id {pred['id']!r} förekommer flera gånger")
        preds[pred["id"]] = pred
    missing = texts.keys() - preds.keys()
    if missing and not allow_missing:
        raise SystemExit(
            f"{path}: prediktion saknas för {len(missing)} av {len(texts)} texter, till exempel "
            f"{sorted(missing)[0]!r}. Använd --allow-missing för att räkna dem som tomma svar."
        )
    return preds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poängsätt prediktioner mot facit.")
    parser.add_argument("--gold", nargs="+", type=Path, required=True, help="facit (JSONL), en eller flera filer")
    parser.add_argument("--pred", type=Path, required=True, help="metodens prediktioner (JSONL)")
    parser.add_argument("--baseline", type=Path, help="en annan metods prediktioner att jämföra parvis mot")
    parser.add_argument("--out", type=Path, help="skriv hela rapporten som JSON hit")
    parser.add_argument(
        "--slice-by",
        action="append",
        metavar="FÄLT[,FÄLT]",
        help=f"dela upp resultatet på dessa fält, kan anges flera gånger (standard: {' '.join(DEFAULT_SLICES)})",
    )
    parser.add_argument("--bootstrap", type=int, default=1000, help="antal bootstrapdragningar, 0 stänger av")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--iou",
        type=float,
        default=0.0,
        help="minsta överlapp (IoU) för att ett spann ska räknas som hittat (standard: all överlapp räknas)",
    )
    parser.add_argument("--allow-missing", action="store_true", help="räkna saknade prediktioner som tomma svar")
    args = parser.parse_args(argv)

    gold = load_gold(args.gold)
    preds = load_predictions(args.pred, gold, args.allow_missing)
    baseline = load_predictions(args.baseline, gold, args.allow_missing) if args.baseline else None
    report = evaluate(
        gold,
        preds,
        baseline,
        slices=tuple(args.slice_by or DEFAULT_SLICES),
        replicates=args.bootstrap,
        seed=args.seed,
        min_iou=args.iou,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
