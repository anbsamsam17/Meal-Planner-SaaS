// apps/web/vitest.config.ts
// Configuration Vitest pour les tests unitaires du frontend
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    // Environnement jsdom pour simuler le DOM navigateur
    environment: "jsdom",
    globals: true,
    // Fichier de setup global (jest-dom matchers)
    setupFiles: ["./src/__tests__/setup.ts"],
    // Patterns de fichiers de test
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    // Exclure node_modules et .next
    exclude: ["node_modules", ".next"],
    // Rapport de couverture (istanbul)
    coverage: {
      provider: "istanbul",
      reporter: ["text", "lcov", "html"],
      // Exclure les fichiers de config, types et stories
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.stories.{ts,tsx}",
        "src/__tests__/setup.ts",
        "src/lib/supabase/database.types.ts",
      ],
    },
    // Variables d'environnement pour les tests
    env: {
      NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
      NEXT_PUBLIC_API_URL: "http://localhost:8000",
    },
  },
  resolve: {
    alias: {
      // Reproduire les path aliases du tsconfig.json
      "@": resolve(__dirname, "./src"),
    },
  },
});
