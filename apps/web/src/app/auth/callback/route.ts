// apps/web/src/app/auth/callback/route.ts
// Route handler PKCE — échange le code d'autorisation Supabase contre une session
// Appelé après clic sur le magic link envoyé par Supabase Auth
//
// Flow :
//   1. L'utilisateur clique sur le lien dans l'email
//   2. Supabase redirige vers /auth/callback?code=<pkce_code>&next=<target>
//   3. Ce handler échange le code contre un access_token + refresh_token
//   4. Il redirige vers :
//      - `next` si fourni et chemin relatif valide
//      - /dashboard si l'utilisateur a déjà un household
//      - /onboarding sinon
//
// Sécurité :
//   - Le paramètre `next` est validé pour bloquer les open redirects
//   - On utilise createServerClient pour accéder aux cookies de session
import { NextResponse, type NextRequest } from "next/server";
import { createServerClient as createSupabaseServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import type { Database } from "@/lib/supabase/database.types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// Valide que le paramètre `next` est un chemin relatif interne sûr
// Bloque tout redirect absolu (https://evil.com) ou protocole malicieux
function getSafeNextPath(next: string | null, defaultPath: string): string {
  if (!next) return defaultPath;

  // Bloquer absolument tout ce qui n'est pas un chemin relatif simple
  if (
    next.startsWith("http") ||
    next.startsWith("//") ||
    next.includes("://") ||
    next.includes("\n") ||
    next.includes("\r") ||
    !next.startsWith("/")
  ) {
    return defaultPath;
  }

  // Chemin relatif valide — autoriser
  return next;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const { searchParams, origin } = request.nextUrl;

  const code = searchParams.get("code");
  const nextParam = searchParams.get("next");

  // Si pas de code PKCE, la requête est invalide
  if (!code) {
    return NextResponse.redirect(new URL("/login?error=missing_code", origin));
  }

  const cookieStore = cookies();

  const supabase = createSupabaseServerClient<Database>(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: Array<{ name: string; value: string; options?: Record<string, unknown> }>) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options as never);
          });
        } catch {
          // Ignoré côté serveur Read-Only — le middleware gère le refresh
        }
      },
    },
  });

  // Échanger le code PKCE contre une session Supabase
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("[auth/callback] Échec échange PKCE:", error.message);
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(error.message)}`, origin),
    );
  }

  // Récupérer l'utilisateur pour vérifier si l'onboarding est nécessaire
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.redirect(new URL("/login?error=no_user", origin));
  }

  // Chemin de redirection après login
  // Priorité : paramètre `next` > vérification household > /dashboard
  const defaultPath = "/dashboard";
  const safePath = getSafeNextPath(nextParam, defaultPath);

  // Si un chemin `next` explicite a été fourni et validé, l'utiliser directement
  // (ex: /onboarding depuis signup, ou une page protégée interceptée par le middleware)
  if (nextParam && safePath !== defaultPath) {
    return NextResponse.redirect(new URL(safePath, origin));
  }

  // Sinon : vérifier si l'utilisateur a déjà un household via l'API FastAPI
  // Si oui → dashboard, sinon → onboarding
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

  if (apiBaseUrl) {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      const token = session?.access_token;

      if (token) {
        const householdRes = await fetch(`${apiBaseUrl}/api/v1/households/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          // Pas de cache — on veut l'état réel
          cache: "no-store",
        });

        // Household trouvé → dashboard
        if (householdRes.ok) {
          return NextResponse.redirect(new URL("/dashboard", origin));
        }

        // 404 = pas de household → onboarding
        if (householdRes.status === 404) {
          return NextResponse.redirect(new URL("/onboarding", origin));
        }
      }
    } catch {
      // API non disponible — fallback dashboard (l'app gère le cas "pas de plan")
    }
  }

  return NextResponse.redirect(new URL("/dashboard", origin));
}
