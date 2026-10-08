# Forskningsfråga och problemformulering

**Kort sagt:** Vi vill ta reda på hur bra olika datorprogram är på att hitta känsliga uppgifter om personer i svensk fritext. Det gäller särskilt uppgifter som inte sägs rakt ut, utan som går att lista ut av sammanhanget.

Ord som kan vara obekanta förklaras där de dyker upp. Alla begrepp finns också samlade i [ORDLISTA.md](ORDLISTA.md).

## Bakgrund: vad är problemet?

Våra tjänster tar emot fritext, till exempel *underrättelser*, alltså meddelanden som myndigheter och privatpersoner skickar in till oss. Texterna innehåller ofta uppgifter om personer som går att identifiera.

Dataskyddsförordningen GDPR delar in personuppgifter i vanliga och känsliga. De känsliga (artikel 9) skyddas extra hårt:

- hälsa
- etniskt ursprung
- politiska åsikter
- religiös eller filosofisk övertygelse
- medlemskap i fackförening
- sexualliv eller sexuell läggning
- genetiska uppgifter och biometriska uppgifter som används för att identifiera någon

Uppgifter om brott och domar (artikel 10) har egna, stränga regler. I projektet behandlas de som ytterligare en känslig kategori.

För att de system som tar emot texterna ska kunna hantera uppgifterna enligt rätt regler måste vi först veta *att* texten innehåller känsliga uppgifter, *var* de står och *vilken sort* det är.

### Vad dagens verktyg klarar och inte klarar

I dag används två sorters verktyg:

- **Regler**, som letar efter fasta mönster. Ett personnummer har till exempel alltid samma form: sex siffror, ett bindestreck och fyra siffror.
- **NER** (named entity recognition), som automatiskt känner igen namn på personer, platser och organisationer.

De fungerar bra för uppgifter med fast form, som personnummer, e-postadresser och telefonnummer. De missar däremot det som är mest skyddsvärt: de känsliga uppgifterna i listan ovan. Det beror på att de känsliga uppgifterna sällan har en fast form och ofta inte sägs rakt ut.

| Sägs rakt ut (explicit) | Går att lista ut av sammanhanget (implicit) |
|---|---|
| "han är muslim" | "han går i moskén varje fredag" |
| "hon röstar på Vänsterpartiet" | "hon var med och startade lokalavdelningen" |

Den högra kolumnen innehåller inget ord som "muslim" eller "parti" som ett verktyg kan leta efter. Ändå avslöjar meningarna samma sak som de i den vänstra kolumnen.

Det finns dessutom inget gemensamt sätt att mäta hur bra olika metoder är på det här för svensk text. Därför går det inte att jämföra dem på ett rättvist sätt.

## Målet

Undersöka hur väl olika metoder kan hitta, avgränsa och kategorisera känsliga personuppgifter och användbar metadata i ostrukturerad svensk text, så att uppgifterna kan hanteras enligt rätt regler i de system som tar emot texten.

## De tre frågorna vi ska besvara

### 1. Hur bygger vi ett testmaterial?

För att kunna jämföra metoder behövs en *benchmark*: en fast samling testtexter med facit, alltså de rätta svaren, och ett fast sätt att räkna poäng.

Frågan är hur vi tar fram en sådan för svensk text utan att människor behöver läsa och märka upp stora mängder riktiga texter med känsliga uppgifter. Det vill vi undvika eftersom det tar mycket tid, och eftersom fler personer då får läsa känsliga uppgifter om riktiga människor.

Det finns tre alternativ:

- **Syntetisk data:** texter som en AI-modell skriver åt oss, om påhittade personer.
- **Publika texter som liknar våra:** färdiga, öppna textsamlingar som inte är våra egna men påminner om dem.
- **Pseudonymiserade urval:** riktiga texter där namn och andra identifierare har bytts ut mot påhittade.

Hur frågan besvaras står i [PLAN_BENCHMARK.md](PLAN_BENCHMARK.md).

### 2. Hur bra är de olika metoderna?

När testmaterialet finns jämför vi fyra typer av metoder:

- **Regler och regex**, alltså fasta textmönster och ordlistor som någon har skrivit i förväg.
- **Statistiska klassificerare**, enklare maskininlärningsmodeller som lär sig av exempel vilka ord som hör ihop med vilken kategori.
- **Finjusterade svenska encoder-modeller.** Det är mellanstora språkmodeller, till exempel av typen BERT, som vi tränar vidare på våra egna exempel så att de lär sig peka ut känsliga textbitar.
- **Stora språkmodeller (LLM:er)** som Gemini eller Claude. De styrs antingen med skrivna instruktioner (*prompting*) eller tränas vidare på våra exempel (*finjustering*).

Vi mäter hur bra metoderna är för varje kategori för sig, och separat för uppgifter som sägs rakt ut och uppgifter som går att lista ut av sammanhanget.

### 3. Vad kostar de olika metoderna?

Den metod som hittar mest är inte nödvändigtvis den bästa att använda. Vi jämför därför också:

- **Träffsäkerhet:** hur mycket metoden hittar och hur ofta den har rätt.
- **Kostnad:** vad det kostar att köra metoden på alla texter.
- **Svarstid:** hur lång tid metoden tar för varje text.
- **Förklarbarhet:** om det går att förstå varför metoden flaggade en text.
- **Var metoden kan köras:** på våra egna servrar eller hos en extern leverantör.

Den sista punkten är viktig. Att skicka en text med känsliga uppgifter till en extern AI-tjänst är i sig en behandling av personuppgifter enligt GDPR. En metod som kan köras i vår egen miljö kan därför vara att föredra även om den hittar något mindre.

## Avgränsningar och antaganden

**Språk och textsort.** Vi arbetar med svensk text och fokuserar på den sortens texter vi faktiskt får in, som underrättelser.

**Vad metoderna ska göra.** Uppgiften består av tre delar. Ta meningen "Jag skriver om min granne Erik Lund. Han går i moskén varje fredag." som exempel:

1. **Hitta:** finns det något känsligt i texten, och i så fall var? Här: "går i moskén varje fredag".
2. **Kategorisera:** vilken sorts känslig uppgift är det? Här: religion.
3. **Koppla till rätt person:** vem gäller uppgiften? Här: grannen Erik Lund, inte den som skriver. Den här delen är önskvärd men inte ett krav.

**Vad som är viktigast att mäta.** Att missa en känslig uppgift bedöms som värre än att flagga något i onödan. En missad uppgift kan hanteras fel, medan ett falsklarm bara innebär lite extra kontroll. Därför mäts framför allt två saker:

- **Recall (täckning)** för varje känslig kategori: hur stor andel av de känsliga uppgifterna som metoden hittar. Om 10 texter innehåller hälsouppgifter och metoden hittar 8 av dem är recall 0,80. Det här är det viktigaste måttet.
- **Precision (träffsäkerhet):** hur stor andel av det metoden flaggar som verkligen är rätt. Den följs också, eftersom en metod som flaggar allt skulle få full recall men vara oanvändbar i praktiken.
