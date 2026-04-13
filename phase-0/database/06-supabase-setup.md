# 06 — Checklist Setup Supabase

## Création du projet

- [ ] Aller sur https://supabase.com/dashboard et créer un nouveau projet
- [ ] **Nom du projet** : `mealplanner-saas-prod` (ou `-dev` pour l'environnement de dev)
- [ ] **Région** : `eu-central-1` (Frankfurt) — obligatoire pour conformité RGPD données FR
  - Raison : données de familles françaises, stockage EU requis
  - Interdit : us-east-1 ou ap-southeast-1 pour une app B2C française
- [ ] **Mot de passe DB** : générer un mot de passe fort (32+ caractères, stocker dans 1Password)
  - Format : utiliser `openssl rand -base64 32` ou le générateur Supabase
- [ ] **Plan Supabase** : Free pour le dev, Pro ($25/mois) avant le lancement beta

---

## Extensions à activer (Dashboard > Database > Extensions)

Activer dans cet ordre :

- [ ] `uuid-ossp` — UUIDs (déjà actif par défaut sur Supabase)
- [ ] `pgcrypto` — fonctions cryptographiques
- [ ] `vector` — pgvector pour les embeddings (rechercher "vector" dans la liste)
- [ ] `pg_trgm` — recherche full-text FR par trigrammes

**Important** : certaines extensions nécessitent un redémarrage de la connexion Supabase Studio après activation.

Vérification via SQL Editor :
```sql
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector', 'pg_trgm');
```

---

## Exécution du schéma initial

Dans Supabase Dashboard > SQL Editor, exécuter les fichiers dans cet ordre :

1. `00-setup-extensions.sql` — (si pas déjà fait via Dashboard)
2. `01-schema-core.sql`
3. `02-indexes.sql`
4. `04-triggers-functions.sql` — **avant** les policies (dépendance `get_current_household_id`)
5. `03-rls-policies.sql`
6. `07-seed-data.sql` — uniquement en environnement dev/staging

Ou via Alembic (recommandé pour la prod) :
```bash
DATABASE_URL="postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres" \
  alembic upgrade head
```

---

## Configuration Authentication

### Magic Link (recommandé pour l'onboarding)

Dashboard > Authentication > Providers > Email :
- [ ] Activer "Enable Email provider"
- [ ] Activer "Enable magic links"
- [ ] Désactiver "Enable email confirmations" en dev (activer en prod)
- [ ] **From name** : `MealPlanner`
- [ ] **From email** : `noreply@mealplanner.fr` (configurer SMTP custom en prod)

### Google OAuth

Dashboard > Authentication > Providers > Google :
- [ ] Créer un projet Google Cloud Console
- [ ] Activer "Google Identity" API
- [ ] Créer des OAuth credentials (Web application)
- [ ] **Authorized redirect URIs** : `https://[PROJECT_REF].supabase.co/auth/v1/callback`
- [ ] Renseigner Client ID et Client Secret dans Supabase
- [ ] En prod : ajouter l'URL de production comme redirect autorisé

### Configuration JWT

Dashboard > Authentication > JWT Settings :
- [ ] **JWT expiry** : 3600 (1 heure) — renouvellement via refresh token
- [ ] **Refresh token rotation** : activé
- [ ] **Reuse interval** : 10 secondes (évite les refresh loops)

### URLs autorisées

Dashboard > Authentication > URL Configuration :
- [ ] **Site URL** : `http://localhost:3000` (dev) / `https://app.mealplanner.fr` (prod)
- [ ] **Redirect URLs** :
  - `http://localhost:3000/**`
  - `https://app.mealplanner.fr/**`

---

## Supabase Realtime

Activer le Realtime sur les tables qui nécessitent des mises à jour en temps réel.

Dashboard > Database > Replication > Supabase Realtime :

- [ ] `weekly_plans` — synchronisation du statut du plan entre membres
- [ ] `shopping_lists` — liste de courses partagée en temps réel
- [ ] `recipe_feedbacks` — affichage immédiat des feedbacks des autres membres
- [ ] `planned_meals` — modification collaborative du menu de la semaine

**Configuration Realtime côté client Next.js** :
```typescript
// Exemple : écoute des changements sur shopping_lists
const channel = supabase
  .channel('shopping-list-changes')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'shopping_lists',
      filter: `plan_id=eq.${planId}`,
    },
    (payload) => {
      // Mettre à jour le state React
      console.log('Shopping list updated:', payload);
    }
  )
  .subscribe();
```

**Important** : Supabase Realtime applique les RLS policies pour filtrer les événements.
Un utilisateur ne recevra que les événements des tables auxquelles sa policy lui donne accès.

---

## Storage Buckets (optionnel Phase 0, requis Phase 2)

Dashboard > Storage > Create bucket :

- [ ] **Bucket `recipe-photos`** :
  - Public : oui (URLs publiques pour les photos de recettes)
  - File size limit : 5 MB
  - Allowed MIME types : `image/jpeg, image/webp`

- [ ] **Bucket `weekly-books`** (Phase 2) :
  - Public : non (accès authentifié uniquement via signed URLs)
  - File size limit : 10 MB
  - Allowed MIME types : `application/pdf`
  - Note : les PDFs sont stockés sur Cloudflare R2 (plus économique), pas Supabase Storage

---

## Row Level Security — Vérification post-déploiement

Tester les policies depuis le SQL Editor avec différents rôles :

```sql
-- Simuler un utilisateur authentifié
SET LOCAL role TO authenticated;
SET LOCAL "request.jwt.claims" TO '{"sub": "test-user-uuid"}';

-- Ce SELECT doit retourner 0 ligne (l'utilisateur n'appartient à aucun foyer)
SELECT * FROM households;

-- Simuler le service_role (bypass RLS)
RESET role;
SELECT * FROM households; -- Doit retourner toutes les lignes
```

---

## Variables d'environnement à récupérer

Dashboard > Settings > API :

```bash
# URL du projet
SUPABASE_URL=https://[PROJECT_REF].supabase.co

# Clé publique (safe côté client Next.js)
SUPABASE_ANON_KEY=eyJ...

# Clé service (backend FastAPI uniquement — NE JAMAIS exposer côté client)
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Connexion directe PostgreSQL (Alembic migrations)
DATABASE_URL=postgresql://postgres:[PWD]@db.[PROJECT_REF].supabase.co:5432/postgres

# Connexion pooler (FastAPI en production)
DATABASE_POOL_URL=postgresql://postgres.[PROJECT_REF]:[PWD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

---

## Monitoring recommandé

- [ ] Activer les **Slow Query Logs** (Dashboard > Database > Performance)
  - Threshold : 500ms en dev, 200ms en prod
- [ ] Activer les **alerts** sur le Dashboard Supabase (Database size, Connections)
- [ ] Connecter Sentry au backend FastAPI pour capturer les erreurs PostgreSQL
- [ ] Configurer PostHog pour tracker les événements d'onboarding et de rétention
