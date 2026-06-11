#!/usr/bin/env python3
"""Render the unified Four Systems dashboard.

Single self-contained HTML file with five tabs (Overview, Keywords, Content
Queue, Vital Signs, Refresh Queue), terminal-grade dark aesthetic, and inline
rendering of the latest vital-signs classification markdown report.

Inputs (all optional, missing files render as empty states):
  state/keyword-bank.json      (System 1)
  state/content-queue.json     (System 2)
  state/vital-signs-queue.json (System 3 layer 1)
  state/refresh-queue.json     (System 4)
  state/agent-log.json         (recent runs for the Overview activity feed)
  reports/<latest>-vital-signs.md (System 3 layer 2 classification, embedded)

Outputs:
  output/keywords/dashboard.html        (overwritten each run)
  output/keywords/<date>-dashboard.html (dated snapshot)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "state" / "keyword-bank.json"
QUEUE = ROOT / "state" / "content-queue.json"
ONSITE = ROOT / "state" / "onsite-audit.json"
CANDIDATES = ROOT / "state" / "refresh-candidates.json"
REFRESH = ROOT / "state" / "refresh-queue.json"
AGENT_LOG = ROOT / "state" / "agent-log.json"
SITE_CONFIG = ROOT / "context" / "site-config.md"
REPORTS_DIR = ROOT / "reports"
OUT_DIR = ROOT / "output" / "keywords"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATE = dt.date.today().isoformat()
NOW = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
# Branding shown in the dashboard header. Override per project by editing
# these two constants, or set the SEO_BRAND_NAME / SEO_BRAND_WORDMARK env vars.
BRAND_NAME = os.environ.get("SEO_BRAND_NAME", "easygrowth")
BRAND_WORDMARK = os.environ.get("SEO_BRAND_WORDMARK", "easygrowth.fr")

# CTA presentation. Controlled without touching agents via SEO_CTA_STYLE:
#   popup  -> only the fixed bottom-right card
#   banner -> only the in-flow full-width band
#   both   -> both (default)
#   none   -> neither
CTA_STYLE = os.environ.get("SEO_CTA_STYLE", "both").strip().lower()
if CTA_STYLE not in ("popup", "banner", "both", "none"):
    CTA_STYLE = "both"

ZCAL_URL = "https://zcal.co/i/DRmQAADm"


# ----------------------------- i18n -----------------------------------------
# UI chrome strings only (never data). French is the baked default rendered into
# the HTML; the EN column feeds the client-side I18N object so setLang('en') can
# swap textContent. Keys must stay identical across fr and en.
I18N = {
    "tab_overview":   {"fr": "vue d'ensemble",    "en": "overview"},
    "tab_keywords":   {"fr": "mots-cles",         "en": "keywords"},
    "tab_queue":      {"fr": "file de contenu",   "en": "content queue"},
    "tab_onsite":     {"fr": "audit onsite",      "en": "onsite audit"},
    "tab_refresh":    {"fr": "file de refresh",   "en": "refresh queue"},

    "last_updated":   {"fr": "DERNIERE MAJ",      "en": "LAST UPDATED"},
    "brand_sub":      {"fr": "rapport SEO",       "en": "SEO report"},

    # Overview
    "stat_kw_bank":   {"fr": "Mots-cles en banque",      "en": "Keywords in bank"},
    "stat_posts":     {"fr": "Articles ecrits / en file","en": "Posts written / queued"},
    "stat_onsite_verdict": {"fr": "Verdict sante onsite","en": "Onsite health verdict"},
    "stat_refresh":   {"fr": "Pages a rafraichir",       "en": "Pages flagged for refresh"},
    "panel_recent":   {"fr": "Activite recente",         "en": "Recent activity"},
    "ts_last12":      {"fr": "12 derniers runs",         "en": "last 12 runs"},
    "th_agent":       {"fr": "Agent",            "en": "Agent"},
    "th_status":      {"fr": "Statut",           "en": "Status"},
    "th_duration":    {"fr": "Duree",            "en": "Duration"},
    "th_timestamp":   {"fr": "Horodatage (UTC)", "en": "Timestamp (UTC)"},
    "empty_no_runs":  {"fr": "Aucun run enregistre pour l'instant.", "en": "No runs logged yet."},

    # Keywords
    "stat_in_bank":   {"fr": "En banque",        "en": "In bank"},
    "stat_skip_zero": {"fr": "Skip / zero-click","en": "Skip / zero-click"},
    "panel_kw_bank":  {"fr": "Banque de mots-cles", "en": "Keyword bank"},
    "kw_sorted_suffix": {"fr": "entrees &middot; triees par BVS &darr; volume &darr;",
                         "en": "entries &middot; sorted by BVS &darr; volume &darr;"},
    "panel_seeds":    {"fr": "Seeds recherches", "en": "Seeds researched"},
    "th_keyword":     {"fr": "Mot-cle",          "en": "Keyword"},
    "th_intent":      {"fr": "Intention",        "en": "Intent"},
    "th_volume":      {"fr": "Volume",           "en": "Volume"},
    "th_fanout":      {"fr": "Parent fan-out",   "en": "Fan-out parent"},
    "th_coverage":    {"fr": "Couverture",       "en": "Coverage"},
    "th_seed":        {"fr": "Seed",             "en": "Seed"},
    "empty_no_keywords": {"fr": "Aucun mot-cle pour l'instant. Lance le skill keyword-researcher.",
                          "en": "No keywords yet. Run the keyword-researcher skill."},
    "empty_no_seeds": {"fr": "Aucun seed recherche pour l'instant.", "en": "No seeds researched yet."},

    # Content queue
    "stat_queued":      {"fr": "En file",       "en": "Queued"},
    "stat_in_progress": {"fr": "En cours",      "en": "In progress"},
    "stat_written":     {"fr": "Ecrits",        "en": "Written"},
    "stat_needs_review":{"fr": "A relire",      "en": "Needs review"},
    "stat_skipped":     {"fr": "Ignores",       "en": "Skipped"},
    "empty_no_queue":   {"fr": "Aucun element en file. Lance le Systeme 1 pour remplir.",
                         "en": "No items queued. Run System 1 to populate."},
    "qc_primary":   {"fr": "primaire",  "en": "primary"},
    "qc_vol":       {"fr": "vol",       "en": "vol"},
    "qc_words":     {"fr": "mots",      "en": "words"},
    "qc_money":     {"fr": "money page","en": "money page"},
    "qc_view_post": {"fr": "voir l'article &nearr;", "en": "view post &nearr;"},
    "qc_fanout":    {"fr": "Cluster fan-out",        "en": "Fan-out cluster"},
    "qc_notes":     {"fr": "Notes pour le redacteur","en": "Notes for writer"},
    "qc_internal":  {"fr": "Liens internes cibles",  "en": "Internal link targets"},
    "qc_external":  {"fr": "Candidats d'autorite externe", "en": "External authority candidates"},
    "qc_lifecycle": {"fr": "Cycle de vie",   "en": "Lifecycle"},
    "qc_queued":    {"fr": "en file",        "en": "queued"},
    "qc_written":   {"fr": "ecrit",          "en": "written"},
    "qc_slug":      {"fr": "slug",           "en": "slug"},
    "qc_none":      {"fr": "aucun",          "en": "none"},

    # Onsite audit
    "empty_no_onsite": {"fr": "Aucun audit onsite pour l'instant. Lance le skill onsite-audit ou planifie l'agent pour remplir.",
                        "en": "No onsite audit yet. Run the onsite-audit skill or schedule the agent to populate."},
    "stat_site_verdict": {"fr": "Verdict du site", "en": "Site verdict"},
    "stat_performance":  {"fr": "Performance",     "en": "Performance"},
    "stat_accessibility":{"fr": "Accessibilite",   "en": "Accessibility"},
    "stat_best_practices":{"fr": "Bonnes pratiques","en": "Best Practices"},
    "stat_seo":          {"fr": "SEO",             "en": "SEO"},
    "panel_lighthouse":  {"fr": "Audit Lighthouse + on-page", "en": "Lighthouse + on-page audit"},
    "panel_money_alerts":{"fr": "Alertes money page",        "en": "Money page alerts"},
    "panel_concerns":    {"fr": "Preoccupations strategiques","en": "Strategic concerns"},
    "ts_bvs_context":    {"fr": "contexte BVS, pas technique", "en": "BVS context, not technical"},
    "concern_target_kw": {"fr": "mot-cle cible :", "en": "target keyword:"},
    "panel_ai_policy":   {"fr": "Politique crawlers IA &amp; llms.txt", "en": "AI crawler policy &amp; llms.txt"},
    "ai_no_robots":      {"fr": "aucune regle robots.txt capturee", "en": "no robots.txt rules captured"},
    "ai_present":        {"fr": "present", "en": "present"},
    "ai_missing":        {"fr": "absent",  "en": "missing"},
    "panel_template":    {"fr": "Problemes au niveau template", "en": "Template-level issues"},
    "ts_fix_once":       {"fr": "corrige une fois, eleve plusieurs pages", "en": "fix once, lift many pages"},
    "th_issue":          {"fr": "Probleme",     "en": "Issue"},
    "th_audit_id":       {"fr": "ID audit Lighthouse", "en": "Lighthouse audit ID"},
    "th_affected":       {"fr": "URLs affectees","en": "Affected URLs"},
    "th_severity":       {"fr": "Severite",      "en": "Severity"},
    "empty_no_template": {"fr": "Aucun probleme au niveau template.", "en": "No template-level issues."},
    "empty_no_urls":     {"fr": "Aucune URL auditee.", "en": "No URLs audited."},
    "th_url":            {"fr": "URL",      "en": "URL"},
    "th_verdict":        {"fr": "Verdict",  "en": "Verdict"},
    "th_issues":         {"fr": "Problemes","en": "Issues"},
    "panel_full_report": {"fr": "Rapport complet &amp; prochaines actions recommandees",
                          "en": "Full report &amp; recommended next actions"},
    "empty_no_audit_report": {"fr": "Aucun rapport d'audit pour l'instant.", "en": "No audit report yet."},

    # Refresh queue
    "stat_not_indexed":  {"fr": "Non indexees", "en": "Not indexed"},
    "stat_index_warning":{"fr": "Alerte d'index","en": "Index warning"},
    "stat_stale":        {"fr": "Obsoletes",    "en": "Stale"},
    "stat_ctr_decay":    {"fr": "Chute de CTR", "en": "CTR decay"},
    "stat_aio_loss":     {"fr": "Perte AIO",    "en": "AIO loss"},
    "stat_actions_queued":{"fr": "Actions en file","en": "Actions queued"},
    "panel_layer2":      {"fr": "Couche 2 &middot; actions recommandees", "en": "Layer 2 &middot; recommended actions"},
    "ts_consumed_by":    {"fr": "consomme par vous (ou votre outil de refresh)",
                          "en": "consumed by you (or your refresh tool)"},
    "panel_layer1":      {"fr": "Couche 1 &middot; scan sitemap + indexation GSC",
                          "en": "Layer 1 &middot; sitemap + GSC indexing scan"},
    "ls_urls_evaluated": {"fr": "URLs evaluees", "en": "URLs evaluated"},
    "ls_flagged":        {"fr": "signalees",     "en": "flagged"},
    "panel_classif_report": {"fr": "Rapport de classification complet", "en": "Full classification report"},
    "empty_no_classif":  {"fr": "Aucun rapport de classification pour l'instant.", "en": "No classification report yet."},
    "th_serp_intent":    {"fr": "Intention SERP", "en": "SERP intent"},
    "th_action":         {"fr": "Action",         "en": "Action"},
    "th_primary_flag":   {"fr": "Flag principal",  "en": "Primary flag"},
    "th_age":            {"fr": "Age (j)",         "en": "Age (d)"},
    "th_content_gaps":   {"fr": "Lacunes contenu", "en": "Content gaps"},
    "th_recommendation": {"fr": "Recommandation",  "en": "Recommendation"},
    "th_flags":          {"fr": "Flags",           "en": "Flags"},
    "th_coverage_state": {"fr": "Etat de couverture","en": "Coverage state"},
    "th_last_crawl":     {"fr": "Dernier crawl",   "en": "Last crawl"},
    "empty_no_candidates": {"fr": "Aucun candidat signale. Lance refresh-recommender pour scanner le sitemap et GSC.",
                            "en": "No flagged candidates. Run refresh-recommender to scan the sitemap and GSC."},
    "empty_no_actions":  {"fr": "Aucune action en file pour l'instant. Lance le refresh-recommender (couche 2) apres un scan couche 1.",
                          "en": "No actions queued yet. Run the refresh-recommender (layer 2) after a layer-1 scan."},

    # CTA
    "cta_msg":      {"fr": "Envie d'aller plus loin avec ce systeme, ou un projet d'automatisation ?",
                     "en": "Want to go further with this system, or have an automation project?"},
    "cta_btn":      {"fr": "Prendre rendez-vous", "en": "Book a call"},
}


def t(key: str, *, cls: str = "", el: str = "span") -> str:
    """Render the French default wrapped with data-i18n so the client can swap it.

    cls adds extra classes; el lets callers emit a different inline element.
    The baked text is always the French value (project default).
    """
    fr = I18N[key]["fr"]
    class_attr = f' class="{cls}"' if cls else ""
    return f'<{el} data-i18n="{key}"{class_attr}>{fr}</{el}>'


def i18n_js_object() -> str:
    """Serialize I18N as a compact JS object literal for the in-page dictionary."""
    fr = {k: v["fr"] for k, v in I18N.items()}
    en = {k: v["en"] for k, v in I18N.items()}
    return json.dumps({"fr": fr, "en": en}, ensure_ascii=False)


# ----------------------------- helpers --------------------------------------

def load(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def esc(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s))


def fmt_int(n) -> str:
    if n is None:
        return "&mdash;"
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return esc(n)


def status_pill(status: str) -> str:
    palette = {
        "queued":       ("--lime", "queued"),
        "in_progress":  ("--amber", "in progress"),
        "written":      ("--mint", "written"),
        "needs_review": ("--rose", "needs review"),
        "skipped":      ("--dim", "skipped"),
    }
    var, label = palette.get(status, ("--dim", status or "?"))
    return f'<span class="pill" style="--c:var({var})">{esc(label)}</span>'


def intent_pill(intent: str) -> str:
    palette = {
        "transactional": "--rose",
        "commercial":    "--amber",
        "informational": "--sky",
        "navigational":  "--dim",
    }
    var = palette.get(intent, "--dim")
    return f'<span class="pill" style="--c:var({var})">{esc(intent or "")}</span>'


def flag_chip(flag: str) -> str:
    palette = {
        "decay":               "--rose",
        "dropped_from_top_10": "--rose",
        "stuck_5_15":          "--amber",
        "low_ctr":             "--sky",
        "not_indexed":         "--rose",
        "index_warning":       "--sky",
        "stale":               "--amber",
        "stale_12mo":          "--amber",  # legacy
        "aging":               "--dim",
        "aio_loss":            "--rose",
        "aio_gain":            "--lime",
        "ctr_decay":           "--amber",
    }
    var = palette.get(flag, "--dim")
    label = flag.replace("_", " ")
    return f'<span class="chip" style="--c:var({var})">{esc(label)}</span>'


def bvs_pill(bvs) -> str:
    """Render a BVS 0-10 pill, color-coded by band."""
    if bvs is None:
        return '<span class="dim">&mdash;</span>'
    try:
        n = int(bvs)
    except (ValueError, TypeError):
        return esc(bvs)
    if n >= 8:
        c = "--lime"
    elif n >= 5:
        c = "--amber"
    elif n >= 2:
        c = "--sky"
    else:
        c = "--rose"
    return f'<span class="pill" style="--c:var({c});font-variant-numeric:tabular-nums">BVS {n}</span>'


def trap_chip(item: dict) -> str:
    """Render a zero-click-trap chip when applicable, empty otherwise."""
    if item.get("zero_click_trap") or item.get("strategic_concern") == "zero_click_target":
        signal = item.get("direct_answer_signal") or item.get("skip_reason") or "zero_click"
        return f'<span class="chip" style="--c:var(--rose)" title="{esc(signal)}">zero-click trap</span>'
    return ""


# ----------------------------- markdown to html ------------------------------

def md_to_html(md: str) -> str:
    """Tiny markdown renderer for the patterns the vital-signs reports use:
    h1-h3, paragraphs, unordered lists, simple GFM tables, inline code,
    inline links. Not a general-purpose md parser; just enough for our reports.
    """
    if not md:
        return ""
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    def inline(s: str) -> str:
        s = html.escape(s, quote=False)
        # links: [text](url)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        # backtick code
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # bold
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        # italic
        s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
        return s

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # tables: header row of pipes, then separator, then rows
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*[-:|\s]+\|", lines[i + 1]):
            header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2  # skip header and separator
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header_cells) + "</tr>"
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            out.append(f'<div class="md-table-wrap"><table class="md-table"><thead>{thead}</thead><tbody>{tbody}</tbody></table></div>')
            continue

        # unordered list
        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(it)}</li>" for it in items) + "</ul>")
            continue

        # paragraph (collect until blank line)
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#|-|\|)", lines[i].strip()):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(p.strip() for p in para))}</p>")

    return "\n".join(out)


def find_latest_vital_report() -> Path | None:
    if not REPORTS_DIR.exists():
        return None
    candidates = sorted(REPORTS_DIR.glob("*-vital-signs.md"), reverse=True)
    candidates = [c for c in candidates if "raw" not in c.stem]
    return candidates[0] if candidates else None


PLACEHOLDER_SITES = {"", "your-site.com", "www.your-site.com", "yoursite.com"}


def resolve_site_name(bank: dict) -> str:
    """Resolve the real site name to show in the header subtitle.

    Resolution order:
      1. state/keyword-bank.json -> "site" (non-empty, non-placeholder string)
      2. context/site-config.md  -> first line matching "# Site: <domain>"
      3. BRAND_NAME fallback
    """
    # 1. keyword-bank.json "site" field
    bank_site = bank.get("site") if isinstance(bank, dict) else None
    if isinstance(bank_site, str) and bank_site.strip() \
            and bank_site.strip().lower() not in PLACEHOLDER_SITES:
        return bank_site.strip()

    # 2. context/site-config.md "# Site: <domain>"
    if SITE_CONFIG.exists():
        try:
            for line in SITE_CONFIG.read_text().splitlines():
                m = re.match(r"^\s*#\s*Site:\s*(\S+)", line)
                if m:
                    domain = m.group(1).strip()
                    if domain and domain.lower() not in PLACEHOLDER_SITES:
                        return domain
        except Exception:
            pass

    # 3. fallback
    return BRAND_NAME


# ----------------------------- per-tab renderers -----------------------------

def render_overview_tab(stats: dict, agent_log: list[dict]) -> str:
    verdict_color = {
        "GREEN": "--lime", "AMBER": "--amber", "RED": "--rose",
    }.get(stats.get("onsite_verdict","") or "", "--mint")
    big_stats = [
        ("01", "System 1", t("stat_kw_bank"), stats["kw_total"], "keywords", "--lime"),
        ("02", "System 2", t("stat_posts"),
         f'{stats["posts_written"]} <span style="opacity:.4;font-size:.5em;font-style:normal">/</span> {stats["queue_active"]}',
         "queue", "--mint"),
        ("03", "System 3", t("stat_onsite_verdict"), stats["onsite_verdict"], "onsite", verdict_color),
        ("04", "System 4", t("stat_refresh"), stats["refresh_queued"], "refresh", "--rose"),
    ]
    cards = "\n".join(
        f'''<a class="hero-card" data-tab="{k}" data-anim-delay="{idx*60}" href="#{k}">
              <div class="hero-card-head">
                <span class="hero-card-num">{num}</span>
                <span class="hero-card-name">{name}</span>
              </div>
              <div class="hero-card-stat" style="--c:var({color})">{val}</div>
              <div class="hero-card-label">{label}</div>
              <div class="hero-card-arrow">&rarr;</div>
            </a>'''
        for idx, (num, name, label, val, k, color) in enumerate(big_stats)
    )

    log_rows = "".join(
        f'''<tr>
              <td><span class="dot" style="--c:var({"--rose" if e.get("status")=="error" else "--mint"})"></span></td>
              <td><code>{esc(e.get("agent","?"))}</code></td>
              <td>{esc(e.get("status","?"))}</td>
              <td class="dim">{esc(e.get("duration_seconds","?"))}s</td>
              <td class="dim mono-sm">{esc(e.get("timestamp","")[:19].replace("T"," "))}</td>
            </tr>'''
        for e in agent_log[-12:][::-1]
    ) or f'<tr><td colspan="5" class="empty">{t("empty_no_runs")}</td></tr>'

    return f'''
<section class="tab-pane" id="tab-overview" data-tab-pane="overview">
  <div class="hero-grid">
    {cards}
  </div>
  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_recent")} {t("ts_last12", cls="ts")}</h2>
    </div>
    <table class="data-table">
      <thead><tr><th></th><th>{t("th_agent")}</th><th>{t("th_status")}</th><th>{t("th_duration")}</th><th>{t("th_timestamp")}</th></tr></thead>
      <tbody>{log_rows}</tbody>
    </table>
  </div>
</section>'''


def render_keywords_tab(bank: dict) -> str:
    keywords = bank.get("keywords", [])

    def _bvs_sort_key(k):
        # Skip items at the bottom; otherwise sort by BVS desc, then priority asc, then volume desc.
        prio = k.get("priority")
        if prio == "skip":
            return (3, 99, 0)
        bvs = k.get("bvs")
        bvs_key = -bvs if isinstance(bvs, (int, float)) else 0
        return (0, prio or 99, bvs_key, -(k.get("volume") or 0))

    keywords_sorted = sorted(keywords, key=_bvs_sort_key)

    p_counts = {1: 0, 2: 0, 3: 0, "skip": 0}
    for k in keywords:
        p = k.get("priority")
        if p in p_counts:
            p_counts[p] += 1

    bvs_bands = {"8_to_10": 0, "5_to_7": 0, "2_to_4": 0, "0_to_1": 0}
    for k in keywords:
        b = k.get("bvs")
        if not isinstance(b, (int, float)):
            continue
        if b >= 8:   bvs_bands["8_to_10"] += 1
        elif b >= 5: bvs_bands["5_to_7"]  += 1
        elif b >= 2: bvs_bands["2_to_4"]  += 1
        else:        bvs_bands["0_to_1"]  += 1

    def _kw_row(k):
        prio = k.get("priority")
        prio_html = (
            f'<span class="pill" style="--c:var(--rose)" title="{esc(k.get("skip_reason") or "skip")}">skip</span>'
            if prio == "skip"
            else f'<span class="prio prio-{prio or 9}">{esc(prio or "-")}</span>'
        )
        return f'''<tr>
              <td class="mono">{esc(k.get("keyword"))} {trap_chip(k)}</td>
              <td>{intent_pill(k.get("intent",""))}</td>
              <td class="r">{fmt_int(k.get("volume"))}</td>
              <td class="r">{esc(k.get("kd")) or "&mdash;"}</td>
              <td class="c">{bvs_pill(k.get("bvs"))}</td>
              <td class="c">{prio_html}</td>
              <td class="dim">{esc(k.get("fan_out_parent"))}</td>
              <td>{f'<a href="{esc(k["covered_by"])}" target="_blank" class="link-sm">covered &nearr;</a>' if k.get("covered_by") else '<span class="dim">&mdash;</span>'}</td>
              <td class="dim mono-sm">{esc(k.get("seed",""))}</td>
            </tr>'''

    rows = "".join(_kw_row(k) for k in keywords_sorted) or \
        f'<tr><td colspan="9" class="empty">{t("empty_no_keywords")}</td></tr>'

    seeds = bank.get("seeds_researched", [])
    seeds_html = "".join(
        f'<li><span class="mono">{esc(s["seed"])}</span><span class="dim mono-sm"> &middot; {esc(s["last_researched"])}</span></li>'
        for s in seeds
    ) or f'<li class="dim">{t("empty_no_seeds")}</li>'

    return f'''
<section class="tab-pane" id="tab-keywords" data-tab-pane="keywords">
  <div class="stat-row">
    <div class="stat"><div class="stat-num">{len(keywords)}</div><div class="stat-label">{t("stat_in_bank")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--lime)">{bvs_bands["8_to_10"]}</div><div class="stat-label">BVS 8-10</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--amber)">{bvs_bands["5_to_7"]}</div><div class="stat-label">BVS 5-7</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--sky)">{bvs_bands["2_to_4"]}</div><div class="stat-label">BVS 2-4</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--rose)">{bvs_bands["0_to_1"] + p_counts["skip"]}</div><div class="stat-label">{t("stat_skip_zero")}</div></div>
  </div>
  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_kw_bank")}</h2>
      <span class="ts">{len(keywords)} {t("kw_sorted_suffix")}</span>
    </div>
    <table class="data-table">
      <thead><tr>
        <th>{t("th_keyword")}</th><th>{t("th_intent")}</th><th class="r">{t("th_volume")}</th><th class="r">KD</th>
        <th class="c">BVS</th><th class="c">P</th><th>{t("th_fanout")}</th><th>{t("th_coverage")}</th><th>{t("th_seed")}</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="panel">
    <div class="panel-head"><h2 class="panel-title">{t("panel_seeds")}</h2></div>
    <ul class="seed-list">{seeds_html}</ul>
  </div>
</section>'''


def render_queue_tab(queue: dict) -> str:
    items = queue.get("items", [])
    order = {"needs_review": 0, "queued": 1, "in_progress": 2, "written": 3, "skipped": 4, "skipped_zero_click_trap": 5}
    # Sort: status first, then BVS desc within each status group, then queued_at asc.
    def _key(x):
        bvs = x.get("bvs")
        return (
            order.get(x.get("status",""), 9),
            -bvs if isinstance(bvs, (int, float)) else 0,
            x.get("queued_at",""),
        )
    items_sorted = sorted(items, key=_key)

    counts = {s: sum(1 for i in items if i.get("status") == s) for s in
              ["queued","in_progress","written","needs_review","skipped"]}

    cards = "\n".join(_render_queue_card(i) for i in items_sorted) or \
        f'<div class="empty-state">{t("empty_no_queue")}</div>'

    return f'''
<section class="tab-pane" id="tab-queue" data-tab-pane="queue">
  <div class="stat-row">
    <div class="stat"><div class="stat-num" style="--c:var(--lime)">{counts["queued"]}</div><div class="stat-label">{t("stat_queued")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--amber)">{counts["in_progress"]}</div><div class="stat-label">{t("stat_in_progress")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--mint)">{counts["written"]}</div><div class="stat-label">{t("stat_written")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--rose)">{counts["needs_review"]}</div><div class="stat-label">{t("stat_needs_review")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--dim)">{counts["skipped"]}</div><div class="stat-label">{t("stat_skipped")}</div></div>
  </div>
  <div class="queue-stack">{cards}</div>
</section>'''


def _render_queue_card(item: dict) -> str:
    fan_out = "".join(f'<li>{esc(k)}</li>' for k in item.get("fan_out_cluster", []))
    internal = "".join(
        f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></li>'
        for u in item.get("internal_link_targets", [])
    )
    external = "".join(
        f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></li>'
        for u in item.get("external_authority_candidates", [])
    )
    post_link = ""
    if item.get("post_url"):
        post_link = f'<a class="link-sm" href="{esc(item["post_url"])}" target="_blank">{t("qc_view_post")}</a>'

    title = item.get("suggested_title") or item.get("primary_keyword", "")
    primary = item.get("primary_keyword", "")
    mp_target = item.get("money_page_target")
    mp_html = (
        f'<span>{t("qc_money", cls="dim")} <a href="{esc(mp_target)}" target="_blank" class="link-sm">{esc(mp_target)}</a></span>'
        if mp_target else ""
    )
    return f'''
<details class="queue-card">
  <summary>
    <div class="queue-card-meta">
      <code class="queue-id">{esc(item.get("id",""))}</code>
      {status_pill(item.get("status",""))}
      {intent_pill(item.get("intent",""))}
      {bvs_pill(item.get("bvs"))}
      {trap_chip(item)}
    </div>
    <h3 class="queue-card-title">{esc(title)}</h3>
    <div class="queue-card-stats">
      <span>{t("qc_primary", cls="dim")} <code>{esc(primary)}</code></span>
      <span>{t("qc_vol", cls="dim")} <strong>{fmt_int(item.get("volume"))}</strong></span>
      <span><span class="dim">kd</span> <strong>{esc(item.get("kd")) or "&mdash;"}</strong></span>
      <span>{t("qc_words", cls="dim")} <strong>{esc(item.get("target_word_count")) or "&mdash;"}</strong></span>
      {mp_html}
      {post_link}
    </div>
  </summary>
  <div class="queue-card-body">
    <div class="qcb-col">
      <h4>{t("qc_fanout")}</h4>
      <ul class="dense">{fan_out or f'<li class="dim">{t("qc_none")}</li>'}</ul>
      <h4>{t("qc_notes")}</h4>
      <p>{esc(item.get("notes",""))}</p>
    </div>
    <div class="qcb-col">
      <h4>{t("qc_internal")}</h4>
      <ul class="dense link-list">{internal or f'<li class="dim">{t("qc_none")}</li>'}</ul>
      <h4>{t("qc_external")}</h4>
      <ul class="dense link-list">{external or f'<li class="dim">{t("qc_none")}</li>'}</ul>
      <h4>{t("qc_lifecycle")}</h4>
      <dl class="meta-dl">
        <dt>{t("qc_queued")}</dt><dd>{esc(item.get("queued_at") or "&mdash;")}</dd>
        <dt>{t("qc_written")}</dt><dd>{esc(item.get("written_at") or "&mdash;")}</dd>
        <dt>{t("qc_slug")}</dt><dd><code>{esc(item.get("suggested_slug") or "")}</code></dd>
      </dl>
    </div>
  </div>
</details>'''


def verdict_pill(v: str) -> str:
    palette = {
        "green": "--lime", "amber": "--amber", "red": "--rose", "error": "--rose",
    }
    var = palette.get(v, "--dim")
    return f'<span class="pill" style="--c:var({var})">{esc(v or "?")}</span>'


def score_cell(n) -> str:
    if n is None:
        return '<span class="dim">&mdash;</span>'
    try:
        n = int(n)
    except (ValueError, TypeError):
        return esc(n)
    if n >= 90:
        c = "--lime"
    elif n >= 70:
        c = "--amber"
    else:
        c = "--rose"
    return f'<strong style="color:var({c})">{n}</strong>'


def render_onsite_tab(onsite: dict) -> str:
    audited = onsite.get("audited_urls", []) if onsite else []
    rollup = onsite.get("site_rollup", {}) if onsite else {}
    avg = rollup.get("avg_scores", {})
    template_issues = rollup.get("template_issues", [])
    money_alerts = rollup.get("money_page_alerts", [])
    site_verdict = rollup.get("verdict", "")
    last_scan = onsite.get("generated_at", "")

    if not onsite:
        body = f'<div class="empty-state">{t("empty_no_onsite")}</div>'
        return f'<section class="tab-pane" data-tab-pane="onsite">{body}</section>'

    # Per-URL rows
    rows = "".join(_render_onsite_row(u) for u in audited) or \
        f'<tr><td colspan="9" class="empty">{t("empty_no_urls")}</td></tr>'

    # Template issues
    template_rows = "".join(
        f'''<tr>
              <td>{esc(ti.get("title") or ti.get("id"))}</td>
              <td><code>{esc(ti.get("id"))}</code></td>
              <td class="c">{esc(ti.get("affected_urls"))}</td>
              <td>{flag_chip(ti.get("severity","medium"))}</td>
            </tr>'''
        for ti in template_issues
    ) or f'<tr><td colspan="4" class="empty">{t("empty_no_template")}</td></tr>'

    # Money page alerts
    money_html = ""
    if money_alerts:
        items = "".join(
            f'''<li><a href="{esc(m.get("url"))}" target="_blank" class="mono-sm link-sm">{esc(m.get("url",""))}</a>
                  <span class="dim"> &middot; </span>{verdict_pill(m.get("verdict",""))}
                  <span class="dim"> &middot; </span>{esc(m.get("main_issue"))}</li>'''
            for m in money_alerts
        )
        money_html = f'<div class="panel"><div class="panel-head"><h2 class="panel-title">{t("panel_money_alerts")}</h2></div><ul class="dense" style="padding:16px 20px">{items}</ul></div>'

    # Find the latest onsite-audit markdown report and embed it
    report_path = None
    if REPORTS_DIR.exists():
        candidates = sorted(REPORTS_DIR.glob("*-onsite-audit.md"), reverse=True)
        report_path = candidates[0] if candidates else None
    if report_path:
        report_html = md_to_html(report_path.read_text())
        report_meta = f'<span class="ts">{esc(report_path.name)}</span>'
    else:
        report_html = f'<p class="empty">{t("empty_no_audit_report")}</p>'
        report_meta = ""

    # Strategic concerns (BVS context, not technical)
    concerns = [u for u in audited if (u.get("bvs_context") or {}).get("strategic_concern")]
    concerns_html = ""
    if concerns:
        items = "".join(
            f'''<li><a href="{esc(c.get("url"))}" target="_blank" class="mono-sm link-sm">{esc(c.get("url",""))}</a>
                  <span class="dim"> &middot; </span>{bvs_pill((c.get("bvs_context") or {}).get("bvs"))}
                  <span class="dim"> &middot; </span>{trap_chip(c.get("bvs_context") or {})}
                  <span class="dim"> &middot; </span>{t("concern_target_kw", cls="dim")} <code>{esc((c.get("bvs_context") or {}).get("target_keyword") or "&mdash;")}</code></li>'''
            for c in concerns
        )
        concerns_html = (
            f'<div class="panel"><div class="panel-head">'
            f'<h2 class="panel-title">{t("panel_concerns")} {t("ts_bvs_context", cls="ts")}</h2></div>'
            f'<ul class="dense" style="padding:16px 20px">{items}</ul></div>'
        )

    # AI crawler policy + llms.txt rollup
    ai_pol = rollup.get("ai_crawler_policy") or {}
    llms_present = (rollup.get("llms_txt") or {}).get("present")
    llms_full_present = (rollup.get("llms_full_txt") or {}).get("present")
    ai_html = ""
    if ai_pol or llms_present is not None:
        def _pol_chip(bot, state):
            c = {"allowed": "--lime", "disallowed": "--rose", "not_mentioned": "--dim"}.get(state, "--dim")
            return f'<span class="chip" style="--c:var({c})">{esc(bot)}: {esc(state)}</span>'
        bots_html = " ".join(_pol_chip(b, s) for b, s in ai_pol.items()) or f'<span class="dim">{t("ai_no_robots")}</span>'
        llms_lbl = I18N["ai_present"]["fr"] if llms_present else I18N["ai_missing"]["fr"]
        llms_full_lbl = I18N["ai_present"]["fr"] if llms_full_present else I18N["ai_missing"]["fr"]
        ll_html = (
            f'<span class="chip" style="--c:var({"--lime" if llms_present else "--dim"})">/llms.txt: '
            f'<span data-i18n="{"ai_present" if llms_present else "ai_missing"}" style="margin-left:3px">{llms_lbl}</span></span> '
            f'<span class="chip" style="--c:var({"--lime" if llms_full_present else "--dim"})">/llms-full.txt: '
            f'<span data-i18n="{"ai_present" if llms_full_present else "ai_missing"}" style="margin-left:3px">{llms_full_lbl}</span></span>'
        )
        ai_html = (
            f'<div class="panel"><div class="panel-head">'
            f'<h2 class="panel-title">{t("panel_ai_policy")}</h2></div>'
            f'<div style="padding:16px 20px;display:flex;flex-wrap:wrap;gap:8px;align-items:center">{bots_html}</div>'
            f'<div style="padding:0 20px 16px 20px">{ll_html}</div></div>'
        )

    return f'''
<section class="tab-pane" data-tab-pane="onsite">
  <div class="stat-row">
    <div class="stat"><div class="stat-num" style="--c:var({"--lime" if site_verdict=="green" else "--amber" if site_verdict=="amber" else "--rose"})">{esc(site_verdict.upper() if site_verdict else "&mdash;")}</div><div class="stat-label">{t("stat_site_verdict")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--{'lime' if (avg.get('performance') or 0) >= 90 else 'amber' if (avg.get('performance') or 0) >= 70 else 'rose'})">{esc(avg.get("performance","&mdash;"))}</div><div class="stat-label">{t("stat_performance")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--{'lime' if (avg.get('accessibility') or 0) >= 90 else 'amber' if (avg.get('accessibility') or 0) >= 70 else 'rose'})">{esc(avg.get("accessibility","&mdash;"))}</div><div class="stat-label">{t("stat_accessibility")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--{'lime' if (avg.get('best_practices') or 0) >= 90 else 'amber' if (avg.get('best_practices') or 0) >= 70 else 'rose'})">{esc(avg.get("best_practices","&mdash;"))}</div><div class="stat-label">{t("stat_best_practices")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--{'lime' if (avg.get('seo') or 0) >= 90 else 'amber' if (avg.get('seo') or 0) >= 70 else 'rose'})">{esc(avg.get("seo","&mdash;"))}</div><div class="stat-label">{t("stat_seo")}</div></div>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_lighthouse")} <span class="ts">{esc(len(audited))} URL{"s" if len(audited)!=1 else ""}</span></h2>
      <span class="ts">{esc(last_scan)}</span>
    </div>
    <table class="data-table">
      <thead><tr>
        <th>{t("th_url")}</th><th>{t("th_verdict")}</th>
        <th class="r">Perf</th><th class="r">A11y</th>
        <th class="r">BP</th><th class="r">SEO</th>
        <th class="r">LCP</th><th class="r">CLS</th>
        <th class="r">INP</th>
        <th class="c">BVS</th>
        <th class="r">{t("th_issues")}</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  {concerns_html}
  {ai_html}

  {money_html}

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_template")} {t("ts_fix_once", cls="ts")}</h2>
    </div>
    <table class="data-table">
      <thead><tr><th>{t("th_issue")}</th><th>{t("th_audit_id")}</th><th class="c">{t("th_affected")}</th><th>{t("th_severity")}</th></tr></thead>
      <tbody>{template_rows}</tbody>
    </table>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_full_report")}</h2>
      {report_meta}
    </div>
    <article class="md-content">{report_html}</article>
  </div>
</section>'''


def _render_onsite_row(u: dict) -> str:
    s = u.get("scores", {})
    cwv = u.get("core_web_vitals", {})
    bvs_ctx = u.get("bvs_context") or {}
    issue_count = len(u.get("lighthouse_issues", [])) + len(u.get("onpage_issues", []))
    url = u.get("url", "")
    short = url.replace("https://", "").replace("http://", "").rstrip("/")
    if len(short) > 60:
        short = short[:57] + "..."
    lcp = cwv.get("LCP_ms")
    cls = cwv.get("CLS")
    inp = cwv.get("INP_ms")
    inp_unknown = cwv.get("inp_unknown")

    def _color_for_lcp(ms):
        if ms is None: return "--dim"
        return "--lime" if ms <= 2500 else "--amber" if ms <= 4000 else "--rose"

    def _color_for_cls(v):
        if v is None: return "--dim"
        return "--lime" if v <= 0.1 else "--amber" if v <= 0.25 else "--rose"

    def _color_for_inp(ms):
        if ms is None: return "--dim"
        return "--lime" if ms <= 200 else "--amber" if ms <= 500 else "--rose"

    lcp_html = (f'<strong style="color:var({_color_for_lcp(lcp)})">{lcp/1000:.1f}s</strong>'
                if isinstance(lcp, (int, float)) else '<span class="dim">&mdash;</span>')
    cls_html = (f'<strong style="color:var({_color_for_cls(cls)})">{cls:.3f}</strong>'
                if isinstance(cls, (int, float)) else '<span class="dim">&mdash;</span>')
    if isinstance(inp, (int, float)):
        suffix = ' <span class="dim" title="lab estimate from TBT, no field INP available">(lab)</span>' if inp_unknown else ""
        inp_html = f'<strong style="color:var({_color_for_inp(inp)})">{int(inp)}ms</strong>{suffix}'
    else:
        inp_html = '<span class="dim">&mdash;</span>'

    return f'''<tr>
      <td><a href="{esc(url)}" target="_blank" rel="noopener" class="mono-sm link-sm">{esc(short)}</a> {trap_chip(bvs_ctx)}</td>
      <td>{verdict_pill(u.get("verdict",""))}</td>
      <td class="r">{score_cell(s.get("performance"))}</td>
      <td class="r">{score_cell(s.get("accessibility"))}</td>
      <td class="r">{score_cell(s.get("best_practices"))}</td>
      <td class="r">{score_cell(s.get("seo"))}</td>
      <td class="r">{lcp_html}</td>
      <td class="r">{cls_html}</td>
      <td class="r">{inp_html}</td>
      <td class="c">{bvs_pill(bvs_ctx.get("bvs"))}</td>
      <td class="r dim">{issue_count}</td>
    </tr>'''


def action_chip(action: str) -> str:
    palette = {
        "request_indexing":             "--rose",
        "refresh":                      "--amber",
        "fix_canonical":                "--sky",
        "audit_then_decide":            "--dim",
        "consider_consolidate_or_remove": "--rose",
    }
    var = palette.get(action, "--dim")
    label = action.replace("_", " ")
    return f'<span class="chip" style="--c:var({var})">{esc(label)}</span>'


def compact_list(items, limit: int = 3) -> str:
    if not items:
        return '<span class="dim">&mdash;</span>'
    if isinstance(items, str):
        items = [items]
    shown = [str(i) for i in items[:limit] if i]
    if not shown:
        return '<span class="dim">&mdash;</span>'
    extra = len(items) - len(shown)
    suffix = f'<li class="dim">+{extra} more</li>' if extra > 0 else ""
    return '<ul class="dense mini-list">' + "".join(f"<li>{esc(i)}</li>" for i in shown) + suffix + "</ul>"


def render_refresh_tab(candidates: dict, refresh: dict) -> str:
    # Layer 1: refresh-candidates.json (sitemap + age + GSC indexing flags)
    # Layer 2: refresh-queue.json (Claude-classified actions)
    cand_list = candidates.get("candidates", []) if isinstance(candidates, dict) else []
    by_flag = candidates.get("totals", {}).get("by_flag", {}) if isinstance(candidates, dict) else {}
    urls_evaluated = candidates.get("totals", {}).get("urls_evaluated", 0) if isinstance(candidates, dict) else 0
    last_scan = candidates.get("generated_at", "") if isinstance(candidates, dict) else ""

    refresh_items = refresh.get("items", []) if isinstance(refresh, dict) else []
    by_action = refresh.get("totals", {}).get("by_action", {}) if isinstance(refresh, dict) else {}

    # Raw layer-1 candidates table (only flagged)
    flagged_cands = [c for c in cand_list if c.get("flags")]
    cand_rows = "".join(
        _render_candidate_row(c) for c in flagged_cands[:60]
    ) or f'<tr><td colspan="5" class="empty">{t("empty_no_candidates")}</td></tr>'

    # Sort layer-2 items by priority asc, then BVS desc within the band, then age desc.
    def _refresh_key(i):
        bvs = i.get("bvs")
        return (
            i.get("priority", 9),
            -bvs if isinstance(bvs, (int, float)) else 0,
            -(i.get("age_days") or 0),
        )
    refresh_items_sorted = sorted(refresh_items, key=_refresh_key)

    def _aio_cell(i):
        bits = []
        if i.get("aio_loss"):
            bits.append('<span class="chip" style="--c:var(--rose)">AIO loss</span>')
        if i.get("aio_gain"):
            bits.append('<span class="chip" style="--c:var(--lime)">AIO gain</span>')
        if i.get("ctr_decay"):
            cur = i.get("ctr_28d_current")
            prv = i.get("ctr_28d_prior")
            tip = f"CTR {prv*100:.1f}% -> {cur*100:.1f}%" if isinstance(cur, (int, float)) and isinstance(prv, (int, float)) else "CTR drop"
            bits.append(f'<span class="chip" style="--c:var(--amber)" title="{esc(tip)}">CTR decay</span>')
        return " ".join(bits) or '<span class="dim">&mdash;</span>'

    # Layer-2 actions
    refresh_rows = "".join(
        f'''<tr>
              <td><a href="{esc(i.get("url",""))}" target="_blank" class="mono-sm link-sm">{esc(i.get("url","").replace("https://","").replace("http://","").rstrip("/"))}</a> {trap_chip(i)}</td>
              <td class="mono-sm">{esc(i.get("target_keyword") or "") or '<span class="dim">&mdash;</span>'}</td>
              <td>{esc(i.get("serp_intent") or "") or '<span class="dim">&mdash;</span>'}</td>
              <td>{action_chip(i.get("action",""))}</td>
              <td class="c">{bvs_pill(i.get("bvs"))}</td>
              <td class="c"><span class="prio prio-{i.get("priority",9)}">{esc(i.get("priority","-"))}</span></td>
              <td>{flag_chip(i.get("primary_flag",""))}</td>
              <td>{_aio_cell(i)}</td>
              <td class="r dim">{esc(i.get("age_days") if i.get("age_days") is not None else "&mdash;")}</td>
              <td class="reason">{compact_list(i.get("content_gaps", []))}</td>
              <td class="reason">{esc(i.get("recommendation",""))}</td>
              <td>{status_pill(i.get("status",""))}</td>
            </tr>'''
        for i in refresh_items_sorted
    ) or f'<tr><td colspan="12" class="empty">{t("empty_no_actions")}</td></tr>'

    # Embedded classification report
    report_path = None
    if REPORTS_DIR.exists():
        candidates_md = sorted(REPORTS_DIR.glob("*-refresh-recommender.md"), reverse=True)
        report_path = candidates_md[0] if candidates_md else None
    if report_path:
        report_html = md_to_html(report_path.read_text())
        report_meta = f'<span class="ts">{esc(report_path.name)}</span>'
    else:
        report_html = f'<p class="empty">{t("empty_no_classif")}</p>'
        report_meta = ""

    return f'''
<section class="tab-pane" data-tab-pane="refresh">
  <div class="stat-row">
    <div class="stat"><div class="stat-num" style="--c:var(--rose)">{by_flag.get("not_indexed",0)}</div><div class="stat-label">{t("stat_not_indexed")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--sky)">{by_flag.get("index_warning",0)}</div><div class="stat-label">{t("stat_index_warning")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--amber)">{by_flag.get("stale", by_flag.get("stale_12mo",0))}</div><div class="stat-label">{t("stat_stale")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--amber)">{by_flag.get("ctr_decay",0)}</div><div class="stat-label">{t("stat_ctr_decay")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--rose)">{sum(1 for i in refresh_items if i.get("aio_loss"))}</div><div class="stat-label">{t("stat_aio_loss")}</div></div>
    <div class="stat"><div class="stat-num" style="--c:var(--lime)">{by_action.get("refresh",0) + by_action.get("request_indexing",0) + by_action.get("fix_canonical",0) + by_action.get("audit_then_decide",0) + by_action.get("consider_consolidate_or_remove",0)}</div><div class="stat-label">{t("stat_actions_queued")}</div></div>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_layer2")}</h2>
      {t("ts_consumed_by", cls="ts")}
    </div>
    <table class="data-table refresh-table">
      <thead><tr>
        <th>{t("th_url")}</th><th>{t("th_keyword")}</th><th>{t("th_serp_intent")}</th><th>{t("th_action")}</th>
        <th class="c">BVS</th><th class="c">P</th>
        <th>{t("th_primary_flag")}</th><th>AIO / CTR</th><th class="r">{t("th_age")}</th>
        <th>{t("th_content_gaps")}</th><th>{t("th_recommendation")}</th><th>{t("th_status")}</th>
      </tr></thead>
      <tbody>{refresh_rows}</tbody>
    </table>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_layer1")}</h2>
      <span class="ts">{esc(last_scan)} &middot; {urls_evaluated} {t("ls_urls_evaluated")} &middot; {len(flagged_cands)} {t("ls_flagged")}</span>
    </div>
    <table class="data-table">
      <thead><tr>
        <th>{t("th_url")}</th><th>{t("th_flags")}</th><th class="r">{t("th_age")}</th>
        <th>{t("th_coverage_state")}</th><th class="dim">{t("th_last_crawl")}</th>
      </tr></thead>
      <tbody>{cand_rows}</tbody>
    </table>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2 class="panel-title">{t("panel_classif_report")}</h2>
      {report_meta}
    </div>
    <article class="md-content">{report_html}</article>
  </div>
</section>'''


def _render_candidate_row(c: dict) -> str:
    flags_html = "".join(flag_chip(f) for f in c.get("flags", []))
    url = c.get("url", "")
    short = url.replace("https://", "").replace("http://", "").rstrip("/")
    if len(short) > 64:
        short = short[:61] + "..."
    insp = c.get("indexing", {}) or {}
    cov = insp.get("coverage_state") or "&mdash;"
    crawl = insp.get("last_crawl_time") or ""
    crawl_short = crawl[:10] if crawl else "&mdash;"
    return f'''<tr>
      <td><a href="{esc(url)}" target="_blank" rel="noopener" class="mono-sm link-sm">{esc(short)}</a></td>
      <td>{flags_html}</td>
      <td class="r">{esc(c.get("age_days") if c.get("age_days") is not None else "&mdash;")}</td>
      <td class="dim">{esc(cov)}</td>
      <td class="r dim mono-sm">{esc(crawl_short)}</td>
    </tr>'''


# ----------------------------- main -----------------------------------------

CSS = r"""
:root {
  --bg: #0B0B0C;
  --bg-2: #141416;
  --bg-3: #1C1C1F;
  --line: rgba(255,255,255,0.08);
  --line-2: rgba(255,255,255,0.16);
  --fg: #ECECEA;
  --fg-2: #B8B8B4;
  --dim: #6E6E6A;
  --ghost: #4A4A47;
  --lime: #C7FF4A;
  --mint: #4ED6B8;
  --amber: #F0B454;
  --rose: #F26D7D;
  --sky: #6CC2E6;
  --paper: #0B0B0C;
  --paper-light: #141416;
  --ink: #0B0B0C;
  --signal: #C7FF4A;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 14px; }
body {
  font-family: 'Geist', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
  min-height: 100vh;
  letter-spacing: 0;
}
a { color: inherit; text-decoration: none; }
code, .mono { font-family: 'JetBrains Mono', 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace; }
.mono-sm { font-family: 'JetBrains Mono', 'Geist Mono', monospace; font-size: 11px; }
.dim { color: var(--dim); }
.r { text-align: right; }
.c { text-align: center; }

/* ----- top bar ----- */
.topbar {
  border-bottom: 1px solid var(--line);
  background: rgba(11,11,12,0.92);
  backdrop-filter: blur(12px);
  position: sticky; top: 0; z-index: 100;
}
.topbar-inner {
  max-width: 1400px; margin: 0 auto;
  padding: 14px 32px;
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px;
}
.brand {
  display: flex; align-items: center; gap: 14px;
}
.brand-logo {
  --size: 34px;
  width: var(--size); height: var(--size);
  border-radius: calc(var(--size) * .18);
  background: var(--signal);
  position: relative;
  flex-shrink: 0;
}
.brand-logo::before,
.brand-logo::after {
  content: "";
  position: absolute;
  left: calc(var(--size) * .22);
  width: calc(var(--size) * .5);
  height: calc(var(--size) * .095);
  background: var(--ink);
  border-radius: calc(var(--size) * .028);
}
.brand-logo::before { top: calc(var(--size) * .22); }
.brand-logo::after { bottom: calc(var(--size) * .22); }
.brand-logo i {
  position: absolute;
  left: calc(var(--size) * .22);
  top: calc(50% - (var(--size) * .095 / 2));
  width: calc(var(--size) * .36);
  height: calc(var(--size) * .095);
  background: var(--ink);
  border-radius: calc(var(--size) * .028);
  display: block;
}
.brand-copy { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.brand-mark {
  font-family: 'Geist', system-ui, sans-serif;
  font-size: 24px;
  line-height: 1;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--fg);
}
.brand-sub { font-size: 11px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.1em; }
.brand-mark-link { text-decoration: none; color: var(--fg); transition: color 0.15s; }
.brand-mark-link:hover { color: var(--lime); }
.live-stamp {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; color: var(--dim);
  text-transform: uppercase; letter-spacing: 0.08em;
}
.live-stamp .pulse {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 0 rgba(199,255,74,0.5);
  animation: pulse 2.4s infinite;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(199,255,74,0.5); }
  70%  { box-shadow: 0 0 0 10px rgba(199,255,74,0); }
  100% { box-shadow: 0 0 0 0 rgba(199,255,74,0); }
}

