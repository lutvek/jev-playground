# Plan för benchmark-datasetet (PoC)

Det här dokumentet beskriver hur vi tar fram testmaterialet som behövs för att besvara fråga 1 i [FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md): hur bygger vi en svensk benchmark för känsliga personuppgifter?

En *benchmark* är en fast samling testtexter med facit, alltså de rätta svaren, och ett fast sätt att räkna poäng. Den gör det möjligt att testa olika metoder på exakt samma sätt och jämföra resultaten.

Källorna som planen bygger på står i [KALLOR.md](KALLOR.md). Begrepp som kan vara obekanta förklaras där de dyker upp och finns också i [ORDLISTA.md](ORDLISTA.md).

## Förutsättningar

- **Det här är en PoC**, ett mindre försöksprojekt som ska visa om idén håller. Det är inte en fullskalig lösning.
- **Ingen handmärkning.** Ingen människa ska behöva gå igenom texter och märka ut var de känsliga uppgifterna står.
- **Inga riktiga texter.** Vi använder inte texter från våra egna system.
- **En extern AI-tjänst får skriva texter åt oss.** Eftersom texterna är påhittade innehåller de inga uppgifter om riktiga personer.
- **Vi har tillgång till Google Cloud (GCP).** Där finns Vertex AI, där man kan anropa AI-modeller som Gemini och Claude, och Model Garden, en katalog med öppna modeller som vi kan köra själva. Vi har också egna GPU:er, den typ av datorkraft som behövs för att köra och träna modeller.

## Sammanfattning

Vi använder färdiga dataset där de räcker, och låter en AI skriva egna texter för det som saknas.

Benchmarken består av tre delar:

| Del | Var den kommer ifrån | Vad den täcker | Hur stor |
|---|---|---|---|
| **REDACT-SV** | Färdigt dataset från GitHub | Namn, personnummer och andra identifierare, samt känsliga uppgifter som sägs rakt ut, framför allt hälsa och brott | 561 texter |
| **PrivoNest-SV** | Färdigt dataset från Hugging Face, om kvaliteten håller | Alla känsliga kategorier, mest uppgifter som sägs rakt ut | ungefär 8 500 rader |
| **Syntetisk** | Texter som en AI skriver på vår beställning | Det som saknas i de färdiga dataseten: uppgifter som går att lista ut av sammanhanget, i alla kategorier, i texter som liknar underrättelser och med uppgift om vem uppgiften gäller | ungefär 1 000 testtexter och 3 000 träningstexter |

I de två färdiga dataseten följer facit med datasetet. I den syntetiska delen följer facit med konstruktionen, se nedan.

**Varför vi måste skriva egna texter.** Inget färdigt dataset, på något språk, innehåller känsliga uppgifter som går att lista ut av sammanhanget utan att sägas rakt ut. Det är just de uppgifterna som dagens verktyg missar, och skillnaden mellan dem och de uppgifter som sägs rakt ut är kärnan i forskningsfrågan.

**Varför ingen behöver märka upp texterna.** Vi bestämmer först vad en text ska innehålla, till exempel "en uppgift om religion om grannen, som inte sägs rakt ut". Sedan ber vi AI:n skriva texten och markera var uppgiften står. Facit finns alltså redan innan texten är skriven. Därefter kontrollerar vi automatiskt att texten verkligen stämmer med facit (avsnitt 5).

## 1. Vad vi letar efter

### Känsliga kategorier

*Kod* är namnet som används i filerna och i koden. *Grund* är den artikel i dataskyddsförordningen GDPR som gör uppgiften skyddad.

Varje kategori har två exempel: ett där uppgiften sägs rakt ut (*explicit*) och ett där den går att lista ut av sammanhanget (*implicit*).

