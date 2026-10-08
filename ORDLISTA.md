# Ordlista

Här förklaras orden och förkortningarna som används i dokumenten. Dokumenten förklarar också varje begrepp kort första gången det dyker upp, så den här listan är till för att slå upp något i efterhand.

## Projektet

**Benchmark.** En fast samling testtexter med facit, och ett fast sätt att räkna poäng. Alla metoder testas på samma texter och poängsätts på samma sätt, så att resultaten går att jämföra.

**PoC (proof of concept).** Ett mindre försöksprojekt som ska visa om en idé håller, innan man lägger tid och pengar på en fullskalig version.

**Dataset.** En samling data. Här betyder det en samling texter med facit.

**Facit.** De rätta svaren för en text: vilka känsliga uppgifter som finns, var i texten de står och vem de gäller. I koden kallas facit ibland *gold*.

**Annotering.** Att en människa läser en text och märker ut var uppgifterna står och vad de är. Det är tidskrävande, och med riktiga texter innebär det att fler personer läser känsliga uppgifter. PoC:n är därför byggd för att klara sig utan annotering.

**Etikett.** Märkningen som talar om vad en bit text är, till exempel `HEALTH` för en hälsouppgift.

**Produktionsdata.** Riktiga texter från våra egna system. De används inte i PoC:n.

**Syntetisk data.** Texter som en AI-modell har skrivit på vår beställning. Personerna och händelserna är påhittade.

**Underrättelse.** I det här projektet ett meddelande i fritext som någon skickar in till oss, till exempel en myndighet eller en privatperson.

## Juridik

**Personuppgift.** En uppgift som går att koppla till en levande person.

**GDPR.** EU:s dataskyddsförordning, lagen om hur personuppgifter får hanteras.

**Känsliga personuppgifter (GDPR artikel 9).** Uppgifter som lagen skyddar extra hårt: etniskt ursprung, politiska åsikter, religiös eller filosofisk övertygelse, medlemskap i fackförening, genetiska uppgifter, biometriska uppgifter som används för att identifiera någon, hälsa, samt sexualliv eller sexuell läggning.

**Lagöverträdelser (GDPR artikel 10).** Uppgifter om brott, domar och liknande. De hör inte till artikel 9 men har egna, stränga regler. I projektet behandlas de som en känslig kategori.

**Identifierare.** Uppgifter som pekar ut vem någon är eller hur man når hen: namn, personnummer, telefonnummer, e-post, adress och liknande.

**Explicit uttryck.** Uppgiften sägs rakt ut. Exempel: "han är muslim".

**Implicit uttryck.** Uppgiften sägs inte rakt ut men går att lista ut av sammanhanget. Exempel: "han går i moskén varje fredag". Det är de här uttrycken som dagens verktyg missar, och de står i centrum för projektet.

**Pseudonymisering.** Att byta ut namn och andra identifierare i en text mot påhittade, så att texten inte längre pekar ut riktiga personer.

**PEP (person i politiskt utsatt ställning).** En person med ett viktigt offentligt uppdrag, till exempel en minister. Begreppet kommer från reglerna mot penningtvätt och säger inget om personens politiska åsikter.

## Metoder

**Regler och regex.** Fasta mönster som programmeraren skriver i förväg. Ett regex (reguljärt uttryck) beskriver ett textmönster, till exempel "sex siffror, ett bindestreck och fyra siffror" för ett personnummer. Fungerar bra för uppgifter med fast format.

**Lexikon.** En ordlista. En lexikonbaserad metod flaggar en text om den innehåller något av orden i listan, till exempel "muslim" eller "Vänsterpartiet".

**NER (named entity recognition).** Automatisk igenkänning av namn på personer, platser och organisationer i text.

**Statistisk klassificerare.** En enklare maskininlärningsmodell som lär sig av exempel vilka ord som brukar höra ihop med vilken kategori.

**Encoder-modell.** En typ av språkmodell, till exempel BERT, som läser en text och kan säga något om varje ord i den. Den är mycket mindre än en LLM, kan tränas på våra egna exempel och kan köras på egna servrar.

**Spanklassificering.** När en modell pekar ut bitar av texten och anger vilken kategori varje bit hör till.

