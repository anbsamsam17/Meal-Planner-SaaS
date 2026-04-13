// apps/web/src/i18n/config.ts
// FIX Phase 1 mature (review 2026-04-12) — BUG #5C : next-intl retiré (Phase 1 = FR only)
// Phase 4 (expansion BE/CH) : réinstaller next-intl et restaurer cette config avec middleware i18n
// Voir ROADMAP.md — Phase 4 "internationalisation"
//
// Remplacé par : src/i18n/t.ts (helper JSON léger, 0 dépendance externe)
// Économie bundle : ~28 KB gzip

export const locales = ["fr"] as const;
export type Locale = (typeof locales)[number];

// Locale par défaut — FR first (marché cible : familles françaises B2C)
export const defaultLocale: Locale = "fr";

// Configuration i18n minimaliste Phase 1 — pas de middleware next-intl
export const i18nConfig = {
  locales,
  defaultLocale,
} as const;

// Messages par locale — chargement statique (pas de middleware next-intl en Phase 1)
export async function getMessages(locale: Locale): Promise<Record<string, unknown>> {
  // Utilisation d'une variable intermédiaire pour éviter la collision avec le module global
  const jsonModule = await import(`./messages/${locale}.json`);
  return jsonModule.default as Record<string, unknown>;
}