/* ----- tab strip ----- */
.tabs {
  border-bottom: 1px solid var(--line);
  background: var(--bg);
  position: sticky; top: 51px; z-index: 90;
}
.tabs-inner {
  max-width: 1400px; margin: 0 auto;
  padding: 0 32px;
  display: flex; gap: 4px;
}
.tab {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--dim);
  cursor: pointer;
  border: none; background: none;
  border-bottom: 1px solid transparent;
  transition: color 0.15s;
  letter-spacing: 0.02em;
}
.tab:hover { color: var(--fg-2); }
.tab .tab-num { color: var(--ghost); font-size: 10px; }
.tab.active { color: var(--fg); border-bottom-color: var(--lime); }
.tab.active .tab-num { color: var(--lime); }
.tab .tab-count {
  background: var(--bg-3);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 10px;
  color: var(--fg-2);
}

/* ----- main ----- */
.main { max-width: 1400px; margin: 0 auto; padding: 32px; }
.tab-pane { display: none; animation: fadein 0.18s ease-out; }
.tab-pane.active { display: block; }
@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }

/* ----- hero (overview) ----- */
.hero-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 32px;
}
.hero-card {
  background: var(--bg-2);
  padding: 28px 24px 24px;
  position: relative;
  display: block;
  cursor: pointer;
  transition: background 0.15s;
  opacity: 0;
  animation: lift 0.5s cubic-bezier(0.2,0.8,0.2,1) forwards;
}
.hero-card[data-anim-delay] { animation-delay: calc(var(--delay,0ms)); }
@keyframes lift { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.hero-card:hover { background: var(--bg-3); }
.hero-card:hover .hero-card-arrow { color: var(--lime); transform: translateX(2px); }
.hero-card-head {
  display: flex; align-items: baseline; gap: 12px;
  margin-bottom: 18px;
}
.hero-card-num {
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--ghost);
  letter-spacing: 0.1em;
}
.hero-card-name {
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.hero-card-stat {
  font-family: 'Geist', system-ui, sans-serif;
    font-size: 56px;
  line-height: 1;
  letter-spacing: 0;
  color: var(--c, var(--fg));
  margin-bottom: 10px;
  font-weight: 400;
}
.hero-card-label {
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--fg-2);
  letter-spacing: 0.01em;
}
.hero-card-arrow {
  position: absolute;
  top: 24px; right: 20px;
  color: var(--ghost);
  font-size: 14px;
  transition: color 0.15s, transform 0.15s;
}

