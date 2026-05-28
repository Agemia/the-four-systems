# The Four Systems

> **Un système agentique de SEO pour 2026, conçu pour l'ère de l'IA Search.**
> 4 agents IA qui se coordonnent pour faire ton SEO en autonomie : recherche de mots-clés, rédaction d'articles, audit technique, et détection des contenus à rafraîchir. Tout cela en privilégiant **la valeur business** plutôt que le volume brut d'impressions.

---

## 📖 Sommaire

1. [Qu'est-ce que ce système fait ?](#1-quest-ce-que-ce-système-fait-)
2. [Les 4 agents en bref](#2-les-4-agents-en-bref)
3. [De quoi as-tu besoin pour le lancer ?](#3-de-quoi-as-tu-besoin-pour-le-lancer-)
4. [Installation pas-à-pas](#4-installation-pas-à-pas-15-minutes)
5. [Premier run](#5-premier-run)
6. [Utilisation au quotidien](#6-utilisation-au-quotidien)
7. [Combien ça coûte](#7-combien-ça-coûte)
8. [Pour aller plus loin](#8-pour-aller-plus-loin)
9. [FAQ et dépannage](#9-faq-et-dépannage)

---

## 1. Qu'est-ce que ce système fait ?

### Le problème

Le SEO en 2020 était simple : tu visais un mot-clé à fort volume, tu écrivais l'article le plus long du marché, tu mettais des mots-clés partout, et tu remontais dans Google.

**En 2026, cette logique est cassée.** Voici pourquoi :

- Quand tu cherches "indicatif Canada", Google affiche directement **"+1"** en haut de la page. Tu ne cliques sur aucun site.
- Quand tu cherches "qu'est-ce que la VoIP", Google répond avec une **AI Overview** générée par Gemini, sans envoyer l'utilisateur ailleurs.
- ChatGPT, Perplexity, Claude, et Gemini répondent aux questions de tes utilisateurs **sans même les amener sur ton site**.

Résultat : tu peux avoir 100 000 impressions par mois sur une page... et seulement 300 clics. Tu fais du volume pour rien. Aucun client.

### La solution

**The Four Systems** est un ensemble de 4 agents IA qui bossent ensemble pour te faire faire du SEO **utile** :

- Ils **refusent automatiquement** les requêtes "zero-click trap" (celles où Google répond directement)
- Ils **priorisent** les requêtes proches de tes pages de vente (les "money pages")
- Ils **écrivent** des articles dans un format optimisé pour les citations IA (AI Overviews, ChatGPT search, Perplexity)
- Ils **surveillent** tes pages existantes et te disent lesquelles refresh, lesquelles consolider, lesquelles supprimer

Le tout est piloté depuis **Claude Code** (le CLI d'Anthropic), avec un tableau de bord HTML unique que tu ouvres dans ton navigateur pour suivre ce qui se passe.

### Le concept clé : Business Value Score (BVS)

Tous les agents parlent le même langage : la **BVS**, une note de **0 à 10** qui répond à une seule question :

> "Si on rank sur ce mot-clé, est-ce que ça nous apporte un client ?"

- **BVS 10** = page produit ciblée par une requête commerciale avec annonces payantes en SERP → jackpot
- **BVS 0** = "indicatif Canada" → zero-click trap, Google répond direct, on n'écrira jamais d'article là-dessus

Les agents calculent automatiquement la BVS de chaque mot-clé et de chaque page. Le système refuse de produire du contenu BVS ≤ 1. Tu gagnes des semaines de rédaction inutile.

📖 Pour comprendre la BVS en détail : [`docs/05-business-value-scoring.md`](docs/05-business-value-scoring.md)

---

## 2. Les 4 agents en bref

| # | Agent | Ce qu'il fait | Fréquence typique |
|---|---|---|---|
| 1 | **Keyword Researcher** | Trouve les mots-clés à viser. Pour chaque candidat, il interroge Google + ChatGPT + DataForSEO, calcule la BVS, et n'ajoute à ta file de rédaction que ce qui a une vraie valeur business. | 1×/mois |
| 2 | **Content Writer** | Rédige un article complet à partir de la file. Format optimisé pour les citations IA (Content Capsules, GEO, Information Gain). Te demande validation à chaque étape clé. | 1×/semaine |
| 3 | **Onsite Audit** | Audit technique des pages importantes : performance, accessibilité, Core Web Vitals (LCP/CLS/**INP**), schema.org, politique des bots IA (GPTBot, ClaudeBot, etc.), llms.txt. | 1×/mois |
| 4 | **Refresh Recommender** | Scanne tes vieilles pages, détecte celles qui décrochent (CTR qui chute, perte de citations AI Overview, contenu obsolète), et te dit pour chacune : refresh, consolider, ou supprimer. | 1×/mois |

📖 Mode d'emploi détaillé par agent : [`docs/01-*`](docs/01-keyword-research.md) à [`docs/04-*`](docs/04-refresh-recommender.md)

---

## 3. De quoi as-tu besoin pour le lancer ?

### 3.1 Logiciels à installer sur ta machine

| Outil | Pourquoi | Comment l'installer |
|---|---|---|
| **macOS, Linux ou WSL2** | Le système tourne sur n'importe quel OS Unix-like | Tu l'as déjà |
| **Claude Code** | Le CLI d'Anthropic. **Pas l'app Desktop**, elle ne marche pas ici. | https://docs.anthropic.com/en/docs/agents-and-tools/claude-code |
| **Python 3.10+** | Pour les scripts d'analyse | macOS l'a déjà, sinon `brew install python` |
| **Node.js 18+** | Pour faire tourner le MCP DataForSEO | `brew install node` ou https://nodejs.org |
| **Git** | Pour cloner le projet et tracker tes runs | `brew install git` |

### 3.2 Comptes API à créer

Tu auras besoin de **3 comptes** (tous ont une option gratuite ou très peu chère) :

**1. Anthropic** (pour faire tourner Claude) — https://console.anthropic.com
- Crée une clé API
- Budget : 5-15 €/mois pour les 4 systèmes combinés

**2. DataForSEO** (pour les données SEO) — https://dataforseo.com
- Crée un compte, fais un top-up de 50 € qui durera plusieurs mois
- Récupère ton username + password depuis Dashboard → API Access
- Budget : 2-3 €/mois pour les 4 systèmes combinés

**3. Google Search Console** (pour les données réelles de ton site) — https://search.google.com/search-console
- Ton site doit être **vérifié** dans GSC (via balise meta ou DNS)
- Tu auras aussi besoin de créer un projet Google Cloud pour obtenir un fichier `client_secret.json` OAuth (pour que le système puisse lire l'API GSC)
- Budget : gratuit

### 3.3 Tes propres informations business

Tu vas devoir remplir **9 fichiers de contexte** qui décrivent ton business à l'IA. Pas de panique : **un agent dédié (`context-bootstrapper`) te pose les questions** pendant 15-20 minutes et remplit tout tout seul. Tu peux aussi le faire à la main si tu préfères.

Les 9 fichiers couvrent :
- Qui tu es, ton site, ta locale (FR/EN/DE…), tes sujets en/hors-scope
- Qui te lit, son niveau, ce qu'il déteste
- Ta voix de marque (formel, direct, etc.)
- Tes vraies victoires chiffrées + tes opinions fortes (LE secret anti "AI slop")
- Ce que tu vends (produits, prix, FAQ)
- Tes mots interdits + concurrents bannis
- Tes concurrents directs/indirects + les sujets qu'ils ont saturés
- L'auteur officiel des articles + ses credentials (pour le SEO E-E-A-T)

📖 Le détail de chaque fichier : voir [`context/README.md`](context/README.md) (dans le repo cloné)

---

## 4. Installation pas-à-pas (15 minutes)

### Étape 1 — Cloner le repo

```bash
git clone https://github.com/<TON-USERNAME>/<TON-REPO> the-four-systems
cd the-four-systems
```

### Étape 2 — Authentifier Claude Code

```bash
claude /login
```

Suis le flux d'authentification (ouvre ton compte Anthropic et autorise).

### Étape 3 — Configurer les credentials DataForSEO et GSC

Copie les templates :

```bash
cp .mcp.json.example .mcp.json
cp .claude/settings.local.json.example .claude/settings.local.json
```

Édite `.mcp.json` et remplace `you@example.com` / `your-dataforseo-password` par tes vraies creds DataForSEO :

```json
{
  "mcpServers": {
    "dfs-mcp": {
      "command": "npx",
      "args": ["-y", "dataforseo-mcp-server"],
      "env": {
        "DATAFORSEO_USERNAME": "ton-email@example.com",
        "DATAFORSEO_PASSWORD": "ton-password-dataforseo"
      }
    },
    "gsc": {
      "command": "uv",
      "args": ["run", "--directory", "/chemin/vers/mcp-gsc", "python", "gsc_server.py"]
    }
  }
}
```

> ⚠️ Le fichier `.mcp.json` est dans `.gitignore`, donc tes creds **ne seront jamais commités sur GitHub**. Mais ne les colle nulle part en dehors de ce fichier.

### Étape 4 — Installer le MCP Google Search Console

Le MCP GSC est un petit serveur Python externe. Suis les instructions de [`docs/00-prerequisites.md`](docs/00-prerequisites.md) section "MCP 2: Google Search Console" pour :
1. Cloner le repo `mcp-gsc`
2. Créer un projet Google Cloud + télécharger `client_secret.json`
3. Mettre à jour le chemin `--directory` dans `.mcp.json`

À la première utilisation, le système ouvrira ton navigateur pour t'authentifier sur GSC une fois.

### Étape 5 — Lancer Claude Code dans le dossier

```bash
claude
```

À ce moment-là, Claude Code lit ton `.mcp.json` et charge les deux MCPs (DataForSEO et GSC). S'il y a une erreur de config, il te le dira ici.

### Étape 6 — Remplir ton contexte business

Dans la session Claude Code qui vient de s'ouvrir, tape :

```
bootstrap my context folder
```

L'agent `context-bootstrapper` va :
1. Te demander ton URL
2. Aller fetcher ton site pour pré-remplir ce qu'il peut
3. Te poser 6 sections de questions pendant 15-20 minutes (audience, voix, expérience, services, brand, concurrents, auteur)
4. Écrire les 9 fichiers dans `context/` tout seul

Tu peux relire/ajuster chaque fichier après. Tu peux aussi t'arrêter en cours de route ; les réponses sont sauvegardées au fur et à mesure.

---

## 5. Premier run

Tu es maintenant prêt à lancer ton premier agent. Toujours dans la session Claude Code :

### Recherche de mots-clés (System 1)

```
research keywords for <ton mot-clé de départ>
```

Exemple : `research keywords for "logiciel CRM PME"`

L'agent va :
1. Fan-out le mot-clé en 30-50 variations via ChatGPT + DataForSEO
2. Extraire les questions "People Also Ask" depuis Google
3. Calculer la **BVS** pour chaque variation
4. Filtrer les zero-click traps
5. Ajouter les bons mots-clés à ta file de rédaction (`state/content-queue.json`)
6. Te montrer un rapport : "32 keywords ajoutés, 8 en priorité 1, 2 zero-click traps filtrés"

### Ouvrir le tableau de bord

Toujours dans la session Claude Code, tape `exit` pour quitter, puis :

```bash
open output/keywords/dashboard.html
```

Tu vois ton dashboard avec 4 onglets : Keywords, Queue, Onsite, Refresh. Au début seul l'onglet Keywords aura des données. Au fil de tes runs, les autres se remplissent.

### Écrire ton premier article (System 2)

```
write a post
```

L'agent te propose les 3 meilleurs items de la file (triés par BVS desc), tu en choisis un, et il fait son workflow en 5 étapes :
1. **Brief** : il valide le sujet, te demande si tu as une anecdote perso
2. **Recherche** : il trouve 8-12 sources, te les présente pour validation
3. **Outline** : il te présente le plan (titre, H2, H3) pour validation
4. **Draft** : il écrit l'article
5. **Review** : il fait son propre lint qualité, et te livre

L'article sort dans `output/posts/YYYY-MM-DD-<slug>.md`.

### Audit technique (System 3)

D'abord, édite `context/audit-urls.txt` pour y mettre 3-5 URLs prioritaires (ta homepage + tes pages de vente principales). Puis :

```
run an onsite audit
```

L'agent lance Lighthouse + on-page checks via DataForSEO, vérifie aussi la politique des bots IA dans ton `robots.txt`, et produit un rapport markdown + une mise à jour du dashboard.

### Détection des pages à rafraîchir (System 4)

```
find pages to refresh
```

L'agent scanne ton sitemap, croise avec GSC, identifie les pages qui décrochent, classe par BVS, et te dit pour chacune : refresh / fix canonical / request indexing / consolider-ou-supprimer.

---

## 6. Utilisation au quotidien

Une fois installé, le rythme typique :

| Quand | Action | Durée |
|---|---|---|
| Une fois (setup initial) | Install + contexte business | 1-2 heures |
| 1× par mois | `research keywords for <nouveau seed>` | 5 min |
| 1× par semaine | `write a post` (pick un item) | 30 min |
| 1× par mois | `run an onsite audit` | 3 min |
| 1× par mois | `find pages to refresh` | 5 min |
| Quand un client raconte un truc cool | Ajouter à `context/experience-notes.md` | 2 min |

Tout le reste se fait tout seul. Le dashboard est régénéré à chaque run.

### Bonus : mode automatique (cron / launchd)

Si tu veux que les runs se déclenchent automatiquement (par exemple toutes les nuits), le dossier `launchd/` contient des fichiers `.plist` prêts pour macOS. Voir la section "Going hands-off (optional)" dans chaque `docs/0X-*.md`.

---

## 7. Combien ça coûte

| Poste | Coût mensuel typique |
|---|---|
| Anthropic API (Claude) | 5 à 15 € |
| DataForSEO (pay-as-you-go) | 2 à 3 € |
| Google Search Console | gratuit |
| Google Cloud OAuth | gratuit |
| **Total** | **~10-20 €/mois pour 1 site** |

Le top-up DataForSEO de 50 € dure typiquement 3-6 mois selon ton volume d'utilisation.

---

## 8. Pour aller plus loin

| Sujet | Doc |
|---|---|
| Carte annotée du projet (où est quoi) | [`STRUCTURE.md`](STRUCTURE.md) |
| Setup complet pas-à-pas + détail des comptes | [`docs/00-prerequisites.md`](docs/00-prerequisites.md) |
| Mode d'emploi System 1 (Keyword Researcher) | [`docs/01-keyword-research.md`](docs/01-keyword-research.md) |
| Mode d'emploi System 2 (Content Writer) | [`docs/02-content-writer.md`](docs/02-content-writer.md) |
| Mode d'emploi System 3 (Onsite Audit) | [`docs/03-onsite-audit.md`](docs/03-onsite-audit.md) |
| Mode d'emploi System 4 (Refresh Recommender) | [`docs/04-refresh-recommender.md`](docs/04-refresh-recommender.md) |
| Tout sur le Business Value Score | [`docs/05-business-value-scoring.md`](docs/05-business-value-scoring.md) |
| Architecture (qui parle à qui) | [`docs/06-architecture.md`](docs/06-architecture.md) |
| Mockup visuel du dashboard | [`docs/dashboard-example.html`](docs/dashboard-example.html) |

---

## 9. FAQ et dépannage

### Pourquoi Claude Code et pas l'app Claude Desktop ?

Desktop est une interface de chat. Elle ne peut pas :
- Lire les fichiers de ton projet local
- Exécuter les scripts Python du système
- Être appelée par un cron / launchd pour les runs automatiques
- Charger les MCPs définis dans `.mcp.json`

Claude Code est le CLI conçu pour le travail sur projet. Même modèle (Claude), surface différente. Gratuit à installer, mêmes coûts d'API.

### Je n'ai pas de site, je peux quand même utiliser le système ?

Non. Tous les agents partent du contexte business (`context/`) et beaucoup s'appuient sur Google Search Console (qui exige un site vérifié). Commence par avoir un site avec quelques URLs indexées, puis reviens.

### Mon site est en allemand / espagnol / japonais, ça marche ?

Oui. Le fichier `context/site-config.md` définit ta locale (`target_country` + `target_language`). Tous les appels DataForSEO la passent. Le système est totalement multilingue. Si ton site est multilingue (FR + EN par exemple), tu choisis une locale primaire et tu peux configurer les alternates.

### Le contexte est gitignored, c'est normal ?

Oui. Le contenu de `context/` est **strictement local à ton install**. Il contient tes prix, tes opinions stratégiques, tes témoignages clients, tes credentials d'auteur. Le `.gitignore` du projet exclut automatiquement `context/*` (sauf le README + .gitkeep) pour que tu ne pousses jamais ces infos sur GitHub par erreur.

### J'ai déjà du contenu sur mon site, est-ce que ça va le casser ?

Non. Le système est **non-destructif** :
- System 1 ajoute des keywords à une bank, ne touche pas à ton site
- System 2 écrit des fichiers markdown dans `output/posts/` ; tu publies à la main (ou via Astro auto-publish optionnel)
- System 3 lit ton site pour l'auditer, ne le modifie pas
- System 4 te donne des **recommandations** à exécuter toi-même, jamais d'écriture auto

### Le système peut-il publier automatiquement sur mon WordPress / Webflow / Notion ?

Pas directement. System 2 produit du markdown propre dans `output/posts/`. Tu l'uploades à la main. Une exception : si ton site est sur Astro, il y a un script `scripts/publish-to-astro.py` qui peut commit en branche draft pour review.

### Combien de temps pour mon premier article publiable ?

- 1-2 h de setup initial (une fois pour toutes)
- 5 min pour lancer System 1 sur un seed
- 30 min pour rédiger un article avec System 2 (en mode interactif, beaucoup de ce temps c'est toi qui valides)

Donc compter ~3h du clone à ton premier article ranked. La 2ème semaine, c'est 30 min par article.

### J'ai un problème, comment je debug ?

1. Vérifie `.mcp.json` : tes creds sont bien là, pas de fautes de frappe
2. Vérifie que Claude Code charge les MCPs : dans la session Claude, tape `/mcp` pour voir le statut
3. Vérifie les permissions : `.claude/settings.local.json` doit pré-autoriser les outils
4. Pour les erreurs Python : regarde la sortie du coordinator (`/tmp/seo-*.log` pour les runs scheduled)

---

## License

MIT. Utilise ce projet comme tu veux : commercial, perso, fork, vendu en formation, etc.

## Contribuer

Pull requests bienvenues. Pour signaler un bug ou proposer une fonctionnalité, ouvre une issue.

---

> **Le système est fait pour évoluer avec ton business.** Plus tu nourris `context/experience-notes.md` avec de vraies histoires et de vrais chiffres, meilleurs sont les articles. Plus tu fais tourner les 4 systèmes longtemps, plus le dashboard accumule de signal stratégique.
>
> Le dashboard à l'écran et un café le lundi matin, c'est tout ce qu'il te faut pour piloter le SEO d'un site en 2026.
