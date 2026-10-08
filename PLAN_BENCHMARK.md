# Plan: benchmark-dataset för känslig information i svensk text

Planen besvarar frågeställning 1 i [FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md). Den beskriver hur vi tar fram ett annoterat svenskt dataset som gör metoderna i frågeställning 2 jämförbara, utan att annotera känslig produktionsdata i stor skala.

## Kort version

Vi bygger benchmarken i tre lager. Varje lager har ett eget syfte.

| Lager | Innehåll | Syfte | Riktvärde | Får lämna säker miljö? |
|---|---|---|---|---|
| **A. Syntetisk** | Fiktiva underrättelser. Genereras från styrda scenarier, en del skrivs av handläggare. | Täcka alla kategorier, implicita uttryck och svåra negativa exempel. Ge träningsdata. | ca 3 000 dokument | Ja |
| **B. Publik proxy** | Utdrag ur domstolsavgöranden, JO-beslut, forumtext med mera. | Riktigt språk som ingen modell har skrivit. | 300–500 utdrag | Ja, men bara internt (licens) |
| **C. Produktionsurval** | Pseudonymiserat urval av riktiga underrättelser. | Kontrollera att resultat på A och B håller på riktiga texter. | 300–500 dokument | Nej |

Grundidén: A och B är vår arbetsbenchmark. C är litet och används bara för att testa om A och B ger samma bild som verkligheten. Om metodernas rangordning på A+B stämmer med rangordningen på C har vi visat att benchmarken är representativ (avsnitt 9). Då är frågeställning 1 besvarad empiriskt, inte bara genom att vi påstår det.

## 1. Vad datasetet ska mäta

### Känsliga kategorier

| Kategori | Kod | Grund | Explicit exempel | Implicit exempel |
|---|---|---|---|---|
| Hälsa | `HEALTH` | art. 9 | "hon är sjukskriven för utmattning" | "hon har tid på BUP varje vecka" |
| Etniskt ursprung | `ETHNICITY` | art. 9 | "han är same" | "han jobbar med renskötseln i familjens sameby" |
| Politisk åsikt | `POLITICS` | art. 9 | "hon röstar på Vänsterpartiet" | "hon var med och startade lokalavdelningen" (om sammanhanget visar att det är ett parti) |
| Religiös eller filosofisk övertygelse | `RELIGION` | art. 9 | "han är muslim" | "han går i moskén varje fredag" |
| Medlemskap i fackförening | `TRADE_UNION` | art. 9 | "hon är med i Kommunal" | "han är klubbordförande på fabriken" |
| Sexualliv eller sexuell läggning | `SEXUALITY` | art. 9 | "han är homosexuell" | "han bor ihop med sin pojkvän" |
| Genetiska och biometriska uppgifter | `GENETIC_BIOMETRIC` | art. 9 | "hon bär på BRCA-mutationen" | (väntas vara sällsynt) |
| Lagöverträdelser | `CRIMINAL` | art. 10 | "han dömdes för misshandel 2019" | "han kom precis ut från Kumla" |

Exemplet med lokalavdelningen visar varför implicita uttryck är svåra. Samma mening kan gälla ett parti eller en fackförening. Bara sammanhanget avgör.

Följande nivå 2 är valfri. Vi tar med den om tjänsten behöver den: övriga skyddsvärda uppgifter som skyddade personuppgifter, socialtjänstinsatser och ekonomiska förhållanden (`OTHER_SENSITIVE`).

### Identifierare och metadata

Det här lagret behövs av tre skäl. Dagens regex- och NER-lösningar ska kunna jämföras på det de redan gör. Attribution kräver att vi vet vilka personer som finns i texten. Och målet omfattar användbar metadata.

- `PERSON`: namn och beskrivande omnämnanden ("min granne", "mamman"). Alla omnämnanden av samma person får samma entitets-id. Pronomen annoteras inte.
- `PERSONNUMMER`, `PHONE`, `EMAIL`, `ADDRESS`
- `LOCATION`, `ORGANISATION`, `DATE`
- `IDENTIFIER`: ärendenummer, registreringsnummer och liknande.

Varje person får en roll: `SUBJECT` (den underrättelsen gäller), `REPORTER` (den som skriver), `THIRD_PARTY` eller `OFFICIAL` (tjänsteperson).

