# Architecture — flow d'exécution + responsabilités

> Cette doc explique **qui parle à qui** et **qui écrit où**. Une fois lue, n'importe quelle personne tierce peut comprendre comment les 4 agents se coordonnent.

## Vue d'ensemble

```
                            ┌──────────────────────┐
                            │  context/  (8 files) │  ← rempli une fois par humain
                            │  - site-config       │     (ou par context-bootstrapper)
                            │  - audience          │
                            │  - tone-of-voice     │
                            │  - experience-notes  │
                            │  - services          │
                            │  - brand-guidelines  │
                            │  - competitors       │
                            │  - author            │
                            │  - audit-urls.txt    │
                            └──────────────────────┘
                                       │
                                       │ (lu par tous les agents avant chaque run)
                                       ▼
        ┌────────────────────────────────────────────────────────────┐
        │                                                            │
   ┌────┴─────┐    ┌───────────┐    ┌────────────┐    ┌───────────┐  │
   │ System 1 │───▶│ System 2  │    │ System 3   │    │ System 4  │  │
   │  KW Rech │    │ Writer    │    │ Audit      │    │ Refresh   │  │
   └────┬─────┘    └─────┬─────┘    └─────┬──────┘    └─────┬─────┘  │
        │                │                │                  │       │
        ▼                ▼                ▼                  ▼       │
   ┌────────────────────────────────────────────────────────────────┐│
   │                       state/   (JSON files)                    ││
   │ ─ keyword-bank.json    ← S1 write, S4 read                     ││
   │ ─ content-queue.json   ← S1 write, S2 read+update              ││
   │ ─ onsite-audit.json    ← S3 write only                         ││
   │ ─ refresh-candidates   ← S4 layer1 write, S4 layer2 read       ││
   │ ─ refresh-queue.json   ← S4 layer2 write                       ││
   │ ─ serp-snapshots/      ← S4 layer2 read+write (aio_loss diff)  ││
   │ ─ seed-keywords.txt    ← humain write, S1 read                 ││
   └────────────────────────────────────────────────────────────────┘│
                                       │                              │
                                       ▼                              │
                            ┌──────────────────────┐                  │
                            │  output/             │                  │
                            │  ─ dashboard.html    │  ← rendu unique  │
                            │  ─ posts/            │  ← S2 écrit      │
                            │  ─ keywords/<csv>    │  ← S1 b-roll     │
                            │  ─ dataforseo/       │  ← S3 raw        │
                            └──────────────────────┘                  │
                                                                      │
                            ┌──────────────────────┐                  │
                            │  reports/            │  ← markdown      │
                            │  YYYY-MM-DD-*.md     │     lisibles     │
                            └──────────────────────┘                  │
                                                                      │
        ──────────────────────────────────────────────────────────────┘
                  Tous se coordonnent via les fichiers state/
                  Le dashboard HTML est régénéré à chaque run.
```

## Responsabilités précises par agent

### System 1 — Keyword Researcher

| Lit | Écrit |
|---|---|
| `context/site-config.md` (locale, in/out scope) | `state/keyword-bank.json` (append) |
| `context/services.md` (money page tokens) | `state/content-queue.json` (append items BVS 5-10) |
| `state/keyword-bank.json` (dedup) | `output/keywords/<date>-<seed>.csv` (b-roll) |
| `state/content-queue.json` (dedup) | `reports/<date>-keyword-researcher.md` |
| `state/seed-keywords.txt` (seed picker) | `output/dashboard.html` (via render script) |
| `prompts/_business-value-scoring.md` (BVS spec) | |
| `prompts/keyword-researcher.md` (méthodologie) | |

**APIs externes** : DataForSEO MCP (`ai_optimization_chat_gpt_scraper`, `keyword_ideas`, `keyword_suggestions`, `related_keywords`, `bulk_keyword_difficulty`, `serp_organic_live_advanced`), WebFetch (sitemap pour coverage check).

### System 2 — Content Writer

| Lit | Écrit |
|---|---|
| Les 8 fichiers `context/*` | `output/posts/<date>-<slug>.md` |
| `state/content-queue.json` (picker) | `state/content-queue.json` (update status) |
| `prompts/_business-value-scoring.md` (refuse BVS ≤ 1) | `reports/<date>-content-writer.md` |
| `prompts/content-writer.md` (workflow 5 étapes) | `output/dashboard.html` (via render) |

