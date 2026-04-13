// tailwind.config.ts — MealPlanner SaaS
// Copié depuis phase-0/design-system/03-tailwind-config.ts
// Content adapté pour pointer sur ./src/**/*.{ts,tsx,mdx}
// npm install -D @tailwindcss/typography @tailwindcss/forms

import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";
// FIX #3 (review 2026-04-12) : remplacer require() CJS par des imports ESM pour cohérence
// avec import type { Config } en haut du fichier — évite l'erreur "require is not defined"
// dans les contextes ESM stricts (tsconfig moduleResolution: bundler / node16)
import typography from "@tailwindcss/typography";
import forms from "@tailwindcss/forms";

const config: Config = {
  // Dark mode via classe CSS (contrôlé par le hook useTimeBasedTheme)
  darkMode: "class",

  // Chemins de scan pour purge CSS — Next.js 14 App Router
  // FIX #2 (review 2026-04-12) : ajout du path monorepo packages/** pour éviter
  // que les classes Tailwind émises par les packages partagés soient purgées en production
  content: [
    "./src/**/*.{ts,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx,mdx}",
    // shadcn/ui components
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    // Packages partagés du monorepo pnpm (packages/ui, packages/shared, etc.)
    "../../packages/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    // FIX #1 (review 2026-04-12) : REFACTOR CRITIQUE — theme.extend au lieu de theme racine
    // Avant ce fix : screens, fontFamily, fontSize, spacing, borderRadius étaient définis
    // au niveau theme: { ... }, ce qui ÉCRASAIT entièrement les valeurs par défaut Tailwind.
    // Conséquence silencieuse : max-w-screen-xl, container, text-gray-*, prose, etc. cassés.
    // Règle : tout ce qui AJOUTE à Tailwind → extend. Tout remplacement intentionnel → racine.
    // Dans notre cas, tout passe en extend pour fusionner avec les défauts Tailwind.
    extend: {
      // -----------------------------------------------------------------------
      // BREAKPOINTS — Mobile-first (extend pour fusionner avec les défauts Tailwind)
      // Note : si on voulait REMPLACER les breakpoints natifs, on les mettrait en racine.
      // Ici on étend, donc sm/md/lg/xl/2xl natifs Tailwind sont préservés en plus de ces valeurs.
      // -----------------------------------------------------------------------
      screens: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1536px",
      },

      // -----------------------------------------------------------------------
      // TYPOGRAPHIE — Noto Serif + Inter via CSS variables (next/font)
      // OPT-8 (review 2026-04-12) : utiliser des CSS variables plutôt que les noms de font
      // directs → pas de saut de layout entre le fallback et la vraie font chargée par next/font
      // Voir section "Font loading strategy" dans 02-design-tokens.md
      // -----------------------------------------------------------------------
      fontFamily: {
        // Serif éditorial — Noto Serif (remplace Fraunces) — titres h1/h2, accents food
        // La variable --font-serif est injectée par next/font dans le layout root
        serif: ["var(--font-serif)", "Georgia", "serif", ...fontFamily.serif],
        // Alias display → pointe sur serif pour compatibilité avec l'existant
        display: ["var(--font-serif)", "Georgia", "serif", ...fontFamily.serif],
        // Corps UI (tout le reste) — Inter
        // La variable --font-inter est injectée par next/font dans le layout root
        sans: ["var(--font-inter)", "system-ui", "sans-serif", ...fontFamily.sans],
        // Données numériques (nutritionnel, quantités)
        mono: ["var(--font-mono)", "ui-monospace", ...fontFamily.mono],
      },

      // -----------------------------------------------------------------------
      // FONT SIZE — Échelle typographique étendue (s'ajoute aux tailles Tailwind natives)
      // -----------------------------------------------------------------------
      fontSize: {
        // Micro (2xs non présent dans Tailwind natif)
        "2xs": ["10px", { lineHeight: "1.4", letterSpacing: "0.02em" }],
        xs: ["12px", { lineHeight: "1.5", letterSpacing: "0.01em" }],
        sm: ["14px", { lineHeight: "1.6" }],
        // Corps
        base: ["16px", { lineHeight: "1.65" }],
        lg: ["18px", { lineHeight: "1.7" }],
        xl: ["20px", { lineHeight: "1.5" }],
        // Headings UI
        "2xl": ["24px", { lineHeight: "1.3" }],
        "3xl": ["28px", { lineHeight: "1.25" }],
        "4xl": ["32px", { lineHeight: "1.2" }],
        "5xl": ["40px", { lineHeight: "1.15" }],
        // Display éditorial
        "6xl": ["48px", { lineHeight: "1.1" }],
        "7xl": ["56px", { lineHeight: "1.05" }],
        "8xl": ["64px", { lineHeight: "1.02" }],
        "9xl": ["72px", { lineHeight: "1.0" }],
      },

      // -----------------------------------------------------------------------
      // ESPACEMENTS — Base 4px (extend préserve tous les spacings Tailwind natifs)
      // -----------------------------------------------------------------------
      spacing: {
        px: "1px",
        0: "0px",
        0.5: "2px",
        1: "4px",
        1.5: "6px",
        2: "8px",
        2.5: "10px",
        3: "12px",
        3.5: "14px",
        4: "16px",
        5: "20px",
        6: "24px",
        7: "28px",
        8: "32px",
        9: "36px",
        10: "40px",
        11: "44px",
        12: "48px",
        14: "56px",
        16: "64px",
        20: "80px",
        24: "96px",
        28: "112px",
        32: "128px",
        36: "144px",
        40: "160px",
        44: "176px",
        48: "192px",
        52: "208px",
        56: "224px",
        60: "240px",
        64: "256px",
        72: "288px",
        80: "320px",
        96: "384px",
      },

      // -----------------------------------------------------------------------
      // BORDER RADIUS (extend préserve rounded-full, rounded natif, etc.)
      // -----------------------------------------------------------------------
      borderRadius: {
        none: "0px",
        sm: "4px",
        DEFAULT: "8px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "24px",
        "3xl": "32px",
        full: "9999px",
      },
      // -----------------------------------------------------------------------
      // COULEURS — Palette complète warm food-friendly
      // Valeurs en HSL : hsl(hue saturation% lightness%)
      // -----------------------------------------------------------------------
      colors: {
        // --- TOKENS PREMIUM — design food premium ---
        surface: "#fff8f6",          // fond warm cream
        "on-surface": "#201a19",     // texte quasi-noir chaud
        outline: "#857370",          // bordures warm subtiles

        // --- PRIMARY — Terracotta #E2725B ---
        primary: {
          50: "#fff8f6",
          100: "hsl(14, 90%, 93%)",   // #FFE4D9
          200: "hsl(14, 85%, 85%)",   // #FFCBB5
          300: "hsl(14, 80%, 75%)",   // #FFA98A
          400: "hsl(14, 78%, 65%)",   // #F08060
          500: "#E2725B",             // terracotta — couleur principale
          600: "hsl(14, 72%, 46%)",   // hover darken 10%
          700: "hsl(14, 70%, 37%)",   // #943D23
          800: "hsl(14, 68%, 28%)",   // #702E1A
          900: "hsl(14, 65%, 18%)",   // #4A1D10
          DEFAULT: "#E2725B",
          foreground: "#ffffff",
        },

        // --- SECONDARY — Olive / Sage ---
        secondary: {
          50: "hsl(78, 50%, 97%)",    // #F5F8EE
          100: "hsl(78, 45%, 90%)",   // #E2ECCC
          200: "hsl(78, 40%, 78%)",   // #C4D9A0
          300: "hsl(78, 38%, 64%)",   // #9BBD6E
          400: "hsl(78, 36%, 52%)",   // #779A4F
          500: "hsl(78, 35%, 42%)",   // #5E7C3F — couleur secondaire
          600: "hsl(78, 34%, 34%)",   // #4C6433
          700: "hsl(78, 33%, 27%)",   // #3C5028
          800: "hsl(78, 32%, 20%)",   // #2C3C1E
          900: "hsl(78, 30%, 13%)",   // #1C2613
          DEFAULT: "hsl(78, 35%, 42%)",
          foreground: "hsl(38, 30%, 98%)",
        },

        // --- ACCENT — Safran / Amber chaud ---
        accent: {
          50: "hsl(38, 100%, 97%)",   // #FFF8EC
          100: "hsl(38, 95%, 90%)",   // #FDECC8
          200: "hsl(38, 92%, 78%)",   // #FBD78E
          300: "hsl(38, 90%, 65%)",   // #F8C254
          400: "hsl(38, 90%, 58%)",   // #F6B325 — étoiles rating
          500: "hsl(38, 90%, 52%)",   // #F2A007
          600: "hsl(38, 88%, 43%)",   // #C98106
          700: "hsl(38, 85%, 34%)",   // #A06404
          800: "hsl(38, 82%, 25%)",   // #764903
          900: "hsl(38, 78%, 16%)",   // #4C2E02
          DEFAULT: "hsl(38, 90%, 52%)",
          foreground: "hsl(38, 14%, 18%)",
        },

        // --- NEUTRALS — Warm Cream ---
        neutral: {
          50: "hsl(38, 30%, 98%)",    // #FDFAF6 — fond de page
          100: "hsl(38, 25%, 95%)",   // #F8F4ED
          200: "hsl(38, 20%, 89%)",   // #EDE6D9 — bordures
          300: "hsl(38, 15%, 80%)",   // #D9CFC0
          400: "hsl(38, 12%, 65%)",   // #B5A892 — placeholder
          500: "hsl(38, 10%, 50%)",   // #8C7E6A — texte secondaire
          600: "hsl(38, 10%, 38%)",   // #6B5E4E — texte corps
          700: "hsl(38, 12%, 28%)",   // #4E4036
          800: "hsl(38, 14%, 18%)",   // #332920
          900: "hsl(38, 16%, 10%)",   // #1C1510 — texte principal
        },

        // --- SEMANTIC — Success ---
        success: {
          50: "hsl(145, 50%, 96%)",   // #EDFAF3
          100: "hsl(145, 45%, 88%)",  // #CAF0DB
          500: "hsl(145, 55%, 38%)",  // #2B8A56
          700: "hsl(145, 60%, 24%)",  // #1A5735
          DEFAULT: "hsl(145, 55%, 38%)",
          foreground: "hsl(145, 50%, 96%)",
        },

        // --- SEMANTIC — Warning ---
        warning: {
          50: "hsl(38, 95%, 97%)",    // #FFFBF0
          100: "hsl(38, 90%, 88%)",   // #FDECC5
          500: "hsl(38, 85%, 42%)",   // #C98505
          700: "hsl(38, 88%, 27%)",   // #825503
          DEFAULT: "hsl(38, 85%, 42%)",
          foreground: "hsl(38, 95%, 97%)",
        },

        // --- SEMANTIC — Error (Rouge terracotta, pas crimson) ---
        error: {
          50: "hsl(4, 90%, 97%)",     // #FFF2F0
          100: "hsl(4, 85%, 90%)",    // #FFCFC9
          500: "hsl(4, 72%, 45%)",    // #C43822
          700: "hsl(4, 75%, 30%)",    // #832416
          DEFAULT: "hsl(4, 72%, 45%)",
          foreground: "hsl(4, 90%, 97%)",
        },

        // --- SEMANTIC — Info (seul bleu autorisé, ardoise chaude) ---
        info: {
          50: "hsl(210, 35%, 97%)",   // #F2F5F9
          100: "hsl(210, 30%, 88%)",  // #CFDAE9
          500: "hsl(210, 45%, 40%)",  // #376A9C
          700: "hsl(210, 50%, 27%)",  // #234568
          DEFAULT: "hsl(210, 45%, 40%)",
          foreground: "hsl(210, 35%, 97%)",
        },

        // --- DARK MODE — Surfaces nocturnes ---
        dark: {
          base: "hsl(28, 15%, 9%)",       // #1A1510 — fond page dark
          surface: "hsl(28, 14%, 13%)",   // #231D17 — sections dark
          border: "hsl(28, 12%, 20%)",    // #352C24 — bordures dark
          text: "hsl(38, 20%, 92%)",      // #EDE6D9 — texte dark
        },

        // Aliases sémantiques pour shadcn/ui compatibility — alignés palette premium
        background: "#fff8f6",
        foreground: "#201a19",
        card: "#ffffff",
        "card-foreground": "#201a19",
        popover: "#ffffff",
        "popover-foreground": "#201a19",
        muted: "hsl(38, 20%, 89%)",
        "muted-foreground": "hsl(38, 10%, 50%)",
        destructive: "hsl(4, 72%, 45%)",
        "destructive-foreground": "hsl(4, 90%, 97%)",
        border: "#857370",
        input: "#857370",
        ring: "#E2725B",
      },

      // -----------------------------------------------------------------------
      // OMBRES — Warm (teinte terracotta, pas gris)
      // -----------------------------------------------------------------------
      boxShadow: {
        xs: "0 1px 2px hsl(14 40% 30% / 0.06)",
        sm: "0 2px 6px hsl(14 40% 30% / 0.08), 0 1px 2px hsl(14 40% 30% / 0.04)",
        DEFAULT: "0 4px 12px hsl(14 40% 30% / 0.10), 0 2px 4px hsl(14 40% 30% / 0.06)",
        md: "0 4px 12px hsl(14 40% 30% / 0.10), 0 2px 4px hsl(14 40% 30% / 0.06)",
        lg: "0 8px 24px hsl(14 40% 30% / 0.12), 0 4px 8px hsl(14 40% 30% / 0.08)",
        xl: "0 16px 40px hsl(14 40% 30% / 0.14), 0 8px 16px hsl(14 40% 30% / 0.10)",
        "2xl": "0 24px 64px hsl(14 40% 30% / 0.18), 0 12px 24px hsl(14 40% 30% / 0.12)",
        inner: "inset 0 2px 6px hsl(14 40% 30% / 0.08)",
        // Dark mode — remplacer par glow subtil
        "dark-sm": "0 0 0 1px hsl(14 60% 40% / 0.15)",
        "dark-md": "0 0 0 1px hsl(14 60% 40% / 0.20), 0 4px 12px hsl(14 40% 20% / 0.30)",
        none: "none",
      },

      // -----------------------------------------------------------------------
      // Z-INDEX SCALE
      // -----------------------------------------------------------------------
      zIndex: {
        base: "0",
        raised: "10",
        dropdown: "100",
        sticky: "200",
        overlay: "300",
        modal: "400",
        toast: "500",
        tooltip: "600",
        top: "9999",
      },

      // -----------------------------------------------------------------------
      // ANIMATIONS — Framer Motion complète, mais définition CSS de base ici
      // -----------------------------------------------------------------------
      transitionDuration: {
        fast: "150ms",
        base: "250ms",
        slow: "400ms",
        slower: "600ms",
      },

      transitionTimingFunction: {
        "ease-out-smooth": "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        "ease-in-out-smooth": "cubic-bezier(0.4, 0, 0.2, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "spring-gentle": "cubic-bezier(0.22, 1, 0.36, 1)",
      },

      keyframes: {
        // Entrée carte recette
        "card-enter": {
          "0%": { opacity: "0", transform: "translateY(12px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        // Succès ajout panier / PDF reçu
        "success-pop": {
          "0%": { transform: "scale(1)" },
          "40%": { transform: "scale(1.12)" },
          "70%": { transform: "scale(0.96)" },
          "100%": { transform: "scale(1)" },
        },
        // Rating étoile haptic-like
        "star-pop": {
          "0%": { transform: "scale(1) rotate(0deg)" },
          "50%": { transform: "scale(1.3) rotate(-8deg)" },
          "100%": { transform: "scale(1) rotate(0deg)" },
        },
        // Skeleton shimmer warm
        "shimmer-warm": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        // Toast slide in
        "toast-slide-in": {
          "0%": { opacity: "0", transform: "translateY(100%) scale(0.95)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        // Fade in générique
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        // Slide up mobile sheet
        "slide-up": {
          "0%": { transform: "translateY(100%)" },
          "100%": { transform: "translateY(0)" },
        },
      },

      animation: {
        "card-enter": "card-enter 250ms cubic-bezier(0.22, 1, 0.36, 1) both",
        "success-pop": "success-pop 400ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        "star-pop": "star-pop 300ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        "shimmer-warm": "shimmer-warm 1.8s linear infinite",
        "toast-slide-in": "toast-slide-in 350ms cubic-bezier(0.22, 1, 0.36, 1)",
        "fade-in": "fade-in 250ms ease-out both",
        "slide-up": "slide-up 350ms cubic-bezier(0.22, 1, 0.36, 1)",
      },

      // -----------------------------------------------------------------------
      // TYPOGRAPHIE PLUGIN — prose styles
      // -----------------------------------------------------------------------
      typography: ({ theme }: { theme: (path: string) => string }) => ({
        warm: {
          css: {
            "--tw-prose-body": theme("colors.neutral.700"),
            "--tw-prose-headings": theme("colors.neutral.900"),
            "--tw-prose-lead": theme("colors.neutral.600"),
            "--tw-prose-links": theme("colors.primary.600"),
            "--tw-prose-bold": theme("colors.neutral.800"),
            "--tw-prose-counters": theme("colors.neutral.500"),
            "--tw-prose-bullets": theme("colors.primary.400"),
            "--tw-prose-hr": theme("colors.neutral.200"),
            "--tw-prose-quotes": theme("colors.neutral.800"),
            "--tw-prose-quote-borders": theme("colors.primary.300"),
            "--tw-prose-captions": theme("colors.neutral.500"),
            "--tw-prose-code": theme("colors.primary.700"),
            "--tw-prose-pre-code": theme("colors.neutral.100"),
            "--tw-prose-pre-bg": theme("colors.neutral.800"),
            "--tw-prose-th-borders": theme("colors.neutral.200"),
            "--tw-prose-td-borders": theme("colors.neutral.200"),
            // Invert (dark mode)
            "--tw-prose-invert-body": theme("colors.neutral.300"),
            "--tw-prose-invert-headings": theme("colors.neutral.100"),
            "--tw-prose-invert-lead": theme("colors.neutral.400"),
            "--tw-prose-invert-links": theme("colors.primary.400"),
            "--tw-prose-invert-bold": theme("colors.neutral.200"),
            "--tw-prose-invert-counters": theme("colors.neutral.400"),
            "--tw-prose-invert-bullets": theme("colors.primary.500"),
            "--tw-prose-invert-hr": theme("colors.neutral.700"),
            "--tw-prose-invert-quotes": theme("colors.neutral.100"),
            "--tw-prose-invert-quote-borders": theme("colors.primary.600"),
            "--tw-prose-invert-captions": theme("colors.neutral.400"),
            "--tw-prose-invert-code": theme("colors.primary.300"),
            "--tw-prose-invert-pre-code": theme("colors.neutral.300"),
            "--tw-prose-invert-pre-bg": "hsl(28, 15%, 9%)",
            "--tw-prose-invert-th-borders": theme("colors.neutral.700"),
            "--tw-prose-invert-td-borders": theme("colors.neutral.700"),
            // Font
            fontFamily: theme("fontFamily.sans"),
            "h1, h2, h3, h4, h5, h6": {
              fontFamily: theme("fontFamily.display"),
            },
          },
        },
      }),
    },
  },

  // ---------------------------------------------------------------------------
  // PLUGINS
  // FIX #3 (review 2026-04-12) : imports ESM (typography, forms) déclarés en haut
  // du fichier — plus de require() CJS mélangé avec import type ESM
  // ---------------------------------------------------------------------------
  plugins: [
    // npm install -D @tailwindcss/typography
    typography,
    // npm install -D @tailwindcss/forms
    forms({
      strategy: "class", // Evite les conflits avec shadcn/ui
    }),
  ],
};

export default config;
