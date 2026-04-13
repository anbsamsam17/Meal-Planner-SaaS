# KPI de Recherche — Beta v1 MealPlanner SaaS
> Phase 0 Discovery | Avril 2026 | Objectifs ROADMAP : 200 beta, J30 > 40%, NPS ≥ 4.0

---

## Introduction

Ces KPI constituent le tableau de bord de recherche pour la phase v1 (Mois 4-6 selon ROADMAP). Ils permettent de mesurer la santé produit, d'anticiper le churn et de valider les hypothèses UX avant le lancement payant en v2.

Chaque KPI est rattaché à : un objectif métier, une méthode de collecte, un seuil d'alerte, et une action corrective.

---

## Catégorie 1 — Activation

### KPI 1.1 — Taux de complétion onboarding
**Définition :** % d'utilisateurs ayant complété les 3 étapes onboarding ET soumis leur email
**Seuil d'alerte :** < 70%
**Cible v1 :** > 85%
**Méthode :** PostHog funnel `onboarding_started → email_submitted`
**Fréquence de revue :** Hebdomadaire
**Action corrective :** Si < 70%, analyser le drop par étape et itérer l'UI en 72h max

### KPI 1.2 — Time-to-First-Plan (TTFP)
**Définition :** Temps écoulé entre `onboarding_started` et `plan_generated` (premier plan semaine affiché)
**Seuil d'alerte :** > 3 minutes
**Cible v1 :** < 90 secondes
**Méthode :** PostHog — durée entre events
**Fréquence de revue :** Hebdomadaire
**Action corrective :** Si TTFP > 3 min → audit UX onboarding + performance API génération

### KPI 1.3 — Activation Rate (first plan generated)
**Définition :** % d'utilisateurs inscrits ayant généré au moins 1 plan semaine dans les 24h suivant l'inscription
**Seuil d'alerte :** < 50%
**Cible v1 :** > 75%
**Méthode :** PostHog — cohort J0 → `plan_generated` dans 24h
**Fréquence de revue :** Hebdomadaire
**Benchmark :** Mealime — 80%+ (estimé, source industrie)
**Action corrective :** Si < 50% → revoir le CTA post-inscription, ajouter un email de relance J+1

### KPI 1.4 — Taux de modification premier plan
**Définition :** % d'utilisateurs ayant swappé au moins 1 recette dans leur premier plan
**Seuil d'alerte :** > 80% (signal que l'IA recommande trop mal) OU < 10% (signal de passivité)
**Cible v1 :** 30-50% (engagement sain)
**Méthode :** PostHog — event `recipe_swapped` dans les 2h suivant `plan_generated`
**Action corrective :** Si > 80% → revoir l'algorithme WEEKLY_PLANNER, ajouter questions onboarding

---

## Catégorie 2 — Rétention

### KPI 2.1 — Rétention J7
**Définition :** % d'utilisateurs actifs au J7 (ont ouvert l'app ET généré ou consulté un plan)
**Seuil d'alerte :** < 40%
**Cible v1 :** > 55%
**Méthode :** PostHog — cohort retention D7
**Benchmark industrie :** Apps lifestyle/food : 35-45% D7 (data.ai 2024)
**Fréquence de revue :** Hebdomadaire
**Action corrective :** Si < 40% → analyser le motif (recettes refusées ? onboarding incomplet ?) → notification push J5 de relance

