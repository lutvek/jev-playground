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


def test_command_line(tmp_path, capsys):
    specs_path = tmp_path / "pilot.specs.jsonl"
    args = ["--name", "pilot", "--n", "8", "--seed", "1", "--split", "dev", "--out", str(specs_path)]
    assert spec_cli.main(args) == 0
    specs = [s for _, s in read_jsonl(specs_path)]
    assert all(s["prompt"] == build_prompt(s) for s in specs)

    responses = list(respond(specs, TemplateLLM(specs)))
    responses[0]["response"] = "Trasig <PERSON P1>text"
    responses[1]["generator"] = "annan"
    responses_path = tmp_path / "pilot.responses.jsonl"
    write_jsonl(responses_path, responses[:-1])
    capsys.readouterr()

    assert build.main(["--specs", str(specs_path), "--responses", str(responses_path)]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert (stats["specar"], stats["utan svar"], stats["godkända"], stats["bortsorterade"]) == (8, 1, 6, 1)
    assert stats["skäl (antal texter)"] == {"taggar": 1}
    assert stats["per generator"]["annan"] == {"godkända": 1, "bortsorterade": 0, "andel bortsorterade": 0.0}
    assert stats["per generator"]["mall"]["bortsorterade"] == 1

    out = tmp_path / "pilot.jsonl"
    assert validate_file(out) == []
    records = [r for _, r in read_jsonl(out)]
    assert [r["id"] for r in records] == [f"syn-{s['scenario_id']}" for s in specs[1:7]]
    assert all(r["split"] == "dev" for r in records)
    [rejected] = [r for _, r in read_jsonl(tmp_path / "pilot.rejected.jsonl")]
    assert rejected["scenario_id"] == specs[0]["scenario_id"]
    assert rejected["problems"][0]["code"] == "taggar"
    assert json.loads((tmp_path / "pilot.stats.json").read_text(encoding="utf-8")) == stats
