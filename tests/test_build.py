import json

from benchmark.generering import build
from benchmark.generering import spec as spec_cli
from benchmark.generering.build import normalize_response, process
from benchmark.generering.llm import respond
from benchmark.generering.prompt import build_prompt
from benchmark.generering.spec import sample_specs
from benchmark.jsonl import read_jsonl, write_jsonl
from benchmark.schema.validate import validate_file

PHRASES = {
    ("HEALTH", "explicit"): "är sjukskriven för depression",
    ("HEALTH", "implicit"): "har tid hos psykologen varje vecka",
    ("ETHNICITY", "explicit"): "är same",
    ("ETHNICITY", "implicit"): "jobbar med renskötseln i familjens sameby",
    ("POLITICS", "explicit"): "röstar på Vänsterpartiet",
    ("POLITICS", "implicit"): "var med och startade partiets lokalavdelning",
    ("RELIGION", "explicit"): "är muslim",
    ("RELIGION", "implicit"): "går i moskén varje fredag",
    ("TRADE_UNION", "explicit"): "är med i Kommunal",
    ("TRADE_UNION", "implicit"): "är klubbordförande på fabriken",
    ("SEXUALITY", "explicit"): "är homosexuell",
    ("SEXUALITY", "implicit"): "bor ihop med sin pojkvän",
    ("GENETIC_BIOMETRIC", "explicit"): "bär på BRCA-mutationen",
    ("CRIMINAL", "explicit"): "dömdes för misshandel",
    ("CRIMINAL", "implicit"): "kom precis ut från Kumla",
}
DISTRACTORS = {
    "HEALTH": "Det är sjukt dyrt att bo här.",
    "ETHNICITY": "Det var samisk nationaldag i veckan.",
    "POLITICS": "Det är val i september.",
    "RELIGION": "Huset ligger bakom kyrkan.",
    "TRADE_UNION": "Det var strejk i hamnen.",
    "SEXUALITY": "Det var Pride i stan.",
    "GENETIC_BIOMETRIC": "Det ligger i familjens DNA.",
    "CRIMINAL": "Det har varit mycket brott i området.",
}


class TemplateLLM:
    """Skriver en enkel, korrekt märkt text för varje spec, så att hela kedjan kan testas utan modell."""

    name = "mall"

    def __init__(self, specs: list[dict]):
        self.specs = {build_prompt(s): s for s in specs}

    def complete(self, prompt: str) -> str:
        spec = self.specs[prompt]
        persons = {p["id"]: p for p in spec["persons"]}
        parts = []
        if name := persons["P0"]["name"]:
            parts.append(f"Jag heter <PERSON P0>{name}</PERSON>.")
        subject = persons["P1"]
        parts.append(f"Det gäller <PERSON P1>{subject['name']}</PERSON>.")
        if subject["personnummer"]:
            parts.append(f"Personnumret är <PERSONNUMMER P1>{subject['personnummer']}</PERSONNUMMER>.")
        if "P2" in persons and persons["P2"]["name"]:
            parts.append(f"<PERSON P2>{persons['P2']['name']}</PERSON> finns också med.")
        for fact in spec["facts"]:
            who = persons[fact["subject"]]
            if who["role"] == "REPORTER":
                ref = "Jag"
            elif who["name"]:
                ref = f"<PERSON {who['id']}>{who['name'].split()[0]}</PERSON>"
            else:
                ref = who["description"].capitalize()
            c, e = fact["category"], fact["expression"]
            parts.append(f"{ref} <{c} {e} {who['id']}>{PHRASES[(c, e)]}</{c}>.")
        parts += [DISTRACTORS[c] for c in spec["distractors"]]
        return "```\n" + " ".join(parts) + "\n```"


def test_whole_chain_accepts_correct_texts():
    specs = sample_specs(300, name="kedja", seed=3)
    for line in respond(specs, TemplateLLM(specs)):
        spec = next(s for s in specs if s["scenario_id"] == line["scenario_id"])
        record, problems = process(spec, line["response"], line["generator"])
        assert problems == [], (spec, line["response"])
        assert record["source"]["generator"] == "mall"


def test_normalize_response():
    tagged = "Hej <PERSON P1>Erik</PERSON>"
    assert normalize_response(f"  ```text\n{tagged}\n```  ") == tagged
    assert normalize_response("\nHej\n") == "Hej"


def test_empty_response_is_rejected():
    spec = sample_specs(1, name="tom", seed=1)[0]
    for response in (None, "", "  "):
        record, problems = process(spec, response, "mall")
        assert record is None
        assert [p.code for p in problems] == ["tomt-svar"]


def test_command_line_with_retries(tmp_path, capsys):
    specs_path = tmp_path / "pilot.specs.jsonl"
    args = ["--name", "pilot", "--n", "8", "--seed", "1", "--split", "dev", "--out", str(specs_path)]
    assert spec_cli.main(args) == 0
    specs = [s for _, s in read_jsonl(specs_path)]
    assert all(s["prompt"] == build_prompt(s) for s in specs)
    ids = [s["scenario_id"] for s in specs]

    # Första omgången: en trasig text, ett tomt svar, ett svar från en annan generator och ett
    # scenario utan svar.
    good = list(respond(specs, TemplateLLM(specs)))
    first = [dict(line) for line in good[:-1]]
    first[0]["response"] = "Trasig <PERSON P1>text"
    first[1]["response"] = None
    first[2]["generator"] = "annan"
    first_path = tmp_path / "pilot.responses.jsonl"
    write_jsonl(first_path, first)
    capsys.readouterr()

    assert build.main(["--specs", str(specs_path), "--responses", str(first_path)]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert (stats["specar"], stats["utan svar"], stats["försök"], stats["godkända"]) == (8, 1, 7, 5)
    assert stats["skäl (antal försök)"] == {"taggar": 1, "tomt-svar": 1}
    assert stats["per generator"]["annan"]["godkända"] == 1
    mall = stats["per generator"]["mall"]
    assert (mall["försök"], mall["godkända"], mall["andel bortsorterade"]) == (6, 4, 0.333)
    assert sum(t["specar"] for t in stats["per typ"].values()) == 8
    assert json.loads((tmp_path / "pilot.stats.json").read_text(encoding="utf-8")) == stats
    rejected = [r for _, r in read_jsonl(tmp_path / "pilot.rejected.jsonl")]
    assert [(r["scenario_id"], r["line"]) for r in rejected] == [(ids[0], 1), (ids[1], 2)]
    retry = [s for _, s in read_jsonl(tmp_path / "pilot.retry.specs.jsonl")]
    assert [s["scenario_id"] for s in retry] == [ids[0], ids[1], ids[7]]
    assert all(s["prompt"] for s in retry)

    # Andra omgången: nya försök för de tre, plus ett överflödigt försök för ett godkänt scenario.
    second_path = tmp_path / "pilot.retry.responses.jsonl"
    write_jsonl(second_path, [good[0], good[1], good[7], good[3]])
    args = ["--specs", str(specs_path), "--responses", str(first_path), str(second_path)]
    assert build.main(args) == 0
    stats = json.loads(capsys.readouterr().out)
    assert (stats["utan svar"], stats["försök"], stats["godkända"]) == (0, 10, 8)
    assert stats["överflödiga försök"] == 1

    out = tmp_path / "pilot.jsonl"
    assert validate_file(out) == []
    records = [r for _, r in read_jsonl(out)]
    assert [r["id"] for r in records] == [f"syn-{i}" for i in ids]
    assert all(r["split"] == "dev" for r in records)
    assert [s for _, s in read_jsonl(tmp_path / "pilot.retry.specs.jsonl")] == []