## 2. Annoteringsschema

Varje känslig uppgift annoteras som ett spann med fyra attribut:

| Attribut | Värden | Kommentar |
|---|---|---|
| `category` | koderna ovan | |
| `expression` | `explicit`, `implicit` | Explicit betyder att texten namnger kategorin eller ett värde i den ("muslim", "diabetes", "Socialdemokrat"). Implicit betyder att kategorin måste slutas ur beteende, sammanhang eller omvärldskunskap. |
| `subject` | entitets-id, `REPORTER`, `GROUP` eller `UNCLEAR` | Attribution: vem uppgiften gäller. |
| `modality` | `asserted`, `uncertain`, `negated`, `hypothetical` | Vi annoterar alltid. Vad som ska räknas i huvudmåttet bestäms i utvärderingen, inte i annoteringen. |

**Spanngränser.** Vi markerar den kortaste sammanhängande fras som bär uppgiften. För implicita uttryck är det ofta en hel verbfras ("går i moskén varje fredag"). Eftersom gränserna är osäkra räknas överlapp som primärt matchningskriterium (avsnitt 8).

**Grundregler** (utvecklas i riktlinjerna):

- Ett namn räknas aldrig ensamt som etniskt ursprung eller religion.
- Uppgifter som inte går att knyta till en person annoteras inte. Ett exempel är "moskén på Storgatan har brunnit". Sådana meningar är värdefulla svåra negativa exempel.
- Uppgifter som skribenten lämnar om sig själv annoteras med `subject: REPORTER`.
- Uppgifter om brottsmisstankar räknas som `CRIMINAL`. Det ska bekräftas med jurist.

**Dataformat.** Vi använder JSONL, en rad per dokument, med teckenpositioner i UTF-8-text:

```json
{
  "id": "syn-000123",
  "layer": "A",
  "source": {"type": "synthetic", "generator": "modell-x", "scenario_id": "scn-0042"},
  "text": "Jag skriver angående min granne Erik Lund. Han går i moskén varje fredag men har sedan i våras slutat äta och verkar mycket nedstämd.",
  "entities": [
    {"id": "P0", "role": "REPORTER", "mentions": []},
    {"id": "P1", "role": "SUBJECT", "mentions": [
      {"start": 21, "end": 31, "type": "PERSON"},
      {"start": 32, "end": 41, "type": "PERSON"}
    ]}
  ],
  "sensitive": [
    {"start": 47, "end": 72, "category": "RELIGION", "expression": "implicit", "subject": "P1", "modality": "asserted"},
    {"start": 77, "end": 132, "category": "HEALTH", "expression": "implicit", "subject": "P1", "modality": "uncertain"}
  ],
  "annotation": {"guideline_version": "1.0", "annotators": ["a1", "a2"], "adjudicated": true}
}
```

Dokumentnivåetiketter (finns kategori X i dokumentet?) härleds från spannen. De behöver inte annoteras separat. Då kan även klassificerare som arbetar på dokumentnivå utvärderas.

## 3. Lager A: syntetisk data

Lager A ger täckning och kontroll. Där kan vi bestämma exakt hur många implicita uttryck om fackmedlemskap som finns, vilket aldrig går med riktig data.

**Steg:**

1. **Scenariospecar.** En strukturerad beskrivning per dokument: typ av underrättelse, avsändare (myndighet eller privatperson), personer och roller, vilka känsliga uppgifter som ska finnas (kategori, explicit eller implicit, vem de gäller), längd, ton och brus (talspråk, stavfel, saknad interpunktion). Specarna tas fram tillsammans med handläggare så att de liknar verkliga ärenden.
2. **Generering.** En LLM skriver texten från specen och märker ut de planerade uppgifterna.
3. **Granskning.** En människa granskar varje dokument i testdelen och rättar spannen. Granskaren letar också efter känsliga uppgifter som modellen lagt till utan att de fanns i specen. Det händer ofta.
4. **Handskrivna texter.** Handläggare skriver en del fiktiva underrättelser själva i en skrivverkstad. Målet är ungefär 10 procent av lager A. De visar om LLM-texterna skiljer sig från mänskligt skrivna.

**Att tänka på:**

