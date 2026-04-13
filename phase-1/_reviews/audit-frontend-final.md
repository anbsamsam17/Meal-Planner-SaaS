# Audit Frontend Presto -- Exhaustif

**Date** : 2026-04-12
**Cible** : https://hop-presto-saas-sa.vercel.app
**Scope** : Toutes les pages, tous les composants, tous les hooks, API client, i18n, filtres

---

## Par page

### / (Landing)

- [x] OK : La page compile (Server Component RSC, fetch recettes avec fallback statique)
- [x] OK : Textes en francais
- [x] OK : Fetch recettes avec timeout 5s + fallback FALLBACK_RECIPES
- [ ] BUG-LAND-01 : Les liens footer `/about`, `/legal/terms`, `/legal/privacy`, `/contact` pointent vers des routes qui n'existent pas dans `apps/web/src/app/` -- ces pages retourneront une 404
- [ ] BUG-LAND-02 : Le CTA "Commencer gratuitement" pointe vers `/onboarding` qui redirige vers `/onboarding/step-1`, mais l'onboarding ne verifie pas l'authentification -- un utilisateur non connecte arrive sur step-1 sans session, et le `submit()` echouera (pas de JWT pour les appels API)
- [ ] BUG-LAND-03 : La section `#pricing` n'a pas d'ancre `id="pricing"` sur le lien nav -- en fait c'est correct, la section a bien `id="pricing"`
- [x] OK : Images Unsplash configurees dans `next.config.mjs` remotePatterns

### /login

- [x] OK : La page compile (Client Component)
- [x] OK : Textes en francais
- [x] OK : 3 modes (password, magic-link, forgot-password)
- [x] OK : Gestion erreurs rate limit, invalid credentials, email not confirmed
- [x] OK : Redirection post-login securisee (getSafeRedirectUrl bloque open redirect)
- [x] OK : Validation email cote client

### /signup

- [x] OK : La page compile (Client Component)
- [x] OK : Textes en francais
- [x] OK : Validation mot de passe (8 chars, 1 majuscule, 1 chiffre)
- [x] OK : Redirect post-signup vers `/auth/callback?next=/onboarding/step-1`
- [x] OK : Mode magic-link alternatif

### /onboarding/step-1

- [x] OK : La page compile (Client Component + Zustand store)
- [x] OK : Textes en francais
- [x] OK : Compteurs adultes/enfants avec min/max
- [x] OK : Tranches d'age enfants revelees conditionnellement
- [ ] BUG-ONB-01 : La barre de progression du layout onboarding (`(onboarding)/layout.tsx` ligne 52) a `style={{ width: "0%" }}` en dur -- elle ne se remplit JAMAIS. Le commentaire dit "Gere dynamiquement par le composant enfant" mais aucun composant enfant ne met a jour ce style. L'utilisateur voit toujours 3 barres vides.

### /onboarding/step-2

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : "Pas de restriction" en premier et en taille XL (regle UX)
- [x] OK : Mapping RESTRICTION_TO_DIET_TAG et RESTRICTION_TO_ALLERGY correct

### /onboarding/step-3

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Selection temps de cuisine + drive
- [x] OK : Submit appelle le store Zustand submit()
- [ ] BUG-ONB-02 : Le `isLoading` est derive de `currentStep === "generating"` mais la detection est fragile -- si l'utilisateur quitte la page generating et revient sur step-3, le bouton peut rester en etat loading

### /generating

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Messages rotatifs pendant la generation
- [x] OK : Redirect vers /dashboard quand `currentStep === "done"`
- [x] OK : Rollback vers step-X si erreur

### /dashboard

- [x] OK : La page compile (Server Component + Client Component DashboardContent)
- [x] OK : Textes en francais
- [x] OK : Fetch plan courant SSR avec fallback gracieux
- [x] OK : Prenom de bienvenue depuis Supabase metadata
- [ ] BUG-DASH-01 : Les boutons navigation semaine (fleches <- et ->) dans `dashboard/page.tsx` lignes 91-109 n'ont AUCUN `onClick` handler -- ils sont purement decoratifs et ne font rien quand on clique
- [ ] BUG-DASH-02 : Le handler `handleGenerate` dans `dashboard-content.tsx` ne passe pas `week_start` dans le body de la mutation -- mais en realite `generatePlan()` dans `endpoints.ts` le calcule avec `getNextMonday()`, donc c'est OK
- [x] OK : Retry automatique apres "Failed to fetch" avec delai 3s

### /recipes (liste)