**LLM (large language model).** En stor språkmodell, till exempel Gemini eller Claude, som kan skriva och läsa text på ett sätt som liknar en människas.

**Prompting.** Att styra en LLM genom att ge den instruktioner i text.

**Finjustering.** Att träna en befintlig modell vidare på egna exempel, så att den blir bättre på just vår uppgift.

**Generator.** Den LLM som skriver de syntetiska texterna. I planen används två, *modell A* och *modell B*, från olika tillverkare.

**Verifierare.** En LLM från en annan tillverkare än generatorn som granskar de syntetiska texterna och deras facit.

**Baslinje.** En enkel metod som andra metoder jämförs med. Om en avancerad metod inte slår baslinjen är den inte värd besväret.

**Zero-shot och few-shot.** En metod som fungerar utan några exempel alls är *zero-shot*. En metod som bara behöver några få exempel per kategori är *few-shot*.

**Lemmatisering.** Att föra tillbaka ett ord till dess grundform, så att till exempel "moskén" och "moskéerna" båda blir "moské".

**Kontextregler.** Regler som avgör om en träff är nekad ("han är *inte* med i facket"), hypotetisk eller gäller någon annan än den texten handlar om. De mest kända heter *NegEx* och *ConText*.

**Inbäddning.** En modell som gör om en mening till en lång lista med tal, en *vektor*, så att meningar med liknande betydelse får liknande tal. Används för att hitta meningar som betyder ungefär samma sak, även när de inte har några ord gemensamt.

**SetFit.** Ett sätt att träna en inbäddningsmodell för en uppgift med bara några få exempel per kategori.

**GLiNER.** En familj av små modeller som pekar ut bitar av texten för etiketter som man beskriver med vanliga ord, utan att först tränas på exempel.

**Beslutsmodell (Jev).** En modell som inte skriver text utan svarar på frågor med fasta svarsalternativ, med en sannolikhet för varje alternativ. Jev, från företaget TypeSafe AI, är den mest kända.

**Tokenklassificering och meningsklassificering.** Två sätt att ställa upp uppgiften för en encoder-modell. Vid *tokenklassificering* får varje ord en etikett, vilket ger exakta spann. Vid *meningsklassificering* får varje mening noll eller flera kategorier.

**LoRA.** En billig metod för finjustering som bara ändrar en liten del av modellen.

**Destillation.** Att träna en liten modell på svar från en stor, så att den lilla modellen lär sig göra ungefär samma sak till lägre kostnad.

**Kaskad.** En kedja av metoder där en billig metod först sållar fram det som kan vara intressant, och en dyrare metod bara läser det som har sållats fram.

**Svag övervakning (weak supervision).** Att låta flera ofullständiga metoder märka upp samma omärkta texter och sedan väga ihop deras svar till träningsdata.

## Data och format

**Spann.** En avgränsad bit av texten, angiven med var den börjar och var den slutar.

**Offset.** En position i texten, räknad i antal tecken från början. Första tecknet har offset 0. Ett spann med `start` 4 och `end` 9 omfattar tecknen på plats 4, 5, 6, 7 och 8, alltså inte tecknet på plats 9.

**JSON.** Ett vanligt textformat för strukturerad data, med fält och värden inom klammerparenteser.

**JSONL (JSON Lines).** En textfil där varje rad är ett eget JSON-objekt. Här är varje rad en text med sitt facit, eller en metods svar för en text.

**Post.** En rad i en JSONL-fil, alltså en text med facit.

**JSON-schema.** En formell beskrivning av vilka fält en post måste ha och vilka värden som är tillåtna. Den används för att automatiskt kontrollera att filer har rätt format.

**Prediktion.** En metods svar för en text: vilka känsliga uppgifter metoden tror finns och var.

**Test, dev och train.** Tre separata högar med texter. *Train* används för att träna modeller. *Dev* används för att prova och justera under arbetets gång. *Test* låses och används bara vid slutmätningen. Om man justerar metoderna mot testtexterna blir resultatet för bra, eftersom metoderna då har anpassats till just de texterna.

**Kodväxling.** När en text blandar språk, till exempel svenska och engelska i samma mening.