/* ----- panel ----- */
.panel {
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 2px;
  margin-bottom: 24px;
  overflow: hidden;
}
.panel-head {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  gap: 16px;
}
.panel-title {
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--fg);
}
.ts {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 400;
}
.ts code { font-size: 10px; color: var(--dim); }

/* ----- stat row ----- */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 2px;
  margin-bottom: 24px;
  overflow: hidden;
}
.stat {
  background: var(--bg-2);
  padding: 18px 20px 16px;
  opacity: 0;
  animation: lift 0.45s cubic-bezier(0.2,0.8,0.2,1) forwards;
  animation-delay: 80ms;
}
.stat-num {
  font-family: 'Geist', system-ui, sans-serif;
    font-size: 38px;
  line-height: 1;
  letter-spacing: 0;
  color: var(--c, var(--fg));
  font-weight: 400;
  margin-bottom: 8px;
}
.stat-label {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ----- tables ----- */
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  font-family: 'Geist Mono', monospace;
  text-align: left;
  padding: 10px 16px;
  font-size: 10px;
  font-weight: 500;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
}
.data-table th.r { text-align: right; }
.data-table th.c { text-align: center; }
.data-table td {
  padding: 12px 16px;
  font-size: 12px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
.data-table tbody tr { transition: background 0.1s; }
.data-table tbody tr:hover { background: var(--bg-3); }
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table .empty {
  padding: 32px;
  text-align: center;
  color: var(--dim);
  }

/* ----- pills, chips, badges ----- */
.pill {
  display: inline-flex; align-items: center;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--c, var(--dim));
  background: color-mix(in srgb, var(--c, var(--dim)) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--c, var(--dim)) 30%, transparent);
  font-weight: 500;
}
.chip {
  display: inline-flex; align-items: center;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 3px;
  text-transform: lowercase;
  letter-spacing: 0;
  color: var(--c, var(--dim));
  background: color-mix(in srgb, var(--c, var(--dim)) 12%, transparent);
  margin-right: 4px;
}
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--c, var(--dim)); }
.prio {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  border-radius: 4px;
  font-weight: 600;
}
.prio-1 { background: color-mix(in srgb, var(--rose) 14%, transparent); color: var(--rose); }
.prio-2 { background: color-mix(in srgb, var(--amber) 14%, transparent); color: var(--amber); }
.prio-3 { background: color-mix(in srgb, var(--dim) 14%, transparent); color: var(--dim); }
.delta.neg { color: var(--rose); font-weight: 600; }
.delta.pos { color: var(--lime); font-weight: 600; }
.link-sm { color: var(--sky); transition: color 0.15s; }
.link-sm:hover { color: var(--fg); }

