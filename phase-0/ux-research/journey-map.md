# Journey Map — Le Dimanche Soir
> Moment clé : l'utilisateur décide les repas de la semaine
> Phase 0 Discovery | MealPlanner SaaS | Avril 2026

---

## Vue d'ensemble

**Persona principal :** Sophie Durand (Famille stressée, 4 personnes)
**Scénario :** Dimanche 19h30-21h00 — planification hebdomadaire des dîners
**Canaux :** Smartphone (iOS/Android), drive en ligne (Leclerc/Auchan), supermarché samedi

---

## Phase 1 — TRIGGER (19h30-19h45)

### Ce qui se passe
Sophie finit de ranger après le dîner du dimanche. Son mari lui demande "c'est quoi le menu cette semaine ?". Déclencheur émotionnel : la question elle-même est source de stress.

### Actions utilisateur
- Soupir intérieur
- Ouvre Google ou Pinterest : "idées repas famille semaine"
- Scroll sur 15-20 recettes sans décider
- Demande aux enfants "qu'est-ce que vous voulez manger ?" → réponse : "je sais pas"

### Émotions
**Niveau de stress : 7/10** — Fatigue accumulée de la semaine. Sentiment de charge mentale injuste ("pourquoi c'est toujours moi ?"). Légère irritation.

### Pain points
- Pas de système centralisé → consultation de 3-4 sources différentes
- Les recettes Pinterest ne génèrent pas de liste de courses automatiquement
- Résultats Google pas adaptés aux contraintes famille (allergies, enfants, temps)
- Décision non prise → report au lendemain → Lundi improvisé

### Opportunités MealPlanner
- Notification push dimanche 19h : "Planifiez votre semaine en 2 minutes"
- Landing screen : "Générer mon plan semaine" — 1 seul CTA visible
- Mémorisation du contexte (profils, goûts) → pas de re-saisie

---

## Phase 2 — PLANIFICATION (19h45-20h15)

### Ce qui se passe
Sophie décide de se lancer. Elle ouvre une app ou un site, commence à sélectionner des recettes. Le processus est lent car elle doit vérifier : est-ce que les enfants vont aimer ? est-ce que j'ai les ingrédients ? combien de temps ça prend ?

### Actions utilisateur
- Parcourt des recettes une par une
- Vérifie les ingrédients dans le placard (va physiquement en cuisine 2-3 fois)
- Tente de se souvenir des goûts de chaque enfant
- Note sur papier ou dans Notes iOS les recettes retenues
- Constate qu'elle n'a pas d'idée pour le vendredi → abandonne le vendredi

### Émotions
**Niveau de stress : 6/10 → 8/10 pic** — Frustration croissante. Sentiment d'inefficacité. Culpabilité si elle répète les mêmes recettes.

### Pain points
- Aucun filtre "validé par mes enfants" → recettes rejetées au dîner = double peine
- Pas de mémoire de ce qui a été cuisiné les semaines précédentes → répétitions
- Vérification des ingrédients non digitalisée → aller-retour cuisine/téléphone
- Planning partiel (4/5 soirs) → les derniers soirs restent flous

### Opportunités MealPlanner
- Génération IA du plan 5 soirs en < 10 secondes, basée sur le profil famille
- Filtres actifs par défaut : "enfants validés", "< 30 min", "saison"
- Mode "ingrédients du frigo" : saisir ce qu'on a → recettes adaptées
- Indicateur de nouveauté : "pas cuisiné depuis 3 semaines"
- Plan modifiable : glisser-déposer pour changer un soir

