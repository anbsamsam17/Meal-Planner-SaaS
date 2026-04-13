// apps/web/src/app/(app)/fridge/page.tsx
// Page "Mon frigo" — gestion des ingrédients disponibles
// Phase 2 — liste, ajout, suggestions recettes
import type { Metadata } from "next";
import { FridgeContent } from "./fridge-content";

export const metadata: Metadata = {
  title: "Mon frigo — Presto",
  description: "Gérez les ingrédients disponibles dans votre frigo et recevez des suggestions.",
};

export default function FridgePage() {
  return (
    <div className="min-h-screen bg-[#fff8f6]">
      <FridgeContent />
    </div>
  );
}
