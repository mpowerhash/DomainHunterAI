# DomainHunterAI

Find short, brandable domains for any industry — fast.

Enter a theme (solar, biology, roofing, AI, finance, health…), set your filters, and get a scored list of domain ideas with CSV export.

---

## Quick Start

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Run the app**

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501` in your browser.

---

## Mock Mode (no API keys needed)

The app runs fully without any API keys.

In mock mode:
- Domain candidates are generated from a built-in themed word bank
- Prices are realistic estimates (not live data)
- Scoring uses a rule-based engine
- A blue banner at the top confirms mock mode is active

---

## Optional: Add API Keys

Copy `.env.example` to `.env` and fill in the keys you have.

```bash
cp .env.example .env
```

### OpenAI (enables AI domain generation)

```
OPENAI_API_KEY=sk-...
```

When set, the app sends your theme and filters to `gpt-4o-mini` to generate smarter, more creative domain ideas.

### Namecheap (enables live availability checks)

```
NAMECHEAP_API_USER=your_username
NAMECHEAP_API_KEY=your_api_key
NAMECHEAP_USERNAME=your_username
NAMECHEAP_CLIENT_IP=your_whitelisted_ip
```

When all four vars are set, the app checks real-time domain availability via the Namecheap API. Pricing remains estimated for MVP.

To get Namecheap API access: log in to Namecheap → Profile → Tools → API Access.

---

## Filters

| Filter | Default | Description |
|---|---|---|
| Theme / Industry | solar energy | Free text: biology, roofing, AI, finance… |
| Tone or style | premium, trustworthy | Guides AI generation |
| TLD | .com | .com / .io / .co / .net / .org |
| Max price | $20,000 | Filters out expensive domains |
| Max syllables | 3 | 1–5 |
| Domain type | any | real word / brandable / any |
| Results | 20 | 5–50 |

---

## Output Table

| Column | Description |
|---|---|
| domain | Full domain name with TLD |
| theme | Theme you searched |
| tld | Top-level domain |
| estimated_price | Mock or live price in USD |
| syllables | Syllable count |
| word_count | Number of words |
| type | real word / brandable / any |
| score | 0–100 quality score |
| notes | Short explanation of score |
| source | mock / openai / namecheap |

Rows are color-coded by score (green = high, red = low).

---

## CSV Export

Click **Export CSV** after generating results to download the table as a `.csv` file.

---

## Legal Disclaimer

Domain suggestions are generated automatically and are not legal advice.
Always run a full trademark search before purchasing any domain.
This tool does not check trademark databases (USPTO, WIPO).

---

## Future Additions (not built yet)

- GoDaddy API integration
- Aftermarket domain pricing
- Trademark risk flags
- Daily automated scans
