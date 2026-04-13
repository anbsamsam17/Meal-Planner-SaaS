// apps/web/src/lib/supabase/client.ts
// Client Supabase pour les composants navigateur (Client Components)
// Utilise @supabase/ssr pour le support SSR/cookies
import { createBrowserClient as createSupabaseBrowserClient } from "@supabase/ssr";
import type { Database } from "./database.types";

// Validation des variables d'environnement au démarrage
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl) {
  throw new Error("Variable d'environnement manquante : NEXT_PUBLIC_SUPABASE_URL");
}

if (!supabaseAnonKey) {
  throw new Error("Variable d'environnement manquante : NEXT_PUBLIC_SUPABASE_ANON_KEY");
}

// Créer un nouveau client à chaque appel — nécessaire pour éviter les fuites de session
// entre les requêtes dans Next.js SSR (singleton interdit côté serveur)
export function createBrowserClient() {
  return createSupabaseBrowserClient<Database>(supabaseUrl!, supabaseAnonKey!);
}
