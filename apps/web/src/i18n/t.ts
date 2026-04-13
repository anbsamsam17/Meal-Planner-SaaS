// apps/web/src/i18n/t.ts
// FIX Phase 1 mature (review 2026-04-12) — BUG #5C : remplacement next-intl par helper léger
// Raison : Phase 1 = FR uniquement. next-intl ajoutait ~28 KB gzip pour rien.
// Remettre next-intl en Phase 4 (expansion BE/CH) selon ROADMAP.
//
// Usage :
//   import { t } from "@/i18n/t"
//   t("common.loading")  // → "Chargement..."
//   t("auth.login.title") // → valeur dans fr.json
//
// Si une clé n'existe pas, la clé elle-même est retournée (comportement fail-safe).

import messages from "./messages/fr.json";

// Type récursif pour les clés imbriquées JSON
type NestedMessages = { [key: string]: string | NestedMessages };

// Résoud une clé "a.b.c" dans l'objet messages
function resolvePath(obj: NestedMessages, path: string): string {
  return path.split(".").reduce<string | NestedMessages>((current, key) => {
    if (typeof current === "object" && current !== null && key in current) {
      return current[key] as string | NestedMessages;
    }
    return path; // clé introuvable → retourne la clé elle-même (fail-safe)
  }, obj) as string;
}

// Fonction de traduction — FR uniquement en Phase 1
export function t(key: string): string {
  const result = resolvePath(messages as NestedMessages, key);
  // Si la résolution échoue (retourne un objet plutôt qu'une string), retourner la clé
  return typeof result === "string" ? result : key;
}
