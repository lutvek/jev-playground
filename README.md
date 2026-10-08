# jev-playground

Ett projekt där vi testar hur bra olika metoder är på att hitta känsliga uppgifter om personer i svensk fritext.

## Vad handlar det om?

Vi tar emot texter, till exempel underrättelser från myndigheter och privatpersoner, som ofta innehåller uppgifter om personer. Vissa av uppgifterna är extra skyddade enligt dataskyddsförordningen GDPR, till exempel uppgifter om hälsa, religion, politisk åsikt eller brott. För att kunna hantera texterna enligt rätt regler måste vi veta var sådana uppgifter finns.

Dagens verktyg hittar uppgifter med fast form, som personnummer och telefonnummer. De missar ofta de känsliga uppgifterna, eftersom de sällan sägs rakt ut. "Han går i moskén varje fredag" säger något om religion utan att innehålla ordet religion.

Projektet ska ta reda på vilka metoder som klarar det bäst, och vad de kostar. Det första steget är en *benchmark*: en fast samling svenska testtexter med facit, så att olika metoder kan testas på samma sätt och jämföras.

## Läsordning

1. **[FORSKNINGSFRAGA.md](FORSKNINGSFRAGA.md):** problemet, målet och de tre frågor projektet ska besvara.
2. **[PLAN_BENCHMARK.md](PLAN_BENCHMARK.md):** hur testmaterialet tas fram, utan riktiga texter och utan att någon behöver märka upp texter för hand.
3. **[KALLOR.md](KALLOR.md):** vilka färdiga dataset, texter och verktyg som finns, och vilka vi använder.
4. **[ANGREPPSSATT.md](ANGREPPSSATT.md):** vilka sorters metoder som är värda att testa, från regex och ordlistor till Jev, LLM:er och kombinationer av dem.
5. **[benchmark/README.md](benchmark/README.md):** hur man kör koden, hur formatet ser ut, hur poängen räknas och vilka brister datan har.

Begrepp som kan vara obekanta, som *recall*, *spann* och *LLM*, förklaras i **[ORDLISTA.md](ORDLISTA.md)**.

## Läget just nu

- **Klart:** Det första färdiga datasetet, REDACT, är hämtat och omgjort till vårt format. Programmen som kontrollerar formatet och räknar poäng är klara.
- **Pågår:** Programmet som låter en AI skriva egna testtexter finns och har provkörts. Det behövs för uppgifter som inte sägs rakt ut, eftersom inget färdigt dataset innehåller sådana.
- **Nästa steg:** Låta en andra AI-modell granska texterna, byta platshållarna mot riktiga namn och testpersonnummer, och sedan skriva alla texter.

## Kom igång med koden

Koden är skriven i Python och använder verktyget [uv](https://docs.astral.sh/uv/). Så här kör man testerna:

```
uv sync
uv run pytest
```

Fler kommandon, och vad de gör, står i [benchmark/README.md](benchmark/README.md#kom-igång).
