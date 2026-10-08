# Benchmark: kod och datablad

Den här mappen innehåller koden som hämtar, kontrollerar och poängsätter benchmark-datan.

Filen är också benchmarkens *datablad*, alltså en beskrivning av varje dataset: var det kommer ifrån, vad det innehåller, hur det har gjorts om till vårt format och vilka brister det har.

Bakgrunden står i [PLAN_BENCHMARK.md](../PLAN_BENCHMARK.md). Begrepp som kan vara obekanta förklaras i [ORDLISTA.md](../ORDLISTA.md).

## Läget just nu

| Del | Status | Fil |
|---|---|---|
| REDACT-SV | Klar | `data/redact/redact_sv.jsonl` |
| PrivoNest-SV | Inte påbörjad | |
| Syntetisk | Generatorn finns och har provkörts. Den fullständiga genereringen återstår. | `data/synthetic/<omgång>.jsonl` |

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
uv run python -m benchmark.eval.score --gold benchmark/data/redact/redact_sv.jsonl --pred pred.jsonl
uv run pytest
```

Det här gör de:

1. **`uv sync`** installerar paketen som projektet behöver.
2. **`benchmark.extern.redact`** laddar ner REDACT (213 MB, bara första gången) och kontrollerar med en checksumma att det är exakt rätt fil. Sedan görs den svenska delen om till vårt format och sparas i `benchmark/data/redact/redact_sv.jsonl`, tillsammans med statistik i `redact_sv.stats.json`. Om någon text inte följer formatet efter konverteringen avbryts programmet.
3. **`benchmark.schema.validate`** kontrollerar att en fil följer formatet. Den skriver `OK`, eller en lista över felen med radnummer. Lägg till `--predictions` för att kontrollera en fil med en metods svar i stället, och `--gold` följt av facitfilen för att också kontrollera svaren mot texterna.
4. **`benchmark.eval.score`** räknar poäng för en metods svar. Filen `pred.jsonl` är de svar som metoden har gett, se [Poängsättning](#poängsättning). Det finns ingen metod i repot än, så det här steget går inte att köra förrän någon har tagit fram en sådan fil.
5. **`uv run pytest`** kör de automatiska testerna.

Hur man tar fram de syntetiska texterna står i [Syntetisk del](#syntetisk-del).

## Mappar och filer

```
schema/
  record.schema.json       formatet för en text med facit
  prediction.schema.json   formatet för en metods svar
  validate.py              programmet som kontrollerar formatet
  labels.py                läser kategorierna ur schemat, så att koden och schemat alltid har samma lista
extern/
  redact.py                hämtning och konvertering av REDACT
generering/
  spec.py                  slumpar fram scenariospecar och skriver dem med instruktionerna till AI:n
  prompt.py                instruktionerna till AI:n
  tags.py                  tolkar AI:ns markeringar
  checks.py                de automatiska kontrollerna
  build.py                 gör om AI:ns svar till texter med facit och sorterar bort dem som inte håller
  categories.py            beskrivningar, ledtrådar och förbjudna ord för varje kategori
  resources.py             namn, personnummer, orter och gator
  llm.py                   hur en koppling till en AI-modell ska se ut
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

- **Var en bit text börjar och slutar** anges med `start` och `end`. `start` är det första tecknet som ingår och `end` det första tecknet som inte ingår. Första tecknet i texten har nummer 0.
- **Tecknen räknas som Python räknar dem**, där varje bokstav, även å, ä och ö, och varje emoji räknas som ett tecken. Program som räknar på ett annat sätt måste räkna om. Räknar man i byte blir varje å, ä och ö två steg i stället för ett. Räknar man i UTF-16, som JavaScript gör, blir varje emoji två steg.
- **En textbit får inte börja eller sluta med mellanslag.**

### Två särskilda regler

- **`ignore: true`** på en känslig uppgift betyder att kategorin nämns i texten utan att något avslöjas om en person, till exempel i ett nekande ("han är inte med i facket") eller ett påhittat exempel. Sådana uppgifter räknas varken som träffar eller som fel när poängen räknas ut.
- **`expression` och `subject` måste anges** i den syntetiska delen, eftersom vi själva bestämmer innehållet i de texterna och därför alltid vet svaret. I de färdiga dataseten får de vara `null`, alltså tomma, eftersom de dataseten inte alltid har den informationen.

