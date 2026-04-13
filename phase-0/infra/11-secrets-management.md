# Stratégie de gestion des secrets — Doppler

> Ce document définit la stratégie de gestion des secrets pour MealPlanner SaaS.
> La règle ROADMAP est non-négociable : aucun secret ne doit jamais être commité.

---

## 1. Décision : Doppler retenu (vs alternatives)

### Comparaison

| Critère | Doppler | Vercel Env Vars | Railway Secrets | HashiCorp Vault |
|---------|---------|-----------------|-----------------|-----------------|
| Centralisation (1 source) | Oui | Non (Vercel seulement) | Non (Railway seulement) | Oui |
| Sync automatique multi-plateforme | Oui | Non | Non | Oui (complexe) |
| CLI dev local | Oui (`doppler run`) | Non | Non | Oui (complexe) |
| Rotation automatique | Plan payant | Non | Non | Oui (complexe) |
| Audit logs | Oui | Non | Limité | Oui |
| Courbe d'apprentissage | Faible | Très faible | Très faible | Élevée |
| Coût Phase 0 | 0 € | 0 € | 0 € | 0 € (self-hosted) |
| Intégration GitHub Actions | Oui | Non | Non | Oui |

**Raison du choix Doppler :** Un seul endroit pour gérer les secrets de tous les services
(Vercel + Railway + GitHub Actions + dev local). Évite la dérive de configuration où
les secrets dev/staging/prod divergent sans qu'on s'en rende compte.

**Fallback si Doppler n'est pas retenu :** Section 5 ci-dessous.

---

## 2. Structure Doppler

### Workplace

```
Workplace : mealplanner-saas
└── Project : mealplanner
    ├── Config : dev       (environnement développement local)
    ├── Config : staging   (environnement staging Railway + Vercel preview)
    └── Config : prod      (environnement production)
```

### Hiérarchie des valeurs

```
prod (valeurs de production — les vraies clés sk_live_, clés ANON prod)
 └── staging (hérite de prod, surcharge avec sk_test_, DB staging)
      └── dev (hérite de staging, surcharge avec localhost, clés test)
```

Cette hiérarchie évite de redéfinir chaque variable dans chaque environnement.
Seules les valeurs qui changent entre envs sont surchargées.

---

## 3. Intégration CI — GitHub Actions

### Configuration

1. Créer un Service Token Doppler pour chaque config (dev, staging, prod)
2. Stocker les tokens dans GitHub Secrets :
   - `DOPPLER_TOKEN_STAGING` → utilisé dans les workflows de staging
   - `DOPPLER_TOKEN_PROD` → utilisé dans les workflows de production

### Usage dans le workflow CI

```yaml
# Extrait pour le job test-api dans ci.yml
- name: Load secrets from Doppler
  uses: dopplerhq/secrets-fetch-action@v1.1.3
  with:
    doppler-token: ${{ secrets.DOPPLER_TOKEN_STAGING }}
    inject-env-vars: true
  # Injecte automatiquement toutes les variables Doppler staging dans l'env du job
```

### Alternative sans action Doppler (plus portable)

```yaml
- name: Install Doppler CLI
  run: curl -Ls https://cli.doppler.com/install.sh | sh

- name: Run tests with Doppler secrets
  run: doppler run --token=${{ secrets.DOPPLER_TOKEN_STAGING }} -- pytest tests/
```

---

## 4. Intégration services déployés

### Doppler → Railway

1. Doppler Dashboard > Integrations > Add Integration > Railway
2. Sélectionner le projet Railway et les services (api, worker, worker-beat)
3. Mapper : `prod` Doppler → services Railway prod
4. Mapper : `staging` Doppler → services Railway staging
5. Activer la synchronisation automatique

Chaque mise à jour d'un secret dans Doppler déclenche un redéploiement Railway.

### Doppler → Vercel

1. Doppler Dashboard > Integrations > Add Integration > Vercel
2. Sélectionner le projet Vercel
3. Mapper : `prod` → `Production` Vercel | `staging` → `Preview` Vercel

**Attention :** Les variables `NEXT_PUBLIC_*` sont injectées par Doppler mais
doivent être marquées comme "sensitive: false" dans Doppler pour que Vercel
les expose correctement au navigateur.

---

## 5. Usage en développement local

```bash
# Installer Doppler CLI
brew install dopplerhq/cli/doppler  # macOS
# ou : curl -Ls https://cli.doppler.com/install.sh | sh  # Linux

# Authentification
doppler login

# Configurer le projet dans le repo (crée .doppler.yaml)
doppler setup --project mealplanner --config dev

# Lancer FastAPI avec les secrets injectés
doppler run -- uvicorn src.main:app --reload

# Lancer les tests avec les secrets
doppler run -- pytest tests/

# Afficher toutes les variables de l'env dev
doppler secrets
```

**Fichier `.doppler.yaml` à committer dans le repo (pas de secret ici) :**
```yaml
setup:
  project: mealplanner
  config: dev
```

---

## 6. Politique de rotation des secrets

| Secret | Fréquence de rotation | Méthode |
|--------|----------------------|---------|
| `ANTHROPIC_API_KEY` | Tous les 90 jours | Rotation manuelle dans Anthropic console |
| `STRIPE_SECRET_KEY` | Jamais (sauf compromission) | Révocation + nouvelle clé Stripe |
| `SUPABASE_SERVICE_ROLE_KEY` | Tous les 180 jours | Supabase Dashboard > Settings > Rotate |
| `R2_SECRET` | Tous les 90 jours | Cloudflare Dashboard > Rotate token |
| `DOPPLER_SERVICE_TOKENS` | Tous les 90 jours | Doppler Dashboard > Rotate |
| `SENTRY_AUTH_TOKEN` | Tous les 90 jours | Sentry > Settings > Rotate |

**Processus de rotation :**
1. Créer la nouvelle clé dans le service concerné
2. Mettre à jour dans Doppler (la synchronisation propage automatiquement)
3. Vérifier que les services ont redémarré avec la nouvelle clé
4. Révoquer l'ancienne clé dans le service concerné

---

## 7. Fallback — Env natifs Vercel + Railway

Si Doppler n'est pas adopté, voici le plan de secours :

### Vercel (frontend)
- Gérer les variables dans Vercel Dashboard > Settings > Environment Variables
- Inconvénient : pas de sync avec Railway, pas de CLI dev

### Railway (backend)
- Gérer les variables dans Railway Dashboard > Service > Variables
- Utiliser les "Shared Variables" Railway pour partager entre services du même projet

### Dev local
- Créer `.env.local` à la racine (gitignored)
- Copier depuis `.env.example` et remplir manuellement

### GitHub Actions
- Stocker chaque secret dans GitHub Settings > Secrets > Actions
- Injecter via `${{ secrets.NOM_DU_SECRET }}`

**Inconvénient majeur du fallback :** Risque élevé de dérive entre environnements.
Une variable manquante en staging causera des erreurs silencieuses en production.
Doppler est fortement recommandé dès le début.

---

## 8. Règles de sécurité non-négociables

1. Aucun secret dans le code source (gitleaks en CI scanne l'historique complet)
2. Aucun secret dans les logs applicatifs (loguru doit masquer les patterns de clés API)
3. Les clés `SUPABASE_SERVICE_ROLE_KEY` et `STRIPE_SECRET_KEY` ne transitent jamais
   dans le frontend — backend uniquement
4. Revue trimestrielle des accès Doppler : révoquer les membres qui ont quitté l'équipe
5. Activer les alertes Doppler pour toute modification d'un secret de production