| Kategori | Kod | Grund | Explicit exempel | Implicit exempel |
|---|---|---|---|---|
| Hälsa | `HEALTH` | art. 9 | "hon är sjukskriven för utmattning" | "hon har tid på BUP varje vecka" |
| Etniskt ursprung | `ETHNICITY` | art. 9 | "han är same" | "han jobbar med renskötseln i familjens sameby" |
| Politisk åsikt | `POLITICS` | art. 9 | "hon röstar på Vänsterpartiet" | "hon var med och startade partiets lokalavdelning" |
| Religiös eller filosofisk övertygelse | `RELIGION` | art. 9 | "han är muslim" | "han går i moskén varje fredag" |
| Medlemskap i fackförening | `TRADE_UNION` | art. 9 | "hon är med i Kommunal" | "han är klubbordförande på fabriken" |
| Sexualliv eller sexuell läggning | `SEXUALITY` | art. 9 | "han är homosexuell" | "han bor ihop med sin pojkvän" |
| Genetiska och biometriska uppgifter | `GENETIC_BIOMETRIC` | art. 9 | "hon bär på BRCA-mutationen" | sällsynt, låg prioritet |
| Lagöverträdelser | `CRIMINAL` | art. 10 | "han dömdes för misshandel 2019" | "han kom precis ut från Kumla" |

### Identifierare

Vi letar också efter *identifierare*, alltså uppgifter som pekar ut vem någon är. De behövs för att kunna avgöra vem en känslig uppgift gäller, och de är personuppgifter i sig.

| Kod | Vad det är |
|---|---|
| `PERSON` | namn på en person |
| `PERSONNUMMER` | personnummer |
| `PHONE` | telefonnummer |
| `EMAIL` | e-postadress |
| `ADDRESS` | gatuadress |
| `LOCATION` | ort, land eller annan plats |
| `ORGANISATION` | företag, myndighet, förening och liknande |
| `DATE` | datum och tidpunkter |
| `IDENTIFIER` | andra nummer som pekar ut någon, till exempel ärendenummer, kundnummer eller passnummer |

## 2. Hur en text med facit sparas

Alla tre delarna sparas i samma format, så att samma program kan räkna poäng för alla. Formatet heter JSONL: en textfil där varje rad beskriver en text och dess facit.

Här är ett exempel, uppdelat på flera rader för att vara lättare att läsa. I filen står allt på en rad.

```json
{
  "id": "syn-000123",
  "part": "synthetic",
  "split": "test",
  "source": {"generator": "modell-a", "scenario_id": "scn-0042"},
  "text": "Jag skriver angående min granne Erik Lund. Han går i moskén varje fredag men har sedan i våras slutat äta och verkar mycket nedstämd.",
  "entities": [
    {"id": "P0", "role": "REPORTER", "mentions": []},
    {"id": "P1", "role": "SUBJECT", "mentions": [
      {"start": 32, "end": 41, "type": "PERSON"}
    ]}
  ],
  "identifiers": [],
  "sensitive": [
    {"start": 47, "end": 72, "category": "RELIGION", "expression": "implicit", "subject": "P1"},
    {"start": 77, "end": 132, "category": "HEALTH", "expression": "implicit", "subject": "P1"}
  ]
}
```

### Så läser man exemplet

Texten handlar om två personer. P0 är den som skriver (`REPORTER`) och nämns inte vid namn. P1 är grannen som texten handlar om (`SUBJECT`) och nämns som "Erik Lund".

Texten innehåller två känsliga uppgifter om P1, och ingen av dem sägs rakt ut:

- "går i moskén varje fredag" avslöjar religion.
- "har sedan i våras slutat äta och verkar mycket nedstämd" avslöjar något om hälsan.

**Positioner i texten.** Var en uppgift står anges med två tal, `start` och `end`. De räknar tecken från textens början, där första tecknet har nummer 0. `start` är det första tecknet som ingår och `end` är det första tecknet som *inte* ingår. I exemplet är `start` 47 och `end` 72 tecknen 47 till och med 71, alltså "går i moskén varje fredag". En sådan avgränsad bit av texten kallas ett *spann*.

### Fälten

