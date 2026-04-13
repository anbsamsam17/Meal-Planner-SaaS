# 05 — Principes Motion

> Gouvernance des animations et transitions pour MealPlanner.
> Implémentation : Framer Motion + View Transitions API (Next.js 14).
> Principe fondateur : "Le mouvement raconte une histoire, il ne fait pas le beau."

---

## Philosophie Motion

Le mouvement dans MealPlanner doit évoquer la **physique du monde alimentaire** : le glissement d'un livre que l'on ouvre, la résistance douce d'une page que l'on tourne, le rebond satisfaisant d'une chose que l'on pose.

Trois interdictions absolues :
- Pas d'animation `linear` (mécanique, sans vie)
- Pas de durée > 600ms pour les interactions UI (frustrant)
- Pas d'animation qui retarde l'accès à l'information (jamais bloquer)

---

## Durées Standard

| Token | Valeur | Usage |
|---|---|---|
| `fast` | 150ms | Hover state, focus ring, checkbox tick, switch toggle |
| `base` | 250ms | Entrée de composants simples (badge, chip, tooltip), transitions couleur |
| `slow` | 400ms | Cards, Progress bar, transitions de pages secondaires |
| `slower` | 600ms | Transitions hero, révélations importantes (PDF prêt, succès panier) |

**Règle :** Les durées s'allongent avec l'importance perçue de l'action. Un feedback micro (checkbox) doit être quasi imperceptible. Une célébration (PDF reçu) peut durer 600ms.

---

## Courbes d'Easing

### ease-out-smooth — Standard
`cubic-bezier(0.25, 0.46, 0.45, 0.94)`

Usage : Entrées d'éléments (slide in, fade in). Démarre vite, ralentit à l'arrivée. Ressenti naturel.

### ease-in-out-smooth — Transitions
`cubic-bezier(0.4, 0, 0.2, 1)`

Usage : Transitions entre états (color change, size change). Symétrique, propre.

### spring — Physique réaliste
`cubic-bezier(0.34, 1.56, 0.64, 1)` (léger dépassement de la cible)

Usage : Cards au hover, avatars, étoiles de notation, boutons CTA. Donne une sensation de "rebond" et de matière.

### spring-gentle — Physique douce
`cubic-bezier(0.22, 1, 0.36, 1)` (pas de dépassement)

Usage : Modals, sheets, navigation entre pages. Plus calme que spring.

### Framer Motion equivalents
```typescript
// Spring pour cards hover
const springConfig = {
  type: "spring",
  stiffness: 400,
  damping: 30,
  mass: 0.8,
}

// Spring pour étoiles
const starSpring = {
  type: "spring",
  stiffness: 600,
  damping: 20,
  mass: 0.5,
}

// Transition page gentille
const pageTransition = {
  type: "spring",
  stiffness: 300,
  damping: 35,
  mass: 1.0,
}
```

---

## Transitions de Pages — View Transitions API

### Principe : "Retourner les pages d'un livre"

Next.js 14 App Router + View Transitions API. Chaque navigation entre routes est animée.

### Configuration de base

```typescript
// app/layout.tsx — activer View Transitions
export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <ViewTransitions>
          {children}
        </ViewTransitions>
      </body>
    </html>
  )
}
```

### Patterns de transition par route

**Feed → Fiche Recette (pattern iOS Card Zoom)**
- Carte recette du feed : `view-transition-name: "recipe-card-{id}"`
- Header image fiche recette : même `view-transition-name`
- Résultat : la carte du feed "grandit" pour devenir la page recette
- Durée : 400ms, spring-gentle
- CSS :
  ```css
  ::view-transition-old(recipe-card-*) {
    animation: none;
  }
  ::view-transition-new(recipe-card-*) {
    animation: card-zoom-in 400ms cubic-bezier(0.22, 1, 0.36, 1);
  }
  @keyframes card-zoom-in {
    from { transform: scale(0.85); opacity: 0; border-radius: 16px; }
    to   { transform: scale(1); opacity: 1; border-radius: 0; }
  }
  ```

