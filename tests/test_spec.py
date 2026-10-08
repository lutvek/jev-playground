from collections import Counter

from benchmark.generering.prompt import build_prompt
from benchmark.generering.resources import luhn_digit
from benchmark.generering.spec import CELLS, REPORT_TYPES, sample_specs

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
    for fact in spec["facts"]:
        line = f"{fact['category']}, {fact['expression']}, om {fact['subject']}."
        assert line in prompt
        forbidden_line = f"\n- {fact['category']}: "
        assert (forbidden_line in prompt) == (fact["expression"] == "implicit")


def test_prompt_for_negative_text_asks_for_distractors():
    spec = next(s for s in SPECS if not s["facts"])
    prompt = build_prompt(spec)
    assert "inte innehålla några känsliga uppgifter" in prompt
    assert "Förbjudna ord" not in prompt
    assert "Implicit betyder" not in prompt