| Fält | Vad det betyder |
|---|---|
| `id` | Textens unika namn. |
| `part` | Vilken av de tre delarna texten kommer från: `redact`, `privonest` eller `synthetic`. |
| `split` | Om texten är till för test, justering (`dev`) eller träning (`train`), se avsnitt 4. |
| `source` | Varifrån texten kommer, till exempel vilken AI-modell som skrev den. |
| `text` | Själva texten. |
| `entities` | Personerna i texten. Var och en har ett id, en roll och en lista över var personen nämns (`mentions`). Rollen är `REPORTER` för den som skriver, `SUBJECT` för den texten handlar om och `OTHER` för övriga. |
| `identifiers` | Identifierare som inte hör till någon särskild person, till exempel orter och datum. I dataset som inte anger vem uppgifterna gäller ligger alla identifierare här. |
| `sensitive` | De känsliga uppgifterna. Var och en har position, kategori, om den är explicit eller implicit (`expression`) och vem den gäller (`subject`). |

Ett känsligt spann kan också ha `ignore: true`. Det betyder att kategorin nämns i texten utan att något avslöjas om en person, till exempel "han är *inte* medlem i facket". Ett sådant spann räknas inte alls när poängen räknas ut: en metod som flaggar det gör inte fel, och en metod som missar det gör inte heller fel.

Om en text innehåller en viss kategori eller inte (*dokumentnivå*) står inte som ett eget fält. Det räknas ut från spannen.

De färdiga dataseten anger inte alltid allt. Där fylls bara de fält i som datasetet har information om. Fälten `identifiers` och `ignore` lades till under arbetet, när det visade sig att REDACT behövde dem.

Det fullständiga formatet och alla regler står i [benchmark/README.md](benchmark/README.md).

## 3. Färdiga dataset

### REDACT-SV

REDACT är ett flerspråkigt dataset där en AI har skrivit texter som e-post, ärendeanteckningar och chattar, bland annat från myndigheter, polis och vård. Personerna är påhittade. Den svenska delen kan hämtas från GitHub redan nu och har 561 texter. 157 av dem innehåller känsliga uppgifter. Vi har gjort om texterna till vårt format och kopplat REDACT:s egna etiketter till våra koder.

Fyra saker är bra att känna till:

- **Bara uppgifter som sägs rakt ut.** Datasetet säger därför inget om hur bra metoder är på uppgifter som går att lista ut av sammanhanget.
- **Etiketterna sitter på ord, inte på personer.** Ett partinamn är märkt som politik även när texten inte säger något om någons politiska åsikt, till exempel när partiet bara nämns i förbigående. Därför används datasetet främst för identifierare, hälsa och brott. Resultat för övriga kategorier redovisas med en reservation.
- **Många texter blandar språk.** Bara 244 av texterna är helt på svenska. Resten blandar in engelska eller andra språk. Resultaten redovisas både för alla texter och för de helt svenska.
- **Få exempel utanför hälsa och brott.** Efter konverteringen räknas 147 texter som att de innehåller något känsligt. (De övriga 10 av de 157 innehåller bara uppgifter som REDACT själv markerar som "avslöjar inget", till exempel nekanden.) Bland de helt svenska texterna finns politik i 6 texter, fack i 3, religion i 1 och sexuell läggning i ingen. Det räcker för att mäta hälsa, och med stor osäkerhet brott, men inte de andra kategorierna.

### PrivoNest-SV

PrivoNest är ett annat flerspråkigt, AI-skrivet dataset, som enligt sin beskrivning har ungefär 8 500 svenska rader med alla känsliga kategorier. Det ligger på Hugging Face, en webbplats som molnmiljön där vi arbetar i dag inte når. Den måste öppnas först.

Planen är att läsa 20–30 slumpvis valda rader. Om kvaliteten håller använder vi datasetets svenska testdel som extra testmaterial och dess träningsdel för att träna encoder-modellerna (se ordlistan). Om kvaliteten inte håller stryks datasetet.

### Engelska dataset

Det finns engelska dataset, som TAB och SynthPAI (se [KALLOR.md](KALLOR.md)), som skulle kunna översättas till svenska. Det ingår inte i PoC:n. De består av andra sorters texter än underrättelser, så det ger mer att skriva egna texter i rätt stil från början.

