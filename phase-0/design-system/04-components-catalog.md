# 04 — Catalogue des Composants

> 30 composants clés du design system MealPlanner.
> Base technique : Radix UI + shadcn/ui. Stylisation : Tailwind CSS (tokens `03-tailwind-config.ts`).
> Ces specs sont destinées au frontend-developer (Phase 2). Aucun code React ici.

---

## Conventions de lecture

| Clé | Signification |
|---|---|
| **Variants** | Les valeurs possibles du prop `variant` |
| **Sizes** | Les valeurs possibles du prop `size` |
| **States** | Les états visuels à implémenter |
| **A11y** | Obligations d'accessibilité WCAG 2.1 AA |
| **Base** | Composant Radix/shadcn de départ |

---

## 01 — Button

**Description :** Bouton principal du design system. Omniprésent.

**Variants :**
- `primary` — Fond terracotta-500, texte cream-50. Action principale ("Générer mon planning", "Valider le panier").
- `secondary` — Fond olive-100, texte olive-700, bordure olive-300. Action secondaire.
- `ghost` — Pas de fond, texte neutral-700. Liens d'action contextuels.
- `outline` — Bordure neutral-300, texte neutral-700. Actions neutres.
- `destructive` — Fond error-500, texte blanc. Suppression, désinscription.

**Sizes :**
- `sm` — Hauteur 32px, padding 8px/12px, texte 12px/medium.
- `md` — Hauteur 40px, padding 10px/16px, texte 14px/medium. (défaut)
- `lg` — Hauteur 48px, padding 12px/20px, texte 16px/medium.
- `xl` — Hauteur 56px, padding 14px/24px, texte 18px/medium. CTA landing.

**States :** default / hover (éclaircissement 6%) / pressed (assombrissement 8%) / focus (ring terracotta 2px offset 2px) / disabled (opacity 40%) / loading (spinner + texte "Chargement...")

**Touch target :** min 44x44px (padding compensé si bouton `sm`)

**A11y :** `aria-busy` pendant loading, `aria-disabled` distinct de `disabled`

**Base :** shadcn/ui `<Button>` avec variants Tailwind CVA

---

## 02 — Input

**Description :** Champ de saisie texte. Utilisé partout (search, onboarding, formulaires).

**Variants :**
- `default` — Fond neutral-50, bordure neutral-300, radius-sm.
- `filled` — Fond neutral-100, sans bordure visible au repos.
- `underline` — Bordure uniquement en bas. Mobile onboarding.

**Sizes :** `sm` (32px) / `md` (44px, défaut) / `lg` (52px)

**States :** idle / focus (bordure primary-500, ring primary-200 2px) / error (bordure error-500, icône !) / success (bordure success-500, icône ✓) / disabled (fond neutral-100, texte neutral-400)

**Éléments optionnels :** label (Inter 14px medium, neutral-700) / helper text (Inter 12px, neutral-500) / error message (Inter 12px, error-600) / leading icon (Lucide 16px) / trailing icon ou action

**A11y :** `aria-label` ou `<label>` associé obligatoire, `aria-invalid` en état error, `aria-describedby` pour helper/error text

**Base :** shadcn/ui `<Input>` + `<Label>` + `<FormMessage>`

---

## 03 — Card Recipe

**Description :** Carte recette — composant le plus identitaire du produit.

**Structure (de haut en bas) :**
1. Zone image (ratio 4:3 sur mobile, 16:9 sur desktop) — `object-fit: cover`, `border-radius: radius-xl radius-xl 0 0`
2. Overlay gradient bas de photo (linear-gradient transparent → terracotta-900/60%)
3. Badge badges (temps, régime, niveau) — positionnés en overlay sur la photo
4. Titre recette — Fraunces 20px/700, neutral-900, 2 lignes max, ellipsis
5. Métadonnées en ligne — temps ⏱ / portions 👥 / difficulté ★ — Inter 12px, neutral-500
6. Rating row — StarRating + compteur avis
7. Footer card — bouton "Ajouter au planning" + icône favoris

