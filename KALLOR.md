# Källor för benchmark-datasetet

Inventering gjord 2026-10-08 med sökningar på Hugging Face, Språkbanken, svenska myndigheters öppna data, GitHub och forskningslitteratur. Hör ihop med [PLAN_BENCHMARK.md](PLAN_BENCHMARK.md).

**Verifieringsnivå:**

- **[V]** Vi har laddat ner data och räknat själva.
- **[D]** Kontrollerat mot dokumentation eller kod på GitHub.
- **[S]** Bara sett i sökmotorutdrag. Måste kontrolleras innan användning.

Molnmiljön där sökningen gjordes blockerade huggingface.co, spraakbanken.gu.se, domstol.se, jo.se, skatteverket.se, scb.se med flera. Bara GitHub gick att nå. Därför är flera Hugging Face-dataset och svenska källor bara verifierade på nivå [S] eller [D].

## Slutsatser

1. **Det finns inget svenskt dataset med riktig text och art. 9-annotering.** Inte på Hugging Face, inte hos Språkbanken och inte i publicerad forskning.
2. **Det finns inget dataset, på något språk, som annoterar implicita art. 9-uttryck om identifierbara personer.** Det närmaste är SynthPAI, som har implicita attribut men inte art. 9-kategorier. Den implicita dimensionen måste vi bygga själva.
3. **Två LLM-genererade flerspråkiga dataset har svensk text med art. 9- och art. 10-etiketter:** REDACT (verifierat) och PrivoNest (overifierat). Båda innehåller nästan bara explicita uttryck.
4. **Fackmedlemskap, lagöverträdelser och genetiska/biometriska uppgifter är tunnast överallt.** Etniskt ursprung finns bara i PrivoNest och engelska TAB.
5. **"SEX" betyder kön** i både TAB och SynthPAI, inte sexualliv eller sexuell läggning.
6. **Bästa källan till riktig svensk text är Domstolsverkets öppna API för rättspraxis.** Migrationsmål innehåller ofta religion, sexuell läggning, etniskt ursprung och politisk åsikt, ofta implicit. Arbetsdomstolen ger fackmedlemskap.

## Används i PoC:n

