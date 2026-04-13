// apps/web/src/components/providers/theme-provider.tsx
// next-themes — dark mode class-based (voir tailwind.config.ts darkMode: "class")
// Synchronisé avec le script anti-FOUC du layout.tsx
"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class" // Ajoute/retire la classe "dark" sur <html>
      defaultTheme="system" // Respecte la préférence système par défaut
      enableSystem={true} // Active la détection prefers-color-scheme
      storageKey="mealplanner-theme" // Clé localStorage (synchronisée avec le script anti-FOUC)
      disableTransitionOnChange // Évite le flash de transition au changement de thème
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
