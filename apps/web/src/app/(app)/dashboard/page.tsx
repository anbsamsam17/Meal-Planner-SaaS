// apps/web/src/app/(app)/dashboard/page.tsx
// Dashboard semaine — Server Component
// Fetch du plan courant via createServerClient + API avec JWT
// Si pas de plan → EmptyState + CTA "Générer"
// Si plan → PlanWeekGrid + PlanActions
import type { Metadata } from "next";
import { Suspense } from "react";
import { createServerClient } from "@/lib/supabase/server";
import { DashboardContent } from "./dashboard-content";
import { WeekNavigator } from "@/components/dashboard/week-navigator";

export const metadata: Metadata = {
  title: "Planning de la semaine",
  description: "Votre planning de dîners pour la semaine",
};

// Calcul du label de la semaine courante
function getWeekLabel(): string {
  const today = new Date();
  const weekStart = new Date(today);
  weekStart.setDate(today.getDate() - today.getDay() + 1); // Lundi
  return weekStart.toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default async function DashboardPage() {
  const supabase = createServerClient();
  const weekLabel = getWeekLabel();

  // Récupérer le JWT Supabase pour l'appel API server-side
  const { data: { user } } = await supabase.auth.getUser();
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token ?? null;

  // BUG 5 FIX : prénom de bienvenue depuis les métadonnées Supabase
  const firstName =
    (user?.user_metadata?.full_name as string | undefined)?.split(" ")[0] ??
    (user?.user_metadata?.name as string | undefined)?.split(" ")[0] ??
    null;

  // Fetch du plan courant côté serveur
  let initialPlanData = null;
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    "https://meal-planner-saas-production.up.railway.app";

  if (token) {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/plans/me/current`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        // Revalidation ISR — données fraîches toutes les 5 minutes
        next: { revalidate: 300 },
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        initialPlanData = await response.json();
      }
      // 404 = pas de plan → null (état valide)
    } catch {
      // Backend non disponible — afficher l'état vide gracieusement
    }
  }

  return (
    <div className="min-h-full bg-[#fff8f6] px-4 py-6 md:px-6 lg:px-10">
      {/* Header de la page */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          {/* BUG 5 FIX : message de bienvenue personnalisé */}
          {firstName && (
            <p className="mb-0.5 text-sm font-medium text-primary-600">
              Bonjour {firstName} !
            </p>
          )}
          <h1 className="font-serif text-3xl font-bold text-neutral-900 dark:text-neutral-100 md:text-4xl">
            Ma semaine
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Semaine du {weekLabel}
          </p>
        </div>

        {/* Navigation semaine — Client Component avec state weekOffset */}
        <WeekNavigator />
      </div>

      {/* Contenu du dashboard — Client Component pour les mutations */}
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent initialPlanData={initialPlanData} />
      </Suspense>
    </div>
  );
}

// Skeleton de chargement — dimensions identiques au contenu (pas de CLS)
function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div className="h-40 animate-pulse bg-neutral-100" />
          <div className="p-3 space-y-2">
            <div className="h-3 w-16 animate-pulse rounded bg-neutral-100" />
            <div className="h-4 w-full animate-pulse rounded bg-neutral-100" />
            <div className="h-4 w-3/4 animate-pulse rounded bg-neutral-100" />
            <div className="h-3 w-24 animate-pulse rounded bg-neutral-100" />
          </div>
        </div>
      ))}
    </div>
  );
}