- [x] OK : La page compile
- [x] OK : Textes en francais (barre de recherche, pills, pagination)
- [x] OK : Pagination numerotee avec ellipses
- [x] OK : Quick filters (Rapide, Desserts, Vegetarien, Facile)
- [ ] BUG-REC-01 : Le quick filter "Vegetarien" envoie `diet: "vegetarien"` (ligne 116 recipes-explorer.tsx) mais l'API backend fait `":diet" = ANY(tags)` -- cela ne marche QUE si la DB contient des recettes avec le tag exactement `vegetarien` dans le tableau `tags`. Si les recettes ont `vegetarian` (anglais) dans la DB, le filtre ne retournera rien.
- [ ] BUG-REC-02 : Le quick filter "Desserts" envoie `q: "dessert"` qui ecrase la recherche textuelle de l'utilisateur -- si l'utilisateur a tape "poulet" et clique "Desserts", sa recherche est perdue
- [ ] BUG-REC-03 : La reponse de `searchRecipesAdvanced` parse `data.results ?? data.data` mais le composant `RecipesExplorer` fait aussi `(data as any)?.results ?? (data as any)?.data` -- double parsing redondant, et le type retourne est deja normalise par `searchRecipesAdvanced`

### /recipes/[id] (detail)

- [x] OK : La page compile (Server Component + Client RecipeTabsClient)
- [x] OK : Textes en francais (tabs "Ingredients", "Instructions", "Nutrition")
- [x] OK : Normalisation defensive des champs API (photo_url, temps, cuisine, difficulty, ingredients)
- [x] OK : Placeholder Unsplash deterministe si pas de photo
- [x] OK : DIFFICULTY_LABELS couvre les formats string ET numerique
- [ ] BUG-RECID-01 : Le `fetchRecipe` utilise `createServerClient()` et `getSession()` pour obtenir le token -- mais si l'API `NEXT_PUBLIC_API_URL` n'est pas definie, la fonction retourne `null` et la page affiche `notFound()`. Or en production, `NEXT_PUBLIC_API_URL` est une variable d'environnement build-time -- si elle n'est pas configuree sur Vercel, TOUTES les fiches recettes seront 404.
- [ ] BUG-RECID-02 : Les titres des recettes venant de TheMealDB ou Spoonacular sont probablement en ANGLAIS (ex: "Chicken Tikka Masala" au lieu de "Poulet Tikka Masala") -- le frontend affiche `recipe.title` tel quel sans traduction. Ce n'est pas un bug de code mais un probleme de donnees.
- [ ] BUG-RECID-03 : `recipe-tabs-client.tsx` importe `@radix-ui/react-tabs` -- si le package n'est pas installe, la page crash

### /fridge

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Dialog ajout produit avec nom, quantite, unite, date expiration
- [x] OK : Suggestions recettes basees sur le frigo
- [x] OK : Swipe-to-delete avec Framer Motion (direct import, pas dynamic)
- [ ] BUG-FRIDGE-01 : `fridge-item.tsx` importe DIRECTEMENT depuis `framer-motion` (`import { motion, useMotionValue, useTransform, animate } from "framer-motion"`) au lieu d'utiliser `@/components/motion` -- cela contredit la regle etablie dans `components/motion/index.tsx` et ajoute du poids au bundle
- [ ] BUG-FRIDGE-02 : La page wrapper `fridge/page.tsx` utilise `bg-cream-50` qui n'est probablement pas defini dans le Tailwind config (la landing utilise `bg-[#fff8f6]` et le design system reference `hsl(38,60%,97%)`) -- risque de fond blanc/transparent au lieu du cream attendu

### /books

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Feature gate UpgradeGate pour le plan Famille
- [x] OK : Generation et telechargement PDF
- [ ] BUG-BOOKS-01 : Meme probleme que le frigo -- `books/page.tsx` utilise `bg-cream-50` qui n'est probablement pas defini dans Tailwind
- [ ] BUG-BOOKS-02 : Le hook `getPlansHistory` est utilise comme `queryFn` pour les books mais l'endpoint retourne `BookInfo[]` -- c'est coherent avec les types

### /shopping-list

- [x] OK : La page compile (Client Component)
- [x] OK : Textes en francais
- [x] OK : Groupement par rayon supermarche francais
- [x] OK : Progression visuelle (cercle SVG + barre)
- [x] OK : Bouton "Envoyer au drive" desactive (Phase 3)
- [ ] BUG-SHOP-01 : Le `useToggleItem` mutation fait un update LOCAL uniquement (`Phase 1 -- mise a jour locale uniquement`) -- le toggle n'est PAS persiste cote serveur. Si l'utilisateur refresh la page, tous les checks sont perdus.
- [ ] BUG-SHOP-02 : La page est un Client Component DIRECT (`"use client"` dans `page.tsx`) sans metadata export -- pas de title/description SEO pour cette page

