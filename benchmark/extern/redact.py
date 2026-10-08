"""Hämtar REDACT och konverterar den svenska delen till benchmarkformatet.

    python -m benchmark.extern.redact

REDACT (https://github.com/guneeshvats/REDACT-PII-Benchmark) är LLM-genererat och omfattas av
REDACT Dataset Terms. Kända brister i datasetet står i benchmark/README.md.
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from benchmark.jsonl import write_jsonl
from benchmark.schema.labels import CATEGORIES, IDENTIFIER_TYPES
from benchmark.schema.validate import validate_record

# Låst version, så att konverteringen ger samma resultat varje gång.
COMMIT = "252232ac29669beeb99cb6474eeb2736761be508"
RAW_URL = (
    "https://media.githubusercontent.com/media/guneeshvats/REDACT-PII-Benchmark/"
    f"{COMMIT}/data/pii_benchmark_full.json"
)
RAW_SHA256 = "f8cb68bf5e54791decd9190792766b37e623bdb346b1641c1d1fd146ddec6d1c"

DATA_DIR = Path(__file__).parents[1] / "data"
DEFAULT_RAW = DATA_DIR / "raw" / "redact" / "pii_benchmark_full.json"
DEFAULT_OUT = DATA_DIR / "redact" / "redact_sv.jsonl"

SENSITIVE_MAP = {
    "Medical_Information": "HEALTH",
    "Allergy_Information": "HEALTH",
    "Sickness_Day_Records": "HEALTH",
    "Crime": "CRIMINAL",
    "Political_Party": "POLITICS",
    "Religion": "RELIGION",
    "Trade_Union_Membership": "TRADE_UNION",
    "Sex_Orientation": "SEXUALITY",
}

IDENTIFIER_MAP = {
    "First_Given_Name": "PERSON",
    "Last_Family_Name": "PERSON",
    "Full_Name": "PERSON",
    "Preferred_Name": "PERSON",
    "National_Identification_Number": "PERSONNUMMER",
    "Telephone_Numbers_Personal": "PHONE",
    "Telephone_Numbers_Work": "PHONE",
    "Personal_Email_Address": "EMAIL",
    "Work_Email_Address": "EMAIL",
    "Address_Personal": "ADDRESS",
    "Address_Work": "ADDRESS",
    "City": "LOCATION",
    "State": "LOCATION",
    "Location": "LOCATION",
    "Country_of_Residence": "LOCATION",
    "Place_of_Birth": "LOCATION",
    "Org_Name": "ORGANISATION",
    "Date_Time": "DATE",
    "Date_of_Birth": "DATE",
    "Customer_Reference_Number": "IDENTIFIER",
    "Employee_ID_Number": "IDENTIFIER",
    "Passport_Number": "IDENTIFIER",
    "Driving_License_Number": "IDENTIFIER",
    "Tax_Reference_Number": "IDENTIFIER",
    "Building_Badge_Card_Number": "IDENTIFIER",
    "Credit_Card_Numbers": "IDENTIFIER",
    "Social_Media_Identifiers": "IDENTIFIER",
    "Static_IP_Address": "IDENTIFIER",
}

# Typer utan motsvarighet i våra koder. Nationality, Citizenship_Status och PEP_Status ligger nära
# ETHNICITY respektive POLITICS men avslöjar inte etniskt ursprung eller politisk åsikt.
# Disciplinary_Action gäller arbetsrättsliga åtgärder, inte lagöverträdelser.
UNMAPPED = frozenset(
    {
        "Account_Statements",
        "Age",
        "Business_Title",
        "Citizenship_Status",
        "Compensation_and_Salary",
        "Disciplinary_Action",
        "Emergency_Contact_Details",
        "Gender",
        "Geolocation_Data",
        "Marital_Status",
        "Nationality",
        "PEP_Status",
        "Password",
        "Performance_Assessment",
        "Professional_Background",
    }
)

assert set(SENSITIVE_MAP.values()) <= set(CATEGORIES)
assert set(IDENTIFIER_MAP.values()) <= set(IDENTIFIER_TYPES)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def download(dest: Path) -> None:
    """Hämtar rådata (213 MB) om den inte redan finns, och kontrollerar checksumman."""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        print(f"Hämtar {RAW_URL}", file=sys.stderr)
        with urllib.request.urlopen(RAW_URL) as response, open(tmp, "wb") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    actual = sha256_of(dest)
    if actual != RAW_SHA256:
        raise SystemExit(f"{dest}: fel checksumma ({actual}), väntade {RAW_SHA256}")


def _drop_nested(spans: list[dict], label_keys: tuple[str, ...]) -> list[dict]:
    """Tar bort spann som ligger helt inuti ett annat spann med samma etikett.

    REDACT märker till exempel både hela namnet och för- och efternamnet var för sig.
    """
    kept: list[dict] = []
    for span in sorted(spans, key=lambda s: (s["start"], -s["end"])):
        label = [span[k] for k in label_keys]
        inside = any(
            k["start"] <= span["start"] and span["end"] <= k["end"] and [k[x] for x in label_keys] == label
            for k in kept
        )
        if not inside:
            kept.append(span)
    return kept


def convert_record(index: int, raw: dict, stats: Counter) -> dict:
    """Konverterar en REDACT-post. index är postens plats i rådatafilen.

    record_id i REDACT är inte unikt, så id byggs på index i stället.
    """
    text = raw["text"]
    sensitive, identifiers = [], []
    for entity in raw["entities"]:
        etype = entity["entity_type"]
        start, end = entity["start"], entity["end"]
        if start is None or end is None or text[start:end] != entity["entity_string"]:
            stats["bortfall: spannet finns inte i texten"] += 1
            continue
        surface = text[start:end]
        start += len(surface) - len(surface.lstrip())
        end -= len(surface) - len(surface.rstrip())
        if start >= end:
            stats["bortfall: tomt spann"] += 1
            continue

        if etype in SENSITIVE_MAP:
            span = {
                "start": start,
                "end": end,
                "category": SENSITIVE_MAP[etype],
                # REDACT anger inte uttryckstyp. Spannen kommer från en katalog med ytformer
                # (sjukdomsnamn, partinamn, brottsrubriceringar) och räknas därför som explicita.
                "expression": "explicit",
                "subject": None,
            }
            # disclosed=false är negationer, hypotetiska exempel och instruktionstexter.
            if not entity["disclosed"]:
                span["ignore"] = True
            sensitive.append(span)
        elif etype in IDENTIFIER_MAP:
            identifiers.append({"start": start, "end": end, "type": IDENTIFIER_MAP[etype]})
        elif etype in UNMAPPED:
            stats[f"omappad: {etype}"] += 1
        else:
            raise ValueError(f"Okänd entitetstyp i REDACT: {etype!r}")

    for span in sensitive:
        span.setdefault("ignore", False)
    n_before = len(sensitive) + len(identifiers)
    sensitive = _drop_nested(sensitive, ("category", "ignore"))
    identifiers = _drop_nested(identifiers, ("type",))
    stats["sammanslagna: inuti spann med samma etikett"] += n_before - len(sensitive) - len(identifiers)
    for span in sensitive:
        if not span["ignore"]:
            del span["ignore"]

    axes = raw["axes"]
    return {
        "id": f"redact-{index:05d}",
        "part": "redact",
        "split": "test",
        "source": {
            "dataset": "REDACT",
            "commit": COMMIT,
            "record_id": raw["record_id"],
            "domain": axes["domain"],
            "format": axes["format"],
            "difficulty": axes["difficulty"],
            "code_switching": axes["code_switching"],
            "behavioral_frame": raw["behavioral_frame"],
        },
        "text": text,
        "entities": [],
        "identifiers": identifiers,
        "sensitive": sensitive,
    }


def convert(raw_records: list[dict], language: str = "SV") -> tuple[list[dict], dict]:
    """Konverterar alla poster på ett språk. Ger posterna och statistik över konverteringen."""
    stats: Counter = Counter()
    records = [
        convert_record(index, raw, stats)
        for index, raw in enumerate(raw_records)
        if raw["axes"]["language"] == language
    ]

    summary: dict = {"dokument": len(records), "konvertering": dict(sorted(stats.items()))}
    for name, subset in (
        ("alla", records),
        ("helt svenska", [r for r in records if r["source"]["code_switching"] == "none"]),
    ):
        spans, docs, ignored_docs = Counter(), Counter(), Counter()
        for rec in subset:
            scored = {s["category"] for s in rec["sensitive"] if not s.get("ignore")}
            ignored = {s["category"] for s in rec["sensitive"] if s.get("ignore")}
            spans.update(s["category"] for s in rec["sensitive"] if not s.get("ignore"))
            docs.update(scored)
            ignored_docs.update(ignored - scored)
        summary[name] = {
            "dokument": len(subset),
            "dokument med känsliga uppgifter": sum(
                any(not s.get("ignore") for s in r["sensitive"]) for r in subset
            ),
            "kategorier": {
                category: {
                    "spann": spans[category],
                    "dokument": docs[category],
                    "dokument med bara ignore-spann": ignored_docs[category],
                }
                for category in CATEGORIES
            },
            "identifierare": dict(
                sorted(Counter(s["type"] for r in subset for s in r["identifiers"]).items())
            ),
        }
    return records, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hämta REDACT och konvertera den svenska delen.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW, help="rådatafil (hämtas om den saknas)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    download(args.raw)
    with open(args.raw, encoding="utf-8") as f:
        records, summary = convert(json.load(f))

    for rec in records:
        if errors := validate_record(rec):
            raise SystemExit(f"{rec['id']}: konverteringen gav en ogiltig post: {errors}")

    write_jsonl(args.out, records)
    stats_path = args.out.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Skrev {len(records)} poster till {args.out} och statistik till {stats_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