### KPI 2.2 — Rétention J14
**Définition :** % d'utilisateurs actifs au J14 (2e semaine complète d'utilisation)
**Seuil d'alerte :** < 35%
**Cible v1 :** > 45%
**Méthode :** PostHog — cohort retention D14
**Signal clé :** La chute J7→J14 est le signal CHURN le plus prédictif (ROADMAP section #08)
**Action corrective :** Si chute > 20 pts entre J7 et J14 → activer RETENTION_LOOP (email personnalisé + offre semaine découverte)

### KPI 2.3 — Rétention J30 (KPI ROADMAP principal)
**Définition :** % d'utilisateurs actifs au J30 (ont utilisé l'app au moins 3 semaines sur 4)
**Seuil d'alerte :** < 35%
**Cible v1 :** > 40% (objectif ROADMAP non-négociable pour passer à v2)
**Méthode :** PostHog — cohort retention D30
**Benchmark :** Jow (estimé) : ~35% J30. Notre cible : dépasser Jow grâce à la mémoire IA.
**Fréquence de revue :** Bi-hebdomadaire
**Action corrective :** Si < 35% → mobiliser RETENTION_LOOP + entretiens qualitatifs sur les churners

### KPI 2.4 — Plans générés par semaine par utilisateur actif
**Définition :** Nombre moyen de plans semaine générés par utilisateur actif sur la période de mesure
**Seuil d'alerte :** < 0.8 plan/semaine (indique usage occasionnel)
**Cible v1 :** > 1 plan/semaine (usage hebdomadaire régulier)
**Méthode :** PostHog — `plan_generated` / active users / semaines
**Action corrective :** Si < 0.8 → notification dimanche 19h à tester en A/B

---

## Catégorie 3 — Satisfaction

### KPI 3.1 — NPS (Net Promoter Score)
**Définition :** Score de recommandation (question "De 0 à 10, recommanderiez-vous MealPlanner ?")
**Seuil d'alerte :** < 25 (NPS brut) / < 3.5/5 (version simplifiée in-app)
**Cible v1 :** NPS ≥ 40 (ou ≥ 4.0/5 in-app — objectif ROADMAP)
**Méthode :** Enquête PostHog in-app (déclenchée à J14 et J30) + email mensuel
**Moment de déclenchement :** Après le 2e plan semaine généré (pas avant — biais négatif si trop tôt)
**Segmentation :** NPS par persona (famille avec enfants vs couple vs parent solo)
**Benchmark :** Mealime : NPS ~45 (estimé). Apps food/lifestyle US : NPS moyen 32.
**Fréquence de revue :** Mensuelle
**Action corrective :** Si NPS < 25 → séquence d'entretiens qualitatifs avec les détracteurs (score 0-6)

### KPI 3.2 — Satisfaction recette (CSAT)
**Définition :** Note moyenne donnée aux recettes cuisinées (1-5 étoiles ou emoji 3-niveaux)
**Seuil d'alerte :** < 3.5/5
**Cible v1 :** > 4.0/5
**Méthode :** In-app rating post-recette (déclenché après `recipe_cooked` ou le lendemain matin)
**Fréquence de revue :** Hebdomadaire
**Action corrective :** Si < 3.5 → audit des recettes les moins bien notées → suppression ou reformulation