- **Generatorbias.** En LLM som utvärderas på text från samma modell kan få orättvist bra resultat. Vi använder därför flera generatormodeller och rapporterar resultat per generator. De handskrivna texterna används som kontroll.
- **Inga produktionstexter i promptar** till externa modeller. Om riktiga underrättelser behövs som stilförebilder används en lokalt körd modell eller pseudonymiserade exempel.
- **Fiktiva identifierare.** Namn tas från SCB:s namnstatistik och personnummer från Skatteverkets testpersonnummer. Adresser och telefonnummer genereras.
- **Svåra negativa exempel.** Minst 25 procent av dokumenten ska sakna känsliga uppgifter, men innehålla ord som liknar dem: kyrkor och moskéer utan koppling till en person, partinamn i nyhetssammanhang, sjukdomsord i bildlig betydelse. Utan dem kan precision inte mätas.
- **Stereotyper.** Namn, ursprung och känsliga uppgifter fördelas balanserat, så att metoder inte kan lära sig genvägar som namn → religion.

## 4. Lager B: publika proxykorpusar

Lager B ger riktigt språk som ingen generator har skrivit. Kandidater, som ska inventeras i fas 0:

| Källa | Ger främst | Förbehåll |
|---|---|---|
| Publicerade domstolsavgöranden | Lagöverträdelser, hälsa (t.ex. rättspsykiatri), etnicitet (hatbrott) | Ofta redan delvis pseudonymiserade. Formellt språk. |
| JO-beslut | Hälsa, socialtjänst, lagöverträdelser, myndighetskontext nära underrättelser | Juridiskt språk. |
| Forumtext via Språkbanken (t.ex. Flashback, Familjeliv) | Informellt språk, implicita uttryck om hälsa, religion och sexualitet | En del korpusar distribueras bara med omkastade meningar. Det förstör sammanhanget som implicita uttryck kräver. Kontrollera licens och format. |
| Riksdagens öppna data | Politiska åsikter | Mest explicita uttryck om offentliga personer. |
| Text Anonymization Benchmark (TAB) | Annoteringsschema som förebild: direkta och indirekta identifierare samt känsliga attribut | Engelska. Används som metodförebild, inte som data. |

- Långa dokument delas upp i utdrag på 100–400 ord. Varje utdrag ska vara begripligt för sig.
- Lager B annoteras från början, utan förannotering från någon av de metoder vi ska jämföra. Annars dras annotatörerna mot den metodens svar.
- Även publik text innehåller personuppgifter. Vi sprider inte de annoterade utdragen utanför projektet och sparar bara det som licensen tillåter.

## 5. Lager C: pseudonymiserat produktionsurval

Lager C är det enda lagret som visar hur verkligheten ser ut. Det är också det svåraste att få till. Därför startar arbetet med det redan i fas 0.

1. **Juridik först.** Rättslig grund och ändamålsprövning görs med dataskyddsombud och jurist. Vi gör en konsekvensbedömning (DPIA). Om verksamheten är en myndighet behöver sekretessfrågor enligt OSL också prövas. Ledtiden kan vara lång.
2. **Urval.** Urvalet görs i två strata:
   - Ett slumpmässigt urval, ungefär två tredjedelar. Det ger opartiska skattningar av förekomst och recall.
   - Ett berikat urval, ungefär en tredjedel, för att få fler positiva fall i sällsynta kategorier. Berikningen bör göras på metadata som ärendetyp, inte på innehållsfilter. Ett nyckelordsfilter hittar just de explicita fall som vi redan vet att metoderna klarar, och missar de implicita. Stratumen rapporteras var för sig.
3. **Pseudonymisering.** Direkta identifierare byts mot konsekventa ersättningar, så att samma person får samma ersättningsnamn. De känsliga uppgifterna måste vara kvar, eftersom det är dem vi mäter. Pseudonymiserade data är fortfarande personuppgifter.
4. **Annotering i säker miljö** med ett självhostat verktyg, av behörig personal.
5. **Bara tillåtna metoder körs på C.** Lokala modeller går bra. En extern LLM kräver att det är juridiskt prövat. Den begränsningen är i sig ett resultat för frågeställning 3.

Om lager C inte går att få till används A+B ensamma. Som komplement granskar handläggare då kvalitativt hur metoderna fungerar på produktionsdata i säker miljö.

