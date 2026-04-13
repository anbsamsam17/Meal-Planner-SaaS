// apps/web/src/app/fonts.ts
// Design premium — Noto Serif remplace Fraunces (titres h1/h2)
// Inter conservé pour le corps UI
// OPT-8 (review 2026-04-12) : chargement optimisé via next/font pour éviter CLS > 0.1
import { Inter, Noto_Serif, JetBrains_Mono } from "next/font/google";

// Font display éditorial — utilisée sur les h1/h2 above-the-fold → preload obligatoire
// Remplace Fraunces — Noto Serif : serif contemporain, excellent rendu food editorial
export const notoSerif = Noto_Serif({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  preload: true,
  variable: "--font-serif",
  weight: ["400", "700"],
  style: ["normal", "italic"],
});

// Font corps UI — utilisée partout → preload critique (impact CLS maximal)
export const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  preload: true,
  variable: "--font-inter",
});

// Font mono — données nutritionnelles, quantités — pas de preload (non above-the-fold)
export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  preload: false,
  variable: "--font-mono",
});
