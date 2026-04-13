// apps/web/src/app/(auth)/logout/route.ts
// Route POST — déconnecte l'utilisateur Supabase et redirige vers /
// Méthode POST pour prévenir la déconnexion accidentelle via GET (prefetch Link)
import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@/lib/supabase/server";

export async function POST(_request: NextRequest) {
  const supabase = createServerClient();

  // Déconnexion — invalide la session côté Supabase et efface les cookies
  await supabase.auth.signOut();

  // Rediriger vers la landing page après déconnexion
  return NextResponse.redirect(new URL("/", _request.url), { status: 303 });
}

// Méthode GET non supportée — sécurité contre CSRF via prefetch
export async function GET() {
  return NextResponse.json({ error: "Méthode non autorisée" }, { status: 405 });
}
