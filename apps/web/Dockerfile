# Dockerfile — apps/web
# Multi-stage build : builder → runner
# Next.js standalone output pour minimiser la taille de l'image
# Non-root user pour la sécurité

# ============================================================
# Stage 1 : deps — Installation des dépendances
# ============================================================
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copier les fichiers de dépendances du monorepo
COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/

# Installer pnpm
RUN npm install -g pnpm@9

# Installer uniquement les dépendances de l'app web
RUN pnpm install --frozen-lockfile --filter @mealplanner/web

# ============================================================
# Stage 2 : builder — Build Next.js
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les dépendances installées
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules

# Copier les sources
COPY apps/web ./apps/web
COPY packages ./packages

WORKDIR /app/apps/web

# Variables d'environnement au build time
# Les variables NEXT_PUBLIC_* sont injectées dans le bundle JS
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_POSTHOG_KEY

ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_POSTHOG_KEY=$NEXT_PUBLIC_POSTHOG_KEY

# Build en mode standalone — réduit la taille de l'image finale
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@9 && pnpm build

# ============================================================
# Stage 3 : runner — Image de production minimale
# ============================================================
FROM node:20-alpine AS runner

WORKDIR /app

# Sécurité : utilisateur non-root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copier uniquement les fichiers nécessaires au runtime
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static

# Variables d'environnement runtime
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

USER nextjs

EXPOSE 3000

# Healthcheck — vérifie que l'app répond sur /api/health
# L'endpoint /api/health sera créé en Phase 1
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
