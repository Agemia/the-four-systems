# Structure du projet — carte rapide

> Tu arrives sur le projet pour la première fois ? Cette page liste tous les dossiers et fichiers avec leur rôle exact. Pour le flow d'exécution, voir [`docs/06-architecture.md`](docs/06-architecture.md).

## Arbre du projet

```
the-four-systems/
│
├── README.md                              Vue d'ensemble + quickstart
├── STRUCTURE.md                           ← cette page
├── CLAUDE.md                              ⭐ Auto-chargé par Claude Code à chaque session :
│                                          déclenche l'onboarding si le setup est incomplet
├── LICENSE                                MIT
├── .gitignore                             Cache .mcp.json, state runtime, output, reports
│
├── coordinator.sh                         Orchestrateur des runs scheduled (cron / launchd)
│                                          Appelé en tant que ./coordinator.sh <system-name>
│
├── .mcp.json.example                      Template des creds MCP (commitable)
├── .mcp.json                              Creds MCP actifs (GITIGNORED — local au dev)
│
├── .claude/
│   ├── settings.local.json.example        Template de l'allowlist permissions
│   ├── settings.local.json                Allowlist actif (GITIGNORED)
│   └── skills/                            Les 6 skills user-invocables dans Claude Code
│       ├── setup.md                         ⭐ Onboarding guidé : clés API + identité +
│       │                                      charte éditoriale (analyse d'exemples) + seeds
│       ├── context-bootstrapper.md          Lance l'interview qui remplit context/
│       ├── keyword-researcher.md            Skill System 1
│       ├── content-writer.md                Skill System 2
│       ├── onsite-audit.md                  Skill System 3
│       └── refresh-recommender.md           Skill System 4
│
├── prompts/                               Source-of-truth méthodologique des agents
│   ├── _business-value-scoring.md         ⭐ BVS spec partagée (lue par les 4 systems)
│   ├── keyword-researcher.md              Méthodologie System 1
│   ├── content-writer.md                  Méthodologie System 2 + linter rules
│   ├── onsite-audit.md                    Méthodologie System 3 + thresholds CWV/INP
│   └── refresh-recommender.md             Méthodologie System 4 + actions + AIO snapshots
│
├── context/                               ⭐ CONTEXTE BUSINESS (GITIGNORED — local)
│   ├── site-config.md                       Identité, locale, content type, scope
│   ├── audience.md                          Persona, niveau, ce qu'il déteste
│   ├── tone-of-voice.md                     Voix, règles de formatage, ban list
│   ├── experience-notes.md                  Wins, opinions, stories (LE fichier anti-AI-slop)
│   ├── services.md                          Produits, prix, FAQ → drive BVS money match
│   ├── brand-guidelines.md                  Mots interdits, claims régulés, concurrents bannis
│   ├── competitors.md                      Carte concurrentielle + content gaps
│   ├── author.md                            E-E-A-T : auteur, credentials, sameAs schema
│   ├── audit-urls.txt                       URLs à auditer par System 3
│   ├── editorial-charter.md                 (optionnel) Généré par `setup` depuis tes exemples
│   │                                        de bons/mauvais articles ; lu par le rédacteur
│   └── publishing.json                      (optionnel) Config auto-publish Astro
│
├── context-templates/                     Templates .example pour bootstrap initial
│   ├── site-config.md.example
│   ├── audience.md.example
│   ├── tone-of-voice.md.example
│   ├── experience-notes.md.example
│   ├── services.md.example
│   ├── brand-guidelines.md.example
│   ├── competitors.md.example
│   ├── author.md.example
│   └── audit-urls.txt.example
│
├── scripts/                               Exécutables Python + shell
│   ├── check-setup.py                     ⭐ Le "docteur" : détecte ce qui manque au setup
│   │                                        (creds, contexte, seeds) ; lu par CLAUDE.md à
│   │                                        chaque session pour déclencher l'onboarding
│   ├── lint-post.py                       Vérif qualité des posts (Three Kings, capsules, headings)
│   ├── mark-queue-item.py                 Update status d'un item content-queue
│   ├── pick-next-queue-item.py            Picker BVS-aware pour System 2
│   ├── publish-to-astro.py                Auto-publish vers repo Astro (optionnel)
│   ├── refresh-scorer.py                  System 4 layer 1 (Python) : sitemap + GSC + CTR + BVS
│   ├── render-html-report.py              Génère output/dashboard.html (4 onglets)
│   └── tutorial-logger.sh                 B-roll logging (pour le tutoriel vidéo)
│
├── state/                                 État runtime — la mémoire opérationnelle
│   ├── keyword-bank.json                  Source of truth des keywords + BVS
│   ├── content-queue.json                 File du Content Writer (BVS-sorted)
│   ├── refresh-candidates.json            Output System 4 layer 1
│   ├── refresh-queue.json                 Output System 4 layer 2 (actions)
│   ├── onsite-audit.json                  Dernier audit System 3
│   ├── seed-keywords.txt                  Liste de seeds pour System 1
│   └── serp-snapshots/                    Snapshots SERP datés (détection aio_loss)
│       └── <sha1-of-keyword-locale>.json
│
├── output/                                Artefacts livrables
│   ├── dashboard/                         Snapshots datés du dashboard
│   ├── keywords/                          CSV par run System 1 + dashboard.html (legacy path)
│   │   ├── dashboard.html                   ⭐ LE dashboard (le path est en dur dans le renderer)
│   │   └── YYYY-MM-DD-<seed>.csv
│   ├── posts/                             Articles écrits par System 2
│   │   └── YYYY-MM-DD-<slug>.md
│   ├── dataforseo/                        Réponses DataForSEO brutes (Lighthouse + on-page)
│   │   ├── <host-path>.lighthouse.json
│   │   └── <host-path>.instant_pages.json
│   └── lighthouse/                        LEGACY — voir output/lighthouse/README.md
│
├── reports/                               Rapports markdown lisibles humain
│   ├── YYYY-MM-DD-keyword-researcher.md
│   ├── YYYY-MM-DD-content-writer.md
│   ├── YYYY-MM-DD-onsite-audit.md
│   └── YYYY-MM-DD-refresh-recommender.md
│
├── docs/                                  Documentation utilisateur
│   ├── 00-prerequisites.md                Setup tools + APIs + creds
│   ├── 01-keyword-research.md             Mode d'emploi System 1
│   ├── 02-content-writer.md               Mode d'emploi System 2
│   ├── 03-onsite-audit.md                 Mode d'emploi System 3
│   ├── 04-refresh-recommender.md          Mode d'emploi System 4
│   ├── 05-business-value-scoring.md       ⭐ Vulgarisation BVS pour utilisateur
│   ├── 06-architecture.md                 ⭐ Carte du flow d'exécution + responsabilités
│   └── dashboard-example.html             Mockup statique du dashboard (référence visuelle)
│
└── launchd/                               Plists pour runs scheduled (macOS)
    ├── com.example.seo-keyword-researcher.plist
    ├── com.example.seo-content-writer.plist
    ├── com.example.seo-onsite-audit.plist
    └── com.example.seo-refresh-recommender.plist
```