/* ----- queue cards ----- */
.queue-stack { display: flex; flex-direction: column; gap: 12px; }
.queue-card {
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 2px;
  overflow: hidden;
  transition: border-color 0.15s;
}
.queue-card:hover { border-color: var(--line-2); }
.queue-card[open] { border-color: var(--line-2); }
.queue-card summary {
  list-style: none;
  cursor: pointer;
  padding: 18px 22px;
  display: block;
}
.queue-card summary::-webkit-details-marker { display: none; }
.queue-card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.queue-id { font-size: 10px; color: var(--dim); }
.queue-card-title {
  font-family: 'Geist', system-ui, sans-serif;
    font-size: 22px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--fg);
  margin-bottom: 12px;
  line-height: 1.2;
}
.queue-card-stats {
  display: flex; gap: 24px;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--fg-2);
  flex-wrap: wrap;
}
.queue-card-stats code { color: var(--lime); font-size: 11px; }
.queue-card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  padding: 20px 22px 22px;
  border-top: 1px solid var(--line);
  background: var(--bg);
}
.qcb-col h4 {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 14px 0 8px;
  font-weight: 500;
}
.qcb-col h4:first-child { margin-top: 0; }
.qcb-col p { font-size: 12px; color: var(--fg-2); line-height: 1.6; }
.dense { list-style: none; }
.dense li {
  padding: 3px 0;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--fg-2);
}
.mini-list { max-width: 300px; }
.mini-list li { line-height: 1.45; }
.link-list li a { color: var(--sky); word-break: break-all; }
.link-list li a:hover { color: var(--fg); }
.meta-dl { font-family: 'Geist Mono', monospace; font-size: 11px; }
.meta-dl dt { color: var(--dim); display: inline; }
.meta-dl dt::before { content: ""; display: block; height: 4px; }
.meta-dl dd { display: inline; margin-left: 8px; color: var(--fg-2); }