| Källa | Vad | Licens och åtkomst | Användning | Nivå |
|---|---|---|---|---|
| **REDACT**, svenska delen<br>[GitHub](https://github.com/guneeshvats/REDACT-PII-Benchmark), [HF](https://huggingface.co/datasets/guneeshv/REDACT-PII-Benchmark) (gated) | 561 svenska LLM-genererade dokument (e-post, ärendeanteckningar, chatt) i bland annat myndighetsdomäner. 157 dokument har art. 9/10-spann: hälsa 192, brott 82, sjukskrivning 74, allergi 52, fack 38, religion 15, parti 15, sexuell läggning 7. 364 personnummer. | Egna "REDACT Dataset Terms": forskning och benchmarking tillåts med attribution, profilering och återidentifiering förbjuds. Koden är MIT. | Extern kontroll av explicita uttryck och identifierare. | [V] |
| **PrivoNest**, svenska delen<br>[HF](https://huggingface.co/datasets/abbasrazalagha/PrivoNest_Multilingual_Privacy_Dataset) | Enligt kortet 8 545 svenska rader (6 968 train, 391 val, 1 186 test) med 88 etiketter, bland annat alla art. 9-kategorier och `CRIMINAL_RECORD`. | Apache-2.0 enligt kortet. | Om ett stickprov håller måttet: extra testdata och träningsdata för encoder-modeller. En enskild uppladdare och okänd genereringsmetod, och vi har inte sett några rader. | [S] |

## Användbart om projektet växer (kräver annotering)

Riktig svensk text, men utan etiketter. Utanför PoC:n eftersom vi inte annoterar.

| Källa | Vad | Licens och åtkomst | Användning | Nivå |
|---|---|---|---|---|
| **Domstolsverkets Rättspraxis-API**<br>`https://rattspraxis.etjanst.domstol.se/api/v1` | Avgöranden från HD, HFD, hovrätter, kammarrätter, Arbetsdomstolen och Migrationsöverdomstolen. Hela avgöranden som PDF sedan mars 2025, referat sedan 1981. Parter anges med initialer. | Öppna data, ingen inloggning. | Utdrag som vi annoterar själva: riktigt språk. Migrationsmål ger religion, sexuell läggning, etniskt ursprung och politik. Arbetsdomstolen ger fack. Kammarrätternas LVU/LVM-mål ger hälsa. Hovrätterna ger brott. | [D] |
| **JO-beslut**<br>[jo.se](https://www.jo.se/jo-beslut/sokresultat/) | Beslut om klagomål på myndigheter, ofta socialtjänst, polis och psykiatri. Ingen bulknedladdning, en PDF per beslut. Lagen.nu-motorn [ferenda](https://github.com/staffanm/ferenda) har kod som hämtar dem. | Allmänna handlingar. | Utdrag att annotera. Närmast myndighetsgenren. | [D] |
| **Flashback och Familjeliv** via Språkbanken/Korp | Mycket stora forumkorpusar, till exempel Familjeliv "Känsliga rummet" och Flashback "Droger" och "Sex". | CC BY 4.0. **Nedladdningarna har omkastade meningar och Korp visar bara en mening som sammanhang.** | En separat meningsnivåsamling med informella, ofta implicita uttryck och svåra negativa exempel. Inga användarnamn sparas. | [S]/[D] |

## Mallar för schema och metod

| Källa | Vad vi tar från den | Nivå |
|---|---|---|
| **TAB** (Text Anonymization Benchmark)<br>[GitHub](https://github.com/NorskRegnesentral/text-anonymization-benchmark), MIT | Annoteringsschemat: direkta och indirekta identifierare, känsliga attribut (`HEALTH`, `POLITICS`, `ETHNIC`, `BELIEF`, `SEX`) på spann, samt koreferens. Fackmedlemskap ingår i `POLITICS`. Lagöverträdelser saknas. | [V] |
| **W3C DPV-PD**<br>[GitHub](https://github.com/w3c/dpv) | Taxonomi med klasser för alla art. 9-kategorier och för lagöverträdelser. Används för kategoridefinitionerna. | [V] |
| **SynthPAI**<br>[GitHub](https://github.com/eth-sri/SynthPAI) | Svårighetsskala 1–5 för implicita uttryck och en metod för att generera text från fiktiva profiler. Har inga art. 9-kategorier. Licensen är MIT på GitHub men uppges vara CC BY-NC-SA på HF. | [V] |
| **ConfAIde**, **PrivacyLens** | Recept för att generera berättelser om namngivna personer med känsliga uppgifter. | [V] |
| **SweLL / Mormor Karl** (Språkbanken) | Svensk tagguppsättning för pseudonymisering av identifierare. Själva datan delas inte. | [D] |

## Byggstenar för syntetisk data

| Källa | Vad | Nivå |
|---|---|---|
| **Skatteverkets testpersonnummer**<br>API: `https://skatteverket.entryscape.net/rowstore/dataset/b4de7df7-63c0-4e7e-bb59-1f156a591763` | Cirka 40 000 personnummer som aldrig delas ut till riktiga personer. Får användas för test. | [D] |
| **Svenska namn med frekvenser**<br>[svensktext/namn](https://github.com/peterdalle/svensktext/tree/master/namn) | Förnamn och efternamn från SCB (2020) med antal bärare. Repot saknar licensfil. SND 2021-272 har namn per födelseland (CC BY 4.0). | [D] |
| **swedish-personas**<br>[HF](https://huggingface.co/datasets/birgermoell/swedish-personas) | 100 000 syntetiska personer, samplade från SCB-statistik. CC BY 4.0. Kan användas som frö för scenariospecar. | [S] |
| **Fiktiva identifierare**<br>[maskera TEST_DATA.md](https://github.com/joelhagvall/maskera/blob/main/docs/TEST_DATA.md) | Lista över telefonnummer reserverade för fiktion, exempeladresser, testkonton med mera. | [D] |

## Baslinjer för metodjämförelsen

Detta är verktyg och modeller, inte dataset. De är relevanta för frågeställning 2.

| Verktyg/modell | Vad | Nivå |
|---|---|---|
| [okasi/swedish-pii](https://github.com/okasi/swedish-pii) | Svenska lexikonbaserade detektorer, bland annat för religion, politisk ideologi, fack och sexuell läggning. MIT. Bra regelbaserad baslinje för explicita uttryck. | [V] |
| [sparv-sbx-pi-detection](https://github.com/spraakbanken/sparv-sbx-pi-detection) | Språkbankens KB-BERT-modeller för identifierare. Enligt README sämre utanför sin domän. | [D] |
| KB/bert-base-swedish-cased-ner, joelhagvall/maskera-sv-ner | Svensk NER för namn, platser och organisationer. | [S] |
| tabularisai/eu-pii-safeguard, bardsai/eu-pii-anonimization-multilang | Flerspråkiga PII-modeller. Den senare uppger att den har art. 9-klasser. | [S] |

## Undersökta men inte användbara nu

- **Stockholm EPR PHI-korpusen** (kliniska journaler): bara för forskare vid SU med etikprövning.
- **SweLL-gold**: kräver ansökan och har bara en samlad etikett `sensitive`.
- **i2b2/n2c2 2014**: engelska och bara identifierare, kräver avtal.
- **Gretel finance multilingual** och äldre **ai4privacy**-versioner: ingen (säker) svenska, bara identifierare.
- **BiaSWE**, svenska hatdatasets och **Riksdagens öppna data**: handlar om grupper eller offentliga personer. Kan ge svåra negativa exempel men inte positiva.
- **SPeDaC**: kräver avtal med författarna.
- **SUC 3.0/SUCX, swedish_ner_corpus, wikiann, MAPA**: bara namn, platser och organisationer.
- **swelaw** (HF): rå juridisk text där namnen mestadels är borttagna. Rättspraxis-API:et ger samma sak med bättre metadata.

## Relaterat arbete att läsa

- Pilán m.fl. 2022, TAB, *Computational Linguistics*.
- Szawerna m.fl. 2024–2025 (Språkbanken): PII-detektion i svenska elevtexter.
- arXiv 2507.10582: anonymisering av 10 842 svenska LVM-domar med LLM. Datan delas bara med etikprövade forskare.
- Examensarbete vid Mittuniversitetet, "Identifying Sensitive Data using NER with LLMs" (diva2:1876988). Innehållet har vi inte kontrollerat.
