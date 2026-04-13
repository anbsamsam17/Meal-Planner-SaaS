# Protocole de Test Utilisateur — Onboarding MealPlanner
> Phase 0 Discovery | Avril 2026 | Benchmark Mealime : 3 questions / 60 secondes

---

## Contexte et objectif

L'onboarding est le moment le plus fragile du produit (ROADMAP section #08). Un onboarding trop long provoque l'abandon avant que l'utilisateur voit la valeur. Trop court = recommandations impertinentes = churn J7.

**Hypothèse de départ :** Un onboarding en 3 étapes réalisable en < 90 secondes permet de générer un premier plan semaine pertinent à 70%+ pour 3 familles sur 4.

**Objectif du protocole :** Valider ou invalider cette hypothèse avec les 50 premiers beta users.

---

## Design de l'onboarding cible (v1)

### Étape 1 — "Votre famille" (30 secondes)
**Question :** Combien de personnes dînent chez vous ?
- Picogrammes cliquables : Adultes (1 / 2 / 3+) + Enfants (0 / 1 / 2 / 3+)
- Age enfants si applicable : < 3 ans / 3-6 ans / 7-12 ans / 13+
- UX : sélection visuelle, pas de saisie texte
- **Donnée collectée :** Taille du foyer, composition, présence enfants

### Étape 2 — "Ce que vous ne mangez pas" (30 secondes)
**Question :** Y a-t-il des restrictions alimentaires dans votre famille ?
- Chips multi-sélection : Végétarien / Végétalien / Sans gluten / Sans porc / Sans fruits de mer / Allergie noix / Pas de restrictions
- Icônes visuelles associées à chaque restriction
- Bouton "Ajouter une restriction personnalisée" (optionnel, ne bloque pas)
- **Donnée collectée :** Restrictions actives par profil foyer

### Étape 3 — "Votre contexte" (30 secondes)
**Question :** En semaine, combien de temps avez-vous pour cuisiner le soir ?
- 3 choix visuels : "< 20 min" (rapide) / "20-40 min" (normal) / "+ 40 min" (je prends mon temps)
- Question secondaire (même écran) : Quel drive utilisez-vous ?
  - Leclerc / Auchan / Carrefour / Intermarché / Autre / Je ne commande pas en drive
- **Donnée collectée :** Contrainte temps, enseigne drive

### Écran de validation — "Votre premier plan" (immédiat)
- Animation 3-5 secondes : "Je prépare votre semaine..."
- Affichage du plan 5 dîners immédiatement — pas de paywall avant ce moment
- Bouton "Modifier un repas" visible dès le premier plan
- Email demandé ICI uniquement — après avoir vu la valeur

**Principe clé :** L'email est demandé APRÈS que l'utilisateur voit son premier plan. Jamais avant.

---

## Questions de recherche à valider

1. Le temps de complétion est-il < 90 secondes pour 80% des participants ?
2. Le premier plan généré est-il "pertinent" (noté ≥ 3/5) par l'utilisateur ?
3. Quelles questions créent le plus de friction (hésitation > 5s) ?
4. Le taux de complétion onboarding est-il > 85% ?
5. Combien d'utilisateurs modifient au moins 1 recette du premier plan ?

---

## Protocole de test utilisateur

### Recrutement
- **Cible :** 20 participants en phase test qualitatif (avant beta), puis 50 en beta quantitatif
- **Critères d'inclusion :**
  - Famille française avec 1+ enfant OU couple cuisinant régulièrement
  - Smartphone iOS ou Android
  - Fait ses courses au minimum 1x/semaine
  - N'utilise pas déjà un planificateur de repas payant
- **Critères d'exclusion :**
  - Professionnel de la cuisine / restauration
  - Utilise déjà MealPlanner (biais de confirmation)
- **Recrutement :** Panel en ligne (Typeform), réseaux sociaux familles FR, bouche-à-oreille
- **Incentive :** 3 mois offerts sur l'abonnement Famille (valeur 30€)

### Format des sessions
- **Type :** Test utilisateur modéré à distance (Lookback.io ou Maze)
- **Durée :** 30 minutes par session
- **Enregistrement :** Écran + audio (consentement signé obligatoire)
- **Nombre de sessions phase 1 :** 8 sessions qualitatives (5 participants familia + 2 couple DINK + 1 parent solo)

### Guide de modération

**Introduction (5 min)**
> "Nous testons un nouveau service pour vous, pas vos compétences. Il n'y a pas de bonne ou mauvaise réponse. Pensez à voix haute pendant que vous utilisez l'app."

**Tâche principale (10 min)**
> "Vous venez d'entendre parler de MealPlanner. Téléchargez l'app et planifiez votre semaine de dîners."

