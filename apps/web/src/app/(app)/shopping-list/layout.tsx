// apps/web/src/app/(app)/shopping-list/layout.tsx
// Layout minimal pour porter les métadonnées SEO de la page liste de courses.
// La page elle-même est un Client Component (useSearchParams) et ne peut pas exporter metadata.
// Cette approche layout est la modification minimale sans refactoring de page.tsx.
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ma liste de courses — Presto",
  description:
    "Votre liste de courses hebdomadaire générée automatiquement par Presto, organisée par rayon.",
};

export default function ShoppingListLayout({ children }: { children: React.ReactNode }) {
  return children;
}
