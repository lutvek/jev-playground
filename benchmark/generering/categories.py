"""Det generatorn behöver veta om varje känslig kategori: beskrivning, distraktorer och förbjudna ord.

Förbjudna ord är ord som namnger kategorin. Ett implicit spann får inte innehålla något av dem,
och inte heller texten i övrigt när kategorin är implicit. Mönstren matchas mot hela ord utan
hänsyn till versaler: * står för valfri början eller slut, och flera ord matchar ord i följd.
Ett ord som "sjuk*" fångar alltså "sjukskriven" men inte "långtidssjukskriven", som "*sjuk*" fångar.
"""

import re
from fnmatch import fnmatchcase

from benchmark.schema.labels import CATEGORIES

DESCRIPTIONS = {
    "HEALTH": (
        "Hälsa: fysisk eller psykisk hälsa, sjukdom, funktionsnedsättning, vård och behandling, "
        "missbruk eller graviditet."
    ),
    "ETHNICITY": (
        "Etniskt ursprung: att någon tillhör en etnisk grupp, till exempel samer, romer eller kurder. "
        "Nationalitet och medborgarskap räknas inte."
    ),
    "POLITICS": "Politisk åsikt: partisympati, politiskt engagemang eller politisk övertygelse.",
    "RELIGION": "Religiös eller filosofisk övertygelse: tro, religionsutövning eller livsåskådning.",
    "TRADE_UNION": "Medlemskap i fackförening, eller ett fackligt uppdrag.",
    "SEXUALITY": "Sexualliv eller sexuell läggning.",
    "GENETIC_BIOMETRIC": (
        "Genetiska uppgifter, till exempel anlag eller DNA-resultat, och biometriska uppgifter som "
        "används för att identifiera någon, till exempel fingeravtryck."
    ),
    "CRIMINAL": "Lagöverträdelser: misstankar, åtal, domar och straff för brott.",
}

# Svåra negativa exempel: ord som liknar kategorin men inte avslöjar något om en person.
DISTRACTORS = {
    "HEALTH": "ett sjukdomsord i bildlig eller allmän betydelse, till exempel att något är sjukt dyrt",
    "ETHNICITY": (
        "en etnisk grupp, ett språk eller ett kulturevenemang som nämns utan koppling till någon "
        "person i texten"
    ),
    "POLITICS": "ett parti, ett val eller en politisk fråga som nämns utan att någons åsikt framgår",
    "RELIGION": (
        "en religiös byggnad eller högtid som nämns utan koppling till någons tro, till exempel som riktmärke"
    ),
    "TRADE_UNION": "ett fackförbund eller en strejk som nämns utan att någon i texten är medlem",
    "SEXUALITY": (
        "Pride eller en dejtingapp som nämns utan att något framgår om någons sexualliv eller läggning"
    ),
    "GENETIC_BIOMETRIC": "DNA eller arv i bildlig betydelse, till exempel att något ligger i företagets DNA",
    "CRIMINAL": (
        "brottslighet som omtalas allmänt, till exempel i området eller på nyheterna, utan att någon "
        "i texten är misstänkt"
    ),
}

