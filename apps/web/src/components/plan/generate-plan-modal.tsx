// apps/web/src/components/plan/generate-plan-modal.tsx
// Modal "4 questions" avant generation du planning
// Questions : temps de preparation, budget, style, envie
// Design premium : fond cream, chips terracotta actifs, titre Noto Serif
// Mobile-first, max-w-lg centre
"use client";

import { useState, useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types filtres ---

export interface GenerateFilters {
  max_time: number | null;
  budget: string | null;
  style: string | null;
}

// --- Options pour chaque question ---

interface ChipOption<T> {
  label: string;
  value: T;
}

const TIME_OPTIONS: ChipOption<number | null>[] = [
  { label: "Express (< 20 min)", value: 20 },
  { label: "Rapide (< 30 min)", value: 30 },
  { label: "Normal (< 45 min)", value: 45 },
  { label: "Pas de limite", value: null },
];

const BUDGET_OPTIONS: ChipOption<string | null>[] = [
  { label: "Economique", value: "economique" },
  { label: "Moyen", value: null },
  { label: "Premium", value: "premium" },
];

const STYLE_OPTIONS: ChipOption<string | null>[] = [
  { label: "Gourmand", value: "gourmand" },
  { label: "Leger & healthy", value: "leger" },
  { label: "Proteine", value: "proteine" },
  { label: "Vegetarien", value: "vegetarien" },
];

const ENVIE_OPTIONS: ChipOption<string | null>[] = [
  { label: "Surprise moi !", value: null },
  { label: "Cuisine francaise", value: "francaise" },
  { label: "Cuisine du monde", value: "monde" },
];

// --- Composant Chip selectable ---

interface ChipGroupProps<T> {
  options: ChipOption<T>[];
  selected: T;
  onChange: (value: T) => void;
}

function ChipGroup<T>({ options, selected, onChange }: ChipGroupProps<T>) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = option.value === selected;
        return (
          <button
            key={String(option.value ?? "null")}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              "rounded-full px-4 py-2 text-sm font-medium transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2",
              "min-h-[40px]",
              isActive
                ? "bg-[#E2725B] text-white shadow-sm"
                : "bg-white text-[#857370] border border-[#857370]/20 hover:border-[#E2725B]/40 hover:bg-[#E2725B]/5",
            )}
            aria-pressed={isActive}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

// --- Question avec titre ---

interface QuestionBlockProps {
  number: number;
  title: string;
  children: React.ReactNode;
}

function QuestionBlock({ number, title, children }: QuestionBlockProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#E2725B]/10 text-xs font-bold text-[#E2725B]">
          {number}
        </span>
        <h3 className="font-serif text-base font-semibold text-[#201a19]">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

// --- Modal principal ---

interface GeneratePlanModalProps {
  open: boolean;
  onClose: () => void;
  onGenerate: (filters: GenerateFilters) => void;
  isGenerating?: boolean;
}

export function GeneratePlanModal({
  open,
  onClose,
  onGenerate,
  isGenerating = false,
}: GeneratePlanModalProps) {
  const [maxTime, setMaxTime] = useState<number | null>(45);
  const [budget, setBudget] = useState<string | null>(null);
  const [style, setStyle] = useState<string | null>(null);
  // Envie est informatif pour le futur, pas envoye a l'API
  const [envie, setEnvie] = useState<string | null>(null);

  const handleGenerate = useCallback(() => {
    onGenerate({
      max_time: maxTime,
      budget,
      style,
    });
  }, [maxTime, budget, style, onGenerate]);

  return (
    <Dialog.Root open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <Dialog.Portal>
        {/* Overlay */}
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />

        {/* Content */}
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2",
            "max-h-[90vh] overflow-y-auto",
            "rounded-2xl bg-[#fff8f6] p-6 shadow-xl",
            "focus:outline-none",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
            "data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]",
            "data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
          )}
          aria-describedby="generate-modal-description"
        >
          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div>
              <Dialog.Title className="font-serif text-xl font-bold text-[#201a19]">
                Personnalisez votre semaine
              </Dialog.Title>
              <p
                id="generate-modal-description"
                className="mt-1 text-sm text-[#857370]"
              >
                4 questions rapides pour un planning sur mesure
              </p>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="flex h-8 w-8 items-center justify-center rounded-full text-[#857370] transition-colors hover:bg-[#857370]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]"
                aria-label="Fermer"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* Questions */}
          <div className="space-y-6">
            <QuestionBlock number={1} title="Temps de preparation">
              <ChipGroup
                options={TIME_OPTIONS}
                selected={maxTime}
                onChange={setMaxTime}
              />
            </QuestionBlock>

            <QuestionBlock number={2} title="Budget">
              <ChipGroup
                options={BUDGET_OPTIONS}
                selected={budget}
                onChange={setBudget}
              />
            </QuestionBlock>

            <QuestionBlock number={3} title="Style">
              <ChipGroup
                options={STYLE_OPTIONS}
                selected={style}
                onChange={setStyle}
              />
            </QuestionBlock>

            <QuestionBlock number={4} title="Envie">
              <ChipGroup
                options={ENVIE_OPTIONS}
                selected={envie}
                onChange={setEnvie}
              />
            </QuestionBlock>
          </div>

          {/* Bouton generer */}
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isGenerating}
            aria-busy={isGenerating}
            className={cn(
              "mt-8 flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3.5",
              "min-h-[48px] text-base font-semibold text-white",
              "bg-[#E2725B] shadow-sm transition-all duration-200",
              "hover:bg-[hsl(14,72%,46%)] hover:shadow-md",
              "active:scale-[0.98]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            {isGenerating ? (
              <>
                <svg
                  className="h-5 w-5 animate-spin"
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
                Generation en cours...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5" aria-hidden="true" />
                Generer mon planning
              </>
            )}
          </button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
