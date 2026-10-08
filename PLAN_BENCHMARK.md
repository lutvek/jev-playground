# Plan: benchmark-dataset för känslig information i svensk text

Planen besvarar frågeställning 1 i [FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md). Den beskriver hur vi tar fram ett annoterat svenskt dataset som gör metoderna i frågeställning 2 jämförbara.

**Förutsättning:** vi får inte spara produktionsdata. Benchmarken bygger därför helt på syntetisk och publik text. Vilka källor som finns, och hur väl de är kontrollerade, står i [KALLOR.md](KALLOR.md).

## Kort version

| Del | Innehåll | Syfte | Riktvärde |
|---|---|---|---|
| **Syntetisk** | LLM-genererade underrättelser från styrda scenarier | Täcka alla kategorier, implicita uttryck och svåra negativa exempel. Ge träningsdata. | ca 3 000 dokument |
| **Handskriven** | Fiktiva underrättelser skrivna av handläggare | Det närmaste produktionsdata vi kan komma. Kontroll av att LLM-texterna är realistiska. | 150–200 dokument |
| **Publik** | Utdrag ur domstolsavgöranden och JO-beslut, plus meningar från Flashback och Familjeliv | Riktigt språk och riktiga sätt att uttrycka känsliga uppgifter | 300–400 utdrag, 300–500 meningar |
| **Extern** | Svenska delen av REDACT, och PrivoNest om den håller måttet | Oberoende jämförelse som någon annan har byggt | 561 dokument (REDACT), plus ev. PrivoNest |

Grundidén: den syntetiska delen är kärnan. Det är det enda sättet att få implicita uttryck i alla kategorier i rätt genre. Det finns inget färdigt dataset som gör det, varken på svenska eller något annat språk.

De andra delarna finns där för att kontrollera att den syntetiska delen inte lurar oss. Om metoderna rangordnas ungefär likadant på syntetisk text som på handskriven och publik text duger den syntetiska delen som arbetsbenchmark (avsnitt 10). Då har vi besvarat frågeställning 1 med en mätning.

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

Kategoridefinitionerna stäms av mot W3C:s taxonomi DPV-PD, så att gränsdragningarna följer en etablerad standard.

Följande nivå 2 är valfri. Vi tar med den om tjänsten behöver den: övriga skyddsvärda uppgifter som skyddade personuppgifter, socialtjänstinsatser och ekonomiska förhållanden (`OTHER_SENSITIVE`).

### Identifierare och metadata

Det här lagret behövs av tre skäl. Dagens regex- och NER-lösningar ska kunna jämföras på det de redan gör. Attribution kräver att vi vet vilka personer som finns i texten. Och målet omfattar användbar metadata.

- `PERSON`: namn, initialer och beskrivande omnämnanden ("min granne", "mamman"). Alla omnämnanden av samma person får samma entitets-id. Pronomen annoteras inte.
- `PERSONNUMMER`, `PHONE`, `EMAIL`, `ADDRESS`
- `LOCATION`, `ORGANISATION`, `DATE`
- `IDENTIFIER`: ärendenummer, registreringsnummer och liknande.

Varje person får en roll: `SUBJECT` (den underrättelsen gäller), `REPORTER` (den som skriver), `THIRD_PARTY` eller `OFFICIAL` (tjänsteperson).

## 2. Annoteringsschema

Schemat bygger på TAB (Text Anonymization Benchmark), som kombinerar identifierare och känsliga attribut på spann. Vi lägger till fack, lagöverträdelser, uttryckstyp och attribution.

Varje känslig uppgift annoteras som ett spann med fyra attribut:

| Attribut | Värden | Kommentar |
|---|---|---|
| `category` | koderna ovan | |
| `expression` | `explicit`, `implicit` | Explicit betyder att texten namnger kategorin eller ett värde i den ("muslim", "diabetes", "Socialdemokrat"). Implicit betyder att kategorin måste slutas ur beteende, sammanhang eller omvärldskunskap. |
| `subject` | entitets-id, `REPORTER`, `GROUP` eller `UNCLEAR` | Attribution: vem uppgiften gäller. |
| `modality` | `asserted`, `uncertain`, `negated`, `hypothetical` | Vi annoterar alltid. Vad som ska räknas i huvudmåttet bestäms i utvärderingen, inte i annoteringen. |

Om uppdelningen explicit/implicit visar sig för grov i piloten lägger vi till en svårighetsgrad 1–5 för implicita uttryck, enligt SynthPAI:s modell.

