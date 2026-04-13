# 07 — Breakpoints & Layouts Responsives

> Architecture des layouts MealPlanner selon les breakpoints.
> Approche : Mobile-first (default = mobile, on ajoute avec sm/md/lg/xl).
> Cibles : PWA mobile (usage principal) + tablet + desktop bento grid.

---

## Breakpoints

| Nom | Valeur | Appareils ciblés |
|---|---|---|
| default | 0px → 639px | Mobile (iPhone SE → iPhone 15 Pro Max) |
| `sm` | 640px+ | Mobile large, petit tablet |
| `md` | 768px+ | Tablet portrait (iPad Mini, iPad) |
| `lg` | 1024px+ | Tablet landscape, petit desktop |
| `xl` | 1280px+ | Desktop standard |
| `2xl` | 1536px+ | Grand écran desktop |

**Appareils prioritaires :**
1. iPhone 13/14/15 (390px wide) — persona Laure
2. iPhone SE 3e gen (375px) — small phones toujours en production
3. iPad 10e gen (820px) — usage table/canapé
4. MacBook 13" (1280px) — desktop secondaire
5. Android Pixel 7 (412px)

---

## Layout Mobile (default — < 640px)

### Structure globale

```
┌─────────────────────────┐
│  [StatusBar SafeArea]   │
│  [AppHeader]  64px      │  — Logo + titre page + avatar xs
│─────────────────────────│
│                         │
│  [Main Content]         │  — Scrollable, flex-col
│  (flex-1 overflow-auto) │
│                         │
│─────────────────────────│
│  [BottomNav] 64px       │  — + safe-area-bottom (env())
│  [SafeAreaBottom]       │
└─────────────────────────┘
```

**CSS :**
```css
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100dvh; /* dvh = dynamic viewport height (règle le bug iOS Safari) */
  overflow: hidden;
}
.app-content {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
}
.bottom-nav {
  padding-bottom: env(safe-area-inset-bottom);
}
```

### Feed Recettes (page principale mobile)

```
┌─────────────────────────┐  padding: 16px
│  [SearchBar] full-width │
│─────────────────────────│
│  [Filter Chips] scroll→ │  overflow-x: scroll, gap 8px
│─────────────────────────│
│                         │
│  [CardRecipe] full-w    │  1 colonne
│  Image 4:3              │
│  Titre + meta           │
│  ─────────────────────  │
│  [CardRecipe] full-w    │
│  ...                    │
│                         │
└─────────────────────────┘
```

**Tailwind classes type :**
```
grid grid-cols-1 gap-4 px-4
```

### Planning Semaine (mobile)

```
┌─────────────────────────┐
│  [WeekSelector] ← Sem → │  — Nav semaine précédente/suivante
│─────────────────────────│
│  [Lun] CardCompact 50%  │  — Scroll vertical
│  [Mar] CardCompact 50%  │
│  [Mer] CardCompact 50%  │
│  ...                    │
│  [Dim] CardCompact 50%  │
│─────────────────────────│
│  [CTA "Générer courses"]│  — Sticky en bas, au-dessus BottomNav
└─────────────────────────┘
```

**Tailwind :**
```
grid grid-cols-2 gap-3 px-4
```

La grille 2 colonnes sur mobile permet de voir 2 jours en même temps sans scroller.

### Liste de Courses (mobile)

```
┌─────────────────────────┐
│  [Header "Ma liste"]    │
│  [Progress] 5/12 coché  │
│─────────────────────────│
│  [Section "Légumes"]    │  — Sticky header section
│  [ShoppingItem] ←swipe  │
│  [ShoppingItem] ←swipe  │
│─────────────────────────│
│  [Section "Viandes"]    │
│  [ShoppingItem]         │
│─────────────────────────│
│  [FAB "Envoyer au drive"]│  — Floating Action Button, coin bas droite
└─────────────────────────┘
```

---

## Layout Tablet (md — 768px+)

### Structure globale

La BottomNav reste présente jusqu'à `lg`. Le header passe en mode étendu.

```
┌─────────────────────────────────────────┐
│  [AppHeader étendu]  72px               │
│  Logo + SearchBar inline + Avatar       │
│─────────────────────────────────────────│
│                                         │
│  [Main Content]  padding 24px           │
│                                         │
│─────────────────────────────────────────│
│  [BottomNav]  64px                      │
└─────────────────────────────────────────┘
```

### Feed Recettes (tablet)

2 colonnes de cards avec plus d'espace.

```
┌──────────────────┬──────────────────┐
│  [CardRecipe]    │  [CardRecipe]    │
│  ratio 16:9      │  ratio 16:9      │
├──────────────────┼──────────────────┤
│  [CardRecipe]    │  [CardRecipe]    │
└──────────────────┴──────────────────┘
```

**Tailwind :**
```
grid grid-cols-2 gap-6 px-6
```

### Planning Semaine (tablet)

5 jours visibles d'un coup (lun-ven), avec scroll pour sam-dim.

```
┌────┬────┬────┬────┬────┐
│Lun │Mar │Mer │Jeu │Ven │
│    │    │    │    │    │
└────┴────┴────┴────┴────┘
```

**Tailwind :**
```
grid grid-cols-5 gap-3 px-6
```

---

## Layout Desktop (lg/xl — 1024px+)

### Structure globale — Sidebar + Contenu

