"use client";
// apps/web/src/components/book/book-card.tsx
// Card affichant un livre PDF hebdomadaire
// Phase 2 — statut, téléchargement, régénération

import { BookOpen, Download, RefreshCw, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { BookInfo, BookStatus } from "@/lib/api/types";

interface StatusConfig {
  label: string;
  color: string;
  icon: typeof AlertCircle;
}

const STATUS_CONFIGS: Record<BookStatus, StatusConfig> = {
  available: {
    label: "Disponible",
    color: "text-green-700 bg-green-100",
    icon: Download,
  },
  generating: {
    label: "En cours...",
    color: "text-amber-700 bg-amber-100",
    icon: Clock,
  },
  error: {
    label: "Erreur",
    color: "text-red-700 bg-red-100",
    icon: AlertCircle,
  },
  not_generated: {
    label: "Non généré",
    color: "text-neutral-600 bg-neutral-100",
    icon: BookOpen,
  },
};

function formatWeekDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

interface BookCardProps {
  book: BookInfo;
  onRegenerate?: (planId: string) => void;
  isRegenerating?: boolean;
}

export function BookCard({ book, onRegenerate, isRegenerating }: BookCardProps) {
  const config = STATUS_CONFIGS[book.status];
  const StatusIcon = config.icon;

  return (
    <article className="flex items-center gap-4 rounded-xl border border-neutral-200 bg-white px-4 py-4 shadow-sm transition-shadow hover:shadow-md">
      {/* Icône livre */}
      <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-primary-100">
        <BookOpen className="h-6 w-6 text-primary-600" aria-hidden />
      </div>

      {/* Contenu */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-neutral-900">
          Semaine du {formatWeekDate(book.week_start_date)}
        </p>
        {book.generated_at && (
          <p className="text-xs text-neutral-400">
            Généré le{" "}
            {new Date(book.generated_at).toLocaleDateString("fr-FR", {
              day: "numeric",
              month: "short",
            })}
          </p>
        )}
        {book.page_count != null && (
          <p className="text-xs text-neutral-400">{book.page_count} pages</p>
        )}
      </div>

      {/* Badge statut */}
      <span
        className={cn(
          "inline-flex flex-shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
          config.color,
        )}
        aria-label={`Statut : ${config.label}`}
      >
        <StatusIcon className="h-3 w-3" aria-hidden />
        {config.label}
      </span>

      {/* Actions */}
      <div className="flex flex-shrink-0 items-center gap-2">
        {/* Télécharger PDF */}
        {book.status === "available" && book.pdf_url && (
          <a
            href={book.pdf_url}
            download
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Télécharger le PDF"
          >
            <Download className="h-4 w-4" aria-hidden />
          </a>
        )}

        {/* Régénérer */}
        {onRegenerate && book.status !== "generating" && (
          <button
            type="button"
            onClick={() => onRegenerate(book.plan_id)}
            disabled={isRegenerating}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50"
            aria-label="Régénérer le PDF"
          >
            <RefreshCw
              className={cn("h-4 w-4", isRegenerating && "animate-spin")}
              aria-hidden
            />
          </button>
        )}
      </div>
    </article>
  );
}
