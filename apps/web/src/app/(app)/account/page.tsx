// apps/web/src/app/(app)/account/page.tsx
// Page "Mon compte" — Server Component
// BUG 2 FIX (2026-04-12) : page créée (route /account manquante → 404)
// Affiche profil Supabase + membres du foyer + actions (logout, paramètres, billing)
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import type { HouseholdAPIResponse, HouseholdMemberAPI } from "@/lib/api/types";
import { AccountContent } from "./account-content";

export const metadata: Metadata = {
  title: "Mon compte — Presto",
  description: "Gérez votre compte, votre foyer et vos préférences.",
};

export default async function AccountPage() {
  const supabase = createServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token ?? null;

  // Fetch du foyer côté serveur (graceful — pas de crash si API down)
  let householdData: HouseholdAPIResponse | null = null;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://meal-planner-saas-production.up.railway.app";

  if (token && apiBaseUrl) {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/households/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        signal: AbortSignal.timeout(5000),
        next: { revalidate: 0 }, // Données utilisateur : jamais en cache
      });

      if (res.ok) {
        const raw = (await res.json()) as HouseholdAPIResponse;
        // Defensif : s'assurer que les membres ont des tableaux valides
        if (raw?.members && Array.isArray(raw.members)) {
          raw.members = raw.members.map((m: HouseholdMemberAPI) => ({
            ...m,
            diet_tags: Array.isArray(m.diet_tags) ? m.diet_tags : [],
            allergies: Array.isArray(m.allergies) ? m.allergies : [],
            dislikes: Array.isArray(m.dislikes) ? m.dislikes : [],
          }));
        }
        householdData = raw;
      } else {
        // Erreur HTTP non-2xx — logger pour le debugging serveur
        console.error(
          `[AccountPage] GET /households/me — HTTP ${res.status}`,
          { userId: user.id },
        );
      }
    } catch (err) {
      // Backend non disponible ou timeout — logger pour le debugging serveur
      console.error("[AccountPage] GET /households/me — fetch error", err);
    }
  }

  return (
    <div className="min-h-full px-4 py-6 md:px-6 lg:px-10">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-3xl font-bold text-neutral-900 dark:text-neutral-100">
            Mon compte
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Gérez votre profil et votre foyer
          </p>
        </div>

        <AccountContent
          user={{
            id: user.id,
            email: user.email ?? "",
            created_at: user.created_at,
            user_metadata: user.user_metadata as Record<string, string> | undefined,
          }}
          householdData={householdData}
        />
      </div>
    </div>
  );
}
