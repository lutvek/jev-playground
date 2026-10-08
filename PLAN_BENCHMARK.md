# Plan: benchmark-dataset (PoC)

Planen besvarar frågeställning 1 i [FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md) på PoC-nivå. Källorna står i [KALLOR.md](KALLOR.md).

**Ramar:**

- Det här är en PoC, inte ett fullskaligt projekt.
- Ingen manuell annotering.
- Ingen produktionsdata.
- En extern LLM får generera syntetisk data.
- Vi har tillgång till GCP: Vertex AI, Model Garden och egna GPU:er.

## Kort version

Färdiga dataset först, generering bara där hyllan inte räcker.

| Del | Källa | Täcker | Etiketter från | Storlek |
|---|---|---|---|---|
| **REDACT-SV** | Färdigt dataset (GitHub) | Identifierare, explicita uttryck för hälsa, brott, fack, religion, politik och sexuell läggning | Datasetet | 561 dokument |
| **PrivoNest-SV** | Färdigt dataset (Hugging Face), om ett stickprov håller måttet | Alla art. 9-kategorier och brott, mest explicita uttryck | Datasetet | ca 8 500 rader |
| **Syntetisk** | Genereras av oss med LLM | Det hyllan saknar: implicita uttryck i alla kategorier, i underrättelsegenren, med vem uppgiften gäller | Konstruktionen | ca 1 000 testtexter, ca 3 000 träningstexter |

Den syntetiska delen behövs eftersom inget färdigt dataset, på något språk, innehåller implicita art. 9-uttryck om identifierbara personer. Det är just den skillnaden mellan explicit och implicit som är kärnan i forskningsfrågan.

Etiketterna behöver inte annoteras. Vi bestämmer först vad texten ska innehålla, och sedan skriver LLM:en texten och märker ut var uppgifterna står.

## 1. Kategorier

| Kategori | Kod | Grund | Explicit exempel | Implicit exempel |
|---|---|---|---|---|
| Hälsa | `HEALTH` | art. 9 | "hon är sjukskriven för utmattning" | "hon har tid på BUP varje vecka" |
| Etniskt ursprung | `ETHNICITY` | art. 9 | "han är same" | "han jobbar med renskötseln i familjens sameby" |
| Politisk åsikt | `POLITICS` | art. 9 | "hon röstar på Vänsterpartiet" | "hon var med och startade partiets lokalavdelning" |
| Religiös eller filosofisk övertygelse | `RELIGION` | art. 9 | "han är muslim" | "han går i moskén varje fredag" |
| Medlemskap i fackförening | `TRADE_UNION` | art. 9 | "hon är med i Kommunal" | "han är klubbordförande på fabriken" |
| Sexualliv eller sexuell läggning | `SEXUALITY` | art. 9 | "han är homosexuell" | "han bor ihop med sin pojkvän" |
| Genetiska och biometriska uppgifter | `GENETIC_BIOMETRIC` | art. 9 | "hon bär på BRCA-mutationen" | (sällsynt, låg prioritet) |
| Lagöverträdelser | `CRIMINAL` | art. 10 | "han dömdes för misshandel 2019" | "han kom precis ut från Kumla" |

Identifierare: `PERSON`, `PERSONNUMMER`, `PHONE`, `EMAIL`, `ADDRESS`, `LOCATION`, `ORGANISATION`, `DATE` och `IDENTIFIER` (till exempel ärendenummer).

## 2. Format

Alla delar konverteras till samma JSONL-format, så att samma poängsättning fungerar överallt.

```json
{
  "id": "syn-000123",
  "part": "synthetic",
  "source": {"generator": "modell-a", "scenario_id": "scn-0042"},
  "text": "Jag skriver angående min granne Erik Lund. Han går i moskén varje fredag men har sedan i våras slutat äta och verkar mycket nedstämd.",
  "entities": [
    {"id": "P0", "role": "REPORTER", "mentions": []},
    {"id": "P1", "role": "SUBJECT", "mentions": [
      {"start": 21, "end": 31, "type": "PERSON"},
      {"start": 32, "end": 41, "type": "PERSON"}
    ]}
  ],
  "sensitive": [
    {"start": 47, "end": 72, "category": "RELIGION", "expression": "implicit", "subject": "P1"},
    {"start": 77, "end": 132, "category": "HEALTH", "expression": "implicit", "subject": "P1"}
  ]
}
```

