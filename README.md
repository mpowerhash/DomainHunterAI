# DomainHunterAI

Find short, brandable, available domains for any industry — scored and availability-checked.

**Live app:** https://domainhunterai.streamlit.app

---

## What it does

Enter a theme (solar, biology, roofing, AI, finance...), set your filters, and get a scored list of domain candidates with live availability checking via RDAP.

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501

---

## Push updates

Double-click `push_to_github.bat` → type what you changed → Streamlit updates in ~60 seconds.

---

## Filters

| Filter | Default | Options |
|---|---|---|
| Theme | solar energy | Any text, comma-separated |
| TLD | .com | .com .io .co .net .org |
| Syllables | 2 | 1-4, exact or max |
| Max price | $20,000 | Any amount |
| Word count | 1 | 1 (single) or 2 (compound) |
| Available only | ON | Toggle |
| Real English words only | ON | Toggle — OFF = invented/brandable |
| Part of speech | All | Noun / Verb / Adjective / Adverb |
| Candidates | 100 | 20-500 slider |
| Letter Starter | OFF | Pick any letter A-Z |

---

## API Keys (.env)

```
GODADDY_API_KEY=       # wired up, currently blocked
GODADDY_API_SECRET=
OPENAI_API_KEY=        # optional — upgrades invented word mode to AI generation
NAMECHEAP_API_USER=    # optional
NAMECHEAP_API_KEY=
NAMECHEAP_USERNAME=
NAMECHEAP_CLIENT_IP=
```

App works without any keys. RDAP availability checking is always active.

---

## Legal

Domain suggestions are generated automatically and are not legal advice.
Always run a trademark search before purchasing any domain.