## 6. Annoteringsprocess och kvalitet

1. **Riktlinjer v0** med definitioner, gränsfall och många exempel per kategori, både explicita och implicita.
2. **Pilot.** 2–3 annotatörer annoterar samma 50 syntetiska och 50 proxydokument. Vi mäter samstämmigheten, går igenom oenigheterna och tar fram **riktlinjer v1**.
3. **Produktion.** All testdata i B och C dubbelannoteras. I A dubbelannoteras minst 20 procent av testdelen, och resten granskas av en person. En tredje person avgör oenigheter. Återkommande oenigheter leder till förtydliganden i riktlinjerna.

**Samstämmighet** mäts som span-F1 mellan annotatörer (med överlapp) och Cohens κ för kategori och uttryckstyp på matchade spann. Båda redovisas separat för explicita och implicita uttryck. För explicita uttryck siktar vi på span-F1 ≥ 0,85. För implicita uttryck väntar vi oss lägre värden. De sätter då ett tak för vad någon metod rimligen kan nå, och det taket är ett resultat i sig.

**Annotatörer.** Handläggare med domänkunskap, och en dataskyddsjurist för gränsfall.

**Verktyg.** INCEpTION eller Label Studio, självhostat. Verktyget måste klara spann, attribut och relationer (attribution), och måste kunna köras i den säkra miljön för lager C.

## 7. Uppdelning och storlek

| Lager | Train | Dev | Test |
|---|---|---|---|
| A | ca 60 % | ca 10 % | ca 30 % |
| B | ca 30 % | ca 20 % | ca 50 % |
| C | – | ev. litet urval för att kalibrera tröskelvärden | resten |

- **Inget läckage.** Uppdelningen görs per scenariospec och per källdokument, så att varianter av samma scenario aldrig hamnar i både train och test.
- **Testdelen är låst.** Promptar, trösklar och hyperparametrar justeras bara mot dev.

**Hur stort behöver testet vara?** Recall per kategori är primärt mått och ska redovisas separat för explicit och implicit. Det ger 16 celler (8 kategorier × 2), och varje cell behöver tillräckligt många positiva fall:

| Positiva fall per cell | 95 % konfidensintervall (±) vid recall 0,8 | i värsta fall (recall 0,5) |
|---|---|---|
| 60 | 0,10 | 0,13 |
| 100 | 0,08 | 0,10 |
| 250 | 0,05 | 0,06 |

Riktvärdet för A-test är **minst 100 positiva fall per cell**, alltså ungefär 1 600 känsliga spann. Med 2–3 spann per dokument och 25 procent negativa dokument blir det cirka 700–1 000 dokument. Sällsynta kategorier (`GENETIC_BIOMETRIC`, troligen `TRADE_UNION`) får lägre mål och redovisas med sina breda intervall. Lager C blir för litet för exakta siffror per cell. Det är avsiktligt: C används för att jämföra rangordning, inte för att ge exakta siffror per kategori. Skillnader mellan metoder testas parat med bootstrap eller McNemar. Det kräver färre fall än att skatta varje metods recall för sig.

## 8. Utvärderingsprotokoll

Benchmarken blir jämförbar först när alla metoder poängsätts på samma sätt. Därför skriver vi poängsättningsskriptet tidigt, i fas 1, och använder det redan i piloten.

- **Spannivå:** recall, precision och F1. Överlapp med samma kategori räknas som träff (primärt), och exakt matchning redovisas som sekundärt mått.
- **Dokumentnivå:** finns kategori X i dokumentet?
- **Uppdelning:** per kategori × explicit/implicit × lager (A, B, C) × generator.
- **Attribution:** andelen korrekt detekterade spann som knyts till rätt person.
- **Modalitet:** huvudmåttet räknar `asserted` och `uncertain`. Negerade och hypotetiska uppgifter redovisas separat tills vi bestämt hur de ska räknas.
- **Osäkerhet:** bootstrap-konfidensintervall för alla siffror.

## 9. Validering: är benchmarken representativ?

