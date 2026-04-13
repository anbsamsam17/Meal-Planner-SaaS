// apps/web/src/components/ui/card.tsx
// Composant Card — design premium Presto
// Fond blanc, rounded-2xl, ombres warm, hover scale léger
// Référence : phase-0/design-system/04-components-catalog.md #03 Card Recipe
import * as React from "react";
import { cn } from "@/lib/utils";

// Card principale — fond blanc, rounded-2xl, ombre warm subtile
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        // Fond blanc (pas surface cream) pour contraste sur fond #fff8f6
        "rounded-2xl border border-[#857370]/20 bg-white shadow-sm",
        "transition-all duration-300",
        "hover:shadow-md hover:scale-[1.01]",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";

// Header de card — zone titre
const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col gap-1 p-5 pb-0", className)}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

// Titre de card — Noto Serif
const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, children, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-serif text-xl font-semibold leading-tight text-[#201a19]",
      className,
    )}
    {...props}
  >
    {children}
  </h3>
));
CardTitle.displayName = "CardTitle";

// Description de card
const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-[#857370]", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

// Contenu de card
const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-5 pt-3", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

// Footer de card — zone actions
const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-center gap-3 border-t border-[#857370]/20 p-5 pt-4", className)}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle };
