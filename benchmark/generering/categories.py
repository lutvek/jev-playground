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
        "*sjuk*", "ohälsa", "*ohälsa", "*hälsoproblem*", "hälsotillstånd*", "psykisk*", "*diagnos*",
        "depression*", "deprimerad*", "cancer*", "diabet*", "adhd", "add", "autism*", "autist*",
        "asperger*", "schizofren*", "bipolär*", "psykos*", "*syndrom*", "utmattning*", "utbränd*",
        "missbruk*", "*missbrukare", "alkoholist*", "funktionsnedsätt*", "*funktionsnedsättning*",
        "funktionsvariation*", "handikapp*", "gravid*", "*graviditet*",
    ),
    "ETHNICITY": (
        "etnisk*", "*etnicitet*", "härkomst", "*härkomst", "same", "samen", "samer", "samerna",
        "samisk*", "rom", "romen", "romer", "romerna", "romsk*", "romani", "kurd*", "assyri*",
        "syrian*", "somali*", "arab*", "tornedaling*", "kvän*", "judisk*", "invandrar*",
    ),
    "POLITICS": (
        "*politi*", "ideolog*", "socialdemokrat*", "sosse*", "moderat*", "sverigedemokrat*",
        "vänsterparti*", "vänsterpartist*", "centerparti*", "centerpartist*", "liberal*",
        "kristdemokrat*", "miljöparti*", "miljöpartist*", "sd", "kd", "mp", "kommunist*",
        "socialist*", "nazist*", "nationalsocialis*", "fascist*", "anarkist*", "feminist*",
        "*extremist*", "vänsterextrem*", "högerextrem*", "rösta", "röstar", "röstade",
    ),
    "RELIGION": (
        # Inte "*troende", som också fångar "förtroende".
        "religi*", "*religiös*", "troende", "icketroende", "gudstro*", "allah", "muslim*", "islam*",
        "kristen", "kristna", "*kristen", "kristendom*", "katolik*", "katolsk*", "protestant*",
        "luthersk*", "jude", "judar", "judarna", "judisk*", "judendom*", "hindu*", "buddhis*",
        "sikh*", "ateist*", "agnostiker", "jehova*", "pingstvän*", "mormon*", "ortodox*",
    ),
    "TRADE_UNION": (
        "fack", "facket", "fackets", "*fackförbund*", "*fackförening*", "fackmedlem*", "facklig*",
        "fackklubb*", "unionen", "lo", "tco", "saco", "if metall", "seko", "vårdförbund*",
        "lärarförbund*", "lärarnas riksförbund", "sveriges lärare", "byggnads", "akademikerförbund*",
    ),
    "SEXUALITY": (
        "*sexuell*", "*sexual*", "sexliv*", "gay", "lesbisk*", "flata", "bög*", "hbtq*", "hbt", "queer*",
    ),
    "GENETIC_BIOMETRIC": (
        "genetisk*", "gen", "genen", "gener", "generna", "dna", "arvsanlag*", "*mutation*", "brca*",
        "ärftlig*", "biometri*", "fingeravtryck*", "ansiktsigenkänning*", "irisskann*",
    ),
    "CRIMINAL": (
        # Inte "brott*" eller "*brott*", som också fångar "brottas", "avbrott" och "benbrott".
        # Inte "*åtal*", som också fångar "påtala".
        "brott", "brottet", "brotten", "brottets", "brotts*", "inbrott*", "narkotikabrott*",
        "våldsbrott*", "vapenbrott*", "hatbrott*", "ekobrott*", "skattebrott*", "sexualbrott*",
        "*brottsl*", "kriminell*", "kriminalitet*", "dömd*", "dömdes", "döms", "domen",
        "*fängelse*", "fängslad*", "*straff*", "åtal*", "åklagar*", "*misshandel*", "*stöld*",
        "snatt*", "*bedrägeri*", "rån", "rånet", "rånade", "mord*", "dråp*", "våldtäkt*",
        "belastningsregist*", "fälld*", "fälldes", "anhållen", "anhölls", "häkta*",
    ),
}

# Ord som namnger kategorin men också har vanliga andra betydelser, som "hälsa på", "kommunal
# förskola" och "läggningen" vid sänggåendet. De är förbjudna i implicita spann, men får stå i
# resten av texten utan att texten sorteras bort.
AMBIGUOUS = {
    "HEALTH": ("hälsa",),
    "ETHNICITY": ("ursprung", "ursprunget", "utländsk*", "utlandsfödd*"),
    "POLITICS": ("konservativ*",),
    "RELIGION": ("gud", "guds"),
    "TRADE_UNION": ("kommunal", "kommunals", "ledarna"),
    "SEXUALITY": ("läggning", "läggningen"),
    "GENETIC_BIOMETRIC": (),
    "CRIMINAL": ("gripen", "greps"),
}

