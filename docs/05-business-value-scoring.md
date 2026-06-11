# System cross-cutting — Business Value Score (BVS)

> Cette doc est l'explication **utilisateur** de la BVS. Pour la spec technique (formule exacte appliquée par les agents), voir [`prompts/_business-value-scoring.md`](../prompts/_business-value-scoring.md).

## Le problème que la BVS résout

Avant la BVS, le système classait les mots-clés et les pages par **volume de recherche**. Plus de volume = plus de priorité. C'est la logique SEO classique des années 2010.

En 2026, cette logique est cassée. Voici pourquoi, avec un scénario que tu peux mesurer sur n'importe quel site dans Google Search Console :

| Page typique d'un site B2B | Impressions / mois | CTR | Clics réels |
|---|---:|---:|---:|
| Page "qu'est-ce qu'un CRM" | 90 000 | 0.4 % | ~360 |
| Page "quelle heure est-il a New York" | 60 000 | 0.3 % | ~180 |
| Page "convertir des miles en km" | 40 000 | 0.5 % | ~200 |
| Page produit "logiciel CRM pour PME" | 900 | 5.0 % | ~45 |

Sous l'ancien système, les 3 premières pages sont des "succès SEO". Sous la BVS, on les voit comme ce qu'elles sont : **des pièges zero-click**. Google donne la réponse directement dans la SERP (Knowledge Graph, AI Overview, calculatrice intégrée), l'utilisateur n'a aucune raison de cliquer. La 4ème page, au contraire, génère ~45 clics par mois mais ces clics vont **directement** vers la page d'achat — un ratio commercial radicalement meilleur.

La BVS répond à une seule question : **"Si on rank sur ce mot-clé, est-ce que ça apporte un client ou pas ?"**

## Comment la BVS est calculée (en plain English)

Une note de 0 à 10, qui combine 5 ingrédients :

1. **Intent score** (0 à 4) — c'est quoi le but de la recherche ?
   - "acheter X", "comparer X vs Y" → 3-4 points (commercial / transactionnel)
   - "qu'est-ce que X", "comment marche X" → 1 point (informationnel)
   - Marque ("ton-produit login") → 2 points si c'est TA marque, 0 sinon

2. **Signaux commerciaux SERP** (0 à +4) — Google montre-t-il des signes d'argent ?
   - Annonces payantes (Google Ads) présentes → +1
   - Carrousel Shopping → +2
   - Pack local → +2
   - Pas de signaux commerciaux → 0

3. **CPC** (0 à +2) — combien les concurrents payent en ads
   - ≥ 5 € / clic → +2 (gros enjeu commercial)
   - 1 à 5 € → +1
   - < 1 € → 0

4. **Match money page** (0 à +3) — le sujet recoupe-t-il un produit/service vendu ?
   - Full match (sujet = produit vendu) → +3
   - Partial match (sujet adjacent) → +1
   - Pas de lien → 0

