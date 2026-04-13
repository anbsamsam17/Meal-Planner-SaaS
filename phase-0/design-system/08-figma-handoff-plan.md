# 08 — Plan d'Import Figma & Handoff

> Guide pour importer les tokens du design system dans Figma et organiser la librairie de composants.
> Prérequis : Figma Pro ou Organisation (pour les variables et librairies partagées).

---

## Structure du Fichier Figma

```
MealPlanner — Design System
├── 📄 Page 1 : Foundation
│   ├── Colors — Variables & Swatches
│   ├── Typography — Styles de texte
│   ├── Spacing — Échelle d'espacement
│   ├── Radius — Styles de coin arrondi
│   └── Shadows — Styles d'ombre
│
├── 📄 Page 2 : Components
│   ├── Buttons
│   ├── Inputs & Forms
│   ├── Cards
│   ├── Navigation
│   ├── Feedback (Toast, Badge, Progress)
│   └── Overlays (Dialog, Sheet, Dropdown)
│
├── 📄 Page 3 : Patterns
│   ├── Feed Mobile
│   ├── Planning Week Grid
│   ├── Shopping List
│   └── Recipe Detail
│
├── 📄 Page 4 : Screens (Mobile)
│   ├── Onboarding (3 écrans)
│   ├── Feed / Home
│   ├── Planning Semaine
│   ├── Fiche Recette
│   ├── Liste de Courses
│   └── Profil / Settings
│
└── 📄 Page 5 : Screens (Desktop)
    ├── Dashboard + Sidebar
    ├── Feed Bento Grid
    └── Planning 7 colonnes
```

---

## Étape 1 — Variables de Couleur

### Créer les Collections de Variables

Aller dans **Assets → Local variables → Créer une collection**.

#### Collection "Primitives" (les valeurs brutes)

Créer un groupe par famille de couleur. Nommer chaque variable avec le chemin complet.

**Exemple de nommage :**
```
Primitives/
├── terracotta/50  → #FFF4F0
├── terracotta/100 → #FFE4D9
├── terracotta/200 → #FFCBB5
├── terracotta/300 → #FFA98A
├── terracotta/400 → #F08060
├── terracotta/500 → #D9613A  ← couleur principale
├── terracotta/600 → #B84E2D
├── terracotta/700 → #943D23
├── terracotta/800 → #702E1A
├── terracotta/900 → #4A1D10
│
├── olive/50  → #F5F8EE
... (même pattern)
│
├── cream/50  → #FDFAF6
... (même pattern)
│
├── accent/50  → #FFF8EC
... (même pattern)
│
├── success/50  → #EDFAF3
├── success/500 → #2B8A56
├── success/700 → #1A5735
│
├── warning/50  → #FFFBF0
├── warning/500 → #C98505
├── warning/700 → #825503
│
├── error/50  → #FFF2F0
├── error/500 → #C43822
├── error/700 → #832416
│
└── info/50  → #F2F5F9
    info/500 → #376A9C
    info/700 → #234568
```

#### Collection "Semantic" (les alias sémantiques)

Ces variables pointent vers les primitives et changent selon le mode (light/dark).

```
Semantic/
├── Color/
│   ├── Background/Default     → Primitives/cream/50
│   ├── Background/Surface     → Primitives/cream/100
│   ├── Background/Muted       → Primitives/cream/200
│   │
│   ├── Text/Primary           → Primitives/cream/900 (dark: cream/50)
│   ├── Text/Secondary         → Primitives/cream/600 (dark: cream/400)
│   ├── Text/Muted             → Primitives/cream/500 (dark: cream/500)
│   ├── Text/Disabled          → Primitives/cream/400
│   │
│   ├── Brand/Primary          → Primitives/terracotta/500
│   ├── Brand/PrimaryHover     → Primitives/terracotta/400
│   ├── Brand/PrimaryActive    → Primitives/terracotta/600
│   ├── Brand/Secondary        → Primitives/olive/500
│   ├── Brand/Accent           → Primitives/accent/500
│   │
│   ├── Border/Default         → Primitives/cream/200
│   ├── Border/Strong          → Primitives/cream/300
│   │
│   ├── Status/Success         → Primitives/success/500
│   ├── Status/Warning         → Primitives/warning/500
│   ├── Status/Error           → Primitives/error/500
│   └── Status/Info            → Primitives/info/500
```

### Ajouter le Mode Dark

