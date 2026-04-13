# Audit Frontend v3 -- Exhaustif

> Date : 2026-04-12
> Auditeur : Claude Code (Opus 4.6)
> Scope : chaque page/composant du frontend Next.js 14
> Methode : lecture ligne par ligne de chaque fichier, validation des types, des handlers, du mapping API

---

## Par page

### /dashboard

**Fichiers** : `dashboard/page.tsx`, `dashboard/dashboard-content.tsx`

- OK : Le bouton "Generer" ouvre bien le modal (`openGenerateModal` -> `setShowGenerateModal(true)`)
- OK : Le modal envoie les filtres a l'API via `handleGenerateWithFilters` -> `generateMutation.mutate({ max_time, budget, style })`
- OK : Apres generation, le polling est relance via `startPolling()` passe a `useGeneratePlan`
- OK : Le plan s'affiche via `PlanWeekGrid` avec `currentPlan` (client) ou `initialPlanData` (SSR)
- OK : "Modifier mon plan" = bouton `onRegenerate` dans `PlanActions` qui ouvre le modal de generation
- OK : "Valider" = `validateMutation.mutate(planId)` dans `PlanActions`
- OK : Textes en francais

- BUG-F001 : **Accents manquants dans les textes hardcodes** -- `dashboard-content.tsx` lignes 272, 273, 289, 292, 312, 315 : "Generer", "Generation" au lieu de "Generer", "Generation". Meme probleme dans `plan-actions.tsx` ligne 79 "Regenerer". Ce sont des accents manquants systematiques (e au lieu de e accent).
  - **Gravite** : Cosmetique (faible)
  - **Fix** : Remplacer par les caracteres accentues corrects

- BUG-F002 : **`toast` importe de deux sources differentes** -- `use-plan.ts` importe `toast` depuis `"sonner"` (ligne 22) tandis que `client.ts` importe `toast` depuis `"@/components/ui/toast"` (ligne 9). Les signatures sont **incompatibles** : le wrapper `@/components/ui/toast` expose `toast.warning(message, description)` avec 2 args string, tandis que Sonner expose `toast.error(msg, { description })` avec un objet options. Le hook `use-plan.ts` et tous les hooks utilisent la signature Sonner directement -- c'est correct. Mais `client.ts` utilise le wrapper qui **ne supporte pas les options avancees** (duration, action, etc.). Risque d'incoherence si un developpeur copie le pattern du client API.
  - **Gravite** : Moyenne (risque de regression)
  - **Fix** : Unifier sur l'import direct de `sonner` partout, ou enrichir le wrapper `toast.tsx` pour supporter les memes options

- BUG-F003 : **`recipe.servings > 0` sans guard null** -- `recipes/[id]/page.tsx` ligne 211 : `{recipe.servings > 0 && ...}`. Le type `servings` est `number | null | undefined`. Comparer `null > 0` retourne `false` en JS (pas de crash), mais `undefined > 0` aussi retourne `false`. **Pas de crash** mais la verification n'est pas explicite. Un linter strict pourrait alerter.
  - **Gravite** : Tres faible (pas de crash, comportement correct par coincidence)
  - **Fix** : `{recipe.servings != null && recipe.servings > 0 && ...}`

---

### /dashboard -- PlanWeekGrid

**Fichier** : `components/plan/plan-week-grid.tsx`

- OK : Jours en FR (`DAYS_FR` avec labels Lundi-Dimanche)
- OK : Bouton "Changer" (RefreshCw) visible et cable vers `onSwapMeal(meal.id)` avec `e.preventDefault()` + `e.stopPropagation()` pour eviter la navigation du `<Link>`
- OK : "+Samedi" / "+Dimanche" cables vers `onAddDay(SATURDAY)` / `onAddDay(SUNDAY)`
- OK : N'apparaissent qu'en mode draft et si le jour n'a pas deja de repas
- OK : day_of_week int ISO 1-7, mapping correct