**Checksumma.** Ett slags fingeravtryck av en fil. Ändras ett enda tecken i filen blir checksumman en helt annan, så den visar att man har fått exakt rätt fil.

**Commit.** En sparad version av ett kodförråd i versionshanteringssystemet git. Att hänvisa till en commit är att hänvisa till exakt den versionen.

## Mått

**Recall (täckning).** Hur stor andel av de känsliga uppgifter som faktiskt finns som metoden hittar. Exempel: om 10 texter innehåller hälsouppgifter och metoden hittar 8 av dem är recall 8 av 10, alltså 0,80.

**Precision (träffsäkerhet).** Hur stor andel av det metoden flaggar som verkligen är rätt. Exempel: om metoden flaggar 12 texter för hälsa och 8 av dem verkligen innehåller hälsouppgifter är precision 8 av 12, alltså ungefär 0,67.

Recall och precision drar åt olika håll. En metod som flaggar allt får full recall men låg precision, och en metod som nästan aldrig flaggar får hög precision men låg recall. Därför redovisas alltid båda.

**Falsklarm.** När metoden flaggar något som inte finns. Många falsklarm ger låg precision.

**Dokumentnivå och spannivå.** Två sätt att räkna. På *dokumentnivå* är frågan om metoden förstår att texten innehåller en viss kategori, oavsett var. På *spannivå* är frågan om metoden också pekar ut rätt ställe i texten.

**Attribution.** Att koppla en uppgift till rätt person. I en text om både en granne och en avsändare räcker det inte att hitta hälsouppgiften, metoden ska också veta vems hälsa det gäller.

**IoU (intersection over union).** Ett mått på hur väl två spann överlappar: längden på den gemensamma delen delat med längden på hela området som de två spannen täcker tillsammans. 1 betyder att de är exakt lika, 0 att de inte möts alls.

**Makromedelvärde (`MACRO`).** Medelvärdet av ett mått över alla kategorier, där varje kategori väger lika mycket oavsett hur vanlig den är. Det hindrar att en vanlig kategori som hälsa döljer att metoden är dålig på ovanliga kategorier.

**Konfidensintervall.** Ett intervall som det sanna värdet troligen ligger inom. Ett resultat från ett begränsat antal testtexter är alltid lite osäkert. Ett 95-procentigt konfidensintervall från 0,70 till 0,90 betyder ungefär att vi är ganska säkra på att metodens verkliga recall ligger någonstans där.

**Bootstrap.** Ett sätt att räkna ut konfidensintervall. Datorn drar slumpmässigt nya urval av testtexterna, där samma text kan komma med flera gånger, och räknar om måttet för varje urval. Här görs det 1 000 gånger. Hur mycket resultatet varierar mellan urvalen visar hur osäkert det är.

**p-värde.** Ett mått på hur troligt det är att se en så stor skillnad mellan två metoder av en slump, om de i själva verket var lika bra. Ett lågt p-värde, till exempel under 0,05, tyder på att skillnaden är verklig.

## Tjänster och verktyg

**GCP (Google Cloud Platform).** Googles molntjänster, som vi har tillgång till.

**Vertex AI.** Den del av GCP där man kan anropa AI-modeller, bland annat Gemini och Claude.

**Model Garden.** En katalog i GCP med öppna modeller som går att köra i vårt eget GCP-projekt.

**GPU.** Grafikprocessor. Den typ av datorkraft som behövs för att träna och köra AI-modeller.

**Hugging Face.** En webbplats där forskare och företag delar dataset och AI-modeller. *Gated* betyder att man måste logga in och godkänna villkor innan man får ladda ner.

**GitHub.** En webbplats där man lagrar och delar kod, och ibland dataset.

**Språkbanken.** En nationell resurs för svenska språkdata, med säte vid Göteborgs universitet. **Korp** är Språkbankens sökverktyg för stora textsamlingar.

**Molnmiljön.** Den utvecklingsmiljö i molnet där arbetet med repot görs. Den släpper bara igenom trafik till vissa webbplatser, vilket begränsar vilka källor som har gått att kontrollera.

**uv.** Ett verktyg som installerar de Python-paket projektet behöver och kör kommandon i projektets miljö.

**pytest.** Ett verktyg som kör projektets automatiska tester.
