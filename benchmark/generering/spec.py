"""Slumpar fram scenariospecar för den syntetiska delen.

    python -m benchmark.generering.spec --name pilot --n 50 --seed 1

En spec bestämmer vad en text ska innehålla innan den skrivs: typ av underrättelse, personer med
roller och vilka känsliga uppgifter som ska finnas med, explicit eller implicit och om vem.
Etiketterna kommer alltså från konstruktionen och behöver inte annoteras.

Varje rad i utfilen är en spec med prompten till LLM:en i fältet prompt, så att texterna kan
genereras var som helst och läsas tillbaka med benchmark.generering.build.
"""

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from benchmark.generering.categories import CUES
from benchmark.generering.prompt import build_prompt
from benchmark.generering.resources import PLACEHOLDERS, PLACES, STREETS, Resources, placeholder_personnummer
from benchmark.jsonl import write_jsonl
from benchmark.schema.labels import CATEGORIES, EXPRESSIONS, SPLITS

DATA_DIR = Path(__file__).parents[1] / "data" / "synthetic"

# Genetiska och biometriska uppgifter uttrycks nästan aldrig implicit (PLAN_BENCHMARK.md, avsnitt 1).
CELLS = tuple(
    (category, expression)
    for category in CATEGORIES
    for expression in EXPRESSIONS
    if (category, expression) != ("GENETIC_BIOMETRIC", "implicit")
)


@dataclass(frozen=True)
class ReportType:
    code: str
    description: str  # med obestämd artikel, så att den kan stå direkt efter "Skriv"
    group: str  # privatperson, myndighet eller vård och skola
    reporters: tuple[str, ...]
    subjects: tuple[str, ...]
    partners: tuple[str, ...]  # partner till den texten främst gäller
    others: tuple[str, ...]  # andra vuxna
    children: tuple[str, ...]  # barn får inga känsliga uppgifter
    tones: tuple[str, ...]
    reporter_named: float  # sannolikhet att avsändaren skriver under med namn
    personnummer: float  # sannolikhet att personnumret för den som underrättelsen gäller står med


# Allmänna typer av underrättelser, tills vi vet vilka texterna ska efterlikna (avsnitt 9 i planen).
# Typer och avsändare som i sig avslöjar en kategori är utelämnade: Kriminalvården och psykiatrin,
# och tips om fusk eller svartarbete, som är misstankar om brott.
REPORT_TYPES = (
    ReportType(
        code="privat-oro",
        description="en orosanmälan till socialtjänsten från en privatperson, via webbformulär eller mejl",
        group="privatperson",
        reporters=("granne", "släkting", "vän till familjen"),
        subjects=("granne", "förälder i en familj som avsändaren känner", "vuxen släkting"),
        partners=("partner till den anmälda",),
        others=("förälder till den anmälda",),
        children=("barn till den anmälda",),
        tones=("vardaglig", "talspråklig", "orolig"),
        reporter_named=0.4,
        personnummer=0.1,
    ),
    ReportType(
        code="privat-klagomal",
        description="ett klagomål från en privatperson till hyresvärden eller kommunen om en granne, till "
        "exempel om störande ljud, nedskräpning eller att grannen inte tar hand om sin lägenhet",
        group="privatperson",
        reporters=("granne", "boende i samma hus"),
        subjects=("granne", "boende i samma trappuppgång"),
        partners=("partner till grannen",),
        others=("vuxen som ofta besöker grannen",),
        children=(),
        tones=("vardaglig", "talspråklig", "upprörd"),
        reporter_named=0.5,
        personnummer=0.05,
    ),
    ReportType(
        code="polis",
        description="en underrättelse från polisen till socialtjänsten om oro för en person, till exempel "
        "efter ett larm från grannar eller en kontroll",
        group="myndighet",
        reporters=("polisinspektör", "polisassistent"),
        subjects=("vuxen som polisen har haft kontakt med", "förälder i ett hushåll där polisen varit"),
        partners=("partner till den underrättelsen gäller",),
        others=("vuxet syskon till den underrättelsen gäller",),
        children=("barn i hushållet",),
        tones=("formell", "saklig"),
        reporter_named=0.8,
        personnummer=0.7,
    ),
    ReportType(
        code="myndighet",
        description="en underrättelse från en myndighet, till exempel Försäkringskassan eller "
        "Arbetsförmedlingen, till en annan myndighet",
        group="myndighet",
        reporters=("handläggare", "utredare"),
        subjects=("person som har ett ärende hos myndigheten",),
        partners=("partner till den ärendet gäller",),
        others=("arbetsgivare", "ombud"),
        children=(),
        tones=("formell", "saklig"),
        reporter_named=0.8,
        personnummer=0.7,
    ),
    ReportType(
        code="skola",
        description="en orosanmälan till socialtjänsten från en förskola eller skola",
        group="vård och skola",
        reporters=("lärare", "förskollärare", "kurator", "rektor"),
        subjects=("förälder till ett barn i verksamheten",),
        partners=("den andra föräldern",),
        others=("mor- eller farförälder till barnet",),
        children=("barnet i verksamheten",),
        tones=("formell", "saklig", "vardaglig"),
        reporter_named=0.7,
        personnummer=0.3,
    ),
    ReportType(
        code="vard",
        description="en orosanmälan från hälso- och sjukvården, till exempel från BVC eller en vårdcentral, "
        "om ett barns situation",
        group="vård och skola",
        reporters=("distriktssköterska", "läkare", "kurator"),
        subjects=("förälder till ett barn på BVC", "förälder till ett barn som har varit på vårdcentralen"),
        partners=("den andra föräldern",),
        others=("mor- eller farförälder till barnet",),
        children=("barnet",),
        tones=("formell", "saklig"),
        reporter_named=0.7,
        personnummer=0.6,
    ),
)

