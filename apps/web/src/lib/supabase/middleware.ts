// apps/web/src/lib/supabase/middleware.ts
// Helper de rafraîchissement de session Supabase pour le middleware Next.js
// Appelé par src/middleware.ts à chaque requête
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import type { Database } from "./database.types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// Rafraîchit la session Supabase et retourne la réponse mise à jour avec les cookies
// Le rafraîchissement doit se faire dans le middleware pour que les Server Components
// accèdent à une session à jour
export async function updateSupabaseSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient<Database>(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: Array<{ name: string; value: string; options?: Record<string, unknown> }>) {
        // Mettre à jour les cookies dans la requête ET dans la réponse
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          supabaseResponse.cookies.set(name, value, options as never);
        });
      },
    },
  });

  // Rafraîchir la session — NE PAS utiliser getSession() ici (non sécurisé côté serveur)
  // getUser() valide le token JWT auprès de Supabase Auth
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return { supabaseResponse, user };
}