```
┌──────────┬─────────────────────────────────────┐
│          │  [AppHeader]  64px                   │
│          │─────────────────────────────────────│
│ Sidebar  │                                     │
│ 240px    │  [Main Content]                     │
│ (fixe)   │  padding 40px                       │
│          │                                     │
│          │                                     │
└──────────┴─────────────────────────────────────┘
```

La BottomNav disparaît. La Sidebar prend le relais.

**Tailwind layout shell :**
```
flex h-screen overflow-hidden
// Sidebar
w-60 flex-shrink-0 border-r border-neutral-200 overflow-y-auto
// Contenu
flex-1 flex flex-col overflow-hidden
```

### Feed Recettes Desktop — Bento Grid

L'ADN "livre de recettes" se manifeste avec la grille bento asymétrique.

```
┌──────────────────────────────────────────────────────────┐
│  [HeroCard large]                  │  [CardRecipe]        │
│  Recette mise en avant             │  compact             │
│  ratio 3:2                         ├──────────────────────┤
│                                    │  [CardRecipe]        │
│                                    │  compact             │
├──────────────┬─────────────────────┴──────────────────────┤
│ [CardRecipe] │  [CardRecipe]         │  [CardRecipe]       │
│              │                       │                     │
│              │                       │                     │
└──────────────┴───────────────────────┴─────────────────────┘
```

**Tailwind (bento grid) :**
```
grid grid-cols-3 grid-rows-2 gap-6
// HeroCard
col-span-2 row-span-1
// Cards normales
col-span-1 row-span-1
```

Variante 4 colonnes sur `xl` :
```
grid grid-cols-4 gap-6
// Hero card
col-span-2 row-span-2
```

### Planning Semaine Desktop

7 colonnes, tout visible.

```
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ Lun  │ Mar  │ Mer  │ Jeu  │ Ven  │ Sam  │ Dim  │
│      │      │      │      │      │      │      │
│      │      │      │      │      │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

**Tailwind :**
```
grid grid-cols-7 gap-4
```

---

## Layout 2xl (1536px+)

Le contenu est centré avec une largeur max.

```
.content-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 40px;
}
```

La bento grid passe à 4-5 colonnes max.

---

## Composants Adaptatifs — Récapitulatif

| Composant | Mobile (< 640) | Tablet (640-1024) | Desktop (1024+) |
|---|---|---|---|
| Navigation | BottomNav | BottomNav | Sidebar |
| Feed | 1 colonne | 2 colonnes | Bento 3-4 col |
| Planning | 2 colonnes (2j) | 5 colonnes | 7 colonnes |
| Fiche recette | Plein écran | Centré max 600px | Split (photo gauche, infos droite) |
| Dialog | Bottom sheet | Modal centré | Modal centré 480px |
| Search | Plein écran overlay | Bar inline | Bar inline + Command palette |
| Filtres | Chips scroll horizontal | Row 2 colonnes | Sidebar filtres collapsible |
| Sidebar | Absent | Absent | Visible |
| Header | 64px, logo + titre | 72px, + search | 64px, minimal (sidebar gère nav) |

---

## Safe Areas iOS (PWA)

Les PWA sur iOS doivent gérer l'encoche et la barre de navigation.

**CSS variables :**
```css
padding-top: env(safe-area-inset-top);
padding-bottom: env(safe-area-inset-bottom);
padding-left: env(safe-area-inset-left);
padding-right: env(safe-area-inset-right);
```

**Viewport meta (dans Next.js `<head>`) :**
```html
<meta name="viewport"
      content="width=device-width, initial-scale=1, viewport-fit=cover">
```

**Zones à traiter :**
- AppHeader : `padding-top` = safe-area-inset-top + 16px
- BottomNav : `padding-bottom` = safe-area-inset-bottom (sinon masqué par l'indicateur home)
- Modals/Sheets : gérer les deux extremités

---

## Breakpoints Tailwind dans le Code

Rappel de la syntaxe Mobile-first :

```html
<!-- Mobile par défaut, desktop override -->
<div class="
  grid-cols-1          <!-- Mobile : 1 colonne -->
  gap-4               <!-- Mobile : gap 16px -->
  px-4                <!-- Mobile : padding 16px -->

  sm:grid-cols-2       <!-- 640px+ : 2 colonnes -->

  md:grid-cols-2       <!-- 768px+ : 2 colonnes, gap plus grand -->
  md:gap-6
  md:px-6

  lg:grid-cols-3       <!-- 1024px+ : 3 colonnes -->
  lg:px-10

  xl:grid-cols-4       <!-- 1280px+ : 4 colonnes bento -->
">
```

**Ordre dans le HTML :** Toujours écrire les classes dans l'ordre croissant de breakpoint pour la lisibilité.

---

## Scrolling Behavior

**Mobile :**
- Scroll vertical natif (pas de scroll custom — trop lent sur mobile)
- `overscroll-behavior-y: contain` pour éviter le pull-to-refresh accidentel sur le contenu
- BottomSheet : drag-to-close (Vaul component)
- Listes horizontales : `overflow-x: auto`, `-webkit-overflow-scrolling: touch`, `scroll-snap-type: x mandatory`

**Desktop :**
- Sidebar scrollable indépendamment du contenu
- Le contenu principal scroll dans sa zone
- Pas de `position: fixed` en cascade (performance)

**Performance scroll :**
- Virtualisation des longues listes (react-virtual ou `@tanstack/react-virtual`)
- Lazy loading des images avec `loading="lazy"` et `IntersectionObserver`
- Skeleton placeholders pour le contenu non chargé
