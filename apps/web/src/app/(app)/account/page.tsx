// apps/web/src/app/(app)/account/page.tsx
// Page "Mon compte" — Server Component
// BUG 2 FIX (2026-04-12) : page créée (route /account manquante → 404)
// Affiche profil Supabase + membres du foyer + actions (logout, paramètres, billing)
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import type { HouseholdAPIResponse } from "@/lib/api/types";
// NOTE : HouseholdAPIResponse est une structure PLATE (id, name, plan, drive_provider, members[])
// Le backend retourne HouseholdRead Pydantic directement, sans clé "household" imbriquée.
// Les champs diet_tags/allergies/dislikes des membres sont dans member.preferences (MemberPreferenceRead).
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
        // Le backend retourne HouseholdRead (structure plate) avec members: MemberRead[]
        // MemberRead contient les champs diet_tags/allergies/dislikes dans preferences,
        // pas au top-level. On normalise ici pour que account-content.tsx puisse les lire.
        const raw = (await res.json()) as Record<string, unknown>;
        if (raw?.members && Array.isArray(raw.members)) {
          raw.members = raw.members.map((m: Record<string, unknown>) => {
            const prefs = (m.preferences as Record<string, unknown>) ?? {};
            return {
              id: m.id,
              display_name: m.display_name,
              is_child: m.is_child ?? false,
              birth_date: m.birth_date ?? null,
              diet_tags: Array.isArray(prefs.diet_tags) ? prefs.diet_tags : [],
              allergies: Array.isArray(prefs.allergies) ? prefs.allergies : [],
              dislikes: Array.isArray(prefs.dislikes) ? prefs.dislikes : [],
            };
          });
        }
        householdData = raw as unknown as HouseholdAPIResponse;
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
