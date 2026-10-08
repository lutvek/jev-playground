# Angreppssätt att testa

**Kort sagt:** Det här dokumentet går igenom vilka *sorters* metoder som är värda att testa i benchmarken, alltså angreppssätt snarare än enskilda modeller. Det hör till fråga 2 och 3 i [FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md): hur bra är olika metoder, och vad kostar de?

Genomgången gjordes 2026-10-08 med webbsökning. Källorna står sist i dokumentet. Begrepp som kan vara obekanta förklaras där de dyker upp och finns också i [ORDLISTA.md](ORDLISTA.md).

## Det viktigaste vi kom fram till

1. **De fyra metodtyperna i forskningsfrågan täcker inte allt.** Fyra angreppssätt saknas och är värda att ta med:
   - *inbäddningar*, som jämför betydelsen hos en mening med betydelsen hos exempelmeningar
   - *zero-shot-modeller* som GLiNER, som letar efter det man beskriver med ord utan att först tränas på exempel
   - *beslutsmodeller* som Jev, som svarar på frågor med fasta svarsalternativ och ger en sannolikhet för varje svar
   - *kombinationer*, där en billig metod sållar och en LLM bara läser det som har sållats fram
2. **Identifierare och känsliga uppgifter är två olika problem.** Identifierare, som personnummer och namn, hittas redan bra med regex och NER. Känsliga uppgifter, särskilt de som inte sägs rakt ut, kräver metoder som förstår vad en mening betyder.
3. **Det är på implicita uppgifter som metoderna troligen skiljer sig mest.** Forskning visar att LLM:er är bra på att lista ut uppgifter om personer ur sammanhanget. Samtidigt är tränade encoder-modeller ofta lika bra eller bättre när mönstret är tydligt. Det är just den skillnaden benchmarken är byggd för att mäta.
4. **Nekanden och frågan om vem uppgiften gäller är egna delproblem.** Det finns beprövade regelmetoder för dem, NegEx och ConText, som kan läggas ovanpå vilken annan metod som helst. NegEx finns redan anpassad till svenska.
5. **Metoderna bör jämföras vid samma recall.** Recall är det viktigaste måttet. Därför bör varje metod först ställas in på dev-texterna så att den hittar en bestämd andel av uppgifterna, till exempel 90 procent. Sedan jämförs hur många falsklarm metoderna ger för att nå dit.

## Tre frågor att ställa om varje metod

Metoderna skiljer sig åt på tre sätt som avgör hur de kan användas och vad de kostar.