5. **Pénalité direct-answer** (0 à -4) — Google donne-t-il déjà la réponse ?
   - Knowledge Graph factoid (ex: "quelle heure est-il a Tokyo" → Google affiche l'heure directement) → -4
   - Instant answer / calculatrice / conversion → -4
   - Featured snippet qui répond complètement → -2
   - AI Overview qui mange l'espace organique → -2

**Total = clamp(somme des 5 composantes, entre 0 et 10).**

## La règle du zero-click trap

C'est la règle qui force `BVS = 0` même si les autres scores donneraient quelque chose. Elle se déclenche quand les **3 conditions** suivantes sont **toutes** vraies :

1. L'intent est `informational` ou `ambiguous` (pas commercial)
2. La SERP a UN parmi : Knowledge Graph factoid, instant answer box, featured snippet complet
3. **Pas de match money page** (le sujet n'est pas adjacent à un produit vendu)

Si les 3 conditions sont remplies → `zero_click_trap: true`, `BVS = 0`, action : ne jamais queuer pour rédaction. Pour les pages existantes → action `consider_consolidate_or_remove`.

### Contre-exemple : pourquoi "logiciel CRM pour PME" n'est PAS un trap (si tu vends un CRM)

Sur la SERP de cette requête, on trouve typiquement un Knowledge Graph (pour une marque concurrente) ET un answer box. On pourrait croire que c'est un piège. Mais :
- Intent = commercial (pas informational) → la première condition tombe
- Money page match = full (si ton site vend exactement ça) → la troisième condition tombe

Conclusion : pas de trap. BVS final ≈ 7. Le système écrit l'article en priorité.

C'est exactement la logique qui permet à la BVS de distinguer "requête commerciale avec SERP encombrée" (à viser) de "requête factuelle avec SERP qui donne la réponse" (à éviter).

## Comment lire la BVS sur le dashboard

| BVS | Couleur | Que faire |
|---|---|---|
| 8-10 | 🟢 vert lime | High-value commercial. Cible en priorité, queue pour rédaction immédiatement. |
| 5-7 | 🟡 jaune ambre | Support utile. Queue quand le budget rédacteur le permet. |
| 2-4 | 🔵 bleu ciel | Park dans la bank. À ne chasser que si autorité topique justifie. |
| 0-1 | 🔴 rouge | Zero-click trap ou hors business. Skip. |

Sur chaque onglet du dashboard tu vois :
- Onglet **Keywords** : distribution des BVS dans la bank + colonne BVS dans le tableau
- Onglet **Queue** : pill BVS sur chaque carte d'article à rédiger
- Onglet **Onsite** : colonne BVS pour chaque URL auditée, panel "Strategic concerns" pour les zero-click traps
- Onglet **Refresh** : colonne BVS pour chaque candidat refresh, action `consolidate or remove` pour les BVS ≤ 1

## Ce que la BVS change concrètement pour ton workflow

**Avant** :
- Le système te queuait "qu'est-ce qu'un CRM" en priorité 1 (vol énorme, KD faible, super facile à ranker)
- Tu écrivais l'article, il rankait
- Tu te disais "j'ai 90k impressions / mois, mission accomplie"
- Tu te demandais pourquoi le pipeline commercial ne bouge pas

**Après** :
- Le système marque "qu'est-ce qu'un CRM" en `skip` (BVS 0 ou 1, zero_click_trap)
- À sa place, il te queue "logiciel CRM pour PME" (BVS 9, commercial, lien naturel vers la money page)
- Tu écris cet article, qui reçoit beaucoup moins d'impressions (peut-être 900/mois) mais un CTR de 4-6%
- Et qui génère des leads parce qu'il funnelle vers `/produits/crm/`

C'est la philosophie : **moins de bruit, plus de signal commercial**.

## Limites connues de la BVS

1. **La BVS est conservative au layer 1 (Python)**. Le scorer Python ne fait pas d'appel SERP. Il ne voit donc pas le Knowledge Graph, l'AI Overview, etc. Sa BVS est "partielle" (`bvs_components_partial: true`). C'est le layer 2 (prompt Claude qui appelle DataForSEO SERP) qui complète et finalise.

2. **La pénalité direct-answer dépend d'un appel SERP**. Sans crédits DataForSEO, la BVS est incomplète et certaines pages zero-click traps passeront à travers.

3. **Les sites multilingues** ont une SERP par locale. Si ton site a des versions FR / EN / DE, chaque version doit être scorée avec la bonne `location` + `language_code` (lus depuis `context/site-config.md`).

4. **L'intent inférence** au layer 1 est URL-based (regex sur `/services/`, `/blog/`, `/buy/`, etc.). C'est rapide mais peut se tromper. Le layer 2 (Claude prompt) raffine via la SERP.

5. **La BVS ne remplace pas le jugement humain**. Une page BVS 9 peut être terrible si elle est mal écrite. Une page BVS 2 peut servir une stratégie d'autorité topique. Le dashboard montre le score, c'est à toi de valider chaque décision.

## En une phrase pour expliquer la BVS à un non-tech

> "C'est une note de 0 à 10 qui dit : si on rank sur ce mot-clé, est-ce qu'on gagne un client ? 10 = oui, gros enjeu commercial. 0 = non, Google répond déjà à la place de l'utilisateur, on perdrait notre temps."