FORBIDDEN = {
    "HEALTH": (
        "*sjuk*", "hälsa", "*hälsoproblem*", "hälsotillstånd*", "psykisk*", "*diagnos*",
        "depression*", "deprimerad*", "cancer*", "diabet*", "adhd", "add", "autism*", "autist*",
        "asperger*", "schizofren*", "bipolär*", "psykos*", "*syndrom*", "utmattning*", "utbränd*",
        "missbruk*", "*missbrukare", "alkoholist*", "funktionsnedsätt*", "*funktionsnedsättning*",
        "funktionsvariation*", "handikapp*", "gravid*", "*graviditet*",
    ),
    "ETHNICITY": (
        "etnisk*", "*etnicitet*", "härkomst", "*härkomst", "ursprung", "ursprunget",
        "same", "samen", "samer", "samerna", "samisk*", "rom", "romen", "romer", "romerna", "romsk*",
        "romani", "kurd*", "assyri*", "syrian*", "somali*", "arab*", "tornedaling*", "kvän*",
        "judisk*", "invandrar*", "utländsk*", "utlandsfödd*",
    ),
    "POLITICS": (
        "*politi*", "ideolog*", "socialdemokrat*", "sosse*", "moderat*", "sverigedemokrat*",
        "vänsterparti*", "vänsterpartist*", "centerparti*", "centerpartist*", "liberal*",
        "kristdemokrat*", "miljöparti*", "miljöpartist*", "sd", "kd", "mp", "kommunist*",
        "socialist*", "nazist*", "nationalsocialis*", "fascist*", "anarkist*", "feminist*",
        "konservativ*", "*extremist*", "vänsterextrem*", "högerextrem*", "rösta", "röstar", "röstade",
    ),
    "RELIGION": (
        "religi*", "*religiös*", "troende", "*troende", "gud", "guds", "allah", "muslim*", "islam*",
        "kristen", "kristna", "*kristen", "kristendom*", "katolik*", "katolsk*", "protestant*",
        "luthersk*", "jude", "judar", "judarna", "judisk*", "judendom*", "hindu*", "buddhis*",
        "sikh*", "ateist*", "agnostiker", "jehova*", "pingstvän*", "mormon*", "ortodox*",
    ),
    "TRADE_UNION": (
        "fack", "facket", "fackets", "*fackförbund*", "*fackförening*", "fackmedlem*", "facklig*",
        "fackklubb*", "unionen", "lo", "tco", "saco", "kommunal", "kommunals", "if metall", "seko",
        "vårdförbund*", "lärarförbund*", "lärarnas riksförbund", "sveriges lärare", "byggnads",
        "akademikerförbund*", "ledarna",
    ),
    "SEXUALITY": (
        "*sexuell*", "*sexual*", "sexliv*", "läggning", "läggningen", "gay", "lesbisk*", "flata",
        "bög*", "hbtq*", "hbt", "queer*",
    ),
    "GENETIC_BIOMETRIC": (
        "genetisk*", "gen", "genen", "gener", "generna", "dna", "arvsanlag*", "*mutation*", "brca*",
        "ärftlig*", "biometri*", "fingeravtryck*", "ansiktsigenkänning*", "irisskann*",
    ),
    "CRIMINAL": (
        # Inte "*brott*", som också fångar "avbrott" och "benbrott".
        "brott*", "inbrott*", "narkotikabrott*", "våldsbrott*", "vapenbrott*", "hatbrott*",
        "ekobrott*", "skattebrott*", "sexualbrott*", "*brottsl*", "kriminell*", "kriminalitet*",
        "dömd*", "dömdes", "döms", "domen", "*fängelse*", "fängslad*", "*straff*", "*åtal*",
        "åklagar*", "*misshandel*", "*stöld*", "snatt*", "*bedrägeri*", "rån", "rånet", "rånade",
        "mord*", "dråp*", "våldtäkt*", "belastningsregist*", "fälld*", "fälldes", "anhållen",
        "anhölls", "häkta*", "gripen", "greps",
    ),
}

assert DESCRIPTIONS.keys() == DISTRACTORS.keys() == FORBIDDEN.keys() == set(CATEGORIES)


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group().casefold(), m.start(), m.end()) for m in re.finditer(r"\w+", text)]


def forbidden_matches(category: str, text: str) -> list[tuple[int, int]]:
    """Platserna (start, end) i text där ett förbjudet ord för kategorin står."""
    tokens = _tokens(text)
    found = []
    for pattern in FORBIDDEN[category]:
        parts = pattern.casefold().split()
        for i in range(len(tokens) - len(parts) + 1):
            window = tokens[i : i + len(parts)]
            if all(fnmatchcase(token, part) for (token, _, _), part in zip(window, parts)):
                found.append((window[0][1], window[-1][2]))
    return sorted(set(found))
