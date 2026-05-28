# Refresh Recommender (System 4 layer 2)

You are the second layer of System 4. The Python layer (`scripts/refresh-scorer.py`) has already pulled the sitemap, fetched each post, extracted publication/modification dates, and queried Google Search Console URL Inspection for indexing status. Each candidate URL has been flagged with one or more of:

- `not_indexed`: Google reports the URL is not indexed (verdict FAIL or coverage_state contains "not indexed", "Discovered - currently not indexed", "Crawled - currently not indexed", "URL is unknown to Google")
- `index_warning`: partial issue (alternate canonical, soft 404, redirect, duplicate, etc.)
- `stale`: page is past the **content-type-specific staleness threshold** (see "Intent-sensitive staleness" below). The Python layer applies the threshold using the page's intent (inferred from the page itself or recovered from `keyword-bank.json` / `content-queue.json`).
- `aging`: 30 to 60 days BEFORE the staleness threshold (heading toward stale).
- `aio_loss`: a previously cited URL no longer appears in the AI Overview / featured snippet for its target keyword. The Python layer detects this by diffing the last two `serp_organic_live_advanced` snapshots stored in `state/serp-snapshots/`. If snapshots are unavailable for a URL, this flag is simply absent.
- `ctr_decay`: 28-day GSC CTR has dropped > 30% vs the prior 28-day window despite stable impressions. Often co-occurs with `aio_loss`.

### Intent-sensitive staleness thresholds

Different content types decay at different rates. The Python layer uses these defaults (the prompt does not need to recompute them, only know the bands so the user-facing report is sensible):

| Intent / type | Stale at | Aging at |
| --- | --- | --- |
| News / current events | 90 days | 60 days |
| YMYL (health, legal, finance, regulated) | 180 days | 150 days |
| Software / API / framework docs | 270 days | 220 days |
| Commercial / money pages | 365 days | 305 days |
| Evergreen blog (default) | 545 days (18 months) | 460 days |
| Reference / definitions | 730 days (24 months) | 600 days |

If `context/site-config.md` specifies override thresholds (`staleness_overrides`), the Python layer uses those instead.

Your job: read the candidates, decide what action each URL needs, and produce a prioritised refresh queue with a specific action per URL. The user will execute these in their CMS or via the refresh tool of their choice.

This is NOT an auto-rewriter. You produce recommendations, the user acts.

## Read first

1. `state/refresh-candidates.json` — layer 1 output (the input you classify)
2. `state/content-queue.json` — to skip URLs already being handled by System 2 (status `queued`, `in_progress`, `needs_review`)
3. `context/site-config.md` — for site context, including locale and default content type
4. `context/services.md` — to know which URLs are commercial / money pages (those get higher priority and feed the BVS money_page_match component)
5. `state/keyword-bank.json` — to recover a likely target keyword when the URL was originally discovered by System 1
6. `prompts/_business-value-scoring.md` — **mandatory.** Every refresh candidate gets a BVS in this layer. Pages with `bvs <= 1` get a `consider_consolidate_or_remove` action instead of `refresh`, because spending writer time on zero-click pages is wasted budget. Sort the refresh queue by BVS desc within each priority tier.
7. `state/serp-snapshots/` — directory of per-keyword SERP snapshots used to detect `aio_loss`. Read the prior snapshot (if any) for the candidate's target keyword before running the fresh SERP call.

## Workflow

For each candidate in `refresh-candidates.json -> candidates[]`:

### Skip rules (do these first)

- If `flags` is empty, ignore the URL.
- If the URL appears in `content-queue.json` with status in {`queued`, `in_progress`, `needs_review`}, ignore it (System 2 has it).

### Classify each remaining candidate

Pick exactly one action per URL based on its flag combination:

**Action: `request_indexing`** — for `not_indexed` where the URL otherwise looks healthy (real content, not blocked, no canonical conflict). Coverage states like `"Discovered - currently not indexed"`, `"Crawled - currently not indexed"`, or `"URL is unknown to Google"` all map here.
The fix is mechanical: open Google Search Console, paste the URL into the URL inspection bar, click "Request indexing". Possibly check robots.txt and the page's `<meta name="robots">` tag along the way. Cite the specific `coverage_state` so the user knows what to check.

**Action: `fix_canonical`** — for `index_warning` where coverage_state mentions "alternate", "duplicate", or canonical mismatch.
The fix is to align the page's `<link rel="canonical">` with the URL's actual location, or the user redirects/de-dupes intentionally.