### /billing

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Comparaison plans Starter/Famille
- [x] OK : CTA checkout Stripe + portail Stripe
- [ ] BUG-BILL-01 : `billing/page.tsx` utilise `bg-cream-50` -- meme probleme potentiel que fridge et books

### /billing/success

- [x] OK : La page compile
- [x] OK : Textes en francais
- [x] OK : Animation confetti Framer Motion
- [ ] BUG-BILLSUC-01 : `billing/success/page.tsx` importe DIRECTEMENT depuis `framer-motion` (`import { motion, AnimatePresence } from "framer-motion"`) au lieu de `@/components/motion` -- inconsistance et poids bundle
- [ ] BUG-BILLSUC-02 : `billing/success/page.tsx` utilise `bg-cream-50` -- meme probleme potentiel

### /billing/cancel

- [x] OK : La page compile (Server Component)
- [x] OK : Textes en francais
- [ ] BUG-BILLCAN-01 : `billing/cancel/page.tsx` utilise `bg-cream-50`

### /account

- [x] OK : La page compile (Server Component + Client AccountContent)
- [x] OK : Textes en francais
- [x] OK : Profil utilisateur + foyer + liens rapides + deconnexion
- [ ] BUG-ACC-01 : La route `/account` n'est PAS dans `PROTECTED_ROUTES` du middleware.ts -- le middleware ne redirige pas vers /login si non authentifie. CEPENDANT, le layout `(app)/layout.tsx` fait un `redirect("/login")` cote serveur si pas de user, donc la protection existe quand meme. Mais le middleware ne rafraichit pas le token pour cette route specifiquement (il le fait quand meme car le matcher est global).
- [x] OK : En fait, `/account` est protege via le layout (app) qui verifie l'auth -- pas de bug reel

### /settings

- [x] OK : La page compile (Server Component + Client SettingsContent)
- [x] OK : Textes en francais
- [x] OK : Formulaire preferences (regimes, allergies, temps, drive, theme)
- [x] OK : Suppression de compte avec confirmation "SUPPRIMER"
- [ ] BUG-SET-01 : `useHousehold()` retourne un type `HouseholdResponse` dont `household` est de type `Household` (avec `members` imbriques), mais le composant accede a `household.preferences` qui est `HouseholdPreferences | null` -- si l'API ne retourne pas `preferences`, le formulaire utilise les valeurs par defaut. Pas un crash, mais les donnees de l'utilisateur ne seront pas pre-remplies.
- [ ] BUG-SET-02 : Le theme est sauvegarde en `localStorage` uniquement -- le script anti-FOUC dans `layout.tsx` le lit bien, mais le changement de theme dans les settings ne met PAS a jour la classe `dark` sur `<html>` en temps reel. L'utilisateur doit recharger la page pour voir le changement.

---

## Textes anglais trouves

### Titres de recettes (donnees API / DB)
Les recettes provenant de TheMealDB ou Spoonacular ont des titres EN ANGLAIS dans la base de donnees. Le frontend affiche `recipe.title` sans traduction.

**Fichiers concernes** :
- `apps/web/src/components/recipe/recipe-card.tsx:137` -- `{recipe.title}`
- `apps/web/src/app/(app)/recipes/[id]/page.tsx:193` -- `{recipe.title}`
- `apps/web/src/components/plan/plan-week-grid.tsx:103` -- via RecipeCard
- `apps/web/src/app/page.tsx:216` -- StaticRecipeCard (mais les fallback sont en FR)

### Labels UI potentiellement en anglais
- `apps/web/src/lib/api/types.ts:97` -- `day_of_week` enum values en anglais (`"monday"`, `"tuesday"`...) mais ils sont traduits dans `plan-week-grid.tsx` via `DAY_LABELS`
- `apps/web/src/lib/api/types.ts:295-305` -- `IngredientCategory` en anglais (`"vegetables"`, `"meat"`...) mais traduits dans `ingredient-list.tsx` et `shopping-list/page.tsx` via les maps `CATEGORY_LABELS` et `RAYON_LABELS`

### Textes anglais dans le code (non visibles par l'utilisateur sauf erreur)
- `apps/web/src/hooks/use-recipes.ts:22` -- `throw new Error("Recipe ID requis")` -- melange FR/EN mais c'est un message d'erreur developpeur
- `apps/web/src/hooks/use-shopping-list.ts:19` -- `throw new Error("Plan ID requis")`
- `apps/web/src/hooks/use-plan.ts:51` -- `throw new Error("Plan ID requis")`

