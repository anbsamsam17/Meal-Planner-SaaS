// apps/web/src/components/ui/badge.tsx
// Composant Badge — tags sémantiques pour les recettes
// Référence : phase-0/design-system/04-components-catalog.md #06 Badge
// 3 familles : diet (régime), time (durée), level (difficulté)
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  // Base
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-2xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        // Régimes alimentaires — famille diet
        vegetarian: "bg-secondary-100 text-secondary-700",
        vegan: "bg-success-100 text-success-700",
        "gluten-free": "bg-accent-100 text-accent-700",
        "lactose-free": "bg-info-100 text-info-700",
        halal: "bg-primary-100 text-primary-700",
        // Durée de préparation — famille time
        time: "bg-neutral-100 text-neutral-700",
        // Niveau de difficulté — famille level
        easy: "bg-success-100 text-success-700",
        medium: "bg-warning-100 text-warning-700",
        hard: "bg-error-100 text-error-700",
        // Spéciaux
        new: "bg-accent-100 text-accent-700",
        ai: "bg-primary-100 text-primary-700",
        // Défaut générique
        default: "bg-neutral-100 text-neutral-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  // Pour les badges dynamiques (annoncés aux lecteurs d'écran)
  dynamic?: boolean;
}

function Badge({ className, variant, dynamic = false, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant }), className)}
      role={dynamic ? "status" : undefined}
      {...props}
    >
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