LENGTHS = ("kort", "medel", "lång")
LENGTH_WEIGHTS = (4, 4, 2)
N_FACTS_WEIGHTS = {1: 0.5, 2: 0.35, 3: 0.15}
OTHER_PERSON = 0.5  # sannolikhet att texten har en tredje person
OTHER_NAMED = 0.7
ADDRESS = 0.5  # sannolikhet att specen anger en gatuadress
TYPOS = 0.3  # sannolikhet för stavfel i texter från privatpersoner
SUBJECT_WEIGHTS = {"SUBJECT": 7, "OTHER": 2, "REPORTER": 1}  # vem en känslig uppgift gäller
MONTHS = (
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december",
)
OPPOSITE = {"kvinna": "man", "man": "kvinna"}


class _Names:
    """Drar namn så att inget för- eller efternamn förekommer två gånger i samma text."""

    def __init__(self, rng: random.Random, resources: Resources):
        self.rng, self.resources, self.used = rng, resources, set()

    def _draw(self, pool: tuple[str, ...]) -> str:
        name = self.rng.choice([n for n in pool if n not in self.used])
        self.used.add(name)
        return name

    def full(self, gender: str) -> str:
        first = self._draw(self.resources.male if gender == "man" else self.resources.female)
        return f"{first} {self._draw(self.resources.surnames)}"

    def first(self, gender: str) -> str:
        return self._draw(self.resources.male if gender == "pojke" else self.resources.female)


def _person(person_id: str, role: str, description: str, gender: str | None, *, adult: bool = True) -> dict:
    return {
        "id": person_id,
        "role": role,
        "description": description,
        "adult": adult,
        "gender": gender,
        "name": None,
        "personnummer": None,
    }