**APIs externes** : DataForSEO MCP (`serp_organic_live_advanced`, `on_page_content_parsing`), WebFetch (sources de citation), Anthropic API (rédaction).

**Scripts appelés** : `scripts/pick-next-queue-item.py` (BVS-aware), `scripts/lint-post.py` (vérif qualité), `scripts/mark-queue-item.py` (update queue), `scripts/publish-to-astro.py` (optionnel).

### System 3 — Onsite Audit

| Lit | Écrit |
|---|---|
| `context/audit-urls.txt` (URLs à auditer) | `state/onsite-audit.json` |
| `context/site-config.md` (locale, type de site) | `reports/<date>-onsite-audit.md` |
| `context/services.md` (money pages) | `output/dataforseo/<host-path>.lighthouse.json` |
| `state/keyword-bank.json` (recovery target keyword) | `output/dataforseo/<host-path>.instant_pages.json` |
| `prompts/_business-value-scoring.md` (BVS contextuel) | `output/dashboard.html` (via render) |
| `prompts/onsite-audit.md` (méthodologie) | |

**APIs externes** : DataForSEO MCP (`on_page_lighthouse`, `on_page_instant_pages`, `serp_organic_live_advanced` pour BVS context), WebFetch (`/robots.txt`, `/llms.txt`, `/llms-full.txt`).

### System 4 — Refresh Recommender

**Layer 1 (Python `scripts/refresh-scorer.py`)** :

| Lit | Écrit |
|---|---|
| `context/site-config.md` (content type → staleness band) | `state/refresh-candidates.json` |
| `context/services.md` (money page tokens) | `reports/<date>-refresh-raw.md` |
| Sitemap public du site (`/sitemap.xml`) | |
| GSC URL Inspection (verdict, coverage) | |
| GSC searchAnalytics (28d vs 28d pour CTR decay) | |
| Pages HTML (extraction dates publish/modify) | |

**Layer 2 (Claude prompt `prompts/refresh-recommender.md`)** :

| Lit | Écrit |
|---|---|
| `state/refresh-candidates.json` (layer 1 output) | `state/refresh-queue.json` (overwrite) |
| `state/content-queue.json` (skip URLs déjà en cours) | `reports/<date>-refresh-recommender.md` |
| `context/site-config.md` (locale SERP) | `state/serp-snapshots/<hash>.json` (snapshots SERP) |
| `context/services.md` (money pages) | `output/dashboard.html` (via render) |
| `state/keyword-bank.json` (target keyword recovery) | |
| `state/serp-snapshots/*` (prior snapshots pour aio_loss diff) | |
| `prompts/_business-value-scoring.md` | |

**APIs externes** : DataForSEO MCP (`serp_organic_live_advanced`, `on_page_content_parsing`), WebFetch (pages pour inférence target keyword si non en bank).

## Flow type d'une session

### Mode interactif (le plus courant)

```
1. tu lances    : claude
                    │
                    │  Claude Code lit .mcp.json, charge le MCP DataForSEO
                    │  et le MCP GSC. Lit .claude/settings.local.json
                    │  pour le allowlist.
                    │
2. tu tapes     : "research keywords for 'voip centre d appel'"
                    │
                    │  Claude lit prompts/keyword-researcher.md + 
                    │  context/* + prompts/_business-value-scoring.md +
                    │  state/keyword-bank.json (dedup) + state/content-queue.json
                    │
3. Claude       : appelle DataForSEO (kw ideas, suggestions, SERP, PAA, KD)
                    │  pour chaque variation : calcule la BVS
                    │  pour la SERP du seed : flagge les zero-click traps
                    │
4. Claude       : append au keyword-bank.json + queue les BVS ≥ 5 dans content-queue.json
                    │
5. Claude       : appelle scripts/render-html-report.py → output/dashboard.html
                    │
6. Claude te dit: "Done. 32 keywords ajoutés (8 BVS ≥ 8, 14 BVS 5-7, 8 BVS 2-4, 2 zero-click traps).
                    Top 3 queued : voip centre d'appel français, logiciel call center français, ..."
```

### Mode scheduled (cron / launchd)

