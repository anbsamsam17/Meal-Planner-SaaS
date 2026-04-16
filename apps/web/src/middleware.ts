// apps/web/src/middleware.ts
// Middleware Next.js — rafraîchissement session Supabase + protection des routes
// S'exécute en Edge Runtime pour une latence minimale
import { type NextRequest, NextResponse } from "next/server";
import { updateSupabaseSession } from "@/lib/supabase/middleware";

// Routes protégées — nécessitent une authentification
const PROTECTED_ROUTES = [
  "/dashboard",
  "/planning",
  "/shopping",
  "/shopping-list",
  "/profile",
  "/settings",
  "/recipes",
  "/feed",
  // Phase 2
  "/billing",
  "/fridge",
  "/books",
  // IMP-08 fix (2026-04-14) : les pages d'onboarding nécessitent une session active.
  // Sans protection, un utilisateur non connecté accède au formulaire, le soumet,
  // et reçoit un 401 de l'API — mauvaise UX. Redirect vers /login avec param `redirect`.
  "/onboarding",
  "/generating",
  "/account",
];

// Routes publiques — accessibles sans authentification (liste de référence pour documentation)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const PUBLIC_ROUTES = ["/", "/login", "/signup"];

// Routes d'authentification — redirigent vers le dashboard si déjà connecté
const AUTH_ROUTES = ["/login", "/signup"];

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // 1. Rafraîchir la session Supabase (toujours, sur toutes les routes)
  const { supabaseResponse, user } = await updateSupabaseSession(request);

  // 2. Rediriger les routes protégées vers /login si non authentifié
  const isProtectedRoute = PROTECTED_ROUTES.some((route) => pathname.startsWith(route));

  if (isProtectedRoute && !user) {
    const loginUrl = new URL("/login", request.url);
    // Sauvegarder la destination pour rediriger après connexion
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 3. Rediriger les pages d'auth vers le dashboard si déjà connecté
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));

  if (isAuthRoute && user) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // 4. Retourner la réponse avec les cookies de session mis à jour
  return supabaseResponse;
}

// FIX Phase 1 (review 2026-04-12) : matcher explicite pour éviter getUser() sur les assets statiques
// Performance QW-2 : -80ms de latence inutile sur _next/static, favicon, robots, etc.
export const config = {
  matcher: [
    /*
     * Matcher toutes les routes sauf :
     * - _next/static  : fichiers statiques Next.js (JS, CSS bundlés)
     * - _next/image   : images optimisées Next.js
     * - favicon.ico   : icône du navigateur
     * - robots.txt    : crawlers SEO (pas besoin d'auth)
     * - sitemap.xml   : indexation SEO (pas besoin d'auth)
     * - api/webhooks  : webhooks Stripe/Supabase sans session (signature HMAC)
     * - .*\\..*       : tout fichier avec extension (.png, .svg, .woff2, .webmanifest…)
     */
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|api/webhooks|.*\\..*).*)",
  ],
};
