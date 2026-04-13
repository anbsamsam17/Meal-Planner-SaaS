// apps/web/src/components/ui/progress.tsx
// Composant Progress — barres de progression onboarding et nutrition
// Référence : phase-0/design-system/04-components-catalog.md #15 Progress
// Basé sur Radix UI Progress (accessibilité ARIA complète)
"use client";

import * as React from "react";
import * as RadixProgress from "@radix-ui/react-progress";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const progressVariants = cva(
  "relative overflow-hidden rounded-full bg-neutral-200",
  {
    variants: {
      size: {
        sm: "h-1", // 4px
        md: "h-2", // 8px
        lg: "h-3", // 12px
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

const indicatorVariants = cva(
  "h-full w-full flex-1 origin-left rounded-full transition-transform duration-slow ease-out",
  {
    variants: {
      color: {
        primary: "bg-primary-500",
        success: "bg-success-500",
        warning: "bg-warning-500",
      },
    },
    defaultVariants: {
      color: "primary",
    },
  },
);

export interface ProgressProps
  extends Omit<React.ComponentPropsWithoutRef<typeof RadixProgress.Root>, "color">,
    VariantProps<typeof progressVariants>,
    VariantProps<typeof indicatorVariants> {
  value?: number;
  "aria-label"?: string;
}

const Progress = React.forwardRef<
  React.ElementRef<typeof RadixProgress.Root>,
  ProgressProps
>(({ className, value = 0, size, color, "aria-label": ariaLabel, ...props }, ref) => (
  <RadixProgress.Root
    ref={ref}
    className={cn(progressVariants({ size }), className)}
    value={value}
    aria-label={ariaLabel ?? `Progression : ${value}%`}
    {...props}
  >
    <RadixProgress.Indicator
      className={cn(indicatorVariants({ color }))}
      style={{ transform: `translateX(-${100 - value}%)` }}
    />
  </RadixProgress.Root>
));

Progress.displayName = RadixProgress.Root.displayName;

export { Progress };