### Verdict textes
**L'interface utilisateur est integralement en francais.** Le seul probleme est que les DONNEES (titres de recettes, cuisines, tags) venant de l'API sont potentiellement en anglais selon la source d'import dans la DB.

---

## Filtres -- Matrice de compatibilite

### Quick Filters (recipes-explorer.tsx)

| Filtre | Param envoye (frontend) | Param API attendu (backend) | Match ? | Notes |
|---|---|---|---|---|
| Rapide (< 15 min) | `max_time=15` | `max_time` (int, filtre `total_time_min <= :max_time`) | OUI | |
| Desserts | `q="dessert"` | `q` (ILIKE sur title) | PARTIEL | Ecrase la recherche textuelle utilisateur |
| Vegetarien | `diet="vegetarien"` | `diet` (filtre `:diet = ANY(tags)`) | INCERTAIN | Depend du contenu exact du tableau `tags` en DB -- si les recettes ont `"vegetarian"` (EN), ca ne match pas |
| Facile | `difficulty=2` | `max_difficulty=2` (via `searchRecipesAdvanced`) | OUI | Le frontend envoie `max_difficulty` correctement |

### Filtres avances (recipe-filters.tsx)

| Filtre | Param envoye (frontend) | Param API attendu (backend) | Match ? | Notes |
|---|---|---|---|---|
| Budget | `budget="economique"/"moyen"/"premium"` | `budget` (filtre `:budget = ANY(tags)`) | INCERTAIN | Depend si les recettes ont ces tags FR dans la DB |
| Temps max | `max_time` (15-120) | `max_time` (int) | OUI | |
| Difficulte | `max_difficulty` (1-5) | `max_difficulty` (int, `difficulty <= :max_difficulty`) | OUI | |
| Regime | `diet[]` (multi-select) | `diet` (un seul, `:diet = ANY(tags)`) | NON | Le frontend envoie PLUSIEURS valeurs `diet` via `params.append("diet", d)` mais l'API n'accepte qu'un seul `diet: str | None`. Seule la derniere valeur sera lue par FastAPI |
| Cuisine | `cuisine` (string) | `cuisine` (filtre `cuisine_type = :cuisine`) | INCERTAIN | Le frontend envoie `"francaise"` (FR) mais la DB a probablement `"French"` dans `cuisine_type` si les recettes viennent de TheMealDB |

---

## Bugs critiques (bloquants en production)

### CRIT-01 : Barre de progression onboarding toujours vide
**Fichier** : `apps/web/src/app/(onboarding)/layout.tsx:52`
**Description** : `style={{ width: "0%" }}` est hardcode -- la barre ne montre jamais la progression.
**Impact** : UX degradee -- l'utilisateur ne sait pas ou il en est.
**Effort** : 15 min

### CRIT-02 : Boutons navigation semaine non fonctionnels
**Fichier** : `apps/web/src/app/(app)/dashboard/page.tsx:91-109`
**Description** : Les fleches <- et -> n'ont pas de `onClick` -- elles ne font rien.
**Impact** : L'utilisateur ne peut pas naviguer entre les semaines.
**Effort** : 1h (necessite un state week offset + refetch plan)