**Spanngränser.** Vi markerar den kortaste sammanhängande fras som bär uppgiften. För implicita uttryck är det ofta en hel verbfras ("går i moskén varje fredag"). Eftersom gränserna är osäkra räknas överlapp som primärt matchningskriterium (avsnitt 9).

**Grundregler** (utvecklas i riktlinjerna):

- Ett namn räknas aldrig ensamt som etniskt ursprung eller religion.
- Uppgifter som inte går att knyta till en person annoteras inte. Ett exempel är "moskén på Storgatan har brunnit". Ett annat är ett parti som nämns som organisation. Sådana meningar är värdefulla svåra negativa exempel.
- Uppgifter som skribenten lämnar om sig själv annoteras med `subject: REPORTER`.
- Uppgifter om brottsmisstankar räknas som `CRIMINAL`. Det ska bekräftas med jurist.

**Dataformat.** Vi använder JSONL, en rad per dokument, med teckenpositioner i UTF-8-text:

```json
{
  "id": "syn-000123",
  "part": "synthetic",
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

## 3. Syntetisk del

Den syntetiska delen ger täckning och kontroll. Där kan vi bestämma exakt hur många implicita uttryck om fackmedlemskap som finns, vilket aldrig går med riktig data.

**Steg:**

1. **Scenariospecar.** En strukturerad beskrivning per dokument: typ av underrättelse, avsändare (myndighet eller privatperson), personer och roller, vilka känsliga uppgifter som ska finnas (kategori, explicit eller implicit, vem de gäller), längd, ton och brus (talspråk, stavfel, saknad interpunktion). Specarna tas fram tillsammans med handläggare så att de liknar verkliga ärenden. Domstolsavgöranden och JO-beslut används för att hitta realistiska typer av scenarier, men inga verkliga sakuppgifter förs över.
2. **Generering.** En LLM skriver texten från specen och märker ut de planerade uppgifterna. ConfAIde och PrivacyLens har recept för den här typen av generering som vi kan låna.
3. **Granskning.** En människa granskar varje dokument i testdelen och rättar spannen. Granskaren letar också efter känsliga uppgifter som modellen lagt till utan att de fanns i specen. Det händer ofta.

**Byggstenar** (detaljer i [KALLOR.md](KALLOR.md)):

- personnummer från Skatteverkets testpersonnummer, som aldrig delas ut till riktiga personer
- namn med frekvenser från SCB:s namnstatistik
- syntetiska personer från swedish-personas som frön till scenarierna
- telefonnummer, adresser och konton från listor över fiktiva identifierare

**Att tänka på:**

- **Generatorbias.** En LLM som utvärderas på text från samma modell kan få orättvist bra resultat. Vi använder därför flera generatormodeller och rapporterar resultat per generator. Den handskrivna delen används som kontroll.
- **Svåra negativa exempel.** Minst 25 procent av dokumenten ska sakna känsliga uppgifter, men innehålla ord som liknar dem: kyrkor och moskéer utan koppling till en person, partinamn i nyhetssammanhang, sjukdomsord i bildlig betydelse. Utan dem kan precision inte mätas.
- **Stereotyper.** Namn, ursprung och känsliga uppgifter fördelas balanserat, så att metoder inte kan lära sig genvägar som namn → religion.

## 4. Handskriven del

Handläggare skriver fiktiva underrättelser i en skrivverkstad. De vet hur riktiga ärenden ser ut, men skriver dem från grunden. Utan produktionsdata är detta det närmaste verkligheten vi kan komma.

- **Fiktivt på riktigt.** Inga verkliga ärenden återges. Namn, platser och detaljer hittas på eller ändras så att ingen verklig person kan kännas igen. Texterna skrivs direkt i annoteringsverktyget, inte i system där produktionsdata finns.
- **Styrd täckning.** Skribenterna får en lista över vilka kategorier och uttryckstyper som behövs, men skriver fritt inom den. De noterar också vad de avsåg att få med. Det jämförs sedan med annoteringen.
- **Annoteras av någon annan** än den som skrev texten.
- **Används bara som test.** Delen ska vara en ren kontroll och används aldrig för träning eller promptjustering.

## 5. Publik del

Den publika delen ger riktigt språk som ingen generator har skrivit. Källorna beskrivs i [KALLOR.md](KALLOR.md).

**Utdrag ur domstolsavgöranden och JO-beslut** (300–400 utdrag):

| Källa | Ger främst |
|---|---|
| Migrationsöverdomstolen och migrationsdomstolarna | Religion, sexuell läggning, etniskt ursprung, politisk åsikt, ofta implicit (asylskäl) |
| Arbetsdomstolen | Fackmedlemskap |
| Kammarrätter (LVU, LVM, LPT) | Hälsa, missbruk, socialtjänst |
| Hovrätter | Lagöverträdelser, hälsa |
| JO-beslut | Socialtjänst, polis och psykiatri. Ligger närmast myndighetsgenren. |

- Avgörandena hämtas via Domstolsverkets Rättspraxis-API. JO-beslut hämtas från jo.se.
- Vi tar ut avsnitt som beskriver omständigheter och parternas berättelser, och delar dem i utdrag på 50–300 ord. Varje utdrag ska vara begripligt för sig.
- Parter anges redan med initialer. Initialerna annoteras som `PERSON`.

**Meningar från Flashback och Familjeliv** (300–500 meningar):

- Språkbanken distribuerar forumkorpusarna med omkastade meningar. Det går därför bara att arbeta på meningsnivå.
- Den här samlingen ger informella, ofta implicita uttryck och svåra negativa exempel. Den rapporteras separat från dokumenten.
- Meningar hämtas via Korp med sökmönster. Det gynnar uttryck som mönstren fångar, så mönstren ska vara breda och inte bara bestå av kategoriord.
- Användarnamn och länkar sparas inte.

**För hela den publika delen gäller:**

- Annoteringen görs från början, utan förannotering från någon av de metoder vi ska jämföra. Annars dras annotatörerna mot den metodens svar.
- Även publik text innehåller personuppgifter. Vi sparar bara utdragen vi behöver och sprider dem inte utanför projektet.

## 6. Extern del

- **REDACT, svenska delen** (561 dokument, varav 157 med art. 9/10-spann). Datan är LLM-genererad och etiketterna gäller nästan bara explicita uttryck. Den har tre svagheter:
  - Mycket kodväxling mot engelska. Bara 244 dokument saknar kodväxling.
  - Liten namnvariation.
  - Etiketterna gäller ord, inte uppgifter om personer. Ett partinamn märks även när ingen persons åsikt avslöjas.

  Vi mappar etiketterna till vårt schema och gör om attributionen för de 157 dokumenten med känsliga spann. Resultaten redovisas både för hela delen och för dokumenten utan kodväxling.
- **PrivoNest, svenska delen** (enligt kortet 8 545 rader med alla art. 9-kategorier). Vi har inte kunnat se några rader. Om en granskning av ett stickprov visar godtagbar kvalitet används den som extra testdata och kanske som träningsdata.

Den externa delen används bara som test. Den visar hur metoderna klarar text som vi inte själva har formgett.

## 7. Annoteringsprocess och kvalitet

1. **Riktlinjer v0** med definitioner, gränsfall och många exempel per kategori, både explicita och implicita. Riktlinjerna bygger på TAB:s riktlinjer.
2. **Pilot.** 2–3 annotatörer annoterar samma cirka 100 dokument: 50 syntetiska, 30 publika utdrag och 20 handskrivna. Vi mäter samstämmigheten, går igenom oenigheterna och tar fram **riktlinjer v1**.
3. **Produktion.** All testdata i den handskrivna och den publika delen dubbelannoteras. I den syntetiska delen dubbelannoteras minst 20 procent av testdelen, och resten granskas av en person. En tredje person avgör oenigheter. Återkommande oenigheter leder till förtydliganden i riktlinjerna.

**Samstämmighet** mäts som span-F1 mellan annotatörer (med överlapp) och Cohens κ för kategori och uttryckstyp på matchade spann. Båda redovisas separat för explicita och implicita uttryck. För explicita uttryck siktar vi på span-F1 ≥ 0,85. För implicita uttryck väntar vi oss lägre värden. De sätter då ett tak för vad någon metod rimligen kan nå, och det taket är ett resultat i sig.

**Annotatörer.** Handläggare med domänkunskap, och en dataskyddsjurist för gränsfall.

**Verktyg.** INCEpTION eller Label Studio, självhostat, eftersom även de publika texterna innehåller personuppgifter. Verktyget måste klara spann, attribut och relationer (attribution).

## 8. Uppdelning och storlek

| Del | Train | Dev | Test |
|---|---|---|---|
| Syntetisk | ca 60 % | ca 10 % | ca 30 % |
| Handskriven | – | – | 100 % |
| Publik, utdrag | ca 30 % | ca 20 % | ca 50 % |
| Publik, meningar | – | ca 30 % | ca 70 % |
| Extern | – | – | 100 % |

- **Inget läckage.** Uppdelningen görs per scenariospec och per källdokument, så att varianter av samma scenario aldrig hamnar i både train och test.
- **Testdelen är låst.** Promptar, trösklar och hyperparametrar justeras bara mot dev.

**Hur stort behöver testet vara?** Recall per kategori är primärt mått och ska redovisas separat för explicit och implicit. Det ger 16 celler (8 kategorier × 2), och varje cell behöver tillräckligt många positiva fall:

| Positiva fall per cell | 95 % konfidensintervall (±) vid recall 0,8 | i värsta fall (recall 0,5) |
|---|---|---|
| 60 | 0,10 | 0,13 |
| 100 | 0,08 | 0,10 |
| 250 | 0,05 | 0,06 |

- **Den syntetiska testdelen** ska ha **minst 100 positiva fall per cell**, alltså ungefär 1 600 känsliga spann. Med 2–3 spann per dokument och 25 procent negativa dokument blir det cirka 700–1 000 dokument.
- **Sällsynta kategorier** (`GENETIC_BIOMETRIC`, troligen `TRADE_UNION`) får lägre mål och redovisas med sina breda intervall.
- **Den handskrivna, den publika och den externa delen** blir för små för exakta siffror per cell. Det är avsiktligt, eftersom de används för att jämföra rangordning.
- **Skillnader mellan metoder** testas parat, med bootstrap eller McNemar. Det kräver färre fall än att skatta varje metods recall för sig.

## 9. Utvärderingsprotokoll

Benchmarken blir jämförbar först när alla metoder poängsätts på samma sätt. Därför skriver vi poängsättningsskriptet tidigt, i fas 1, och använder det redan i piloten.

- **Spannivå:** recall, precision och F1. Överlapp med samma kategori räknas som träff (primärt), och exakt matchning redovisas som sekundärt mått.
- **Dokumentnivå:** finns kategori X i dokumentet?
- **Uppdelning:** per kategori × explicit/implicit × del × generator.
- **Attribution:** andelen korrekt detekterade spann som knyts till rätt person.
- **Modalitet:** huvudmåttet räknar `asserted` och `uncertain`. Negerade och hypotetiska uppgifter redovisas separat tills vi bestämt hur de ska räknas.
- **Osäkerhet:** bootstrap-konfidensintervall för alla siffror.

## 10. Validering: är benchmarken representativ?

Utan produktionsdata kan vi inte mäta direkt mot verkligheten. Vi använder i stället fyra indirekta kontroller.

1. **Rangordning.** Vi kör 5–10 metodkonfigurationer (regex, befintlig NER, en klassificerare, en finjusterad encoder, en lokal LLM) på alla delar. Sedan jämför vi rangordningen på den syntetiska delen med rangordningen på den handskrivna och den publika delen (Kendalls τ). Vi tittar också på hur mycket recall sjunker per kategori.
2. **Blindtest av realism.** Handläggare får en blandning av syntetiska och handskrivna texter. De betygsätter hur realistiska texterna är och gissar vilka som är skrivna av en människa. Om de inte kan skilja dem åt är det ett gott tecken.
3. **Adversariell validering.** Vi tränar en enkel klassificerare som ska skilja syntetiska texter från handskrivna. Om det är lätt finns systematiska skillnader, och vi undersöker vilka.
4. **Jämför fördelningar** mellan delarna: förekomst per kategori, andel implicita uttryck, textlängd, stavfel och talspråk.

**Förslag på kriterium:** den syntetiska delen duger som arbetsbenchmark om rangordningen i stort sett är densamma på den handskrivna och den publika delen (τ ≥ 0,7) och ingen kategori tappar kraftigt i recall där utan att det syns i den syntetiska delen.

Slutsatserna gäller syntetisk och publik text. Hur väl de håller på riktiga underrättelser kan vi bara argumentera för, inte mäta. Det ska stå tydligt i resultatredovisningen.

## 11. Faser

| Fas | Innehåll | Leverabel |
|---|---|---|
| **0. Förberedelser** | Fastställa taxonomin och ta besluten i avsnitt 13. Ladda ner och granska REDACT och PrivoNest. Kontrollera att Rättspraxis-API:et och Korp ger det vi behöver. | Taxonomi, granskad källförteckning |
| **1. Riktlinjer och verktyg** | Riktlinjer v0, JSON-schema, valideringsskript, poängsättningsskript, annoteringsverktyg. | `benchmark/` i repot med schema, riktlinjer och poängsättning |
| **2. Pilot** | Cirka 100 dokument dubbelannoteras. Samstämmighet mäts. Riktlinjer v1 tas fram. Två enkla baslinjer (regex och en LLM) körs på piloten och på REDACT för att testa hela kedjan. | Riktlinjer v1, pilotrapport |
| **3. Skalning** | Generering och granskning av den syntetiska delen. Annotering av den publika delen. Skrivverkstäder för den handskrivna delen. | Alla delar i version 0.9 |
| **4. Validering och frysning** | Analyserna i avsnitt 10. Datablad för datasetet. | Benchmark v1.0 |

Den kritiska linjen går nu genom tillgången på handläggare för skrivverkstäder och annotering.

**Struktur i repot:**

```
benchmark/
  README.md          datablad: syfte, källor, statistik, kända brister
  riktlinjer/        annoteringsriktlinjer med exempel
  schema/            JSON-schema för dokument och annoteringar
  generering/        scenariospecar, promptar och skript för den syntetiska delen
  publik/            skript som hämtar och förbereder domstols-, JO- och forumtext
  extern/            skript som hämtar och mappar REDACT och PrivoNest
  eval/              poängsättning och statistik
  data/              annoterade data, beroende på beslut 6 i avsnitt 13