## 4. Egna, AI-skrivna texter

### Så går det till

Varje text tas fram i fyra steg.

**Steg 1: Datorn slumpar fram en beställning.** Ett program väljer slumpvis vad texten ska innehålla. En sådan beställning kallas *scenariospec* och anger:

- vilken sorts underrättelse det är och vem som skickar den
- 1–3 personer och vilken roll var och en har
- 1–3 känsliga uppgifter, och för varje uppgift kategori, om den ska sägas rakt ut eller inte, och vem den gäller
- hur lång texten ska vara och vilken ton den ska ha, till exempel vardagligt språk eller enstaka stavfel

Namnen hämtas från SCB:s namnstatistik, så att de är vanliga svenska namn. Personnumren hämtas från Skatteverkets lista över testpersonnummer, som aldrig delas ut till riktiga personer.

**Steg 2: AI:n skriver texten och markerar uppgifterna.** Varje känslig uppgift omges av en markering som anger kategori, uttryckstyp och person. Det kan se ut ungefär så här:

```
Jag skriver angående min granne <PERSON P1>Erik Lund</PERSON>. Han <RELIGION implicit P1>går i moskén varje fredag</RELIGION> men ...
```

Personer och identifierare markeras på samma sätt. Exakt hur markeringarna ska se ut bestäms när generatorn byggs.

**Steg 3: Ett program tar bort markeringarna.** Programmet noterar var varje markering stod, räknar ut start- och slutposition och tar sedan bort markeringarna ur texten. Kvar blir en vanlig text och ett facit i formatet ovan.

**Steg 4: Automatiska kontroller.** Texter som inte klarar kontrollerna i avsnitt 5 sorteras bort.

### Kontroll av att implicit verkligen är implicit

En AI som ska skriva en uppgift som inte sägs rakt ut kan ändå råka skriva ut den. För att fånga det finns det en lista med förbjudna ord för varje kategori. För `RELIGION` står till exempel "muslim", "religion", "troende" och "kristen" på listan. Ett spann som är märkt som implicit får inte innehålla något av orden. Ett program kontrollerar det, så att uppgifterna verkligen är implicita och inte bara märkta så.

### Texter som liknar känsliga men inte är det

Ungefär en fjärdedel av texterna ska sakna känsliga uppgifter men ändå innehålla ord som påminner om dem:

- en moské eller ett parti som nämns utan koppling till någon person
- sjukdomsord som används bildligt, som "det här är ju sjukt"
- brott som omtalas allmänt, utan att någon pekas ut

De behövs för att kunna mäta precision, alltså hur ofta en metod har rätt när den flaggar något. Utan dem skulle en metod som flaggar varje text där ordet "moské" förekommer se lika bra ut som en metod som förstår sammanhanget.

Nekanden, som "han är inte medlem i facket", tas inte med i PoC:n. Det är oklart om de ska räknas som känsliga, och den frågan vill vi inte behöva avgöra nu.

### Storlek och uppdelning

Texterna delas upp i tre högar som används till olika saker:

| Hög | Storlek | Skrivs av | Används till |
|---|---|---|---|
| Test | ungefär 1 000 texter, med minst 50 exempel per kategori och uttryckstyp | Hälften av modell A, hälften av modell B | Låst. Används bara vid slutmätningen. |
| Dev | ungefär 200 texter | Modell A | Prova och justera instruktioner och gränsvärden under arbetets gång. |
| Train | ungefär 3 000 texter | Bara modell A | Träna klassificerare och encoder-modeller. |

**Varför testtexterna är låsta.** Om man justerar en metod tills den blir bra på testtexterna mäter man till slut hur väl metoden har anpassats till just de texterna, inte hur bra den är i allmänhet. Därför justerar vi bara mot dev-texterna och tittar på testtexterna först vid slutmätningen.