### CRIT-03 : Toggle shopping-list non persiste
**Fichier** : `apps/web/src/hooks/use-shopping-list.ts:33-36`
**Description** : `useToggleItem` fait un update local only -- pas de PATCH API.
**Impact** : Les cochages sont perdus au refresh.
**Effort** : 30 min (ajouter PATCH API quand l'endpoint existera)

### CRIT-04 : Regime multi-select vs API single param
**Fichier** : `apps/web/src/lib/api/endpoints.ts:277-279` vs `apps/api/src/api/v1/recipes.py:378`
**Description** : Le frontend envoie plusieurs `diet` params mais l'API n'accepte qu'un seul `diet: str | None`.
**Impact** : Seul le dernier regime selectionne est pris en compte.
**Effort** : 1h (modifier l'API pour accepter `list[str]` ou modifier le frontend pour n'envoyer qu'un seul)

---

## Bugs importants (non bloquants mais impactants)

### IMP-01 : Classe CSS `bg-cream-50` non definie
**Fichiers** : `fridge/page.tsx`, `books/page.tsx`, `billing/page.tsx`, `billing/success/page.tsx`, `billing/cancel/page.tsx`
**Description** : `bg-cream-50` n'est pas une classe Tailwind standard. Si non definie dans `tailwind.config.ts`, le fond sera transparent.
**Impact** : Fond visuel incorrect sur 5 pages.
**Effort** : 5 min (remplacer par `bg-[#fff8f6]` ou definir `cream-50` dans tailwind.config)

### IMP-02 : Pages juridiques manquantes (404)
**Fichiers** : Liens dans `apps/web/src/app/page.tsx` et `apps/web/src/app/(auth)/layout.tsx`
**Routes manquantes** : `/about`, `/legal/terms`, `/legal/privacy`, `/contact`
**Impact** : 4 pages 404 accessibles depuis la landing et le layout auth.
**Effort** : 2h (creer les pages minimales)

### IMP-03 : Import Framer Motion direct vs dynamique
**Fichiers** : `fridge-item.tsx`, `billing/success/page.tsx`
**Description** : Import direct `from "framer-motion"` au lieu de `@/components/motion`
**Impact** : Bundle plus lourd, inconsistance avec la regle etablie.
**Effort** : 15 min

### IMP-04 : Quick filter "Desserts" ecrase la recherche
**Fichier** : `apps/web/src/app/(app)/recipes/recipes-explorer.tsx:114`
**Description** : `activeQuickFilter === "dessert" && { q: "dessert" }` ecrase `debouncedQuery`.
**Impact** : La recherche textuelle de l'utilisateur est perdue.
**Effort** : 15 min (concatener plutot qu'ecraser)

### IMP-05 : Compatibilite tags FR/EN dans les filtres
**Description** : Les filtres envoient des valeurs FR (`"vegetarien"`, `"economique"`, `"francaise"`) mais les donnees en DB sont potentiellement en EN.
**Impact** : Filtres qui ne retournent aucun resultat.
**Effort** : 2h (audit DB + mapping bidirectionnel ou normalisation des tags)

### IMP-06 : Theme settings non applique en temps reel
**Fichier** : `apps/web/src/app/(app)/settings/settings-content.tsx`
**Description** : Le choix du theme est sauvegarde en localStorage mais la classe `dark` sur `<html>` n'est pas mise a jour dynamiquement.
**Impact** : L'utilisateur doit recharger la page pour voir le changement.
**Effort** : 30 min

### IMP-07 : Shopping-list page sans metadata SEO
**Fichier** : `apps/web/src/app/(app)/shopping-list/page.tsx`
**Description** : La page est un Client Component direct sans export `metadata`.
**Impact** : Pas de title/description dans l'onglet navigateur ni pour le SEO.
**Effort** : 10 min (extraire dans page.tsx Server Component + client content)

---

## Plan de correction prioritise

### Priorite 1 -- Bugs critiques (a corriger immediatement)

| # | Tache | Fichier(s) | Effort |
|---|---|---|---|
| 1 | Barre de progression onboarding | `(onboarding)/layout.tsx` | 15 min |
| 2 | Boutons nav semaine fonctionnels | `dashboard/page.tsx` + nouveau state | 1h |
| 3 | Classe `bg-cream-50` -> `bg-[#fff8f6]` | 5 fichiers (fridge, books, billing, success, cancel) | 5 min |
| 4 | Multi-select regime -> fix API ou frontend | `endpoints.ts` + `recipes.py` | 1h |

### Priorite 2 -- Bugs importants (avant prochaine release)

| # | Tache | Fichier(s) | Effort |
|---|---|---|---|
| 5 | Pages juridiques minimales | Creer 4 pages (`/about`, `/legal/terms`, `/legal/privacy`, `/contact`) | 2h |
| 6 | Quick filter Desserts sans ecraser recherche | `recipes-explorer.tsx` | 15 min |
| 7 | Imports Framer Motion -> @/components/motion | `fridge-item.tsx`, `billing/success/page.tsx` | 15 min |
| 8 | Theme applique en temps reel | `settings-content.tsx` | 30 min |
| 9 | Shopping-list metadata SEO | `shopping-list/page.tsx` | 10 min |
| 10 | Audit tags DB FR vs EN + mapping | `recipe-filters.tsx` + DB | 2h |

### Priorite 3 -- Ameliorations (Phase 2+)

| # | Tache | Fichier(s) | Effort |
|---|---|---|---|
| 11 | Persistance toggle shopping-list (PATCH API) | `use-shopping-list.ts` | 30 min + API |
| 12 | Traduction titres recettes EN->FR | Pipeline ETL / DB | 4h+ |
| 13 | Onboarding : verifier auth avant step-1 | `(onboarding)/layout.tsx` ou middleware | 30 min |

**Effort total estime** : ~9h pour les priorites 1+2
