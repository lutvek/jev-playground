import copy

import pytest

from benchmark.generering.build import process
from benchmark.generering.categories import forbidden_matches


def person(pid: str, role: str, name: str | None, pnr: str | None = None, adult: bool = True) -> dict:
    return {
        "id": pid,
        "role": role,
        "description": "granne",
        "adult": adult,
        "gender": "man",
        "name": name,
        "personnummer": pnr,
    }


SPEC = {
    "scenario_id": "test-00001",
    "placeholders": True,
    "report_type": "privat-oro",
    "report": "orosanmälan",
    "tone": "vardaglig",
    "typos": False,
    "length": "kort",
    "persons": [
        person("P0", "REPORTER", None),
        person("P1", "SUBJECT", "Erik Lund", "850315-4171"),
        person("P2", "OTHER", "Elsa", adult=False),
    ],
    "facts": [
        {"category": "RELIGION", "expression": "implicit", "subject": "P1"},
        {"category": "HEALTH", "expression": "explicit", "subject": "P1"},
    ],
    "distractors": [],
}

INTRO = (
    "Jag vill anmäla oro för min granne <PERSON P1>Erik Lund</PERSON> "
    "(<PERSONNUMMER P1>850315-4171</PERSONNUMMER>). "
)
RELIGION = "<PERSON P1>Erik</PERSON> <RELIGION implicit P1>går i moskén varje fredag</RELIGION>"
HEALTH = " men <HEALTH explicit P1>är sjukskriven för depression</HEALTH> sedan i våras."
ELSA = " Dottern <PERSON P2>Elsa</PERSON> verkar må dåligt."
RESPONSE = INTRO + RELIGION + HEALTH + ELSA


def problems(response: str, spec: dict = SPEC) -> list[tuple[str, str]]:
    _, found = process(spec, response, "test")
    return [(p.code, p.message) for p in found]


def codes(response: str, spec: dict = SPEC) -> list[str]:
    return [code for code, _ in problems(response, spec)]


def test_valid_text_passes():
    assert problems(RESPONSE) == []


def test_missing_and_unexpected_facts():
    untagged = RESPONSE.replace("<HEALTH explicit P1>", "").replace("</HEALTH>", "")
    assert ("saknad-uppgift", "HEALTH explicit om P1 är inte märkt") in problems(untagged)

    extra = RESPONSE + " Han <POLITICS explicit P1>röstar på Vänsterpartiet</POLITICS>."
    assert codes(extra) == ["oväntad-uppgift"]

    wrong_person = RESPONSE.replace("<RELIGION implicit P1>", "<RELIGION implicit P2>")
    assert sorted(codes(wrong_person)) == ["oväntad-uppgift", "saknad-uppgift"]

    wrong_expression = RESPONSE.replace("<RELIGION implicit P1>", "<RELIGION explicit P1>")
    assert sorted(codes(wrong_expression)) == ["oväntad-uppgift", "saknad-uppgift"]


def test_category_words():
    in_implicit = RESPONSE.replace("går i moskén", "går som troende i moskén")
    assert problems(in_implicit) == [("förbjudet-ord", "'troende' namnger RELIGION i ett implicit spann")]

    outside = RESPONSE + " Han är muslim."
    assert problems(outside) == [
        ("omärkt-kategoriord", "'muslim' namnger RELIGION men står utanför de explicita spannen")
    ]

    # Ord från en kategori som inte finns i specen får inte heller stå omärkta, och inte i ett
    # implicit spann i en annan kategori.
    assert codes(RESPONSE + " Han dömdes för stöld.") == ["omärkt-kategoriord", "omärkt-kategoriord"]
    assert codes(RESPONSE.replace("varje fredag", "varje fredag trots sin cancer")) == ["omärkt-kategoriord"]

    # Ett explicit spann räcker, också i en annan kategori: "sexualbrott" är både brott och sexualitet.
    assert codes(RESPONSE.replace("för depression", "för depression efter ett sexualbrott")) == []


def test_distractor_categories_are_exempt_in_negative_texts():
    spec = copy.deepcopy(SPEC)
    spec["facts"], spec["distractors"] = [], ["HEALTH"]
    text = INTRO + "Det är sjukt dyrt att bo här." + ELSA
    assert problems(text, spec) == []
    assert codes(text + " Han är muslim.", spec) == ["omärkt-kategoriord"]


def test_names():
    assert codes(RESPONSE + " Erik är aldrig hemma.") == ["omärkt-namn"]
    assert codes(RESPONSE + " Eriks bil står kvar.") == ["omärkt-namn"]
    assert codes(RESPONSE + " <PERSON P1>Eriks</PERSON> bil står kvar.") == []
    assert codes(RESPONSE + " Han bor på <ADDRESS>Eriks väg 3</ADDRESS>.") == []
    assert codes(RESPONSE + " <PERSON P1>Elsa</PERSON> leker.") == ["fel-namn"]
    assert codes(RESPONSE + " Jag heter <PERSON P0>Karin</PERSON>.") == ["fel-namn"]
    assert problems(RESPONSE.replace(ELSA, "")) == [("namn-saknas", "namnet på P2, Elsa, står inte i texten")]


def test_personnummer():
    untagged = RESPONSE.replace("<PERSONNUMMER P1>", "").replace("</PERSONNUMMER>", "")
    assert problems(untagged) == [
        ("personnummer", "personnumret för P1 är inte märkt"),
        ("personnummer", "'850315-4171' är inte märkt som personnummer"),
    ]
    assert codes(RESPONSE.replace("850315-4171", "850315-4172")) == ["personnummer"]
    assert codes(RESPONSE.replace("850315-4171", "19850315-4171")) == []
    assert codes(RESPONSE + " Hon har <PERSONNUMMER P2>150101-2220</PERSONNUMMER>.") == ["personnummer"]
    assert codes(RESPONSE + " Ärendet har nummer <IDENTIFIER>202401-1234</IDENTIFIER>.") == []
    assert codes(RESPONSE + " Ärendet har nummer 202401-1234.") == ["personnummer"]


def test_tag_errors_reject_the_text():
    assert problems(RESPONSE.replace("<PERSON P2>", "<PERSON P7>")) == [
        ("taggar", "<PERSON> gäller P7, som inte finns i specen")
    ]
    assert codes(RESPONSE.replace("</HEALTH>", "")) == ["taggar"]


@pytest.mark.parametrize(
    "category, text, expected",
    [
        ("RELIGION", "Han är Muslim sedan länge", ["Muslim"]),
        ("RELIGION", "Han är frikristen", ["frikristen"]),
        ("HEALTH", "Hon är långtidssjukskriven", ["långtidssjukskriven"]),
        ("TRADE_UNION", "Han är med i IF Metall", ["IF Metall"]),
        ("TRADE_UNION", "Hon är skyddsombud", []),
        ("CRIMINAL", "Det blev ett avbrott i ett benbrott", []),
        ("CRIMINAL", "Han åtalades för inbrott", ["åtalades", "inbrott"]),
    ],
)
def test_forbidden_matches(category, text, expected):
    assert [text[s:e] for s, e in forbidden_matches(category, text)] == expected
