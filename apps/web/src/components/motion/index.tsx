// apps/web/src/components/motion/index.tsx
// FIX Phase 1 (review 2026-04-12) : dynamic import framer-motion pour réduire le bundle initial
// Objectif : passer de ~174 KB gzip à <150 KB gzip (HIGH-3 performance-audit)
//
// RÈGLE D'USAGE (à respecter par tous les développeurs) :
// - Importer depuis "@/components/motion" et PAS depuis "framer-motion" directement
//   pour les composants hors above-the-fold (cartes recettes, listes, modales, etc.)
// - "ssr: false" → les animations ne sont PAS rendues côté serveur (acceptable pour les
//   éléments sous le fold qui ne sont pas indexés pour le SEO)
// - Pour les animations ABOVE-THE-FOLD critiques (hero, onboarding step 1), importer
//   directement depuis "framer-motion" (bundle chargé de toute façon côté client)
//
// Composants exposés :
// - MotionDiv     → <motion.div> avec dynamic import
// - MotionSection → <motion.section> avec dynamic import
// - MotionUl      → <motion.ul> avec dynamic import
// - MotionLi      → <motion.li> avec dynamic import
// - MotionSpan    → <motion.span> avec dynamic import
// - MotionButton  → <motion.button> avec dynamic import
// - AnimatePresence → pour les transitions de montage/démontage
"use client";

import dynamic from "next/dynamic";
import type { HTMLMotionProps, AnimatePresenceProps } from "framer-motion";
import type { ReactNode } from "react";

// --- MotionDiv ---
// Usage : <MotionDiv initial={{ opacity: 0 }} animate={{ opacity: 1 }}>...</MotionDiv>
export const MotionDiv = dynamic<HTMLMotionProps<"div">>(
  () => import("framer-motion").then((mod) => mod.motion.div),
  {
    ssr: false,
    // Pas de loading skeleton — l'élément s'affiche normalement sans animation pendant l'hydratation
    loading: () => null,
  },
);

// --- MotionSection ---
export const MotionSection = dynamic<HTMLMotionProps<"section">>(
  () => import("framer-motion").then((mod) => mod.motion.section),
  { ssr: false, loading: () => null },
);

// --- MotionUl ---
export const MotionUl = dynamic<HTMLMotionProps<"ul">>(
  () => import("framer-motion").then((mod) => mod.motion.ul),
  { ssr: false, loading: () => null },
);

// --- MotionLi ---
export const MotionLi = dynamic<HTMLMotionProps<"li">>(
  () => import("framer-motion").then((mod) => mod.motion.li),
  { ssr: false, loading: () => null },
);

// --- MotionSpan ---
export const MotionSpan = dynamic<HTMLMotionProps<"span">>(
  () => import("framer-motion").then((mod) => mod.motion.span),
  { ssr: false, loading: () => null },
);

// --- MotionButton ---
export const MotionButton = dynamic<HTMLMotionProps<"button">>(
  () => import("framer-motion").then((mod) => mod.motion.button),
  { ssr: false, loading: () => null },
);

// --- MotionArticle ---
export const MotionArticle = dynamic<HTMLMotionProps<"article">>(
  () => import("framer-motion").then((mod) => mod.motion.article),
  { ssr: false, loading: () => null },
);

// --- AnimatePresence ---
// Composant de transition montage/démontage — nécessite aussi un import dynamique
export const AnimatePresence = dynamic<AnimatePresenceProps & { children?: ReactNode }>(
  () => import("framer-motion").then((mod) => mod.AnimatePresence),
  { ssr: false, loading: () => null },
);

// --- Hooks Framer Motion (re-exports) ---
// Pour les composants qui ont besoin de useMotionValue, useTransform, animate
// On les re-exporte depuis ce module pour centraliser l'import
export { useMotionValue, useTransform, animate } from "framer-motion";