### KPI 3.3 — Taux de réponse au premier feedback recette
**Définition :** % d'utilisateurs ayant noté au moins 1 recette dans la première semaine d'usage
**Seuil d'alerte :** < 20%
**Cible v1 :** > 40%
**Méthode :** PostHog — event `recipe_rated` dans J1-J7
**Importance :** Le feedback est le carburant de TASTE_PROFILE — sans lui, l'IA ne peut pas apprendre
**Action corrective :** Si < 20% → rendre la notation plus visible (nudge visuel J+2), réduire la friction (emoji au lieu d'étoiles)

---

## Catégorie 4 — Engagement produit

### KPI 4.1 — DAU/WAU ratio (stickiness)
**Définition :** Ratio utilisateurs actifs journaliers / hebdomadaires — mesure l'habitude créée
**Seuil d'alerte :** < 15%
**Cible v1 :** > 25%
**Méthode :** PostHog — DAU / WAU par semaine
**Benchmark :** Apps lifestyle : 20-30%. Apps meal planning : ~20% (estimé)
**Action corrective :** Si < 15% → l'app n'est utilisée que le dimanche. Ajouter des micro-interactions quotidiennes (notification "Votre dîner ce soir : Poulet basquaise — recette ici")

### KPI 4.2 — Taux d'utilisation de la liste de courses
**Définition :** % d'utilisateurs ayant consulté la liste de courses générée dans la semaine suivant le plan
**Seuil d'alerte :** < 50%
**Cible v1 :** > 70%
**Méthode :** PostHog — event `shopping_list_opened` dans les 7 jours suivant `plan_generated`
**Action corrective :** Si < 50% → la liste n'est pas trouvée ou pas utile → revoir l'UX navigation

### KPI 4.3 — Taux de partage liste famille
**Définition :** % d'utilisateurs ayant partagé leur liste de courses avec un autre membre du foyer
**Seuil d'alerte :** —
**Cible v1 :** > 20% (feature secondaire en v1)
**Méthode :** PostHog — event `list_shared`
**Note :** Le partage est un signal viral fort — chaque partage = invitation potentielle

### KPI 4.4 — Taux d'import recette URL (feature Paprika)
**Définition :** % d'utilisateurs ayant importé au moins 1 recette depuis une URL externe (Marmiton, 750g…)
**Seuil d'alerte :** —
**Cible v1 :** > 15%
**Méthode :** PostHog — event `recipe_imported_from_url`
**Action :** Si > 30% → monter en priorité la v1.1, ajouter des sources pré-intégrées (Marmiton, 750g)

---

## Catégorie 5 — Churn & rétention avancée

### KPI 5.1 — Taux de churn hebdomadaire
**Définition :** % d'utilisateurs n'ayant pas utilisé l'app pendant 2 semaines consécutives
**Seuil d'alerte :** > 15%/semaine
**Cible v1 :** < 10%/semaine
**Méthode :** PostHog — absence d'event pendant 14j → tag `churned_risk`
**Action corrective :** Activation RETENTION_LOOP : push J5 sans activité + email J7 + offre J14

### KPI 5.2 — Motifs de churn déclarés
**Définition :** Raisons invoquées lors de la désinstallation ou du non-renouvellement
**Méthode :** Exit survey (in-app ou email) — 3 questions max
  - Q1 : "Pourquoi avez-vous arrêté ?" (5 choix + libre)
  - Q2 : "Qu'est-ce qui vous ferait revenir ?"
  - Q3 : NPS final
**Catégories à surveiller :** Recettes non adaptées / Trop cher / Trop complexe / Drive non intégré / Autre app
**Cible :** 30%+ de réponses aux exit surveys

---

## Dashboard de suivi recommandé

### Revue hebdomadaire (équipe produit)
- Activation Rate
- TTFP
- Rétention J7 (cohorte de la semaine précédente)
- Plans générés / actifs
- CSAT recettes

### Revue mensuelle (avec stakeholders)
- Rétention J30 (cohorte du mois précédent)
- NPS
- Churn rate
- Taux de complétion onboarding
- Motifs de churn déclarés

### Seuil de go/no-go pour passage à v2 (lancement payant)
Toutes ces conditions doivent être remplies simultanément :
- 200 beta users actifs (J30)
- Rétention J30 > 40%
- NPS ≥ 4.0/5 (ou NPS brut ≥ 40)
- CSAT recettes ≥ 4.0/5
- Taux de complétion onboarding > 80%
- 0 bug critique remonté non résolu

---

## Outils de collecte recommandés

| KPI | Outil | Configuration |
|---|---|---|
| Funnel onboarding | PostHog | Events normalisés (cf. onboarding-protocol.md) |
| Rétention J7/J14/J30 | PostHog | Cohort analysis automatique |
| NPS | PostHog Surveys | Déclenchement post J14 + J30 |
| CSAT recettes | In-app custom | Widget post-repas (lendemain 8h) |
| Exit survey | Typeform embedé | Déclenché à la désinstallation |
| Sessions utilisateurs | Hotjar / Clarity | Heatmaps + session recordings |
| Entretiens qualitatifs | Lookback.io | Sessions J7 et J30 avec churners |
