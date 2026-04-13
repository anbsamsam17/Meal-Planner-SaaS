// apps/web/src/app/(auth)/callback/route.ts
// Route handler pour le callback OAuth/magic link Supabase
// Échange le code PKCE pour une session, puis redirige :
// - /onboarding si pas de household (nouveau user)
// - /dashboard si household existant (user récurrent)
import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const redirectTo = searchParams.get("redirect");

  // Si pas de code → erreur de configuration OAuth ou lien expiré
  if (!code) {
    return NextResponse.redirect(new URL("/login?error=missing_code", origin));
  }

  const supabase = createServerClient();

  // Échange du code PKCE pour une session Supabase
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    // Lien expiré (> 24h) ou déjà utilisé
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(error.message)}`, origin),
    );
  }

  // Si une URL de redirection explicite est fournie (ex: /onboarding/step-1 depuis signup)
  if (redirectTo && redirectTo.startsWith("/")) {
    return NextResponse.redirect(new URL(redirectTo, origin));
  }

  // Vérifier si le household existe pour décider de la destination
  try {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

    if (apiBaseUrl) {
      // Récupérer le token Supabase pour l'appel API
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (token) {
        const householdResponse = await fetch(`${apiBaseUrl}/api/v1/households/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          // Pas de cache — on veut la donnée fraîche
          cache: "no-store",
        });

        // 404 = pas de household → onboarding
        if (householdResponse.status === 404) {
          return NextResponse.redirect(new URL("/onboarding/step-1", origin));
        }

        // Household trouvé → dashboard directement
        if (householdResponse.ok) {
          return NextResponse.redirect(new URL("/dashboard", origin));
        }
      }
    }
  } catch {
    // En cas d'erreur réseau (backend non disponible), aller au dashboard
    // Le dashboard gère l'absence de plan gracieusement
  }

  // Fallback → onboarding (sécuritaire pour les nouveaux utilisateurs)
  return NextResponse.redirect(new URL("/onboarding/step-1", origin));
}
