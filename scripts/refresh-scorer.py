#!/usr/bin/env python3
"""System 4 layer 1: Score every blog post on age + indexing + CTR + BVS.

For each URL in the site's sitemap (filtered to blog posts), we determine:
  - publication / last-modified date (from JSON-LD, article meta tags, or <time>)
  - GSC indexing status via urlInspection.index.inspect
  - last crawl time
  - 28-day vs prior-28-day GSC CTR and impressions (for ctr_decay)
  - partial Business Value Score (BVS): the components we can compute without
    DataForSEO. The layer-2 Claude prompt completes BVS with SERP signals.

We flag:
  not_indexed:   GSC reports the URL is not indexed
  index_warning: GSC reports a partial issue (canonical mismatch, soft 404, etc.)
  stale:         age past the intent-sensitive threshold (news 90d, YMYL 180d,
                 software 270d, money page 365d, evergreen 18mo, reference 24mo)
  aging:         30 to 60 days BEFORE the staleness threshold
  ctr_decay:     28-day CTR dropped > 30% vs prior 28d with stable impressions

Output: state/refresh-candidates.json (consumed by the layer-2 Claude prompt
that adds per-URL action recommendations and produces refresh-queue.json).

Auth reuses the helpers from SEO-Access/mcp-gsc/gsc_server.py.

Usage:
  refresh-scorer.py [--site https://www.your-site.com/] [--include /blog/] [--max-urls 60]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
GSC_PATH = Path("/path/to/the-four-systems/SEO-Access/mcp-gsc")
sys.path.insert(0, str(GSC_PATH))

try:
    from gsc_server import get_gsc_service  # type: ignore
except Exception as e:
    print(f"ERROR: cannot import gsc_server auth helpers: {e}", file=sys.stderr)
    sys.exit(1)

UA = "Mozilla/5.0 (compatible; the-four-systems/refresh-scorer)"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Intent-sensitive staleness thresholds in days. Maps content_type -> (stale_at, aging_at).
# The default is the "evergreen" band — applied when site-config does not specify.
STALENESS_BANDS: dict[str, tuple[int, int]] = {
    "news":       (90,  60),
    "ymyl":       (180, 150),
    "software":   (270, 220),
    "commercial": (365, 305),
    "evergreen":  (545, 460),
    "reference":  (730, 600),
}
DEFAULT_CONTENT_TYPE = "evergreen"


# ---------- site-config + services parsing -----------------------------------

def read_site_config(root: Path) -> dict:
    """Return dict with content_type, locale_location, locale_language.

    Falls back to evergreen / United States / en if the file is missing or
    fields are absent. The layer-2 prompt is the authoritative source for
    locale at SERP-call time; the Python layer only uses content_type here.
    """
    cfg = {
        "content_type": DEFAULT_CONTENT_TYPE,
        "locale_location": "United States",
        "locale_language": "en",
        "staleness_overrides": None,
    }
    path = root / "context" / "site-config.md"
    if not path.exists():
        return cfg
    text = path.read_text(errors="replace")
    # Look for the Section A keys we documented in context-bootstrapper.
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("- target_country:"):
            cfg["locale_location"] = s.split(":", 1)[1].strip()
        elif s.lower().startswith("- target_language:"):
            cfg["locale_language"] = s.split(":", 1)[1].strip()
        elif s.lower().startswith("default_content_type:") or "## default content type" in s.lower():
            # On the heading line, parse the next non-blank line; otherwise the value follows ":".
            if ":" in s and not s.lower().startswith("##"):
                cfg["content_type"] = s.split(":", 1)[1].strip().lower()
    # Fallback: find first non-blank line after the "## Default content type" header.
    if cfg["content_type"] == DEFAULT_CONTENT_TYPE:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("## default content type"):
                for follow in lines[i + 1:]:
                    if follow.strip():
                        cfg["content_type"] = follow.strip().lower()
                        break
                break
    # Normalize to a known band; fall back if the user wrote something unexpected.
    if cfg["content_type"] not in STALENESS_BANDS:
        cfg["content_type"] = DEFAULT_CONTENT_TYPE
    return cfg


def read_services_tokens(root: Path) -> set[str]:
    """Build a token set from services.md to power money_page_match.

    Heuristic: pull words (>=4 chars, lowercased) from the "## What we sell"
    list items. Good enough to match keywords like "phone numbers", "drain
    cleaning", etc. against the BVS money_page_match component.
    """
    path = root / "context" / "services.md"
    if not path.exists():
        return set()
    tokens: set[str] = set()
    in_what = False
    for line in path.read_text(errors="replace").splitlines():
        s = line.strip()
        if s.startswith("##"):
            in_what = "what we sell" in s.lower() or "offerings" in s.lower()
            continue
        if in_what and s.startswith("- "):
            entry = s.lstrip("- ").split(":", 1)[0]
            for w in re.findall(r"[a-zA-Z]{4,}", entry.lower()):
                tokens.add(w)
    return tokens


def staleness_for(content_type: str, age_days: int | None) -> tuple[str | None, int, int]:
    """Return (flag, stale_at, aging_at) for the given content type + age."""
    stale_at, aging_at = STALENESS_BANDS.get(content_type, STALENESS_BANDS[DEFAULT_CONTENT_TYPE])
    if age_days is None:
        return None, stale_at, aging_at
    if age_days >= stale_at:
        return "stale", stale_at, aging_at
    if aging_at <= age_days < stale_at:
        return "aging", stale_at, aging_at
    return None, stale_at, aging_at


# ---------- GSC searchAnalytics for CTR decay --------------------------------

def gsc_ctr_28d(svc, site: str, url: str, today: dt.date) -> dict:
    """Return current 28d vs prior 28d CTR and impressions for a single URL.

    Strategy: two searchAnalytics.query calls with dimensions=['page'] and a
    page filter. We aggregate over all queries the URL ranked for; the per-URL
    CTR is impressions-weighted across them.
    """
    def _query(start: dt.date, end: dt.date) -> dict:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["page"],
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "page",
                    "operator": "equals",
                    "expression": url,
                }],
            }],
            "rowLimit": 1,
        }
        try:
            resp = svc.searchanalytics().query(siteUrl=site, body=body).execute()
            rows = resp.get("rows", [])
            if not rows:
                return {"impressions": 0, "clicks": 0, "ctr": None}
            r = rows[0]
            return {
                "impressions": int(r.get("impressions", 0)),
                "clicks": int(r.get("clicks", 0)),
                "ctr": float(r.get("ctr", 0.0)) if r.get("impressions") else None,
            }
        except Exception as e:
            return {"impressions": 0, "clicks": 0, "ctr": None, "_error": str(e)[:200]}

    # Current window: last 28 days ending 3 days ago (GSC data lag).
    end_cur = today - dt.timedelta(days=3)
    start_cur = end_cur - dt.timedelta(days=27)
    # Prior window: 28 days immediately before that.
    end_prev = start_cur - dt.timedelta(days=1)
    start_prev = end_prev - dt.timedelta(days=27)

    return {
        "current":  _query(start_cur, end_cur),
        "previous": _query(start_prev, end_prev),
        "windows": {
            "current":  [start_cur.isoformat(),  end_cur.isoformat()],
            "previous": [start_prev.isoformat(), end_prev.isoformat()],
        },
    }


def ctr_decay_flag(ctr_block: dict) -> dict:
    """Return {"ctr_decay": bool, "ctr_change_pct": float|None, "impr_change_pct": float|None}.

    Rule: ctr_decay = true when current CTR dropped >= 30% vs previous, AND
    impressions are stable (within ±20% of the previous window). Otherwise the
    CTR drop is probably just impressions falling.
    """
    cur = ctr_block.get("current", {})
    prv = ctr_block.get("previous", {})
    cur_ctr = cur.get("ctr") or 0.0
    prv_ctr = prv.get("ctr") or 0.0
    cur_imp = cur.get("impressions") or 0
    prv_imp = prv.get("impressions") or 0
    if prv_ctr == 0 or prv_imp == 0:
        return {"ctr_decay": False, "ctr_change_pct": None, "impr_change_pct": None}
    ctr_change = (cur_ctr - prv_ctr) / prv_ctr
    impr_change = (cur_imp - prv_imp) / prv_imp
    decayed = ctr_change <= -0.30 and abs(impr_change) <= 0.20
    return {
        "ctr_decay": bool(decayed),
        "ctr_change_pct": round(ctr_change * 100, 1),
        "impr_change_pct": round(impr_change * 100, 1),
    }


# ---------- partial BVS (layer 2 completes the SERP components) --------------

def _infer_intent_from_url(url: str) -> str:
    """Very rough intent inference from URL path. Refined by layer 2 if needed."""
    path = url.lower()
    if any(x in path for x in ("/pricing", "/buy", "/order", "/checkout", "/shop", "/cart")):
        return "transactional"
    if any(x in path for x in ("/vs-", "-vs-", "/compare", "/review", "/alternatives")):
        return "comparison"
    if any(x in path for x in ("/services", "/products", "/solutions", "/platform")):
        return "commercial"
    return "informational"


def _money_page_match(url: str, title_or_keyword: str, tokens: set[str]) -> str:
    """Return 'full' | 'partial' | 'none' based on token overlap with services.md."""
    if not tokens:
        return "none"
    haystack = (url + " " + (title_or_keyword or "")).lower()
    haystack_tokens = set(re.findall(r"[a-z]{4,}", haystack))
    overlap = tokens & haystack_tokens
    if not overlap:
        return "none"
    # "full" if multiple service tokens hit or any commercial URL marker is present.
    if len(overlap) >= 2 or any(p in url.lower() for p in ("/services/", "/products/", "/pricing", "/platform")):
        return "full"
    return "partial"


def partial_bvs(url: str, target_keyword: str | None, services_tokens: set[str]) -> dict:
    """Compute the BVS components we can determine without DataForSEO.

    Returns the same shape the layer-2 prompt will fill in, with SERP-dependent
    components set to 0 and `bvs_components_partial: true` so the consumer knows
    to either run the SERP analysis or accept a lower-confidence BVS.
    """
    intent = _infer_intent_from_url(url)
    intent_score = {
        "transactional": 4,
        "commercial":    3,
        "comparison":    3,
        "navigational":  2,
        "informational": 1,
        "ambiguous":     1,
    }.get(intent, 1)
    mp_match = _money_page_match(url, target_keyword or "", services_tokens)
    money_score = {"full": 3, "partial": 1, "none": 0}[mp_match]
    components = {
        "intent_score": intent_score,
        "serp_commercial_signals": 0,
        "cpc_band": 0,
        "money_page_match": money_score,
        "direct_answer_penalty": 0,
    }
    raw = sum(components.values())
    return {
        "bvs": max(0, min(10, raw)),
        "bvs_components": components,
        "bvs_components_partial": True,
        "money_page_match": mp_match,
        "inferred_intent": intent,
        "zero_click_trap": False,
    }


# ---------- sitemap helpers --------------------------------------------------

def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read().decode("utf-8", errors="replace")


def discover_sitemaps(site: str) -> list[str]:
    """Find sitemap URL(s) via /robots.txt and common fallbacks."""
    site = site.rstrip("/")
    found: list[str] = []
    try:
        robots = fetch_text(f"{site}/robots.txt")
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                found.append(line.split(":", 1)[1].strip())
    except Exception:
        pass
    if found:
        return found
    # fallbacks
    for path in ["/sitemap.xml", "/sitemap-index.xml", "/sitemap-0.xml"]:
        try:
            fetch_text(f"{site}{path}")
            return [f"{site}{path}"]
        except Exception:
            continue
    return []


def expand_sitemap(url: str, depth: int = 0) -> list[dict]:
    """Return list of dicts: {loc, lastmod (or None)}. Follows index files."""
    if depth > 3:
        return []
    try:
        body = fetch_text(url)
    except Exception as e:
        print(f"WARN: failed to fetch {url}: {e}", file=sys.stderr)
        return []
    body = re.sub(r"<\?xml[^>]+\?>", "", body)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"WARN: sitemap parse error {url}: {e}", file=sys.stderr)
        return []
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        out: list[dict] = []
        for sm in root.findall("sm:sitemap", SITEMAP_NS):
            loc = sm.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
            if loc:
                out.extend(expand_sitemap(loc, depth + 1))
        return out
    elif tag == "urlset":
        out = []
        for u in root.findall("sm:url", SITEMAP_NS):
            loc = u.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
            lastmod = u.findtext("sm:lastmod", default="", namespaces=SITEMAP_NS).strip() or None
            if loc:
                out.append({"loc": loc, "lastmod": lastmod})
        return out
    return []


# ---------- date extraction --------------------------------------------------

DATE_PATTERNS = [
    # JSON-LD (preferred): catches both datePublished and dateModified
    (re.compile(r'"datePublished"\s*:\s*"([^"]+)"'), "json_ld_published"),
    (re.compile(r'"dateModified"\s*:\s*"([^"]+)"'), "json_ld_modified"),
    # OpenGraph / article meta
    (re.compile(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', re.I), "og_published"),
    (re.compile(r'<meta[^>]+property=["\']article:modified_time["\'][^>]+content=["\']([^"\']+)', re.I), "og_modified"),
    (re.compile(r'<meta[^>]+name=["\']pubdate["\'][^>]+content=["\']([^"\']+)', re.I), "meta_pubdate"),
    # <time datetime="...">
    (re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\'][^>]*>', re.I), "time_datetime"),
]


def parse_iso_date(s: str) -> dt.date | None:
    s = s.strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(s).date()
    except ValueError:
        pass
    # Try date-only patterns
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def extract_dates(html: str) -> dict:
    """Return dict with published, modified, and source labels."""
    out: dict = {"published": None, "modified": None, "source": None}
    for pat, label in DATE_PATTERNS:
        for m in pat.finditer(html):
            d = parse_iso_date(m.group(1))
            if d is None:
                continue
            if "modified" in label and out["modified"] is None:
                out["modified"] = d.isoformat()
                out["source"] = out["source"] or label
            elif "published" in label and out["published"] is None:
                out["published"] = d.isoformat()
                out["source"] = out["source"] or label
            elif label == "time_datetime" and out["published"] is None:
                out["published"] = d.isoformat()
                out["source"] = out["source"] or label
    return out


# ---------- GSC URL inspection -----------------------------------------------

def inspect_url(svc, site: str, url: str) -> dict:
    """Call urlInspection.index.inspect. Returns the inspectionResult dict or {}."""
    try:
        body = {"inspectionUrl": url, "siteUrl": site}
        resp = svc.urlInspection().index().inspect(body=body).execute()
        return resp.get("inspectionResult", {})
    except Exception as e:
        return {"_error": str(e)[:200]}


def summarise_inspection(insp: dict) -> dict:
    """Compress the verbose inspection response into the fields we score on."""
    if not insp or "_error" in insp:
        return {
            "verdict": None,
            "coverage_state": None,
            "indexing_state": None,
            "last_crawl_time": None,
            "google_canonical": None,
            "user_canonical": None,
            "error": insp.get("_error") if insp else None,
        }
    idx = insp.get("indexStatusResult", {}) or {}
    return {
        "verdict": idx.get("verdict"),
        "coverage_state": idx.get("coverageState"),
        "indexing_state": idx.get("indexingState"),
        "last_crawl_time": idx.get("lastCrawlTime"),
        "google_canonical": idx.get("googleCanonical"),
        "user_canonical": idx.get("userCanonical"),
        "error": None,
    }


# ---------- main flow --------------------------------------------------------

def score(candidate: dict, today: dt.date, content_type: str) -> dict:
    flags: list[str] = []

    # Pick the best date we have: modified > published > sitemap lastmod
    date_str = (candidate["dates"].get("modified")
                or candidate["dates"].get("published")
                or candidate.get("sitemap_lastmod"))
    age_days = None
    if date_str:
        try:
            d = dt.date.fromisoformat(date_str[:10])
            age_days = (today - d).days
        except ValueError:
            pass

    stale_flag, stale_at, aging_at = staleness_for(content_type, age_days)
    if stale_flag:
        flags.append(stale_flag)

    insp = candidate["indexing"]
    cov = (insp.get("coverage_state") or "").lower()
    verdict = (insp.get("verdict") or "").lower()
    if verdict == "fail" or "not in index" in cov or "discovered" in cov or ("crawled" in cov and "not indexed" in cov):
        flags.append("not_indexed")
    elif verdict == "neutral" or any(k in cov for k in ["alternate", "duplicate", "soft 404", "redirect"]):
        flags.append("index_warning")

    if candidate.get("ctr", {}).get("ctr_decay"):
        flags.append("ctr_decay")

    # Priority: not_indexed > stale > ctr_decay > aging > index_warning
    priority = 9
    if "not_indexed" in flags:
        priority = 1
    elif "stale" in flags:
        priority = 2
    elif "ctr_decay" in flags:
        priority = 2
    elif "aging" in flags:
        priority = 3
    elif "index_warning" in flags:
        priority = 3

    # Apply BVS override: if the partial BVS is already <= 1, drop priority to 4.
    # Layer 2 will revisit this once the SERP components are filled in, but the
    # Python heuristic catches obvious zero-business URLs early.
    bvs = candidate.get("bvs_block", {}).get("bvs")
    if bvs is not None and bvs <= 1:
        priority = max(priority, 4)

    return {
        "flags": flags,
        "age_days": age_days,
        "priority": priority,
        "staleness_band": {"content_type": content_type, "stale_at": stale_at, "aging_at": aging_at},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--site", default=os.environ.get("REFRESH_SITE", "https://www.your-site.com/"))
    p.add_argument("--include", default=os.environ.get("REFRESH_INCLUDE", "/blog/"),
                   help="Substring URLs must contain to be considered (e.g. /blog/)")
    p.add_argument("--max-urls", type=int, default=int(os.environ.get("REFRESH_MAX_URLS", "60")))
    args = p.parse_args()

    site = args.site
    print(f"Site: {site}")
    print(f"Include filter: {args.include!r}")
    print(f"Max URLs: {args.max_urls}")

    sitemaps = discover_sitemaps(site)
    if not sitemaps:
        print(f"ERROR: could not find a sitemap for {site}", file=sys.stderr)
        return 1
    print(f"Sitemaps: {sitemaps}")

    all_urls: list[dict] = []
    for sm in sitemaps:
        all_urls.extend(expand_sitemap(sm))
    print(f"Sitemap URLs total: {len(all_urls)}")

    # Filter
    filtered = [u for u in all_urls if args.include in u["loc"]]
    print(f"After include filter: {len(filtered)}")
    filtered = filtered[: args.max_urls]
    print(f"After max-urls cap: {len(filtered)}")

    # GSC client
    print("Authenticating GSC...")
    try:
        svc = get_gsc_service()
    except Exception as e:
        print(f"ERROR: GSC auth failed: {e}", file=sys.stderr)
        return 1

    # Site-config drives content-type-aware staleness, plus services tokens for BVS.
    site_cfg = read_site_config(ROOT)
    content_type = site_cfg["content_type"]
    services_tokens = read_services_tokens(ROOT)
    print(f"Content type (from site-config): {content_type} "
          f"-> stale at {STALENESS_BANDS[content_type][0]}d, aging at {STALENESS_BANDS[content_type][1]}d")
    print(f"Money-page tokens loaded: {len(services_tokens)}")

    today = dt.date.today()
    candidates: list[dict] = []
    for i, u in enumerate(filtered, 1):
        loc = u["loc"]
        print(f"[{i:3d}/{len(filtered)}] {loc}")
        # Date extraction
        dates = {"published": None, "modified": None, "source": None}
        try:
            html = fetch_text(loc)
            dates = extract_dates(html)
        except Exception as e:
            print(f"  fetch failed: {e}")
        # GSC inspection
        insp = summarise_inspection(inspect_url(svc, site, loc))
        # GSC searchAnalytics 28d vs 28d (skipped if URL inspection errored — likely auth/quota).
        ctr_block = {"current": None, "previous": None, "ctr_decay": False, "ctr_change_pct": None, "impr_change_pct": None}
        if not insp.get("error"):
            try:
                raw = gsc_ctr_28d(svc, site, loc, today)
                decay = ctr_decay_flag(raw)
                ctr_block = {**raw, **decay}
            except Exception as e:
                ctr_block["_error"] = str(e)[:200]
        # Partial BVS (layer-2 prompt completes the SERP components).
        bvs_block = partial_bvs(loc, target_keyword=None, services_tokens=services_tokens)

        c = {
            "url": loc,
            "sitemap_lastmod": u.get("lastmod"),
            "dates": dates,
            "indexing": insp,
            "ctr": ctr_block,
            "bvs_block": bvs_block,
        }
        c.update(score(c, today, content_type))
        candidates.append(c)

    # Sort: priority asc, then oldest first
    candidates.sort(key=lambda c: (c.get("priority", 9), -(c.get("age_days") or 0)))

    flagged = [c for c in candidates if c.get("flags")]
    out = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": site,
        "include_filter": args.include,
        "content_type": content_type,
        "staleness_band": {
            "content_type": content_type,
            "stale_at_days": STALENESS_BANDS[content_type][0],
            "aging_at_days": STALENESS_BANDS[content_type][1],
        },
        "totals": {
            "urls_evaluated": len(candidates),
            "urls_flagged": len(flagged),
            "by_flag": {
                "not_indexed":   sum(1 for c in candidates if "not_indexed" in c["flags"]),
                "index_warning": sum(1 for c in candidates if "index_warning" in c["flags"]),
                "stale":         sum(1 for c in candidates if "stale" in c["flags"]),
                "aging":         sum(1 for c in candidates if "aging" in c["flags"]),
                "ctr_decay":     sum(1 for c in candidates if "ctr_decay" in c["flags"]),
            },
            "bvs_partial_distribution": {
                "8_to_10": sum(1 for c in candidates if (c.get("bvs_block") or {}).get("bvs", 0) >= 8),
                "5_to_7":  sum(1 for c in candidates if 5 <= (c.get("bvs_block") or {}).get("bvs", 0) <= 7),
                "2_to_4":  sum(1 for c in candidates if 2 <= (c.get("bvs_block") or {}).get("bvs", 0) <= 4),
                "0_to_1":  sum(1 for c in candidates if (c.get("bvs_block") or {}).get("bvs", 0) <= 1),
            },
        },
        "candidates": candidates,
    }

    out_path = ROOT / "state" / "refresh-candidates.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path} ({len(candidates)} candidates, {len(flagged)} flagged)")

    # Raw markdown report (b-roll)
    raw = ROOT / "reports" / f"{today}-refresh-raw.md"
    lines = [
        f"# Refresh raw scan, {site}, {today}",
        "",
        f"- URLs evaluated: {len(candidates)}",
        f"- Flagged: {len(flagged)}",
        "",
        "## Counts by flag",
    ]
    for f, n in out["totals"]["by_flag"].items():
        lines.append(f"- {f}: {n}")
    lines += ["", "## Top 30 flagged URLs", "",
              "| URL | Flags | Age (d) | Coverage |",
              "| --- | --- | ---: | --- |"]
    for c in flagged[:30]:
        cov = c["indexing"].get("coverage_state") or "-"
        lines.append(
            f"| `{c['url']}` | {', '.join(c['flags'])} | {c.get('age_days') if c.get('age_days') is not None else '-'} | {cov} |"
        )
    raw.write_text("\n".join(lines) + "\n")
    print(f"Wrote {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
