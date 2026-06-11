# Business Value Score (BVS) — shared spec

> **Read this file before scoring any keyword, queue item, audit target, or refresh candidate.** All four systems compute BVS the same way so priorities stay coherent across the dashboard.

## The single question this answers

"If we rank this query, will it produce business value, or is it a zero-click trap?"

A keyword with 50,000 monthly searches is worth nothing if Google answers it directly in the SERP (Knowledge Graph, instant answer box, calculator). A keyword with 200 monthly searches is gold if it maps to a money page and the SERP shows commercial intent (Shopping ads, product pack, comparison snippets, paying advertisers).

BVS expresses this on a single 0 to 10 scale. Use it instead of relying on volume + intent alone.

## Inputs

For every keyword or URL, gather what you can. Missing inputs are fine — score the rest and record which inputs were missing.

| Input | Source | Notes |
|---|---|---|
| `intent` | DataForSEO search_intent, or inferred from query | One of: `transactional`, `commercial`, `comparison`, `navigational`, `informational`, `ambiguous`. |
| `cpc_usd` | DataForSEO keyword_ideas / keyword_overview | Average CPC in USD. Higher CPC = advertisers pay = commercial value. |
| `serp_features` | DataForSEO serp_organic_live_advanced | List of features on the SERP: `ai_overview`, `featured_snippet`, `people_also_ask`, `knowledge_graph`, `instant_answer`, `shopping`, `local_pack`, `top_stories`, `images`, `video`, `paid_ads` (count). |
| `organic_above_fold` | derived | true if any organic blue link is above the first SERP feature on desktop 1080p. |
| `money_page_match` | `context/services.md` | `full` if the topic IS one of the products/services, `partial` if adjacent, `none` otherwise. |
| `direct_answer_pattern` | derived from query | true if the query matches a factoid pattern (definition, conversion, time zone lookup, weather, currency, distance, sports score, dictionary lookup, mathematical operation, etc.). |
| `our_brand_in_serp` | site sitemap | true if the site already has a URL ranking in top 10 for this query. Used to gate navigational scoring. |

## Scoring components (sum to BVS, then clamp 0..10)

### Intent score (0 to 4)

| Intent | Score |
|---|---|
| `transactional` | 4 |
| `commercial` | 3 |
| `comparison` | 3 |
| `navigational` | 2 (only if `our_brand_in_serp = true`; otherwise 0, it belongs to a competitor) |
| `informational` | 1 |
| `ambiguous` | 1 |

### SERP commercial signals (0 to +4)

Sum the present signals:

| Signal | Bonus |
|---|---|
| `shopping` pack present | +2 |
| `paid_ads_count >= 2` (advertisers paying for this query) | +1 |
| `local_pack` present AND site has local-business intent (per site-config) | +2 |
| `product_pack` / `popular_products` present | +2 |

Cap the SERP commercial signal sum at +4.

### CPC band (0 to +2)

| CPC USD | Bonus |
|---|---|
| `>= 5` | +2 |
| `>= 1 and < 5` | +1 |
| `< 1` or `null` | 0 |

### Money-page match (0 to +3)

| Match | Bonus |
|---|---|
| `full` (topic IS one of the products / services in `context/services.md`) | +3 |
| `partial` (adjacent topic, supporting content for a money page) | +1 |
| `none` | 0 |

### Direct-answer penalty (−4 to 0) — the zero-click filter

Subtract the worst applicable penalty (do NOT stack them).

| SERP situation | Penalty |
|---|---|
| `knowledge_graph` answer present AND `direct_answer_pattern = true` (e.g. "quelle heure est-il a Tokyo" → Google shows the time directly) | −4 |
| `instant_answer` / calculator / converter present (e.g. "USD to EUR", "5 km to miles") | −4 |
| `knowledge_panel` present AND no organic link above the fold | −3 |
| `featured_snippet` (definition or paragraph) where the snippet contains a complete answer | −2 |
| `ai_overview` present AND no organic link above the fold | −2 |
| Overall zero-click density ≥ 0.7 (most pixels above the fold are SERP features, not organic results) | −2 |
| None of the above | 0 |

