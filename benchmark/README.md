# Benchmark: datablad

Här finns koden som bygger och poängsätter benchmark-datasetet. Bakgrunden står i [PLAN_BENCHMARK.md](../PLAN_BENCHMARK.md).

## Status

| Del | Status | Fil |
|---|---|---|
| REDACT-SV | Klar | `data/redact/redact_sv.jsonl` |
| PrivoNest-SV | Inte påbörjad | |
| Syntetisk | Inte påbörjad | |

Data checkas inte in i repot. De återskapas med kommandona nedan.

## Kom igång

```
uv sync
uv run python -m benchmark.extern.redact        # hämtar 213 MB och konverterar den svenska delen
uv run python -m benchmark.schema.validate benchmark/data/redact/redact_sv.jsonl
uv run python -m benchmark.eval.score --gold benchmark/data/redact/redact_sv.jsonl --pred pred.jsonl
uv run pytest
```

## Struktur

```
schema/     JSON-schema för poster och prediktioner, samt validering
extern/     hämtning och konvertering av färdiga dataset
eval/       poängsättning
data/       hämtade och konverterade data (checkas inte in)
```

## Format

Varje rad i en JSONL-fil är en text med facit. Schemat finns i [schema/record.schema.json](schema/record.schema.json).

- **Offset** är Python-strängindex, alltså Unicode-kodpunkter, med `start` inklusive och `end` exklusive. Verktyg som räknar i UTF-16 eller byte måste räkna om.
- **`entities`** är personerna i texten, med roll och omnämnanden.
- **`identifiers`** är identifierare som inte är knutna till en person, till exempel platser och datum. I dataset utan personkoppling ligger alla identifierare här.
- **`sensitive`** är de känsliga uppgifterna, med kategori, uttryckstyp (`expression`) och vem uppgiften gäller (`subject`).
- **`ignore: true`** på ett känsligt spann betyder att kategorin nämns utan att något avslöjas om en person, till exempel i en negation. Spannet räknas varken som träff eller som falsklarm.

I den syntetiska delen krävs `expression` och `subject` på varje känsligt spann. I de färdiga dataseten får de vara `null`.

## REDACT-SV