- BUG-F004 : **`containerVariants` declare mais jamais utilise** -- ligne 72-78 : `containerVariants` est defini avec `staggerChildren: 0.08` mais n'est **jamais passe** a un composant parent. La grille utilise un `<div>` standard (pas un `MotionDiv`), donc le stagger ne fonctionne pas. Les `itemVariants` sur chaque `MotionDiv` enfant marchent individuellement mais **sans stagger**.
  - **Gravite** : Cosmetique (l'animation stagger ne fonctionne pas comme prevu)
  - **Fix** : Remplacer le `<div className="grid ...">` par `<MotionDiv variants={containerVariants} initial="hidden" animate="visible" className="grid ...">`

- BUG-F005 : **`loading: () => null` dans MotionDiv** -- Quand framer-motion n'est pas encore charge (SSR hydration), `MotionDiv` retourne `null` (pas de fallback). Cela signifie que toutes les cartes de la grille sont **invisibles** pendant le chargement du chunk framer-motion. Sur connexion lente, il y a un flash : contenu vide -> contenu rendu.
  - **Gravite** : Moyenne (UX : flash de contenu vide)
  - **Fix** : Changer `loading: () => null` en un composant qui rend un `<div>` standard avec les memes classes CSS

---

### /dashboard -- SwapSuggestionsPanel

**Fichier** : `components/plan/swap-suggestions-panel.tsx`

- OK : Panel s'ouvre via Radix Dialog controle (`open` prop)
- OK : Suggestions chargees depuis l'API via `useRecipeSuggestions(planId, filters, open)` -- `enabled` = `open`
- OK : Clic sur une suggestion appelle `onSelectRecipe(recipe.id)` puis le parent fait le swap/add
- OK : Textes en francais

Pas de bug identifie.

---

### /dashboard -- GeneratePlanModal

**Fichier** : `components/plan/generate-plan-modal.tsx`

- OK : 4 questions affichees (temps, budget, style, envie)
- OK : Filtres envoyes a l'API (sauf `envie` qui est informatif -- documente en commentaire)
- OK : `handleGenerate` appelle `onGenerate({ max_time, budget, style })`

- BUG-F006 : **Le budget "Moyen" est mappe sur `null`** -- ligne 37 : `{ label: "Moyen", value: null }`. Quand l'utilisateur selectionne "Moyen", le filtre budget n'est PAS envoye a l'API (null est filtre dans `endpoints.ts` ligne 193 : `params?.budget != null`). Cela signifie que "Moyen" = pas de filtre = comportement identique a "ne rien selectionner". L'utilisateur pense filtrer mais ne filtre pas.
  - **Gravite** : Moyenne (UX trompeuse, pas de bug technique)
  - **Fix** : Envoyer `"moyen"` a l'API au lieu de `null`, aligne sur l'enum backend `"economique" | "moyen" | "premium"`

- BUG-F007 : **Accents manquants** -- "Personnalisez", "Generer" sans accents dans le JSX (lignes 168, 190, 260, 266). Meme pattern que BUG-F001.
  - **Gravite** : Cosmetique
  - **Fix** : Ajouter les accents

---

### /recipes

**Fichiers** : `recipes/page.tsx`, `recipes/recipes-explorer.tsx`, `recipe-card.tsx`

- OK : Pagination fonctionnelle (`Pagination` component, `handlePageChange`, scroll to top)
- OK : Filtres fonctionnels (quick pills + sidebar avancee)
- OK : Images s'affichent (photo_url || image_url || placeholder Unsplash)
- OK : Textes en francais

- BUG-F008 : **Le bouton "Tous les filtres" ne fait rien de visible** -- `recipes-explorer.tsx` ligne 196-206 : le bouton "Tous les filtres" reset les filtres et le quick filter, mais il devrait probablement **ouvrir** le panneau de filtres. Il agit comme un bouton "Reset" deguise. L'utilisateur ne comprend pas pourquoi "Tous les filtres" reinitialise tout.
  - **Gravite** : Moyenne (UX confuse)
  - **Fix** : Soit renommer le label en "Reinitialiser" (avec icone RotateCcw), soit ouvrir le panel filtres mobile

- BUG-F009 : **`difficulty: 2` envoye pour le filtre "Facile"** -- ligne 117 : `activeQuickFilter === "easy" && { difficulty: 2 }`. L'API attend `max_difficulty` (converti dans `searchRecipesAdvanced`), et `difficulty: 2` sur le type `RecipeFilters` est de type `1 | 2 | 3 | 4 | 5`. Fonctionnel mais conceptuellement, "Facile" devrait probablement envoyer `max_difficulty: 2` pour inclure aussi "Tres facile (1)". C'est le comportement actuel grace a la conversion dans `endpoints.ts` ligne 353 (`params.set("max_difficulty", ...)`). **Pas un bug technique**, mais la semantique `difficulty: 2` sur le type RecipeFilters est ambigue (est-ce "exactement 2" ou "max 2" ?).
  - **Gravite** : Faible (fonctionne mais semantique ambigue)
  - **Fix** : Documenter dans le type ou renommer le champ

---

### /recipes/[id]

**Fichiers** : `recipes/[id]/page.tsx`, `recipe-tabs-client.tsx`

- OK : Page ne crash pas (try/catch + notFound() si null)
- OK : Ingredients affichent (normalisation `canonical_name` -> `name`, `ingredient_id` -> `id`)
- OK : Instructions affichent (normalisation `step/text` -> `step_number/description`)
- OK : Photo affiche (hero image avec fallback placeholder)
- OK : Tabs Radix fonctionnels (Ingredients / Instructions / Nutrition)

- BUG-F010 : **`fetchRecipe` dans le Server Component n'utilise PAS le fallback Railway** -- `page.tsx` ligne 38 : `const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;` puis ligne 42 : `if (!token || !apiBaseUrl) return null;`. Le client-side `client.ts` a un fallback vers `RAILWAY_API_URL` si la variable est absente, mais le server component **ne l'a pas**. Si `NEXT_PUBLIC_API_URL` n'est pas defini sur Vercel, toutes les pages recette seront en 404.
  - **Gravite** : Haute (page cassee si variable d'environnement manquante)
  - **Fix** : Ajouter le meme fallback : `const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://meal-planner-saas-production.up.railway.app";`

- BUG-F011 : **Meme probleme dans `account/page.tsx`** -- ligne 54 : `const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;` sans fallback. La page compte sera vide (sans donnees foyer) si la variable manque.
  - **Gravite** : Haute
  - **Fix** : Meme fallback

- BUG-F012 : **`quality_score * 5` peut produire des ratings >5** -- `endpoints.ts` ligne 309 : `rating_average: raw.quality_score != null ? raw.quality_score * 5 : (raw.rating_average ?? null)`. Si `quality_score` est deja sur une echelle 0-5 (au lieu de 0-1), cela produit des ratings jusqu'a 25. Idem dans `page.tsx` ligne 75. Dependant du contrat API reel.
  - **Gravite** : Moyenne (affichage incorrect si le contrat API change)
  - **Fix** : Ajouter un `Math.min(result, 5)` ou documenter le contrat

---

### /account

**Fichiers** : `account/page.tsx`, `account/account-content.tsx`

- OK : Page charge (guard auth avec redirect /login)
- OK : Donnees user affichees (email, nom, date inscription)
- OK : Membres du foyer affiches (avec badge "Enfant")
- OK : Bouton deconnexion cable (`supabase.auth.signOut()` + redirect /login)
- OK : Textes en francais

Voir BUG-F011 ci-dessus (fallback API manquant).

---

### /settings

**Fichiers** : `settings/page.tsx`, `settings/settings-content.tsx`

- OK : Page charge (loading state pendant le fetch household)
- OK : Preferences affichees (regimes, allergies, temps, drive, theme)
- OK : Modifications sauvegardees (`apiClient.patch`)

- BUG-F013 : **Le theme selectionne n'est PAS applique** -- `settings-content.tsx` : le theme est sauvegarde dans `localStorage` (ligne 108) mais **jamais lu ni applique**. Il n'y a pas de logique dans `theme-provider.tsx` ou `root-providers.tsx` pour appliquer la classe `dark` sur le `<html>`. Le bouton theme est decoratif.
  - **Gravite** : Moyenne (feature promise mais non fonctionnelle)
  - **Fix** : Implementer la logique dans le ThemeProvider qui lit `localStorage("presto-theme")` et applique la classe `dark`

- BUG-F014 : **Le drive provider n'est PAS envoye a l'API** -- ligne 114-126 : `apiClient.patch(url, { diet_tags, allergies, dislikes, cooking_time_max, budget_pref })`. Le champ `driveProvider` du formulaire n'est **jamais inclus** dans le payload PATCH. L'API endpoint est pour les preferences du membre, pas du household. Il faudrait un second appel pour mettre a jour `drive_provider` sur le household.
  - **Gravite** : Haute (donnee jamais sauvegardee)
  - **Fix** : Ajouter un appel `apiClient.patch("/api/v1/households/me", { drive_provider: form.driveProvider })` ou un endpoint dedie

---

### /shopping-list

**Fichier** : `shopping-list/page.tsx`

- OK : Items affiches avec noms + quantites (normalisation `canonical_name` -> `ingredient_name`)
- OK : Cochage fonctionne (`handleToggle` -> `toggleMutation.mutate`)
- OK : Items groupes par rayon (via `byCategory` + `RAYON_ORDER`)
- OK : Quantites aggregees affichees via `quantity_display`

- BUG-F015 : **Double groupement inutile -- `byRayon` calcule mais jamais utilise** -- lignes 71-77 : `byRayon` est construite mais le rendu utilise `byCategory` (ligne 204). Le `byRayon` inclut le rayon FR de l'API mais est ignore. C'est du code mort.
  - **Gravite** : Faible (code mort, pas de bug visible)
  - **Fix** : Supprimer `byRayon` ou l'utiliser pour le rendu a la place de `byCategory`

- BUG-F016 : **`getShoppingList` utilise un chemin d'URL douteux** -- `endpoints.ts` ligne 268 : `"/api/v1/plans/me/${planId}/shopping-list"`. Ce chemin contient `/me/` suivi d'un `planId` specifique. C'est inhabituel -- soit c'est `/api/v1/plans/me/shopping-list` (plan courant implicite), soit `/api/v1/plans/${planId}/shopping-list` (plan explicite). Le `/me/` est potentiellement superflu ou incorrect. Depend du contrat backend.
  - **Gravite** : Potentiellement haute (404 si le backend ne supporte pas cette route)
  - **Fix** : Verifier avec le backend. Probablement `/api/v1/plans/${planId}/shopping-list`

---

### /fridge

**Fichiers** : `fridge/page.tsx`, `fridge/fridge-content.tsx`

- OK : Page charge
- OK : Ajout d'un produit fonctionne (`addMutation.mutate(data)` + dialog ferme au succes)
- OK : Suppression fonctionne (`removeMutation.mutate(id)` + optimistic update)
- OK : Suggestions recettes fonctionnelles
- OK : Textes en francais

Pas de bug identifie.

---

### /books

**Fichiers** : `books/page.tsx`, `books/books-content.tsx`

- OK : Page charge
- OK : Feature gating fonctionne (UpgradeGate avec blur si plan starter)
- OK : Telechargement PDF via `<a href={book.pdf_url} download>`
- OK : Regeneration via `generateMutation.mutate(planId)`

- BUG-F017 : **Le bouton Plus en haut a droite n'est pas cable** -- `books-content.tsx` ligne 108-109 : un `<div>` avec icone `<Plus>` est rendu mais sans `onClick` handler. C'est un element decoratif qui ressemble a un bouton mais ne fait rien.
  - **Gravite** : Faible (UX confuse -- element cliquable en apparence mais inactif)
  - **Fix** : Soit supprimer, soit le relier a une action (ex: generer un nouveau livre)

---

### /billing

**Fichiers** : `billing/page.tsx`, `billing/billing-content.tsx`, `billing/success/page.tsx`, `billing/cancel/page.tsx`

- OK : Page charge
- OK : Plan courant affiche
- OK : CTA upgrade fonctionne (`checkoutMutation.mutate()` -> redirect Stripe)
- OK : Portail Stripe fonctionne (`portalMutation.mutate()` -> redirect)
- OK : Page succes avec confetti et recap features
- OK : Page cancel avec CTA retour

Pas de bug identifie.

---

### /login, /signup (Auth)

**Fichiers** : `(auth)/login/page.tsx`, `(auth)/signup/page.tsx`

- OK : Login email+password fonctionne (`signInWithPassword`)
- OK : Login magic link fonctionne (`signInWithOtp`)
- OK : Signup email+password fonctionne (`signUp`)
- OK : Signup magic link fonctionne (`signInWithOtp` avec `shouldCreateUser: true`)
- OK : Validation email + mot de passe (8 chars, 1 majuscule, 1 chiffre)
- OK : Mot de passe oublie fonctionne (`resetPasswordForEmail`)
- OK : Open redirect bloque (`getSafeRedirectUrl`)
- OK : Textes en francais

- BUG-F018 : **Deux routes callback auth avec logique dupliquee** -- `(auth)/callback/route.ts` et `app/auth/callback/route.ts` font le meme travail (echange PKCE, verification household, redirect). Le signup redirige vers `/auth/callback?next=...` tandis que le login redirige vers `/auth/callback` aussi. Les deux callback utilisent des parametres differents (`redirect` vs `next`). Le callback `(auth)` cherche `searchParams.get("redirect")` tandis que `app/auth` cherche `searchParams.get("next")`. Confusion potentielle.
  - **Gravite** : Moyenne (duplication, risque de divergence)
  - **Fix** : Consolider en un seul callback

---

### Hooks API (`endpoints.ts`)

- OK : `generatePlan` envoie `week_start` + filtres optionnels
- OK : `searchRecipesAdvanced` envoie `max_difficulty` (pas `difficulty`)
- OK : `normalizeRecipe` mappe les champs API bruts vers le format frontend
- OK : `normalizePlanDetail` garantit la structure plate
- OK : `swapMeal` envoie `{ new_recipe_id }`
- OK : `createFeedback` envoie le bon enum backend

Voir BUG-F016 pour `getShoppingList`.

---

### Types (`types.ts`)

- OK : Interfaces alignees sur les reponses API (avec documentation des deux formats)
- OK : `DietaryTag` couvre les variantes FR/EN avec et sans tirets/underscores
- OK : `Instruction` supporte les deux formats API (`step_number/description` et `step/text`)
- OK : `PaginatedResponse` supporte `data` et `results`

- BUG-F019 : **`DietaryTag` est un union trop large** -- Le type inclut `"vegetarian"`, `"vegetarien"`, `"vegetarien"` (sans accent), `"gluten-free"`, `"gluten_free"`, etc. Cela fonctionne en runtime mais rend le type quasiment inutile comme contrainte a la compilation (n'importe quelle variante est acceptee). Un mapping de normalisation serait plus propre.
  - **Gravite** : Faible (pas de bug runtime, maintenabilite reduite)
  - **Fix** : Normaliser les tags cote client vers un format canonique

---

## Liste complete des bugs

| ID | Page | Description | Gravite | Fichier | Fix |
|---|---|---|---|---|---|
| BUG-F001 | /dashboard | Accents manquants dans les textes hardcodes ("Generer" au lieu de "Generer") | Cosmetique | `dashboard-content.tsx:272,289` | Ajouter les accents |
| BUG-F002 | Global | `toast` importe de 2 sources incompatibles (sonner vs wrapper) | Moyenne | `client.ts:9` vs hooks | Unifier sur sonner |
| BUG-F003 | /recipes/[id] | `recipe.servings > 0` sans guard null explicite | Tres faible | `recipes/[id]/page.tsx:211` | Ajouter `!= null &&` |
| BUG-F004 | /dashboard | `containerVariants` (stagger) declare mais jamais utilise | Cosmetique | `plan-week-grid.tsx:72` | Passer au parent MotionDiv |
| BUG-F005 | Global | `MotionDiv` retourne null pendant le chargement (flash vide) | Moyenne | `motion/index.tsx:35` | Rendre un div standard en fallback |
| BUG-F006 | /dashboard | Budget "Moyen" mappe sur null = pas de filtre envoye | Moyenne | `generate-plan-modal.tsx:37` | Envoyer `"moyen"` |
| BUG-F007 | /dashboard | Accents manquants dans le modal generation | Cosmetique | `generate-plan-modal.tsx` | Ajouter les accents |
| BUG-F008 | /recipes | Bouton "Tous les filtres" agit comme Reset au lieu d'ouvrir les filtres | Moyenne | `recipes-explorer.tsx:196` | Renommer ou changer le comportement |
| BUG-F009 | /recipes | `difficulty: 2` semantique ambigue (exact vs max) | Faible | `recipes-explorer.tsx:117` | Documenter |
| BUG-F010 | /recipes/[id] | **fetchRecipe sans fallback API URL** -- page 404 si env var manquante | **Haute** | `recipes/[id]/page.tsx:38` | Ajouter fallback Railway |
| BUG-F011 | /account | **fetchHousehold sans fallback API URL** -- donnees manquantes si env var absente | **Haute** | `account/page.tsx:54` | Ajouter fallback Railway |
| BUG-F012 | /recipes/[id] | `quality_score * 5` peut depasser 5 si echelle incorrecte | Moyenne | `endpoints.ts:309` | Ajouter Math.min |
| BUG-F013 | /settings | **Theme selectionne jamais applique** (localStorage ecrit mais jamais lu) | Moyenne | `settings-content.tsx:108` | Implementer ThemeProvider |
| BUG-F014 | /settings | **Drive provider jamais sauvegarde** -- absent du payload PATCH | **Haute** | `settings-content.tsx:114` | Ajouter l'appel API |
| BUG-F015 | /shopping-list | Code mort : `byRayon` calcule mais jamais utilise dans le rendu | Faible | `shopping-list/page.tsx:71` | Supprimer ou utiliser |
| BUG-F016 | /shopping-list | **Chemin API `/plans/me/${planId}/shopping-list`** potentiellement incorrect | Potentiellement haute | `endpoints.ts:268` | Verifier avec le backend |
| BUG-F017 | /books | Bouton Plus decoratif non cable | Faible | `books-content.tsx:108` | Supprimer ou caler |
| BUG-F018 | Auth | Deux routes callback auth dupliquees avec parametres differents | Moyenne | `(auth)/callback` vs `app/auth/callback` | Consolider |
| BUG-F019 | Types | DietaryTag union trop large, pas de normalisation | Faible | `types.ts:281` | Normaliser |

---

## Resume

### Bugs critiques (haute gravite) : 4
- **BUG-F010** : Page recette cassee si NEXT_PUBLIC_API_URL non defini (Server Component sans fallback)
- **BUG-F011** : Page compte pareil
- **BUG-F014** : Drive provider jamais sauvegarde (feature brisee silencieusement)
- **BUG-F016** : Chemin API shopping-list potentiellement incorrect

### Bugs moyens : 7
- BUG-F002 : Toast importe de 2 sources
- BUG-F005 : Flash vide pendant chargement framer-motion
- BUG-F006 : Budget "Moyen" = pas de filtre
- BUG-F008 : Bouton "Tous les filtres" = Reset
- BUG-F012 : Rating potentiellement >5
- BUG-F013 : Theme non applique
- BUG-F018 : Callback auth duplique

### Bugs faibles/cosmetiques : 8
- BUG-F001, F003, F004, F007, F009, F015, F017, F019

### Ce qui fonctionne bien
- Architecture hooks TanStack Query solide (polling, optimistic updates, invalidation)
- Normalisation API → frontend bien pensee (double format absorbe)
- Auth complete (password + magic link + password reset)
- Accessibilite correcte (aria-label, aria-pressed, aria-busy, roles)
- Textes majoritairement en FR
- Feature gating billing fonctionnel
- Swipe-to-delete sur mobile (Framer Motion)
