# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import random
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment — reads Streamlit secrets (cloud) then .env (local)
# ---------------------------------------------------------------------------

def _env(key: str):
    """Works both on Streamlit Cloud (st.secrets) and locally (.env)."""
    try:
        v = st.secrets.get(key)
        if v:
            return v
    except Exception:
        pass
    return os.getenv(key)

OPENAI_API_KEY      = _env("OPENAI_API_KEY")
GODADDY_API_KEY     = _env("GODADDY_API_KEY")
GODADDY_API_SECRET  = _env("GODADDY_API_SECRET")
NAMECHEAP_API_USER  = _env("NAMECHEAP_API_USER")
NAMECHEAP_API_KEY   = _env("NAMECHEAP_API_KEY")
NAMECHEAP_USERNAME  = _env("NAMECHEAP_USERNAME")
NAMECHEAP_CLIENT_IP = _env("NAMECHEAP_CLIENT_IP")

USE_OPENAI    = bool(OPENAI_API_KEY)
USE_GODADDY   = all([GODADDY_API_KEY, GODADDY_API_SECRET])
USE_NAMECHEAP = all([NAMECHEAP_API_USER, NAMECHEAP_API_KEY, NAMECHEAP_USERNAME, NAMECHEAP_CLIENT_IP])

# ---------------------------------------------------------------------------
# Word banks — seed words for theme relevance scoring
# ---------------------------------------------------------------------------

THEME_WORDS = {
    "solar":    ["sol","sun","helio","lumen","volt","beam","glow","nova","flare","ray","lux","dawn","bright","arc"],
    "biology":  ["cell","gene","flora","fauna","vita","morph","spore","stem","bloom","seed","bion","zoe"],
    "roofing":  ["apex","shield","peak","ridge","slate","span","dome","cap","crest","cover"],
    "ai":       ["axon","synth","logic","core","node","flux","nova","arc","mind","vex"],
    "finance":  ["vault","prime","merit","nexus","yield","asset","forte","capita","apex","crest"],
    "health":   ["vital","zenith","bloom","pulse","vigor","vive","mend","thrive","salus"],
    "home":     ["haven","nest","hearth","grove","vista","crest","lodge","abode","nook"],
    "energy":   ["volt","watt","grid","spark","surge","flux","amp","joule","kilo","ohm"],
    "default":  ["apex","nova","core","prime","nexus","forte","zen","flux","arc","crest","sol","lux"],
}

BRANDABLE_SUFFIXES = ["ify","ly","io","hub","co","ai","ex","ix","on","ow"]
BRANDABLE_PREFIXES = ["my","go","be","up","in","ez"]

