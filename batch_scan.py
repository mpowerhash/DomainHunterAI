# -*- coding: utf-8 -*-
"""
batch_scan.py — Domain Matrix Scanner
======================================
Scans every combination of:
  - Letter   : A-Z
  - Syllables: 3 and 4 (exact)
  - POS      : Noun, Verb, Adjective, Adverb

Filters:
  - Real English words only  (wordfreq >= 1e-6)
  - Single word
  - TLD: .com
  - No numbers, no hyphens

Output: domain_matrix.csv  (open in Excel to filter/sort)

Run:  python batch_scan.py
No browser. No API keys. Takes ~5-10 minutes.
"""

import csv
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# NLP setup
# ---------------------------------------------------------------------------

def ensure_nlp():
    import nltk
    for corpus, path in [
        ("wordnet", "corpora/wordnet"),
        ("omw-1.4", "corpora/omw-1.4"),
        ("words",   "corpora/words"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            print(f"  Downloading {corpus}...")
            nltk.download(corpus, quiet=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def count_syllables(word: str) -> int:
    word = word.lower().strip()
    vowels = "aeiouy"
    count, prev = 0, False
    for ch in word:
        v = ch in vowels
        if v and not prev:
            count += 1
        prev = v
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def get_pos(word: str, wn) -> str:
    """Primary part of speech via WordNet. Pass wn module to avoid re-importing."""
    synsets = wn.synsets(word.lower())
    if not synsets:
        return "—"
    counts = {}
    for syn in synsets:
        counts[syn.pos()] = counts.get(syn.pos(), 0) + 1
    primary = max(counts, key=counts.get)
    return {
        "n": "Noun",
        "v": "Verb",
        "a": "Adjective",
        "s": "Adjective",   # satellite adjective
        "r": "Adverb",
    }.get(primary, "—")


def score_word(word: str) -> int:
    """0-100 score based on length and pronounceability."""
    l   = len(word)
    syl = count_syllables(word)
    s   = 0
    # Length
    if l <= 5:    s += 20
    elif l <= 8:  s += 15
    elif l <= 11: s +=  8
    else:         s +=  4
    # Syllables
    if syl == 1:   s += 15
    elif syl == 2: s += 10
    elif syl == 3: s +=  5
    # Memorability
    if l <= 7 and word[-1] in "aeiou": s += 15
    elif l <= 10:                       s +=  8
    else:                               s +=  3
    # Pronunciation
    awkward = ["xz", "qv", "bq", "vk", "jx", "zw", "kq"]
    if not any(a in word for a in awkward):
        s += 12 if l <= 8 else 6
    # Premium endings
    if any(word.endswith(e) for e in ["ex", "ix", "on", "en", "ar", "or"]):
        s += 10
    elif l <= 6:
        s += 7
    return min(100, s)

# ---------------------------------------------------------------------------
# Pool builder — loads once, reused for all 208 combos
# ---------------------------------------------------------------------------

def build_pool() -> list:
    """
    Returns every real English word (2-16 chars, freq >= 1e-6).
    Loads the full NLTK corpus and filters by wordfreq threshold.
    """
    from nltk.corpus import words as nltk_words
    from wordfreq import word_frequency

    raw     = set(w.lower() for w in nltk_words.words("en"))
    pool    = []
    for word in raw:
        if not word.isalpha():
            continue
        if not (2 <= len(word) <= 16):
            continue
        if "-" in word or any(c.isdigit() for c in word):
            continue
        if word_frequency(word, "en") < 1e-6:
            continue
        pool.append(word)
    return pool

# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

LETTERS        = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
SYLLABLE_COUNTS = [3, 4]
POS_TYPES      = ["Noun", "Verb", "Adjective", "Adverb"]

def run():
    print("=" * 56)
    print("  Domain Matrix Scanner")
    print("=" * 56)

    print("\n[1/3] Setting up NLP data...")
    ensure_nlp()
    from nltk.corpus import wordnet as wn

    print("[2/3] Loading dictionary...")
    t0   = time.time()
    pool = build_pool()
    print(f"      {len(pool):,} real English words loaded  ({time.time()-t0:.1f}s)")

    print(f"[3/3] Scanning 208 combinations (26 letters × 2 syllables × 4 POS)...\n")

    total_combos = len(LETTERS) * len(SYLLABLE_COUNTS) * len(POS_TYPES)
    done         = 0
    results      = []

    for letter in LETTERS:
        # Pre-slice by starting letter — avoids scanning full pool 208 times
        letter_words = [w for w in pool if w.startswith(letter.lower())]

        for exact_syl in SYLLABLE_COUNTS:
            syl_words = [w for w in letter_words if count_syllables(w) == exact_syl]

            for pos_type in POS_TYPES:
                done += 1
                matching = [w for w in syl_words if get_pos(w, wn) == pos_type]

                for word in matching:
                    results.append({
                        "domain":    f"{word}.com",
                        "word":      word,
                        "letter":    letter,
                        "syllables": exact_syl,
                        "pos":       pos_type,
                        "score":     score_word(word),
                    })

                bar = "#" * int(20 * done / total_combos)
                print(
                    f"  [{done:>3}/{total_combos}] [{bar:<20}]  "
                    f"{letter}  syl={exact_syl}  {pos_type:<10}  → {len(matching)} words"
                )

    return results


def save(results: list):
    out = Path(__file__).parent / "domain_matrix.csv"
    fields = ["domain", "word", "letter", "syllables", "pos", "score"]

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    print(f"\n{'='*56}")
    print(f"  ✓  {len(results):,} rows saved")
    print(f"  →  {out}")
    print(f"{'='*56}")
    print("\nOpen domain_matrix.csv in Excel to filter and sort.\n")


if __name__ == "__main__":
    rows = run()
    save(rows)
