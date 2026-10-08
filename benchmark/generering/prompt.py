"""Prompten som får LLM:en att skriva en text enligt en scenariospec och märka uppgifterna med taggar."""

from benchmark.generering.categories import DESCRIPTIONS, DISTRACTORS, FORBIDDEN

LENGTHS = {"kort": "3–5 meningar", "medel": "6–9 meningar", "lång": "10–15 meningar"}
ROLES = {"REPORTER": "avsändaren", "SUBJECT": "den som texten främst gäller", "OTHER": "annan person"}

INTRO = """\
Du skriver påhittade texter till ett testdataset. Datasetet mäter hur bra olika metoder hittar \
känsliga personuppgifter i svensk text. Alla personer och uppgifter är påhittade."""

NAMES = "Använd namnen exakt som de står, hela eller bara för- eller efternamnet."

EXPRESSION_RULES = """\
- Explicit betyder att uppgiften sägs rakt ut, till exempel med en diagnos, en religion, ett \
parti, ett fackförbund eller ett brott.
- Implicit betyder att en uppmärksam läsare kan sluta sig till uppgiften av sammanhanget, till \
exempel av vanor, platser, aktiviteter, uppdrag eller behandlingar, men att kategorin aldrig namnges."""

RULES = """\
- Ord som namnger en kategori får bara stå inuti märkningen av en uppgift i den kategorin.
- Skriv inga negationer om känsliga uppgifter, som att någon inte är medlem i facket.
- Nämn inga andra personer vid namn, och hitta inte på telefonnummer, e-postadresser eller \
personnummer."""

TAGGING = """\
# Märkning

Märk uppgifterna med taggar direkt i texten.

- Känsliga uppgifter: <KATEGORI explicit|implicit person>…</KATEGORI>, med kategorin och \
uttrycket från listan ovan, till exempel \
<CRIMINAL explicit P1>dömdes för rattfylleri förra året</CRIMINAL>. Märk de ord som avslöjar \
uppgiften, varken fler eller färre. Nämns samma uppgift flera gånger märks varje ställe.
- Namn: <PERSON P1>Erik</PERSON>. Märk varje gång ett namn står, också när bara förnamnet eller \
efternamnet står. Märk inte pronomen eller beskrivningar som "grannen".
- Personnummer: <PERSONNUMMER P1>…</PERSONNUMMER>.
- Andra identifierare, utan person: <DATE> för datum och klockslag, <LOCATION> för orter och \
platser, <ADDRESS> för gatuadresser, <ORGANISATION> för myndigheter, företag, skolor och \
föreningar, och <IDENTIFIER> för ärendenummer och liknande.
- Taggar får ligga inuti varandra men inte korsa varandra.

Svara bara med den märkta texten, utan rubrik, förklaring eller kodblock."""


def _person_line(person: dict) -> str:
    line = f"- {person['id']}, {ROLES[person['role']]}: {person['description']}."
    if person["name"]:
        line += f" Namn: {person['name']} ({person['gender']})."
    else:
        line += f" Nämns inte vid namn ({person['gender']})."
    if person["personnummer"]:
        line += f" Personnummer: {person['personnummer']}."
    return line


def build_prompt(spec: dict) -> str:
    persons = "\n".join(_person_line(p) for p in spec["persons"])
    style = f"Längd: {LENGTHS[spec['length']]}. Ton: {spec['tone']}."
    if spec["typos"]:
        style += (
            " Skriv som någon som skriver snabbt, med några stavfel och slarvig interpunktion, "
            "men stava namnen rätt."
        )

    if spec["facts"]:
        facts = "\n".join(
            f"{i}. {f['category']}, {f['expression']}, om {f['subject']}. {DESCRIPTIONS[f['category']]}"
            for i, f in enumerate(spec["facts"], start=1)
        )
        sensitive = f"Texten ska innehålla exakt de här känsliga uppgifterna och inga andra:\n\n{facts}"
    else:
        distractors = "\n".join(f"- {DISTRACTORS[c]}" for c in spec["distractors"])
        sensitive = (
            "Texten ska inte innehålla några känsliga uppgifter om någon person. Den ska däremot "
            f"nämna följande, utan att något avslöjas om någon person i texten:\n\n{distractors}"
        )

    rules = f"{EXPRESSION_RULES}\n{RULES}" if spec["facts"] else RULES
    sections = [
        INTRO,
        f"# Text att skriva\n\nSkriv en {spec['report']}. {style}",
        f"# Personer\n\n{persons}\n\n{NAMES}",
        f"# Känsliga uppgifter\n\n{sensitive}",
        f"# Regler\n\n{rules}",
    ]
    implicit = [f["category"] for f in spec["facts"] if f["expression"] == "implicit"]
    if implicit:
        words = "\n".join(f"- {c}: {', '.join(FORBIDDEN[c])}" for c in implicit)
        sections.append(
            "# Förbjudna ord\n\nDe här orden namnger en kategori där uppgiften är implicit och får "
            f"inte stå någonstans i texten. En stjärna står för valfri början eller slut på ordet.\n\n{words}"
        )
    sections.append(TAGGING)
    return "\n\n".join(sections)