/* ----- seed list ----- */
.seed-list { list-style: none; padding: 16px 20px; }
.seed-list li { padding: 4px 0; font-size: 12px; }

/* ----- markdown content (vital signs report) ----- */
.md-content {
  padding: 24px 28px 28px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.65;
  color: var(--fg-2);
}
.md-content h1, .md-content h2, .md-content h3, .md-content h4 {
  font-family: 'Geist Mono', monospace;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--fg);
  margin: 28px 0 12px;
}
.md-content > h1:first-child, .md-content > h2:first-child { margin-top: 0; }
.md-content h1 {
  font-family: 'Geist', system-ui, sans-serif;
    font-size: 28px;
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
}
.md-content h2 {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--lime);
  border-top: 1px solid var(--line);
  padding-top: 24px;
}
.md-content h3 {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--dim);
}
.md-content p { margin: 0 0 14px; }
.md-content ul { margin: 0 0 14px 18px; }
.md-content li { margin: 4px 0; }
.md-content a { color: var(--sky); }
.md-content a:hover { color: var(--fg); }
.md-content code {
  background: var(--bg-3);
  border: 1px solid var(--line);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--lime);
}
.md-table-wrap { overflow-x: auto; margin: 16px 0; border: 1px solid var(--line); border-radius: 8px; }
.md-table { width: 100%; border-collapse: collapse; font-family: 'Geist Mono', monospace; font-size: 11px; }
.md-table th {
  text-align: left;
  padding: 10px 14px;
  font-size: 10px;
  font-weight: 500;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
}
.md-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  color: var(--fg-2);
  vertical-align: top;
}
.md-table tr:last-child td { border-bottom: none; }
.md-table strong { color: var(--fg); }

