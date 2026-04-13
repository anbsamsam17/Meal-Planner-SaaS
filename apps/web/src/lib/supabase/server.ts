// apps/web/src/lib/supabase/server.ts
// Client Supabase pour les Server Components et Server Actions
// Lit/écrit les cookies de session via next/headers (Next.js 14)
//
// FIX Phase 1 (review 2026-04-12) : décision version Next.js — FIX #3
// DÉCISION : Rester sur Next.js 14.2.x pour la Phase 1 (stabilité + écosystème mûr)
// Migration vers Next.js 15 prévue en Phase 2
// Voir : apps/web/README.md section "Décisions techniques"
//
// ATTENTION BREAKING CHANGE Next.js 15 :
// `cookies()` et `headers()` sont devenus asynchrones dans Next.js 15.
// Si migration vers Next 15 : remplacer `const cookieStore = cookies()` par
// `const cookieStore = await cookies()` ICI et dans tout Server Component qui utilise cookies().
// Lancer `npx @next/codemod@canary upgrade` pour automatiser la migration.
import { createServerClient as createSupabaseServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import type { Database } from "./database.types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Variables Supabase manquantes : NEXT_PUBLIC_SUPABASE_URL ou NEXT_PUBLIC_SUPABASE_ANON_KEY",
  );
}

// À utiliser dans les Server Components et Server Actions
// Crée un client Supabase avec accès aux cookies Next.js
export function createServerClient() {
  const cookieStore = cookies();

  return createSupabaseServerClient<Database>(supabaseUrl!, supabaseAnonKey!, {
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
          // setAll peut échouer dans les Server Components en lecture seule
          // Le middleware gère le rafraîchissement de session dans ce cas
        }
      },
    },
  });
}
