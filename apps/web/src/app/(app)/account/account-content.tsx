// apps/web/src/app/(app)/account/account-content.tsx
// Client Component — interactions : déconnexion
// BUG 2 FIX (2026-04-12)
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Loader2, LogOut, Settings, CreditCard, User, Users, ChevronRight } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase/client";

interface AccountUser {
  id: string;
  email: string;
  created_at: string;
  user_metadata?: Record<string, string>;
}

interface HouseholdMemberAPI {
  id: string;
  display_name: string;
  is_child: boolean;
  birth_date: string | null;
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
}

interface HouseholdAPI {
  id: string;
  owner_id: string;
  name: string;
  drive_provider: string | null;
}

interface HouseholdData {
  household: HouseholdAPI;
  members: HouseholdMemberAPI[];
}

interface AccountContentProps {
  user: AccountUser;
  householdData: HouseholdData | null;
}

export function AccountContent({ user, householdData }: AccountContentProps) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const displayName =
    user.user_metadata?.full_name ??
    user.user_metadata?.name ??
    user.email.split("@")[0] ??
    "Utilisateur";

  const joinedDate = new Date(user.created_at).toLocaleDateString("fr-FR", {
    month: "long",
    year: "numeric",
  });

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      const supabase = createBrowserClient();
      const { error } = await supabase.auth.signOut();
      if (error) {
        toast.error("Erreur lors de la déconnexion", { description: error.message });
        return;
      }
      toast.success("À bientôt !");
      router.push("/login");
      router.refresh();
    } catch {
      toast.error("Erreur inattendue", { description: "Impossible de vous déconnecter." });
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Section profil */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="profile-title"
      >
        <h2
          id="profile-title"
          className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-neutral-400"
        >
          <User className="h-4 w-4" aria-hidden="true" />
          Profil
        </h2>

        <div className="flex items-center gap-4">
          {/* Avatar initiale */}
          <div
            className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-xl font-bold text-primary-600"
            aria-hidden="true"
          >
            {displayName.charAt(0).toUpperCase()}
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-semibold text-neutral-900 dark:text-neutral-100">
              {displayName}
            </p>
            <p className="truncate text-sm text-neutral-500">{user.email}</p>
            <p className="mt-0.5 text-xs text-neutral-400">Membre depuis {joinedDate}</p>
          </div>
        </div>
      </section>

      {/* Section foyer */}
      {householdData ? (
        <section
          className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
          aria-labelledby="household-title"
        >
          <h2
            id="household-title"
            className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-neutral-400"
          >
            <Users className="h-4 w-4" aria-hidden="true" />
            Mon foyer — {householdData.household.name}
          </h2>

          <ul className="space-y-3">
            {householdData.members.map((member) => (
              <li
                key={member.id}
                className="flex items-center gap-3 rounded-xl border border-neutral-100 bg-neutral-50 px-4 py-3 dark:border-neutral-700 dark:bg-neutral-800"
              >
                <div
                  className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-secondary-100 text-sm font-bold text-secondary-700"
                  aria-hidden="true"
                >
                  {member.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {member.display_name}
                    {member.is_child && (
                      <span className="ml-2 rounded-full bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-700">
                        Enfant
                      </span>
                    )}
                  </p>
                  {member.diet_tags.length > 0 && (
                    <p className="mt-0.5 truncate text-xs text-neutral-400">
                      {member.diet_tags.join(", ")}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900">
          <p className="text-sm text-neutral-400">
            Données du foyer non disponibles — vérifiez votre connexion.
          </p>
        </section>
      )}

      {/* Section liens rapides */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="quick-links-title"
      >
        <h2
          id="quick-links-title"
          className="sr-only"
        >
          Liens rapides
        </h2>

        <nav aria-label="Actions du compte">
          <Link
            href="/settings"
            className="flex min-h-[52px] items-center gap-3 border-b border-neutral-100 px-6 py-4 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
          >
            <Settings className="h-5 w-5 text-neutral-400" aria-hidden="true" strokeWidth={1.5} />
            <span className="flex-1">Paramètres</span>
            <ChevronRight className="h-4 w-4 text-neutral-300" aria-hidden="true" />
          </Link>

          <Link
            href="/billing"
            className="flex min-h-[52px] items-center gap-3 px-6 py-4 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 dark:text-neutral-300 dark:hover:bg-neutral-800"
          >
            <CreditCard className="h-5 w-5 text-neutral-400" aria-hidden="true" strokeWidth={1.5} />
            <span className="flex-1">Mon abonnement</span>
            <ChevronRight className="h-4 w-4 text-neutral-300" aria-hidden="true" />
          </Link>
        </nav>
      </section>

      {/* Bouton déconnexion */}
      <div className="pb-4">
        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          aria-busy={isLoggingOut}
          className="flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
            border border-red-200 bg-white px-6 py-3 text-sm font-semibold text-red-600
            transition-all hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2
            focus-visible:ring-red-500 focus-visible:ring-offset-2
            active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50
            dark:border-red-800 dark:bg-neutral-900 dark:text-red-400 dark:hover:bg-red-950/30"
        >
          {isLoggingOut ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Déconnexion…
            </>
          ) : (
            <>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Se déconnecter
            </>
          )}
        </button>
      </div>
    </div>
  );
}
