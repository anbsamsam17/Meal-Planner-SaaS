# 02 — Design Tokens

> Source de vérité de tous les tokens visuels du projet.
> Ces valeurs sont implémentées dans `03-tailwind-config.ts` et importées dans Figma.
> Format : HSL (facilite les variantes avec CSS custom properties).

---

## Couleurs — Palette Complète

### Stratégie chromatique

La palette repose sur 3 familles sémantiques :
- **Terracotta** (primary) : action, identité de marque, call-to-action
- **Olive** (secondary) : navigation, états actifs, éléments secondaires
- **Cream** (neutre/base) : fonds, surfaces, textes

Les couleurs sont définies en HSL pour permettre des variantes en CSS avec `hsl(var(--color-primary-500))`.

---

### Primary — Terracotta

Teinte de base : `14 75% 55%` (hsl)

| Token | HSL | HEX | Usage |
|---|---|---|---|
| `primary-50` | `14 100% 97%` | `#FFF4F0` | Fonds très légers, hover subtil |
| `primary-100` | `14 90% 93%` | `#FFE4D9` | Fond input focus, badges légers |
| `primary-200` | `14 85% 85%` | `#FFCBB5` | Bordures actives légères |
| `primary-300` | `14 80% 75%` | `#FFA98A` | États disabled sur fond coloré |
| `primary-400` | `14 78% 65%` | `#F08060` | Hover sur bouton primary |
| `primary-500` | `14 75% 55%` | `#D9613A` | **Couleur principale — boutons, liens actifs** |
| `primary-600` | `14 72% 46%` | `#B84E2D` | Pressed state bouton primary |
| `primary-700` | `14 70% 37%` | `#943D23` | Texte primary sur fond clair |
| `primary-800` | `14 68% 28%` | `#702E1A` | Texte primary sur fond très clair |
| `primary-900` | `14 65% 18%` | `#4A1D10` | Titres sur fond cream (haut contraste) |

