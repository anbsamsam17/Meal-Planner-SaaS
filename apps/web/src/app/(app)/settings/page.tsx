// apps/web/src/app/(app)/settings/page.tsx
// Page "Paramètres" — Server Component (metadata) + Client Component (formulaire)
// BUG 3 FIX (2026-04-12) : page créée (route /settings manquante → 404)
import type { Metadata } from "next";
import { SettingsContent } from "./settings-content";

export const metadata: Metadata = {
  title: "Paramètres — Presto",
  description: "Configurez vos préférences alimentaires, temps de cuisine et thème.",
};

export default function SettingsPage() {
  return (
    <div className="min-h-full px-4 py-6 md:px-6 lg:px-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8">
          <h1 className="font-serif text-3xl font-bold text-neutral-900 dark:text-neutral-100">
            Paramètres
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Personnalisez votre expérience Presto
          </p>
        </div>

        <SettingsContent />
      </div>
    </div>
  );
}