def sample_spec(
    scenario_id: str,
    rng: random.Random,
    cell_counts: Counter,
    *,
    negative: bool = False,
    resources: Resources = PLACEHOLDERS,
) -> dict:
    """En spec. cell_counts räknar känsliga uppgifter per (kategori, uttryck) över alla specar,
    och varje ny uppgift väljs bland de celler som har minst hittills. Då blir cellerna jämnstora.
    """
    report = rng.choice(REPORT_TYPES)
    names = _Names(rng, resources)

    reporter = _person("P0", "REPORTER", rng.choice(report.reporters), rng.choice(("kvinna", "man")))
    if rng.random() < report.reporter_named:
        reporter["name"] = names.full(reporter["gender"])

    subject = _person("P1", "SUBJECT", rng.choice(report.subjects), rng.choice(("kvinna", "man")))
    subject["name"] = names.full(subject["gender"])
    if rng.random() < report.personnummer:
        subject["personnummer"] = placeholder_personnummer(rng, subject["gender"])
    persons = [reporter, subject]

    other = None
    if rng.random() < OTHER_PERSON:
        description = rng.choice(report.partners + report.others + report.children)
        if description in report.children:
            other = _person("P2", "OTHER", description, rng.choice(("flicka", "pojke")), adult=False)
            other["name"] = names.first(other["gender"])
        else:
            # En partners kön bestäms när uppgifterna är kända, se nedan.
            gender = None if description in report.partners else rng.choice(("kvinna", "man"))
            other = _person("P2", "OTHER", description, gender)
        persons.append(other)

    facts, distractors = [], []
    if negative:
        distractors = sorted(rng.sample(CATEGORIES, rng.choice((1, 2))), key=CATEGORIES.index)
    else:
        # En privatperson kan skriva om sig själv, en tjänsteperson gör det inte.
        eligible = [
            p for p in persons if p["adult"] and (p["role"] != "REPORTER" or report.group == "privatperson")
        ]
        weights = [SUBJECT_WEIGHTS[p["role"]] for p in eligible]
        n_facts = rng.choices(list(N_FACTS_WEIGHTS), weights=list(N_FACTS_WEIGHTS.values()))[0]
        used: set[str] = set()
        for _ in range(n_facts):
            # Högst en uppgift per kategori, så att en text aldrig har både ett explicit och ett
            # implicit uttryck i samma kategori (se Poängsättning i benchmark/README.md).
            options = [cell for cell in CELLS if cell[0] not in used]
            fewest = min(cell_counts[cell] for cell in options)
            category, expression = rng.choice([c for c in options if cell_counts[c] == fewest])
            cell_counts[(category, expression)] += 1
            used.add(category)
            who = rng.choices(eligible, weights=weights)[0]
            cue = rng.choice(CUES[(category, expression)])
            facts.append({"category": category, "expression": expression, "subject": who["id"], "cue": cue})

    if other is not None and other["adult"]:
        if other["gender"] is None:
            # Ett par av samma kön avslöjar sexuell läggning. Det får bara förekomma när specen
            # har en uppgift om läggningen hos någon av de två.
            couple = {"P1", "P2"}
            same_sex = any(f["category"] == "SEXUALITY" and f["subject"] in couple for f in facts)
            other["gender"] = subject["gender"] if same_sex else OPPOSITE[subject["gender"]]
        if rng.random() < OTHER_NAMED:
            other["name"] = names.full(other["gender"])

    length = rng.choices(LENGTHS, weights=LENGTH_WEIGHTS)[0]
    if len(facts) == 3 and length == "kort":
        length = "medel"

    street = f"{rng.choice(STREETS)} {rng.randint(1, 60)}" if rng.random() < ADDRESS else None
    return {
        "scenario_id": scenario_id,
        "placeholders": resources.placeholder,
        "report_type": report.code,
        "report": report.description,
        "tone": rng.choice(report.tones),
        "typos": report.group == "privatperson" and rng.random() < TYPOS,
        "length": length,
        "place": rng.choice(PLACES),
        "address": street,
        "date": f"{rng.randint(1, 28)} {rng.choice(MONTHS)} {rng.choice((2025, 2026))}",
        "persons": persons,
        "facts": facts,
        "distractors": distractors,
    }


def sample_specs(
    n: int,
    *,
    name: str,
    seed: int,
    negative_share: float = 0.25,
    split: str | None = None,
    resources: Resources = PLACEHOLDERS,
) -> list[dict]:
    """n specar med id:n <name>-00001 och uppåt. Andelen negativa är exakt negative_share, avrundat."""
    rng = random.Random(seed)
    negatives = set(rng.sample(range(n), round(n * negative_share)))
    cell_counts: Counter = Counter()
    specs = []
    for i in range(n):
        scenario_id = f"{name}-{i + 1:05d}"
        spec = sample_spec(scenario_id, rng, cell_counts, negative=i in negatives, resources=resources)
        if split is not None:
            spec["split"] = split
        specs.append(spec)
    return specs


def summarize(specs: list[dict]) -> dict:
    cells = Counter(f"{f['category']} {f['expression']}" for s in specs for f in s["facts"])
    return {
        "specar": len(specs),
        "negativa": sum(not s["facts"] for s in specs),
        "uppgifter per cell": {f"{c} {e}": cells[f"{c} {e}"] for c, e in CELLS},
        "typer": dict(sorted(Counter(s["report_type"] for s in specs).items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slumpa fram scenariospecar med promptar.")
    parser.add_argument("--name", required=True, help="namn på omgången, blir början på varje scenario-id")
    parser.add_argument("--n", type=int, required=True, help="antal specar")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--split", choices=SPLITS)
    parser.add_argument(
        "--negative-share", type=float, default=0.25, help="andel texter utan känsliga uppgifter"
    )
    parser.add_argument("--out", type=Path, help=f"standard: {DATA_DIR}/<name>.specs.jsonl")
    args = parser.parse_args(argv)

    specs = sample_specs(
        args.n, name=args.name, seed=args.seed, negative_share=args.negative_share, split=args.split
    )
    out = args.out or DATA_DIR / f"{args.name}.specs.jsonl"
    write_jsonl(out, ({**spec, "prompt": build_prompt(spec)} for spec in specs))
    print(json.dumps(summarize(specs), ensure_ascii=False, indent=2))
    print(f"Skrev {len(specs)} specar till {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