/* ----- empty state ----- */
.empty-state {
  padding: 64px 32px;
  text-align: center;
  color: var(--dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  }
.refresh-table .reason { color: var(--fg-2); max-width: 380px; line-height: 1.5; }

@media (max-width: 900px) {
  .hero-grid { grid-template-columns: 1fr 1fr; }
  .queue-card-body { grid-template-columns: 1fr; gap: 16px; }
  .topbar-inner, .tabs-inner, .main { padding-left: 20px; padding-right: 20px; }
}

/* ----- CTA card ----- */
.cta-card {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 200;
  width: 290px;
  background: var(--bg-2);
  border: 1px solid rgba(199,255,74,0.35);
  border-radius: 2px;
  padding: 18px 20px 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.04);
  font-family: 'Geist', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}
.cta-card-dismiss {
  position: absolute;
  top: 10px; right: 12px;
  background: none; border: none;
  color: var(--dim);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 4px;
  transition: color 0.15s;
}
.cta-card-dismiss:hover { color: var(--fg); }
.cta-card-overline {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--lime);
  margin-bottom: 8px;
}
.cta-card-body {
  font-size: 13px;
  color: var(--fg-2);
  line-height: 1.5;
  margin-bottom: 14px;
}
.cta-card-btn {
  display: inline-block;
  background: var(--lime);
  color: var(--ink, #0B0B0C);
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 8px 16px;
  border-radius: 2px;
  text-decoration: none;
  transition: opacity 0.15s;
}
.cta-card-btn:hover { opacity: 0.85; }
.main { padding-bottom: 100px; }

/* ----- CTA banner (in-flow, every tab) ----- */
.cta-band {
  margin-top: 48px;
  background: var(--bg-2);
  border: 1px solid rgba(199,255,74,0.35);
  border-radius: 4px;
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.03);
  font-family: 'Geist', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}