## Pour s'y retrouver vite

| Tu veux... | Va dans... |
|---|---|
| Lancer ton premier run | Suis [`docs/00-prerequisites.md`](docs/00-prerequisites.md) |
| Comprendre la BVS | [`docs/05-business-value-scoring.md`](docs/05-business-value-scoring.md) |
| Comprendre comment les agents se parlent | [`docs/06-architecture.md`](docs/06-architecture.md) |
| Modifier la méthodologie d'un agent | `prompts/<agent>.md` |
| Adapter au business d'un nouveau site | Édite tous les fichiers `context/*.md` (ou lance `context-bootstrapper`) |
| Voir le dashboard | `open output/keywords/dashboard.html` |
| Ajouter un seed | Édite `state/seed-keywords.txt` |
| Ajouter une URL à auditer | Édite `context/audit-urls.txt` |
| Configurer les creds | `.mcp.json` (gitignored, local) + `claude /login` |
| Configurer les permissions auto | `.claude/settings.local.json` |
| Schedule un run nocturne | `launchd/*.plist` + `launchctl load` |

## Conventions de nommage

- `_business-value-scoring.md` (préfixe underscore) : fichier partagé entre prompts, lu par plusieurs agents.
- `YYYY-MM-DD-*.md` : artefacts datés, accumulés au fil des runs (jamais écrasés).
- `<system>.json` dans `state/` : état canonique pour un système (écrasé à chaque run).
- `.gitkeep` : marqueur pour tracker un dossier vide.

## Les 3 sources de vérité

1. **`context/`** = vérité business (qui tu es, ce que tu vends, à qui tu parles).
2. **`prompts/`** = vérité méthodologique (comment chaque agent doit travailler).
3. **`state/`** = vérité opérationnelle (qu'est-ce qui s'est passé, où on en est).

Tout le reste (`output/`, `reports/`, `docs/`, `scripts/`, `launchd/`) découle de ces 3 sources.