- **Vad lämnar metoden ifrån sig?** Bara vilka kategorier texten innehåller (dokumentnivå), en flagga per mening, exakta spann, eller också vem uppgiften gäller. Poängprogrammet räknar bara på det metoden lämnar, se [benchmark/README.md](benchmark/README.md#poängsättning).
- **Hur många exempel behöver den?** Inga alls (*zero-shot*), några få per kategori (*few-shot*) eller tusentals (*finjustering*). Med de ungefär 3 000 syntetiska träningstexterna i planen går alla tre att testa.
- **Var körs den?** På en vanlig server utan GPU, på en egen GPU eller hos en extern leverantör. Det avgör både kostnaden och om texterna lämnar vår egen miljö.

## Översikt

| | Angreppssätt | Väntas klara | Behöver exempel | Körs | Nytt jämfört med forskningsfrågan |
|---|---|---|---|---|---|
| 1 | Regex med validering | Identifierare med fast form | Nej | Vanlig server | Nej |
| 2 | Lexikon med svensk ordanalys | Explicita uppgifter | Nej | Vanlig server | Nej |
| 3 | Kontextregler (nekande och vem) | Ett tillägg till andra metoder | Nej | Vanlig server | Ja |
| 4 | NER | Namn, platser och organisationer | Nej, färdiga modeller finns | Vanlig server | Nej |
| 5 | Statistisk klassificerare | Explicita uppgifter | Ja, tusentals | Vanlig server | Nej |
| 6 | Inbäddningar | Explicita, och delvis implicita | Få eller många | Vanlig server | Ja |
| 7 | Zero-shot-spannmodeller (GLiNER) | Okänt för svenska, måste testas | Nej, men kan finjusteras | Vanlig server | Ja |
| 8 | Finjusterad encoder-modell | Explicita, och troligen många implicita | Ja, tusentals | GPU för träning | Nej |
| 9 | LLM med instruktioner | Troligen bäst på implicita | Inga eller få | Extern eller egen GPU | Nej |
| 10 | Beslutsmodell (Jev) | Okänt för svenska, måste testas | Nej | Extern tjänst | Ja |
| 11 | Finjusterad liten LLM | Som 9, men lokalt | Ja, tusentals | Egen GPU | Nej |
| 12 | Kombinationer | Beror på delarna | Beror på delarna | Blandat | Ja |

Kolumnen *Väntas klara* är en förhandsbedömning utifrån forskningen. Det är just den bedömningen benchmarken ska pröva.

## Angreppssätten ett i taget

### 1. Regex med validering

Ett *regex* är ett textmönster, till exempel "sex siffror, ett bindestreck och fyra siffror". Ett mönster ensamt ger många falsklarm, eftersom många nummer har samma form. Det blir mycket bättre med två tillägg:

- **Validering.** Ett personnummer har en kontrollsiffra som räknas fram ur de andra siffrorna, och ett datum måste vara ett datum som finns. Ett nummer som inte klarar kontrollen flaggas inte.
- **Kontextord.** Ord som "personnr" eller "tel" i närheten gör en träff säkrare. Ramverket Microsoft Presidio är byggt på just den idén och kan byggas ut med egna mönster för svenska.

**Klarar:** `PERSONNUMMER`, `PHONE`, `EMAIL` och `IDENTIFIER` med känt format, till exempel ärendenummer. Klarar inte känsliga uppgifter.

**Roll i benchmarken:** baslinje för identifierare. Det är också en byggsten i alla andra metoder. Det finns ingen anledning att låta en LLM leta efter personnummer.

### 2. Lexikon med svensk ordanalys

Ett *lexikon* är en ordlista per kategori. En metod som flaggar texter med ord ur listan finns redan med i planen, som en av de två första referensmetoderna (steg 6 i [PLAN_BENCHMARK.md](PLAN_BENCHMARK.md#8-arbetsgång-och-status)). För svenska blir den mycket bättre med två sorters ordanalys:

- **Grundform** (*lemmatisering*). "moskén" och "moskéerna" ska träffa "moské".
- **Sammansättningar.** Svenska skriver ihop ord. En lista med "diabetes" missar "diabetesmottagningen" om inte ordet först delas upp. Språkbankens verktyg Sparv gör både grundform och uppdelning av sammansättningar.

Listorna kan byggas från öppna källor, till exempel diagnosnamn ur ICD-10-SE, läkemedelsnamn, riksdagspartierna, fackförbunden inom LO, TCO och Saco, trossamfund, brottsrubriceringar i brottsbalken och Kriminalvårdens anstalter. Svenska listor för flera kategorier finns redan i [okasi/swedish-pii](https://github.com/okasi/swedish-pii).

Listor över platser och verksamheter, som "Kumla" eller "BUP", fångar en del uppgifter som inte sägs rakt ut. Det är ett billigt sätt att se hur långt man kommer utan att förstå sammanhanget.

**Klarar:** explicita uppgifter. **Svaghet:** flaggar varje omnämnande, även när ingen person pekas ut, så precisionen blir låg på de syntetiska texterna som bara liknar känsliga. **Styrka:** snabbt och helt förklarbart, eftersom man ser vilket ord som gav träffen.

### 3. Kontextregler: nekanden och vem uppgiften gäller

Kontextregler är ingen egen metod. De är ett lager som läggs på träffarna från en annan metod och avgör tre saker:

- **Är det nekat?** "Han är *inte* medlem i facket."
- **Är det hypotetiskt?** "*Om* hon skulle bli sjuk ..."
- **Gäller det någon annan?** "Hans *mamma* har diabetes."

Den mest kända metoden är *NegEx*, som letar efter signalord som "inte" och "ingen" i ett fönster runt träffen. Utbyggnaden *ConText* avgör också om uppgiften gäller patienten eller någon annan. Det är vårt problem med att koppla uppgiften till rätt person, i liten skala.

NegEx har anpassats till svenska journaltext, med en precision på 75 procent och en recall på 82 procent (Skeppstedt 2011). Listan med svenska signalord är offentlig. En nederländsk anpassning av ConText kom upp i 99–100 procent för vem uppgiften gällde, men i journaltext där det nästan alltid handlar om patienten. Det finns färdiga program för ConText, till exempel medspaCy.

**Roll i benchmarken:** att testa om lexikonmetoden (2) blir bättre med det här lagret. Nekanden finns i REDACT, där de är märkta med `ignore`. I den syntetiska delen ingår inte nekanden i PoC:n, men de texter som bara liknar känsliga mäter samma sorts precision.

### 4. NER

*NER* (named entity recognition) känner igen namn på personer, platser och organisationer. Det finns färdiga svenska modeller, se [KALLOR.md](KALLOR.md#färdiga-verktyg-att-jämföra-med).

**Klarar:** `PERSON`, `LOCATION`, `ORGANISATION` och ofta `DATE`. Klarar inte känsliga uppgifter.

**Roll i benchmarken:** baslinje för identifierare tillsammans med regex. NER behövs också för att koppla en uppgift till rätt person. För att kunna säga att hälsouppgiften gäller Erik Lund måste man först ha hittat "Erik Lund".

### 5. Statistisk klassificerare

En klassisk metod är att räkna vilka ord och ordpar som förekommer i en mening och låta en enkel modell, till exempel *logistisk regression*, lära sig hur mycket varje ord talar för varje kategori. Varje mening får noll eller flera kategorier. Meningens position i texten blir då spannet.

**Kräver:** träningstexterna. **Styrka:** snabb, billig och förklarbar, eftersom man kan se vilka ord som vägde tyngst. **Risk:** modellen kan lära sig ord som modell A, som skrev träningstexterna, gärna använder. Jämförelsen mellan modell A:s och modell B:s testtexter visar om det har hänt.

**Roll i benchmarken:** visar hur långt man kommer med "ord som brukar förekomma". En avancerad metod som inte slår den här är inte värd besväret.

### 6. Inbäddningar

En *inbäddningsmodell* gör om en mening till en lång lista med tal, en *vektor*, så att meningar med liknande betydelse får liknande tal. "Han går i moskén varje fredag" och "hon ber i kyrkan varje söndag" hamnar nära varandra fast de inte har ett enda ord gemensamt. Därför är angreppssättet intressant för uppgifter som inte sägs rakt ut.

Det finns tre varianter, med olika behov av exempel:

- **Likhetssökning mot en exempelbank.** Någon skriver 20–50 exempelmeningar per kategori. En mening flaggas om den liknar något av exemplen tillräckligt mycket. Ingen träning behövs, och förklaringen är enkel: "liknade exemplet X".
- **Inbäddning och enkel klassificerare.** Samma som metod 5, men med vektorerna i stället för orden. Tränas på träningstexterna.
- **SetFit.** Tränar om själva inbäddningsmodellen med några få exempel per kategori. I den ursprungliga artikeln räckte 8 exempel per kategori för att komma i nivå med en större modell som tränats på 3 000 exempel.

Det finns svenska och flerspråkiga inbäddningsmodeller, till exempel KBLab:s sentence-bert-swedish-cased. De går att köra utan GPU.

**Roll i benchmarken:** den billigaste lokala metoden som kan tänkas klara implicita uppgifter. Den passar också som första steg i en kaskad (metod 12).

### 7. Zero-shot-spannmodeller (GLiNER)

*GLiNER* är en familj av små modeller, ungefär 100–500 miljoner parametrar, alltså en bråkdel av en LLM. De pekar ut spann för etiketter som man beskriver med vanliga ord, till exempel "religiös övertygelse" eller "sjukdom eller hälsotillstånd". De behöver ingen träning för att fungera, men kan finjusteras på våra träningstexter. En systermodell, GLiClass, gör samma sak för hela texter i stället för spann. Båda går att köra utan GPU.

Under 2025–2026 har det kommit flera GLiNER-modeller för personuppgifter, till exempel GLiNER2-PII med 42 sorters identifierare. De är byggda för identifierare, inte för känsliga uppgifter.

**Okänt:** hur bra de flerspråkiga versionerna klarar svenska, och om de alls hittar uppgifter som inte sägs rakt ut. Enligt dem som har använt modellerna är formuleringen av etiketterna det som påverkar resultatet mest.

**Roll i benchmarken:** en lokal metod som pekar ut spann utan att behöva träningsdata. Den bör testas både utan träning och finjusterad.

### 8. Finjusterad encoder-modell

En *encoder-modell* är en mellanstor språkmodell av typen BERT som tränas vidare på våra exempel. Den finns redan med i forskningsfrågan. Det finns två sätt att ställa upp uppgiften, och båda är värda att testa:

- **Per ord** (*tokenklassificering*). Varje ord får en etikett, till exempel "början på ett hälsospann". Det ger exakta spann och passar för explicita uppgifter och identifierare.
- **Per mening** (*meningsklassificering*). Varje mening får noll eller flera kategorier. Uppgifter som inte sägs rakt ut har ofta otydliga gränser, som "har sedan i våras slutat äta och verkar mycket nedstämd". Då kan det vara lättare för modellen att lära sig vilka meningar som är känsliga än exakt var spannet börjar och slutar. Eftersom huvudmåttet räknas på dokumentnivå kan det räcka.

Som grund finns svenska modeller, som KB-BERT och AI Swedens RoBERTa, och nyare flerspråkiga, som mmBERT och EuroBERT, som klarar längre texter i ett svep. Äldre BERT-modeller läser bara ungefär 512 ordbitar åt gången, så längre texter måste delas upp. Språkbankens försök att hitta personuppgifter i svenska elevtexter fann att KB-BERT i regel var bäst av de modeller som testades.

En japansk studie från 2026 gjorde nästan exakt det vi planerar: en LLM märkte upp texter med känsliga personuppgifter, och sedan tränades en snabb modell på dem.

**Roll i benchmarken:** den viktigaste kandidaten bland metoder som kan köras i vår egen miljö.

### 9. LLM med instruktioner

En stor språkmodell får instruktioner i text och svarar med vad den hittar. Det finns flera varianter som skiljer sig i kostnad och träffsäkerhet:

- **Zero-shot:** bara beskrivningar av kategorierna.
- **Few-shot:** beskrivningarna plus några exempel. Ännu bättre är att för varje text välja de exempel ur träningstexterna som liknar texten mest, med hjälp av inbäddningar (metod 6).
- **Med eller utan resonemang:** modellen får "tänka" innan den svarar. Det kostar mer men kan hjälpa för uppgifter som måste listas ut.
- **Extern eller lokal modell:** en stark modell via Vertex AI, som Gemini eller Claude, jämfört med en öppen modell som körs i Model Garden eller på egna GPU:er. Skillnaden mellan dem är kärnan i fråga 3.

Tre praktiska råd:

- **Låt modellen citera, inte räkna.** LLM:er är dåliga på att räkna tecken. Be modellen återge den känsliga biten ordagrant och låt ett program leta upp var den står i texten. Det är samma lösning som Googles verktyg LangExtract använder.
- **Kräv ett fast svarsformat** (JSON), så att svaren alltid går att läsa in.
- **Fråga vem uppgiften gäller.** Koppling till rätt person blir nästan gratis med en LLM, men är svårt för de flesta andra metoder.

**Vad forskningen säger:** LLM:er är mycket bra på att lista ut uppgifter om personer ur sammanhanget. I en studie gissade de rätt på till exempel bostadsort och inkomst från Reddit-inlägg i 85 procent av fallen, till en hundradel av kostnaden för människor (Staab m.fl. 2024). Det är just den förmågan implicita uppgifter kräver. Jämförelser av LLM:er och finjusterade encoder-modeller för textklassificering visar å andra sidan att encoder-modellerna ofta är lika bra eller bättre när uppgiften styrs av tydliga mönster, och att LLM:ernas svar kan ändras mycket av små ändringar i instruktionen.

**Roll i benchmarken:** troligen den bästa metoden för implicita uppgifter, och därför den som visar hur bra det alls går att bli. Den finns med i planen som den andra av de två första referensmetoderna. Om samma modell också har skrivit testtexterna ska det redovisas, som planen redan säger.

### 10. Beslutsmodeller (Jev)

*Jev* är en modell från företaget TypeSafe AI som släpptes i september 2026. Den skriver ingen text. I stället skickar man in en text tillsammans med en eller flera frågor som har fasta svarsalternativ, och modellen svarar med en sannolikhet för varje alternativ. Frågorna kan vara av tre slag:

- **Välj ett alternativ** (`Choice`), av upp till 255 möjliga.
- **Placera på en skala** (`Score`).
- **Ja eller nej** (`Noul`): hur troligt det är att ett påstående stämmer, som ett tal mellan 0 och 1.

Det passar vår uppgift bra. För varje kategori kan man ställa en ja/nej-fråga, till exempel "Avslöjar texten något om en enskild persons religiösa övertygelse?", och få en sannolikhet tillbaka. Flera frågor i samma anrop tar ungefär lika lång tid som en.

**Det som talar för att testa den:**

- **Den ger sannolikheter.** Då kan man välja en gräns på dev-texterna och jämföra Jev med andra metoder vid samma recall. Det går sällan med en LLM.
- **Den behöver inga exempel.** Kategorierna beskrivs i frågorna, så den kan testas direkt, även på uppgifter som inte sägs rakt ut.
- **Den är billig och snabb.** Priset är ungefär 0,042 dollar per miljon ordbitar som skickas in, och svaren kostar inget. Det är en bråkdel av vad en stor LLM kostar. Oberoende tester anger svarstider runt 150 millisekunder.

**Det som måste kontrolleras, eller talar emot:**

- **Inga spann.** Jev svarar på frågor om det den får läsa, men pekar inte ut var i texten svaret finns. För att få spann kan frågorna ställas per mening, och meningen blir då spannet. Det ger fler anrop, men kostar lite.
- **Svenska.** TypeSafe uppger att modellen främst är tränad på engelska och är sämre på andra språk, men publicerar inga siffror. En oberoende utvärdering visar att träffsäkerheten sjunker utanför engelska, mest för små språk. Ett annat test fann att det försämrar resultatet mer att översätta frågorna än att texten är på ett annat språk. Därför bör både engelska och svenska frågor testas på de svenska texterna.
- **Var den körs.** Jev finns bara som en tjänst, hos TypeSafe och hos några mellanhänder, och körs i USA. Det finns inget dokumenterat alternativ med datacenter i EU, och den finns inte i Vertex AI. För benchmarken spelar det ingen roll, eftersom texterna är påhittade. För riktiga underrättelser innebär det att personuppgifter förs över till ett land utanför EU.
- **Ny och föränderlig.** Tjänsten finns bara i en tidig version, och reglerna för nya konton har ändrats flera gånger. Sannolikheterna kan skilja sig ungefär 0,05 mellan två körningar av samma text. Versionen bör därför låsas när gränserna ställs in.

Det finns öppna modeller som efterliknar Jev och kan köras lokalt, till exempel *Laya*, som har en flerspråkig version byggd på mmBERT. Utan träning är den svag enligt de tester som finns. Finjusterad blir den i praktiken samma sak som metod 8.

**Roll i benchmarken:** ett mellanting mellan en finjusterad encoder-modell och en LLM. Den behöver inga exempel, precis som en LLM, men ger sannolikheter och är billig. Den bör testas per text och per mening, med frågor på både engelska och svenska. Den passar också som första steg i en kaskad (metod 12).

### 11. Finjusterad liten LLM (destillation)

En öppen, liten LLM, med några miljarder parametrar, tränas vidare på träningstexterna. Det görs vanligen med *LoRA*, en billig träningsmetod som bara ändrar en liten del av modellen. Eftersom träningstexterna är skrivna av en stor LLM överförs i praktiken den stora modellens förmåga till en liten modell som kan köras på egen GPU. Det kallas *destillation*.

I studien UniversalNER blev en liten modell som tränats på ChatGPT:s svar bättre än ChatGPT själv på att hitta namn och andra entiteter i text.

**Roll i benchmarken:** visar om förståelsen hos en LLM går att få i vår egen miljö till lägre kostnad. Lägre prioritet än metod 8 och 9. Den blir intressant om LLM:er visar sig vara klart bättre än encoder-modellerna.

### 12. Kombinationer

I praktiken används nästan alltid flera metoder tillsammans. Fyra kombinationer är värda att testa:

- **Kaskad.** En billig metod med hög recall, till exempel inbäddningar (6), en encoder-modell (8) eller Jev (10), sållar fram de meningar som kan vara känsliga. Bara de skickas vidare till en LLM. Kostnaden sjunker med andelen som sållas bort. Risken är att sållet missar något, så dess recall ska mätas för sig. Forskning om kaskader visar stora besparingar, och att gränsen för sållet kan väljas så att en viss recall garanteras.
- **Union.** En text flaggas om någon av metoderna flaggar den. Det höjer recall, eftersom metoderna missar olika saker, men sänker precisionen.
- **LLM som granskare.** En billig metod flaggar brett och en LLM avgör vilka flaggor som stämmer. Det höjer precisionen.
- **Pseudonymisera först.** Regex och NER byter ut namn och nummer i vår egen miljö innan texten skickas till en extern LLM. Då lämnar färre identifierare miljön. Det löser inte allt: den känsliga uppgiften skickas ändå, och forskning visar att en LLM ofta kan lista ut uppgifter om personer även när identifierarna är borttagna.

En svensk studie om domar enligt LVM är ett exempel på en kombination som körs helt i egen miljö: en öppen LLM, uppbackad av NER och regler, på en enda GPU.

## Färdiga verktyg och tjänster att jämföra med

Utöver verktygen i [KALLOR.md](KALLOR.md#färdiga-verktyg-att-jämföra-med) finns tre som är värda att känna till:

- **Google Sensitive Data Protection** (tidigare Cloud DLP) i GCP. Har färdiga detektorer för identifierare, bland annat för enskilda länder. Den motsvarar "dagens verktyg" och är lätt att köra eftersom vi redan har GCP. Vilka svenska detektorer som finns måste kontrolleras i tjänsten, eftersom listan ändras.
- **OpenAI Privacy Filter**, en öppen modell från april 2026 som kan köras lokalt. Den hittar identifierare men inte känsliga uppgifter.
- **Microsoft Presidio**. Inte en modell utan ett ramverk som kopplar ihop regex, kontextord och NER, och som kan byggas ut med egna delar. En bra stomme för metod 1–4.

**Inte användbar:** Googles Natural Language API har en funktion som sorterar texter efter ämnen som hälsa, religion och politik. Den stöder inte svenska, och den säger vad en text handlar om, inte vad den avslöjar om en person.

## Hur metoderna bör jämföras

Planen beskriver redan hur poängen räknas. Fyra saker behöver läggas till när metoderna jämförs:

- **Jämför vid samma recall.** Många metoder ger ett tal för hur säkra de är. Då kan man välja en gräns på dev-texterna så att metoden når en bestämd recall per kategori, till exempel 0,90, och sedan jämföra precisionen på testtexterna. Annars ser en metod som flaggar mycket bra ut på recall och dålig på precision, och det går inte att säga vilken metod som är bäst. LLM:er ger sällan ett sådant tal. Då redovisas de som de är.
- **Jämför modell A och modell B för alla metoder som tränas** (5, 6, 8 och 11). De är de metoder som kan lära sig skrivstilen i stället för uppgiften.
- **Spann per mening.** Metoder som arbetar per mening lämnar hela meningen som spann. Det räknas som träff med poängprogrammets standardinställning, där det räcker att spannen överlappar med ett tecken, men oftast inte med `--iou 0.5`. Det ska stå i redovisningen.
- **Mät kostnad och tid** per 1 000 texter, och ange om texterna lämnar vår miljö.

## Förslag: vad PoC:n testar

Listan täcker alla tre frågorna ovan: vad metoden lämnar, hur många exempel den behöver och var den körs.

| Ordning | Metod | Varför |
|---|---|---|
| 1 | Regex med validering och färdig svensk NER | Baslinje för identifierare och byggsten för koppling till person. |
| 2 | Lexikon med svensk ordanalys, med och utan NegEx | Baslinje för explicita uppgifter. Finns redan i planen. |
| 3 | LLM via Vertex AI, zero-shot och few-shot | Troligen bäst på implicita uppgifter. Finns redan i planen. |
| 4 | Samma instruktioner till en öppen LLM i egen miljö | Visar vad det kostar i träffsäkerhet att inte skicka texterna vidare. |
| 5 | Jev, med frågor per text och per mening, på engelska och svenska | Behöver inga exempel, ger sannolikheter och är billig. Kan också vara sållet i en kaskad. |
| 6 | Statistisk klassificerare och inbäddningar, per mening | Billiga lokala metoder. Visar om implicita uppgifter går att fånga utan stora modeller. |
| 7 | Finjusterad svensk encoder-modell, per mening och per ord | Den viktigaste lokala kandidaten. |
| 8 | GLiNER, utan träning och finjusterad | Lokal spannmodell som inte behöver träningsdata. |
| 9 | Kaskad: rad 5, 6 eller 7 sållar, rad 3 eller 4 avgör | Svarar på kostnadsfrågan. |
| Senare | Finjusterad liten LLM | Om LLM:er är klart bättre än encoder-modellerna. |

## Om projektet växer

**Svag övervakning** (*weak supervision*) är ett sätt att få träningsdata från riktiga texter utan handmärkning. Flera ofullständiga metoder, till exempel regler, lexikon och en LLM, får märka upp samma omärkta texter. Ett program väger sedan ihop deras svar utifrån hur ofta var och en verkar ha rätt. Resultatet används för att träna en encoder-modell.

Med öppna svenska texter, som domstolsavgöranden från Domstolsverket eller meningar från Familjeliv och Flashback (se [KALLOR.md](KALLOR.md#källor-om-projektet-växer)), skulle modellerna bli mindre beroende av hur AI:n skriver de syntetiska texterna. Verktyget skweak är byggt för det här och kommer från Norsk Regnesentral, samma grupp som står bakom TAB.

## Öppna frågor

1. **Vilka öppna LLM:er finns i Model Garden, i vilken region och med vilka kvoter?** Svaret avgör vilka modeller som kan testas lokalt i metod 9 och 11. Frågan finns också i planen.
2. **Klarar de flerspråkiga GLiNER- och inbäddningsmodellerna, och Jev, svenska tillräckligt bra?** Det går snabbt att ta reda på med dev-texterna, och avgör om metod 6, 7 och 10 är värda mer arbete.
3. **Kan vi få ett konto hos TypeSafe?** Jev finns bara i en tidig version, och det har periodvis varit stängt för nya konton. Ett konto behövs för att testa metod 10.
4. **Ska sållet i kaskaden ha en garanterad recall?** I så fall behövs fler dev-texter per kategori än de ungefär 200 som planen räknar med.

## Källor

Genomgången gjordes med webbsökning. Webbplatsen arxiv.org gick inte att nå från molnmiljön, så uppgifterna om forskningsartiklarna kommer från sammanfattningar och sökträffar, inte från artiklarna själva. Siffrorna är författarnas egna och har inte kontrollerats av någon annan. Jev är så ny att nästan alla uppgifter om den kommer från andra än TypeSafe, som bloggar och oberoende tester, och de stämmer inte alltid överens.

**LLM:er och implicita uppgifter**

- Staab m.fl. 2024, *Beyond Memorization: Violating Privacy via Inference with Large Language Models*, ICLR 2024. [arXiv 2310.07298](https://arxiv.org/abs/2310.07298)
- *Do BERT-Like Bidirectional Models Still Perform Better on Text Classification in the Era of LLMs?*, Findings of EMNLP 2025. [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.1033/)
- *NLPeace@GermEval Shared Task 2025: Fine-Tuned BERT vs. Prompted LLMs*. [ACL Anthology](https://aclanthology.org/2025.konvens-2.28.pdf)
- Minamoto, Oda och Kawahara 2026, *Detecting Sensitive Personal Information in Japanese Pre-Training Corpora for Large Language Models*, Findings of ACL 2026. [arXiv 2606.12114](https://arxiv.org/abs/2606.12114)

**Kontextregler**

- Skeppstedt 2011, *Negation detection in Swedish clinical text: An adaption of NegEx to Swedish*, Journal of Biomedical Semantics. [PMC3194175](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3194175/)
- Harkema m.fl. 2009, *ConText: An algorithm for determining negation, experiencer, and temporal status from clinical reports*, Journal of Biomedical Informatics 42(5).
- [medspaCy](https://github.com/medspacy/medspacy), färdigt program med ConText.

**Inbäddningar, GLiNER och encoder-modeller**

- Tunstall m.fl. 2022, *Efficient Few-Shot Learning Without Prompts* (SetFit). [arXiv 2209.11055](https://arxiv.org/abs/2209.11055)
- [KBLab/sentence-bert-swedish-cased](https://huggingface.co/KBLab/sentence-bert-swedish-cased), svensk inbäddningsmodell.
- [GLiNER](https://github.com/urchade/GLiNER) och *GLiNER2-PII* (2026). [arXiv 2605.09973](https://arxiv.org/abs/2605.09973)
- [GLiClass](https://huggingface.co/knowledgator/gliclass-base-v3.0), klassificering av hela texter med samma idé som GLiNER.
- mmBERT [arXiv 2509.06888](https://arxiv.org/abs/2509.06888) och EuroBERT [arXiv 2503.05500](https://arxiv.org/abs/2503.05500), nyare flerspråkiga encoder-modeller.
- Szawerna m.fl. 2024, *Detecting Personal Identifiable Information in Swedish Learner Essays*. [ACL Anthology](https://aclanthology.org/2024.caldpseudo-1.7/)

**Jev**

- [TypeSafe AI, API-dokumentation](https://docs.typesafe.ai/api)
- Deußer, Sparrenberg och Sifa 2026, *Evaluating and Benchmarking the System One Model Jev*. [arXiv 2609.37647](https://arxiv.org/abs/2609.37647)
- [Galtea: Does an AI judge need to speak your customer's language?](https://galtea.ai/blog/multilingual-llm-judge-benchmark), om frågor på andra språk än engelska.
- [innFactory om Jev](https://innfactory.ai/en/ai-models/typesafe-jev/) och [Colchix om Jev och GDPR](https://colchix.com/blog/can-european-enterprises-use-jev), om var tjänsten körs.
- [awesome-typesafe-jev](https://github.com/AbdelStark/awesome-typesafe-jev), en samling verktyg och oberoende utvärderingar.
- [Laya](https://www.llmreference.com/model-family/laya), ett öppet alternativ som kan köras lokalt.

**Destillation och kombinationer**

- Zhou m.fl. 2024, *UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recognition*, ICLR 2024. [arXiv 2308.03279](https://arxiv.org/abs/2308.03279)
- Chen, Zaharia och Zou 2023, *FrugalGPT*. [arXiv 2305.05176](https://arxiv.org/abs/2305.05176)
- *BARGAIN*, kaskader med garanterad recall eller precision. [arXiv 2509.02896](https://arxiv.org/abs/2509.02896)
- *Transforming Sensitive Documents into Quantitative Data* (2025), om LVM-domarna. [arXiv 2507.10582](https://arxiv.org/abs/2507.10582)
- Lison m.fl. 2021, *skweak: Weak Supervision Made Easy for NLP*. [arXiv 2104.09683](https://arxiv.org/abs/2104.09683)
- [LangExtract](https://github.com/google/langextract), Googles verktyg som letar upp en LLM:s citat i texten.

**Verktyg och tjänster**

- [Microsoft Presidio](https://github.com/microsoft/presidio)
- [OpenAI Privacy Filter](https://openai.com/index/introducing-openai-privacy-filter/)
- [Google Sensitive Data Protection, lista över detektorer](https://cloud.google.com/sensitive-data-protection/docs/infotypes-reference)
- [Google Natural Language API, språkstöd](https://cloud.google.com/natural-language/docs/languages)
- [Sparv](https://spraakbanken.gu.se/sparv), Språkbankens verktyg för svensk ordanalys.
