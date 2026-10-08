# Benchmark: kod och datablad

Den här mappen innehåller koden som hämtar, kontrollerar och poängsätter benchmark-datan.

Filen är också benchmarkens *datablad*, alltså en beskrivning av varje dataset: var det kommer ifrån, vad det innehåller, hur det har gjorts om till vårt format och vilka brister det har.

Bakgrunden står i [PLAN_BENCHMARK.md](../PLAN_BENCHMARK.md). Begrepp som kan vara obekanta förklaras i [ORDLISTA.md](../ORDLISTA.md).

## Läget just nu

| Del | Status | Fil |
|---|---|---|
| REDACT-SV | Klar | `data/redact/redact_sv.jsonl` |
| PrivoNest-SV | Inte påbörjad | |
| Syntetisk | Inte påbörjad | |

Datafilerna sparas inte i repot, bland annat eftersom rådatan är 213 MB. De skapas på nytt med kommandona nedan.

## Kom igång

Det här behövs:

- Python 3.11 eller senare.
- [uv](https://docs.astral.sh/uv/), ett verktyg som installerar de Python-paket projektet behöver och kör kommandon i projektets miljö.
- Internetåtkomst till GitHub, för att hämta REDACT.

Kör kommandona från repots rotmapp, i den här ordningen:

```
uv sync
uv run python -m benchmark.extern.redact
uv run python -m benchmark.schema.validate benchmark/data/redact/redact_sv.jsonl
uv run pytest
```

Det här gör de:

1. **`uv sync`** installerar paketen som projektet behöver.
2. **`benchmark.extern.redact`** laddar ner REDACT (213 MB, bara första gången) och kontrollerar med en checksumma att det är exakt rätt fil. Sedan görs den svenska delen om till vårt format och sparas i `benchmark/data/redact/redact_sv.jsonl`, tillsammans med statistik i `redact_sv.stats.json`. Om någon text inte följer formatet efter konverteringen avbryts programmet.
3. **`benchmark.schema.validate`** kontrollerar att en fil följer formatet. Den skriver `OK`, eller en lista över felen med radnummer.
4. **`uv run pytest`** kör de automatiska testerna.

### När en metod har lämnat svar

Det finns ingen metod i repot än. När en metod har lämnat sina svar i en fil, här kallad `pred.jsonl` (se [Poängsättning](#poängsättning)), kontrollerar och poängsätter man dem så här:

```
uv run python -m benchmark.schema.validate --predictions pred.jsonl --gold benchmark/data/redact/redact_sv.jsonl
uv run python -m benchmark.eval.score --gold benchmark/data/redact/redact_sv.jsonl --pred pred.jsonl
```

Det första kommandot kontrollerar att svaren följer formatet och att de stämmer med texterna i facit. Svarsfilen måste stå före `--gold`, annars tolkas den som en facitfil. Det andra kommandot räknar poängen.

## Mappar och filer

```
schema/
  record.schema.json       formatet för en text med facit
  prediction.schema.json   formatet för en metods svar
  validate.py              programmet som kontrollerar formatet
  labels.py                läser kategorierna ur schemat, så att koden och schemat alltid har samma lista
extern/
  redact.py                hämtning och konvertering av REDACT
eval/
  score.py                 poängsättningen
jsonl.py                   läsning och skrivning av JSONL-filer
data/                      hämtade och konverterade data (sparas inte i repot)
```

De automatiska testerna ligger i mappen `tests/` i repots rot.

## Formatet

All data sparas som JSONL: en textfil där varje rad beskriver en text och dess facit. Exakt vilka fält som får och måste finnas beskrivs med JSON-schema i [schema/record.schema.json](schema/record.schema.json). Ett utförligt exempel med förklaring finns i [PLAN_BENCHMARK.md, avsnitt 2](../PLAN_BENCHMARK.md#2-hur-en-text-med-facit-sparas).

### Fälten

| Fält | Vad det betyder |
|---|---|
| `id` | Textens unika namn. |
| `part` | Vilken del texten kommer från: `redact`, `privonest` eller `synthetic`. |
| `split` | Om texten är till för `test`, `dev` eller `train`. Kan utelämnas. |
| `source` | Varifrån texten kommer. Innehållet varierar mellan delarna. |
| `text` | Själva texten. |
| `entities` | Personerna i texten, med id, roll (`REPORTER`, `SUBJECT` eller `OTHER`) och var i texten personen nämns (`mentions`). Tom lista om datasetet inte anger personer. |
| `identifiers` | Identifierare som inte hör till någon särskild person, till exempel orter och datum. I dataset som inte anger personer ligger alla identifierare här. |
| `sensitive` | De känsliga uppgifterna, med position, kategori, om uppgiften är explicit eller implicit (`expression`) och vem den gäller (`subject`). |

### Regler för positioner

En avgränsad bit av texten, till exempel en känslig uppgift eller ett namn, kallas ett *spann*. Längre ned kallas den ibland också *textbit*.

- **Var ett spann börjar och slutar** anges med `start` och `end`. `start` är det första tecknet som ingår och `end` det första tecknet som inte ingår. Första tecknet i texten har nummer 0.
- **Tecknen räknas som Python räknar dem**, i så kallade Unicode-kodpunkter. Varje bokstav, även å, ä och ö, är en kodpunkt. De flesta emojier är också en kodpunkt, men vissa, som flaggor, består av flera.
- **Program som räknar på ett annat sätt måste räkna om.** Räknar man i UTF-8-byte blir varje å, ä och ö två steg i stället för ett. Räknar man i UTF-16, som JavaScript gör, blir de flesta emojier två steg.
- **Ett spann får inte börja eller sluta med blanktecken**, alltså mellanslag, radbrytning eller tabb.

### Två särskilda regler

- **`ignore: true`** på en känslig uppgift betyder att kategorin nämns i texten utan att något avslöjas om en person, till exempel i ett nekande ("han är inte med i facket") eller ett påhittat exempel. Sådana uppgifter räknas varken som träffar eller som fel när poängen räknas ut.
- **`expression` och `subject` måste anges** i den syntetiska delen, eftersom vi själva bestämmer innehållet i de texterna och därför alltid vet svaret. I de färdiga dataseten får de vara `null`, alltså tomma, eftersom de dataseten inte alltid har den informationen.

### Vad kontrollprogrammet kontrollerar

Utöver det som står i schemat kontrollerar [schema/validate.py](schema/validate.py) att:

- varje textbit ligger inom texten och att `start` är mindre än `end`
- inget spann börjar eller slutar med blanktecken
- inga två texter, och inga två personer i samma text, har samma id
- varje `subject` hänvisar till en person som finns i `entities`
- `expression` och `subject` finns på alla känsliga uppgifter i den syntetiska delen

## REDACT-SV

REDACT är ett flerspråkigt dataset med texter som en AI har skrivit. Vi använder den svenska delen.

| | |
|---|---|
| Källa | [guneeshvats/REDACT-PII-Benchmark](https://github.com/guneeshvats/REDACT-PII-Benchmark), filen `data/pii_benchmark_full.json` |
| Version | Commit `252232ac`. Programmet [extern/redact.py](extern/redact.py) hämtar alltid exakt den versionen och kontrollerar den med en checksumma, så att konverteringen ger samma resultat varje gång. |
| Villkor | [REDACT Dataset Terms](https://github.com/guneeshvats/REDACT-PII-Benchmark/blob/252232ac29669beeb99cb6474eeb2736761be508/DATASET_TERMS.md). Forskning och benchmarking är tillåtet. Den som sprider datan vidare ska länka till villkoren och ange att det är REDACT. |
| Ursprung | Texterna är skrivna av en AI. De handlar inte om riktiga personer. |
| Innehåll | E-post, ärendeanteckningar, chattar, loggrader, JSON-poster och listor med fält och värden, från tolv områden, bland annat myndighet, polis, vård och HR. |
| Storlek | 561 texter. Den kortaste är 134 tecken, den längsta 8 075 och medianen 1 610. |
| Används till | Bara test. Den används för att kontrollera resultaten mot data som någon annan har byggt, för uppgifter som sägs rakt ut och för identifierare. |

### Innehåll efter konverteringen

Tabellen visar hur många texter som innehåller varje kategori. Inom parentes står hur många märkta uppgifter det rör sig om totalt, eftersom en text kan innehålla flera.

| Kategori | Alla texter (561) | Bara helt svenska texter (244) |
|---|---|---|
| `HEALTH` | 85 (306) | 49 (196) |
| `CRIMINAL` | 34 (66) | 13 (39) |
| `POLITICS` | 11 (15) | 6 (6) |
| `TRADE_UNION` | 11 (32) | 3 (9) |
| `RELIGION` | 10 (12) | 1 (1) |
| `SEXUALITY` | 5 (7) | 0 |
| `ETHNICITY`, `GENETIC_BIOMETRIC` | 0 | 0 |
| Någon känslig kategori | 147 | 70 |

Antal identifierare i alla 561 texter:

| Typ | Antal |
|---|---|
| `PERSON` | 3 372 |
| `IDENTIFIER` | 1 596 |
| `DATE` | 943 |
| `EMAIL` | 893 |
| `LOCATION` | 815 |
| `ORGANISATION` | 638 |
| `PHONE` | 546 |
| `ADDRESS` | 386 |
| `PERSONNUMMER` | 364 |

De exakta siffrorna skrivs till `data/redact/redact_sv.stats.json` varje gång konverteringen körs.

### Hur REDACT:s etiketter kopplas till våra koder

REDACT använder egna namn på sina etiketter. Så här har de kopplats till våra koder:

| REDACT | Vår kod |
|---|---|
| `Medical_Information`, `Allergy_Information`, `Sickness_Day_Records` | `HEALTH` |
| `Crime` | `CRIMINAL` |
| `Political_Party` | `POLITICS` |
| `Religion` | `RELIGION` |
| `Trade_Union_Membership` | `TRADE_UNION` |
| `Sex_Orientation` | `SEXUALITY` |
| Namn, personnummer, telefon, e-post, adress, ort, organisation, datum och olika nummer | Motsvarande identifierare. Hela listan står i [extern/redact.py](extern/redact.py). |

Några av REDACT:s etiketter kopplas inte till någon kod:

- **Nationalitet och medborgarskap** (`Nationality`, `Citizenship_Status`) ligger nära etniskt ursprung men är inte detsamma.
- **PEP-status** (`PEP_Status`), alltså att någon har ett viktigt offentligt uppdrag, är inte detsamma som en politisk åsikt.
- **Disciplinära åtgärder** (`Disciplinary_Action`) gäller åtgärder från en arbetsgivare, inte brott.
- **Övriga**, som kön (`Gender`), civilstånd (`Marital_Status`), ålder (`Age`), yrkestitel (`Business_Title`), lön (`Compensation_and_Salary`), lösenord (`Password`) och kontoutdrag (`Account_Statements`), hör inte till de känsliga kategorierna och inte heller till våra identifierare.

Hur många märkningar av varje sort som inte kopplades står i statistikfilen, på raderna som börjar med `omappad:`.

### Val vi gjorde vid konverteringen

- **Id.** REDACT:s eget id, `record_id`, är inte unikt: de 561 svenska texterna delar på bara 219 olika värden. Vi ger i stället varje text ett id efter dess plats i REDACT:s fil, till exempel `redact-01245`.
- **Explicit eller implicit.** REDACT anger inte om en uppgift sägs rakt ut eller inte. Vi har märkt alla som `explicit`, eftersom de är tagna från listor över ord och uttryck som sjukdomsnamn, partinamn och brottsrubriceringar.
- **Vem uppgiften gäller.** REDACT anger inte det. `subject` är därför `null` och `entities` är tom.
- **Nekanden och exempel.** REDACT markerar själv uppgifter som inte avslöjar något om en person, med `disclosed: false`. De får `ignore: true` hos oss. Det gäller 24 känsliga uppgifter. I 10 texter finns en kategori bara i sådana uppgifter, och de texterna räknas inte som positiva för den kategorin.
- **Dubbelmärkningar.** REDACT märker till exempel både hela namnet "Erik Lund" och "Erik" och "Lund" var för sig. Vi tar bort märkningar som ligger helt inuti en annan märkning med samma kod hos oss, efter kopplingen ovan. För känsliga uppgifter måste också `ignore` vara lika. Det gäller 3 561 märkningar.
- **Felaktiga märkningar.** 48 av REDACT:s 14 693 märkningar i de svenska texterna pekar inte på den text de ska. De tas bort.

### Kända brister

- **Bara uppgifter som sägs rakt ut.** Datasetet säger inget om hur bra metoder är på uppgifter som går att lista ut av sammanhanget.
- **Etiketterna sitter på ord, inte på personer.** Ett partinamn eller en brottsrubricering är märkt även när texten inte avslöjar någons åsikt eller brott. Resultaten för `POLITICS`, `TRADE_UNION`, `RELIGION` och `CRIMINAL` ska därför läsas med försiktighet, särskilt precision. En metod som förstår sammanhanget och låter bli att flagga ett partinamn som inte säger något om någon får det räknat som en miss, vilket sänker recall. En metod som flaggar varje partinamn får i stället för hög precision.
- **Få exempel i de flesta kategorier.** Bara `HEALTH` och `CRIMINAL` finns i fler än 11 texter. Bland de helt svenska texterna går det i praktiken bara att mäta `HEALTH`, och med stor osäkerhet `CRIMINAL`.
- **Många texter blandar språk.** 317 av de 561 texterna blandar svenska med engelska eller andra språk. Hur mycket varje text blandar står i fältet `source.code_switching`: `none` (bara svenska), `light` eller `heavy`.
- **Konstlade ord.** Ett 40-tal av de 438 känsliga uppgifterna är ihopskrivna ord utan mellanslag, som `PenicillinSvårAnafylaxi` och `ErikLindqvistPD4010Sjuk5Dagar`. Så skriver inte människor.
- **Ofullständiga identifierare.** 276 av rådatans 14 693 märkningar är delvis dolda eller ofullständiga, till exempel `850315-XXXX`. De ligger kvar som vanliga identifierare.

## Poängsättning

Programmet [eval/score.py](eval/score.py) jämför en metods svar med facit och räknar ut hur bra metoden är.

### Vad metoden ska lämna in

Metoden ska lämna in en JSONL-fil med en rad per text, i formatet som beskrivs i [schema/prediction.schema.json](schema/prediction.schema.json). Här är ett exempel för texten om Erik Lund i [PLAN_BENCHMARK.md](../PLAN_BENCHMARK.md#2-hur-en-text-med-facit-sparas):

```json
{
  "id": "syn-000123",
  "categories": ["RELIGION", "HEALTH"],
  "sensitive": [{"start": 47, "end": 72, "category": "RELIGION", "subject": "Erik Lund"}],
  "identifiers": [{"start": 32, "end": 41, "type": "PERSON"}]
}
```

| Fält | Vad det betyder |
|---|---|
| `id` | Vilken text svaret gäller. Måste finnas i facit. |
| `categories` | Vilka känsliga kategorier metoden tror att texten innehåller. Utelämnas fältet räknas kategorierna ut från `sensitive`. |
| `sensitive` | Var metoden tror att de känsliga uppgifterna står, vilken kategori de har och, om metoden kan, vem de gäller. |
| `identifiers` | Var metoden tror att identifierare står, och vilken typ de har. |

En metod tar bara med de fält den klarar av. En metod som bara kan säga vilka kategorier en text innehåller lämnar till exempel bara `id` och `categories`. Ett fält som saknas i hela filen poängsätts inte.

`subject`, alltså vem uppgiften gäller, kan anges på tre sätt:

- som personens id i facit, till exempel `P1`, om metoden har fått se personlistan
- som en roll, till exempel `SUBJECT`, om bara en person har den rollen
- som personens namn så som det står i texten. Det räcker med en del av namnet, till exempel "Erik" för "Erik Lund", så länge det bara passar in på en person. Ett namn som passar in på flera personer räknas som fel.

Det måste finnas ett svar för varje text i facit. Annars avbryts programmet. Med `--allow-missing` räknas texter som saknar svar i stället som att metoden inte hittade något i dem.

### Vad som mäts

Poängen räknas på fyra nivåer:

| Nivå | Frågan som besvaras | Mått |
|---|---|---|
| Dokument | Förstår metoden att texten innehåller kategorin? | Recall, separat för explicita och implicita uppgifter, samt precision. |
| Spann | Pekar metoden också ut var i texten uppgiften står? | Recall, separat för explicita och implicita uppgifter, samt precision. |
| Attribution | Kopplar metoden uppgiften till rätt person? | Andel med rätt person bland de uppgifter metoden hittade, och andel av alla uppgifter som både hittades och fick rätt person. |
| Identifierare | Hittar metoden namn, personnummer och liknande? | Recall och precision för varje typ. |

*Recall* är hur stor andel av det som finns som metoden hittar. *Precision* är hur stor andel av det metoden flaggar som är rätt.

I rapporten har måtten de här namnen:

| Namn | Betyder |
|---|---|
| `recall` | Andel av uppgifterna (eller texterna) i facit som metoden hittade. |
| `recall_explicit`, `recall_implicit` | Samma sak, men bara för explicita respektive implicita uppgifter. |
| `precision` | Andel av metodens flaggningar som var rätt. |
| `accuracy` | Attribution: andel med rätt person bland de uppgifter som metoden hittade. |
| `recall_with_subject` | Attribution: andel av alla uppgifter i facit som metoden både hittade och kopplade till rätt person. |

### Räkneexempel

Om metoden i exemplet ovan körs mot facit för texten om Erik Lund blir resultatet:

- **Dokumentnivå: allt rätt.** Metoden har angett både `RELIGION` och `HEALTH` under `categories`, och texten innehåller båda.
- **Spannivå: hälften rätt.** Metoden pekar ut var religionsuppgiften står men inte var hälsouppgiften står. Recall blir därför 1 av 2, alltså 0,50.
- **Attribution: rätt person för religion.** Namnet "Erik Lund" passar på person P1, som är den uppgiften gäller. Bland de uppgifter som metoden hittade har alla rätt person (`accuracy` 1,00). Men eftersom hälsouppgiften inte hittades är det bara 1 av 2 uppgifter som både hittades och fick rätt person (`recall_with_subject` 0,50).
- **Identifierare: allt rätt.** Metoden har hittat namnet.

### Regler

- **Överlapp.** En uppgift i facit räknas som hittad om metoden har pekat ut en textbit med samma etikett som överlappar den med minst ett tecken. Med `--iou` kan man kräva mer: `--iou 0.5` kräver att den gemensamma delen är minst hälften av hela området som de två textbitarna täcker tillsammans.
- **`ignore`.** En text där en kategori bara finns i `ignore`-märkta uppgifter räknas inte alls för den kategorin. Om metoden pekar ut en textbit som bara träffar en `ignore`-märkt uppgift räknas det varken som rätt eller fel.
- **`ANY`** är en extra rad i resultatet som bortser från kategorin: hittar metoden att det finns något känsligt alls?
- **`MACRO`** är en extra rad med medelvärdet över kategorierna, där varje kategori väger lika mycket oavsett hur vanlig den är. Då syns det om metoden är dålig på ovanliga kategorier, även om den är bra på de vanliga. Bara kategorier där måttet går att räkna ut tas med: för recall de som finns i facit, för precision de som metoden har flaggat.
- **Uppdelning.** Resultaten redovisas för varje del (`part`), för varje del och AI-modell som skrev texterna (`source.generator`), och, för REDACT, för varje del och grad av språkblandning (`source.code_switching`). Med `--slice-by` väljer man själv uppdelningen. Det ersätter standarduppdelningen, så den som vill ha kvar den måste ange den också. Kommatecken kombinerar fält: `--slice-by part,source.domain` ger en uppdelning per del och område. Standarduppdelningen motsvarar `--slice-by part --slice-by part,source.generator --slice-by part,source.code_switching`.
- **Osäkerhet.** Varje resultat har ett 95-procentigt konfidensintervall, ett intervall som det verkliga värdet troligen ligger inom. Det räknas fram med bootstrap: programmet drar 1 000 slumpvisa urval av texterna och räknar om resultatet för varje urval.
- **Jämförelse med en annan metod.** Med `--baseline` följt av en annan metods svarsfil jämförs de två metoderna på samma slumpvisa urval. Rapporten visar skillnaden mellan dem, ett konfidensintervall för skillnaden och ett p-värde. Ett lågt p-värde, till exempel under 0,05, tyder på att skillnaden sannolikt inte bara beror på slumpen.

### Inställningar

| Inställning | Vad den gör |
|---|---|
| `--gold FIL ...` | Facit. Krävs. Kan vara en eller flera filer. |
| `--pred FIL` | Metodens svar. Krävs. |
| `--baseline FIL` | En annan metods svar att jämföra med. |
| `--out FIL` | Sparar hela rapporten som JSON, för vidare bearbetning. |
| `--slice-by FÄLT[,FÄLT]` | Väljer hur resultatet delas upp, i stället för standarduppdelningen. Kan anges flera gånger. Kommatecken kombinerar fält. |
| `--bootstrap N` | Antal slumpvisa urval för konfidensintervallen. Standard 1 000. `0` stänger av dem. |
| `--seed N` | Startvärde för slumpen, så att samma körning alltid ger samma intervall. Standard 0. |
| `--iou X` | Hur mycket textbitar måste överlappa för att räknas som träff. Standard 0, alltså räcker det med ett tecken. |
| `--allow-missing` | Räknar texter utan svar som att metoden inte hittade något. |

### Så läser man rapporten

Programmet skriver ut en tabell per delmängd och nivå. Varje ruta ser ut så här:

```
0.800 [0.69–0.91] (n=50)
```

- `0.800` är resultatet, här en recall på 0,80.
- `[0.69–0.91]` är konfidensintervallet.
- `n=50` är hur många resultatet bygger på. För recall är det antalet uppgifter eller texter i facit, för precision antalet flaggningar från metoden.

Ett streck (`–`) betyder att det inte finns något att räkna på, till exempel precision för en kategori som metoden aldrig flaggade.

### En begränsning

På dokumentnivå vet vi inte vilken uppgift i texten metoden reagerade på. Om en text innehåller både en explicit och en implicit uppgift i samma kategori, och metoden flaggar kategorin, räknas båda som hittade, även om metoden kanske bara förstod den explicita. Generatorn bör därför undvika att skriva texter med den kombinationen. På spannivå finns inte problemet, eftersom metoden där måste peka ut var varje uppgift står.