```
0:05 du mois  : launchd déclenche ./coordinator.sh keyword-researcher
                    │
                    │  coordinator.sh utilise `claude -p ... --dangerously-skip-permissions`
                    │  pour exécuter sans intervention humaine.
                    │
                    │  Mode AUTO : Claude prend les décisions par défaut (top seed le moins récent,
                    │  validation auto des sources, etc.)
                    │
                    │  Tout le reste identique au mode interactif.
                    │  À la fin, auto-commit git de toutes les modifications.
```

## Les credentials et leur rôle exact

### 1. `.mcp.json` (à la racine, gitignored)

```json
{
  "mcpServers": {
    "dfs-mcp": {
      "command": "npx",
      "args": ["-y", "dataforseo-mcp-server"],
      "env": {
        "DATAFORSEO_USERNAME": "...",
        "DATAFORSEO_PASSWORD": "..."
      }
    },
    "gsc": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-gsc", "python", "gsc_server.py"]
    }
  }
}
```

- **DataForSEO MCP** : utilisé par Systems 1, 2, 3, 4 pour tout ce qui est SERP, keyword data, Lighthouse, on-page.
- **GSC MCP** : utilisé par System 4 layer 1 (refresh-scorer.py) pour URL Inspection et searchAnalytics. Le MCP est lancé en tant que sous-process Python depuis `mcp-gsc`.

**Important** : le GSC MCP nécessite un `client_secret.json` Google Cloud OAuth + un `.gsc_token.json` (token persistant, refresh automatique).

### 2. `.claude/settings.local.json` (gitignored)

Pré-autorise les outils que les 4 agents utilisent, pour ne pas avoir 50 prompts de permission à chaque run. Sans ce fichier, le système marche, juste avec des "Allow tool ?" à chaque tool call la première fois.

### 3. Anthropic API key

Set via `claude /login` ou variable d'env `ANTHROPIC_API_KEY`. Sans ça, le LLM ne tourne pas.

## Cycle de vie d'un keyword dans le système

```
seed.txt          "voip centre d'appel"
   │
   ▼
System 1          fan-out → 32 variations + BVS pour chaque
   │
   ├──▶ keyword-bank.json (toutes les 32, dont les skip)
   │
   └──▶ content-queue.json (les 5 priority 1 ou 2 max)
                   │
                   ▼
System 2          pick par BVS desc → article rédigé
                   │
                   ├──▶ output/posts/<slug>.md
                   │
                   └──▶ content-queue.json (status: written, post_url: ...)
                                  │
                                  ▼
                          (le post est publié sur ton site)
                                  │
                                  ▼ (3 mois plus tard)
                          System 4 layer 1 le repère dans le sitemap
                                  │
                                  ▼
                          GSC inspection + CTR 28d → flags
                                  │
                                  ▼
                          System 4 layer 2 → SERP analysis → BVS recalculée
                                  │
                                  ├──▶ refresh-queue.json (action: refresh / consolidate / ...)
                                  │
                                  └──▶ snapshots/<hash>.json (pour détection aio_loss future)
```

## Erreurs courantes et où chercher

| Symptôme | Cause probable | Où chercher |
|---|---|---|
| `dfs-mcp` ne charge pas | Creds manquantes ou faux | `.mcp.json` env block |
| `gsc` ne charge pas | Path mcp-gsc faux | `.mcp.json` `--directory` |
| `gsc_token.json` not found | Premier lancement, pas authentifié | `claude /login` puis flux OAuth Google |
| Le picker retourne `NO_QUEUED_ITEMS` | Tout est BVS ≤ 1 ou déjà written | Vérifier `state/content-queue.json`, lancer System 1 |
| Le rédacteur refuse d'écrire | Item flagué `zero_click_trap: true` | C'est le comportement attendu. Pick un autre item. |
| `Locale` introuvable dans site-config | Section manquante | Cf [docs/00-prerequisites.md](00-prerequisites.md) ou le template `context-templates/site-config.md.example` |
| Dashboard cassé sur un onglet | State malformé | Recharger avec un state fresh, le renderer dégrade gracieusement les champs manquants |

## En une phrase pour expliquer l'architecture à un non-tech

> "Quatre agents lisent un dossier de contexte business commun (`context/`), font leurs analyses via DataForSEO et Google Search Console, écrivent leurs résultats dans des fichiers JSON partagés (`state/`), et un script Python régénère un dashboard HTML unique (`output/dashboard.html`) à chaque run. Le dossier `context/` est la source de vérité business ; le dossier `state/` est la mémoire opérationnelle ; le dossier `output/` contient les artefacts livrables."
