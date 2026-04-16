// apps/web/src/app/(app)/settings/settings-content.tsx
// Client Component — formulaire préférences alimentaires, temps, drive, thème, suppression compte
// BUG 3 FIX (2026-04-12)
// PATCH /api/v1/households/me/members/{id}/preferences
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Save, Trash2, Sun, Moon, Monitor } from "lucide-react";
import { useHousehold } from "@/hooks/use-household";
import { apiClient } from "@/lib/api/client";

// Régimes alimentaires disponibles
const DIET_OPTIONS = [
  { value: "vegetarian", label: "Végétarien" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten-free", label: "Sans gluten" },
  { value: "lactose-free", label: "Sans lactose" },
  { value: "halal", label: "Halal" },
  { value: "no-pork", label: "Sans porc" },
  { value: "no-seafood", label: "Sans fruits de mer" },
  { value: "nut-free", label: "Sans fruits à coque" },
] as const;

// Drives disponibles
const DRIVE_OPTIONS = [
  { value: "none", label: "Aucun" },
  { value: "leclerc", label: "E.Leclerc Drive" },
  { value: "auchan", label: "Auchan Drive" },
  { value: "carrefour", label: "Carrefour Drive" },
  { value: "intermarche", label: "Intermarché Drive" },
  { value: "other", label: "Autre" },
] as const;

type DriveValue = (typeof DRIVE_OPTIONS)[number]["value"];
type ThemeValue = "light" | "dark" | "system";

interface SettingsFormState {
  dietTags: string[];
  allergies: string;
  cookingTimeMax: number;
  driveProvider: DriveValue;
  theme: ThemeValue;
}

export function SettingsContent() {
  const router = useRouter();
  const { household, loading } = useHousehold();

  // Récupérer le premier membre propriétaire (non-enfant)
  const ownerMember = household?.members.find((m) => !m.is_child) ?? household?.members[0];

  const [form, setForm] = useState<SettingsFormState>({
    dietTags: [],
    allergies: "",
    cookingTimeMax: 45,
    driveProvider: "none",
    theme: "system",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmInput, setDeleteConfirmInput] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  // Hydration depuis les donnees du foyer
  // Defensif : tous les champs nullable/undefined sont proteges par des fallbacks
  useEffect(() => {
    if (!household) return;

    const prefs = household.preferences;
    const member = ownerMember;

    // Proteger allergies : peut etre undefined si l'API ne retourne pas le champ
    const memberAllergies = Array.isArray(member?.allergies) ? member.allergies : [];
    const memberDietTags = Array.isArray(member?.diet_tags) ? member.diet_tags : [];

    setForm({
      dietTags: memberDietTags,
      allergies: memberAllergies.join(", "),
      cookingTimeMax: prefs?.cooking_time_max ?? 45,
      driveProvider: (household.household?.drive_provider as DriveValue | null) ?? "none",
      theme: (typeof window !== "undefined"
        ? (localStorage.getItem("presto-theme") as ThemeValue | null) ?? "system"
        : "system"),
    });
  }, [household, ownerMember]);

  function toggleDiet(value: string) {
    setForm((prev) => ({
      ...prev,
      dietTags: prev.dietTags.includes(value)
        ? prev.dietTags.filter((t) => t !== value)
        : [...prev.dietTags, value],
    }));
  }

  async function handleSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!ownerMember) {
      toast.error("Foyer introuvable", {
        description: "Impossible de sauvegarder sans foyer configuré.",
      });
      return;
    }

    setIsSaving(true);

    // Sauvegarder le thème localement
    try {
      localStorage.setItem("presto-theme", form.theme);
    } catch {
      // Navigation privée — ignorer
    }

    try {
      // Sauvegarder les preferences du membre (alimentation, temps, budget)
      await apiClient.patch(
        `/api/v1/households/me/members/${ownerMember.id}/preferences`,
        {
          diet_tags: form.dietTags,
          allergies: form.allergies
            .split(",")
            .map((a) => a.trim())
            .filter(Boolean),
          dislikes: [],
          cooking_time_max: form.cookingTimeMax,
          budget_pref: null,
        },
      );

      // Guard : s'assurer que le foyer existe avant de PATCH /households/me
      if (!household?.household?.id) {
        toast.error("Foyer introuvable", {
          description: "Impossible de sauvegarder le drive — foyer non configuré.",
        });
        setIsSaving(false);
        return;
      }

      // Sauvegarder le drive provider sur le household
      const driveValue = form.driveProvider === "none" ? null : form.driveProvider;
      try {
        await apiClient.patch("/api/v1/households/me", {
          drive_provider: driveValue,
        });
      } catch (driveErr) {
        // Erreur spécifique au PATCH /households/me — logguer et afficher un message clair
        const msg = driveErr instanceof Error ? driveErr.message : "Erreur inconnue";
        toast.error("Impossible de sauvegarder le drive", { description: msg });
        setIsSaving(false);
        return;
      }

      toast.success("Préférences sauvegardées !", {
        description: "Vos paramètres ont été mis à jour.",
      });
    } catch (err) {
      // Erreur sur le PATCH des préférences membre
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      toast.error("Erreur de sauvegarde", { description: msg });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteAccount() {
    if (deleteConfirmInput !== "SUPPRIMER") return;

    setIsDeleting(true);
    try {
      // Appel API de suppression — le backend gère la suppression Supabase + données
      await apiClient.delete("/api/v1/households/me");

      toast.success("Compte supprimé", {
        description: "Vos données ont été supprimées. À bientôt.",
      });

      // Déconnexion côté client
      const { createBrowserClient } = await import("@/lib/supabase/client");
      const supabase = createBrowserClient();
      await supabase.auth.signOut();

      router.push("/");
    } catch {
      toast.error("Suppression impossible", {
        description: "Contactez le support si le problème persiste.",
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary-400" aria-hidden="true" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Section préférences alimentaires */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="diet-title"
      >
        <h2
          id="diet-title"
          className="mb-1 text-base font-semibold text-neutral-900 dark:text-neutral-100"
        >
          Préférences alimentaires
        </h2>
        <p className="mb-4 text-sm text-neutral-500">
          Sélectionnez les régimes qui s&apos;appliquent à votre foyer.
        </p>

        <fieldset>
          <legend className="sr-only">Régimes alimentaires</legend>
          <div className="flex flex-wrap gap-2">
            {DIET_OPTIONS.map((opt) => {
              const isSelected = form.dietTags.includes(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleDiet(opt.value)}
                  aria-pressed={isSelected}
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-all
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                    ${
                      isSelected
                        ? "border-primary-500 bg-primary-500 text-white"
                        : "border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-300 hover:bg-neutral-100"
                    }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Allergies */}
        <div className="mt-4">
          <label
            htmlFor="allergies"
            className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            Allergies spécifiques
          </label>
          <input
            id="allergies"
            type="text"
            value={form.allergies}
            onChange={(e) => setForm((prev) => ({ ...prev, allergies: e.target.value }))}
            placeholder="Ex : arachides, sésame, kiwi (séparés par des virgules)"
            className="block h-11 w-full rounded-xl border border-neutral-300 bg-neutral-50 px-4 text-sm
              placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none
              focus:ring-2 focus:ring-primary-500 focus:ring-offset-0
              dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          />
        </div>
      </section>

      {/* Section temps de cuisine */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="cooking-title"
      >
        <h2
          id="cooking-title"
          className="mb-1 text-base font-semibold text-neutral-900 dark:text-neutral-100"
        >
          Temps de cuisine
        </h2>
        <p className="mb-4 text-sm text-neutral-500">
          Durée maximale de préparation par repas.
        </p>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-neutral-400">15 min</span>
            <span className="rounded-full bg-primary-100 px-3 py-1 text-sm font-semibold text-primary-700">
              {form.cookingTimeMax} min max
            </span>
            <span className="text-xs text-neutral-400">120 min</span>
          </div>
          <input
            type="range"
            id="cooking-time"
            min={15}
            max={120}
            step={5}
            value={form.cookingTimeMax}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, cookingTimeMax: parseInt(e.target.value, 10) }))
            }
            aria-label={`Temps de cuisine maximum : ${form.cookingTimeMax} minutes`}
            className="h-2 w-full cursor-pointer appearance-none rounded-full bg-neutral-200
              accent-primary-500 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500"
          />
        </div>
      </section>

      {/* Section drive préféré */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="drive-title"
      >
        <h2
          id="drive-title"
          className="mb-1 text-base font-semibold text-neutral-900 dark:text-neutral-100"
        >
          Drive préféré
        </h2>
        <p className="mb-4 text-sm text-neutral-500">
          Choisissez votre enseigne pour la liste de courses automatique.
        </p>

        <select
          id="drive-provider"
          value={form.driveProvider}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, driveProvider: e.target.value as DriveValue }))
          }
          aria-label="Drive préféré"
          className="block h-11 w-full rounded-xl border border-neutral-300 bg-neutral-50 px-4 text-sm
            focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500
            dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
        >
          {DRIVE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </section>

      {/* Section thème */}
      <section
        className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
        aria-labelledby="theme-title"
      >
        <h2
          id="theme-title"
          className="mb-1 text-base font-semibold text-neutral-900 dark:text-neutral-100"
        >
          Thème
        </h2>
        <p className="mb-4 text-sm text-neutral-500">Choisissez l&apos;apparence de l&apos;interface.</p>

        <fieldset>
          <legend className="sr-only">Thème de l&apos;application</legend>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                { value: "light" as ThemeValue, label: "Clair", icon: Sun },
                { value: "dark" as ThemeValue, label: "Sombre", icon: Moon },
                { value: "system" as ThemeValue, label: "Système", icon: Monitor },
              ] as const
            ).map(({ value, label, icon: Icon }) => {
              const isSelected = form.theme === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setForm((prev) => ({ ...prev, theme: value }));
                    // Appliquer le thème immédiatement sans attendre la sauvegarde
                    if (value === "dark") {
                      document.documentElement.classList.add("dark");
                    } else if (value === "light") {
                      document.documentElement.classList.remove("dark");
                    } else {
                      // system : détecter la préférence OS
                      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                      document.documentElement.classList.toggle("dark", prefersDark);
                    }
                  }}
                  aria-pressed={isSelected}
                  className={`flex flex-col items-center gap-2 rounded-xl border py-4 text-sm font-medium transition-all
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                    ${
                      isSelected
                        ? "border-primary-500 bg-primary-50 text-primary-700"
                        : "border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-300"
                    }`}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" strokeWidth={1.5} />
                  {label}
                </button>
              );
            })}
          </div>
        </fieldset>
      </section>

      {/* Bouton sauvegarder */}
      <button
        type="submit"
        disabled={isSaving}
        aria-busy={isSaving}
        className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
          bg-primary-500 px-6 py-3 text-base font-semibold text-white
          transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-primary-500 focus-visible:ring-offset-2
          active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSaving ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Sauvegarde…
          </>
        ) : (
          <>
            <Save className="h-4 w-4" aria-hidden="true" />
            Sauvegarder les préférences
          </>
        )}
      </button>

      {/* Section danger — suppression de compte */}
      <section
        className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-950/20"
        aria-labelledby="danger-title"
      >
        <h2
          id="danger-title"
          className="mb-1 text-base font-semibold text-red-700 dark:text-red-400"
        >
          Zone de danger
        </h2>
        <p className="mb-4 text-sm text-red-600/80 dark:text-red-400/80">
          La suppression de votre compte est irréversible. Toutes vos données seront effacées.
        </p>

        {!showDeleteConfirm ? (
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-red-300 bg-white
              px-4 py-2.5 text-sm font-semibold text-red-600 transition-colors
              hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-red-500 focus-visible:ring-offset-2"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Supprimer mon compte
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-medium text-red-700">
              Tapez <strong>SUPPRIMER</strong> pour confirmer :
            </p>
            <input
              type="text"
              value={deleteConfirmInput}
              onChange={(e) => setDeleteConfirmInput(e.target.value)}
              placeholder="SUPPRIMER"
              aria-label="Confirmation de suppression — tapez SUPPRIMER"
              className="block h-11 w-full rounded-xl border border-red-300 bg-white px-4 text-sm
                placeholder:text-red-300 focus:border-red-500 focus:outline-none
                focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteConfirmInput("");
                }}
                className="flex-1 rounded-xl border border-neutral-200 bg-white px-4 py-2.5
                  text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-500"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmInput !== "SUPPRIMER" || isDeleting}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl
                  bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors
                  hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2
                  focus-visible:ring-red-500 focus-visible:ring-offset-2
                  disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isDeleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                )}
                Confirmer
              </button>
            </div>
          </div>
        )}
      </section>
    </form>
  );
}
