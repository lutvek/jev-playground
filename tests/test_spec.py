from collections import Counter

from benchmark.generering.categories import CUES, forbidden_matches
from benchmark.generering.prompt import build_prompt
from benchmark.generering.resources import luhn_digit
from benchmark.generering.spec import CELLS, REPORT_TYPES, sample_specs
from benchmark.schema.labels import CATEGORIES

SPECS = sample_specs(400, name="test", seed=7)


def test_same_seed_gives_same_specs():
    assert sample_specs(400, name="test", seed=7) == SPECS
    assert sample_specs(400, name="test", seed=8) != SPECS


def test_ids_and_split():
    assert [s["scenario_id"] for s in SPECS[:2]] == ["test-00001", "test-00002"]
    assert "split" not in SPECS[0]
    assert all(s["split"] == "dev" for s in sample_specs(5, name="dev", seed=1, split="dev"))


def test_negative_share_is_exact():
    negatives = [s for s in SPECS if not s["facts"]]
    assert len(negatives) == 100
    assert all(1 <= len(s["distractors"]) <= 2 for s in negatives)
    assert all(not s["distractors"] for s in SPECS if s["facts"])


def test_cells_are_balanced():
    counts = Counter((f["category"], f["expression"]) for s in SPECS for f in s["facts"])
    assert set(counts) == set(CELLS)
    assert ("GENETIC_BIOMETRIC", "implicit") not in CELLS
    assert max(counts.values()) - min(counts.values()) <= 1


def test_facts_follow_the_constraints():
    groups = {r.code: r.group for r in REPORT_TYPES}
    for spec in SPECS:
        categories = [f["category"] for f in spec["facts"]]
        assert len(categories) == len(set(categories)), "högst en uppgift per kategori"
        persons = {p["id"]: p for p in spec["persons"]}
        for fact in spec["facts"]:
            about = persons[fact["subject"]]
            assert about["adult"]
            assert about["role"] != "REPORTER" or groups[spec["report_type"]] == "privatperson"


def test_names_are_unique_within_a_text():
    for spec in SPECS:
        parts = [part for p in spec["persons"] if p["name"] for part in p["name"].split()]
        assert len(parts) == len(set(parts))
        assert spec["persons"][1]["name"], "den som texten gäller har alltid ett namn"


def test_placeholder_personnummer_cannot_belong_to_anyone():
    persons = [p for s in SPECS for p in s["persons"] if p["personnummer"]]
    assert persons
    for p in persons:
        digits = p["personnummer"].replace("-", "")
        assert len(digits) == 10
        assert int(digits[9]) != luhn_digit(digits[:9])
        assert int(digits[8]) % 2 == (1 if p["gender"] == "man" else 0)


def test_luhn_digit():
    # Exempel från Skatteverkets beskrivning av kontrollsiffran: 811218-9876.
    assert luhn_digit("811218987") == 6


def test_prompt_lists_persons_facts_and_forbidden_words():
    spec = next(
        s
        for s in SPECS
        if any(f["expression"] == "implicit" for f in s["facts"])
        and any(f["expression"] == "explicit" for f in s["facts"])
        and s["persons"][1]["personnummer"]
    )
    prompt = build_prompt(spec)
    assert spec["persons"][1]["name"] in prompt
    assert spec["persons"][1]["personnummer"] in prompt
    assert spec["place"] in prompt and spec["date"] in prompt
    forbidden = prompt.split("# Förbjudna ord")[1].split("# Märkning")[0]
    for fact in spec["facts"]:
        line = f"{fact['category']}, {fact['expression']}, om {fact['subject']}. Ledtråd: {fact['cue']}."
        assert line in prompt
        assert (f"\n- {fact['category']}: " in forbidden) == (fact["expression"] == "implicit")


def test_prompt_for_negative_text_asks_for_unmarked_distractors():
    spec = next(s for s in SPECS if not s["facts"])
    prompt = build_prompt(spec)
    assert "inte innehålla några känsliga uppgifter" in prompt
    assert "de ska inte märkas" in prompt
    assert "<KATEGORI" not in prompt
    assert "Förbjudna ord" not in prompt
    assert "Implicit betyder" not in prompt


def test_couples_are_same_sex_only_with_a_fact_about_sexuality():
    partners = {d for r in REPORT_TYPES for d in r.partners}
    couples = [s for s in SPECS if len(s["persons"]) == 3 and s["persons"][2]["description"] in partners]
    assert len(couples) > 20
    for spec in couples:
        subject, partner = spec["persons"][1:]
        facts = [f for f in spec["facts"] if f["category"] == "SEXUALITY" and f["subject"] in ("P1", "P2")]
        assert (subject["gender"] == partner["gender"]) == bool(facts)


def test_details_and_cues_vary():
    assert len({s["place"] for s in SPECS}) > 30
    assert len({s["date"] for s in SPECS}) > 200
    assert 0.3 < sum(s["address"] is not None for s in SPECS) / len(SPECS) < 0.7
    cell = ("RELIGION", "implicit")
    cues = {f["cue"] for s in SPECS for f in s["facts"] if (f["category"], f["expression"]) == cell}
    assert cues == set(CUES[cell])


def test_cues_avoid_forbidden_words():
    for (category, expression), cues in CUES.items():
        for cue in cues:
            if expression == "implicit":
                assert forbidden_matches(category, cue) == [], cue
            for other in CATEGORIES:
                if other != category:
                    assert forbidden_matches(other, cue, ambiguous=False) == [], (cue, other)
