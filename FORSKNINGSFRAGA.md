# Forskningsfråga och problemformulering

## Övergripande mål

Undersöka hur väl olika metoder kan identifiera, avgränsa och klassificera känslig personinformation och användbar metadata i ostrukturerad svensk text, så att informationen kan hanteras enligt rätt regler i efterföljande system.

## Problemformulering

Våra tjänster tar emot fritext, till exempel underrättelser från myndigheter och privatpersoner. Texterna innehåller ofta uppgifter om identifierbara personer.

Dagens regelbaserade kontroller och NER-lösningar fångar explicita, mönsterbara uppgifter som personnummer, e-post och telefonnummer. De missar däremot det som är mest skyddsvärt: uppgifter som avslöjar en persons religiösa övertygelse, politiska åsikter, hälsa, etniska ursprung, sexuella läggning med mera (GDPR art. 9, och lagöverträdelser enligt art. 10).

Sådana uppgifter uttrycks sällan explicit. De framgår ofta indirekt eller ur sammanhanget, till exempel:

- "han går i moskén varje fredag"
- "hon var med och startade lokalavdelningen"

Det saknas också ett gemensamt sätt att mäta hur bra olika metoder är på detta för svensk text.

## Frågeställningar

1. **Benchmark:** Hur kan vi ta fram ett representativt, annoterat svenskt dataset som gör olika metoder jämförbara, utan att det kräver att vi annoterar riktig känslig produktionsdata i stor skala? Alternativen är syntetisk data, publika proxykorpusar och pseudonymiserade urval.
2. **Metodjämförelse:** Hur presterar olika angreppssätt på det datasetet? Jämförelsen omfattar regler/regex, statistiska klassificerare, finjusterade svenska encoder-modeller (NER/spanklassificering) och LLM:er med prompting eller finjustering. Prestanda mäts per kategori och för explicita respektive implicita uttryck.
3. **Avvägningar:** Vilka avvägningar finns mellan träffsäkerhet, kostnad, latens, förklarbarhet och var modellen kan köras? Det sista är viktigt eftersom det i sig är en personuppgiftsbehandling att skicka känslig text till en extern LLM.

## Avgränsningar och antaganden

- Svensk text, med fokus på domäntypiska texter som underrättelser.
- Uppgiften ses som både **detektion** (finns det något känsligt här, och var?) och **klassificering** (vilken kategori?). Helst ingår även **attribution**, alltså vem uppgiften gäller.
- Missad känslig information bedöms som dyrare än falsklarm. **Recall per känslig kategori** är därför primärt mått, men precision följs så att systemet inte flaggar allt.