SUFFIXES_BY_TYPE = {
    "Nouns":      ["ness","ment","tion","ation","er","or","ist","ism","ity","ance","ence","ship","hood","ling"],
    "Adjectives": ["al","ic","ous","ful","less","y","ing","ive","able","ible","ant","ent","en","ish"],
    "Adverbs":    ["ly","ily","ally","ically","ward","wise"],
    "Verbs":      ["ize","ise","ify","en","ate"],
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def count_syllables(word: str) -> int:
    word = word.lower().strip()
    vowels = "aeiouy"
    count, prev_vowel = 0, False
    for ch in word:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def is_valid_candidate(name: str, syllables: int, syl_exact: bool = True, max_words: int = 1) -> bool:
    if not name or len(name) < 2 or len(name) > 16:
        return False
    if any(c.isdigit() for c in name) or "-" in name:
        return False
    if max_words == 1:  # syllable constraint only applies to single-word domains
        n = count_syllables(name)
        if syl_exact and n != syllables:
            return False
        if not syl_exact and n > syllables:
            return False
    return True


def get_theme_key(theme: str) -> str:
    tl = theme.lower()
    for key in THEME_WORDS:
        if key in tl or tl in key:
            return key
    return "default"


def is_real_english_word(word: str, min_freq: float = 1e-6) -> bool:
    from wordfreq import word_frequency
    return word_frequency(word.lower(), "en") >= min_freq


def get_pos(word: str) -> str:
    """
    Returns primary part of speech via WordNet: Noun, Verb, Adjective, Adverb, or —.

    Weights by corpus frequency (lemma.count()) rather than raw synset count.
    Raw count gives wrong results for words like 'submarine' that have equal noun/verb
    synsets but are overwhelmingly used as nouns in practice.
    """
    _ensure_nlp_data()
    from nltk.corpus import wordnet as wn
    synsets = wn.synsets(word.lower())
    if not synsets:
        return "—"
    counts = {}
    for syn in synsets:
        # Sum corpus frequency across all lemmas in this synset.
        # lemma.count() = how often this sense appeared in the Brown corpus.
        # Fall back to 1 so zero-count senses still contribute a small weight.
        freq = sum(lemma.count() for lemma in syn.lemmas()) or 1
        counts[syn.pos()] = counts.get(syn.pos(), 0) + freq
    primary = max(counts, key=counts.get)
    return {"n": "Noun", "v": "Verb", "a": "Adjective", "s": "Adjective", "r": "Adverb"}.get(primary, "—")

# ---------------------------------------------------------------------------
# NLP corpus setup
# ---------------------------------------------------------------------------

def _ensure_nlp_data():
    import nltk
    for corpus, path in [("wordnet","corpora/wordnet"),
                         ("omw-1.4","corpora/omw-1.4"),
                         ("words","corpora/words")]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(corpus, quiet=True)

# ---------------------------------------------------------------------------
# Dictionary pool — full NLTK English words, scored by theme + frequency
# ---------------------------------------------------------------------------

def _theme_relevance_set(themes: list) -> set:
    _ensure_nlp_data()
    from nltk.corpus import wordnet as wn
    relevant = set()
    for theme in themes:
        for word in theme.lower().split():
            for syn in wn.synsets(word):
                for lemma in syn.lemmas():
                    n = lemma.name().lower().replace("_","")
                    if n.isalpha(): relevant.add(n)
                    for d in lemma.derivationally_related_forms():
                        n = d.name().lower().replace("_","")
                        if n.isalpha(): relevant.add(n)
                for hypo in syn.hyponyms()[:5]:
                    for lemma in hypo.lemmas():
                        n = lemma.name().lower().replace("_","")
                        if n.isalpha(): relevant.add(n)
                for hyper in syn.hypernyms()[:3]:
                    for lemma in hyper.lemmas():
                        n = lemma.name().lower().replace("_","")
                        if n.isalpha(): relevant.add(n)
    return relevant


@st.cache_data(show_spinner="Building dictionary pool…")
def build_dictionary_pool(theme_tuple: tuple, max_syllables: int) -> list:
    """
    Full NLTK corpus filtered to UP TO max_syllables, scored by theme proximity.
    Cached per (themes, max_syllables). Exact/max filtering happens downstream.
    """
    _ensure_nlp_data()
    from nltk.corpus import words as nltk_words
    from wordfreq import word_frequency

    themes     = list(theme_tuple)
    theme_set  = _theme_relevance_set(themes)
    for t in themes:
        theme_set.update(THEME_WORDS.get(get_theme_key(t), []))

    all_words = set(w.lower() for w in nltk_words.words("en"))
    scored = []
    for word in all_words:
        if not word.isalpha() or not (2 <= len(word) <= 12):
            continue
        if count_syllables(word) > max_syllables:
            continue
        freq = word_frequency(word, "en")
        if freq < 1e-7:
            continue
        rel   = 3 if word in theme_set else 0
        score = rel + min(freq * 1_000_000, 3)
        scored.append((word, score))

    scored.sort(key=lambda x: -x[1])
    return [w for w, _ in scored]

# ---------------------------------------------------------------------------
# Word variations (WordNet + suffix rules)
# ---------------------------------------------------------------------------

def _ensure_wordnet():
    _ensure_nlp_data()


def generate_word_variations(base_words: list, variation_types: list) -> list:
    from wordfreq import word_frequency
    _ensure_wordnet()
    from nltk.corpus import wordnet as wn

    POS_MAP = {"Nouns": wn.NOUN, "Adjectives": wn.ADJ,
               "Adverbs": wn.ADV, "Verbs": wn.VERB}
    candidates  = set()
    base_set    = set(w.lower() for w in base_words)
    target_pos  = [POS_MAP[t] for t in variation_types if t in POS_MAP]

    for word in base_words:
        word = word.lower()
        for pos_type in variation_types:
            for suffix in SUFFIXES_BY_TYPE.get(pos_type, []):
                candidates.add(word + suffix)
                if word.endswith("e") and suffix[0] in "aeiou":
                    candidates.add(word[:-1] + suffix)
                if word.endswith("y") and not suffix.startswith("y"):
                    candidates.add(word[:-1] + "i" + suffix)
                if (len(word) >= 3 and word[-1] not in "aeiouylrwh"
                        and word[-2] in "aeiou" and word[-3] not in "aeiou"):
                    candidates.add(word + word[-1] + suffix)
                if pos_type == "Adverbs" and suffix == "ly" and word.endswith("ic"):
                    candidates.add(word + "ally")

        for syn in wn.synsets(word):
            for lemma in syn.lemmas():
                for derived in lemma.derivationally_related_forms():
                    if not target_pos or derived.synset().pos() in target_pos:
                        candidates.add(derived.name().replace("_","").lower())
                if not target_pos or syn.pos() in target_pos:
                    candidates.add(lemma.name().replace("_","").lower())

    return [v for v in candidates
            if v not in base_set and " " not in v and "-" not in v
            and len(v) <= 16 and not any(c.isdigit() for c in v)
            and word_frequency(v, "en") >= 1e-7]

# ---------------------------------------------------------------------------
# Brandable fill — invented names when real_words_only is OFF and pool runs short
# ---------------------------------------------------------------------------

def _generate_brandable_fill(themes: list, syllables: int, syl_exact: bool,
                               count: int, exclude: set,
                               extra_roots: list = None,
                               start_letter: str = None) -> list:
    """
    Return up to `count` invented brandable names that pass the syllable filter.
    - extra_roots: short dict words to use as roots alongside theme seeds
    - start_letter: when set, ALL returned names begin with this letter
    """
    theme_key = get_theme_key(themes[0] if themes else "default")
    seed      = list(THEME_WORDS.get(theme_key, THEME_WORDS["default"]))
    all_roots = list({r for r in seed + (extra_roots or []) if 2 <= len(r) <= 6})

    endings  = ["ix", "ex", "on", "en", "ax", "ar", "or", "ia", "eo", "io",
                "yx", "rix", "nex", "vex", "max", "pex", "tex", "ux", "ev", "an"]
    prefixes = ["neo", "pro", "uni", "lux", "sol", "max", "pri", "axi",
                "omni", "vex", "rex", "hex", "nex", "ziv"]

    letter = start_letter.lower() if start_letter else None

    def _ok(name: str) -> bool:
        if letter and not name.startswith(letter):
            return False
        return name not in seen and is_valid_candidate(name, syllables, syl_exact, 1)

    seen = set(exclude)
    candidates = []

    # root + ending
    for root in all_roots:
        for end in endings:
            name = (root + end).lower()
            if _ok(name):
                seen.add(name); candidates.append(name)

    # prefix + root
    for pre in prefixes:
        for root in all_roots:
            name = (pre + root).lower()
            if _ok(name):
                seen.add(name); candidates.append(name)

    # short root + short root
    short_roots = [r for r in all_roots if len(r) <= 4]
    for r1 in short_roots:
        for r2 in short_roots:
            if r1 != r2:
                name = (r1 + r2).lower()
                if _ok(name):
                    seen.add(name); candidates.append(name)

    # When a letter constraint is active, also try letter + root and letter + ending combos
    # so we generate enough names even if few roots start with that letter naturally
    if letter:
        for root in all_roots:
            name = (letter + root).lower()
            if _ok(name):
                seen.add(name); candidates.append(name)
        for end in endings:
            for root in all_roots:
                name = (letter + end + root).lower()
                if _ok(name):
                    seen.add(name); candidates.append(name)

    random.shuffle(candidates)
    return candidates[:count]


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def score_domain(name: str, theme: str, price=None) -> tuple:
    score, notes = 0, []
    length       = len(name)
    syllables    = count_syllables(name)
    name_lower   = name.lower()

    # Shortness (0-20)
    if length <= 5:   score += 20; notes.append("very short")
    elif length <= 8: score += 15; notes.append("short")
    elif length <= 11: score += 8
    elif length <= 14: score += 4
    else: notes.append("long")

    # Syllables (0-15)
    if syllables == 1:   score += 15; notes.append("1 syllable")
    elif syllables == 2: score += 10
    elif syllables == 3: score += 5

    # Industry fit (0-20)
    theme_words = THEME_WORDS.get(get_theme_key(theme), THEME_WORDS["default"])
    if any(w in name_lower for w in theme_words):
        score += 20; notes.append("industry fit")
    elif any(w in name_lower for w in theme.lower().split()):
        score += 12; notes.append("theme match")
    else:
        score += 4

    # Memorability (0-15)
    if length <= 7 and name_lower[-1] in "aeiou":
        score += 15; notes.append("memorable")
    elif length <= 10: score += 8
    else:              score += 3

    # Pronunciation (0-15)
    awkward = ["xz","qv","bq","vk","jx","zw","kq"]
    if any(a in name_lower for a in awkward): notes.append("hard to pronounce")
    elif length <= 8: score += 15; notes.append("easy to say")
    else:             score += 7

    # Premium feel (0-10)
    premium_ends = ["ex","ix","on","en","ar","or","an","ax"]
    if any(name_lower.endswith(e) for e in premium_ends):
        score += 10; notes.append("premium feel")
    elif length <= 6: score += 7
    else:             score += 3

    # Trust (0-5)
    odd = set("xzq")
    if not (set(name_lower) & odd) and length <= 10: score += 5
    elif length <= 8:                                 score += 3

    # Price value (0-5) — only when real price is known
    if price is not None:
        if price <= 20:     score += 5; notes.append("reg price")
        elif price <= 1000: score += 4
        elif price <= 5000: score += 3
        elif price <= 10000: score += 2
        elif price <= 20000: score += 1

    return min(100, score), ", ".join(notes) if notes else "good domain"

# ---------------------------------------------------------------------------
# Candidate generator
# ---------------------------------------------------------------------------

def generate_candidates(themes, tld: str, syllables: int, syl_exact: bool, count: int,
                        max_words: int = 1, variation_types: list = None) -> list:
    if isinstance(themes, str):
        themes = [t.strip() for t in themes.split(",") if t.strip()]
    if not themes:
        themes = ["general"]
    display_theme = ", ".join(themes)

    # For 2-word compounds use a broader syllable pool; single-word respects exact setting
    pool_syl = syllables if max_words == 1 else 4
    pool     = build_dictionary_pool(tuple(sorted(themes)), pool_syl)

    # Generate 4x the requested count so downstream filters (real-words, POS, availability)
    # still leave roughly `count` results to display
    target = min(count * 4, 2000)

    if max_words == 2:
        # Two-word compound domains: join word1 + word2 (no space, no hyphen)
        short = [w for w in pool if 3 <= len(w) <= 7]
        random.shuffle(short)
        compound_seen = set()
        compound_pool = []
        limit = target * 3
        for i, w1 in enumerate(short):
            for w2 in short[i + 1:]:
                compound = w1 + w2
                if 6 <= len(compound) <= 14 and compound not in compound_seen:
                    compound_seen.add(compound)
                    compound_pool.append(compound)
                    if len(compound_pool) >= limit:
                        break
            if len(compound_pool) >= limit:
                break
        all_candidates = compound_pool
    else:
        seed_words = pool[:200]
        extra = []
        for w in seed_words:
            for s in BRANDABLE_SUFFIXES:
                extra.append(w + s)
        for p in BRANDABLE_PREFIXES:
            for w in seed_words[:50]:
                extra.append(p + w)
        short = [w for w in seed_words if len(w) <= 5][:60]
        for i, w1 in enumerate(short):
            for w2 in short[i + 1:]:
                if len(w1 + w2) <= 12:
                    extra += [w1 + w2, w2 + w1]
        all_candidates = pool + extra

    seen, valid = set(), []
    for name in all_candidates:
        name = name.lower()
        if name not in seen and is_valid_candidate(name, syllables, syl_exact, max_words):
            seen.add(name)
            valid.append(name)
            if len(valid) >= target:
                break

    results = []
    for name in valid:
        best = themes[0]
        for t in themes:
            if any(w in name for w in THEME_WORDS.get(get_theme_key(t), [])):
                best = t; break
        sc, notes = score_domain(name, best)
        results.append({
            "domain":       f"{name}.{tld.lstrip('.')}",
            "theme":        display_theme,
            "tld":          f".{tld.lstrip('.')}",
            "registrar":    "—",
            "price":        None,
            "availability": "Unknown",
            "syllables":    count_syllables(name),
            "word_count":   max_words,
            "score":        sc,
            "notes":        notes,
        })
    results.sort(key=lambda x: -x["score"])
    return results

# ---------------------------------------------------------------------------
# GoDaddy — availability + pricing
# Requires account with >10 active domains. Falls back silently otherwise.
# ---------------------------------------------------------------------------

def check_godaddy(domains: list) -> dict:
    """
    Returns {domain: {"available": bool, "price": float|None}}.
    Probes first domain to catch account-level 403 before parallelizing.
    Empty dict if credentials missing, 403, or all checks fail → caller falls through to WHOIS.
    """
    if not USE_GODADDY:
        return {}
    import requests

    headers = {
        "Authorization": f"sso-key {GODADDY_API_KEY}:{GODADDY_API_SECRET}",
        "Accept":        "application/json",
    }

    def _parse(data: dict) -> dict:
        available = data.get("available", False)
        raw_price = data.get("price")
        price     = round(raw_price / 1_000_000, 2) if raw_price and available else None
        return {
            "availability": "Available" if available else "Taken",
            "price":        price,
            "registrar":    "godaddy",
        }

    # Probe the first domain — if 403, bail immediately rather than hammering all domains
    try:
        probe = requests.get(
            "https://api.godaddy.com/v1/domains/available",
            headers=headers,
            params={"domain": domains[0], "checkType": "FAST"},
            timeout=10,
        )
        if probe.status_code == 403:
            try:
                detail = probe.json()
            except Exception:
                detail = probe.text
            st.warning(f"GoDaddy 403 — {detail}. Switching to WHOIS.")
            return {}
        probe.raise_for_status()
    except Exception as e:
        st.warning(f"GoDaddy: connection failed ({e}). Switching to WHOIS.")
        return {}

    results   = {domains[0]: _parse(probe.json())}
    remaining = domains[1:]
    if not remaining:
        return results

    def _check(domain: str):
        try:
            r = requests.get(
                "https://api.godaddy.com/v1/domains/available",
                headers=headers,
                params={"domain": domain, "checkType": "FAST"},
                timeout=10,
            )
            if r.status_code != 200:
                return domain, None
            return domain, _parse(r.json())
        except Exception:
            return domain, None

    completed = 1
    bar       = st.progress(completed / len(domains),
                            text=f"GoDaddy: {completed}/{len(domains)} checked…")

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_check, d): d for d in remaining}
        for future in as_completed(futures):
            domain, result = future.result()
            if result is not None:
                results[domain] = result
            completed += 1
            bar.progress(completed / len(domains),
                         text=f"GoDaddy: {completed}/{len(domains)} checked…")
    bar.empty()
    return results

