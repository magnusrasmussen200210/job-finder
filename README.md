# Job Finder

Tjekker Jobindex, Jobnet og LinkedIn hver time (GitHub Actions) for nye job inden for ca. en times kørsel fra Aarhus C, som Magnus realistisk kan få: junior økonomi/controlling, analytiker, BI, planner, indkøb, barselsvikariater og andre tidsbegrænsede stillinger. Relevante job sendes på Telegram med titel, by, fuldtid/deltid og om stillingen er tidsbegrænset.

## Sådan sorteres der
1. Søgeordene står i `finder/config.py` (`QUERIES_DA`, `QUERIES_LINKEDIN`).
2. Titlen skal handle om økonomi, tal eller analyse, og må ikke være senior, ledelse, studiejob, praktik eller butik.
3. Stedet skal ligge i de postnumre, der står i `ALLOWED_POSTCODES` (Østjylland, Midtjylland, Vejle, Fredericia, Herning, Hobro).
4. Opslag, der kræver 3+ års erfaring, frasorteres.
5. Hvis secret'en `ANTHROPIC_API_KEY` findes, læser Claude Haiku hvert opslag og giver en score fra 1 til 10. Job under 6 sendes ikke.

Kun job fra de sidste 7 dage hentes, og hvert job sendes én gang (`state/seen.json`).

## Secrets (Settings → Secrets and variables → Actions)
| Navn | Indhold |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token fra @BotFather |
| `TELEGRAM_CHAT_ID` | Valgfri. Findes automatisk ud fra den seneste besked til botten |
| `ANTHROPIC_API_KEY` | Valgfri. Slår LLM-vurderingen til (ca. 5 kr./md. med Haiku) |

## Kør manuelt
Actions → "Tjek job" → Run workflow. Sæt "dry run" for kun at se loggen uden at sende noget.

`tools/probe.py` (workflow "Probe (debug)") henter vilkårlige sider og gemmer HTML og JSON-kald på en `probe-out-*`-branch, så nye jobsites kan tilføjes.