# Ledtrådar som slumpas ut till varje uppgift, så att texterna inte alla blir likadana.
# För explicita uppgifter anger ledtråden vad som sägs, för implicita vad uppgiften kan
# märkas på. Implicita ledtrådar innehåller inga förbjudna ord.
CUES = {
    ("HEALTH", "explicit"): (
        "diabetes", "depression", "en hjärtsjukdom", "MS", "cancer under behandling", "adhd",
        "en ätstörning", "alkoholberoende", "graviditet", "epilepsi", "utmattningssyndrom",
    ),
    ("HEALTH", "implicit"): (
        "återkommande besök på en specialistmottagning",
        "medicin som personen hämtar ut eller tar",
        "ett hjälpmedel, till exempel rullator eller hörapparat",
        "behandling, till exempel dialys eller cellgifter",
        "en vistelse på ett behandlingshem",
        "att personen har färdtjänst",
        "följder i vardagen, till exempel att personen inte orkar arbeta",
        "besök på BUP eller beroendemottagningen",
    ),
    ("ETHNICITY", "explicit"): (
        "samisk", "romsk", "kurdisk", "tornedalsk", "assyrisk eller syriansk", "somalisk",
    ),
    ("ETHNICITY", "implicit"): (
        "en traditionell näring eller livsstil, till exempel renskötsel",
        "en kulturförening, festival eller högtid för gruppen",
        "traditionella kläder, smycken eller hantverk",
        "släktens bakgrund och var släkten har levt",
        "gruppens nationaldag eller flagga",
    ),
    ("POLITICS", "explicit"): (
        "Socialdemokraterna", "Moderaterna", "Sverigedemokraterna", "Vänsterpartiet",
        "Centerpartiet", "Liberalerna", "Kristdemokraterna", "Miljöpartiet",
    ),
    ("POLITICS", "implicit"): (
        "valarbete, till exempel i en valstuga",
        "ett uppdrag i en partiförening eller i kommunfullmäktige",
        "demonstrationer eller namninsamlingar för en viss sak",
        "insändare i lokaltidningen om en samhällsfråga",
        "medlemskap i ett ungdomsförbund till ett parti",
        "affischer eller dekaler med ett budskap i hemmet",
    ),
    ("RELIGION", "explicit"): (
        "islam", "kristendom i en frikyrka", "katolicism", "judendom", "ortodox kristendom",
        "buddhism", "hinduism", "Jehovas vittnen", "ateism", "sikhism",
    ),
    ("RELIGION", "implicit"): (
        "bön på bestämda tider",
        "fasta under en viss period",
        "regelbundna besök i en kyrka, moské, synagoga eller ett tempel",
        "kläder eller symboler som hör till en tro",
        "matregler, till exempel att inte äta fläsk",
        "en församling eller ett samfund som personen är aktiv i",
        "en högtid som personen firar",
        "en pilgrimsresa",
    ),
    ("TRADE_UNION", "explicit"): (
        "Kommunal", "IF Metall", "Unionen", "Vårdförbundet", "Sveriges Lärare", "Byggnads",
        "Handels", "Seko", "Transport", "Vision",
    ),
    ("TRADE_UNION", "implicit"): (
        "ett uppdrag som skyddsombud",
        "ett uppdrag som klubbordförande på arbetsplatsen",
        "förhandlingar med arbetsgivaren för kollegornas räkning",
        "deltagande i en strejk",
        "möten på förbundets lokala avdelning",
        "en kurs för förtroendevalda på arbetsplatsen",
    ),
    ("SEXUALITY", "explicit"): ("homosexuell", "bisexuell", "lesbisk", "gay", "queer"),
    ("SEXUALITY", "implicit"): (
        "en partner av samma kön",
        "en tidigare relation med någon av samma kön",
        "att personen går på Pride varje år",
        "att personen är aktiv i RFSL",
    ),
    ("GENETIC_BIOMETRIC", "explicit"): (
        "ett gentest som visar ett ärftligt anlag, till exempel BRCA",
        "ett DNA-test som visar släktskap",
        "fingeravtryck som används för att identifiera personen",
        "ansiktsigenkänning som används för att identifiera personen",
    ),
    ("CRIMINAL", "explicit"): (
        "en dom för misshandel", "misstanke om stöld", "en dom för rattfylleri",
        "åtal för bedrägeri", "en dom för narkotikabrott", "fängelse för rån",
        "misstanke om skadegörelse",
    ),
    ("CRIMINAL", "implicit"): (
        "tid på en anstalt, till exempel Kumla eller Hall",
        "fotboja",
        "möten med frivården eller en övervakare",
        "att personen har kallats till förhör hos polisen",
        "att personen inte får närma sig en viss person",
        "att körkortet är indraget efter en händelse i trafiken",
    ),
}

assert DESCRIPTIONS.keys() == DISTRACTORS.keys() == FORBIDDEN.keys() == AMBIGUOUS.keys() == set(CATEGORIES)
assert {category for category, _ in CUES} == set(CATEGORIES)


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group().casefold(), m.start(), m.end()) for m in re.finditer(r"\w+", text)]


def forbidden_matches(category: str, text: str, *, ambiguous: bool = True) -> list[tuple[int, int]]:
    """Platserna (start, end) i text där ett förbjudet ord för kategorin står.

    Med ambiguous=False räknas inte ord som också har andra vanliga betydelser.
    """
    patterns = FORBIDDEN[category] + (AMBIGUOUS[category] if ambiguous else ())
    tokens = _tokens(text)
    found = []
    for pattern in patterns:
        parts = pattern.casefold().split()
        for i in range(len(tokens) - len(parts) + 1):
            window = tokens[i : i + len(parts)]
            if all(fnmatchcase(token, part) for (token, _, _), part in zip(window, parts)):
                found.append((window[0][1], window[-1][2]))
    return sorted(set(found))