**Varför två olika AI-modeller skriver testtexterna.** Varje AI-modell har sin egen stil. En metod som tränas på texter från modell A kan lära sig känna igen modell A:s stil i stället för de känsliga uppgifterna. Träningstexterna kommer därför bara från modell A, medan testtexterna kommer från både A och B. Om en metod är mycket bättre på A:s testtexter än på B:s har den lärt sig stilen och inte uppgiften.

**Varför minst 50 exempel per kategori räcker.** Med 50 exempel blir osäkerheten i ett resultat ungefär plus minus 0,11–0,14. Om en metod hittar 40 av 50 (recall 0,80) ligger det verkliga värdet alltså troligen någonstans mellan 0,69 och 0,91. Det är för grovt för att skilja metoder som är nästan lika bra, men tillräckligt för att se tydliga skillnader, och det är vad en PoC behöver.

### Vilka AI-modeller som används

- **För att skriva texterna** använder vi en stark modell via Vertex AI, där både Gemini och Claude finns. Det viktigaste är att den skriver bra svenska. Kostnaden blir låg, eftersom det handlar om några tusen korta texter.
- **Modell A och modell B** ska komma från olika tillverkare. Om en av dem också testas som metod redovisar vi det, eftersom en modell kan ha en fördel när den ska analysera texter som den själv har skrivit.
- **Öppna modeller**, som vi kan köra via Model Garden eller på egna GPU:er, passar bättre att testa som metoder än att använda för att skriva texter. De motsvarar alternativet att köra analysen i vår egen miljö i stället för hos en extern leverantör, vilket är en av avvägningarna i fråga 3.

## 5. Kvalitetskontroll utan handmärkning

Eftersom ingen människa läser texterna kontrolleras varje AI-skriven text automatiskt. Texter som inte klarar alla tre kontrollerna sorteras bort.

1. **Formatkontroll.** Markeringarna går att tolka, positionerna stämmer och alla uppgifter som beställdes i scenariospecen finns med.
2. **Förbjudna ord.** Inga implicita spann innehåller ord som avslöjar kategorin rakt ut (se ovan).
3. **Granskning av en annan AI-modell.** En AI från en annan tillverkare än den som skrev texten får läsa texten och facit, och svara på två frågor:
   - Avslöjar varje markerad bit verkligen den angivna kategorin om den angivna personen?
   - Finns det känsliga uppgifter i texten som inte är markerade?

Vi redovisar hur stor andel av texterna som sorteras bort i varje kategori. Det visar vilka kategorier som är svåra att få AI:n att skriva bra texter om.

**En känd risk.** Granskningen kan sortera bort texter där uppgiften är så subtil att granskaren inte uppfattar den. Då blir de kvarvarande testtexterna något lättare för AI-baserade metoder, eftersom de mest svårfångade fallen har försvunnit. Risken minskar av att granskaren får se facit och bara ska bedöma det, i stället för att själv leta efter uppgifterna. Helt borta är den inte.

**En frivillig stickprovskontroll.** Om någon kan läsa 30 slumpvis valda texter, vilket tar ungefär en timme, får vi en grov uppfattning om hur bra facit är. Det är inget krav men rekommenderas.

## 6. Hur resultaten mäts

Samma poängprogram används för alla metoder och alla delar, så att resultaten går att jämföra.

**Huvudmått: recall per kategori på dokumentnivå.** För varje kategori räknar vi hur stor andel av de texter som innehåller kategorin som metoden har flaggat för just den kategorin. Det redovisas separat för uppgifter som sägs rakt ut och uppgifter som går att lista ut av sammanhanget. Precision, alltså hur stor andel av metodens flaggningar som var rätt, redovisas bredvid.

**Kompletterande mått:**

- **Spannivå:** pekar metoden också ut rätt ställe i texten? Det räcker att metodens spann överlappar facit.
- **Rätt person:** kopplar metoden uppgiften till rätt person? Kan bara mätas i den syntetiska delen, eftersom de färdiga dataseten inte anger vem uppgifterna gäller.
- **Identifierare:** hittar metoden namn, personnummer och liknande? Mäts främst i REDACT.