1. Dans la collection "Semantic", cliquer **"Add mode"** → nommer "Dark"
2. Remapper chaque variable sémantique vers les valeurs dark (voir `02-design-tokens.md`)
3. Le mode "Dark" sera activé automatiquement via le plugin **"Dark mode"** ou manuellement sur les frames

---

## Étape 2 — Styles de Texte

### Créer les Text Styles

Aller dans **Assets → Text styles → Créer un style**.

Nommage hiérarchique :
```
Display/XL        → Fraunces / 72 / Bold / lh 1.0
Display/LG        → Fraunces / 56 / Bold / lh 1.05
Display/MD        → Fraunces / 40 / SemiBold / lh 1.1
Display/SM        → Fraunces / 32 / SemiBold / lh 1.15

Heading/XL        → Fraunces / 28 / SemiBold / lh 1.2
Heading/LG        → Fraunces / 24 / SemiBold / lh 1.25
Heading/MD        → Fraunces / 20 / SemiBold / lh 1.3
Heading/SM        → Fraunces / 18 / SemiBold / lh 1.35

Body/XL           → Inter / 18 / Regular / lh 1.7
Body/LG           → Inter / 16 / Regular / lh 1.65
Body/MD           → Inter / 14 / Regular / lh 1.6
Body/SM           → Inter / 12 / Regular / lh 1.5

Label/LG          → Inter / 16 / Medium / lh 1.2
Label/MD          → Inter / 14 / Medium / lh 1.2
Label/SM          → Inter / 12 / SemiBold / lh 1.2

UI/MD             → Inter / 14 / Regular / lh 1.4
UI/SM             → Inter / 12 / Regular / lh 1.4

Mono/MD           → JetBrains Mono / 14 / Regular / lh 1.5
Mono/SM           → JetBrains Mono / 12 / Regular / lh 1.5
```

**Pré-requis :** Installer les polices Fraunces et Inter via Google Fonts ou Fontshare avant de créer les styles.

---

## Étape 3 — Styles d'Ombre

Créer les **Effect Styles** :

```
Shadow/XS   → Drop Shadow: x=0, y=1, blur=2, spread=0, color=#6B3020 à 6%
Shadow/SM   → Drop Shadow: x=0, y=2, blur=6, spread=0, color=#6B3020 à 8%
Shadow/MD   → Drop Shadow: x=0, y=4, blur=12, spread=0, color=#6B3020 à 10%
Shadow/LG   → Drop Shadow: x=0, y=8, blur=24, spread=0, color=#6B3020 à 12%
Shadow/XL   → Drop Shadow: x=0, y=16, blur=40, spread=0, color=#6B3020 à 14%
Shadow/2XL  → Drop Shadow: x=0, y=24, blur=64, spread=0, color=#6B3020 à 18%
Shadow/Inner → Inner Shadow: x=0, y=2, blur=6, spread=0, color=#6B3020 à 8%
```

Couleur de base des ombres : `#6B3020` (équivalent HSL `14 40% 30%`).

---

## Étape 4 — Grille et Espacements

### Grille Mobile (375px)
```
Colonnes : 4
Gouttière (gutter) : 16px
Marge latérale : 16px
```

### Grille Tablet (768px)
```
Colonnes : 8
Gouttière : 24px
Marge latérale : 24px
```

### Grille Desktop (1280px)
```
Colonnes : 12
Gouttière : 32px
Marge latérale : 40px
```

Créer ces grilles comme des **Layout Grids** réutilisables dans Figma (Assets → Grid styles).

---

## Étape 5 — Organisation des Composants

### Conventions de nommage Figma

Le nommage des composants détermine l'arborescence dans l'onglet Assets.

```
Button/Primary/Large
Button/Primary/Medium
Button/Primary/Small
Button/Secondary/Large
Button/Ghost/Medium
Button/Destructive/Medium

Input/Default/Idle
Input/Default/Focus
Input/Default/Error
Input/Default/Disabled

Card Recipe/Feed/Default
Card Recipe/Feed/Hover
Card Recipe/Compact/Default
Card Recipe/Hero/Default

Badge/Diet/Vegetarien
Badge/Diet/Vegan
Badge/Time/Default
Badge/Level/Easy

...
```

### Variants Figma

Utiliser le système de **Variants** pour chaque composant :

**Exemple Button :**
- Property 1 : Variant (Primary / Secondary / Ghost / Outline / Destructive)
- Property 2 : Size (SM / MD / LG / XL)
- Property 3 : State (Default / Hover / Pressed / Disabled / Loading)
- Property 4 : Icon (None / Left / Right / Only)