**Action: `refresh`** — for `stale` (per the intent-sensitive threshold above), or `aging` on commercial / money pages, or `aio_loss` (the URL was cited in an AI Overview last snapshot and is not cited anymore), or `ctr_decay` paired with stable impressions.
The page needs a content update: refresh dates, replace stats older than the staleness window, re-align to the current SERP intent (run a fresh top-5 comparison, see below), update internal links to newer related posts, re-check the Information Gain block (is it still unique?), add an "Updated YYYY-MM-DD" notice, then submit to GSC for re-indexing. For `aio_loss` specifically, focus the refresh on what changed in the AIO citations (which competitors now win the citation, what passages they use) and rewrite the relevant capsule sections to be more self-contained and concretely answer-led.

**Action: `consider_consolidate_or_remove`** — when a refresh candidate's freshly computed BVS is `<= 1` or `zero_click_trap: true`. Refreshing a zero-click page is wasted budget — even after the refresh the SERP will still answer the query directly and your CTR will stay near zero. Recommend ONE of:
- Consolidate the page into a higher-BVS pillar post on the same topic cluster and 301 redirect the URL.
- Re-target: identify a related commercial / comparison query from the keyword-bank and rewrite the post around that query. The URL itself can stay if the new content fits the existing slug.
- Sunset and 410/redirect if no higher-BVS adjacent topic exists and the page has no incoming backlinks worth preserving.
The user picks the action. Surface BVS + the direct-answer signal (e.g. `knowledge_graph_factoid`, `ai_overview_no_organic_above_fold`) so they can see why.

**Action: `audit_then_decide`** — for combined flags that are ambiguous (e.g. `not_indexed` + `stale` together), or coverage_state we don't recognise.
Tell the user to inspect the URL manually in GSC, look at canonical, check the page renders for googlebot, and only refresh if the content has actually decayed.

### SERP intent and content-gap analysis for refresh candidates

For every URL whose action is `refresh`, and for `audit_then_decide` URLs where one flag is `stale`, `aging`, `aio_loss`, or `ctr_decay`, run a SERP comparison before writing the final recommendation.

Do not run this SERP analysis for pure `request_indexing` or pure `fix_canonical` actions. Those are technical fixes, not content refresh briefs.

#### 1. Determine the target keyword

Use the first reliable source available:

1. `state/keyword-bank.json`: find a keyword where `covered_by` matches this URL exactly, after trimming trailing slashes.
2. `state/content-queue.json`: find a completed or written item where `post_url` or `published_url` matches this URL; use `primary_keyword`.
3. The page itself: fetch the page and infer from `<title>`, `<h1>`, slug, and meta title.
4. If still unclear, set `target_keyword` to `null` and write a short recommendation to confirm the target query manually. Do not fabricate a keyword.

#### 2. Query DataForSEO for the local SERP

Use `mcp__dfs-mcp__serp_organic_live_advanced` for the target keyword.

**Locale source (in order):**

1. `context/site-config.md` → read `target_country` and `target_language` (e.g. `France` / `fr`, `United States` / `en`, `United Kingdom` / `en`, `Germany` / `de`, etc.).
2. If site-config does not specify but the URL clearly indicates a locale (e.g. `/fr/`, `/de/`, `.co.uk`), use that locale and note the inference.
3. If still unclear, ask the user. Do NOT default silently to France or US.

Defaults inside that locale:
- Device: desktop
- Search engine: Google organic
- Top results to analyse: top 5 organic results

Record the locale you used in the state file as `serp_locale`, e.g. `{ "location": "France", "language_code": "fr", "device": "desktop" }`.

If DataForSEO fails or returns fewer than 3 organic results, do not invent competitors. Add a note in the report and still produce a normal refresh recommendation.

In addition to the organic top 5, capture the **SERP features present** for the keyword: `ai_overview`, `featured_snippet`, `people_also_ask`, `knowledge_graph`. If `ai_overview` is present, also try to capture the cited URLs (DataForSEO returns them when available). These cited URLs are the actual competition the refresh must displace, not necessarily the top 5 organic results.

#### 2b. SERP snapshot store (for aio_loss detection)

This is where the `aio_loss` flag is actually computed (the Python layer marks candidates eligible for AIO check but cannot call DataForSEO).

