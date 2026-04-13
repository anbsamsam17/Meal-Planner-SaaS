// apps/web/src/components/ui/skeleton.tsx
// Composant Skeleton — états de chargement avec shimmer warm
// Référence : phase-0/design-system/04-components-catalog.md #08 Skeleton
// Animation shimmer-warm définie dans globals.css
import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  // Variante visuelle du skeleton
  variant?: "text" | "image" | "avatar" | "badge" | "card";
}

function Skeleton({ className, variant = "text", ...props }: SkeletonProps) {
  const variantClasses: Record<NonNullable<SkeletonProps["variant"]>, string> = {
    text: "h-4 rounded-md",
    image: "rounded-xl",
    avatar: "rounded-full",
    badge: "h-5 w-16 rounded-full",
    card: "h-48 rounded-xl",
  };

  return (
    <div
      className={cn("skeleton-shimmer", variantClasses[variant], className)}
      role="status"
      aria-busy="true"
      aria-label="Chargement en cours"
      {...props}
    />
  );
}

// Skeleton de card recette complète
function RecipeCardSkeleton() {
  return (
    <div
      className="overflow-hidden rounded-xl border border-neutral-200"
      role="status"
      aria-busy="true"
      aria-label="Chargement de la recette"
    >
      {/* Image placeholder */}
      <Skeleton variant="image" className="aspect-video w-full" aria-hidden="true" />
      {/* Contenu */}
      <div className="p-4" aria-hidden="true">
        <Skeleton variant="text" className="mb-2 w-3/4" />
        <Skeleton variant="text" className="w-1/2" />
        <div className="mt-3 flex gap-2">
          <Skeleton variant="badge" />
          <Skeleton variant="badge" />
        </div>
      </div>
    </div>
  );
}

export { Skeleton, RecipeCardSkeleton };
