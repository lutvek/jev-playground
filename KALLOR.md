# Källor för benchmark-datasetet

Här går vi igenom vilka färdiga dataset, texter och verktyg som finns och om de går att använda i benchmarken. Genomgången gjordes 2026-10-08. Den omfattar Hugging Face, Språkbanken, svenska myndigheters öppna data, GitHub och forskningslitteratur.

Planen som bygger på genomgången står i [PLAN_BENCHMARK.md](PLAN_BENCHMARK.md). Begrepp som kan vara obekanta förklaras i [ORDLISTA.md](ORDLISTA.md).

## Hur säkra uppgifterna är

Alla källor har inte gått att kontrollera lika noga. Molnmiljön där genomgången gjordes nådde bara GitHub. Webbplatser som huggingface.co, spraakbanken.gu.se, domstol.se, jo.se, skatteverket.se och scb.se var blockerade.

Varje källa är därför märkt med hur väl vi har kontrollerat den:

| Märkning | Betyder |
|---|---|
| **[V]** verifierad | Vi har laddat ner datan och räknat själva. |
| **[D]** dokumenterad | Vi har läst källans dokumentation eller kod på GitHub, men inte undersökt själva datan. |
| **[S]** sökträff | Vi har bara sett källan i en sökmotors träfflista. Uppgifterna måste kontrolleras innan källan används. |

## Det viktigaste vi kom fram till

1. **Det finns inget svenskt dataset med riktiga texter där känsliga uppgifter är uppmärkta per kategori enligt artikel 9.** Varken på Hugging Face, hos Språkbanken eller i publicerad forskning.
2. **Det finns inget dataset, på något språk, som märker ut känsliga uppgifter om identifierbara personer som går att lista ut av sammanhanget.** Det närmaste är SynthPAI, som har uppgifter om personer som går att lista ut av sammanhanget, men inte de känsliga kategorierna i GDPR artikel 9. Den delen måste vi alltså bygga själva.
3. **Två AI-skrivna, flerspråkiga dataset har svenska texter där känsliga uppgifter och brott är märkta.** Det är REDACT, som vi har kontrollerat, och PrivoNest, som vi inte har kunnat kontrollera. I båda sägs uppgifterna nästan alltid rakt ut.
4. **Fackmedlemskap, brott och genetiska eller biometriska uppgifter är de kategorier där det finns minst data överallt.** Etniskt ursprung finns bara i PrivoNest och i det engelska datasetet TAB.
5. **Se upp med etiketten "SEX".** I både TAB och SynthPAI betyder den kön, inte sexualliv eller sexuell läggning.
6. **Den bästa källan till riktig svensk text är Domstolsverkets öppna gränssnitt för rättspraxis.** Där kan ett program hämta domstolsavgöranden. Migrationsmål handlar ofta om skälen till att någon söker asyl, och innehåller därför ofta religion, sexuell läggning, etniskt ursprung och politisk åsikt, ofta uttryckt indirekt. Arbetsdomstolens avgöranden innehåller fackmedlemskap.

## Källor som används i PoC:n

### REDACT, svenska delen [V]