| | |
|---|---|
| Källa | [guneeshvats/REDACT-PII-Benchmark](https://github.com/guneeshvats/REDACT-PII-Benchmark), filen `data/pii_benchmark_full.json` |
| Version | commit `252232ac`, låst med checksumma i [extern/redact.py](extern/redact.py) |
| Villkor | [REDACT Dataset Terms](https://github.com/guneeshvats/REDACT-PII-Benchmark/blob/252232ac29669beeb99cb6474eeb2736761be508/DATASET_TERMS.md). Forskning och benchmarking tillåts. Den som sprider data vidare ska länka till villkoren och ange att det är REDACT. |
| Ursprung | LLM-genererade texter. Inga riktiga personer. |
| Innehåll | E-post, ärendeanteckningar, chattar, loggrader, JSON-poster och nyckel-värde-listor i tolv domäner, bland annat myndighet, polis, vård och HR |
| Storlek | 561 texter, 134–8 075 tecken, median 1 610 |
| Användning | Bara test. Extern kontroll av explicita uttryck och identifierare. |

### Innehåll efter konvertering

Antal texter där kategorin räknas som positiv, och antal spann inom parentes.

| Kategori | Alla (561 texter) | Helt svenska (244 texter) |
|---|---|---|
| `HEALTH` | 85 (306) | 49 (196) |
| `CRIMINAL` | 34 (66) | 13 (39) |
| `POLITICS` | 11 (15) | 6 (6) |
| `TRADE_UNION` | 11 (32) | 3 (9) |
| `RELIGION` | 10 (12) | 1 (1) |
| `SEXUALITY` | 5 (7) | 0 |
| `ETHNICITY`, `GENETIC_BIOMETRIC` | 0 | 0 |
| Någon kategori | 147 | 70 |

Identifierare i alla texter: `PERSON` 3 372, `IDENTIFIER` 1 596, `DATE` 943, `EMAIL` 893, `LOCATION` 815, `ORGANISATION` 638, `PHONE` 546, `ADDRESS` 386 och `PERSONNUMMER` 364.

Exakta siffror skrivs till `data/redact/redact_sv.stats.json` vid varje konvertering.

### Mappning av etiketter

| REDACT | Vår kod |
|---|---|
| `Medical_Information`, `Allergy_Information`, `Sickness_Day_Records` | `HEALTH` |
| `Crime` | `CRIMINAL` |
| `Political_Party` | `POLITICS` |
| `Religion` | `RELIGION` |
| `Trade_Union_Membership` | `TRADE_UNION` |
| `Sex_Orientation` | `SEXUALITY` |
| Namn, personnummer, telefon, e-post, adress, ort, organisation, datum och olika nummer | motsvarande identifierare, se [extern/redact.py](extern/redact.py) |
| `Nationality`, `Citizenship_Status`, `PEP_Status`, `Disciplinary_Action`, `Gender`, `Marital_Status`, lön med flera | mappas inte |

Nationalitet och medborgarskap är inte etniskt ursprung, och PEP-status är inte politisk åsikt. Därför mappas de inte.

### Val vid konverteringen

- **Id.** `record_id` i REDACT är inte unikt: de 561 svenska texterna delar på 219 värden. Vårt id är i stället textens plats i rådatafilen, till exempel `redact-01245`.
- **Uttryckstyp.** REDACT anger inte om ett uttryck är explicit eller implicit. Alla spann sätts till `explicit`, eftersom de kommer från en katalog med ytformer som sjukdomsnamn, partinamn och brottsrubriceringar.
- **Person.** REDACT anger inte vem en uppgift gäller. `subject` är `null` och `entities` är tom.
- **Negationer och exempel.** Spann som REDACT märker med `disclosed: false` får `ignore: true`. Det gäller 24 känsliga spann. I 10 texter finns en kategori bara i sådana spann.
- **Nästlade spann.** REDACT märker både hela namnet och för- och efternamnet var för sig. Spann som ligger helt inuti ett annat spann med samma etikett tas bort (3 561 stycken).
- **Bortfall.** 48 av 14 693 spann pekar inte ut den sträng de ska och tas bort.

### Kända brister

- **Bara explicita uttryck.** Datasetet säger inget om implicita uttryck.
- **Etiketterna gäller ord, inte personer.** Ett partinamn eller en brottsrubricering märks även när ingen persons åsikt eller brott avslöjas. Precision i `POLITICS`, `TRADE_UNION`, `RELIGION` och `CRIMINAL` ska därför läsas med förbehåll.
- **Tunt i de flesta kategorier.** Bara `HEALTH` och `CRIMINAL` har fler än 11 positiva texter. Bland de helt svenska texterna går det i praktiken bara att mäta `HEALTH`, och med stor osäkerhet `CRIMINAL`.
- **Mycket kodväxling.** 317 av 561 texter blandar svenska med engelska eller andra språk. Uppdelningen finns i `source.code_switching`.
- **Konstlade strängar.** 37 av 438 känsliga spann är hopskrivna strängar utan mellanslag, som `PenicillinSvårAnafylaxi` och `ErikLindqvistPD4010Sjuk5Dagar`. De liknar inte text som människor skriver.
- **Ofullständiga identifierare.** 276 av rådatans 14 693 spann är delvisa eller maskerade former, till exempel `850315-XXXX`. De ligger kvar som vanliga identifierare.

## Poängsättning

Skriptet [eval/score.py](eval/score.py) jämför en metods prediktioner med facit. Prediktionerna är en JSONL-fil med en rad per text, enligt [schema/prediction.schema.json](schema/prediction.schema.json):

```json
{
  "id": "syn-000123",
  "categories": ["RELIGION", "HEALTH"],
  "sensitive": [{"start": 47, "end": 72, "category": "RELIGION", "subject": "Erik Lund"}],
  "identifiers": [{"start": 32, "end": 41, "type": "PERSON"}]
}
```

En metod lämnar bara de fält den stöder. Fält som saknas i hela filen poängsätts inte. Saknas `categories` härleds det från `sensitive`.

| Nivå | Fråga | Mått |
|---|---|---|
| Dokument | Finns kategorin i texten? | Recall, uppdelat på explicit och implicit, samt precision |
| Spann | Var står uppgiften? | Recall och precision |
| Attribution | Gäller uppgiften rätt person? | Andel rätt person bland hittade spann, samt recall med rätt person |
| Identifierare | Var står namn, personnummer med mera? | Recall och precision per typ |

Regler:

- **Överlapp.** Ett spann i facit är hittat om en prediktion med samma etikett överlappar det med minst ett tecken. `--iou` ställer ett hårdare krav.
- **`ignore`.** En text där kategorin bara finns i `ignore`-spann räknas inte för den kategorin. En prediktion som bara träffar ett `ignore`-spann räknas inte.
- **`ANY`** är detektion utan hänsyn till kategori: finns det något känsligt alls?
- **`MACRO`** är medelvärdet över de etiketter som förekommer i facit.
- **Person.** `subject` i en prediktion får vara ett person-id ur facit, en roll som bara en person har, eller personens namn som det står i texten. Ett namn som passar på flera personer räknas som fel.
- **Uppdelning.** Resultatet redovisas per del, per generator och, för REDACT, per grad av kodväxling. `--slice-by` väljer andra fält.
- **Osäkerhet.** Konfidensintervallen är 95 % och kommer från bootstrap över texter, 1 000 dragningar.
- **Jämförelse.** Med `--baseline` jämförs två metoder parvis på samma dragningar. Rapporten visar skillnaden, dess intervall och ett p-värde.

Begränsning: på dokumentnivå vet vi inte vilket uttryck metoden reagerade på. En text som har både ett explicit och ett implicit uttryck i samma kategori räknas som hittad i båda uppdelningarna. Generatorn bör därför undvika den kombinationen. Spannivån har inte det problemet.
