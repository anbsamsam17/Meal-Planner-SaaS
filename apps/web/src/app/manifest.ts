// apps/web/src/app/manifest.ts
// PWA manifest — Next.js 14 Metadata API
// Référence : phase-0/design-system/02-design-tokens.md (couleur terracotta)
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Presto — Le livre de recettes de votre famille",
    short_name: "Presto",
    description:
      "Le livre de recettes de votre famille, réinventé par Presto.",
    start_url: "/dashboard",
    display: "standalone",
    orientation: "portrait",
    // Terracotta-500 comme couleur de thème de l'app
    background_color: "#FDFAF6", // neutral-50 — fond de page
    theme_color: "#D9613A", // primary-500 — terracotta
    categories: ["food", "lifestyle", "utilities"],
    lang: "fr",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
    shortcuts: [
      {
        name: "Mon planning",
        short_name: "Planning",
        description: "Voir le planning de la semaine",
        url: "/dashboard",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "Ma liste de courses",
        short_name: "Courses",
        description: "Voir ma liste de courses",
        url: "/shopping",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
    ],
    screenshots: [
      {
        src: "/screenshot-mobile.png",
        sizes: "390x844",
        type: "image/png",
        // @ts-expect-error -- form_factor non encore typé dans MetadataRoute.Manifest
        form_factor: "narrow",
        label: "Planning de la semaine sur mobile",
      },
    ],
  };
}
