// apps/web/src/components/recipe/import-url-modal.tsx
// Modal d'import d'une recette depuis une URL — pattern identique à rating-modal.tsx
// POST /api/v1/recipes/import-url via useImportRecipe hook
"use client";

import { useState } from "react";
import { X, Loader2, Link2, CheckCircle2 } from "lucide-react";
import { useImportRecipe } from "@/hooks/use-import-recipe";
import { cn } from "@/lib/utils";

interface ImportUrlModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ImportUrlModal({ isOpen, onClose }: ImportUrlModalProps) {
  const [url, setUrl] = useState("");
  const importMutation = useImportRecipe();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    await importMutation.mutateAsync(trimmed);
  }

  function handleClose() {
    if (importMutation.isPending) return;
    setUrl("");
    importMutation.reset();
    onClose();
  }

  if (!isOpen) return null;

  const isSuccess = importMutation.isSuccess;
  const isValid = url.trim().length >= 10 && /^https?:\/\/.+\..+/.test(url.trim());

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-url-modal-title"
    >
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-neutral-900/50"
        onClick={handleClose}
        onKeyDown={(e) => { if (e.key === "Escape") handleClose(); }}
        aria-label="Fermer la modale"
        tabIndex={-1}
      />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-md rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-2xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="import-url-modal-title"
            className="flex items-center gap-2 font-serif text-lg font-bold text-[#201a19]"
          >
            <Link2 className="h-5 w-5 text-[#E2725B]" aria-hidden="true" />
            Importer une recette
          </h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={importMutation.isPending}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-[#857370]
              transition-colors hover:bg-[#E2725B]/10 hover:text-[#E2725B]
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]
              disabled:opacity-50"
            aria-label="Fermer"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {isSuccess ? (
          /* Succès */
          <div className="flex flex-col items-center gap-4 py-6">
            <CheckCircle2 className="h-12 w-12 text-green-500" aria-hidden="true" />
            <p className="text-center text-sm text-[#201a19]">
              La recette est en cours d&apos;import !
              <br />
              <span className="text-[#857370]">
                Elle apparaitra dans la liste sous quelques secondes.
              </span>
            </p>
            <button
              type="button"
              onClick={handleClose}
              className="rounded-xl bg-[#E2725B] px-6 py-3 text-sm font-semibold text-white
                transition-all hover:bg-[#d4624d] focus-visible:outline-none
                focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2"
            >
              Fermer
            </button>
          </div>
        ) : (
          /* Formulaire */
          <form onSubmit={handleSubmit}>
            <p className="mb-4 text-sm text-[#857370]">
              Collez le lien d&apos;une recette depuis n&apos;importe quel site
              (Marmiton, 750g, Cuisine AZ, blogs...).
            </p>

            <label htmlFor="import-url-input" className="sr-only">
              URL de la recette
            </label>
            <input
              id="import-url-input"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.marmiton.org/recettes/..."
              autoFocus
              disabled={importMutation.isPending}
              className={cn(
                "w-full rounded-xl border bg-[#E2725B]/5 px-4 py-3.5 text-sm text-[#201a19]",
                "placeholder:text-[#857370]/60",
                "focus:outline-none focus:ring-2 focus:ring-[#E2725B]/30",
                "disabled:opacity-60",
                importMutation.isError
                  ? "border-red-300 focus:ring-red-300"
                  : "border-transparent",
              )}
            />

            {importMutation.isError && (
              <p className="mt-2 text-xs text-red-600" role="alert">
                {importMutation.error.message.includes("429")
                  ? "Limite atteinte — max 10 imports par heure."
                  : importMutation.error.message.includes("422")
                    ? "URL invalide. Vérifiez le lien et réessayez."
                    : "Impossible d'importer cette recette."}
              </p>
            )}

            <button
              type="submit"
              disabled={!isValid || importMutation.isPending}
              aria-busy={importMutation.isPending}
              className="mt-4 inline-flex min-h-[48px] w-full items-center justify-center gap-2
                rounded-xl bg-[#E2725B] px-6 py-3 font-semibold text-white
                transition-all hover:bg-[#d4624d] focus-visible:outline-none
                focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2
                active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {importMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Import en cours...
                </>
              ) : (
                "Importer la recette"
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