1. **Jämför fördelningar** mellan A, B och C: förekomst per kategori, andel implicita uttryck, textlängd, stavfel och talspråk.
2. **Adversariell validering.** Vi tränar en enkel klassificerare som ska skilja syntetiska texter från produktionstexter (i säker miljö). Om det är lätt finns systematiska skillnader, och vi undersöker vilka.
3. **Rangordning.** Vi kör 5–10 metodkonfigurationer (regex, befintlig NER, en klassificerare, en finjusterad encoder, en lokal LLM) på alla lager. Sedan jämför vi rangordningen på A+B med rangordningen på C (Kendalls τ) och tittar på hur mycket recall sjunker per kategori.

**Förslag på kriterium:** A+B duger som utvecklingsbenchmark om rangordningen i stort sett är densamma på C (τ ≥ 0,7) och ingen kategori tappar kraftigt i recall på C utan att det syns i A+B.

## 10. Faser

| Fas | Innehåll | Leverabel |
|---|---|---|
| **0. Förberedelser** | Fastställa taxonomin. Starta den juridiska processen för C. Inventera källor och licenser för B. | Taxonomi, källförteckning, beslut om C påbörjat |
| **1. Riktlinjer och verktyg** | Riktlinjer v0, JSON-schema, valideringsskript, poängsättningsskript, annoteringsverktyg. | `benchmark/` i repot med schema, riktlinjer och poängsättning |
| **2. Pilot** | 50 A + 50 B dubbelannoteras. Samstämmighet mäts. Riktlinjer v1 tas fram. Två enkla baslinjer (regex och en LLM) körs för att testa hela kedjan. | Riktlinjer v1, pilotrapport |
| **3. Skalning** | Generering och granskning av A. Annotering av B. | A och B i version 0.9 |
| **4. Produktionsurval** | Urval, pseudonymisering och annotering av C i säker miljö. | C (stannar i säker miljö) |
| **5. Validering och frysning** | Analyserna i avsnitt 9. Datablad för datasetet. | Benchmark v1.0 |

Den kritiska linjen går genom den juridiska processen för C. Fas 1–3 kan därför löpa parallellt med den.

**Struktur i repot:**

```
benchmark/
  README.md          datablad: syfte, källor, statistik, kända brister
  riktlinjer/        annoteringsriktlinjer med exempel
  schema/            JSON-schema för dokument och annoteringar
  generering/        scenariospecar, promptar och skript för lager A
  proxy/             skript som hämtar och förbereder källorna i lager B
  eval/              poängsättning och statistik
  data/              bara lager A, och B om licensen tillåter
```

Lager C och all produktionsdata hamnar aldrig i repot.

## 11. Risker

| Risk | Åtgärd |
|---|---|
| Syntetiska texter blir för tydliga och för "rena" | Handskrivna texter, brus i specarna, granskning av handläggare, adversariell validering |
| LLM-metoder gynnas av LLM-genererad text | Flera generatorer, resultat per generator, handskriven kontrollgrupp, lager B och C |
| Låg samstämmighet för implicita uttryck | Pilot och iterativa riktlinjer. Låg samstämmighet redovisas som ett tak, inte som ett misslyckande. |
| Juridiska hinder för lager C | Starta tidigt. Reservplan: A+B och kvalitativ granskning i säker miljö. |
| Sällsynta kategorier ger för få fall | Överrepresentation i A, berikat stratum i C, redovisning med breda intervall |
| Metoder lär sig stereotypa genvägar | Balanserade scenarier och svåra negativa exempel |
| Läckage mellan train och test | Uppdelning per scenario och källdokument |

## 12. Beslut vi behöver ta

1. Vilka typer av underrättelser är i fokus? Det styr scenariospecarna.
2. Får vi använda produktionsdata alls, och vem driver den juridiska frågan?
3. Får en extern LLM användas för att generera fiktiv data?
4. Ska nivå 2 (`OTHER_SENSITIVE`) ingå i version 1?
5. Hur ska misstankar, negerade och hypotetiska uppgifter räknas i huvudmåttet?
6. Vem annoterar, och hur mycket tid finns?

## Första konkreta steg

1. Fastställa taxonomin och svara på besluten ovan.
2. Skriva JSON-schema och poängsättningsskript i `benchmark/`.
3. Skriva riktlinjer v0 med exempel.
4. Ta fram 20–30 scenariospecar och generera de första 50 syntetiska dokumenten.
5. Starta den juridiska processen för lager C.
