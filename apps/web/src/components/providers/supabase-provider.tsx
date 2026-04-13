// apps/web/src/components/providers/supabase-provider.tsx
// Supabase browser client — contexte React pour les composants clients
// Expose le client Supabase et la session via le hook useSupabase()
"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createBrowserClient } from "@/lib/supabase/client";

interface SupabaseContextValue {
  supabase: ReturnType<typeof createBrowserClient>;
  user: User | null;
  isLoading: boolean;
}

const SupabaseContext = createContext<SupabaseContextValue | null>(null);

interface SupabaseProviderProps {
  children: React.ReactNode;
}

export function SupabaseProvider({ children }: SupabaseProviderProps) {
  const [supabase] = useState(() => createBrowserClient());
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Récupérer la session initiale
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      setIsLoading(false);
    });

    // Écouter les changements d'état d'authentification
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    // Nettoyer l'abonnement au démontage
    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  return (
    <SupabaseContext.Provider value={{ supabase, user, isLoading }}>
      {children}
    </SupabaseContext.Provider>
  );
}

// Hook — usage : const { supabase, user } = useSupabase()
export function useSupabase(): SupabaseContextValue {
  const context = useContext(SupabaseContext);
  if (!context) {
    throw new Error("useSupabase doit être utilisé dans un SupabaseProvider");
  }
  return context;
}
