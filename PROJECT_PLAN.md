# DomainHunterAI — Project Spec

## What it is
A Streamlit web app that finds short, brandable, available domain names for any industry.
Live at: https://domainhunterai.streamlit.app
GitHub: https://github.com/mpowerhash/DomainHunterAI

## Status: LIVE (MVP complete)

---

## Tech Stack
- Python + Streamlit (single file: app.py)
- NLTK corpus (~235k words) for dictionary
- wordfreq — frequency-based real word filtering
- WordNet — part of speech detection (frequency-weighted via lemma.count())
- RDAP — domain availability checking (404=Available, 200=Taken)
- GoDaddy API — wired up but returns ACCESS_DENIED (unresolved)
- Namecheap API — wired up, not configured
- OpenAI API — wired up, not yet active (no key)

---

## How to run locally
```bash
cd "c:\Users\ohashai\Documents\Claude\claude code Projects\SolarDomainHunter"
streamlit run app.py
```
Opens at http://localhost:8501

## How to push updates
Double-click push_to_github.bat → type commit message → Streamlit auto-updates in ~60 seconds

---

## Sidebar Controls

| Control | What it does |
|---|---|
| Themes / Industries | Free text, comma-separated (solar, biology, roofing...) |
| TLD | .com / .io / .co / .net / .org |
| Syllables | 1-4, with Exact/Max toggle |
| Max price ($) | Filters by price, default $20,000 |
| Word count | 1 = single word, 2 = compound (solarapex) |
| Available domains only | Only show RDAP-confirmed available |
| Real English words only | ON = dictionary words, OFF = invented/brandable names |
| Part of speech | Filter by Noun / Verb / Adjective / Adverb (exact match) |
| Candidates to generate | How many to find and check (20-500) |
| Letter Starter | Pick a letter — all results start with that letter |
| Combine with theme results | Merge letter results with theme results |

---

## Results Table Columns

| Column | Description |
|---|---|
| Domain | Full domain with TLD |
| Type | Part of speech (Noun/Verb/Adjective/Adverb) |
| Letter ✓ | Whether it starts with chosen letter |
| Real Word | Whether it's a real English word |
| Syllables | Syllable count |
| Availability | Available / Taken / Unknown (via RDAP) |
| Source | Which API confirmed availability |
| Price ($) | $12.99 default for Available .com, None for Taken |
| Score | 0-100 quality score |
| Notes | Why it scored the way it did |
| Market | GoDaddy aftermarket link |

---

## Generation Logic

### Real English words ON
1. Loads NLTK corpus, filters by wordfreq >= 1e-7
2. Scores by theme relevance + frequency
3. Filters by syllable count and POS
4. Checks availability via RDAP

### Real English words OFF (Invented mode)
1. If OpenAI key present → GPT-4o-mini generates creative names (Vanta/Zapier style)
2. Falls back to algorithmic: theme roots + endings/prefixes (solix, voltex, neosol...)
3. All names filtered by syllable setting and letter constraint if active

### Letter Starter
- Pulls all words starting with chosen letter from dictionary
- Pre-filters by real-words, POS, syllable BEFORE sampling
- Uses main "Candidates to generate" count as target
- Shuffle on every run = different words each time

### Availability check order
1. GoDaddy API (broken — ACCESS_DENIED, skipped)
2. Namecheap API (not configured, skipped)
3. RDAP (always runs) — parallel, 10 workers

---

## POS Detection
Uses WordNet with frequency weighting via lemma.count() (Brown corpus frequency).
NOT raw synset count — that gave wrong results (submarine = Verb).
Weighted approach: submarine noun freq ~35 >> verb freq ~3 → correctly returns Noun.

---

## Scoring (0-100)
- Shortness: up to 20 pts
- Syllables: up to 15 pts
- Industry fit: up to 20 pts
- Memorability: up to 15 pts
- Pronunciation: up to 15 pts
- Premium feel: up to 10 pts
- Trust: up to 5 pts
- Price value: up to 5 pts (only when real price known)

---

## Known Issues / Future Work
- GoDaddy API: ACCESS_DENIED — needs account investigation
- OpenAI key: not yet added — would upgrade invented word mode significantly
- Price column: shows estimated reg price ($12.99) for available domains, None for taken
- Secondary market pricing: not implemented (would need Sedo/Afternic API)
- Trademark checks: not implemented
- batch_scan.py: standalone script, scans all 26 letters × syllables 3&4 × 4 POS = 208 combos, outputs domain_matrix.csv

---

## Files
- app.py — entire app (single file)
- batch_scan.py — offline bulk scanner
- push_to_github.bat — one-click deploy
- requirements.txt — pip dependencies
- .env — API keys (local only, never pushed to GitHub)
