#!/usr/bin/env python3
"""Lint a Content Writer markdown post against the hard quality rules.

Exits 0 if the post passes every rule. Exits 1 if any rule fails, with a
human-readable list of failures printed to stdout.

Rules checked:
  1. Zero em-dashes (—)
  2. Zero phrases from context/brand-guidelines.md "Banned words and phrases"
  3. No excluded competitor names from brand-guidelines.md
  4. Every markdown link has anchor text of 1-3 words (4 allowed when the phrase
     is a multi-word capitalized entity like "Core Web Vitals")
  5. H2 capsule ratio is between 55% and 75% (capsules end with "?")
  6. Word count within +/- 25% of target_word_count from front-matter
  7. Three Kings: primary_keyword in title, first paragraph, AND >=2 H2s
  8. Heading hierarchy: exactly one H1, no level skips (H2 -> H4)
  9. Passage self-containment: each capsule's first sentence does not start
     with a context-dependent pronoun ("It ", "This ", "These ", "They ",
     "Those ", "That ", "Such ")

The Content Writer's coordinator calls this AFTER the post is saved.
On failure, the coordinator marks the queue item status='needs_review'.

Usage:
  lint-post.py <markdown-path>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = None  # lazy-loaded


def load_brand_rules() -> dict:
    """Parse banned-words and competitor names from brand-guidelines.md."""
    global BRAND
    if BRAND is not None:
        return BRAND
    candidates = [
        ROOT.parent / "context" / "brand-guidelines.md",
        ROOT.parent.parent / "context" / "brand-guidelines.md",
        ROOT / "context" / "brand-guidelines.md",
    ]
    path = next((c for c in candidates if c.exists()), None)
    if path is None:
        BRAND = {"banned": [], "competitors": []}
        return BRAND
    text = path.read_text()
    banned, competitors = [], []
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            h = line.lower()
            if "banned" in h:
                section = "banned"
            elif "competitor" in h and "must not" in h.lower() or "competitor" in h and "not appear" in h.lower():
                section = "competitors"
            else:
                section = None
        elif line.lstrip().startswith("- ") and section:
            entry = line.lstrip("- ").strip().strip('"').strip("'")
            entry = entry.split(":", 1)[0].strip()
            entry = entry.split("(", 1)[0].strip()
            entry = entry.split("/", 1)[0].strip()
            if entry and not entry.lower().startswith("however"):
                if section == "banned":
                    banned.append(entry)
                elif section == "competitors":
                    competitors.extend([c.strip() for c in entry.split(",")])
    BRAND = {"banned": banned, "competitors": [c for c in competitors if c]}
    return BRAND


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, parts[2]


def count_anchor_words(anchor: str) -> int:
    # Hyphenated terms count as one word (AI-specific is 1, not 2)
    cleaned = re.sub(r"[^\w\s\-]", " ", anchor)
    return len([w for w in cleaned.split() if not w.isdigit() and len(w) > 0])


def is_named_entity_phrase(anchor: str) -> bool:
    """A 4-word anchor is allowed when it's a multi-word capitalized entity.

    Heuristic: at least 2 of the words are capitalized (e.g. "Core Web Vitals",
    "Google AI Overviews", "Search Quality Rater"). This carves an exception
    for proper nouns without opening the door to long marketing anchors.
    """
    words = [w for w in re.sub(r"[^\w\s\-]", " ", anchor).split() if w]
    cap_count = sum(1 for w in words if w[:1].isupper() and w[1:].lower() == w[1:])
    return cap_count >= 2


def keyword_head(primary: str) -> str:
    """Return the most distinctive 2-word head of a primary keyword.

    "how to rank in ai overviews" -> "ai overviews"
    "best ai seo tool" -> "ai seo tool" (last 2)
    """
    words = [w for w in primary.lower().split() if w not in {
        "how", "to", "for", "in", "the", "a", "an", "of", "your", "best", "what", "is",
    }]
    if len(words) >= 2:
        return " ".join(words[-2:])
    return primary.lower().strip()


def lint(path: Path) -> list[str]:
    failures: list[str] = []
    text = path.read_text()
    fm, body = split_front_matter(text)
    rules = load_brand_rules()

    # Rule 1: em-dashes
    em = body.count("—")
    if em:
        failures.append(f"em-dashes found: {em} (must be 0)")

    # Rule 2: banned phrases
    body_lc = body.lower()
    for phrase in rules["banned"]:
        p = phrase.strip().strip('"').lower()
        if not p:
            continue
        if re.search(r"\b" + re.escape(p).replace(r"\ ", r"\s+") + r"\b", body_lc):
            failures.append(f"banned phrase: {phrase!r}")

    # Rule 3: excluded competitor names
    for comp in rules["competitors"]:
        if not comp:
            continue
        if re.search(r"\b" + re.escape(comp.lower()) + r"\b", body_lc):
            failures.append(f"excluded competitor mentioned: {comp!r}")

    # Rule 4: anchor text length 1-3 words (4 allowed for named entity phrases)
    links = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", body)
    long_anchors = []
    for anchor, _url in links:
        n = count_anchor_words(anchor)
        if n > 4:
            long_anchors.append(f"{n} words: {anchor!r}")
        elif n == 4 and not is_named_entity_phrase(anchor):
            long_anchors.append(f"4 words (not a named entity): {anchor!r}")
    if long_anchors:
        failures.append(
            f"anchors over 3 words (and not multi-word named entities): "
            f"{len(long_anchors)} of {len(links)} links\n  "
            + "\n  ".join(long_anchors)
        )

    # Rule 5: H2 capsule ratio (capsules phrased as questions)
    h2s = re.findall(r"^## (.+)$", body, flags=re.MULTILINE)
    h2s = [h for h in h2s if h.strip().upper() != "TL;DR"]
    if h2s:
        capsules = sum(1 for h in h2s if h.strip().endswith("?"))
        ratio = capsules / len(h2s)
        if not (0.55 <= ratio <= 0.75):
            failures.append(
                f"H2 capsule ratio {ratio:.0%} ({capsules}/{len(h2s)}); target 60-70%"
            )

    # Rule 6: word count within +/-25% of target (relaxed from 15%)
    try:
        target = int(fm.get("target_word_count", "0"))
        actual = int(fm.get("word_count", str(len(body.split()))))
        if target:
            delta = abs(actual - target) / target
            if delta > 0.25:
                failures.append(
                    f"word count {actual} is {delta:.0%} off target {target} (max 25%)"
                )
    except (ValueError, TypeError):
        pass

    # Rule 7: Three Kings extended
    primary = fm.get("primary_keyword", "").lower().strip()
    if primary:
        title = fm.get("title", "").lower()
        first_para = ""
        for chunk in body.strip().split("\n\n"):
            chunk = chunk.strip()
            if chunk and not chunk.startswith("#") and not chunk.startswith("-") and not chunk.startswith("|"):
                first_para = chunk.lower()
                break
        head = keyword_head(primary)
        h2_hits = sum(1 for h in h2s if head in h.lower())
        # Title and first-paragraph checks: full phrase OR keyword head must appear
        title_match = primary in title or head in title
        first_match = primary in first_para or head in first_para
        if not title_match:
            failures.append(f"Three Kings: keyword head {head!r} missing from title")
        if not first_match:
            failures.append(f"Three Kings: keyword head {head!r} missing from first paragraph")
        if h2_hits < 2:
            failures.append(
                f"Three Kings: keyword head {head!r} in only {h2_hits} H2 (need >=2)"
            )

    # Rule 8: heading hierarchy (one H1, no level skips)
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = [(len(m.group(1)), m.group(2).strip()) for m in heading_pattern.finditer(body)]
    h1s = [text for lvl, text in headings if lvl == 1]
    if len(h1s) > 1:
        failures.append(f"heading hierarchy: {len(h1s)} H1 tags found (must be exactly 1)")
    # Detect level skips: if a heading is more than 1 level deeper than the previous one
    skips = []
    prev = None
    for lvl, text in headings:
        if prev is not None and lvl > prev + 1:
            skips.append(f"H{prev} -> H{lvl}: {text!r}")
        prev = lvl
    if skips:
        failures.append(
            f"heading hierarchy: {len(skips)} level skip(s)\n  " + "\n  ".join(skips)
        )

    # Rule 9: passage self-containment (capsule first sentence does not start
    # with a context-dependent pronoun). Applies to capsule sections only.
    pronoun_starts = ("It ", "This ", "These ", "They ", "Those ", "That ", "Such ")
    capsule_sections = re.findall(
        r"^## (.+\?)\s*\n+([^\n].*?)(?=\n+(?:#{1,6}\s|$))",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    weak_starts = []
    for h2, section in capsule_sections:
        first_para = section.strip().split("\n\n", 1)[0].lstrip()
        # Strip a leading inline-link wrapper like "[anchor](url)" if present
        first_sentence = first_para.split(".")[0].strip()
        if any(first_sentence.startswith(p) for p in pronoun_starts):
            # Only flag if the pronoun isn't immediately followed by a clarifying noun
            # we can detect (e.g. "It takes about 30 minutes" is fine if the H2 is
            # "How long does setup take?"). Heuristic: check the noun appears nearby.
            head_words = {w.lower() for w in re.findall(r"\w+", h2) if len(w) > 3}
            sentence_words = {w.lower() for w in re.findall(r"\w+", first_sentence)}
            if not (head_words & sentence_words):
                weak_starts.append(f"{h2!r}: starts with {first_sentence.split()[0]!r}")
    if weak_starts:
        failures.append(
            f"passage self-containment: {len(weak_starts)} capsule(s) start with a "
            f"context-dependent pronoun without re-stating the subject\n  "
            + "\n  ".join(weak_starts)
        )

    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: lint-post.py <markdown-path>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    failures = lint(path)
    if failures:
        print(f"LINT FAIL ({len(failures)} issue{'s' if len(failures)!=1 else ''}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("LINT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
