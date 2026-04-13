// apps/web/src/components/ui/input.tsx
// Composant Input — design premium Presto
// Border warm #857370/30, focus ring primary/20, rounded-xl, fond blanc
// Touch target 44px minimum, accessibilité maintenue
import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  errorMessage?: string;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
  inputVariant?: "default" | "filled" | "underline";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = "text",
      label,
      helperText,
      errorMessage,
      leadingIcon,
      trailingIcon,
      inputVariant = "default",
      id,
      ...props
    },
    ref,
  ) => {
    const generatedId = React.useId();
    const inputId = id ?? `input-${generatedId}`;
    const helperId = helperText ? `${inputId}-helper` : undefined;
    const errorId = errorMessage ? `${inputId}-error` : undefined;

    const hasError = Boolean(errorMessage);

    const inputBaseClasses = [
      // Fond blanc + texte on-surface
      "w-full rounded-xl bg-white text-[#201a19]",
      "text-sm placeholder:text-[#857370]",
      "transition-all duration-300",
      "focus:outline-none",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "min-h-[44px]",
    ];

    const variantClasses = {
      default: [
        // Border warm outline/30 — focus ring primary/20
        "border border-[#857370]/30 px-3 py-2",
        hasError
          ? "border-error-500 focus:border-error-500 focus:ring-2 focus:ring-error-100"
          : "focus:border-[#E2725B] focus:ring-2 focus:ring-[#E2725B]/20",
      ].join(" "),
      filled: [
        "border-0 border-b-2 border-[#857370]/30 bg-[#fff8f6] px-3 py-2",
        hasError
          ? "border-b-error-500 focus:border-b-error-500"
          : "focus:border-b-[#E2725B] focus:bg-white",
      ].join(" "),
      underline: [
        "border-0 border-b-2 border-[#857370]/30 bg-transparent rounded-none px-0 py-2",
        hasError
          ? "border-b-error-500"
          : "focus:border-b-[#E2725B]",
      ].join(" "),
    };

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-[#201a19]"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leadingIcon && (
            <div
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#857370]"
              aria-hidden="true"
            >
              {leadingIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            type={type}
            className={cn(
              inputBaseClasses,
              variantClasses[inputVariant],
              leadingIcon && "pl-9",
              trailingIcon && "pr-9",
              className,
            )}
            aria-invalid={hasError ? true : undefined}
            aria-describedby={
              [helperId, errorId].filter(Boolean).join(" ") || undefined
            }
            {...props}
          />

          {trailingIcon && (
            <div
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#857370]"
              aria-hidden="true"
            >
              {trailingIcon}
            </div>
          )}
        </div>

        {helperText && !errorMessage && (
          <p id={helperId} className="text-xs text-[#857370]">
            {helperText}
          </p>
        )}

        {errorMessage && (
          <p id={errorId} className="text-xs text-error-500" role="alert">
            {errorMessage}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

export { Input };
