# Benchmark UX Comparatif — Concurrents Meal Planning
> Phase 0 Discovery | MealPlanner SaaS | Avril 2026

---

## Méthode d'analyse

Évaluation sur 4 critères : Onboarding, UX planning semaine, UX liste de courses, Gaps identifiés.
Note sur 5. Sources : tests produits directs (AppStore/Play), reviews, analyse concurrentielle ROADMAP.

---

## 1. Jow (France) — Concurrent direct

**Statut :** Actif | 9M utilisateurs FR | Gratuit (affiliation)

### Onboarding
- **Étapes :** 5-6 questions (taille foyer, adultes/enfants/animaux, régimes, allergies, enseigne)
- **Temps estimé :** 90-120 secondes
- **Qualité UX :** Bon. Progression claire, illustrations friendly. Pas de barre de progression.
- **Frein identifié :** Question sur les animaux domestiques (irrelevante pour les recettes) — signe de collecte data publicitaire, pas UX
- **Note onboarding :** 3.5/5

### UX Planning semaine
- Génération automatique de 4-5 recettes par semaine
- Swipe pour accepter/refuser chaque recette — intuitif
- Pas de vue calendrier : recettes présentées en liste, pas en planning
- Recettes limitées (~5 000) → répétitions fréquentes après 6-8 semaines
- Pas de mémoire des goûts : pas d'apprentissage progressif
- **Note planning :** 3/5

### UX Liste de courses
- Liste auto-générée regroupée par rayon : point fort majeur
- Synchronisation drive (Leclerc, Auchan, Carrefour, Intermarché) directe — leader du marché
- Modification des quantités possible
- Partage famille : non documenté (liste individuelle)
- **Note liste de courses :** 4.5/5

### Gaps exploitables
- Aucune mémoire des goûts / apprentissage IA
- Base recettes limitée → lassitude à 6-8 semaines → churn
- Pas de profils enfants détaillés
- Pas de mode frigo / anti-gaspi
- Pas de PDF hebdomadaire
- Monétisation affiliation = pas d'expérience premium possible
- **Gap stratégique :** Le segment "prêt à payer" (9,99€/mois) est totalement ignoré par Jow

---

## 2. Mealime (USA) — Référence mondiale UX

**Statut :** Actif | Freemium → Pro 3$/mois | Anglais uniquement

### Onboarding
- **Étapes :** 3 questions + email
- **Temps estimé :** 45-60 secondes — BENCHMARK INDUSTRIEL
- Q1 : Combien de personnes ? Q2 : Régimes alimentaires ? Q3 : Temps de cuisine ?
- Progression visuelle claire (3 points), pas de compte requis avant de voir la valeur
- Première recette visible avant inscription email → "valeur avant engagement"
- **Note onboarding :** 5/5 — référence absolue

### UX Planning semaine
- Interface card-based : une recette = une card
- Sélection manuelle (pas de génération auto) → effort plus important
- Filtres : régime, temps, calories — efficaces
- Pas de vue calendrier sur 7 jours
- Pas de suggestions basées sur l'historique
- Recettes limitées (<30 min) — positionnement "semaine chargée"
- **Note planning :** 3.5/5

### UX Liste de courses
- Liste groupée par rayon : meilleure implémentation du marché
- Cochage individuel des items — intuitif
- Partage famille : oui (basic)
- Pas d'intégration drive FR → blocant pour la France
- **Note liste de courses :** 3.5/5 (sans drive FR)

### Gaps exploitables
- Pas d'IA générative ni de mémoire des goûts
- Pas de version française
- Pas d'intégration drive Europe
- Pas de profils multi-membres famille
- Sélection recettes manuelle = effort utilisateur
- Pas de PDF ou de contenu "tangible"
- **Leçon principale :** L'onboarding en 3 questions / 60 secondes est LE standard à atteindre

---

## 3. PlateJoy (USA) — [FERMÉ en 2025]

**Statut :** Fermé depuis 2025 (racheté par RVO Health, service arrêté)

### Onboarding (analyse post-mortem)
- **Étapes :** Quiz de 50 points de données
- **Temps estimé :** 8-15 minutes
- Couvrait : objectifs santé, IMC, conditions médicales, cuisine, appareils, budget, emploi du temps
- Très personnalisé mais taux d'abandon élevé (non communiqué)
- **Note onboarding :** 2/5 (trop long pour le grand public)

### UX Planning semaine
- Meilleure personnalisation du marché — plan 100% adapté aux 50 critères
- Gestion pantry/frigo réelle : pionnier du mode anti-gaspi
- Interface datée mais fonctionnelle
- Intégration Instacart (US) efficace
- **Note planning :** 4/5 (si l'utilisateur survivait à l'onboarding)

### Gaps exploitables (leçons de sa mort)
- L'onboarding trop long = mort produit : les utilisateurs abandonnent avant de voir la valeur
- La personnalisation avancée ne doit pas bloquer l'entrée — construire progressivement
- Sans marché FR = impossible à reproduire direct
- **Leçon principale :** Onboarding progressif — 3 questions au départ, enrichissement au fil des semaines

---

## 4. eMeals (USA) — Meilleure intégration grocery

**Statut :** Actif | 5-10$/mois | Anglais uniquement

### Onboarding
- **Étapes :** 4 étapes (type de plan alimentaire, taille du foyer, enseigne grocery)
- **Temps estimé :** 2-3 minutes
- Sélection du plan parmi 15 catégories (Clean Eating, Keto, Budget, Rapide…)
- **Note onboarding :** 3.5/5

### UX Planning semaine
- Menus hebdo curatés par diététiciens — qualité garantie
- Peu de personnalisation individuelle — "one size fits family"
- Interface claire, semaine visible d'un coup
- Swap de recettes possible mais limité
- **Note planning :** 3.5/5

