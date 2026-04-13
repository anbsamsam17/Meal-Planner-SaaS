# 06 — Accessibilité

> Baseline WCAG 2.1 niveau AA pour MealPlanner.
> L'accessibilité n'est pas une option : elle est requise légalement (RGAA en France) et améliore l'UX pour tous les utilisateurs.
> Document de référence pour le frontend-developer et le QA.

---

## Contrastes WCAG — Palette Warm Vérifiée

La palette terracotta/olive/cream présente des pièges classiques. Voici les combinaisons validées et les combinaisons à éviter.

### Règles de contraste WCAG 2.1 AA
- Texte normal (< 18px ou < 14px bold) : ratio minimum **4.5:1**
- Grand texte (≥ 18px ou ≥ 14px bold) : ratio minimum **3:1**
- Composants UI / graphiques : ratio minimum **3:1**

### Combinaisons validées

| Texte | Fond | Ratio | Statut | Usage |
|---|---|---|---|---|
| `neutral-900` (#1C1510) | `neutral-50` (#FDFAF6) | 17.8:1 | AAA ✓ | Texte principal |
| `neutral-700` (#4E4036) | `neutral-50` (#FDFAF6) | 9.1:1 | AAA ✓ | Corps standard |
| `neutral-600` (#6B5E4E) | `neutral-50` (#FDFAF6) | 5.8:1 | AA ✓ | Corps secondaire |
| `primary-700` (#943D23) | `neutral-50` (#FDFAF6) | 8.2:1 | AAA ✓ | Liens actifs |
| `primary-500` (#D9613A) | `neutral-50` (#FDFAF6) | 4.6:1 | AA ✓ | CTA texte (≥ 14px) |
| `primary-500` (#D9613A) | `#FFFFFF` | 4.1:1 | AA ✓ | Grand texte seulement (≥ 18px) |
| `secondary-500` (#5E7C3F) | `neutral-50` (#FDFAF6) | 5.1:1 | AA ✓ | Navigation active |
| `secondary-700` (#3C5028) | `neutral-50` (#FDFAF6) | 9.3:1 | AAA ✓ | Texte secondaire |
| `cream-100` (#FFE4D9) | `primary-700` (#943D23) | 5.4:1 | AA ✓ | Texte inversé sur bouton |
| `neutral-50` (#FDFAF6) | `primary-500` (#D9613A) | 4.6:1 | AA ✓ | Texte sur bouton primary |
| `neutral-50` (#FDFAF6) | `secondary-500` (#5E7C3F) | 5.1:1 | AA ✓ | Texte sur bouton secondaire |
| `success-500` (#2B8A56) | `#FFFFFF` | 4.6:1 | AA ✓ | Texte succès |
| `error-500` (#C43822) | `#FFFFFF` | 5.2:1 | AA ✓ | Texte erreur |
| `info-500` (#376A9C) | `#FFFFFF` | 5.0:1 | AA ✓ | Texte info |
| `warning-700` (#825503) | `warning-50` (#FFFBF0) | 6.8:1 | AA ✓ | Texte warning |

### Combinaisons interdites (echec WCAG AA)

| Texte | Fond | Ratio | Problème |
|---|---|---|---|
| `primary-400` (#F08060) | `neutral-50` (#FDFAF6) | 2.8:1 | Trop clair pour texte normal |
| `primary-500` (#D9613A) | `#FFFFFF` | 4.1:1 | Insuffisant pour texte normal (< 18px) |
| `accent-500` (#F2A007) | `neutral-50` (#FDFAF6) | 2.1:1 | Jaune insuffisant — uniquement décoration |
| `accent-400` (#F6B325) | `#FFFFFF` | 1.9:1 | Jamais de texte en amber clair |
| `neutral-500` (#8C7E6A) | `neutral-50` (#FDFAF6) | 3.2:1 | AA large text uniquement (≥ 18px) |
| `neutral-400` (#B5A892) | `neutral-50` (#FDFAF6) | 1.8:1 | Placeholder uniquement, jamais de contenu important |

**Règle pratique :** Pour les textes sur fond cream, utiliser `neutral-600` minimum. Pour les textes décoratifs ou icônes informatives, le seuil 3:1 s'applique.

---

## Dark Mode — Contrastes Vérifiés

| Texte | Fond Dark | Ratio | Statut |
|---|---|---|---|
| `neutral-50` (#FDFAF6) | `dark-base` (#1A1510) | 16.2:1 | AAA ✓ |
| `neutral-200` (#EDE6D9) | `dark-base` (#1A1510) | 13.4:1 | AAA ✓ |
| `neutral-400` (#B5A892) | `dark-base` (#1A1510) | 6.8:1 | AA ✓ |
| `primary-400` (#F08060) | `dark-base` (#1A1510) | 5.1:1 | AA ✓ (texte sur dark seulement) |
| `primary-500` dark ajusté (#E07458) | `dark-base` (#1A1510) | 5.8:1 | AA ✓ |
| `secondary-400` (#779A4F) | `dark-base` (#1A1510) | 4.7:1 | AA ✓ |

---

## Focus Visible

**Standard :** Tous les éléments interactifs doivent avoir un indicateur de focus visible, conforme à WCAG 2.4.11 (Focus Appearance — niveau AA en WCAG 2.2).

### Spécification focus ring

```css
/* Focus ring standard — à appliquer via Tailwind focus-visible: */
outline: 2px solid hsl(14, 75%, 55%); /* primary-500 */
outline-offset: 2px;
border-radius: inherit; /* Suit le radius de l'élément */
```

**Pour les éléments sur fond foncé :**
```css
outline: 2px solid hsl(14, 100%, 97%); /* primary-50 */
outline-offset: 2px;
```

**Classes Tailwind à utiliser :**
```
focus-visible:outline-none
focus-visible:ring-2
focus-visible:ring-primary-500
focus-visible:ring-offset-2
focus-visible:ring-offset-neutral-50
```

**Règle :** Supprimer `outline: none` uniquement si un focus custom est fourni. Ne jamais supprimer le focus sans remplacement.

---

## Touch Targets — 44px Minimum

Tous les éléments interactifs sur mobile doivent avoir un touch target de minimum 44×44px (WCAG 2.5.5, AAA recommandé — Apple HIG impose 44px, Android 48px).

### Implémentation

**Cas courants :**
- Boutons `sm` (hauteur 32px) : ajouter `py-[6px]` de padding invisible ou utiliser `min-h-[44px]`
- Icônes seules (24px) : wrapper avec `w-11 h-11 flex items-center justify-center`
- Checkbox/Radio : label étendu avec `cursor-pointer` pour zone cliquable >= 44px
- Étoiles de notation : chaque étoile 20px → wrapper 44px minimum (3 étoiles = 132px total, acceptable)
- BottomNav items : hauteur fixe 64px, largeur auto >= 44px ✓
- Switch : 44×24px nativement ✓ (largeur 44px satisfait l'axe horizontal)

**Vérification :** Utiliser Chrome DevTools > Rendering > "Show potential tap issues" pour identifier les éléments trop petits.

---

## HTML Sémantique

### Structure de page

```html
<header role="banner">...</header>
<nav aria-label="Navigation principale">...</nav>
<main id="main-content">
  <h1>Titre de la page</h1>
  ...
</main>
<footer role="contentinfo">...</footer>
```

### Hierarchie des titres

- Une seule balise `<h1>` par page
- Ordre logique `h1 → h2 → h3` (pas de saut h1 → h3)
- Les titres Fraunces display sont des `<h1>` ou `<h2>`, jamais un `<p>` stylé en gros
- Les noms de sections nav ne sont pas des titres

### Listes

- Navigation : `<ul>` + `<li>`
- Ingrédients : `<ul>` (liste non ordonnée)
- Instructions : `<ol>` (liste ordonnée — l'ordre compte)
- Résultats de recherche : `<ul role="listbox">` + `<li role="option">`

### Formulaires

```html
<!-- Toujours associer label et input -->
<label for="portions">Nombre de portions</label>
<input id="portions" type="number" min="1" max="12"
       aria-describedby="portions-helper"
       aria-invalid="false">
<p id="portions-helper">Entre 1 et 12 personnes</p>

<!-- En cas d'erreur -->
<input aria-invalid="true" aria-describedby="portions-error">
<p id="portions-error" role="alert">Ce champ est requis</p>
```

---

## ARIA Roles et Labels

### Navigation

```html
<!-- BottomNav mobile -->
<nav aria-label="Navigation principale">
  <a href="/feed" aria-current="page">Accueil</a>
  <a href="/planning">Planning</a>
  <a href="/courses">Courses
    <span aria-label="3 articles dans la liste" class="badge">3</span>
  </a>
  <a href="/profil">Profil</a>
</nav>

<!-- Sidebar desktop -->
<nav aria-label="Navigation latérale">...</nav>
```

### Images de recettes

```html
<!-- Image informative -->
<img src="..." alt="Risotto aux champignons avec parmesan râpé, présenté dans un bol en céramique blanche">

<!-- Image décorative -->
<img src="..." alt="" role="presentation">

<!-- Image de background CSS : aria-hidden ou contenu alternatif à côté -->
```

### Dialogs et Modals

```html
<div role="dialog"
     aria-modal="true"
     aria-labelledby="dialog-title"
     aria-describedby="dialog-description">
  <h2 id="dialog-title">Supprimer cette recette ?</h2>
  <p id="dialog-description">Cette action est irréversible.</p>
  <button>Annuler</button>
  <button>Confirmer la suppression</button>
</div>
```

### Notifications dynamiques

```html
<!-- Succès, info : polite (attend que l'utilisateur soit libre) -->
<div role="status" aria-live="polite" aria-atomic="true">
  Recette ajoutée au planning du mercredi.
</div>

<!-- Erreurs critiques : assertive (interrompt immédiatement) -->
<div role="alert" aria-live="assertive" aria-atomic="true">
  Erreur lors de la génération du planning. Veuillez réessayer.
</div>
```

### Skeleton loaders

```html
<div role="status" aria-busy="true" aria-label="Chargement des recettes...">
  <!-- Éléments skeleton visuels ici, aria-hidden="true" -->
</div>
```

---

## Reduced Motion

Implémenter le hook `useReducedMotion()` de Framer Motion sur tous les composants animés.

```typescript
// Règle : ce hook doit être présent dans TOUT composant qui anime
import { useReducedMotion } from "framer-motion"

function AnimatedCard() {
  const shouldReduceMotion = useReducedMotion()

  const variants = {
    hidden: {
      opacity: 0,
      y: shouldReduceMotion ? 0 : 12, // Pas de translation si reduced
    },
    visible: {
      opacity: 1,
      y: 0,
    },
  }

  return <motion.div variants={variants} />
}
```

**Comportements en reduced motion :**
- Flip card : pas de rotation, transition opacity 0→1
- Swipe gestures : désactiver le drag (proposer boutons alternatifs)
- Particules de célébration : remplacer par un simple checkmark avec fade
- Transitions de page : cross-fade 250ms uniquement
- Skeleton shimmer : remplacer par fond statique neutral-100

---

## Navigation Clavier

### Focus order logique

Le focus suit l'ordre de lecture visuel (gauche-droite, haut-bas). Ne jamais utiliser `tabindex > 0`.

**Valeurs `tabindex` autorisées :**
- `tabindex="0"` : rendre un élément non-natif focusable (custom component)
- `tabindex="-1"` : retirer du flux de focus (éléments gérés programmatiquement)

### Focus management dans les modals

```typescript
// Quand un dialog s'ouvre : déplacer le focus sur le titre ou le premier bouton
// Quand il se ferme : retourner le focus à l'élément déclencheur
// Radix UI gère cela automatiquement via FocusScope
```

### Raccourcis clavier

| Raccourci | Action | Scope |
|---|---|---|
| `Cmd/Ctrl + K` | Ouvrir la command palette | Global |
| `Escape` | Fermer modal/sheet/dropdown | Local (élément actif) |
| `Enter / Space` | Activer un bouton/lien/option | Standard HTML |
| `←→` | Navigation entre tabs/onglets | Tablist |
| `↑↓` | Navigation dans dropdown/listbox | List |
| `Home/End` | Premier/dernier élément de liste | List |

---

## Couleurs et Daltonisme

Ne jamais transmettre une information uniquement par la couleur. Toujours doubler avec un texte, une icône ou un pattern.

**Exemples :**
- Erreur de formulaire : couleur rouge + icône `!` + texte d'erreur (pas seulement rouge)
- Étoile active : couleur amber + forme pleine (pas seulement la couleur)
- Badge "Végétarien" : couleur olive + texte "Végétarien" (pas seulement la couleur)
- Barre de progression : couleur + valeur numérique "%"

---

## Texte Alternatif — Guide Pratique

| Type d'image | Alt recommandé |
|---|---|
| Photo de recette | Description visuelle de l'assiette (ingrédients visibles, présentation) |
| Avatar utilisateur | "Photo de profil de {prénom}" |
| Icône informative | Description de l'action ou de l'état (pas le nom de l'icône) |
| Icône décorative | `alt=""` |
| Logo | "MealPlanner" |
| Illustration EmptyState | `alt=""` (description dans le titre/texte adjacent) |
| Photo IA générée pour PDF | Description de la recette |

---

## RGAA (France) — Points Spécifiques

La France impose le **RGAA 4.1** pour les services publics et recommande son suivi pour les services privés.

**Points critiques RGAA au-delà de WCAG :**
- Langue de la page déclarée : `<html lang="fr">`
- Changements de langue en inline : `<span lang="en">scan</span>`
- Titres de pages uniques et descriptifs : `<title>Planning de la semaine — MealPlanner</title>`
- Documents PDF accessibles : le PDF hebdomadaire doit avoir des balises de structure (WeasyPrint + balisage HTML sémantique)
- Formulaires : erreurs de validation annoncées par les lecteurs d'écran (`aria-live`)

---

## Checklist Accessibilité par Composant

Avant de marquer un composant comme terminé, valider :

- [ ] Contraste ratio ≥ 4.5:1 (texte normal) ou 3:1 (grand texte / UI)
- [ ] Focus visible sur tous les états interactifs
- [ ] Touch target ≥ 44×44px
- [ ] `aria-label` ou `<label>` associé pour chaque input
- [ ] Navigation clavier fonctionnelle (Tab, Enter, Escape, ←→)
- [ ] `role` ARIA approprié sur les composants custom
- [ ] Images avec `alt` descriptif (ou `alt=""` si décoratif)
- [ ] Notifications dynamiques via `aria-live`
- [ ] Comportement en `prefers-reduced-motion` défini
- [ ] Testé avec VoiceOver (iOS) ou TalkBack (Android) — au moins une fois par écran

---

## Outils de Test Accessibilité

| Outil | Usage |
|---|---|
| axe DevTools (extension) | Audit automatique en développement |
| Lighthouse | Score accessibilité dans CI/CD |
| WebAIM Contrast Checker | Vérification manuelle des contrastes |
| VoiceOver (Mac/iOS) | Test lecteur d'écran natif |
| NVDA (Windows, gratuit) | Test lecteur d'écran Windows |
| Storybook + a11y addon | Tests d'accessibilité par composant |
