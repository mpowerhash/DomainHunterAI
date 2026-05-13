# DomainHunterAI

You are acting as a senior full-stack engineer, but keep this MVP simple.

## Goal

Build a lightweight app that helps users discover premium, brandable domains based on custom themes and filters.

This is NOT only for solar.

The user should be able to enter any context, such as:

- Solar help company
- Biology
- Roofing
- AI automation
- Finance
- Health
- Home services

Example user input:

Theme: Biology  
Rules:
- one word
- .com
- 3 syllables or fewer
- under $20,000

The app should generate, filter, score, and display domain ideas.

---

## Important Simplicity Rule

Do NOT overbuild.

Do NOT use:
- Next.js
- React
- Prisma
- Redis
- authentication
- complex backend infrastructure
- multiple services

Use:

- Python
- Streamlit
- pandas
- Selenium for Namecheap
- GoDaddy official API
- live domain availability checks
- live pricing retrieval

This should be a single-page MVP.

This should be a single-page MVP.

---

## Core Features

The app should let the user enter:

- Theme / industry / context
- Tone or style
- TLD, default `.com`
- Max price, default `$20,000`
- Max syllables, default `3`
- Word count, default `1`
- Exact real word vs brandable
- Number of results to generate

---

## App Workflow

When the user clicks "Generate Domains":

1. Read the user's theme and filters.
2. Generate domain candidates.
3. Filter by:
   - TLD
   - syllable count
   - word count
   - max price
   - no numbers
   - no hyphens
4. Estimate/mock pricing.
5. Score each domain.
6. Display a sortable results table.
7. Allow CSV export.

---

## Domain Generation

Use AI if `OPENAI_API_KEY` exists.

If no API key exists, use a mock generator.

The generator should create:
- real one-word names
- brandable names
- short premium-sounding names
- industry-relevant names

Avoid:
- awkward spellings
- names longer than 16 characters
- confusing pronunciation
- hyphens
- numbers

---

## Scoring

Score each domain from 0–100.

Categories:
- memorability
- pronunciation
- industry fit
- premium feel
- shortness
- clarity
- trust
- estimated price value

Each result should include short notes explaining why it scored well or poorly.

---

## Output Table

Show these columns:

- domain
- theme
- tld
- estimated_price
- syllables
- word_count
- type
- score
- notes

Allow sorting/filtering in Streamlit.

---

## CSV Export

Add a button to export results as CSV.

CSV columns should match the table.

---

## Mock Mode

The app must work without any API keys.

If no `OPENAI_API_KEY` exists:
- generate realistic mock domains
- generate realistic mock prices
- generate mock scores
- show a note that mock mode is active

---

## Optional Future APIs
## Optional Future APIs

## Namecheap Integration

Add optional Namecheap integration.

If Namecheap API credentials are provided:

- check domain availability
- check estimated pricing
- prioritize real live data over mock pricing

Use environment variables:

- NAMECHEAP_API_USER
- NAMECHEAP_API_KEY
- NAMECHEAP_USERNAME
- NAMECHEAP_CLIENT_IP

If credentials are missing:
- continue using mock mode automatically

Do not block the app if APIs are unavailable.

For MVP:
- Namecheap integration is optional
- mock mode must always work

Do not build these yet, but structure code so they can be added later:

- GoDaddy availability/pricing
- Namecheap availability/pricing
- domain aftermarket pricing
Do not build these yet, but structure code so they can be added later:

- GoDaddy availability/pricing
- Namecheap availability/pricing
- domain aftermarket pricing
- trademark checks
- daily scans

---

## Files to Create

Create only:

- `app.py`
- `requirements.txt`
- `README.md`
- `.env.example`

Do not create a large project structure yet.

---

## Run Command

The app should run with:

```bash
streamlit run app.py
```