Dokumentnivåetiketter (finns kategori X i texten?) härleds från spannen. För de färdiga dataseten fylls bara de fält i som datasetet har.

## 3. Färdiga dataset

**REDACT-SV.** Datasetet kan hämtas från GitHub redan nu. Det har 561 svenska dokument, och 157 av dem har art. 9/10-spann. Dess etiketter mappas till våra koder. Tre saker att veta:

- **Bara explicita uttryck.** Datasetet säger inget om implicita uttryck.
- **Etiketterna gäller ord, inte personer.** Ett partinamn märks även när ingen persons åsikt avslöjas. Därför används datasetet främst för identifierare, hälsa och brott. Övriga kategorier redovisas med förbehåll.
- **Mycket kodväxling.** Bara 244 dokument är helt på svenska. Resultat redovisas både för alla dokument och för de helt svenska.

**PrivoNest-SV.** Kräver att huggingface.co öppnas i molnmiljön. Vi tittar på ett stickprov på 20–30 rader. Håller kvaliteten används den svenska testdelen som extra testdata och träningsdelen som träningsdata till encoder-modellerna. Annars stryks den.

Engelska dataset, som TAB och syntetiska självutlämnanden, skulle kunna översättas. Det ingår inte i PoC:n eftersom det tillför lite jämfört med egen generering i rätt genre.

## 4. Syntetisk generering

### Så fungerar det

1. **Scenariospecar slumpas fram i kod.** Varje spec innehåller:
   - typ av underrättelse och avsändare
   - 1–3 personer med roller
   - 1–3 känsliga uppgifter, var och en med kategori, explicit eller implicit, och vem den gäller
   - längd och ton, inklusive talspråk och stavfel

   Namn tas från SCB:s namnstatistik och personnummer från Skatteverkets testpersonnummer.
2. **LLM:en skriver texten** och märker varje uppgift med en tagg, till exempel `<RELIGION implicit P1>går i moskén varje fredag</RELIGION>`. Personer och identifierare märks på samma sätt.
3. **Kod tolkar taggarna** till spann och tar bort dem ur texten.
4. **Automatisk kontroll** (avsnitt 5) sorterar bort texter som inte stämmer.

### Implicit på riktigt

För varje kategori finns en lista med förbjudna ord som namnger kategorin, till exempel "muslim", "religion", "troende" och "kristen" för `RELIGION`. Ett implicit spann får inte innehålla något av orden. Det kontrolleras i kod, så att implicita uttryck verkligen är implicita och inte bara märkta så.

### Svåra negativa exempel

Ungefär 25 procent av texterna saknar känsliga uppgifter men innehåller ord som liknar dem:

- en moské eller ett parti som nämns utan koppling till en person
- sjukdomsord i bildlig betydelse ("det här är ju sjukt")
- brott som omtalas allmänt

Utan dem kan precision inte mätas. Negationer ("han är inte medlem i facket") undviks helt i PoC:n, eftersom det är oklart om de ska räknas som känsliga.

### Storlek och uppdelning

| Mängd | Storlek | Generator | Användning |
|---|---|---|---|
| Test | ca 1 000 texter, minst 50 positiva fall per kategori och uttryckstyp | Hälften med modell A, hälften med modell B | Låst. Används bara för slutmätning. |
| Dev | ca 200 texter | Modell A | Justera promptar och tröskelvärden |
| Train | ca 3 000 texter | Bara modell A | Träna klassificerare och encoder-modeller |

Träningsdata kommer bara från modell A. Skillnaden mellan resultat på A-test och B-test visar då hur mycket metoderna har lärt sig generatorns stil i stället för själva uppgiften. Med 50 fall per cell blir konfidensintervallet för recall ungefär ±0,11–0,14. Det räcker för att se tydliga skillnader i en PoC.

### Modeller på GCP

- **Generering:** en stark modell via Vertex AI, där både Gemini och Claude finns. Svensk textkvalitet är viktigast här, och kostnaden är låg för några tusen korta texter.
- **Modell A och B** kommer från olika modellfamiljer. Om en av dem också testas som metod redovisas det, eftersom den kan gynnas av att ha skrivit testtexterna.
- **Öppna modeller** (via Model Garden eller på egen GPU) passar bättre som metoder att testa än som generatorer. De motsvarar alternativet att köra modellen i egen miljö, och det är en av avvägningarna i frågeställning 3.

