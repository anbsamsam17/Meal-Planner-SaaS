"use client";
// apps/web/src/components/fridge/fridge-item.tsx
// Item du frigo avec badge expiry et swipe-to-delete (Framer Motion)
// Phase 2

import { useRef } from "react";
import { MotionDiv, MotionArticle, useMotionValue, useTransform, animate } from "@/components/motion";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FridgeItem } from "@/lib/api/types";

type ExpiryStatus = "fresh" | "soon" | "urgent" | "expired" | "unknown";

function getExpiryStatus(expiryDate: string | null): ExpiryStatus {
  if (!expiryDate) return "unknown";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(expiryDate);
  expiry.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return "expired";
  if (diffDays < 2) return "urgent";
  if (diffDays < 5) return "soon";
  return "fresh";
}

const EXPIRY_BADGE: Record<
  ExpiryStatus,
  { label: string; classes: string }
> = {
  fresh: { label: "Frais", classes: "bg-green-100 text-green-700" },
  soon: { label: "Bientôt périmé", classes: "bg-amber-100 text-amber-700" },
  urgent: { label: "Expire sous 2j", classes: "bg-red-100 text-red-700" },
  expired: { label: "Périmé", classes: "bg-red-200 text-red-800" },
  unknown: { label: "", classes: "bg-neutral-100 text-neutral-500" },
};

interface FridgeItemCardProps {
  item: FridgeItem;
  onDelete: (id: string) => void;
  isDeleting?: boolean;
}

const SWIPE_THRESHOLD = -80; // px — seuil pour déclencher la suppression

export function FridgeItemCard({ item, onDelete, isDeleting }: FridgeItemCardProps) {
  const x = useMotionValue(0);
  const deleteOpacity = useTransform(x, [0, SWIPE_THRESHOLD], [0, 1]);
  const constraintsRef = useRef<HTMLDivElement>(null);

  const status = getExpiryStatus(item.expiry_date);
  const badge = EXPIRY_BADGE[status];

  function handleDragEnd() {
    const currentX = x.get();
    if (currentX < SWIPE_THRESHOLD) {
      // Supprimer après animation de sortie
      void animate(x, -300, { duration: 0.2 }).then(() => {
        onDelete(item.id);
      });
    } else {
      // Revenir à la position initiale
      void animate(x, 0, { type: "spring", stiffness: 400, damping: 30 });
    }
  }

  return (
    <div ref={constraintsRef} className="relative overflow-hidden rounded-xl">
      {/* Arrière-plan rouge (révélé au swipe) */}
      <MotionDiv
        className="absolute inset-0 flex items-center justify-end rounded-xl bg-red-500 px-4"
        style={{ opacity: deleteOpacity }}
        aria-hidden
      >
        <Trash2 className="h-5 w-5 text-white" />
      </MotionDiv>

      {/* Contenu draggable */}
      <MotionArticle
        style={{ x }}
        drag="x"
        dragConstraints={{ left: -120, right: 0 }}
        dragElastic={0.1}
        onDragEnd={handleDragEnd}
        className={cn(
          "relative flex items-center gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm",
          "cursor-grab active:cursor-grabbing select-none",
          isDeleting && "opacity-50",
        )}
        aria-label={`Produit : ${item.ingredient_name}, ${item.quantity} ${item.unit}`}
      >
        {/* Nom + quantité */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-neutral-900">
            {item.ingredient_name}
          </p>
          <p className="text-xs text-neutral-500">
            {item.quantity} {item.unit}
          </p>
        </div>

        {/* Badge expiry */}
        {status !== "unknown" && (
          <span
            className={cn(
              "inline-flex flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium",
              badge.classes,
            )}
          >
            {badge.label}
          </span>
        )}

        {/* Bouton supprimer accessible au clavier (en complément du swipe) */}
        <button
          type="button"
          onClick={() => onDelete(item.id)}
          disabled={isDeleting}
          className="flex-shrink-0 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50"
          aria-label={`Supprimer ${item.ingredient_name}`}
        >
          <Trash2 className="h-4 w-4" aria-hidden />
        </button>
      </MotionArticle>
    </div>
  );
}