### UX Liste de courses
- Meilleure implémentation grocery du marché hors France
- Envoi en 1 clic vers Walmart, Instacart, Shipt
- Groupage par rayon excellent
- Modification possible avant envoi
- **Note liste de courses :** 4.5/5

### Gaps exploitables
- Pas d'IA / pas de mémoire
- Pas de version FR / pas de drive FR
- Menus figés = pas de personnalisation goûts individuels
- **Leçon principale :** L'expérience "1 clic → panier drive" est le moment de vérité. Reproduire cette fluidité avec les drives FR.

---

## 5. Paprika (USA/International) — Référence organisation recettes

**Statut :** Actif | One-time 4,99-29,99€ | Partiellement FR

### Onboarding
- **Étapes :** 1 étape (création compte ou import depuis autre Paprika)
- **Temps estimé :** 30 secondes
- Pas d'onboarding guidé — utilisateur lâché dans l'app
- **Note onboarding :** 2/5 (trop peu guidé pour les non-experts)

### UX Planning semaine
- Planning manuel complet : drag-and-drop des recettes sur un calendrier
- Pas de suggestions auto / pas d'IA
- Import depuis n'importe quel site web : fonctionnalité star
- Synchronisation multi-device excellente
- **Note planning :** 3/5 (effort manuel mais puissant)

### UX Liste de courses
- Génération depuis les recettes du planning
- Groupage par rayon configurable
- Pas d'intégration drive
- **Note liste de courses :** 3/5

### Gaps exploitables
- Pas d'IA / pas de suggestions automatiques
- Pas d'intégration drive
- Onboarding difficile pour les non-experts
- Fidélité extrême mais croissance limitée
- **Leçon principale :** L'import de recette depuis une URL est une fonctionnalité très attendue — intégrer dès v1

---

## 6. Petit Citron (France) — Concurrent FR santé

**Statut :** Actif | Freemium | Français natif

### Onboarding
- **Étapes :** 4-5 questions (objectif santé, régime, allergies, taille foyer)
- **Temps estimé :** 2 minutes
- Focus sur l'aspect santé/poids — positionnement différent de MealPlanner
- **Note onboarding :** 3/5

### UX Planning semaine
- Menus équilibrés générés automatiquement — bon point
- Faible diversité culinaire — recettes françaises classiques dominantes
- Pas d'IA mémorielle — mêmes recettes cycliques
- UX datée : interface fonctionnelle mais pas inspirante
- **Note planning :** 2.5/5

### UX Liste de courses
- Liste générée automatiquement
- Pas de drive intégré — major gap sur le marché FR
- **Note liste de courses :** 2.5/5

### Gaps exploitables
- Pas de drive intégré = opportunité directe
- UX datée = opportunité esthétique
- Pas d'IA = différenciation majeure disponible
- **Leçon principale :** Le marché FR premium meal planning reste vide. Petit Citron ne monétise pas efficacement.

---

## Tableau comparatif synthétique

| Critère | Jow | Mealime | PlateJoy | eMeals | Paprika | Petit Citron | **MealPlanner cible** |
|---|---|---|---|---|---|---|---|
| Onboarding (étapes) | 5-6 | **3** | 50 | 4 | 1 | 4-5 | **3 max** |
| Onboarding (temps) | 90s | **45s** | 10min | 2min | 30s | 2min | **< 90s** |
| IA mémorielle | Non | Non | Partielle | Non | Non | Non | **Oui** |
| Drive FR intégré | **Oui** | Non | Non | Non | Non | Non | **Oui (v3)** |
| PDF hebdomadaire | Non | Non | Non | Non | Non | Non | **Oui (v2)** |
| Profils famille | Basique | Non | Oui | Basique | Non | Basique | **Avancé** |
| Mode frigo | Non | Non | Basique | Non | Non | Non | **Oui (v2)** |
| Version FR | **Oui** | Non | Non | Non | Partiel | **Oui** | **Oui natif** |
| Prix | Gratuit | 3$/mois | Fermé | 5-10$ | 5-30€ | Freemium | **9,99€/mois** |

---

## Conclusions actionnables

### Ce qu'on DOIT reproduire (must-haves)
1. **Onboarding Mealime** : 3 questions, < 90 secondes, valeur visible AVANT l'inscription email
2. **Drive Jow** : intégration Leclerc/Auchan/Intermarché en 1 clic — LE différenciateur de rétention
3. **Liste par rayon Mealime/eMeals** : groupage automatique, cochage temps réel, partage famille
4. **Import URL Paprika** : recette importée depuis Marmiton en 1 clic — demande forte identifiée
5. **Plans diets eMeals** : 5-6 profils alimentaires clairs à l'onboarding (végé, sans gluten, rapide, budget…)

### Ce qu'on doit ÉVITER absolument
1. **Onboarding PlateJoy** : 50 questions = mort. Aucune question facultative en onboarding v1.
2. **Absence de mémoire Jow** : sans apprentissage IA, le churn post J30 est inévitable (répétitions)
3. **UX datée Petit Citron** : dans un marché où l'esthétique = perception de qualité, c'est rédhibitoire
4. **Sélection manuelle seule Paprika** : trop d'effort côté utilisateur. Génération auto obligatoire.
5. **Monétisation affiliation seule Jow** : le modèle gratuit/affiliation empêche l'investissement UX premium

### Différenciation réelle disponible
La combinaison IA mémorielle + drive FR natif + PDF hebdo + profils famille avancés n'existe chez AUCUN concurrent. C'est une fenêtre d'opportunité réelle, confirmée par le vide laissé par PlateJoy (fermé 2025) et les limites de Jow.