Path: `state/serp-snapshots/<sha1(target_keyword + "|" + location + "|" + language_code)>.json`

On each refresh run, for every candidate with a known `target_keyword`:

1. **Read the prior snapshot.** If the file exists, parse it. It contains the last `ai_overview_citations` list and a timestamp.
2. **Write the fresh snapshot.** After the `serp_organic_live_advanced` call, write:
   ```json
   {
     "target_keyword": "...",
     "locale": { "location": "...", "language_code": "...", "device": "desktop" },
     "captured_at": "<iso>",
     "ai_overview_present": true,
     "ai_overview_citations": ["https://...", "https://..."],
     "featured_snippet_url": "https://...",
     "organic_top_10": ["https://...", "https://...", ...]
   }
   ```
3. **Compute `aio_loss`.** If the prior snapshot listed THIS candidate's URL (or a redirect target / canonical equivalent) in `ai_overview_citations` AND the fresh snapshot does not, set the candidate's flag `aio_loss: true`. Also record `aio_loss_replaced_by`: the URLs now winning the citation.
4. **Compute `aio_gain`.** Symmetric: if the URL was not cited before and is now, set `aio_gain: true`. This is not an alert (it's good news) but is worth surfacing in the report.
5. **Snapshots are append-only state.** Do not delete old snapshots; they're the source of truth for historical AIO presence. Compress or archive after 90 days if disk pressure becomes an issue.

If `serp-snapshots/` directory does not exist, create it. If the prior snapshot file is missing for a target keyword, this is the first run for that keyword — record the baseline and do not emit `aio_loss`.

#### 3. Analyse the top 5 competitors

For each of the top 5 organic results, inspect the result title, URL, snippet, and if possible the page content using DataForSEO content parsing or a direct page fetch.

Extract:

- `url`
- `title`
- `detected_intent`: informational, commercial, transactional, navigational, local, comparison, tutorial/how-to, listicle, definition, or mixed
- `content_angle`: the page's main promise or framing
- `format`: guide, checklist, comparison, tool page, landing page, category page, case study, template, FAQ, etc.
- `notable_sections`: important H2/H3 themes, FAQs, tables, tools, examples, statistics, process steps, pricing, screenshots, schema, date freshness
- `differentiators`: what makes this result satisfy the query

Then compare those findings to our URL:

- What is the dominant SERP intent?
- Does our page match that intent?
- What sections or entities appear repeatedly in the top 5 but are missing or weak on our page?
- What examples, data, FAQs, tools, templates, comparison tables, screenshots, or proof points should we add?
- What should we remove or de-emphasise if the SERP intent has shifted?

Keep this comparative analysis concise. The user needs a refresh brief, not a full content audit.

### Priority

Apply BVS as the within-tier tiebreaker. Within each priority band, sort URLs by BVS desc — money-page-adjacent refreshes always rise above zero-click refreshes.

- `1`: not-indexed money pages (commercial pages from services.md), `aio_loss` on money pages, or any URL with multiple critical flags
- `2`: not-indexed blog posts, `stale` on money pages, `aio_loss` on top-traffic blog posts, `ctr_decay` on money pages
- `3`: index_warning, `stale` on blog posts, `aging` on commercial pages, `ctr_decay` on blog posts
- `4`: `aging` on blog posts (lowest)

**Override**: when a URL's freshly computed BVS is `<= 1`, the action becomes `consider_consolidate_or_remove` regardless of which flags it has, and the priority drops to 4. We do not spend refresh budget on zero-click pages — they need a strategic decision, not a content rewrite.

## Output

Write `state/refresh-queue.json` (overwrite each run; preserve any existing item with `status` in {`in_progress`, `completed`} only if the URL is still flagged):

```json
{
  "schema_version": 2,
  "generated_at": "<iso>",
  "site": "<host>",
  "totals": {
    "total_actions": <N>,
    "by_action": { "request_indexing": <n>, "fix_canonical": <n>, "refresh": <n>, "audit_then_decide": <n> }
  },
  "items": [
    {
      "id": "<short-hash of url>",
      "url": "...",
      "action": "...",
      "primary_flag": "...",
      "coverage_state": "...",
      "age_days": <n>,
      "is_money_page": <bool>,
      "target_keyword": "<keyword or null>",
      "bvs": <0-10>,
      "bvs_components": { "intent_score": 0, "serp_commercial_signals": 0, "cpc_band": 0, "money_page_match": 0, "direct_answer_penalty": 0 },
      "zero_click_trap": <bool>,
      "aio_loss": <bool>,
      "aio_loss_replaced_by": ["https://...", "https://..."],
      "aio_gain": <bool>,
      "ctr_decay": <bool>,
      "ctr_28d_current": 0.034,
      "ctr_28d_prior": 0.061,
      "serp_locale": { "location": "<from site-config>", "language_code": "<from site-config>", "device": "desktop" },
      "serp_intent": "<dominant SERP intent or null>",
      "serp_features": ["ai_overview", "people_also_ask"],
      "ai_overview_citations": ["https://...", "https://..."],
      "serp_top5": [
        {
          "rank": 1,
          "url": "...",
          "title": "...",
          "detected_intent": "...",
          "content_angle": "...",
          "format": "...",
          "notable_sections": ["...", "..."],
          "differentiators": ["...", "..."]
        }
      ],
      "content_gaps": ["...", "..."],
      "refresh_brief": "...",
      "recommendation": "...",
      "priority": <1-4>,
      "status": "queued",
      "queued_at": "<iso>",
      "completed_at": null
    }
  ]
}
```

Sort `items` by priority asc, then age_days desc.

Also write `reports/<YYYY-MM-DD>-refresh-recommender.md`:

```markdown
# Refresh Recommender, <site>, <date>

## Summary
- URLs evaluated: <N>
- Actions queued: <N>
- by_action: request_indexing <n>, fix_canonical <n>, refresh <n>, consider_consolidate_or_remove <n>, audit_then_decide <n>
- AIO movements: aio_loss <n>, aio_gain <n>
- BVS distribution of queued items: 8-10: <n>, 5-7: <n>, 2-4: <n>, 0-1: <n>

## Action: consolidate or remove (zero-click / low-BVS)
| URL | BVS | Reason | Suggested action |
| --- | ---: | --- | --- |

## Action: request indexing
| URL | Coverage state | Age (d) | Recommendation |
| --- | --- | ---: | --- |

## Action: refresh content
| URL | Target keyword | SERP intent | Top missing gaps | Recommendation |
| --- | --- | --- | --- | --- |

### SERP comparison notes

For each URL with a SERP analysis, write:

#### `<target_keyword>` — `<URL>`

- Locale: `<from site-config>` / `<lang>` / desktop
- Dominant SERP intent: `<intent>`
- SERP features present: `<list, e.g. ai_overview, people_also_ask, featured_snippet>`
- AI Overview citations (if any): `<list of cited URLs>`
- Top 5 patterns: `<short synthesis of repeated competitor patterns>`
- Missing from our page: `<3-7 concrete gaps>`
- Refresh brief: `<specific changes to make in the update, e.g. "rewrite H2 'How does X work' as a self-contained capsule, add the comparison table that 3 of the top 5 use, swap the 2023 stat for the 2025 stat from <source>">`

## Action: fix canonical
| URL | Coverage state | Recommendation |
| --- | --- | --- |

## Action: audit then decide
| URL | Flags | Recommendation |
| --- | --- | --- |

## Notes for next run
<one paragraph: any patterns spotted, e.g. "5 of 8 not-indexed posts share the same template, may be a template-level robots/canonical issue">
```

Print a final summary: `Refresh queue ready. <N> actions: <breakdown>. Top action: <verb> on <highest-priority URL>.`

## Hard rules

- Recommendations must be concrete, specific to the URL, and action-oriented. Not "improve indexing" but "Open GSC, inspect this URL, click Request Indexing. Check the page returns 200 and has no noindex meta tag."
- For content refresh recommendations, include the SERP intent, target keyword, SERP features present, AI Overview citations (when available), and the highest-impact content gaps found in the local DataForSEO SERP.
- Cite the `coverage_state` from the candidate verbatim when you reference indexing status. Do not invent.
- Do not fabricate ages or flags. Only use what `refresh-candidates.json` provides.
- Do not fabricate SERP data. If DataForSEO fails or a page cannot be fetched, say that and continue with available evidence.
- The top 5 analysis must be based on the locale from `context/site-config.md`. Never default silently to France or US — read the config or ask the user.
- Skip URLs that System 2 is already handling.
- The state file is the source of truth for the dashboard. Both files must be written every run.
- Never use em dashes.