.cta-band-copy { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.cta-band-overline {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--lime);
}
.cta-band-msg {
  font-size: 15px;
  color: var(--fg);
  line-height: 1.45;
}
.cta-band-btn {
  display: inline-block;
  flex-shrink: 0;
  background: var(--lime);
  color: var(--ink, #0B0B0C);
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 12px 22px;
  border-radius: 2px;
  text-decoration: none;
  transition: opacity 0.15s;
}
.cta-band-btn:hover { opacity: 0.85; }
@media (max-width: 720px) {
  .cta-band { flex-direction: column; align-items: flex-start; }
}

/* ----- language switcher ----- */
.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  margin-left: 18px;
}
.lang-btn {
  background: none;
  border: none;
  color: var(--dim);
  cursor: pointer;
  padding: 2px 6px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: color 0.15s;
  font-family: inherit;
  font-size: inherit;
}
.lang-btn:hover { color: var(--fg-2); }
.lang-btn.active { color: var(--lime); }
.lang-sep { color: var(--ghost); }
"""

JS = r"""
(function() {
  var tabs = document.querySelectorAll('.tab');
  var panes = document.querySelectorAll('.tab-pane');
  function activate(name) {
    tabs.forEach(function(t) { t.classList.toggle('active', t.dataset.tab === name); });
    panes.forEach(function(p) { p.classList.toggle('active', p.dataset.tabPane === name); });
    if (history.replaceState) history.replaceState(null, '', '#' + name);
  }
  tabs.forEach(function(t) {
    t.addEventListener('click', function(e) {
      e.preventDefault();
      activate(t.dataset.tab);
    });
  });
  // Apply staggered reveal delays
  document.querySelectorAll('[data-anim-delay]').forEach(function(el) {
    el.style.setProperty('--delay', el.dataset.animDelay + 'ms');
  });
  // Read initial tab from hash
  var initial = (location.hash || '').replace('#','');
  var valid = Array.from(tabs).map(function(t){return t.dataset.tab;});
  activate(valid.indexOf(initial) >= 0 ? initial : 'overview');
  // Hero card click navigates to corresponding tab
  document.querySelectorAll('.hero-card').forEach(function(c) {
    c.addEventListener('click', function(e) {
      var dest = c.dataset.tab;
      if (!dest) return;
      e.preventDefault();
      var name = dest.replace('tab-','');
      activate(name);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

  // ----- i18n: French default, FR/EN toggle -----
  // I18N is injected just before this script as window.I18N (fr/en dicts of
  // trusted chrome strings). innerHTML is used so HTML entities in the strings
  // (&middot;, &darr;, &amp;) render; these are author-controlled, never data.
  var I18N = window.I18N || { fr: {}, en: {} };
  function setLang(lang) {
    if (lang !== 'fr' && lang !== 'en') lang = 'fr';
    var dict = I18N[lang] || {};
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
      var key = el.getAttribute('data-i18n');
      if (Object.prototype.hasOwnProperty.call(dict, key)) {
        el.innerHTML = dict[key];
      }
    });
    document.querySelectorAll('.lang-btn').forEach(function(b) {
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    document.documentElement.setAttribute('lang', lang);
    try { localStorage.setItem('fs_lang', lang); } catch (e) {}
  }
  window.setLang = setLang;
  document.querySelectorAll('.lang-btn').forEach(function(b) {
    b.addEventListener('click', function() { setLang(b.dataset.lang); });
  });
  var saved = 'fr';
  try { saved = localStorage.getItem('fs_lang') || 'fr'; } catch (e) {}
  setLang(saved);
})();
"""


def main() -> int:
    bank = load(BANK)
    queue = load(QUEUE)
    onsite = load(ONSITE)
    candidates = load(CANDIDATES)
    refresh = load(REFRESH)
    log_data = load(AGENT_LOG) if AGENT_LOG.exists() else []
    if isinstance(log_data, dict):
        log_data = log_data.get("entries", [])

    keywords = bank.get("keywords", [])
    items = queue.get("items", [])
    audited = onsite.get("audited_urls", []) if isinstance(onsite, dict) else []
    refresh_items = refresh.get("items", []) if isinstance(refresh, dict) else []

    onsite_verdict = onsite.get("site_rollup", {}).get("verdict", "") if isinstance(onsite, dict) else ""
    onsite_count_label = onsite_verdict.upper() if onsite_verdict else (str(len(audited)) if audited else "")

    stats = {
        "kw_total": len(keywords),
        "queue_active": sum(1 for i in items if i.get("status") in ("queued","in_progress","needs_review")),
        "posts_written": sum(1 for i in items if i.get("status") == "written"),
        "onsite_verdict": onsite_count_label or "&mdash;",
        "refresh_queued": sum(1 for i in refresh_items if i.get("status") == "queued"),
    }

    counts_by_tab = {
        "overview": "",
        "keywords": str(len(keywords)),
        "queue":    str(stats["queue_active"]),
        "onsite":   onsite_count_label,
        "refresh":  str(stats["refresh_queued"]),
    }

    overview_html = render_overview_tab(stats, log_data if isinstance(log_data, list) else [])
    keywords_html = render_keywords_tab(bank)
    queue_html = render_queue_tab(queue)
    onsite_html = render_onsite_tab(onsite)
    refresh_html = render_refresh_tab(candidates, refresh)

    site = resolve_site_name(bank)
    site_short = site.replace("https://", "").replace("http://", "").rstrip("/")

    brand_overline = esc(BRAND_NAME).upper()
    cta_msg = I18N["cta_msg"]["fr"]
    cta_btn = I18N["cta_btn"]["fr"]

    # CTA popup (fixed bottom-right). Texts are i18n-tagged so setLang swaps them.
    cta_popup = f"""
<div id="cta-card" class="cta-card">
  <button class="cta-card-dismiss" onclick="document.getElementById('cta-card').style.display='none'" aria-label="Fermer">x</button>
  <div class="cta-card-overline">{brand_overline}</div>
  <p class="cta-card-body" data-i18n="cta_msg">{cta_msg}</p>
  <a class="cta-card-btn" href="{ZCAL_URL}" target="_blank" rel="noopener" data-i18n="cta_btn">{cta_btn}</a>
</div>""" if CTA_STYLE in ("popup", "both") else ""

    # CTA banner (in document flow, appears on every tab via the shared container).
    cta_banner = f"""
  <aside class="cta-band">
    <div class="cta-band-copy">
      <span class="cta-band-overline">{brand_overline}</span>
      <span class="cta-band-msg" data-i18n="cta_msg">{cta_msg}</span>
    </div>
    <a class="cta-band-btn" href="{ZCAL_URL}" target="_blank" rel="noopener" data-i18n="cta_btn">{cta_btn}</a>
  </aside>""" if CTA_STYLE in ("banner", "both") else ""

    i18n_script = f'<script>window.I18N = {i18n_js_object()};</script>'

    page = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(BRAND_NAME)} &middot; SEO report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <span class="brand-logo" aria-hidden="true"><i></i></span>
      <span class="brand-copy">
        <a class="brand-mark brand-mark-link" href="https://easygrowth.fr" target="_blank" rel="noopener">{esc(BRAND_WORDMARK)}</a>
        <span class="brand-sub">{t("brand_sub")} &middot; {esc(site_short)}</span>
      </span>
    </div>
    <div class="live-stamp">
      <span class="pulse"></span>
      <span>{t("last_updated")} {esc(NOW)}</span>
      <span class="lang-switch" role="group" aria-label="Language">
        <button type="button" class="lang-btn" data-lang="fr">FR</button>
        <span class="lang-sep">|</span>
        <button type="button" class="lang-btn" data-lang="en">EN</button>
      </span>
    </div>
  </div>
</header>

<nav class="tabs">
  <div class="tabs-inner">
    <button class="tab" data-tab="overview"><span class="tab-num">00</span> {t("tab_overview")}</button>
    <button class="tab" data-tab="keywords"><span class="tab-num">01</span> {t("tab_keywords")} <span class="tab-count">{counts_by_tab["keywords"]}</span></button>
    <button class="tab" data-tab="queue"><span class="tab-num">02</span> {t("tab_queue")} <span class="tab-count">{counts_by_tab["queue"]}</span></button>
    <button class="tab" data-tab="onsite"><span class="tab-num">03</span> {t("tab_onsite")} <span class="tab-count">{counts_by_tab["onsite"]}</span></button>
    <button class="tab" data-tab="refresh"><span class="tab-num">04</span> {t("tab_refresh")} <span class="tab-count">{counts_by_tab["refresh"]}</span></button>
  </div>
</nav>

<main class="main">
  {overview_html}
  {keywords_html}
  {queue_html}
  {onsite_html}
  {refresh_html}
  {cta_banner}
</main>
{cta_popup}

{i18n_script}
<script>{JS}</script>
</body>
</html>
"""

    latest = OUT_DIR / "dashboard.html"
    snapshot = OUT_DIR / f"{DATE}-dashboard.html"
    latest.write_text(page)
    snapshot.write_text(page)
    print(f"Dashboard written: {latest}")
    print(f"Snapshot:          {snapshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
