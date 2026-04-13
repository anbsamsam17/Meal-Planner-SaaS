// apps/web/src/app/(app)/books/page.tsx
// Page "Mes livres de recettes" — PDFs hebdomadaires
// Phase 2 — feature gated plan Famille, liste des livres, génération
import type { Metadata } from "next";
import { BooksContent } from "./books-content";

export const metadata: Metadata = {
  title: "Mes livres — Presto",
  description: "Téléchargez vos livres de recettes hebdomadaires en PDF.",
};

export default function BooksPage() {
  return (
    <div className="min-h-screen bg-cream-50">
      <BooksContent />
    </div>
  );
}
