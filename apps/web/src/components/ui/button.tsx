// apps/web/src/components/ui/button.tsx
// Composant Button — design premium Presto
// Fond primary #E2725B, rounded-xl, shadow-sm, transition 300ms
// Touch target min 44px, focus ring terracotta, variants CVA
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "font-sans font-semibold",
    // Premium : rounded-xl partout
    "rounded-xl",
    "transition-all duration-300",
    // Focus ring terracotta (WCAG 2.4.11)
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2",
    // Disabled state
    "disabled:cursor-not-allowed disabled:opacity-40",
    // Active press feedback
    "active:scale-95",
    // Touch target minimum (WCAG 2.5.5)
    "min-h-[44px]",
  ].join(" "),
  {
    variants: {
      variant: {
        // Fond terracotta #E2725B, texte blanc — action principale
        primary: [
          "bg-[#E2725B] text-white",
          "hover:bg-[hsl(14,72%,46%)]",
          // Ombre warm premium
          "shadow-sm hover:shadow-md",
        ].join(" "),
        // Fond olive-100, texte olive-700 — action secondaire
        secondary: [
          "bg-secondary-100 text-secondary-700 border border-secondary-300",
          "hover:bg-secondary-200",
        ].join(" "),
        // Sans fond, texte on-surface — action contextuelle
        ghost: [
          "bg-transparent text-[#201a19]",
          "hover:bg-[#fff8f6] hover:text-[#201a19]",
        ].join(" "),
        // Bordure outline warm — action neutre
        outline: [
          "bg-transparent text-[#201a19] border border-[#857370]/30",
          "hover:bg-[#fff8f6] hover:border-[#857370]",
        ].join(" "),
        // Fond error — suppression
        destructive: [
          "bg-error-500 text-error-foreground",
          "hover:bg-error-700",
          "shadow-sm",
        ].join(" "),
        // Lien textuel
        link: [
          "bg-transparent text-[#E2725B] underline-offset-4",
          "hover:underline hover:text-[hsl(14,72%,46%)]",
          "min-h-0",
        ].join(" "),
      },
      size: {
        sm: "h-8 min-h-8 px-3 py-1 text-xs",
        md: "h-10 min-h-[44px] px-4 py-2 text-sm",
        lg: "h-12 min-h-[44px] px-5 py-3 text-base",
        xl: "h-14 min-h-[56px] px-8 py-4 text-lg",
        icon: "h-11 w-11 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, isLoading = false, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled ?? isLoading}
        aria-busy={isLoading ? true : undefined}
        {...props}
      >
        {isLoading ? (
          <>
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Chargement...</span>
          </>
        ) : (
          children
        )}
      </Comp>
    );
  },
);

Button.displayName = "Button";

export { Button, buttonVariants };