**Variants :**
- `feed` — Pleine largeur mobile, empilé vertical. Layout standard du feed.
- `compact` — 50% width, 2 colonnes. Shopping list, suggestions secondaires.
- `hero` — Pleine largeur desktop, image droite, texte gauche. Feature recette.
- `featured` — Card horizontale. Top picks, recommandations IA.
- `placeholder` — Skeleton (voir composant 08).

**States :** default / hover (shadow-lg + translateY -2px, 250ms spring) / selected (ring primary-400 2px) / favorited (cœur plein terracotta-500)

**A11y :** lien englobant avec `aria-label="Voir la recette : [nom]"`, image avec `alt` descriptif

**Animations :** Entrée en `card-enter` (250ms). Hover spring (voir `05-motion-principles.md`).

**Base :** Composition custom sur shadcn/ui `<Card>`

---

## 04 — PlanWeekGrid

**Description :** Grille 7 jours du planning hebdomadaire. Composant central de l'app.

**Structure :**
- Header : semaine (ex: "Semaine du 14 avril") + boutons navigation ← →
- 7 cellules jours (lun–dim) en layout vertical sur mobile, grille 7col sur desktop
- Chaque cellule contient : nom du jour + CardRecipe compact OU slot vide
- Cellule vide = état `EmptySlot` (fond neutre pointillé, bouton "+ Ajouter")
- Footer : bouton "Générer mes courses" primary xl + "Régénérer la semaine" ghost

**Variants :**
- `week` — Vue 7 jours. Vue principale.
- `days-5` — Lundi → vendredi seulement. Option utilisateur.
- `compact` — 1 colonne, scroll vertical, mobile small.

**States par cellule :** empty / filled / loading (skeleton) / locked (recette validée, non modifiable)

**Interactions :** Drag & drop entre cellules (desktop), long press → menu contextuel (mobile), swipe left → supprimer recette du jour

**A11y :** `role="grid"`, chaque cellule `role="gridcell"`, navigation clavier ←→↑↓

---

## 05 — RatingStars

**Description :** Notation de 1 à 5 étoiles. Feedback utilisateur sur les recettes.

**Variants :**
- `interactive` — Cliquable, état hover par étoile. Utilisé sur fiche recette.
- `display` — Lecture seule, fraction d'étoile possible (ex: 4.3). Utilisé sur Card.
- `haptic` — Mode mobile, tap déclenche animation `star-pop` + vibration API (navigator.vibrate(8)).

**Sizes :** `sm` (14px) / `md` (20px, défaut) / `lg` (28px)