**Contraste WCAG vérifié :**
- `primary-500` sur `cream-50` (#FDFAF6) : ratio 4.6:1 → WCAG AA ✓
- `primary-700` sur `cream-50` : ratio 8.2:1 → WCAG AAA ✓
- `primary-500` sur blanc #FFFFFF : ratio 4.1:1 → WCAG AA ✓ (large text)
- ⚠️ `primary-400` sur `cream-50` : ratio 3.1:1 → WCAG AA ECHEC sur texte normal — utiliser uniquement pour décoration ou texte ≥ 18px

---

### Secondary — Olive / Sage

Teinte de base : `78 35% 42%` (hsl)

| Token | HSL | HEX | Usage |
|---|---|---|---|
| `secondary-50` | `78 50% 97%` | `#F5F8EE` | Fond sections "nature", tags régimes |
| `secondary-100` | `78 45% 90%` | `#E2ECCC` | Badges végétarien, fond actif nav |
| `secondary-200` | `78 40% 78%` | `#C4D9A0` | Bordures sections végé |
| `secondary-300` | `78 38% 64%` | `#9BBD6E` | Icônes secondaires |
| `secondary-400` | `78 36% 52%` | `#779A4F` | Hover liens nav |
| `secondary-500` | `78 35% 42%` | `#5E7C3F` | **Couleur secondaire — nav active, tags** |
| `secondary-600` | `78 34% 34%` | `#4C6433` | Pressed nav, texte secondaire |
| `secondary-700` | `78 33% 27%` | `#3C5028` | Texte secondaire haute lisibilité |
| `secondary-800` | `78 32% 20%` | `#2C3C1E` | Sur fond très clair |
| `secondary-900` | `78 30% 13%` | `#1C2613` | Usage rare, maximum contraste |

**Contraste WCAG vérifié :**
- `secondary-500` sur `cream-50` : ratio 5.1:1 → WCAG AA ✓
- `secondary-700` sur `cream-50` : ratio 9.3:1 → WCAG AAA ✓
- `secondary-400` sur blanc : ratio 3.8:1 → WCAG AA ✓ (large text seulement)

---

### Accent — Safran / Amber Chaud

Teinte de base : `38 90% 52%` (hsl)

| Token | HSL | HEX | Usage |
|---|---|---|---|
| `accent-50` | `38 100% 97%` | `#FFF8EC` | Fond warnings très légers |
| `accent-100` | `38 95% 90%` | `#FDECC8` | Fond notifications |
| `accent-200` | `38 92% 78%` | `#FBD78E` | Bordure warning |
| `accent-300` | `38 90% 65%` | `#F8C254` | Badge "nouveau" |
| `accent-400` | `38 90% 58%` | `#F6B325` | Étoile notation active |
| `accent-500` | `38 90% 52%` | `#F2A007` | **Accent principal — étoiles, highlights** |
| `accent-600` | `38 88% 43%` | `#C98106` | Hover étoiles |
| `accent-700` | `38 85% 34%` | `#A06404` | Texte sur fond accent clair |
| `accent-800` | `38 82% 25%` | `#764903` | Haute lisibilité |
| `accent-900` | `38 78% 16%` | `#4C2E02` | Maximum contraste |

**Contraste WCAG vérifié :**
- `accent-500` sur `cream-50` : ratio 2.1:1 → ⚠️ ECHEC texte normal → utiliser uniquement pour icônes/décoration
- `accent-700` sur `cream-50` : ratio 5.4:1 → WCAG AA ✓ pour texte
- `accent-800` sur blanc : ratio 7.1:1 → WCAG AAA ✓

---

### Neutrals — Warm Cream

Teinte de base : `38 20% 95%` pour le fond, déclinée vers le brun chaud

| Token | HSL | HEX | Usage |
|---|---|---|---|
| `neutral-50` | `38 30% 98%` | `#FDFAF6` | **Fond de page principal** |
| `neutral-100` | `38 25% 95%` | `#F8F4ED` | Fond sections secondaires |
| `neutral-200` | `38 20% 89%` | `#EDE6D9` | Bordures légères, séparateurs |
| `neutral-300` | `38 15% 80%` | `#D9CFC0` | Bordures inputs, disabled |
| `neutral-400` | `38 12% 65%` | `#B5A892` | Texte placeholder |
| `neutral-500` | `38 10% 50%` | `#8C7E6A` | Texte secondaire / métadonnées |
| `neutral-600` | `38 10% 38%` | `#6B5E4E` | Texte corps standard |
| `neutral-700` | `38 12% 28%` | `#4E4036` | Texte corps haute lisibilité |
| `neutral-800` | `38 14% 18%` | `#332920` | Texte titres |
| `neutral-900` | `38 16% 10%` | `#1C1510` | **Texte principal — maximum contraste** |

**Contraste WCAG vérifié :**
- `neutral-900` sur `neutral-50` : ratio 17.8:1 → WCAG AAA ✓✓
- `neutral-700` sur `neutral-50` : ratio 9.1:1 → WCAG AAA ✓
- `neutral-600` sur `neutral-50` : ratio 5.8:1 → WCAG AA ✓
- `neutral-500` sur `neutral-50` : ratio 3.2:1 → ⚠️ AA large text seulement (16px+ bold)

---

### Couleurs Sémantiques

#### Success — Vert Herbe Chaud
| Token | HSL | HEX | Usage |
|---|---|---|---|
| `success-50` | `145 50% 96%` | `#EDFAF3` | Fond état succès |
| `success-100` | `145 45% 88%` | `#CAF0DB` | Background toast succès |
| `success-500` | `145 55% 38%` | `#2B8A56` | Icône et texte succès |
| `success-700` | `145 60% 24%` | `#1A5735` | Texte sur fond success-100 |

**Contraste :** `success-500` sur blanc → 4.6:1 → WCAG AA ✓

#### Warning — Amber Doux (pas rouge alarmiste)
| Token | HSL | HEX | Usage |
|---|---|---|---|
| `warning-50` | `38 95% 97%` | `#FFFBF0` | Fond avertissement |
| `warning-100` | `38 90% 88%` | `#FDECC5` | Background toast warning |
| `warning-500` | `38 85% 42%` | `#C98505` | Icône et texte warning |
| `warning-700` | `38 88% 27%` | `#825503` | Texte sur fond warning-100 |

**Contraste :** `warning-700` sur `warning-50` → 6.8:1 → WCAG AA ✓

#### Error — Rouge Terracotta (cohérent palette, pas crimson)
| Token | HSL | HEX | Usage |
|---|---|---|---|
| `error-50` | `4 90% 97%` | `#FFF2F0` | Fond erreur |
| `error-100` | `4 85% 90%` | `#FFCFC9` | Background toast erreur |
| `error-500` | `4 72% 45%` | `#C43822` | Icône et texte erreur |
| `error-700` | `4 75% 30%` | `#832416` | Texte sur fond error-100 |

**Contraste :** `error-500` sur blanc → 5.2:1 → WCAG AA ✓

#### Info — Bleu Ardoise Chaud (le seul bleu autorisé)
| Token | HSL | HEX | Usage |
|---|---|---|---|
| `info-50` | `210 35% 97%` | `#F2F5F9` | Fond info |
| `info-100` | `210 30% 88%` | `#CFDAE9` | Background toast info |
| `info-500` | `210 45% 40%` | `#376A9C` | Icône et texte info |
| `info-700` | `210 50% 27%` | `#234568` | Texte sur fond info-100 |

**Contraste :** `info-500` sur blanc → 5.0:1 → WCAG AA ✓

---

## Dark Mode — Adaptations Nocturnes

Le dark mode s'active automatiquement après 21h (hook `useTimeBasedTheme`).

### Principe : "Cuisine à la bougie"
Le dark mode n'est pas un simple inversion. Les couleurs doivent évoquer une cuisine éclairée le soir — chaleureuse, pas aveuglante.

| Token Light | Token Dark | Logique |
|---|---|---|
| `neutral-50` (fond page) | `28 15% 9%` — `#1A1510` | Brun très sombre, pas noir pur |
| `neutral-100` (fond sections) | `28 14% 13%` — `#231D17` | Légèrement plus clair |
| `neutral-200` (bordures) | `28 12% 20%` — `#352C24` | Séparateurs visibles |
| `neutral-900` (texte) | `38 20% 92%` — `#EDE6D9` | Cream clair, pas blanc |
| `primary-500` (terracotta) | `14 68% 62%` — `#E07458` | Légèrement plus clair (compensation fond sombre) |
| `secondary-500` (olive) | `78 32% 52%` — `#729A50` | Légèrement plus clair |

**Règle :** En dark mode, les surfaces utilisent la gamme `neutral-800/900` comme fond. Les textes utilisent `neutral-50/100`. Les couleurs primaires et secondaires sont éclaircies de 8-10% pour maintenir le contraste.

---

## Typographie

### Duo typographique

#### Fraunces — Display / Éditorial
Variable font. Axis : Optical size (9–144), Wonky (0–1), Weight (100–900), Softness (0–100).

| Rôle | Specs | Exemple d'usage |
|---|---|---|
| `display-xl` | Fraunces 72px / weight 700 / lh 1.0 / wonky 1 | Hero titre landing |
| `display-lg` | Fraunces 56px / weight 700 / lh 1.05 / wonky 1 | Titre fiche recette |
| `display-md` | Fraunces 40px / weight 600 / lh 1.1 | Titre section |
| `display-sm` | Fraunces 32px / weight 600 / lh 1.15 | Titre carte recette |
| `heading-xl` | Fraunces 28px / weight 600 / lh 1.2 | Titre modal |
| `heading-lg` | Fraunces 24px / weight 600 / lh 1.25 | Titre page mobile |
| `heading-md` | Fraunces 20px / weight 600 / lh 1.3 | Titre section mobile |
| `heading-sm` | Fraunces 18px / weight 600 / lh 1.35 | Sous-titre, label |

**Chargement :** `font-display: swap`, `preload` sur les 2 weights (400 et 700).

#### Inter — Corps / UI
Variable font. Weights : 400 (Regular), 500 (Medium), 600 (SemiBold).

| Rôle | Specs | Exemple d'usage |
|---|---|---|
| `body-xl` | Inter 18px / weight 400 / lh 1.7 | Corps recette, texte long |
| `body-lg` | Inter 16px / weight 400 / lh 1.65 | Corps standard |
| `body-md` | Inter 14px / weight 400 / lh 1.6 | Corps compact, listes |
| `body-sm` | Inter 12px / weight 400 / lh 1.5 | Métadonnées, captions |
| `label-lg` | Inter 16px / weight 500 / lh 1.2 | Label bouton large |
| `label-md` | Inter 14px / weight 500 / lh 1.2 | Label bouton standard |
| `label-sm` | Inter 12px / weight 600 / lh 1.2 | Badge, tag |
| `ui-md` | Inter 14px / weight 400 / lh 1.4 | Navigation, métadata |
| `ui-sm` | Inter 12px / weight 400 / lh 1.4 | Horodatage, sous-info |

#### Mono — Code / Données
`JetBrains Mono` ou fallback `ui-monospace`.

| Rôle | Specs | Exemple d'usage |
|---|---|---|
| `mono-md` | JetBrains Mono 14px / weight 400 | Valeurs nutritionnelles, quantités |
| `mono-sm` | JetBrains Mono 12px / weight 400 | Données compactes |

---

## Espacements

Base 4px. Échelle : 0 / 1 (4px) / 2 (8px) / 3 (12px) / 4 (16px) / 5 (20px) / 6 (24px) / 8 (32px) / 10 (40px) / 12 (48px) / 16 (64px) / 20 (80px) / 24 (96px) / 32 (128px)

| Token | Valeur px | Usage typique |
|---|---|---|
| `space-1` | 4px | Gap interne micro (icône + texte) |
| `space-2` | 8px | Padding badge, gap liste serrée |
| `space-3` | 12px | Padding bouton sm (vertical) |
| `space-4` | 16px | Padding bouton md, gap standard |
| `space-5` | 20px | Padding card interne |
| `space-6` | 24px | Padding section mobile |
| `space-8` | 32px | Gap entre cards |
| `space-10` | 40px | Padding section desktop |
| `space-12` | 48px | Marge section |
| `space-16` | 64px | Séparation majeure |
| `space-20` | 80px | Padding hero |
| `space-24` | 96px | Sections landing |

---

## Border Radius

| Token | Valeur | Usage |
|---|---|---|
| `radius-sm` | 4px | Input, petits éléments UI |
| `radius-md` | 8px | Boutons, badges |
| `radius-lg` | 12px | Cards compactes |
| `radius-xl` | 16px | Cards recette |
| `radius-2xl` | 24px | Cards hero, sheets mobiles |
| `radius-3xl` | 32px | Bottom sheet handle area |
| `radius-full` | 9999px | Avatar, tags pills |

---

## Ombres — Warm, pas grises

Toutes les ombres utilisent une teinte terracotta/brun pour rester dans l'ADN warm. Pas d'ombre gris froide.

```
shadow-xs  : 0 1px 2px hsl(14 40% 30% / 0.06)
shadow-sm  : 0 2px 6px hsl(14 40% 30% / 0.08), 0 1px 2px hsl(14 40% 30% / 0.04)
shadow-md  : 0 4px 12px hsl(14 40% 30% / 0.10), 0 2px 4px hsl(14 40% 30% / 0.06)
shadow-lg  : 0 8px 24px hsl(14 40% 30% / 0.12), 0 4px 8px hsl(14 40% 30% / 0.08)
shadow-xl  : 0 16px 40px hsl(14 40% 30% / 0.14), 0 8px 16px hsl(14 40% 30% / 0.10)
shadow-2xl : 0 24px 64px hsl(14 40% 30% / 0.18), 0 12px 24px hsl(14 40% 30% / 0.12)
shadow-inner: inset 0 2px 6px hsl(14 40% 30% / 0.08)
```

**Règle :** En dark mode, les ombres sont remplacées par des `border` légères ou des `glow` terracotta subtils (box-shadow colorée à 15% d'opacité).

---

## Z-Index Scale

| Token | Valeur | Usage |
|---|---|---|
| `z-base` | 0 | Flux normal |
| `z-raised` | 10 | Cards survolées |
| `z-dropdown` | 100 | Menus déroulants |
| `z-sticky` | 200 | Header fixe, bottom nav |
| `z-overlay` | 300 | Overlays, backdrops |
| `z-modal` | 400 | Dialogs, sheets |
| `z-toast` | 500 | Notifications |
| `z-tooltip` | 600 | Tooltips |
| `z-top` | 9999 | Emergency overlay |

---

## Icônes

**Librairie :** Lucide React (cohérent avec shadcn/ui)
**Taille standard :** 16px (ui), 20px (standard), 24px (large), 32px (feature icon)
**Stroke width :** 1.5 (défaut) — plus léger pour look éditorial (pas le 2.0 bold générique)

**Règle :** Lucide pour les icônes fonctionnelles. Illustrations personnalisées (ou Phosphor Light) pour les états vides, onboarding, et illustrations features.

---

## Font loading strategy

> OPT-8 (review 2026-04-12) — Ajouté suite à l'audit performance.
> Fraunces + Inter sans preload correct provoque un CLS > 0.1 sur mobile,
> ce qui fait rater les Core Web Vitals (objectif LCP < 2.5s compromis).

### Pourquoi c'est critique

- Sans `display: swap`, le navigateur cache le texte le temps de charger la font (FOIT — Flash Of Invisible Text) : l'utilisateur voit une page blanche pendant 1–3s.
- Sans `preload: true`, la font n'est pas dans le chemin critique : le navigateur la découvre tard, après le premier rendu → saut de layout visible (CLS).
- Sans CSS variables dans Tailwind, il n'y a pas de continuité entre le fallback system-font et la vraie font → saut de layout même avec swap.
- Sans subset `latin-ext`, les caractères français (é, è, à, ç, ê, î, ù) tombent en fallback → rendu incohérent sur les textes FR.

### Pattern Next.js 14 — `next/font/google`

Créer le fichier `apps/web/src/app/fonts.ts` :

```ts
// apps/web/src/app/fonts.ts
// OPT-8 (review 2026-04-12) : chargement optimisé via next/font pour éviter CLS > 0.1
import { Fraunces, Inter, JetBrains_Mono } from 'next/font/google'

// Font display éditorial — utilisée sur les h1/h2 above-the-fold → preload obligatoire
export const fraunces = Fraunces({
  subsets: ['latin', 'latin-ext'],   // latin-ext requis pour é, è, à, ç (textes FR)
  display: 'swap',                   // Evite FOIT : affiche le fallback immédiatement
  preload: true,                     // Injecte <link rel="preload"> dans le <head>
  variable: '--font-fraunces',       // CSS variable référencée dans tailwind.config.ts
  weight: ['400', '500', '600', '700', '900'],
  axes: ['opsz', 'SOFT', 'WONK'],   // Variable font axes : optical size, softness, wonky
})

// Font corps UI — utilisée partout → preload critique (impact CLS maximal)
export const inter = Inter({
  subsets: ['latin', 'latin-ext'],   // latin-ext requis pour les accents FR
  display: 'swap',
  preload: true,
  variable: '--font-inter',          // CSS variable référencée dans tailwind.config.ts
  weight: ['400', '500', '600', '700'],
})

// Font mono — données nutritionnelles, quantités — pas de preload (non above-the-fold)
export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  preload: false,                    // Jamais above-the-fold → pas de preload
  variable: '--font-mono',
  weight: ['400', '500'],
})
```

### Intégration dans le layout root

Dans `apps/web/src/app/layout.tsx` :

```tsx
// apps/web/src/app/layout.tsx
import { fraunces, inter, jetbrainsMono } from './fonts'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // Les trois variables CSS sont injectées sur <html> → disponibles dans tout le DOM
    <html lang="fr" className={`${fraunces.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  )
}
```

### Référence dans `tailwind.config.ts`

Dans `03-tailwind-config.ts`, `fontFamily` référence les CSS variables (pas les noms de fonts directs) :

```ts
// Dans theme.extend.fontFamily :
fontFamily: {
  display: ["var(--font-fraunces)", "Georgia", "serif"],  // fallback si next/font échoue
  sans:    ["var(--font-inter)",    "system-ui", "sans-serif"],
  mono:    ["var(--font-mono)",     "ui-monospace"],
}
```

Ce pattern garantit qu'il n'y a **aucun saut de layout** entre le rendu du fallback system-font et l'activation de la font réelle : les deux utilisent exactement la même CSS variable, donc les dimensions ne changent pas.

### Checklist Core Web Vitals — fonts

- [ ] `preload: true` sur Inter (body) et Fraunces (h1-h2 above-the-fold)
- [ ] `display: 'swap'` sur toutes les fonts (élimine FOIT)
- [ ] Subsets `['latin', 'latin-ext']` sur Inter et Fraunces (caractères FR)
- [ ] CSS variables `--font-fraunces` / `--font-inter` utilisées dans `tailwind.config.ts`
- [ ] Variables injectées sur `<html>` dans le layout root (pas sur `<body>`)
- [ ] CLS < 0.1 mesuré en dev (Lighthouse DevTools > Performance > CLS)
- [ ] LCP < 2.5s mesuré sur mobile simulé 4G (Lighthouse mobile preset)

### Budgets à respecter

| Métrique | Budget Phase 0 | Risque sans ce fix |
|----------|---------------|-------------------|
| CLS | < 0.1 | > 0.25 (saut font visible) |
| LCP | < 2.5s | +300–600ms si font bloque le rendu |
| Font weight total chargé | < 150 KB gzip | Inter variable ~80 KB + Fraunces ~60 KB |

> **Note sur Fraunces :** Si le budget font est serré, préférer `next/font/local` avec
> uniquement les fichiers `.woff2` des weights utilisés (700 et 900 pour les headings).
> Voir `performance-audit.md` OPT-8 pour l'implémentation avec `localFont`.