**Uppdelning.** Resultaten redovisas per del (REDACT, PrivoNest, syntetisk) och per AI-modell som skrev texterna.

**Osäkerhet.** Varje resultat redovisas med ett konfidensintervall, ett intervall som det verkliga värdet troligen ligger inom. Intervallen räknas fram med *bootstrap*: datorn drar slumpvis nya urval av testtexterna och räknar om resultatet för varje urval. Hur mycket resultatet varierar mellan urvalen visar hur osäkert det är. Två metoder jämförs på samma urval, så att det syns om skillnaden mellan dem är verklig eller kan bero på slumpen.

## 7. Vad PoC:n kan och inte kan visa

**Den kan visa:**

- vilka metoder som är bättre och sämre än andra
- hur mycket sämre metoderna är på uppgifter som går att lista ut av sammanhanget än på uppgifter som sägs rakt ut, per kategori
- vad metoderna kostar, hur snabba de är och om de kan köras i vår egen miljö (fråga 3)

**Den kan inte visa** hur bra metoderna är på riktiga underrättelser. Alla testtexter är antingen AI-skrivna eller hämtade från andra sammanhang.

Tre enkla kontroller ger ändå en fingervisning:

1. **Spelar det roll vem som skrev texterna?** Om metoderna hamnar i samma ordning på modell A:s och modell B:s testtexter beror resultatet mindre på vilken AI som skrev dem.
2. **Stämmer det med någon annans data?** Om metoderna hamnar i samma ordning på explicita uppgifter i vår syntetiska del som i REDACT, som någon annan har byggt, är det ett gott tecken.
3. **Liknar texterna verkligheten?** Om någon som arbetar med riktiga underrättelser läser ett 20-tal av texterna får vi veta om de liknar det vi faktiskt tar emot. Det är frivilligt.

De här begränsningarna ska stå tydligt när resultaten redovisas.

## 8. Arbetsgång och status

| Steg | Vad | Status |
|---|---|---|
| 1 | **REDACT-SV:** hämta datasetet, göra om det till vårt format och koppla dess etiketter till våra koder. | Klart |
| 2 | **Poängprogram och formatkontroll:** programmet som räknar poäng och programmet som kontrollerar att filer har rätt format. | Klart |
| 3 | **Textgeneratorn:** programmet som slumpar fram beställningar, instruktionerna till AI:n, tolkningen av markeringarna och kontrollerna. Vi skriver först 50 provtexter, läser dem och justerar. | Inte påbörjat |
| 4 | **Alla AI-skrivna texter:** test (av modell A och B), dev och train. | Inte påbörjat |
| 5 | **PrivoNest-SV:** stickprov och konvertering till vårt format, när Hugging Face har öppnats. | Inte påbörjat |
| 6 | **Två enkla referensmetoder** körs på allt för att testa att hela kedjan fungerar: en som letar efter ord ur en ordlista och en AI med skrivna instruktioner. Därefter börjar metodjämförelsen i fråga 2. | Inte påbörjat |

### Mappar i repot

```
benchmark/
  README.md       datablad: delarna, storlek och kända brister
  schema/         beskrivning av formatet och programmet som kontrollerar det
  extern/         hämtning och konvertering av REDACT och PrivoNest
  generering/     textgeneratorn (finns inte än)
  eval/           poängprogrammet
  data/           hämtade och genererade texter (sparas inte i repot)
```

## 9. Öppna frågor

1. **Var ska texterna genereras?** Antingen i molnmiljön där vi arbetar med repot, vilket kräver en GCP-nyckel som hemlighet och att miljön får nå Vertex AI, eller som ett program som körs direkt i GCP.
2. **Vilka AI-modeller finns i ert GCP-projekt,** och i vilken region och med vilka kvoter? Svaret avgör vilka modeller som kan bli A och B, och vilka AI-modeller som kan testas som metoder.
3. **Vilka sorters underrättelser ska texterna likna?** Om vi inte får något svar väljer vi några allmänna typer: underrättelser från myndigheter, från privatpersoner och från vård och skola.