## 5. Kvalitet utan manuell annotering

Varje genererad text går igenom automatiska kontroller. Texter som inte klarar dem sorteras bort.

1. **Format.** Taggarna går att tolka, spannen ligger rätt och alla uppgifter i specen finns med.
2. **Förbjudna ord** i implicita spann (se ovan).
3. **Verifiering med en annan modell.** En LLM från en annan familj än generatorn får texten och etiketterna. Den svarar på två frågor: avslöjar varje märkt spann verkligen den angivna kategorin om den angivna personen? Finns det känsliga uppgifter som inte är märkta?

Hur stor andel som sorteras bort, per kategori, redovisas. Det visar vilka kategorier som är svåra att generera.

**Känd risk.** Verifieringen kan sortera bort implicita texter som är för subtila för en LLM. Det gör testet något lättare för LLM-metoder. Att verifieraren ser etiketterna, i stället för att själv hitta uppgifterna, minskar risken men tar inte bort den. Om någon kan läsa igenom 30 slumpade texter, ungefär en timme, får vi ett grovt mått på hur bra etiketterna är. Det är frivilligt men rekommenderas.

## 6. Utvärdering

Ett gemensamt poängsättningsskript används för alla metoder och alla delar.

- **Primärt:** recall per kategori på dokumentnivå, uppdelat på explicit och implicit. Precision redovisas bredvid.
- **Sekundärt:**
  - spannivå med överlapp
  - attribution, det vill säga rätt person (bara i den syntetiska delen)
  - identifierare (främst i REDACT)
- **Uppdelning:** per del och per generator.
- **Osäkerhet:** konfidensintervall med bootstrap. Metoder jämförs parvis.

## 7. Vad PoC:n kan och inte kan visa

**Kan visa:**

- hur metoderna rangordnas
- hur stort glappet är mellan explicita och implicita uttryck, per kategori
- kostnad, latens och var modellen kan köras (frågeställning 3)

**Kan inte visa:** hur väl siffrorna håller på riktiga underrättelser.

Tre billiga kontroller ger ändå en indikation:

1. **Generatorkänslighet.** Om metoderna rangordnas likadant på A-test och B-test beror resultatet mindre på vem som skrev texterna.
2. **Extern jämförelse.** Om rangordningen på explicita uttryck stämmer mellan vår syntetiska del och REDACT, som någon annan har byggt, är det ett gott tecken.
3. **Läsning av domänperson.** En snabb genomläsning av ett 20-tal texter visar om de liknar riktiga underrättelser. Den är frivillig.

Detta ska stå tydligt i resultatredovisningen.

## 8. Steg

1. **REDACT-SV:** hämta, konvertera till formatet och mappa etiketterna. Kan göras nu.
2. **Poängsättningsskript och formatvalidering.**
3. **Generator:** spec-slumpare, prompt, taggtolkning och kontroller. Generera 50 pilottexter, titta på dem och justera.
4. **Full generering:** test (A+B), dev och train.
5. **PrivoNest-SV:** stickprov och konvertering, när huggingface.co är öppnat.
6. **Två enkla baslinjer** (regex/lexikon och en LLM med prompt) körs på allt för att testa hela kedjan. Därefter tar metodjämförelsen i frågeställning 2 vid.

**Struktur i repot:**

```
benchmark/
  README.md       datablad: delar, storlek, kända brister
  schema/         JSON-schema och validering
  extern/         hämtning och konvertering av REDACT och PrivoNest
  generering/     spec-slumpare, promptar, taggtolkning, kontroller
  eval/           poängsättning
  data/           genererade och konverterade data
```

## 9. Öppna frågor

1. **Var ska genereringen köras?** Antingen här i molnmiljön, vilket kräver en GCP-nyckel som hemlighet och nätverksåtkomst till Vertex AI, eller som skript i GCP.
2. **Vilka modeller finns i ert GCP-projekt** (region och kvoter)? Det styr valet av generator A och B och vilka LLM:er som testas som metoder.
3. **Vilka typer av underrättelser** ska texterna efterlikna? Utan svar väljer vi några allmänna typer: underrättelser från myndigheter, från privatpersoner och från vård och skola.
