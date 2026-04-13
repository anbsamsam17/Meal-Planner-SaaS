// apps/web/src/components/shopping/shopping-list-item.tsx
// Item de la liste de courses avec swipe-to-delete mobile (Framer Motion)
// Référence : 04-components-catalog.md #20 ShoppingListItem
// 05-motion-principles.md — swipe : résistance progressive puis snap
"use client";

import { useRef } from "react";
import { Trash2 } from "lucide-react";
import { MotionDiv } from "@/components/motion";
import { cn } from "@/lib/utils";
import type { ShoppingListItem as ShoppingListItemType, IngredientCategory } from "@/lib/api/types";

interface ShoppingListItemProps {
  item: ShoppingListItemType;
  onToggle: (id: string, isChecked: boolean) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

// Labels FR catégories rayon supermarché
const CATEGORY_RAYON: Record<IngredientCategory, string> = {
  vegetables: "Légumes",
  fruits: "Fruits",
  meat: "Boucherie",
  fish: "Poissonnerie",
  dairy: "Crèmerie",
  grains: "Épicerie",
  legumes: "Épicerie",
  condiments: "Épicerie",
  herbs: "Épicerie",
  other: "Divers",
};

export function ShoppingListItem({ item, onToggle, onDelete, className }: ShoppingListItemProps) {
  const constraintsRef = useRef<HTMLDivElement>(null);

  return (
    <div ref={constraintsRef} className={cn("relative overflow-hidden", className)}>
      {/* Background rouge "supprimer" — visible pendant le swipe */}
      {onDelete && (
        <div className="absolute inset-0 flex items-center justify-end bg-red-500 px-4">
          <Trash2 className="h-5 w-5 text-white" aria-hidden="true" />
        </div>
      )}

      {/* Item — draggable via Framer Motion */}
      <MotionDiv
        drag={onDelete ? "x" : false}
        dragConstraints={{ left: -80, right: 0 }}
        dragElastic={0.1}
        onDragEnd={(_event, info) => {
          // Seuil de 40% de largeur standard (80px / 200px = 40%)
          if (info.offset.x < -70 && onDelete) {
            onDelete(item.id);
          }
        }}
        className="relative flex items-center gap-3 bg-white px-4 py-3 dark:bg-neutral-800"
      >
        {/* Checkbox */}
        <input
          type="checkbox"
          id={`item-${item.id}`}
          checked={item.is_checked}
          onChange={() => onToggle(item.id, !item.is_checked)}
          className="h-5 w-5 rounded border-neutral-300 accent-primary-500
            focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          aria-checked={item.is_checked}
        />

        {/* Contenu */}
        <label
          htmlFor={`item-${item.id}`}
          className="flex flex-1 cursor-pointer items-center justify-between gap-2"
        >
          <div className="flex flex-col">
            {/* Nom ingredient + quantite aggregee */}
            <span
              className={cn(
                "text-sm font-medium text-neutral-900 dark:text-neutral-100",
                item.is_checked && "text-neutral-400 line-through dark:text-neutral-500",
              )}
            >
              {item.quantity_display ? `${item.quantity_display} — ` : ""}
              {item.ingredient_name}
            </span>

            {/* Rayon — badge discret */}
            <span className="text-xs text-neutral-400 dark:text-neutral-500">
              {CATEGORY_RAYON[item.category]}
            </span>
          </div>

          {/* Quantite brute — fallback si pas de quantity_display */}
          {!item.quantity_display && item.quantity > 0 && (
            <span
              className={cn(
                "shrink-0 text-sm text-neutral-500 dark:text-neutral-400",
                item.is_checked && "text-neutral-300 line-through dark:text-neutral-600",
              )}
            >
              {item.quantity} {item.unit}
            </span>
          )}
        </label>

        {/* Badge "En stock" */}
        {item.is_in_stock && (
          <span className="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">
            En stock
          </span>
        )}
      </MotionDiv>
    </div>
  );
}