### Vad kontrollprogrammet kontrollerar

Utöver det som står i schemat kontrollerar [schema/validate.py](schema/validate.py) att:

- varje textbit ligger inom texten och att `start` är mindre än `end`
- ingen textbit börjar eller slutar med mellanslag
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

- **Nationalitet och medborgarskap** säger inget om etniskt ursprung.
- **PEP-status**, alltså att någon har ett viktigt offentligt uppdrag, säger inget om personens politiska åsikter.
- **Disciplinära åtgärder** gäller åtgärder från en arbetsgivare, inte brott.
- **Övriga**, som kön, civilstånd, ålder, yrkestitel, lön, lösenord och kontoutdrag, hör inte till de känsliga kategorierna och inte heller till våra identifierare.

### Val vi gjorde vid konverteringen

- **Id.** REDACT:s eget id, `record_id`, är inte unikt: de 561 svenska texterna delar på bara 219 olika värden. Vi ger i stället varje text ett id efter dess plats i REDACT:s fil, till exempel `redact-01245`.
- **Explicit eller implicit.** REDACT anger inte om en uppgift sägs rakt ut eller inte. Vi har märkt alla som `explicit`, eftersom de är tagna från listor över ord och uttryck som sjukdomsnamn, partinamn och brottsrubriceringar.
- **Vem uppgiften gäller.** REDACT anger inte det. `subject` är därför `null` och `entities` är tom.
- **Nekanden och exempel.** REDACT markerar själv uppgifter som inte avslöjar något om en person, med `disclosed: false`. De får `ignore: true` hos oss. Det gäller 24 känsliga uppgifter. I 10 texter finns en kategori bara i sådana uppgifter, och de texterna räknas inte som att de innehåller kategorin.
- **Dubbelmärkningar.** REDACT märker till exempel både hela namnet "Erik Lund" och "Erik" och "Lund" var för sig. Vi tar bort märkningar som ligger helt inuti en annan märkning med samma etikett, vilket gäller 3 561 märkningar.
- **Felaktiga märkningar.** 48 av REDACT:s 14 693 märkningar i de svenska texterna pekar inte på den text de ska. De tas bort.

### Kända brister

- **Bara uppgifter som sägs rakt ut.** Datasetet säger inget om hur bra metoder är på uppgifter som går att lista ut av sammanhanget.
- **Etiketterna sitter på ord, inte på personer.** Ett partinamn eller en brottsrubricering är märkt även när texten inte avslöjar någons åsikt eller brott. Resultaten för `POLITICS`, `TRADE_UNION`, `RELIGION` och `CRIMINAL` ska därför läsas med försiktighet, särskilt precision. En metod som flaggar varje partinamn får rätt även när partinamnet inte säger något om någon, medan en metod som förstår sammanhanget och låter bli får fel.
- **Få exempel i de flesta kategorier.** Bara `HEALTH` och `CRIMINAL` finns i fler än 11 texter. Bland de helt svenska texterna går det i praktiken bara att mäta `HEALTH`, och med stor osäkerhet `CRIMINAL`.
- **Många texter blandar språk.** 317 av de 561 texterna blandar svenska med engelska eller andra språk. Hur mycket varje text blandar står i fältet `source.code_switching`: `none` (bara svenska), `light` eller `heavy`.
- **Konstlade ord.** Ett 40-tal av de 438 känsliga uppgifterna är ihopskrivna ord utan mellanslag, som `PenicillinSvårAnafylaxi` och `ErikLindqvistPD4010Sjuk5Dagar`. Så skriver inte människor.
- **Ofullständiga identifierare.** 276 av de 14 693 märkningarna är delvis dolda eller ofullständiga, till exempel `850315-XXXX`. De ligger kvar som vanliga identifierare.

## Syntetisk del

