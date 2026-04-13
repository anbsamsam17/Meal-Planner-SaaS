"use client";
// apps/web/src/app/(app)/fridge/fridge-content.tsx
// Contenu interactif du frigo — Client Component
// Phase 2 — liste items, dialog ajout, suggestions recettes

import { useState } from "react";
import { Plus, Refrigerator, Sparkles, X } from "lucide-react";
import { useFridge, useAddFridgeItem, useRemoveFridgeItem, useFridgeSuggestions } from "@/hooks/use-fridge";
import { FridgeItemCard } from "@/components/fridge/fridge-item";
import { RecipeCard } from "@/components/recipe/recipe-card";
import type { FridgeItemCreate, FridgeItemUnit } from "@/lib/api/types";

const UNITS: FridgeItemUnit[] = [
  "g", "kg", "ml", "L", "pièce", "tranche", "botte", "sachet", "boîte", "pot", "autre",
];

// Dialog simple d'ajout d'un produit (pas de librairie UI pour rester léger)
interface AddItemDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: FridgeItemCreate) => void;
  isSubmitting: boolean;
}

function AddItemDialog({ open, onClose, onSubmit, isSubmitting }: AddItemDialogProps) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState<FridgeItemUnit>("pièce");
  const [expiry, setExpiry] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      ingredient_name: name.trim(),
      quantity,
      unit,
      expiry_date: expiry || null,
    });
    setName("");
    setQuantity(1);
    setUnit("pièce");
    setExpiry("");
  }

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-item-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-t-2xl bg-white p-6 shadow-xl sm:rounded-2xl">
        {/* Header dialog */}
        <div className="mb-4 flex items-center justify-between">
          <h2 id="add-item-title" className="text-base font-semibold text-neutral-900">
            Ajouter un produit
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nom ingrédient */}
          <div>
            <label htmlFor="ingredient-name" className="mb-1 block text-sm font-medium text-neutral-700">
              Nom du produit <span aria-hidden>*</span>
            </label>
            <input
              id="ingredient-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex : tomates cerises, poulet..."
              required
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 placeholder-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>

          {/* Quantité + unité */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label htmlFor="quantity" className="mb-1 block text-sm font-medium text-neutral-700">
                Quantité
              </label>
              <input
                id="quantity"
                type="number"
                min={0.1}
                step={0.1}
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
              />
            </div>
            <div className="flex-1">
              <label htmlFor="unit" className="mb-1 block text-sm font-medium text-neutral-700">
                Unité
              </label>
              <select
                id="unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value as FridgeItemUnit)}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
              >
                {UNITS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Date d'expiration (optionnelle) */}
          <div>
            <label htmlFor="expiry" className="mb-1 block text-sm font-medium text-neutral-700">
              Date d&apos;expiration{" "}
              <span className="font-normal text-neutral-400">(optionnelle)</span>
            </label>
            <input
              id="expiry"
              type="date"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !name.trim()}
            className="inline-flex min-h-[44px] w-full items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {isSubmitting ? "Ajout..." : "Ajouter au frigo"}
          </button>
        </form>
      </div>
    </div>
  );
}

export function FridgeContent() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  const { data: items = [], isLoading } = useFridge();
  const addMutation = useAddFridgeItem();
  const removeMutation = useRemoveFridgeItem();
  const suggestionsMutation = useFridgeSuggestions();

  function handleAdd(data: FridgeItemCreate) {
    addMutation.mutate(data, {
      onSuccess: () => setDialogOpen(false),
    });
  }

  function handleDelete(id: string) {
    setDeletingIds((prev) => new Set([...prev, id]));
    removeMutation.mutate(id, {
      onSettled: () => {
        setDeletingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      },
    });
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* En-tête */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Mon frigo</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {items.length} produit{items.length !== 1 ? "s" : ""} disponible
            {items.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          <Plus className="h-4 w-4" aria-hidden />
          Ajouter
        </button>
      </div>

      {/* Liste des items */}
      {isLoading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-300 border-t-primary-600" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-white py-16 text-center">
          <Refrigerator className="mb-4 h-12 w-12 text-neutral-300" aria-hidden />
          <p className="mb-1 text-sm font-semibold text-neutral-700">
            Votre frigo est vide
          </p>
          <p className="mb-4 text-xs text-neutral-500">
            Ajoutez vos ingrédients pour recevoir des suggestions de recettes personnalisées.
          </p>
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            <Plus className="h-4 w-4" aria-hidden />
            Ajouter un produit
          </button>
        </div>
      ) : (
        <>
          <ul className="space-y-2" role="list">
            {items.map((item) => (
              <li key={item.id}>
                <FridgeItemCard
                  item={item}
                  onDelete={handleDelete}
                  isDeleting={deletingIds.has(item.id)}
                />
              </li>
            ))}
          </ul>

          {/* CTA suggestions recettes */}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => suggestionsMutation.mutate()}
              disabled={suggestionsMutation.isPending}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-primary-200 bg-primary-50 px-4 py-3 text-sm font-semibold text-primary-700 transition-colors hover:bg-primary-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" aria-hidden />
              {suggestionsMutation.isPending
                ? "Recherche en cours..."
                : "Que cuisiner avec mon frigo ?"}
            </button>
          </div>

          {/* Suggestions recettes */}
          {suggestionsMutation.isSuccess && suggestionsMutation.data.recipes.length > 0 && (
            <section className="mt-8" aria-label="Suggestions basées sur le frigo">
              <h2 className="mb-3 text-base font-semibold text-neutral-900">
                Recettes suggérées
                <span className="ml-2 text-xs font-normal text-neutral-500">
                  basées sur :{" "}
                  {suggestionsMutation.data.matched_ingredients
                    .slice(0, 3)
                    .join(", ")}
                  {suggestionsMutation.data.matched_ingredients.length > 3 && "..."}
                </span>
              </h2>
              <ul className="grid gap-4 sm:grid-cols-2" role="list">
                {suggestionsMutation.data.recipes.slice(0, 5).map((recipe) => (
                  <li key={recipe.id}>
                    <RecipeCard recipe={recipe} variant="md" />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {/* Dialog ajout produit */}
      <AddItemDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleAdd}
        isSubmitting={addMutation.isPending}
      />
    </div>
  );
}