**Navigation principale (BottomNav / Sidebar)**
- Transition cross-fade (250ms) avec léger slide horizontal (16px)
- Slide vers la droite si navigation "en avant" (plus profond dans l'arborescence)
- Slide vers la gauche si retour

**Onboarding (Stepper)**
- Slides horizontaux gérés par Framer Motion (pas View Transitions)
- `AnimatePresence` + `motion.div` avec `x` et `opacity`

---

## Micro-Interactions Détaillées

### Swipe Recette (ShoppingListItem, CardRecipe)

**Comportement :**
1. Début du swipe : résistance initiale (translateX = swipeX * 0.4 jusqu'à 20px)
2. Seuil atteint (50% de la largeur) : snap vers l'action, couleur arrière-plan change
3. Relâchement avant seuil : retour à 0 avec spring `stiffness: 300, damping: 25`
4. Relâchement après seuil : snap complet, action déclenchée, item sort avec `translateX(-100%)` 250ms

**Implémentation Framer Motion :**
```typescript
// Pseudo-spec, pas du code final
const swipeConstraints = { left: -cardWidth, right: 0 }
const dragElastic = 0.1
const snapThreshold = cardWidth * 0.4
```

### Rating Feedback (StarRating Haptic)

**Séquence :**
1. Tap sur étoile N
2. Scale 1 → 1.0 → 1.3 → 1.0 (300ms spring star)
3. Étoiles 1 à N-1 s'illuminent en cascade (delay 40ms entre chaque, 150ms each)
4. Label textuel apparaît (fade-in 200ms) sous les étoiles
5. Vibration `navigator.vibrate([8, 4, 8])` si supporté

**Règle :** Le feedback visuel doit précéder ou être simultané au feedback haptique.

### Add to Cart / Planning Success Celebration

**Déclencheur :** Bouton "Ajouter au planning" tapé.

**Séquence :**
1. Bouton : scale 1 → 0.95 (80ms) → 1 (200ms spring)
2. Icône check remplace le texte (cross-fade 200ms)
3. Particules confetti (4-6 petits dots terracotta + olive) : éruption depuis le bouton, trajectoires aléatoires, gravity, 600ms
4. Couleur bouton : terracotta → success-500 (transition 250ms)
5. Toast "Ajouté au planning !" (slide-in depuis le bas)

**Note technique :** Les particules sont des divs absolus animés via Framer Motion `motion.div`. Détruire le composant particule après l'animation.

### Flip Card Recette

**Séquence :**
1. Long press 500ms (mobile) : petit scale 0.98 (signal que l'action est détectée)
2. À 500ms : rotateY 0 → 90 (200ms ease-in)
3. À 200ms : swap du contenu (recto → verso)
4. rotateY 90 → 0 (200ms ease-out)
5. Ombre augmente pendant la rotation (profondeur)

**CSS perspective :**
```css
.flip-container {
  perspective: 1200px;
}
.flip-card {
  transform-style: preserve-3d;
}
```

### Skeleton → Content (Shimmer to Real)

**Séquence :**
1. Skeleton shimmer pendant le chargement
2. Données reçues : skeleton fade out (150ms)
3. Contenu réel fade in (200ms, `staggerChildren: 0.05s` pour les éléments multiples)

**Règle :** Jamais de saut de layout au remplacement. Le skeleton doit avoir les mêmes dimensions que le contenu final.

---

## Animations de l'Objet Livre Hebdomadaire

Le PDF hebdomadaire est le différenciant #4 du produit. Son arrivée doit être mémorable.

**Notification "Votre livre est prêt" :**
1. Push notification → ouverture app sur l'écran de réception
2. Animation d'ouverture : un rectangle (la "couverture du livre") descend du haut de l'écran
3. La couverture s'ouvre (rotateY 0 → 90) révélant l'aperçu du PDF
4. Pages qui se "feuillettent" (stagger de 3 thumbnails, chacun avec un léger décalage rotatif)
5. Bouton "Voir mon livre" + bouton "Partager"
6. Durée totale : ~1.2s. Peut être ignorée en tapant n'importe où.

---

## Reduced Motion

**Règle impérative :** Respecter `prefers-reduced-motion: reduce`.

```typescript
// Hook à utiliser dans tous les composants animés
const prefersReducedMotion = useReducedMotion()

const variants = prefersReducedMotion
  ? { hidden: { opacity: 0 }, visible: { opacity: 1 } }
  : { hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }
```

**En mode reduced motion :**
- Toutes les animations de translation (x, y) sont supprimées
- Seuls les fades (opacity) sont conservés, à 150ms max
- Les animations de célébration (particules, flip card) sont remplacées par un simple fade
- Les View Transitions se font en cross-fade simple

---

## Performance Budget Motion

| Type d'animation | Budget GPU | Propriétés autorisées |
|---|---|---|
| Micro-interactions | Faible | transform, opacity uniquement |
| Transitions page | Moyen | transform, opacity (GPU promoted) |
| Célébrations | Élevé ponctuel | transform, opacity, will-change: transform |
| Backgrounds | INTERDIT | Pas d'animation sur background-color, box-shadow animés |

**Règle :** N'animer que `transform` et `opacity`. Jamais `width`, `height`, `top`, `left`, `margin`, `padding`. Ces propriétés déclenchent un reflow.

**Exception contrôlée :** `box-shadow` au hover de card (dans Tailwind, via transition-shadow) — acceptable car isolé à un seul composant et déclenché par interaction humaine.

---

## Stagger Patterns

Quand plusieurs éléments apparaissent ensemble, les décaler visuellement donne une impression de vie.

| Contexte | Stagger delay |
|---|---|
| Feed de cards recettes | 80ms entre cards |
| Badges sur une fiche | 40ms entre badges |
| Items d'une liste | 50ms entre items |
| Étoiles de notation | 40ms entre étoiles |
| Tooltips groupés | 30ms entre items |

**Limite :** Ne pas appliquer le stagger à plus de 8 éléments (au-delà, le dernier attend trop longtemps).