Den syntetiska delen består av texter som en AI skriver på vår beställning. Bakgrunden står i [PLAN_BENCHMARK.md, avsnitt 4](../PLAN_BENCHMARK.md#4-egna-ai-skrivna-texter). Koden finns i mappen [generering/](generering/).

### Så tar man fram texter

```
uv run python -m benchmark.generering.spec --name pilot --n 50 --seed 1
uv run python -m benchmark.generering.build --specs benchmark/data/synthetic/pilot.specs.jsonl \
    --responses benchmark/data/synthetic/pilot.responses.jsonl
```

1. **`benchmark.generering.spec`** slumpar fram 50 beställningar, så kallade scenariospecar, och sparar dem i `pilot.specs.jsonl`. Varje rad innehåller också den färdiga instruktionen till AI:n, i fältet `prompt`. Samma `--seed` ger alltid samma specar. Med `--split` anger man om texterna är till för `test`, `dev` eller `train`.
2. **AI:n svarar.** Varje `prompt` skickas till AI-modellen, och svaren sparas i `pilot.responses.jsonl` med en rad per svar: `{"scenario_id": ..., "generator": ..., "response": ...}`. `generator` är modellens namn. Repot har ingen färdig koppling till en modell, så det här steget görs med valfritt verktyg. Hur en sådan koppling ska se ut står i [generering/llm.py](generering/llm.py).
3. **`benchmark.generering.build`** tolkar markeringarna i svaren, gör om dem till texter med facit och kör kontrollerna. Programmet skriver fyra filer:
   - `pilot.jsonl`: de godkända texterna
   - `pilot.rejected.jsonl`: de bortsorterade svaren, med skälen
   - `pilot.stats.json`: statistik, se nedan
   - `pilot.retry.specs.jsonl`: specarna för de scenarier som ännu saknar en godkänd text

**Nya försök.** Skicka instruktionerna i `pilot.retry.specs.jsonl` till AI:n igen, spara svaren i en ny fil och kör `build` med båda svarsfilerna efter `--responses`. Det första godkända svaret för varje scenario används, och senare svar för samma scenario hoppas över. På så sätt krymper inte de kombinationer av kategori och uttryckstyp där många svar sorteras bort.

### Vad en scenariospec innehåller

| Del | Innehåll |
|---|---|
| Typ av underrättelse | En av sex allmänna typer: orosanmälningar och klagomål på grannar från privatpersoner, underrättelser från polisen och från andra myndigheter, och orosanmälningar från skola och vård. |
| Personer | Avsändaren (P0), den som texten främst gäller (P1) och i hälften av texterna en tredje person (P2): en partner, en annan vuxen eller ett barn. |
| Känsliga uppgifter | 1–3 per text. Varje uppgift har kategori, uttryckstyp, vem den gäller och en ledtråd. |
| Ledtrådar | Slumpas ur en lista för varje kombination av kategori och uttryckstyp, till exempel "fasta under en viss period" för en implicit uppgift om religion. Utan ledtrådar skriver AI:n gärna samma sak varje gång. |
| Distraktorer | En fjärdedel av texterna har inga känsliga uppgifter. De har i stället 1–2 *distraktorer*: ord som liknar en känslig kategori utan att avslöja något om någon, till exempel en moské som nämns som riktmärke. |
| Ort, datum och adress | Slumpas ut, adressen i hälften av texterna, så att texterna inte alla utspelar sig på samma gata samma dag. |
| Stil | Längd, ton och, i texter från privatpersoner, stavfel. |

Regler för slumpningen:

- **Lika många uppgifter i varje kombination.** Varje ny uppgift väljs bland de kombinationer av kategori och uttryckstyp som har fått minst uppgifter hittills. 1 000 texter ger ungefär 80 uppgifter per kombination. Det räcker till kravet på minst 50 även om en del sorteras bort.
- **Högst en uppgift per kategori och text.** Då innehåller en text aldrig både en explicit och en implicit uppgift i samma kategori, se [En begränsning](#en-begränsning).
- **Inga implicita genetiska eller biometriska uppgifter**, eftersom sådana uttryck nästan aldrig förekommer.
- **Bara vuxna får känsliga uppgifter.** En privatperson kan skriva om sig själv, men en polis eller handläggare gör det aldrig.
- **Par av samma kön bara när det ingår i facit.** En partner av samma kön avslöjar sexuell läggning. Partnern får därför samma kön som P1 bara när specen har en uppgift om läggningen hos någon av de två. Annars får partnern motsatt kön.
- **Namnen slumpas oberoende av uppgifterna**, så att ett namn aldrig avslöjar en kategori.
- **Inga typer eller avsändare som i sig avslöjar en kategori.** Kriminalvården och psykiatrin är inte med. Inte heller tips om fusk eller svartarbete, eftersom ett sådant tips är en misstanke om brott.

### Platshållare för namn och personnummer

Namnen ska hämtas från SCB:s namnstatistik och personnumren från Skatteverkets lista över testpersonnummer. Ingen av källorna går att nå från molnmiljön än. Tills vidare används en kort lista med vanliga namn, och personnummer med fel kontrollsiffra, som därför inte kan tillhöra någon. Specar och texter som bygger på platshållarna har `placeholders: true`. De ska bytas ut före den fullständiga genereringen.

### Markeringarna

AI:n markerar uppgifterna med taggar direkt i texten:

```
Jag skriver om <PERSON P1>Erik Lund</PERSON>. Han <RELIGION implicit P1>går i moskén varje fredag</RELIGION>.
```

- **Känsliga uppgifter** har kategori, `explicit` eller `implicit`, och vem uppgiften gäller.
- **Namn och personnummer** har typ och person. Bara namn markeras, inte "han" eller "grannen". Då mäts identifierare på samma sätt som i REDACT.
- **Andra identifierare**, som `DATE`, `LOCATION`, `ADDRESS`, `ORGANISATION` och `IDENTIFIER`, markeras utan person och hamnar i fältet `identifiers`.
- **Taggar får ligga inuti varandra** men inte korsa varandra. Versaler och gemener räknas lika. Allt annat som ser ut som en tagg, till exempel `<br>`, gör att svaret sorteras bort.

### Kontrollerna

Ett svar sorteras bort om någon kontroll slår till. Det här är kontroll 1 och 2 i [planens avsnitt 5](../PLAN_BENCHMARK.md#5-kvalitetskontroll-utan-handmärkning). Kontroll 3, granskningen av en annan AI-modell, finns inte än.

| Skäl | Vad det betyder |
|---|---|
| `tomt-svar` | Svaret är tomt. |
| `taggar` | Markeringarna går inte att tolka, eller pekar på en person som inte finns i specen. |
| `format` | Texten klarar inte formatkontrollen. |
| `saknad-uppgift`, `oväntad-uppgift` | De markerade uppgifterna stämmer inte med specen, till exempel fel person eller fel uttryckstyp. |
| `förbjudet-ord` | En implicit uppgift innehåller ett ord som namnger kategorin, till exempel "muslim" för `RELIGION`. |
| `omärkt-kategoriord` | Ett ord som namnger en kategori står utanför de explicita uppgifterna. Det fångar uppgifter som AI:n har skrivit men inte markerat. |
| `namn-saknas`, `fel-namn`, `omärkt-namn` | Ett namn ur specen saknas, är markerat som fel person eller står utan markering. Ett genitiv-s får stå utanför taggen. |
| `personnummer` | Ett personnummer saknas, är fel eller står utan markering. |

**Förbjudna ord.** Listorna står i [generering/categories.py](generering/categories.py). De tar med böjningsformer och vanliga sammansättningar, men inte felstavningar. Tre regler hindrar att kontrollen sorterar bort rimliga texter:

- **Distraktorer** får innehålla ord från sin kategori.
- **Ord med andra vanliga betydelser**, som "hälsa" i "hälsa på" och "kommunal" i "kommunal förskola", är förbjudna i implicita uppgifter men får stå i resten av texten.
- **Ord som hör till två kategorier**, som "sexualbrott", räknas som markerade om de står i en explicit uppgift i någon av kategorierna.

### Statistiken

`pilot.stats.json` visar hur många svar som godkändes och sorterades bort. Siffrorna finns totalt, per skäl, per kombination av kategori och uttryckstyp, per typ av underrättelse och per AI-modell. Andelen bortsorterade räknas per svar och visar hur svårt det är att få AI:n att skriva en viss sorts text. Fältet `specar` visar hur många texter som beställdes, så att man ser om en kombination har fått för få godkända texter och behöver nya försök.

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
| Spann | Pekar metoden också ut var i texten uppgiften står? | Recall och precision. |
| Attribution | Kopplar metoden uppgiften till rätt person? | Andel med rätt person bland de uppgifter metoden hittade, och andel av alla uppgifter som både hittades och fick rätt person. |
| Identifierare | Hittar metoden namn, personnummer och liknande? | Recall och precision för varje typ. |

*Recall* är hur stor andel av det som finns som metoden hittar. *Precision* är hur stor andel av det metoden flaggar som är rätt.

### Räkneexempel

Om metoden i exemplet ovan körs mot facit för texten om Erik Lund blir resultatet:

- **Dokumentnivå: allt rätt.** Metoden har angett både `RELIGION` och `HEALTH` under `categories`, och texten innehåller båda.
- **Spannivå: hälften rätt.** Metoden pekar ut var religionsuppgiften står men inte var hälsouppgiften står. Recall blir därför 1 av 2, alltså 0,50.
- **Attribution: rätt för religion.** Namnet "Erik Lund" passar på person P1, som är den uppgiften gäller.
- **Identifierare: allt rätt.** Metoden har hittat namnet.

### Regler

- **Överlapp.** En uppgift i facit räknas som hittad om metoden har pekat ut en textbit med samma etikett som överlappar den med minst ett tecken. Med `--iou` kan man kräva mer: `--iou 0.5` kräver att den gemensamma delen är minst hälften av hela området som de två textbitarna täcker tillsammans.
- **`ignore`.** En text där en kategori bara finns i `ignore`-märkta uppgifter räknas inte alls för den kategorin. Om metoden pekar ut en textbit som bara träffar en `ignore`-märkt uppgift räknas det varken som rätt eller fel.
- **`ANY`** är en extra rad i resultatet som bortser från kategorin: hittar metoden att det finns något känsligt alls?
- **`MACRO`** är en extra rad med medelvärdet över alla kategorier som finns i facit, där varje kategori väger lika mycket oavsett hur vanlig den är. Då syns det om metoden är dålig på ovanliga kategorier, även om den är bra på de vanliga.
- **Uppdelning.** Resultaten redovisas för varje del (`part`), för varje del och AI-modell som skrev texterna (`source.generator`), och, för REDACT, för varje del och grad av språkblandning (`source.code_switching`). Med `--slice-by` kan man välja andra fält, till exempel `--slice-by source.domain`.
- **Osäkerhet.** Varje resultat har ett 95-procentigt konfidensintervall, ett intervall som det verkliga värdet troligen ligger inom. Det räknas fram med bootstrap: programmet drar 1 000 slumpvisa urval av texterna och räknar om resultatet för varje urval.
- **Jämförelse med en annan metod.** Med `--baseline` följt av en annan metods svarsfil jämförs de två metoderna på samma slumpvisa urval. Rapporten visar skillnaden mellan dem, ett konfidensintervall för skillnaden och ett p-värde. Ett lågt p-värde, till exempel under 0,05, tyder på att skillnaden inte beror på slumpen.

### Inställningar

| Inställning | Vad den gör |
|---|---|
| `--gold FIL ...` | Facit. Krävs. Kan vara en eller flera filer. |
| `--pred FIL` | Metodens svar. Krävs. |
| `--baseline FIL` | En annan metods svar att jämföra med. |
| `--out FIL` | Sparar hela rapporten som JSON, för vidare bearbetning. |
| `--slice-by FÄLT[,FÄLT]` | Delar upp resultatet på andra fält. Kan anges flera gånger. |
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
- `n=50` är hur många texter eller uppgifter resultatet bygger på.

Ett streck (`–`) betyder att det inte finns något att räkna på, till exempel precision för en kategori som metoden aldrig flaggade.

### En begränsning

På dokumentnivå vet vi inte vilken uppgift i texten metoden reagerade på. Om en text innehåller både en explicit och en implicit uppgift i samma kategori, och metoden flaggar kategorin, räknas båda som hittade, även om metoden kanske bara förstod den explicita. Generatorn bör därför undvika att skriva texter med den kombinationen. På spannivå finns inte problemet, eftersom metoden där måste peka ut var varje uppgift står.