### Final BVS

```
bvs_raw = intent_score + serp_commercial_signals + cpc_band + money_page_match + direct_answer_penalty
bvs     = clamp(bvs_raw, 0, 10)
```

## Mapping BVS to priority

| BVS | Priority | Meaning |
|---|---|---|
| 8 to 10 | **1** | High-value commercial / money-page proximity. Target aggressively, queue immediately. |
| 5 to 7 | **2** | Useful supporting content. Queue when budget allows. |
| 2 to 4 | **3** | Park in bank. Only chase if the topic cluster justifies it (topical authority play) or if the writer can produce real Information Gain on it. |
| 0 to 1 | **skip** | Zero-click trap or off-business. Record in bank with `priority: "skip"` and a `skip_reason`. Never queue. |

## Zero-click trap detection (the zero-click trap rule)

A keyword is a **zero-click trap** when ALL of the following are true:

1. `intent` is `informational` or `ambiguous`.
2. The SERP has either `knowledge_graph` with a direct factoid answer, OR an `instant_answer` box, OR a `featured_snippet` whose text fully answers the query without needing the underlying page.
3. `money_page_match` is `none`.

In that case:
- Force `bvs = 0`.
- Set `skip_reason: "zero_click_trap: <which signal>"`.
- Never add to content-queue. Add to keyword-bank with `priority: "skip"` so it's not researched again.

**Counter-example**: "logiciel CRM pour PME" for a company selling CRM software → `intent = transactional`, `money_page_match = full`, SERP shows paid_ads + product_pack → BVS ≈ 4 + 3 + 1 + 3 = 11 → clamped to 10. This IS the kind of keyword to chase.

## Anti-pattern: do not exclusively chase high-volume informational keywords

Before this rule existed, the systems happily queued "what is X" definitional queries with high volume. Those are exactly the queries Google answers in the AI Overview / Knowledge Graph. Even if you rank #1, your CTR is 2-5%. The BVS sends those to skip unless there's a money-page link (e.g. a "what is X" post that funnels into the product page can still earn priority 2 via `money_page_match: partial`).

## Required output shape

Whenever a system records BVS for a keyword or URL, use this shape:

```json
{
  "bvs": 7,
  "bvs_components": {
    "intent_score": 3,
    "serp_commercial_signals": 2,
    "cpc_band": 1,
    "money_page_match": 3,
    "direct_answer_penalty": -2
  },
  "direct_answer_signal": "ai_overview_no_organic_above_fold",
  "zero_click_trap": false,
  "skip_reason": null
}
```

Store this on the keyword (in `keyword-bank.json` rows), on the queue item (in `content-queue.json` rows), and on the refresh candidate (in `refresh-candidates.json` rows). The dashboard renders BVS so you can see at a glance which work is high-value.

## Cost note

The component requiring DataForSEO `serp_organic_live_advanced` (for SERP features and AIO presence) is the main cost driver. The keyword-researcher already calls this once per seed, so SERP-feature data is free for seed-level BVS. For per-variation BVS, inherit the seed's `serp_features` unless the variation is specifically commercial — in which case call serp_organic_live_advanced once more on that variation (typical extra cost: $0.002 per call).

## Hard rules

- Never compute BVS from imagination. If you don't have the SERP features, set `serp_commercial_signals = 0` and `direct_answer_penalty = 0` and record `bvs_components_partial: true`.
- Never override `zero_click_trap = true` to push a keyword into the queue. If you think the trap detection is wrong, fix the detector (PR the rule above), not the individual case.
- BVS is computed at research time AND re-checked on refresh. A page that was BVS 8 in 2024 can be BVS 2 in 2026 because Google added an AI Overview that eats the click. The refresh-recommender re-scores BVS on every run.
