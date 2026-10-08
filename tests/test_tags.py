import pytest

from benchmark.generering.tags import TagError, TaggedSpan, parse


def surfaces(text: str, spans: list[TaggedSpan]) -> list[tuple[str, str]]:
    return [(text[s.start : s.end], s.label) for s in spans]


def test_strips_tags_and_keeps_offsets():
    text, spans = parse(
        "Jag skriver om <PERSON P1>Erik Lund</PERSON>. "
        "Han <RELIGION implicit P1>går i moskén varje <DATE>fredag</DATE></RELIGION>."
    )
    assert text == "Jag skriver om Erik Lund. Han går i moskén varje fredag."
    assert surfaces(text, spans) == [
        ("Erik Lund", "PERSON"),
        ("går i moskén varje fredag", "RELIGION"),
        ("fredag", "DATE"),
    ]
    person, religion, date = spans
    assert person == TaggedSpan(person.start, person.end, "PERSON", None, "P1")
    assert (religion.expression, religion.person) == ("implicit", "P1")
    assert date.person is None


def test_attributes_in_any_order_and_case():
    _, [span] = parse("<HEALTH P2 Explicit>sjukskriven</HEALTH>")
    assert (span.expression, span.person) == ("explicit", "P2")


def test_whitespace_at_tag_edges_falls_outside_span():
    text, [span] = parse("Hon <HEALTH explicit P1> har astma </HEALTH>.")
    assert text[span.start : span.end] == "har astma"


def test_text_that_only_looks_like_tags_is_kept():
    text, spans = parse("Betyg <3 och <br> är inte taggar.")
    assert text == "Betyg <3 och <br> är inte taggar."
    assert spans == []


@pytest.mark.parametrize(
    "tagged, expected",
    [
        ("<HEALTH explicit P1>sjuk", "stängs aldrig"),
        ("sjuk</HEALTH>", "saknar starttagg"),
        ("<HEALTH explicit P1><PERSON P1>Erik</HEALTH></PERSON>", "stänger <PERSON P1>"),
        ("<SJUK explicit P1>sjuk</SJUK>", "okänd tagg"),
        ("<HEALTH P1>sjuk</HEALTH>", "både uttryckstyp och person"),
        ("<HEALTH explicit>sjuk</HEALTH>", "både uttryckstyp och person"),
        ("<HEALTH explicit P1 P2>sjuk</HEALTH>", "okända eller dubbla attribut"),
        ("<HEALTH explicit P1 tydligt>sjuk</HEALTH>", "okända eller dubbla attribut"),
        ("<PERSON implicit P1>Erik</PERSON>", "ingen uttryckstyp"),
        ("<PERSON P1>Erik</PERSON P1>", "har attribut"),
        ("<PERSON P1> </PERSON>", "är tom"),
    ],
)
def test_errors(tagged, expected):
    with pytest.raises(TagError, match=expected):
        parse(tagged)