Observer sans intervenir. Chronométrer chaque étape de l'onboarding.

**Questions d'exploration post-tâche (10 min)**
1. "Qu'est-ce qui vous a semblé le plus facile dans le processus ?"
2. "Y a-t-il eu un moment où vous avez hésité ? Lequel ?"
3. "Est-ce que le plan proposé vous semble correspondre à votre famille ?"
4. "Qu'est-ce qui vous manque dans ce premier plan ?"
5. "Si vous deviez expliquer ce service à un ami, que diriez-vous ?"
6. "Pour 9,99€/mois, est-ce que vous souscrirez ?" (avec échelle 1-10 + pourquoi)

**Clôture (5 min)**
Remercier, expliquer la suite, collecter les coordonnées pour la beta.

---

## Critères de succès — onboarding v1

| Métrique | Seuil d'alerte | Cible | Source de mesure |
|---|---|---|---|
| Temps de complétion onboarding | > 120s | < 90s | PostHog — event timestamps |
| Taux de complétion onboarding | < 70% | > 85% | PostHog — funnel |
| Satisfaction premier plan (note 1-5) | < 3.0 | ≥ 4.0 | In-app rating post-génération |
| Taux de swap recette (≥ 1 recette modifiée) | — | 30-50% (sain) | PostHog — event swap_recipe |
| Email fourni après visualisation plan | < 50% | > 70% | PostHog — registration_complete |
| Time-to-first-plan | > 3 min | < 90s | PostHog — plan_generated |

---

## Métriques PostHog à implémenter

### Events à tracker (noms normalisés)

```
onboarding_started          — utilisateur arrive sur l'écran step 1
onboarding_step_completed   — { step: 1|2|3, duration_ms: ... }
onboarding_abandoned        — { at_step: 1|2|3, reason: "back_button"|"app_closed" }
plan_generated              — { duration_ms: ..., recipes_count: 5 }
recipe_swapped              — { position: 1-5, reason: "dislike"|"time"|"ingredients" }
email_submitted             — timestamp post-plan
drive_selected              — { provider: "leclerc"|"auchan"|... }
```

### Funnel PostHog à configurer

```
Étape 1 : onboarding_started
Étape 2 : onboarding_step_completed (step 1)
Étape 3 : onboarding_step_completed (step 2)
Étape 4 : onboarding_step_completed (step 3)
Étape 5 : plan_generated
Étape 6 : email_submitted
```

Taux de conversion entre chaque étape → identifier les drops.

---

## Scénarios d'abandon à surveiller

### Scénario A — Abandon Étape 1 (< 5% toléré)
**Signal :** Utilisateur ne complète pas la sélection du foyer
**Causes probables :** Interface confuse, trop de choix d'âge enfants, chargement lent
**Action :** Simplifier les picogrammes, réduire les options d'âge à 2 tranches

### Scénario B — Abandon Étape 2 (< 8% toléré)
**Signal :** Abandon sur les restrictions alimentaires
**Causes probables :** Peur de "cocher la mauvaise chose", question perçue comme obligatoire
**Action :** Ajouter "Pas de restriction" en premier et en taille XXL, rendre toutes les restrictions optionnelles

### Scénario C — Abandon Étape 3 (< 5% toléré)
**Signal :** Abandon sur la question drive
**Causes probables :** "Pas de drive dans mon secteur", question drive perçue comme engagement
**Action :** Rendre la sélection du drive optionnable avec "Je ne sais pas encore"

### Scénario D — Abandon après génération plan (critique)
**Signal :** Plan affiché mais pas d'email soumis
**Causes probables :** Plan non pertinent, premier plan décevant, paywall mal placé
**Action :** A/B test sur le moment de demande email (avant vs après modification d'une recette)

### Scénario E — Complétion sans engagement (zombie)
**Signal :** Onboarding complété, email fourni, mais aucune action dans les 24h
**Causes probables :** Curiosité sans intention réelle, démo sans usage
**Action :** Email de relance J+1 : "Votre semaine commence demain — voici votre plan"

---

## Planning de test recommandé

| Phase | Période | Participants | Méthode | Objectif |
|---|---|---|---|---|
| Test cognitif interne | Semaines 1-2 | 3 personnes (équipe) | Walkthrough manuel | Détecter les bugs UX évidents |
| Test qualitatif externe | Semaines 3-4 | 8 participants | Sessions modérées 30 min | Insights profonds, friction points |
| Test quantitatif beta | Mois 2 | 50 premiers beta | Analyse PostHog | Validation métriques |
| Itération v1.1 | Mois 3 | — | A/B test in-app | Optimisation conversion |
