// apps/web/src/components/providers/root-providers.tsx
// Composition de tous les providers dans le bon ordre
// Ordre important : ThemeProvider en premier (affecte le DOM), QueryProvider en dernier
"use client";

import { ThemeProvider } from "./theme-provider";
import { QueryProvider } from "./query-provider";
import { SupabaseProvider } from "./supabase-provider";
import { Toaster } from "sonner";

interface RootProvidersProps {
  children: React.ReactNode;
}

export function RootProviders({ children }: RootProvidersProps) {
  return (
    <ThemeProvider>
      <SupabaseProvider>
        <QueryProvider>
          {children}
          {/* Toast global — sonner (positionné en bas, style warm) */}
          <Toaster
            position="bottom-center"
            richColors
            closeButton
            toastOptions={{
              style: {
                // Correspond à la palette neutral du design system
                background: "hsl(38, 30%, 98%)",
                border: "1px solid hsl(38, 20%, 89%)",
                color: "hsl(38, 16%, 10%)",
              },
              className: "font-sans text-sm",
            }}
          />
        </QueryProvider>
      </SupabaseProvider>
    </ThemeProvider>
  );
}
