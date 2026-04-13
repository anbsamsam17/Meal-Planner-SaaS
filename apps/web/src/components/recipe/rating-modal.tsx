// apps/web/src/components/recipe/rating-modal.tsx
// Modal de notation d'une recette — 3 emojis OU étoiles 1-5
// Référence : 04-components-catalog.md #22 StarRating Haptic-like
// POST /api/v1/feedbacks après validation
// FIX Phase 1 mature (review 2026-04-12) — Mismatch B : mapping UI → enum backend
"use client";

import { useState } from "react";
import { X, Loader2, Star } from "lucide-react";
import { useRateRecipe } from "@/hooks/use-recipes";
import { cn } from "@/lib/utils";
import type { BackendFeedbackType } from "@/lib/api/endpoints";

interface RatingModalProps {
  recipeId: string;
  recipeTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

// FIX Phase 1 mature (review 2026-04-12) — Mismatch B
// Mapping UI emoji → contrat backend Pydantic FeedbackCreate
// Backend attend : "cooked" | "skipped" | "favorited"
// 😍 Adoré     → "cooked" (a cuisiné et adoré) + rating 5
// 🙂 Correct   → "cooked" (a cuisiné, c'était correct) + rating 3
// 😕 Pas terrible → "skipped" (a évité / ne referait pas) + rating 1
const QUICK_RATINGS = [
  { emoji: "😍", label: "Adoré !", feedbackType: "cooked" as BackendFeedbackType, rating: 5 },
  { emoji: "🙂", label: "Correct", feedbackType: "cooked" as BackendFeedbackType, rating: 3 },
  { emoji: "😕", label: "Pas terrible", feedbackType: "skipped" as BackendFeedbackType, rating: 1 },
] as const;

// Type UI interne — distinct du type backend pour garder la lisibilité
type UiEmojiKey = "loved" | "ok" | "disliked";

// Table de correspondance UI → backend (utilisée dans handleSubmit)
const UI_TO_BACKEND_FEEDBACK: Record<UiEmojiKey, BackendFeedbackType> = {
  loved: "cooked",
  ok: "cooked",
  disliked: "skipped",
};

export function RatingModal({ recipeId, recipeTitle, isOpen, onClose }: RatingModalProps) {
  const [selectedEmoji, setSelectedEmoji] = useState<UiEmojiKey | null>(null);
  const [starRating, setStarRating] = useState<number>(0);
  const [hoveredStar, setHoveredStar] = useState<number>(0);
  const [notes, setNotes] = useState("");

  const rateRecipeMutation = useRateRecipe();

  async function handleSubmit() {
    // Déterminer le rating final — emoji ou étoile
    let finalRating: 1 | 2 | 3 | 4 | 5;
    // FIX Phase 1 mature (review 2026-04-12) — Mismatch B : type backend obligatoire
    let feedbackType: BackendFeedbackType;

    if (starRating > 0) {
      finalRating = starRating as 1 | 2 | 3 | 4 | 5;
      // Mapping étoiles → enum backend : ≥4 étoiles = cuisiné et adoré, sinon skipped
      feedbackType = starRating >= 4 ? "favorited" : starRating >= 3 ? "cooked" : "skipped";
    } else if (selectedEmoji) {
      // Mapping emoji UI → rating numérique
      const quickRating = QUICK_RATINGS.find((r) => {
        // Correspondance : loved→cooked/5, ok→cooked/3, disliked→skipped/1
        if (selectedEmoji === "loved") return r.rating === 5;
        if (selectedEmoji === "ok") return r.rating === 3;
        return r.rating === 1; // disliked
      });
      finalRating = (quickRating?.rating ?? 3) as 1 | 2 | 3 | 4 | 5;
      feedbackType = UI_TO_BACKEND_FEEDBACK[selectedEmoji];
    } else {
      return; // Pas de rating sélectionné
    }

    await rateRecipeMutation.mutateAsync({
      recipe_id: recipeId,
      rating: finalRating,
      feedback_type: feedbackType,
      notes: notes.trim() || null,
    });

    handleClose();
  }

  function handleClose() {
    setSelectedEmoji(null);
    setStarRating(0);
    setHoveredStar(0);
    setNotes("");
    onClose();
  }

  if (!isOpen) return null;

  const hasSelection = selectedEmoji !== null || starRating > 0;

  return (
    // Overlay backdrop — position relative pour le dialog positionné en absolu
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="rating-modal-title"
    >
      {/* Fond cliquable — button transparent pour satisfaire a11y (élément interactif) */}
      <button
        type="button"
        className="absolute inset-0 bg-neutral-900/50"
        onClick={handleClose}
        onKeyDown={(e) => { if (e.key === "Escape") handleClose(); }}
        aria-label="Fermer la modale"
        tabIndex={-1}
      />

      {/* Panneau modal — au-dessus du bouton overlay (z-index relatif) */}
      <div className="relative z-10 w-full max-w-sm rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-2xl dark:bg-neutral-800">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="rating-modal-title"
            className="font-serif text-lg font-bold text-neutral-900 dark:text-neutral-100"
          >
            Noter cette recette
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-neutral-400
              transition-colors hover:bg-neutral-100 hover:text-neutral-600
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
              dark:hover:bg-neutral-700"
            aria-label="Fermer"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Titre de la recette */}
        <p className="mb-6 text-sm text-neutral-500 dark:text-neutral-400">
          {recipeTitle}
        </p>

        {/* 3 emojis de feedback rapide */}
        {/* FIX Phase 1 mature (review 2026-04-12) — clé UI indépendante du type backend */}
        <div className="mb-6 flex justify-center gap-4">
          {(["loved", "ok", "disliked"] as UiEmojiKey[]).map((uiKey, idx) => {
            const option = QUICK_RATINGS[idx];
            if (!option) return null;
            return (
            <button
              key={uiKey}
              type="button"
              onClick={() => {
                setSelectedEmoji(uiKey);
                setStarRating(0); // Réinitialiser les étoiles si emoji sélectionné
              }}
              aria-pressed={selectedEmoji === uiKey}
              className={cn(
                "flex flex-col items-center gap-1 rounded-2xl p-3 transition-all duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
                selectedEmoji === uiKey
                  ? "bg-primary-50 ring-2 ring-primary-400 dark:bg-primary-950"
                  : "hover:bg-neutral-50 dark:hover:bg-neutral-700",
              )}
            >
              <span className="text-3xl" role="img" aria-label={option.label}>
                {option.emoji}
              </span>
              <span
                className={cn(
                  "text-xs font-medium",
                  selectedEmoji === uiKey
                    ? "text-primary-600 dark:text-primary-400"
                    : "text-neutral-500 dark:text-neutral-400",
                )}
              >
                {option.label}
              </span>
            </button>
            );
          })}
        </div>

        {/* Séparateur */}
        <div className="mb-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
          <span className="text-xs text-neutral-400">ou</span>
          <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
        </div>

        {/* Étoiles 1-5 — Référence : 04-components-catalog.md #05 RatingStars */}
        <div className="mb-6 flex justify-center gap-1" role="group" aria-label="Note de 1 à 5 étoiles">
          {[1, 2, 3, 4, 5].map((star) => {
            const isActive = star <= (hoveredStar || starRating);
            return (
              <button
                key={star}
                type="button"
                onClick={() => {
                  setStarRating(star);
                  setSelectedEmoji(null); // Réinitialiser l'emoji si étoile sélectionnée
                }}
                onMouseEnter={() => setHoveredStar(star)}
                onMouseLeave={() => setHoveredStar(0)}
                aria-label={`${star} étoile${star > 1 ? "s" : ""}`}
                aria-pressed={starRating === star}
                className="transition-transform duration-fast hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              >
                <Star
                  className={cn(
                    "h-7 w-7 transition-colors duration-fast",
                    isActive
                      ? "fill-amber-400 text-amber-400"
                      : "fill-none text-neutral-300 dark:text-neutral-600",
                  )}
                  aria-hidden="true"
                />
              </button>
            );
          })}
        </div>

        {/* Notes optionnelles */}
        <div className="mb-6">
          <label
            htmlFor="rating-notes"
            className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            Commentaire <span className="font-normal text-neutral-400">(optionnel)</span>
          </label>
          <textarea
            id="rating-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Les enfants ont adoré ! À refaire la semaine prochaine…"
            rows={3}
            maxLength={500}
            className="w-full resize-none rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3
              text-sm text-neutral-900 placeholder:text-neutral-400
              focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500
              dark:border-neutral-700 dark:bg-neutral-700/50 dark:text-neutral-100"
          />
        </div>

        {/* Bouton Envoyer */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!hasSelection || rateRecipeMutation.isPending}
          aria-busy={rateRecipeMutation.isPending}
          className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
            bg-primary-500 px-6 py-3 font-semibold text-white
            transition-all hover:bg-primary-600 focus-visible:outline-none
            focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2
            active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {rateRecipeMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Envoi en cours…
            </>
          ) : (
            "Envoyer mon avis"
          )}
        </button>
      </div>
    </div>
  );
}