- **Var:** [GitHub](https://github.com/guneeshvats/REDACT-PII-Benchmark) och [Hugging Face](https://huggingface.co/datasets/guneeshv/REDACT-PII-Benchmark). På Hugging Face måste man logga in och godkänna villkoren innan man kan ladda ner.
- **Vad:** 561 svenska texter som en AI har skrivit, till exempel e-post, ärendeanteckningar och chattar, bland annat i myndighetsmiljöer. 157 av texterna innehåller känsliga uppgifter eller brott. Antal märkta uppgifter i rådatan, före konverteringen: hälsa 192, brott 82, sjukskrivning 74, allergi 52, fack 38, religion 15, parti 15 och sexuell läggning 7. Dessutom finns 364 personnummer.
- **Villkor:** Datasetet har egna villkor, "REDACT Dataset Terms". Forskning och benchmarking är tillåtet om man anger källan. Det är förbjudet att använda datan för att kartlägga personer (profilering) eller för att försöka ta reda på vilka riktiga personer som ligger bakom (återidentifiering). Koden har MIT-licens, som tillåter nästan all användning.
- **Används till:** att kontrollera våra resultat mot data som någon annan har byggt, för uppgifter som sägs rakt ut och för identifierare.

Hur vi har gjort om datasetet till vårt format, och siffrorna efter konverteringen, står i [benchmark/README.md](benchmark/README.md#redact-sv).

### PrivoNest, svenska delen [S]

- **Var:** [Hugging Face](https://huggingface.co/datasets/abbasrazalagha/PrivoNest_Multilingual_Privacy_Dataset).
- **Vad:** Enligt datasetets beskrivning 8 545 svenska rader: 6 968 för träning, 391 för justering (validering, motsvarar vår dev-hög) och 1 186 för test. Det har 88 olika etiketter, bland annat alla känsliga kategorier i artikel 9 och `CRIMINAL_RECORD` för brott.
- **Villkor:** Apache-2.0 enligt beskrivningen, en öppen licens som tillåter fri användning.
- **Används till:** om ett stickprov visar att kvaliteten håller, som extra testmaterial och som träningsdata för encoder-modellerna, de mellanstora språkmodeller som vi tränar på egna exempel.
- **Förbehåll:** Datasetet är uppladdat av en enskild person, det är okänt hur texterna har tagits fram och vi har inte sett en enda rad av det.

## Källor om projektet växer

De här källorna innehåller riktiga svenska texter men inget facit. Någon måste märka upp dem för hand, och det ingår inte i PoC:n.

### Domstolsverkets Rättspraxis-API [D]

- **Adress:** `https://rattspraxis.etjanst.domstol.se/api/v1`
- **Vad:** Avgöranden från Högsta domstolen, Högsta förvaltningsdomstolen, hovrätterna, kammarrätterna, Arbetsdomstolen och Migrationsöverdomstolen. Hela avgöranden finns som PDF från mars 2025, och sammanfattningar (referat) från 1981. Parterna anges med initialer.
- **Villkor:** Öppna data. Ingen inloggning krävs.
- **Används till:** utdrag som vi märker upp själva, för att få riktigt språk. Olika domstolar ger olika kategorier:
  - Migrationsmål: religion, sexuell läggning, etniskt ursprung och politisk åsikt.
  - Arbetsdomstolen: fackmedlemskap.
  - Kammarrätternas mål om tvångsvård enligt LVU (lagen om vård av unga) och LVM (lagen om vård av missbrukare): hälsa.
  - Hovrätterna: brott.

### JO-beslut [D]

- **Var:** [jo.se](https://www.jo.se/jo-beslut/sokresultat/)
- **Vad:** Justitieombudsmannens beslut om klagomål på myndigheter, ofta socialtjänst, polis och psykiatri. Det går inte att ladda ner alla på en gång, utan varje beslut är en egen PDF. Programmet [ferenda](https://github.com/staffanm/ferenda), som ligger bakom webbplatsen lagen.nu, har kod som hämtar dem.
- **Villkor:** Allmänna handlingar.
- **Används till:** utdrag att märka upp. Av källorna här är det de texter som ligger närmast våra underrättelser.

### Flashback och Familjeliv, via Språkbanken och Korp [S]/[D]

- **Vad:** Mycket stora samlingar av inlägg från diskussionsforum, till exempel Familjelivs "Känsliga rummet" och Flashbacks avdelningar "Droger" och "Sex".
- **Villkor:** CC BY 4.0, alltså fri användning om man anger källan.
- **Viktig begränsning:** I filerna som går att ladda ner ligger meningarna i omkastad ordning, och sökverktyget Korp visar bara en mening i taget. Det går alltså inte att läsa längre sammanhängande inlägg.
- **Används till:** en separat samling enskilda meningar med vardagligt språk. Den skulle ge många uppgifter som sägs indirekt, och många meningar som liknar känsliga utan att vara det. Inga användarnamn sparas.

## Förebilder för formatet och metoden

De här källorna används inte som data. Vi har hämtat idéer från dem om hur facit ska vara uppbyggt och hur texter kan genereras.

- **TAB, Text Anonymization Benchmark** ([GitHub](https://github.com/NorskRegnesentral/text-anonymization-benchmark), MIT-licens) [V]. Ett engelskt dataset för anonymisering av domar från Europadomstolen. Vi har tagit efter hur märkningen är uppbyggd:
  - *Direkta identifierare*, som pekar ut en person på egen hand, till exempel ett namn.
  - *Indirekta identifierare*, som kan peka ut en person tillsammans med andra uppgifter, till exempel yrke och hemort.
  - *Känsliga uppgifter* som märks på textbitar: `HEALTH`, `POLITICS`, `ETHNIC`, `BELIEF` och `SEX` (som betyder kön).
  - *Koreferens*, alltså att olika omnämnanden, som "Erik Lund" och "han", märks som samma person.

  I TAB ingår fackmedlemskap i `POLITICS`, och brott finns inte med.
- **W3C DPV-PD** ([GitHub](https://github.com/w3c/dpv)) [V]. En begreppslista för personuppgifter, framtagen av en arbetsgrupp inom W3C, organisationen bakom webbens standarder. Den har en klass för varje känslig kategori i artikel 9 och för lagöverträdelser. Vi använder den för att definiera våra kategorier.
- **SynthPAI** ([GitHub](https://github.com/eth-sri/SynthPAI)) [V]. Har en skala från 1 till 5 för hur svårt det är att lista ut en uppgift som inte sägs rakt ut, och en metod för att låta en AI skriva texter utifrån påhittade personprofiler. Den har inte de känsliga kategorierna i artikel 9. Licensen är MIT på GitHub men uppges vara CC BY-NC-SA, som förbjuder kommersiell användning, på Hugging Face.
- **ConfAIde och PrivacyLens** [V]. Recept för att låta en AI skriva berättelser om namngivna personer med känsliga uppgifter.
- **SweLL och Mormor Karl** (Språkbanken) [D]. En svensk uppsättning etiketter för att byta ut identifierare mot påhittade (pseudonymisering). Själva texterna delas inte.

## Byggstenar för de AI-skrivna texterna

Det här är listor som generatorn, alltså programmet som låter en AI skriva våra testtexter, kan hämta realistiska men påhittade uppgifter från.

- **Skatteverkets testpersonnummer** [D]. Ungefär 40 000 personnummer som aldrig delas ut till riktiga personer och som får användas för test. Går att hämta från `https://skatteverket.entryscape.net/rowstore/dataset/b4de7df7-63c0-4e7e-bb59-1f156a591763`.
- **Svenska namn med frekvenser** ([svensktext/namn](https://github.com/peterdalle/svensktext/tree/master/namn)) [D]. Förnamn och efternamn från SCB (2020) med uppgift om hur många som bär varje namn, så att vanliga namn kan bli vanliga även i våra texter. Repot saknar licensfil, så det är oklart vad som är tillåtet. Svensk nationell datatjänst har en annan samling, SND 2021-272, med namn uppdelade per födelseland under licensen CC BY 4.0.
- **swedish-personas** ([Hugging Face](https://huggingface.co/datasets/birgermoell/swedish-personas)) [S]. 100 000 påhittade personer, framtagna så att de följer SCB:s statistik. CC BY 4.0. Kan användas som utgångspunkt när beställningarna till AI:n, de så kallade scenariospecarna i [PLAN_BENCHMARK.md](PLAN_BENCHMARK.md#så-går-det-till), slumpas fram.
- **Fiktiva identifierare** ([maskera TEST_DATA.md](https://github.com/joelhagvall/maskera/blob/main/docs/TEST_DATA.md)) [D]. En lista över telefonnummer som är reserverade för film, böcker och liknande, exempeladresser, testkonton och annat som går att använda utan att peka ut någon riktig person.

## Färdiga verktyg att jämföra med

Det här är verktyg och modeller, inte dataset. De är aktuella som baslinjer, alltså referensmetoder, när metoderna jämförs i fråga 2.

- **[okasi/swedish-pii](https://github.com/okasi/swedish-pii)** [V]. Svenska ordlistor som letar efter bland annat religion, politisk ideologi, fackmedlemskap och sexuell läggning. MIT-licens. En bra regelbaserad baslinje för uppgifter som sägs rakt ut.
- **[sparv-sbx-pi-detection](https://github.com/spraakbanken/sparv-sbx-pi-detection)** [D]. Språkbankens modeller för identifierare, byggda på KB-BERT, en svensk encoder-modell från Kungliga biblioteket. Enligt beskrivningen fungerar de sämre på andra sorters texter än de har tränats på.
- **KB/bert-base-swedish-cased-ner** och **joelhagvall/maskera-sv-ner** [S]. Svenska NER-modeller, alltså modeller som känner igen namn på personer, platser och organisationer.
- **tabularisai/eu-pii-safeguard** och **bardsai/eu-pii-anonimization-multilang** [S]. Flerspråkiga modeller för personuppgifter. Den senare uppger att den kan känna igen de känsliga kategorierna i artikel 9.

## Undersökta men inte användbara nu

| Källa | Varför den inte används |
|---|---|
| **Stockholm EPR PHI-korpusen** (patientjournaler) | Får bara användas av forskare vid Stockholms universitet, med godkänd etikprövning. |
| **SweLL-gold** | Kräver ansökan, och alla känsliga uppgifter har samma etikett, `sensitive`, utan uppdelning i kategorier. |
| **i2b2/n2c2 2014** | På engelska, har bara identifierare och kräver avtal. |
| **Gretel finance multilingual** och äldre versioner av **ai4privacy** | Har ingen svenska, eller så är det osäkert om de har det, och de har bara identifierare. |
| **BiaSWE**, svenska dataset om hatiska uttalanden och **Riksdagens öppna data** | Handlar om grupper eller offentliga personer, inte om privatpersoner. Kan ge meningar som liknar känsliga utan att vara det, men inga exempel på känsliga uppgifter om privatpersoner. |
| **SPeDaC** | Kräver avtal med författarna. |
| **SUC 3.0/SUCX**, **swedish_ner_corpus**, **wikiann** och **MAPA** | Har bara namn, platser och organisationer märkta. |
| **swelaw** (Hugging Face) | Juridisk text utan märkning, där namnen för det mesta redan är borttagna. Rättspraxis-API:et ger samma sorts text med bättre uppgifter om varje avgörande. |

## Forskning att läsa

- **Pilán m.fl. 2022**, *Computational Linguistics*. Artikeln som beskriver TAB.
- **Szawerna m.fl. 2024–2025** (Språkbanken). Om att automatiskt hitta personuppgifter i svenska elevtexter.
- **arXiv 2507.10582.** Om att anonymisera 10 842 svenska LVM-domar med hjälp av en stor språkmodell (LLM). Datan delas bara med forskare som har godkänd etikprövning.
- **Examensarbete vid Mittuniversitetet**, "Identifying Sensitive Data using NER with LLMs" (diva2:1876988). Vi har inte kontrollerat innehållet.
