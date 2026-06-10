# context/ — ton contexte business

Ce dossier doit contenir **9 fichiers** qui décrivent ton site web et ton business. Les 4 agents les lisent à chaque run.

**Ce dossier est volontairement vide à l'installation.** Tu le remplis pour TON site. Tes fichiers ne seront jamais commités (le `.gitignore` les exclut).

## Deux façons de le remplir

### Option 1 — Onboarding guidé avec l'IA (recommandé pour la première fois)

1. Ouvre ce projet dans Claude Code : `cd the-four-systems && claude`
2. Claude détecte tout seul que le setup est incomplet et te propose l'onboarding. Sinon, tape :

   ```
   setup
   ```

3. L'onboarding couvre TOUT : tes clés API, l'identité du site, tes money pages, ta charte éditoriale (tu peux donner des exemples de bons et mauvais articles, en URL ou en PDF, qu'il analyse), le reste du contexte, et tes seed keywords. 30-45 minutes la première fois, interruptible et reprennable à tout moment.

Si tu veux seulement régénérer les fichiers de contexte (sans la partie clés API), tape `bootstrap my context folder` pour lancer l'interview seule.

### Option 2 — Édition manuelle

1. Copie les templates depuis `context-templates/` :

   ```bash
   cp ../context-templates/site-config.md.example context/site-config.md
   cp ../context-templates/audience.md.example context/audience.md
   cp ../context-templates/tone-of-voice.md.example context/tone-of-voice.md
   cp ../context-templates/experience-notes.md.example context/experience-notes.md
   cp ../context-templates/services.md.example context/services.md
   cp ../context-templates/brand-guidelines.md.example context/brand-guidelines.md
   cp ../context-templates/competitors.md.example context/competitors.md
   cp ../context-templates/author.md.example context/author.md
   cp ../context-templates/audit-urls.txt.example context/audit-urls.txt
   ```

2. Édite chaque fichier à la main pour adapter à ton business.

## Les 9 fichiers attendus

| Fichier | À quoi ça sert | Critique pour... |
|---|---|---|
| `site-config.md` | Identité, **locale** (target_country + target_language), in/out-scope topics, content type par défaut | Toutes les requêtes DataForSEO (locale) + filtrage des sujets |
| `audience.md` | Persona principal, niveau de compétence, ce qu'il déteste | Le ton et la profondeur des articles |
| `tone-of-voice.md` | Voix, règles de format, phrases bannies, exemple-modèle | Que les articles sonnent comme TOI, pas comme une IA générique |
| `experience-notes.md` | Vraies victoires chiffrées, histoires, opinions fortes | **LE fichier anti-AI-slop** — sans lui, articles génériques |
| `services.md` | Produits/services vendus, prix, FAQ | La détection des **money pages** dans le Business Value Score |
| `brand-guidelines.md` | Mots bannis, concurrents interdits, claims régulés | Le linter automatique des articles |
| `competitors.md` | Concurrents directs/indirects, content gaps | Le rédacteur sait quoi NE PAS dupliquer |
| `author.md` | Auteur officiel, credentials, profils sociaux | Le schema E-E-A-T injecté dans chaque article |
| `audit-urls.txt` | Les 3-10 URLs prioritaires à auditer techniquement | Le System 3 (onsite audit) |

## Le 10ème fichier (optionnel mais puissant) : `editorial-charter.md`

Pendant l'onboarding (`setup`), tu peux fournir des **exemples de bons et de mauvais articles** : des URLs, des PDFs, des fichiers markdown ou texte. L'IA les analyse (structure, voix, style de preuve, formatage) et génère `context/editorial-charter.md` : les patterns à reproduire, les anti-patterns interdits, et des règles de relecture supplémentaires.

Le rédacteur (System 2) lit ce fichier à chaque run quand il existe : les anti-patterns deviennent des échecs de relecture automatiques. C'est le moyen le plus direct d'imposer TA définition d'un bon article sans toucher aux prompts du système.

## Pourquoi ces fichiers sont gitignored

Ils contiennent des informations propres à ton business :
- Prix de tes produits
- Témoignages clients
- Opinions stratégiques internes
- Identité de tes auteurs
- Liste de tes concurrents interdits

Le `.gitignore` du projet exclut `context/*` automatiquement (sauf ce README et le `.gitkeep`). Si tu utilises ce projet sur plusieurs sites, tu auras un `context/` différent par instance, et aucun ne sera publié sur GitHub.

## Vérifier qu'il manque rien

Une fois le bootstrap fait, lance :

```bash
ls context/
```

Tu dois voir 9 fichiers (en plus de ce README et du `.gitkeep`). Si l'un manque, l'agent qui en a besoin échouera avec un message clair, t'indiquant comment le créer.