# ---------------------------------------------------------------------------
# Namecheap — availability + pricing
# Requires official API credentials (apply at namecheap.com → Profile → Tools → API)
# ---------------------------------------------------------------------------

def check_namecheap(domains: list) -> dict:
    """
    Returns {domain: {"available": bool, "price": float|None}}.
    Empty dict if credentials missing or check fails.
    """
    if not USE_NAMECHEAP:
        return {}
    try:
        import requests
        import xml.etree.ElementTree as ET
        params = {
            "ApiUser":    NAMECHEAP_API_USER,
            "ApiKey":     NAMECHEAP_API_KEY,
            "UserName":   NAMECHEAP_USERNAME,
            "ClientIp":   NAMECHEAP_CLIENT_IP,
            "Command":    "namecheap.domains.check",
            "DomainList": ",".join(domains),
        }
        r    = requests.get("https://api.namecheap.com/xml.response", params=params, timeout=10)
        root = ET.fromstring(r.text)
        ns   = {"nc": "http://api.namecheap.com/xml.response"}
        out  = {}
        for res in root.findall(".//nc:DomainCheckResult", ns):
            domain    = res.get("Domain", "")
            available = res.get("Available", "false").lower() == "true"
            out[domain] = {
                "availability": "Available" if available else "Taken",
                "price":        None,
                "registrar":    "namecheap",
            }
        return out
    except Exception as e:
        st.warning(f"Namecheap check failed: {e}")
        return {}

