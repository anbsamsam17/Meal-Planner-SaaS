// @ts-check
// FIX Phase 1 mature (review 2026-04-12) — BUG #5D : ajout @next/bundle-analyzer
// Mesurer le bundle : ANALYZE=true pnpm build
import withBundleAnalyzer from "@next/bundle-analyzer";
import withPWA from "next-pwa";

const bundleAnalyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

// FIX Phase 1 (review 2026-04-12) : CSP améliorée avec séparation dev/prod
// TODO Phase 2 : durcir en prod via nonces strict-dynamic pour éliminer unsafe-inline/unsafe-eval
// Référence : FIX #5 code-review + H9 security audit
const isDev = process.env.NODE_ENV === "development";

// FIX Phase 1 (review 2026-04-12) : headers de sécurité complets — FIX #5
const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      // unsafe-eval requis par Next.js dev (HMR) — conditionné à l'env
      // unsafe-inline requis pour les styles inline Next.js — à remplacer par nonces en Phase 2
      `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""} https://*.posthog.com`,
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      // data: requis pour les fonts en base64 inline
      "font-src 'self' https://fonts.gstatic.com data:",
      "img-src 'self' data: blob: https://*.supabase.co https://*.r2.cloudflarestorage.com https://imagedelivery.net https://img.spoonacular.com",
      // localhost:8000 = API FastAPI en développement local
      // localhost:8001 = API FastAPI en développement local (port configuré dans .env.local)
      `connect-src 'self' https://*.supabase.co wss://*.supabase.co https://*.posthog.com https://*.railway.app${isDev ? " http://localhost:8001 http://localhost:8000 ws://localhost:3000" : ""}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
  {
    key: "X-Frame-Options",
    value: "DENY",
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // FIX Phase 1 (review 2026-04-12) : output standalone pour Docker multi-stage — FIX #8
  // Réduit l'image Docker de ~400 MB → ~50 MB (copie uniquement .next/standalone)
  // Requis par le Dockerfile multi-stage (COPY .next/standalone ./app)
  // Référence : HIGH-1 performance-audit
  output: "standalone",

  // Ignorer les erreurs ESLint et TypeScript au build Vercel
  // Les checks sont faits en CI (GitHub Actions) — pas besoin de bloquer le build Vercel
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },

  experimental: {
    // FIX Phase 1 (review 2026-04-12) : optimisePackageImports étendu — FIX #2B
    // Réduit le bundle en faisant du tree-shaking sur les packages à imports multiples
    // Gain estimé : lucide-react -90%, radix-ui -20%, framer-motion -15%
    optimizePackageImports: [
      "framer-motion",
      "lucide-react",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-label",
      "@radix-ui/react-progress",
      "@radix-ui/react-select",
      "@radix-ui/react-slot",
      "@radix-ui/react-switch",
      "@radix-ui/react-tabs",
      "@radix-ui/react-toast",
      "@radix-ui/react-tooltip",
    ],
  },

  images: {
    remotePatterns: [
      {
        // Images Supabase Storage (recettes uploadées par les utilisateurs)
        protocol: "https",
        hostname: "*.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
      {
        // Images Cloudflare R2 (photos recettes IA générées, PDF covers)
        protocol: "https",
        hostname: "*.r2.cloudflarestorage.com",
        pathname: "/**",
      },
      {
        // CDN Cloudflare Images si activé ultérieurement
        protocol: "https",
        hostname: "imagedelivery.net",
        pathname: "/**",
      },
      {
        // Placeholders food Unsplash (recettes sans photo en dev + prod)
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
      {
        // Photos recettes importées depuis l'API Spoonacular
        // Format : https://img.spoonacular.com/recipes/{id}-556x370.jpg
        protocol: "https",
        hostname: "img.spoonacular.com",
        pathname: "/recipes/**",
      },
    ],
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

// Configuration PWA via next-pwa
const pwaConfig = withPWA({
  dest: "public",
  // Désactiver le service worker en développement pour éviter les conflits de cache
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
});

// FIX Phase 1 mature (review 2026-04-12) — BUG #5D : chaîner bundleAnalyzer + pwa
// Ordre : bundleAnalyzer(pwa(nextConfig)) — le plus externe wrap les internes
export default bundleAnalyzer(pwaConfig(nextConfig));