**Exemple Card Recipe :**
- Property 1 : Layout (Feed / Compact / Hero / Featured)
- Property 2 : State (Default / Hover / Selected / Favorited)

---

## Étape 6 — Librairie Partagée

### Publier la librairie

1. Fichier "Design System" → **Assets → Publish** → Nommer "MealPlanner Design System v1.0"
2. Dans les fichiers d'écrans : **Assets → Libraries → Activer MealPlanner DS**
3. Les composants, variables et styles sont maintenant disponibles dans tous les fichiers du projet

### Workflow de mise à jour

1. Modifications dans le fichier Design System
2. **Publish update** (avec description du changement)
3. Dans les fichiers consumers : notification "X updates available"
4. Décider d'accepter ou de reporter les mises à jour

---

## Étape 7 — Annotations de Handoff

Pour chaque composant livré au developer, ajouter des annotations :

### Annotations requises par composant

```
[Spec Card]
Composant : Card Recipe — Variant Feed
Dimensions : width 100% (max 400px) / height auto
Radius : 16px (radius-xl)
Shadow : Shadow/LG
Spacing interne : 16px padding bas + 12px entre éléments
Police titre : Display/SM (Fraunces 32px SemiBold)
Police meta : UI/SM (Inter 12px)
Animation : card-enter 250ms spring-gentle au montage
Touch : lien englobant, min touch target 44px
A11y : aria-label="Voir la recette : [titre]"
Tokens : bg neutral-50, border neutral-200 1px
```

### Plugin recommandé : Tokens Studio for Figma

Ce plugin permet d'importer directement les design tokens depuis un fichier JSON et de les synchroniser avec GitHub.

**Workflow :**
1. Installer Tokens Studio for Figma
2. Créer un fichier `design-tokens.json` (à générer depuis `02-design-tokens.md`)
3. Connecter à un repo GitHub pour synchronisation bidirectionnelle
4. Les tokens Figma et Tailwind restent en sync

---

## Étape 8 — Spécifications Développeur

### Format de livraison

Pour chaque écran ou composant, préparer :

**Figma Dev Mode (natif Figma)** :
- Activer Dev Mode sur le fichier
- Le developer peut inspecter les valeurs CSS, voir les variables, copier les assets

**Fiche spec complémentaire (par feature) :**
```
Écran : Feed Recettes — Mobile
Date : 2026-04-12
Statut : Prêt pour développement

Composants utilisés :
- AppHeader (x1)
- SearchBar (x1)
- Chip/Filter (x variable)
- CardRecipe/Feed (x N — virtuel)
- BottomNav (x1)

Tokens spéciaux :
- Fond page : bg-neutral-50
- Spacing page : px-4 py-4

Interactions à implémenter :
- Scroll vertical infini (virtualisation)
- Swipe card → favoris (swipe right)
- Pull-to-refresh

Animations :
- CardRecipe : card-enter au premier render (stagger 80ms)
- Chips : fade-in au mount (stagger 40ms)

Accessibilité :
- SearchBar : aria-label="Rechercher une recette"
- Cards : liste <ul>, chaque card <li>
- Chips filtres : aria-pressed="true/false"
```

---

## Checklist de Livraison Design System

Avant de considérer le design system comme prêt à être consommé :

- [ ] Variables de couleur créées dans Figma (primitives + sémantiques + dark mode)
- [ ] Text styles créés (tous les niveaux typographiques)
- [ ] Effect styles créés (toutes les ombres)
- [ ] Layout grids créées (mobile / tablet / desktop)
- [ ] 30 composants créés avec tous leurs variants et states
- [ ] Librairie publiée et partagée
- [ ] `03-tailwind-config.ts` copié dans le repo Next.js et testé
- [ ] Polices Fraunces + Inter chargées via `next/font`
- [ ] Tokens Studio synchronisé avec GitHub (optionnel mais recommandé)
- [ ] Dev Mode activé sur les écrans livrés
- [ ] Checklist accessibilité (06-accessibility.md) validée sur chaque composant
- [ ] Contrastes vérifiés avec WebAIM Contrast Checker

---

## Référence Plugin Recommandés Figma

| Plugin | Usage |
|---|---|
| Tokens Studio for Figma | Sync tokens Figma ↔ GitHub ↔ Tailwind |
| Contrast | Vérifier le contraste WCAG directement dans Figma |
| A11y Annotation Kit | Annoter les specs d'accessibilité |
| Figma to Code (Locofy) | Générer du code Tailwind de base |
| Remove BG | Détourage rapide des photos recettes |
| Unsplash | Placeholder images food |
