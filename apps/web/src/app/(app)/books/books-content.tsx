"use client";
// apps/web/src/app/(app)/books/books-content.tsx
// Contenu interactif de la page livres PDF — Client Component
// Phase 2 — liste, génération, gating plan Famille

import { useState } from "react";
import { BookOpen, Plus } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPlansHistory, generateBook } from "@/lib/api/endpoints";
import type { BookInfo } from "@/lib/api/types";
import { BookCard } from "@/components/book/book-card";
import { UpgradeGate } from "@/components/billing/upgrade-gate";
import { toast } from "sonner";

function BooksListContent() {
  const queryClient = useQueryClient();
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(new Set());

  const { data: books = [], isLoading } = useQuery<BookInfo[], Error>({
    queryKey: ["books", "history"],
    queryFn: getPlansHistory,
    staleTime: 2 * 60 * 1000,
  });

  const generateMutation = useMutation({
    mutationFn: (planId: string) => generateBook(planId),
    onMutate: (planId) => {
      setGeneratingIds((prev) => new Set([...prev, planId]));
    },
    onSuccess: (_data, planId) => {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(planId);
        return next;
      });
      void queryClient.invalidateQueries({ queryKey: ["books", "history"] });
      toast.success("Génération lancée !", {
        description: "Votre livre sera disponible dans quelques instants.",
      });
    },
    onError: (err: Error, planId) => {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(planId);
        return next;
      });
      toast.error("Impossible de générer le livre", { description: err.message });
    },
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-300 border-t-primary-600" />
      </div>
    );
  }

  // Aucun livre : état vide
  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-white py-16 text-center">
        <BookOpen className="mb-4 h-12 w-12 text-neutral-300" aria-hidden />
        <p className="mb-1 text-sm font-semibold text-neutral-700">
          Aucun livre de recettes pour l&apos;instant
        </p>
        <p className="mb-6 max-w-xs text-xs text-neutral-500">
          Générez votre premier livre PDF depuis un plan hebdomadaire validé.
        </p>
        <p className="text-xs text-neutral-400">
          Validez d&apos;abord un plan dans{" "}
          <a href="/dashboard" className="text-primary-600 underline">
            Ma semaine
          </a>{" "}
          pour débloquer la génération.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-3" role="list">
      {books.map((book) => (
        <li key={book.id}>
          <BookCard
            book={book}
            onRegenerate={(planId) => generateMutation.mutate(planId)}
            isRegenerating={generatingIds.has(book.plan_id)}
          />
        </li>
      ))}
    </ul>
  );
}

export function BooksContent() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* En-tête */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Mes livres de recettes</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Téléchargez vos plans de repas en PDF pour cuisiner sans internet.
          </p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
          <Plus className="h-5 w-5 text-primary-600" aria-hidden />
        </div>
      </div>

      {/* Feature gate plan Famille */}
      <UpgradeGate
        requiredPlan="famille"
        featureLabel="Livres PDF hebdomadaires"
        blurChildren
      >
        <BooksListContent />
      </UpgradeGate>
    </div>
  );
}