# ---------------------------------------------------------------------------
# WHOIS — parallel availability check (primary fallback)
# ---------------------------------------------------------------------------

def check_rdap(domains: list, max_workers: int = 10) -> dict:
    """
    Parallel RDAP availability check (modern replacement for WHOIS).
    Returns {domain: {"availability": "Available"|"Taken"|"Unknown", ...}}.

    Rules:
      - Available : RDAP server returns 404 (domain not registered)
      - Taken     : RDAP server returns 200 (domain registered)
      - Unknown   : timeout, connection error, or unexpected response
    """
    import requests

    # Direct RDAP endpoints for common TLDs — faster than IANA bootstrap
    RDAP_BASE = {
        "com": "https://rdap.verisign.com/com/v1/domain/",
        "net": "https://rdap.verisign.com/net/v1/domain/",
        "org": "https://rdap.org/domain/",
        "io":  "https://rdap.iana.org/domain/",
        "co":  "https://rdap.iana.org/domain/",
    }

    def _check(domain: str):
        tld  = domain.rsplit(".", 1)[-1].lower()
        base = RDAP_BASE.get(tld, "https://rdap.iana.org/domain/")
        try:
            r = requests.get(f"{base}{domain}", timeout=8,
                             headers={"Accept": "application/json"})
            if r.status_code == 200:
                return domain, "Taken"
            if r.status_code == 404:
                return domain, "Available"
            return domain, "Unknown"
        except Exception:
            return domain, "Unknown"

    results   = {}
    completed = 0
    bar       = st.progress(0, text=f"RDAP: checking {len(domains)} domains…")

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_check, d): d for d in domains}
        for future in as_completed(futures):
            domain, status = future.result()
            results[domain] = {"availability": status, "price": None, "registrar": "rdap"}
            completed      += 1
            bar.progress(completed / len(domains),
                         text=f"RDAP: {completed}/{len(domains)} checked…")
    bar.empty()
    return results

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="DomainHunterAI", page_icon="🔍", layout="wide")
    st.title("🔍 DomainHunterAI")
    st.caption("Find short, brandable domains for any industry — scored and availability-checked.")

    # ---- Status row --------------------------------------------------------
    col1, col2, col3 = st.columns(3)
    with col1:
        if USE_GODADDY:
            st.success("✅ GoDaddy connected")
        else:
            st.warning("⚠️ GoDaddy — no credentials")
    with col2:
        if USE_NAMECHEAP:
            st.success("✅ Namecheap connected")
        else:
            st.info("ℹ️ Namecheap — not configured")
    with col3:
        st.info("🔍 RDAP — always active")

    # ---- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.header("Search Settings")

        theme_input = st.text_input(
            "Themes / Industries",
            value="solar energy",
            help="One or more themes separated by commas — e.g. solar, biology, roofing",
        )
        themes = [t.strip() for t in theme_input.split(",") if t.strip()] or ["general"]

        tld = st.selectbox("TLD", [".com", ".io", ".co", ".net", ".org"])

        exact_syl = st.selectbox("Syllables", [1, 2, 3, 4], index=1)
        syl_exact = st.toggle("Exact syllables", value=True,
                              help="ON = only this count  |  OFF = up to this count")

        max_price = st.number_input("Max price ($)", value=20000, step=500, min_value=0)

        word_count = st.selectbox("Word count", [1, 2], index=0,
                                  help="1 = single word  |  2 = two words joined (e.g. solarapex)")

        st.divider()
        st.subheader("Filters")
        available_only  = st.toggle("Available domains only", value=True)
        real_words_only = st.toggle("Real English words only", value=True)
        pos_filter = st.multiselect(
            "Part of speech",
            ["Noun", "Verb", "Adjective", "Adverb"],
            default=[],
            help="Only show words of these types. Leave empty for all.",
        )

        st.divider()
        result_count = st.slider("Candidates to generate", min_value=20, max_value=500, value=100)

        st.divider()
        with st.expander("🔤 Letter Starter"):
            letter_enabled = st.toggle("Enable Letter Starter", value=False)
            start_letter = st.selectbox(
                "Starting letter",
                list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                index=0,
                disabled=not letter_enabled,
            )
            # letter_count removed — uses main "Candidates to generate" slider
            letter_combine = st.toggle(
                "Combine with theme results",
                value=False,
                disabled=not letter_enabled,
            )

    # ---- Generate ----------------------------------------------------------
    if st.button("🚀 Generate & Check Availability", use_container_width=True, type="primary"):

        # Step 1 — Build theme candidate pool
        with st.spinner("Building candidate list from dictionary…"):
            candidates = generate_candidates(
                themes, tld.lstrip("."), exact_syl, syl_exact, result_count, word_count, []
            )

        # Step 2 — Letter Starter: build letter-specific pool, merge, then HARD-ENFORCE letter
        if letter_enabled:
            with st.spinner(f"Picking '{start_letter}' words from dictionary…"):
                letter_pool = build_dictionary_pool(tuple(sorted(themes)), exact_syl)
                matching = [
                    w for w in letter_pool
                    if w.lower().startswith(start_letter.lower())
                    and (count_syllables(w) == exact_syl if syl_exact
                         else count_syllables(w) <= exact_syl)
                ]
                # Pre-apply real-words filter so the count requested is honoured
                if real_words_only:
                    matching = [w for w in matching if is_real_english_word(w)]
                # Pre-apply POS filter so we fill up to requested count with correct word types
                if pos_filter:
                    matching = [w for w in matching if get_pos(w) in pos_filter]
                # Shuffle — different words every run even for the same letter
                random.shuffle(matching)
                sampled = matching[:result_count]
                pos_label = "/".join(pos_filter) if pos_filter else "all types"
                st.info(f"Found {len(matching)} '{start_letter}' words ({pos_label}) — using {len(sampled)}.")
                display_theme = ", ".join(themes)
                letter_candidates = []
                for name in sampled:
                    sc, notes = score_domain(name, themes[0] if themes else "")
                    letter_candidates.append({
                        "domain":       f"{name}.{tld.lstrip('.')}",
                        "theme":        display_theme,
                        "tld":          f".{tld.lstrip('.')}",
                        "registrar":    "—",
                        "price":        None,
                        "availability": "Unknown",
                        "syllables":    count_syllables(name),
                        "word_count":   1,
                        "score":        sc,
                        "notes":        notes,
                    })
            if letter_combine:
                existing   = {c["domain"] for c in candidates}
                candidates += [c for c in letter_candidates if c["domain"] not in existing]
            else:
                candidates = letter_candidates

            # Hard enforce — drop any candidate that doesn't start with chosen letter
            candidates = [
                c for c in candidates
                if c["domain"].split(".")[0].lower().startswith(start_letter.lower())
            ]

        # Step 3 — Real English words filter  OR  Invented mode
        if word_count == 1:
            if real_words_only:
                # Keep only confirmed real dictionary words
                candidates = [
                    c for c in candidates
                    if is_real_english_word(c["domain"].split(".")[0])
                ]
            else:
                # Invented mode: REPLACE the whole candidate list with brandable names.
                # Use short words from the pool as roots so we have enough variety
                # to fill large counts (not just the ~14 theme seed words).
                pool_for_roots = build_dictionary_pool(tuple(sorted(themes)), exact_syl)
                short_roots    = [w for w in pool_for_roots if 2 <= len(w) <= 5][:200]
                brandable_names = _generate_brandable_fill(
                    themes, exact_syl, syl_exact,
                    result_count * 4,   # 4x so availability filter still leaves result_count
                    set(),
                    extra_roots=short_roots,
                    start_letter=start_letter if letter_enabled else None,
                )
                disp_theme = ", ".join(themes)
                candidates = []
                for name in brandable_names:
                    sc, notes = score_domain(name, themes[0])
                    candidates.append({
                        "domain":       f"{name}.{tld.lstrip('.')}",
                        "theme":        disp_theme,
                        "tld":          f".{tld.lstrip('.')}",
                        "registrar":    "—",
                        "price":        None,
                        "availability": "Unknown",
                        "syllables":    count_syllables(name),
                        "word_count":   1,
                        "score":        sc,
                        "notes":        notes + ", invented",
                    })
        # For 2-word compounds, skip real-word check — components come from the real-word
        # pool already; the joined string won't be a dictionary entry.

        if not candidates:
            st.warning(
                "No candidates matched your filters. "
                "Try adjusting syllable count, letter choice, or turning off 'Real English words only'."
            )
            st.stop()

        # Step 4 — Compute pos + rule-pass columns (used for filtering and display)
        for c in candidates:
            root         = c["domain"].split(".")[0].lower()
            c["pos"]         = get_pos(root)
            c["starts_with"] = "✓" if (not letter_enabled or root.startswith(start_letter.lower())) else "✗"
            c["real_word"]   = "✓" if is_real_english_word(root) else "✗"

        # Step 5 — Part of speech filter (exact match — Noun stays Noun, Adverb stays Adverb)
        if pos_filter:
            candidates = [c for c in candidates if c.get("pos") in pos_filter]
            if not candidates:
                st.warning("No candidates matched the selected part of speech. Try a different type.")
                st.stop()

        # Step 6 — Availability: GoDaddy → RDAP for any gaps
        domains    = [c["domain"] for c in candidates]
        avail_data = {}

        if USE_GODADDY:
            avail_data = check_godaddy(domains)

        missing = [d for d in domains if d not in avail_data]
        if missing and USE_NAMECHEAP:
            with st.spinner("Checking via Namecheap API…"):
                avail_data.update(check_namecheap(missing))

        missing = [d for d in domains if d not in avail_data]
        if missing:
            avail_data.update(check_rdap(missing))

        # Step 7 — Merge availability as text status into each candidate
        for c in candidates:
            info              = avail_data.get(c["domain"], {})
            c["availability"] = info.get("availability", "Unknown")
            c["registrar"]    = info.get("registrar", "—")
            real_price        = info.get("price")
            if real_price is not None:
                c["price"]          = real_price
                name                = c["domain"].split(".")[0]
                c["score"], c["notes"] = score_domain(name, themes[0], real_price)

        # Step 7.5 — Fill in estimated registration price for Available domains with no price.
        # GoDaddy API is unreliable; RDAP doesn't return prices. Use TLD defaults so the
        # Price column is useful for available domains.
        TLD_REG_PRICE = {".com": 12.99, ".net": 14.99, ".org": 13.99, ".io": 39.99, ".co": 25.99}
        for c in candidates:
            if c.get("availability") == "Available" and c["price"] is None:
                c["price"] = TLD_REG_PRICE.get(c.get("tld", ".com"), 12.99)

        # Step 8 — "Available only" filter: ONLY confirmed Available (Unknown is excluded)
        if available_only:
            candidates = [c for c in candidates if c.get("availability") == "Available"]

        # Step 9 — Price filter
        candidates = [c for c in candidates if c["price"] is None or c["price"] <= max_price]

        # Cap at requested count — the 4x internal pool is headroom for filters, not extra results
        candidates = candidates[:result_count]

        # Sort: more syllables first (more availability), then score within each tier
        candidates.sort(key=lambda x: (-x["syllables"], -x["score"]))
        st.session_state["results"]     = candidates
        st.session_state["theme_input"] = theme_input

    # ---- Results -----------------------------------------------------------
    if "results" in st.session_state:
        data = st.session_state["results"]

        if not data:
            st.warning(
                "No domains matched your filters. "
                "Try turning off 'Available only' (to see Taken/Unknown too), "
                "raising the price limit, or adjusting letter/syllable settings."
            )
            return

        df = pd.DataFrame(data)

        # Secondary market link — GoDaddy aftermarket search per domain
        df["market_url"] = df["domain"].apply(
            lambda d: f"https://www.godaddy.com/domainsearch/find?domainToCheck={d}"
        )

        # Ordered display columns — only include what exists in the dataframe
        display_cols = [
            "domain", "pos", "starts_with", "real_word",
            "syllables", "availability", "registrar", "price", "score", "notes", "market_url",
        ]
        df = df[[c for c in display_cols if c in df.columns]]
        df = df.rename(columns={
            "domain":       "Domain",
            "pos":          "Type",
            "starts_with":  "Letter ✓",
            "real_word":    "Real Word",
            "syllables":    "Syllables",
            "availability": "Availability",
            "registrar":    "Source",
            "price":        "Price ($)",
            "score":        "Score",
            "notes":        "Notes",
            "market_url":   "Market",
        })

        st.markdown(f"### {len(df)} candidates")
        st.dataframe(
            df,
            column_config={
                "Market": st.column_config.LinkColumn(
                    "Market 🔍",
                    display_text="GoDaddy →",
                )
            },
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False)
        label = st.session_state.get("theme_input", "domains").replace(" ", "_").replace(",", "-")
        st.download_button("📥 Export CSV", csv, f"domains_{label}.csv", "text/csv")


if __name__ == "__main__":
    main()