**Couleur active :** accent-400 (#F6B325). Couleur inactive : neutral-300.

**A11y :** `<fieldset>` + `<legend>` + `<input type="radio">` visuellement masqués, labels descriptifs ("1 étoile", "2 étoiles"...)

**Interaction :** Au hover, les étoiles précédentes s'allument en cascade (300ms, décalage 40ms par étoile). Au clic, `star-pop` sur l'étoile sélectionnée.

---

## 06 — Badge

**Description :** Tag informatif sur les recettes. 3 familles sémantiques.

**Variants :**
- `diet` — Régime alimentaire. Couleurs : végétarien (olive-100/700), vegan (success-100/700), sans gluten (accent-100/700), sans lactose (info-100/700), halal (primary-100/700).
- `time` — Durée de préparation. Couleur : neutral-100/700. Icône horloge Lucide 12px.
- `level` — Niveau de difficulté. Facile (success-100/700), Moyen (warning-100/700), Chef (error-100/700).
- `new` — Nouveau / Recent. Accent-100, texte accent-700. "Nouveau".
- `ai` — Suggéré par l'IA. Primary-100, texte primary-700. Icône sparkle.

**Taille fixe :** hauteur 22px, padding 4px/8px, texte 11px/semibold, radius-full.

**A11y :** `role="status"` pour badges dynamiques, contenu explicite (pas d'icône seule)

---

## 07 — Avatar Household

**Description :** Représentation visuelle d'un membre du foyer.

**Structure :** Cercle avec photo ou initiales. Indicateur de régime alimentaire (petit badge sur le coin inférieur droit).

**Sizes :** `xs` (24px) / `sm` (32px) / `md` (40px, défaut) / `lg` (56px) / `xl` (80px)

**Variants :**
- `photo` — Image ronde avec `object-fit: cover`.
- `initials` — Fond généré par hash du prénom (parmi palette terracotta/olive/accent), initiales en blanc.
- `group` — Stack de 3-4 avatars (-8px overlap). Affiche "+ N" si plus.

**States :** default / active (ring primary-400 2px, shadow-sm) / offline (opacité 60%)

**A11y :** `alt` avec le prénom du membre, `aria-label` sur les groupes

---

## 08 — Skeleton

**Description :** État de chargement des composants. Utilise l'animation `shimmer-warm`.

**Variants :**
- `text` — Lignes de texte (1 ou N lignes, largeurs variées pour réalisme).
- `card` — Forme Card Recipe complète (image + 3 lignes texte).
- `avatar` — Cercle.
- `badge` — Pilule courte.
- `image` — Rectangle avec ratio paramétrable.

**Style shimmer :** `background: linear-gradient(90deg, neutral-100 25%, neutral-200 50%, neutral-100 75%)`, animation `shimmer-warm` 1.8s infini.

**A11y :** `role="status"`, `aria-busy="true"`, `aria-label="Chargement en cours"`

---

## 09 — EmptyState

**Description :** État vide pour les listes, le planning, la liste de courses.

**Structure :**
1. Illustration (SVG ou Lottie, 120×120px)
2. Titre (Fraunces 20px, neutral-800)
3. Description (Inter 14px, neutral-500, max 2 lignes)
4. CTA optionnel (Button primary ou ghost)

**Variants par contexte :**
- `plan-empty` — Planning vide. "Votre semaine vous attend". CTA "Générer mon planning".
- `recipes-empty` — Résultats de recherche vides. "On n'a rien trouvé pour ça". CTA "Effacer les filtres".
- `favorites-empty` — Pas de favoris. "Sauvegardez vos recettes préférées". Illustration cœur vide.
- `shopping-empty` — Liste de courses vide. Illustration panier.

**A11y :** `role="status"` sur le conteneur, illustration `aria-hidden="true"`

---

## 10 — Toast

**Description :** Notification temporaire. 4 types sémantiques. Positionnement : bas de l'écran centré (mobile), bas-droite (desktop).

**Variants :** `success` / `warning` / `error` / `info`

**Structure :** Icône (20px) + texte principal (Inter 14px medium) + texte secondaire optionnel (Inter 12px) + bouton action optionnel (ghost sm) + bouton fermer (X)

**Durée :** 4s par défaut. Action uniquement (ex: "PDF reçu !") : 6s.

**Animation entrée :** `toast-slide-in` (350ms spring). Sortie : fade + slide down (200ms).

**Comportement :** Max 3 toasts simultanés. File d'attente si plus. Auto-dismiss. Pause au hover.

**A11y :** `role="alert"` pour errors, `role="status"` pour autres, `aria-live="polite"` ou `"assertive"`

**Base :** Radix UI `<Toast>` via shadcn/ui

---

## 11 — Dialog

**Description :** Modal overlay pour actions importantes. Blocage du fond.

**Variants :**
- `default` — Largeur max 480px desktop, plein écran mobile.
- `wide` — Largeur max 680px. Prévisualisation recette, détails planning.
- `destructive` — Header en error-50, icône warning. Confirmation suppression.

**Structure :** Backdrop (neutral-900/50%) + Card (bg neutral-50, shadow-2xl, radius-2xl) + Header (titre Fraunces + bouton fermer) + Body (scroll si besoin) + Footer (2 boutons CTA)

**Animation :** Entrée fond `fade-in` 250ms + carte scale 0.95→1 + translateY 20→0, spring-gentle.

**A11y :** `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, focus trap, `Escape` pour fermer

**Base :** Radix UI `<Dialog>` via shadcn/ui

---

## 12 — Sheet Mobile (Bottom Sheet)

**Description :** Panneau qui monte depuis le bas sur mobile. Alternative au Dialog.

**Variants :**
- `half` — 50% hauteur écran. Actions contextuelles rapides.
- `full` — 90% hauteur écran. Fiche recette, filtres détaillés.
- `snap` — Multiple snap points (25%, 50%, 90%). Carte recette expandable.

**Structure :** Backdrop + Sheet container (radius-3xl top seulement, bg neutral-50) + Handle bar (neutral-300, 36×4px, radius-full, centré) + Header optionnel + Body scroll

**Geste :** Drag down pour fermer (threshold 40% hauteur ou vélocité > 500px/s). Snap points si variant `snap`.

**Animation :** `slide-up` (350ms spring). Fermeture : translateY(100%) 300ms ease-in.

**A11y :** `role="dialog"`, focus trap, Escape ferme, background non-interactif

**Base :** Radix UI `<Dialog>` adapté ou `vaul` (Drawer component Vercel)

---

## 13 — Tabs

**Description :** Navigation par onglets. Utilisé sur fiche recette (Ingrédients / Instructions / Nutrition) et profil (Planning / Favoris / Historique).

**Variants :**
- `underline` — Indicateur ligne sous l'onglet actif (primary-500, 2px). Fond transparent.
- `pill` — Onglet actif en pill (primary-100, texte primary-700). Fond neutral-100.
- `card` — Tabs en cards avec fond distinct. Desktop.

**States :** inactive (neutral-500) / active (primary-700 + indicateur) / hover (neutral-700) / focus (ring primary)

**A11y :** `role="tablist"` + `role="tab"` + `role="tabpanel"`, `aria-selected`, navigation clavier ←→

**Base :** Radix UI `<Tabs>` via shadcn/ui

---

## 14 — Dropdown Menu

**Description :** Menu contextuel déroulant. Trios puntini (…) sur card recette, actions profil, etc.

**Structure :** Trigger (Button ghost ou icône) + Menu panel (bg neutral-50, shadow-lg, radius-lg) + Items (Inter 14px, 36px hauteur, hover bg neutral-100) + Séparateurs + Items destructifs (texte error-600)

**A11y :** `role="menu"`, `role="menuitem"`, navigation clavier ↑↓ Enter Escape

**Base :** Radix UI `<DropdownMenu>` via shadcn/ui

---

## 15 — Progress

**Description :** Indicateur de progression. Onboarding, génération PDF, analyse frigo.

**Variants :**
- `bar` — Barre horizontale. Onboarding steps, chargement.
- `circle` — Cercle SVG. Objectif nutritionnel hebdomadaire.
- `steps` — Dots de progression. Stepper (voir composant 16).

**Sizes :** `sm` (4px hauteur bar) / `md` (8px) / `lg` (12px)

**Couleur fill :** primary-500 (default) / success-500 (objectif atteint) / warning-500 (attention)

**Animation :** Transition width `slow` (400ms) ease-out. Pas de flash au chargement.

**A11y :** `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`

**Base :** Radix UI `<Progress>` via shadcn/ui

---

## 16 — Stepper Onboarding

**Description :** Navigation multi-étapes de l'onboarding. Max 3 étapes (benchmark Mealime).

**Structure :**
1. Progress dots en haut (3 dots, actif = primary-500, inactif = neutral-300)
2. Zone contenu (slide horizontal entre étapes)
3. Bouton "Suivant" primary xl full-width
4. Lien "Passer" ghost sm (si étape optionnelle)

**Étapes MealPlanner :**
- Étape 1 : Taille du foyer + prénoms membres
- Étape 2 : Restrictions alimentaires par membre (checkbox visuelles, pas de liste)
- Étape 3 : Temps de cuisine disponible + préférences budget

**Animation :** Slide horizontal entre étapes (Framer Motion). Étape sortante : translateX(-100%) + fade. Étape entrante : translateX(100%)→0 + fade.

**Règle UX :** Max 60 secondes pour compléter les 3 étapes. Valider ce KPI avec les beta users.

---

## 17 — BottomNav Mobile

**Description :** Navigation principale sur mobile. Fixée en bas. 4 items maximum.

**Items MealPlanner :**
1. Maison (Accueil/Feed recettes) — icône Home
2. Calendrier (Planning semaine) — icône CalendarDays
3. Panier (Liste de courses) — icône ShoppingCart + badge count
4. Profil — Avatar household xs

**Structure :** Barre fixe bg neutral-50, shadow-2xl, hauteur 64px + padding safe-area-bottom. Items centrés verticalement.

**States item :** inactive (neutral-400, icône 24px) / active (primary-600, icône 24px + label Inter 10px medium)

**Badge :** Sur Panier, badge count neutral-900 bg + texte cream, radius-full, 18px.

**A11y :** `<nav>` avec `aria-label="Navigation principale"`, `aria-current="page"` sur item actif

---

## 18 — Sidebar Desktop

**Description :** Navigation latérale fixe sur desktop (≥ 1024px). Remplace BottomNav.

**Largeur :** 240px (expanded) / 64px (collapsed, icônes only)

**Structure :** Logo + nom (haut) + Nav items (milieu, vertical) + Separator + Infos compte + Bouton upgrade (si plan Starter)

**Nav items :** Icône 20px + label Inter 14px. Active : bg primary-100, texte primary-700, bordure gauche 3px primary-500. Hover : bg neutral-100.

**Comportement :** Collapsed auto sur lg, expanded sur xl+. Toggle utilisateur sauvegardé en localStorage.

**A11y :** `<nav>` + `aria-label="Navigation latérale"`, `aria-expanded` sur toggle

---

## 19 — Command Palette

**Description :** Recherche rapide universelle. Trigger : Cmd/Ctrl+K.

**Fonctions :** Recherche recettes (par nom, ingrédient, cuisine) + Navigation rapide + Actions rapides ("Générer planning", "Voir liste de courses")

**Structure :** Overlay backdrop (neutral-900/50%) + Panel centré (max-w-lg, radius-2xl, shadow-2xl, bg neutral-50) + Input search (Inter 16px, pas de bordure, full-width) + Résultats groupés (Recettes / Pages / Actions) + Kbd shortcut hints

**A11y :** `role="combobox"`, `aria-haspopup="listbox"`, `role="listbox"` + `role="option"`, navigation clavier ↑↓ Enter

**Base :** `cmdk` (Command Menu React) — base de shadcn/ui `<Command>`

---

## 20 — ShoppingListItem

**Description :** Item de la liste de courses. Composant critique (feature de rétention).

**Structure :** Checkbox (carré, radius-sm) + Nom ingrédient (Inter 14px) + Quantité/unité (Inter 12px, neutral-500) + Rayon (badge neutral-100 xs) + Swipe actions (mobile)

**Swipe actions (mobile) :**
- Swipe left (rouge, error-500) : Supprimer l'item
- Swipe right (olive, secondary-500) : Marquer comme "déjà en stock"

**States :** unchecked / checked (texte barré neutral-400, checkbox primary-500) / stock (italique, neutral-400, badge "En stock")

**Groupement :** Items groupés par rayon (Légumes, Viandes, Féculents...). Header de groupe sticky.

**Animation :** Check → checkbox `success-pop` 300ms. Swipe : résistance progressive puis snap.

**A11y :** `<ul>` + `<li>`, `<input type="checkbox">` + `<label>` associé, `aria-checked`

---

## 21 — PhotoUpload

**Description :** Chargement de photo pour le scan frigo ou les recettes custom.

**Variants :**
- `frigo` — Zone drop large (full-width, 160px hauteur), fond neutral-100, icône appareil photo centré, texte "Prends une photo de ton frigo".
- `recipe` — Zone compacte dans formulaire ajout recette.

**States :** idle (pointillé neutral-300) / drag-over (fond primary-50, bordure primary-400) / uploading (Progress bar + %) / success (miniature photo + bouton supprimer) / error (bordure error-400 + message)

**Interactions :** Clic → input file. Drag & drop. Camera sur mobile (accept="image/*", capture="environment").

**A11y :** `<input type="file">` avec `<label>` associé, `aria-describedby` pour instructions

---

## 22 — StarRating Haptic-like

**Description :** Version enrichie de RatingStars (composant 05) pour les interactions post-repas.

**Différences vs RatingStars :**
- Animation plus prononcée au tap (scale 1→1.4→1)
- Vibration native `navigator.vibrate([8, 4, 8])` si supporté
- Label contextuel qui change avec le score : "Pas terrible" / "Moyen" / "Bien" / "Très bien" / "On a adoré !"
- Le label apparaît en Fraunces 18px primary-600 sous les étoiles au tap

**Usage :** Modale de feedback post-dîner (déclenché le soir par RETENTION_LOOP).

---

## 23 — FlipCard Recette

**Description :** Carte qui se retourne pour révéler le résumé de la recette. Interaction "livre de recettes".

**Recto :** Photo pleine + titre + 2 badges
**Verso :** Fond cream-100, liste des ingrédients principaux (5 max) + temps + difficulté + bouton "Voir la recette complète"

**Trigger :** Long press (mobile, 500ms) / hover persistant (desktop, 600ms)

**Animation :** rotateY 0→180 en 400ms, `ease-out-smooth`. Perspective 1200px. Le verso entre en miroir (rotateY 180→0).

**A11y :** Bouton dédié "Afficher le résumé" pour les utilisateurs ne pouvant pas faire de long press. `aria-expanded`.

---

## 24 — Notification Badge

**Description :** Badge de comptage sur icônes de navigation.

**Sizes :** dot (6px, pas de chiffre) / `sm` (16px, 1-9) / `md` (20px, 1-99) / `lg` (24px, 99+)

**Couleurs :** primary-500 (actions requises) / error-500 (alertes) / neutral-800 (info)

**Position :** `-top-1 -right-1` par rapport au composant parent.

**A11y :** `aria-label="N nouvelles notifications"` sur le parent.

---

## 25 — Chip / Tag Filtres

**Description :** Filtres sélectionnables sur la page recherche de recettes.

**Structure :** Texte + optionnellement icône gauche + croix si sélectionné.

**States :** unselected (neutral-100, texte neutral-600) / selected (primary-100, texte primary-700, bordure primary-400) / hover (neutral-200)

**Taille :** Hauteur 32px, padding 4px/12px, radius-full.

**Comportement :** Multi-sélection possible. Scroll horizontal sur mobile.

---

## 26 — Divider

**Description :** Séparateur visuel entre sections.

**Variants :** `horizontal` (full-width, 1px neutral-200) / `vertical` (inline, 1px, hauteur définie) / `decorative` (ligne + texte centré, ex: "OU", texte neutral-400)

---

## 27 — Tooltip

**Description :** Info-bulle au survol. Uniquement pour desktop (hover).

**Structure :** Bulle (neutral-800, texte cream-100 12px, radius-md, shadow-md) + Flèche

**Delay :** 600ms avant apparition (évite les flickering). Disparaît immédiatement.

**A11y :** Accessible uniquement via `aria-describedby`. Ne jamais mettre d'information critique dans un tooltip seul.

**Base :** Radix UI `<Tooltip>` via shadcn/ui

---

## 28 — Select

**Description :** Sélecteur pour formulaires (nombre de portions, enseigne drive, etc.).

**Structure :** Trigger (apparence input) + Dropdown panel (bg neutral-50, shadow-lg, max-h 240px scroll) + Options (Inter 14px, 40px hauteur, hover bg neutral-100) + Check actif (primary-500)

**A11y :** `role="combobox"`, navigation clavier, label associé obligatoire.

**Base :** Radix UI `<Select>` via shadcn/ui

---

## 29 — Switch

**Description :** Toggle on/off pour préférences (dark mode, notifications, membre actif).

**Taille :** 44×24px (conforme touch target 44px sur l'axe horizontal).

**States :** off (neutral-300) / on (primary-500) / focus (ring primary 2px offset)

**Animation :** Thumb slide 150ms spring.

**A11y :** `role="switch"`, `aria-checked`, label obligatoire visible ou `aria-label`.

**Base :** Radix UI `<Switch>` via shadcn/ui

---

## 30 — NutritionBar

**Description :** Barre de progression visuelle pour macros (glucides, protéines, lipides, calories). Fiche recette + récap hebdomadaire.

**Structure :** Label (Inter 12px, neutral-600) + Valeur (JetBrains Mono 14px, neutral-800) + Barre (hauteur 6px, radius-full) + Pourcentage (Inter 11px, neutral-500)

**Couleurs par macro :**
- Calories : primary-400
- Glucides : accent-400
- Protéines : secondary-500
- Lipides : info-400

**Animation :** Barre se remplit au `IntersectionObserver` (entrée dans le viewport), 400ms ease-out.

**A11y :** `role="progressbar"` avec `aria-label="Glucides : 45g (56% des apports journaliers recommandés)"`