### Métriques à mesurer
- Temps de génération du plan (cible : < 5s)
- Nombre de recettes swapées (indicateur de satisfaction / signal d'apprentissage)
- Taux d'abandon pendant la planification (cible : < 15%)

---

## Phase 3 — LISTE DE COURSES (20h15-20h30)

### Ce qui se passe
Sophie a son plan (approximatif). Elle doit maintenant construire la liste de courses. C'est l'étape la plus laborieuse : elle compare les recettes, regroupe les ingrédients, vérifie ce qu'elle a déjà.

### Actions utilisateur
- Copie manuellement les ingrédients depuis chaque recette
- Groupe par rayon mentalement (pas toujours)
- Ouvre Rappels iOS ou un carnet pour la liste
- Vérifie le fond du frigo et des placards
- Partage la liste par WhatsApp à son mari

### Émotions
**Niveau de stress : 5/10** — Soulagement d'avoir un plan, mais fatigue de la saisie manuelle. Irritation si oubli d'un ingrédient samedi matin.

### Pain points
- Construction de liste = travail manuel répétitif → 20-30 minutes perdues
- Doublons non détectés (2 recettes avec oignons → achat 2x la quantité)
- Pas de regroupement par rayon automatique → désorganisation au supermarché
- Partage famille non structuré (WhatsApp = perte d'info)

### Opportunités MealPlanner
- Liste auto-générée, dédupliquée, groupée par rayon (fruits/légumes, viandes, crèmerie…)
- Cocoche en temps réel partagée avec le conjoint (Supabase Realtime)
- Envoi direct au drive Leclerc/Auchan en 1 clic — moment de vérité produit
- Indicateur "vous avez déjà ça" basé sur l'historique d'achats

### Métriques à mesurer
- Temps de construction liste (avant/après) — cible : < 2 minutes
- Taux d'utilisation du partage liste famille
- Taux de conversion liste → panier drive (cible v3 : > 40%)

---

## Phase 4 — COURSES & CUISINE SEMAINE (Lundi–Vendredi)

### Ce qui se passe
Sophie récupère les ingrédients samedi matin (drive ou magasin). La semaine commence. Chaque soir elle consulte la recette et cuisine.

### Actions utilisateur
- Consulte la fiche recette le soir (7-8 min avant de commencer)
- Cherche comment adapter (enfant #1 n'aime pas les champignons → retire-les)
- Cuisine en 20-30 minutes
- Sert — réaction des enfants : positive ou négative
- Jeudi : réalise qu'elle a oublié un ingrédient pour le vendredi

### Émotions
**Lundi-Mardi : 4/10 stress** (plan en place = sérénité)
**Mercredi : 3/10** (routine installée)
**Jeudi-Vendredi : remontée à 6/10** si imprévus

### Pain points
- Fiche recette sur téléphone = écran qui s'éteint pendant la cuisine
- Pas d'indication si un ingrédient peut être remplacé
- Si un enfant est malade ou mange ailleurs → recette prévue sans utilité → gaspi
- Oubli d'ingrédient → course supplémentaire en semaine

### Opportunités MealPlanner
- Mode cuisine : écran toujours allumé, instructions step-by-step
- Bouton "remplacer un ingrédient" avec suggestion IA instantanée
- Mode "modifier le plan en cours de semaine" : réaffecter une recette
- Notification push lundi matin : "Voici votre programme de la semaine !"
- Import recette URL depuis Marmiton, 750g (Paprika-like)

---

## Phase 5 — FEEDBACK & APPRENTISSAGE (Dimanche suivant)

### Ce qui se passe
Dimanche suivant, Sophie recommence. Elle a des retours sur la semaine passée — 2 succès, 1 échec (les enfants n'ont pas aimé), 1 recette excellente à refaire.

### Actions utilisateur
- Se souvient vaguement des plats de la semaine passée
- N'a aucun système pour noter ou mémoriser ce feedback
- Recommence le cycle depuis le début, sans capitaliser

### Émotions
**Résignation légère** — sentiment que ça sera encore le même effort dimanche prochain.

### Pain points
- Pas de mémoire systémique des plats cuisinés et des réactions
- L'IA ne peut pas apprendre si l'utilisateur ne note pas
- L'effort hebdomadaire ne diminue pas avec le temps

### Opportunités MealPlanner
- Notation rapide en fin de semaine : 3 emojis par recette (adoré / bof / refusé)
- Récap dimanche : "Vous avez cuisiné 4/5 recettes — 2 coups de cœur !"
- IA TASTE_PROFILE : amélioration visible après 4 semaines — communiquer le progrès
- Moment viral : "Partagez votre plat préféré de la semaine" → growth loop

---

## Synthèse — Carte émotionnelle

```
Niveau de stress (1-10)

10 |
 9 |
 8 |        ●  (Planification bloquée)
 7 |   ●  (Trigger)
 6 |                              ●  (Jeudi imprévus)
 5 |                    ●  (Liste manuelle)
 4 |                                          ●  (Lundi-Mer)
 3 |                                              ●  (Feedback résigné)
 2 |
   |_______________________________________________
     Trigger  Planif  Liste  Cuisine  Feedback
```

## Moments de vérité (Make-or-break)

1. **J1 : Génération du premier plan** — si trop lente ou mal adaptée → désinstallation immédiate
2. **J3 : Première recette cuisinée** — si mal reçue par les enfants → NPS négatif dès J7
3. **J7 : Drive en 1 clic** (v3) — si fluide → rétention quasi garantie
4. **J28 : Plan semaine amélioré vs J1** — l'utilisateur doit percevoir que l'IA a appris

---

## Recommandations design immédiates

- **Écran dimanche soir** : notification push 19h → deep link direct sur "Générer ma semaine" — 0 friction
- **Génération plan** : < 5 secondes, animation de chargement avec message "Je connais vos goûts…"
- **Profils enfants** : picogrammes rapides à l'onboarding — "Robin (6 ans) n'aime pas : ..."
- **Liste de courses** : groupée par rayon Leclerc (fruits/légumes, BOF, épicerie, surgélés…)
- **Mode cuisine** : keep-awake screen, polices grandes, mode portrait forcé
