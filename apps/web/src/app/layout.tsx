// apps/web/src/app/layout.tsx
// Root layout RSC — Server Component (pas de "use client")
// Design premium — Noto Serif + Inter
// Voir phase-0/design-system/02-design-tokens.md section "Font loading strategy"
import type { Metadata, Viewport } from "next";
import { notoSerif, inter, jetbrainsMono } from "./fonts";
import "./globals.css";
import { RootProviders } from "@/components/providers/root-providers";

// Métadonnées SEO — Metadata API Next.js 14
export const metadata: Metadata = {
  title: {
    default: "Presto — Le livre de recettes de votre famille",
    template: "%s — Presto",
  },
  description:
    "Le livre de recettes de votre famille, réinventé par Presto. Drive intégré, livre PDF hebdomadaire, mode anti-gaspi.",
  keywords: [
    "planificateur repas",
    "meal planning",
    "recettes familles",
    "liste de courses",
    "drive leclerc",
    "anti-gaspi",
  ],
  authors: [{ name: "Presto" }],
  creator: "Presto",
  publisher: "Presto",
  // Open Graph — prévisualisation réseaux sociaux
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: "https://presto.app",
    siteName: "Presto",
    title: "Presto — Le livre de recettes de votre famille",
    description:
      "Presto apprend les goûts de votre famille et réinvente votre livre de recettes.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Presto — Le livre de recettes de votre famille, réinventé par Presto",
      },
    ],
  },
  // Twitter Card
  twitter: {
    card: "summary_large_image",
    title: "Presto — Le livre de recettes de votre famille",
    description:
      "Presto apprend les goûts de votre famille et réinvente votre livre de recettes.",
    images: ["/og-image.png"],
  },
  // PWA — icônes
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180" },
      { url: "/logo.png", sizes: "180x180" },
    ],
  },
  manifest: "/manifest.json",
  // Robots — indexable en production, pas en dev
  robots: {
    index: process.env.NODE_ENV === "production",
    follow: process.env.NODE_ENV === "production",
  },
};

// Viewport — mobile-first + PWA safe areas
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // viewport-fit=cover nécessaire pour les safe areas iOS (PWA)
  viewportFit: "cover",
  themeColor: [
    // Thème clair : terracotta
    { media: "(prefers-color-scheme: light)", color: "#E2725B" },
    // Thème sombre : brun sombre
    { media: "(prefers-color-scheme: dark)", color: "hsl(28, 15%, 9%)" },
  ],
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    // Les trois CSS variables sont injectées sur <html> → disponibles dans tout le DOM
    // --font-serif (Noto Serif), --font-inter, --font-mono
    <html
      lang="fr"
      className={`${notoSerif.variable} ${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning // Nécessaire pour le script anti-FOUC du dark mode
    >
      <head>
        {/*
          Script anti-FOUC pour le dark mode class-based.
          Doit être inline et synchrone pour s'exécuter avant le premier paint.
          Évite le flash de thème clair si l'utilisateur préfère le dark mode.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('presto-theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  // Activer dark si : préférence sauvegardée = 'dark', ou préférence système et pas de préférence sauvegardée
                  if (theme === 'dark' || (!theme && prefersDark)) {
                    document.documentElement.classList.add('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