```

Ingen produktionsdata hamnar någonsin i repot.

## 12. Risker

| Risk | Åtgärd |
|---|---|
| Vi kan inte mäta mot riktiga underrättelser | Handskriven del, publik del och rangordningsjämförelse. Slutsatserna formuleras försiktigt. |
| Syntetiska texter blir för tydliga och för "rena" | Brus i specarna, granskning av handläggare, blindtest, adversariell validering |
| LLM-metoder gynnas av LLM-genererad text | Flera generatorer, resultat per generator, handskriven och publik del |
| Handskrivna texter återger verkliga ärenden | Tydliga instruktioner, krav på att ändra detaljer, granskning före annotering |
| Låg samstämmighet för implicita uttryck | Pilot och iterativa riktlinjer. Låg samstämmighet redovisas som ett tak, inte som ett misslyckande. |
| Sällsynta kategorier ger för få fall | Överrepresentation i den syntetiska delen. Riktade urval ur Arbetsdomstolen (fack) och migrationsmål (religion, sexuell läggning, etnicitet). Redovisning med breda intervall. |
| Metoder lär sig stereotypa genvägar | Balanserade scenarier och svåra negativa exempel |
| Läckage mellan train och test | Uppdelning per scenario och källdokument |
| Licens- och personuppgiftsfrågor för publik och extern data | Spara bara det som behövs. Inga användarnamn från forum. Följ REDACT:s villkor. |

## 13. Beslut vi behöver ta

1. Vilka typer av underrättelser är i fokus? Det styr scenariospecarna.
2. Får en extern LLM användas för att generera den syntetiska datan? Ingen verklig persondata ingår i promptarna.
3. Kan handläggare avsätta tid för skrivverkstäder och annotering? Ungefär hur mycket?
4. Ska nivå 2 (`OTHER_SENSITIVE`) ingå i version 1?
5. Hur ska misstankar, negerade och hypotetiska uppgifter räknas i huvudmåttet?
6. Får annoterade utdrag ur domstolsavgöranden och forum sparas i repot? Alternativet är att bara spara skript och annoteringar som pekar på källorna. Repot är privat, så mitt förslag är att spara utdragen.

## Första konkreta steg

1. Öppna nätverksåtkomst till huggingface.co, spraakbanken.gu.se, rattspraxis.etjanst.domstol.se, jo.se och skatteverket.entryscape.net, så att vi kan hämta data i molnmiljön.
2. Ladda ner REDACT och PrivoNest och granska de svenska delarna. Det ger en extern testmängd snabbt.
3. Skriva JSON-schema och poängsättningsskript i `benchmark/`.
4. Skriva riktlinjer v0 med exempel.
5. Ta fram 20–30 scenariospecar och generera de första 50 syntetiska dokumenten.
6. Hämta 30 utdrag ur domstolsavgöranden och JO-beslut till piloten.
