# ROADMAP — MealPlanner SaaS

> **Ce fichier est la source de vérité du projet.** Tous les agents IA doivent le lire avant d'entreprendre toute tâche de développement. Il définit la vision produit, l'architecture technique, les phases de développement, les priorités et les contraintes.

---

## Vue d'ensemble

| Paramètre | Valeur |
|---|---|
| Durée totale | 18 mois |
| Phases | 5 (v0 → v4) |
| Agents IA | 6 |
| Recettes cibles | 50 000+ |
| Prix principal | 9,99 €/mois |
| Marché cible | Familles françaises B2C |

**Positionnement :** Planificateur de dîners hebdomadaires avec commande drive intégrée. Le Jow premium — IA générative, base de recettes mondiale, PDF hebdomadaire, mémoire des goûts, mode frigo anti-gaspi.

---

## 01 — Analyse concurrentielle

### Jow 🇫🇷 — Concurrent direct
- **Tagline :** "L'app française qui fait tes courses" — 9M utilisateurs, 33M€ levés
- **Forces :** Drive intégré (Leclerc, Auchan, Carrefour…), free to use, forte notoriété FR
- **Failles :** Recettes limitées (~5 000), pas d'IA générative, pas de livre PDF, gratuit = monétisation affiliés uniquement
- **Modèle :** Affiliation supermarchés (GRATUIT pour l'user). Pas d'abonnement.
- **Leçon :** La preuve que le drive intégré fonctionne en France. Notre différence = IA + premium

### Mealime 🇺🇸 — Référence mondiale
- **Tagline :** "Plans rapides, liste organisée par rayon" — Pro à 3$/mois
- **Forces :** UX minimaliste et intuitive, listes organisées par rayon, recettes <30 min
- **Failles :** Dîners uniquement, pas d'IA générative, pas de mémoire des goûts, pas disponible en français
- **Modèle :** Freemium → Pro 3$/mois. Intégration Instacart, Walmart.
- **Leçon :** La simplicité bat la richesse de features. Ne jamais complexifier l'onboarding.

### PlateJoy 🇺🇸 — Premium · Personnalisation
- **Tagline :** "50 data points à l'onboarding, pantry tracker, Instacart" — 10$/mois
- **Forces :** Hyper-personnalisation (50 critères), gestion du frigo/pantry, réduction du gaspi
- **Failles :** Onboarding trop long → abandon, pas de version française, pas d'IA générative
- **Modèle :** Abonnement 10-12$/mois. Intégration Instacart/Amazon Fresh.
- **Leçon :** La personnalisation avancée a de la valeur mais ne doit pas bloquer l'entrée.

### eMeals 🇺🇸 — Meilleure intégration grocery
- **Tagline :** "Dîner + panier en 1 clic" — partenariats Walmart, Kroger, Instacart
- **Forces :** 15 plans diets, menus hebdo curatés par diététiciens, intégration drive la plus fluide du marché
- **Failles :** Pas d'IA, menus figés (peu de personnalisation), anglais uniquement
- **Modèle :** 5-10$/mois selon plan. Meilleur benchmark pour l'expérience drive.
- **Leçon :** Le "1 clic → panier" est le feature le plus transformateur. C'est LE moment de vérité.

### Paprika 🇺🇸 — Référence organisation
- **Tagline :** "Votre bibliothèque de recettes personnelle" — one-time purchase
- **Forces :** Importation depuis n'importe quel site, offline, liste organisée par rayon, cross-device sync
- **Failles :** Pas de suggestion IA, pas de drive, pas de planning auto, pas de version FR
- **Modèle :** One-time 4,99-29,99€. Fidélité extrême, pas de churn.
- **Leçon :** L'import de recettes depuis le web = feature très demandée à implémenter dès v1.

### Petit Citron 🇫🇷 — Concurrent FR · Santé
- **Tagline :** "Menus équilibrés + courses en 5 min" — app française
- **Forces :** Français natif, focus nutrition équilibrée, menus familiaux
- **Failles :** Pas de drive intégré, peu de diversité culinaire, pas d'IA, UX datée
- **Modèle :** Freemium. Marché FR peu monétisé.
- **Leçon :** Le marché FR premium meal planning reste VIDE. Jow gratuit ne répond pas aux besoins avancés.

### Gaps du marché identifiés

- Aucune app française ne combine : IA générative + drive intégré + livre PDF hebdomadaire + mémoire famille
- Jow est gratuit (affiliation) → pas de premium expérience. Notre cible = utilisateurs prêts à payer 9,99€/mois
- Aucun acteur ne propose de recettes mondiales (50 000+) avec filtres culturels précis
- Le "mode utiliser les restes" n'est implémenté sérieusement par aucun acteur français
- La gestion "frigo actuel" est absente en France
- Yummly est mort (déc. 2024) → 20M d'utilisateurs sans app. Fenêtre d'opportunité ouverte

---

## 02 — Éléments différenciants

Ces 6 piliers sont non-négociables. Aucune décision de développement ne doit les affaiblir.

### 1. Base de recettes mondiale 🌍
50 000+ recettes scrappées et structurées depuis Marmiton, Allrecipes, NYT Cooking, Serious Eats, bases API (Spoonacular, Edamam), et sources ethniques (japonais, mexicain, indien, libanais…). Vecteurs d'embedding pour recherche sémantique. Aucun concurrent FR n'a cette profondeur.
- Technologie : Base vectorielle pgvector, sentence-transformers

### 2. IA mémorielle des goûts 🧠
Chaque retour utilisateur (note, skip, "on a adoré") entraîne le profil de goût famille. Après 4 semaines, l'IA connaît mieux les goûts que le couple lui-même. Profils individuels par membre du foyer.
- Technologie : Collaborative filtering + content-based hybrid, fine-tuning

### 3. Drive FR natif 🛒
Intégration directe Leclerc Drive, Auchan Drive, Intermarché Drive, Carrefour. Le panier se remplit en 1 clic depuis l'app. Substitution intelligente si produit indisponible. C'est le feature qui crée la rétention long terme.
- Technologie : Affiliation + API partenaires

### 4. Livre de recettes hebdomadaire 📚
Chaque dimanche, génération automatique d'un PDF/print imprimable : les 5-7 recettes de la semaine, avec photos générées, liste de courses, infos nutritionnelles, niveau de difficulté. Objet "tangible" à forte valeur perçue.
- Technologie : WeasyPrint + Jinja2 + Stability AI

### 5. Mode frigo & anti-gaspi 🥦
Scan des produits du frigo (photo ou saisie). L'IA propose des recettes qui utilisent l'existant en priorité. "Restes du lundi" → recette du mardi. Réduction prouvée du gaspi alimentaire de 20-30%.
- Technologie : OCR + Vision AI (GPT-4o Vision ou Claude Vision)

### 6. Profils multi-membres 👨‍👩‍👧
Chaque membre du foyer a ses propres restrictions, goûts et modes (enfants capricieux, sportif, végétarien, allergie). La planification réconcilie les contraintes automatiquement. Partage en temps réel de la liste de courses.
- Technologie : Multi-profil, Supabase Realtime

---

## 03 — Base de recettes : stratégie

### Sources de données

| Source | Volume | Usage |
|---|---|---|
| Spoonacular API | ~380 000 recettes | Base de départ, données nutritionnelles |
| Edamam API | ~2M recettes | Couverture internationale, nutrition précise |
| Marmiton (scraping) | ~70 000 recettes FR | Recettes françaises authentiques, notes |
| Open Food Facts | ~3M produits | Lien recette → produit drive → panier |
| Web scraping ciblé | ~30 000 recettes | NYT Cooking, Serious Eats, 750g, Ricardo |
| LLM Generation | Illimité | Recettes on-demand, variations, cuisines rares |

### Pipeline de traitement

1. **Normalisation** : ingrédients → format canonique (nom, quantité, unité, catégorie)
2. **Embedding vectoriel** : OpenAI text-embedding-3 ou sentence-transformers → stockage pgvector
3. **Tagging automatique** : temps, difficulté, cuisine, régime, saison, budget estimé (via LLM)
4. **Mapping produit** : ingrédient → Open Food Facts → SKU enseigne drive
5. **Déduplication** : similarité cosine > 0.92 → suppression des doublons inter-sources
6. **Validation qualité** : filtre LLM avant insertion en base (recette incomplète = rejet)

### KPI données : 50 000 recettes dédupliquées, taggées, embedées avant le lancement v1

---

## 04 — Architecture des agents IA

Six agents orchestrés via **LangGraph**. Chaque agent est une classe Python indépendante avec une méthode `run()` claire.

### RECIPE_SCOUT
- **Rôle :** Collecte & enrichissement de recettes
- **Déclenchement :** Batch nocturne (Celery)
- **Responsabilités :** Scraping sources ciblées, normalisation, déduplication via embedding, tagging automatique, validation qualité LLM
- **Inputs :** URLs sources, configuration scraping
- **Outputs :** Recettes normalisées en PostgreSQL + embeddings pgvector

### TASTE_PROFILE
- **Rôle :** Moteur de recommandation personnalisé
- **Déclenchement :** Temps réel (après chaque feedback utilisateur)
- **Responsabilités :** Analyse des feedbacks (notes, skips, favoris), mise à jour vecteurs de préférence, détection patterns familiaux, gestion contraintes contradictoires
- **Modèle :** Collaborative filtering + content-based hybrid
- **Inputs :** Feedback utilisateur, profil famille
- **Outputs :** Vecteur de goût mis à jour, score de pertinence par recette

### WEEKLY_PLANNER
- **Rôle :** Planificateur hebdomadaire intelligent
- **Déclenchement :** À la demande (dimanche soir ou ouverture app)
- **Responsabilités :** Génération plan 5-7 dîners/semaine, contraintes (régimes, allergies, temps, budget, saison), anti-répétition, réutilisation des restes, équilibre nutritionnel
- **Inputs :** Profil famille, historique, préférences, stocks frigo
- **Outputs :** JSON plan semaine + liste de courses consolidée

### CART_BUILDER
- **Rôle :** Constructeur de panier drive
- **Déclenchement :** À la demande (après validation du plan semaine)
- **Responsabilités :** Mapping ingrédient → produit Open Food Facts → SKU enseigne, gestion substitutions si rupture, optimisation quantités (anti-gaspi), envoi panier API partenaire
- **Inputs :** Liste de courses, enseigne choisie, catalogue produits temps réel
- **Outputs :** Panier drive rempli + récapitulatif prix estimé

### BOOK_GENERATOR
- **Rôle :** Générateur du livre PDF hebdomadaire
- **Déclenchement :** Automatique chaque dimanche soir (Celery beat)
- **Responsabilités :** Compilation des 5-7 recettes, mise en page PDF (WeasyPrint + Jinja2), génération photos (Stability AI), calcul infos nutritionnelles, génération liste de courses imprimable
- **Inputs :** Plan semaine validé, profil famille
- **Outputs :** PDF stocké sur Cloudflare R2 + notification push à l'utilisateur

### RETENTION_LOOP
- **Rôle :** Anti-churn & engagement
- **Déclenchement :** Monitoring continu (Celery beat toutes les 4h)
- **Responsabilités :** Détection signaux de décrochage (inactivité 5j+, baisse taux d'ouverture), déclenchement notifications push personnalisées, emails de relance, gestion win-back (offre mois gratuit à J+30 sans activité)
- **Inputs :** Métriques d'engagement utilisateur (PostHog)
- **Outputs :** Notifications push, emails Resend, actions Stripe (pause/offre)

---

## 05 — Stack technique

### Backend
- Python 3.12
- FastAPI (API REST)
- Celery + Redis (tâches asynchrones et batch)
- Pydantic v2 (validation données)

### Base de données
- PostgreSQL 16 (données principales)
- pgvector extension (embeddings recettes)
- Supabase (auth + realtime WebSocket)
- Redis (cache + broker Celery)

### IA & LLM
- Claude API — claude-sonnet-4-5 (agent principal, génération, validation)
- LangGraph (orchestration des agents)
- sentence-transformers (embeddings locaux, coût zéro)
- Stability AI (génération photos recettes pour PDF)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- PWA (service worker, offline partiel)

### Scraping & Data
- Scrapy (scraping batch)
- Playwright (pages JavaScript-rendered)
- Spoonacular API
- Edamam API
- Open Food Facts (base produits FR)

### PDF Generation
- WeasyPrint (HTML → PDF)
- Jinja2 (templates)
- ReportLab (fallback, tableaux complexes)

### Infra & Deploy
- Railway ou Render (backend Python)
- Vercel (frontend Next.js)
- Cloudflare R2 (storage PDF + images)
- Sentry (monitoring erreurs)
- PostHog (analytics produit)

### Paiement & Auth
- Stripe (abonnements, webhooks)
- Supabase Auth (magic link + OAuth Google)

---

## 06 — Roadmap de développement

### v0 — Fondations (Mois 1–3)
**Objectif :** Zéro utilisateur. Tout le travail est invisible mais critique.  
**KPI de sortie :** 50 000 recettes dédupliquées, taggées, embedées en base.

#### Devs à prioriser (dans l'ordre)
1. Pipeline de scraping Marmiton + 750g + Allrecipes (Scrapy + Playwright)
2. Intégration Spoonacular API + Edamam API
3. Schéma PostgreSQL recettes + ingrédients normalisés
4. Embedding vectoriel (sentence-transformers → pgvector)
5. Pipeline de déduplication (similarité cosine, seuil 0.92)
6. Tagging automatique LLM (cuisine, régime, temps, difficulté, budget)
7. Mapping ingrédient → Open Food Facts

#### Agent actif
- **RECIPE_SCOUT** : scraping + normalisation + validation batch

#### Challenges v0
- ⚠️ Qualité des données scrappées très hétérogène → pipeline de validation obligatoire
- ⚠️ Mapping ingrédient → produit imparfait → base de correspondance manuelle initiale
- ⚠️ Coûts API Spoonacular/Edamam à surveiller (budgéter dès le départ)

---

### v1 — MVP (Mois 4–6)
**Objectif :** Lancement beta fermée.  
**KPI de sortie :** 200 beta users, rétention J30 > 40%, NPS ≥ 4.0/5.

#### Devs à prioriser (dans l'ordre)
1. Onboarding : profil foyer (taille, régimes, allergies, temps de cuisine) — max 3 étapes
2. Génération plan 5 dîners/semaine (WEEKLY_PLANNER)
3. Liste de courses consolidée (groupée par rayon)
4. Partage liste en temps réel (Supabase Realtime)
5. Fiches recettes complètes (instructions, photos, temps, difficulté)
6. Système de notation (1-5 étoiles + skip)
7. Import de recette depuis URL (parsing à la Paprika)
8. Auth + gestion multi-profils famille

#### Agents actifs
- **WEEKLY_PLANNER** : génération plan hebdo
- **TASTE_PROFILE** : initialisation profil + premières recommandations
- **RECIPE_SCOUT** : continue en fond

#### Challenges v1
- ⚠️ Churn post-J14 si les recettes proposées ne conviennent pas → feedback actif dès la semaine 1
- ⚠️ Onboarding : trouver l'équilibre (trop court = mauvaises reco, trop long = abandon)
- ⚠️ Partage liste temps réel : complexité technique à ne pas sous-estimer

---

### v2 — Différenciation (Mois 7–10)
**Objectif :** Lancement public payant.  
**KPI de sortie :** 500 payants, MRR 5 000€, churn mensuel < 5%.

#### Devs à prioriser (dans l'ordre)
1. Générateur PDF livre de recettes hebdomadaire (WeasyPrint + Jinja2)
2. Gestion "frigo actuel" : saisie manuelle + scan photo (Vision AI)
3. Mode "utiliser les restes" : recette J+1 basée sur restes J
4. Système de paiement Stripe + plans abonnement
5. Filtres avancés : budget semaine, temps de préparation, niveau
6. Notifications push hebdomadaires (dimanche soir)
7. Mode "cuisine du monde" : explorer par région géographique

#### Agents actifs
- **BOOK_GENERATOR** : PDF automatique chaque dimanche
- **TASTE_PROFILE** : modèle maturé (4+ semaines de data)
- **RETENTION_LOOP** : activation anti-churn
- **CART_BUILDER** : version beta (liste structurée sans intégration drive)

#### Challenges v2
- ⚠️ Générer un PDF de qualité suffisante = travail de mise en page non négligeable
- ⚠️ Scan frigo : reconnaissance fiable des produits → coûts API Vision à budgéter
- ⚠️ Conversion freemium → payant : moment de vérité commercial

---

### v3 — Intégration Drive (Mois 11–14)
**Objectif :** Feature de rétention principale, croissance accélérée.  
**KPI de sortie :** 5 000 payants, MRR 50 000€, 2 enseignes intégrées.

#### Devs à prioriser (dans l'ordre)
1. Partenariat affiliation Leclerc Drive (contact commercial direct)
2. Intégration API Auchan Drive (ou scraping panier si API indisponible)
3. CART_BUILDER v2 : mapping ingrédient → SKU + substitution automatique
4. Sélection de l'enseigne au niveau du profil utilisateur
5. Optimisation panier : mutualiser les ingrédients entre les recettes
6. Alerte prix produit (Nutriscore + comparatif prix)
7. Intégration Intermarché + Carrefour

#### Agents actifs
- **CART_BUILDER** : version production avec vraie intégration drive
- **WEEKLY_PLANNER** v2 : tient compte des promos enseigne de la semaine
- Tous les agents précédents en production

#### Challenges v3
- ⚠️ CRITIQUE : les enseignes n'ont pas d'API publique stable — Jow a mis 2 ans à négocier
- ⚠️ Stratégie : scraping panier en attendant les partenariats + démarche commerciale parallèle
- ⚠️ Commencer par Leclerc (API la plus accessible), puis Auchan

---

### v4 — Scale (Mois 15–18)
**Objectif :** App native, IA avancée, expansion internationale.  
**KPI de sortie :** 25 000 payants, MRR 250 000€, ARR 3M€.

#### Devs à prioriser (dans l'ordre)
1. App iOS/Android (React Native ou Flutter)
2. Mode vocal "qu'est-ce qu'on mange ce soir ?" (Whisper + TTS)
3. Coach nutrition IA (objectifs perte de poids, prise de muscle)
4. Intégration wearables (Apple Health, Garmin)
5. Expansion Belgique / Suisse (enseignes locales)
6. API B2B (nutrition apps, mutuelles, employeurs)

#### Nouveaux agents v4
- **NUTRITION_COACH** : suivi objectifs santé long terme
- **SEASONAL** : adaptation automatique aux saisons et aux promos
- **SOCIAL** : suggestions basées sur les tendances TikTok food

#### Challenges v4
- ⚠️ App native = budget significatif (React Native recommandé pour solo/petit dev)
- ⚠️ Mode vocal : expérience mémorable mais complexité élevée
- À ce stade : envisager une levée de fonds si 5 000+ payants actifs

---

## 07 — Modèle de monétisation

### Plans d'abonnement

#### Starter — Gratuit (v1, acquisition)
- 3 recettes/semaine
- Liste de courses basique
- Sans partage famille
- Sans PDF
- Sans drive intégré
- Objectif : convertir en payant après 2 semaines d'usage actif

#### Famille — 9,99€/mois ⭐ Plan principal (v2)
**Doit représenter 80% du CA.**
- 7 dîners/semaine générés par IA
- Profils multi-membres illimités
- Livre PDF hebdomadaire
- Liste partagée temps réel
- Mode frigo & anti-gaspi
- Mémoire des goûts
- Drive intégré (à partir de v3)

#### Coach — 14,99€/mois (v4, premium)
- Tout le plan Famille
- Tracking macros / calories
- Coach nutrition IA
- Intégration Apple Health
- Recommandations diététicien validées
- Support prioritaire

### Revenue secondaire : affiliation drive
- Modèle Jow : commission 1-3% sur chaque panier commandé via l'app
- Potentiel à 5 000 utilisateurs : 5 000 × 80€/panier/semaine × 2% = 400K€/an
- Ce revenu secondaire peut financer l'app même avec un pricing principal bas

---

## 08 — Challenges critiques

### #01 — Le churn après 4–6 semaines [CRITIQUE]
Les meal apps perdent 15-30% de leurs utilisateurs en mois 2 si les suggestions se répètent. Solution : IA mémorielle active dès la semaine 1, relance proactive J+5 si inactivité, option "surprise me" pour briser la routine.

### #02 — L'intégration drive sans API publique [CRITIQUE]
Leclerc, Auchan et Intermarché n'ont pas d'API partenaire accessible. Jow a mis 2 ans à négocier. Stratégie : scraping panier (fragile mais fonctionnel) + démarche commerciale parallèle dès les premiers utilisateurs.

### #03 — La qualité et diversité des recettes [IMPORTANT]
50 000 recettes de mauvaise qualité valent moins que 5 000 excellentes. Pipeline de validation rigoureux obligatoire (LLM + humain pour les premières centaines), photos attractives, vraie diversité culinaire mondiale.

### #04 — L'onboarding : le moment le plus fragile [IMPORTANT]
Trop court → mauvaises recommandations → churn J+7. Trop long → abandon avant d'avoir vu la valeur. Benchmark : Mealime 3 questions/60 secondes. Tester avec les 50 premiers beta users.

### #05 — Le mapping ingrédient → produit → panier [IMPORTANT]
"200g de lardons fumés" → quel produit exact chez Leclerc ? Quantité ajustée au format vendu ? Substitut si rupture ? Résolution : Open Food Facts + base locale + validation manuelle initiale.

### #06 — Différenciation vs Jow long terme [IMPORTANT]
Jow a 9M d'utilisateurs, 33M€ levés, les mêmes partenariats drive. Réponse : se différencier sur la qualité de l'IA (mémoire, diversité mondiale), le contenu premium (PDF, livre), et les profils famille avancés. Viser le segment "willing to pay" que Jow laisse intact.

---

## 09 — KPI par phase

| Phase | Période | Utilisateurs payants | MRR | Churn |
|---|---|---|---|---|
| v0 · Fondations | M1–M3 | 0 | 0€ | — |
| v1 · MVP Beta | M4–M6 | 200 beta | 0€ | — |
| v2 · Payant | M7–M10 | 500 | 5 000€ | <5%/mois |
| v3 · Drive | M11–M14 | 5 000 | 50 000€ | <3%/mois |
| v4 · Scale | M15–M18 | 25 000 | 250 000€ | <2%/mois |

**ARR run rate cible à M18 : 3 000 000€**

---

## 10 — Règles de développement

Ces règles s'appliquent à toutes les tâches de développement, sans exception.

1. **Code Python uniquement** pour le backend. Pas de Node.js côté serveur.
2. **Chaque fonction** doit avoir sa docstring, ses types hints, et ses tests unitaires (pytest).
3. **Chaque agent** est une classe Python indépendante avec une méthode `run()` claire.
4. **Les tâches longues** (scraping, embeddings batch) passent par Celery + Redis. Ne jamais bloquer le thread principal FastAPI.
5. **Logging structuré** sur toutes les tâches critiques (loguru). Niveau DEBUG pour le dev, INFO pour la prod.
6. **Variables d'environnement** pour toutes les clés API. Jamais de secret en dur dans le code.
7. **Git commits** : format conventionnel (`feat:`, `fix:`, `chore:`, `refactor:`).
8. **Priorité à la qualité des données** : une recette mal structurée vaut moins qu'une recette absente. Pipeline de validation LLM avant insertion.
9. **Tests** : couverture minimale de 80% sur les agents IA. Pytest + pytest-asyncio pour les tâches async.
10. **Documentation** : chaque agent doit avoir un README décrivant ses inputs, outputs et effets de bord.

---

## 11 — Note stratégique finale

La leçon principale de **Jow** (33M€ levés, gratuit, affiliation) et de **Yummly** (mort en déc. 2024 malgré 20M d'utilisateurs) est que la valeur réelle est dans l'expérience premium payante, pas dans le volume gratuit.

Viser un petit nombre d'utilisateurs très engagés qui paient 9,99€/mois vaut mieux que 1M de gratuits.

**La priorité absolue en v1 : ne pas lancer avant d'avoir les 50 premiers beta users satisfaits. Tout le reste découlera de ça.**

---

*Dernière mise à jour : Avril 2026 — v1.0*
