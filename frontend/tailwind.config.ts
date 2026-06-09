import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        fulkro: {
          // Paleta DEFINITIVA purple+ink (Sesión 11 FASE 1; escala completada Sprint 1 P1.b).
          // Formato `rgb(var(--token-rgb) / <alpha-value>)` habilita Tailwind alpha modifier.
          primary: {
            50:  "rgb(var(--fulkro-primary-50-rgb) / <alpha-value>)",
            100: "rgb(var(--fulkro-primary-100-rgb) / <alpha-value>)",
            200: "rgb(var(--fulkro-primary-200-rgb) / <alpha-value>)",
            300: "rgb(var(--fulkro-primary-300-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-primary-500-rgb) / <alpha-value>)",
            600: "rgb(var(--fulkro-primary-600-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-primary-700-rgb) / <alpha-value>)",
            800: "rgb(var(--fulkro-primary-800-rgb) / <alpha-value>)",
            900: "rgb(var(--fulkro-primary-900-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-primary-500-rgb) / <alpha-value>)",
          },
          accent: {
            300: "rgb(var(--fulkro-accent-300-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-accent-500-rgb) / <alpha-value>)",
            // Sub-atom Sesión 3B-2B.2 Phase A.3.X · WCAG token overhaul.
            // Previous DEFAULT = -500 (#8b83ff) gave 2.92:1 on white (FAIL AA).
            // DEFAULT now points to fulkro-primary-700 (#5048cc) = 7.6:1 (AAA).
            // -500 still available as explicit `text-fulkro-accent-500` if needed
            // for non-text decorative SVG marks.
            DEFAULT: "rgb(var(--fulkro-primary-700-rgb) / <alpha-value>)",
          },
          ink: {
            50:  "rgb(var(--fulkro-ink-50-rgb) / <alpha-value>)",
            100: "rgb(var(--fulkro-ink-100-rgb) / <alpha-value>)",
            200: "rgb(var(--fulkro-ink-200-rgb) / <alpha-value>)",
            300: "rgb(var(--fulkro-ink-300-rgb) / <alpha-value>)",
            400: "rgb(var(--fulkro-ink-400-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-ink-500-rgb) / <alpha-value>)",
            600: "rgb(var(--fulkro-ink-600-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-ink-700-rgb) / <alpha-value>)",
            800: "rgb(var(--fulkro-ink-800-rgb) / <alpha-value>)",
            900: "rgb(var(--fulkro-ink-900-rgb) / <alpha-value>)",
            950: "rgb(var(--fulkro-ink-950-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-ink-900-rgb) / <alpha-value>)",
          },
          // Canvas — superficie inset (tracks, code blocks, hovers) · P1.b
          canvas: "rgb(var(--fulkro-canvas-rgb) / <alpha-value>)",
          // Estados semánticos — escala 3-step · P1.b
          //
          // Sub-atom Sesión 3B-2B.2 Phase A.3.X · WCAG token overhaul.
          // DEFAULT shade re-mapped from -500 (base saturated) to -700 (deep
          // shade) to satisfy WCAG AA contrast across all current usages
          // (`text-fulkro-success` etc on white/tinted bgs). Previous -500
          // DEFAULT gave 2.6-4.5:1 ratios in card/badge/chip contexts (FAIL).
          // -700 gives 4.7-10+ ratios (PASS AA/AAA).
          //
          // Explicit -500/-50/-700 access still available via `text-fulkro-{name}-{shade}`.
          // Backgrounds with alpha (e.g. `bg-fulkro-success/10`) now use -700
          // base · visually very subtle tint difference (alpha 10% mostly
          // transparent · blended bg ≈ rgb(232,239,235) was rgb(234,244,239)).
          success: {
            50:  "rgb(var(--fulkro-success-50-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-success-500-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-success-700-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-success-700-rgb) / <alpha-value>)",
          },
          warning: {
            50:  "rgb(var(--fulkro-warning-50-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-warning-500-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-warning-700-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-warning-700-rgb) / <alpha-value>)",
          },
          info: {
            50:  "rgb(var(--fulkro-info-50-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-info-500-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-info-700-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-info-700-rgb) / <alpha-value>)",
          },
          danger: {
            50:  "rgb(var(--fulkro-danger-50-rgb) / <alpha-value>)",
            500: "rgb(var(--fulkro-danger-500-rgb) / <alpha-value>)",
            700: "rgb(var(--fulkro-danger-700-rgb) / <alpha-value>)",
            DEFAULT: "rgb(var(--fulkro-danger-700-rgb) / <alpha-value>)",
          },
          // Surface glass — alpha horneado en el var · P1.b (modifier <alpha-value> no compone)
          "surface-glass":        "var(--fulkro-surface-glass)",
          "surface-glass-strong": "var(--fulkro-surface-glass-strong)",
          "surface-glass-border": "var(--fulkro-surface-glass-border)",
          // Tokens semánticos de texto · P1.b (apuntan a los vars resueltos de tokens.css)
          title:    "var(--fulkro-title)",
          subtitle: "var(--fulkro-subtitle)",
          body:     "var(--fulkro-body)",
          muted:    "var(--fulkro-muted)",
        },
        // ── shadcn design system tokens · puente FASE 2 completado (Sub-atom O).
        // Triplets RGB en globals.css → tokens.css. Mismo patrón que fulkro.*
        // arriba: `rgb(triplet / <alpha-value>)` habilita el alpha modifier
        // (lo usan badge.tsx `bg-primary/80`, alert.tsx `bg-destructive/10`…).
        background: "rgb(var(--background-rgb) / <alpha-value>)",
        foreground: "rgb(var(--foreground-rgb) / <alpha-value>)",
        border: "rgb(var(--border-rgb) / <alpha-value>)",
        input: "rgb(var(--input-rgb) / <alpha-value>)",
        ring: "rgb(var(--ring-rgb) / <alpha-value>)",
        muted: {
          DEFAULT: "rgb(var(--muted-rgb) / <alpha-value>)",
          foreground: "rgb(var(--muted-foreground-rgb) / <alpha-value>)",
        },
        primary: {
          DEFAULT: "rgb(var(--primary-rgb) / <alpha-value>)",
          foreground: "rgb(var(--primary-foreground-rgb) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "rgb(var(--secondary-rgb) / <alpha-value>)",
          foreground: "rgb(var(--secondary-foreground-rgb) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent-rgb) / <alpha-value>)",
          foreground: "rgb(var(--accent-foreground-rgb) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "rgb(var(--destructive-rgb) / <alpha-value>)",
          foreground: "rgb(var(--destructive-foreground-rgb) / <alpha-value>)",
        },
        card: {
          DEFAULT: "rgb(var(--card-rgb) / <alpha-value>)",
          foreground: "rgb(var(--card-foreground-rgb) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "rgb(var(--popover-rgb) / <alpha-value>)",
          foreground: "rgb(var(--popover-foreground-rgb) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "Consolas", "monospace"],
      },
      spacing: {
        sidebar: "290px",
        "sidebar-collapsed": "60px",
        "detail-panel": "400px",
        "tree-panel": "250px",
      },
      boxShadow: {
        ink: "0 4px 24px rgba(26, 26, 46, 0.15)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-in-right": {
          from: { transform: "translateX(100%)" },
          to: { transform: "translateX(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 150ms ease-out",
        "slide-in-right": "slide-in-right 200ms ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
