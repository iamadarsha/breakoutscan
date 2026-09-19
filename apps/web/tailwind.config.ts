import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // rgb(var(--x-rgb) / <alpha-value>) is what makes bg-accent/10 etc. compile.
        page: "rgb(var(--bg-page-rgb) / <alpha-value>)",
        sidebar: "rgb(var(--bg-sidebar-rgb) / <alpha-value>)",
        card: "rgb(var(--bg-card-rgb) / <alpha-value>)",
        elevated: "rgb(var(--bg-elevated-rgb) / <alpha-value>)",
        border: "rgb(var(--border-rgb) / <alpha-value>)",
        "border-subtle": "rgb(var(--border-subtle-rgb) / <alpha-value>)",
        accent: {
          DEFAULT: "rgb(var(--accent-rgb) / <alpha-value>)",
          hover: "rgb(var(--accent-hover-rgb) / <alpha-value>)",
          solid: "rgb(var(--accent-solid-rgb) / <alpha-value>)",
          "solid-hover": "rgb(var(--accent-solid-hover-rgb) / <alpha-value>)",
          glow: "var(--accent-glow)",
        },
        bullish: "rgb(var(--bullish-rgb) / <alpha-value>)",
        bearish: "rgb(var(--bearish-rgb) / <alpha-value>)",
        warning: "rgb(var(--warning-rgb) / <alpha-value>)",
        info: "rgb(var(--info-rgb) / <alpha-value>)",
        "text-primary": "rgb(var(--text-primary-rgb) / <alpha-value>)",
        "text-secondary": "rgb(var(--text-secondary-rgb) / <alpha-value>)",
        "text-muted": "rgb(var(--text-muted-rgb) / <alpha-value>)",
      },
      boxShadow: {
        card: "var(--shadow-panel)",
        glass: "var(--shadow-panel)",
        pop: "var(--shadow-pop)",
        accent: "0 1px 2px rgba(16, 24, 40, 0.12)",
        glow: "0 0 0 3px var(--accent-glow)",
      },
      borderRadius: {
        panel: "10px",
      },
      fontSize: {
        // Type scale: one step per level of the hierarchy.
        micro: ["10px", { lineHeight: "14px" }],   // overlines, units
        label: ["11px", { lineHeight: "16px" }],   // column heads, KPI labels, meta
        data: ["13px", { lineHeight: "20px" }],                              // body / table cells
        panel: ["14px", { lineHeight: "20px" }],                             // panel titles
        title: ["22px", { lineHeight: "28px", letterSpacing: "-0.01em" }],   // page title
        kpi: ["28px", { lineHeight: "32px", letterSpacing: "-0.02em" }],     // headline numbers
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      animation: {
        "flash-bullish": "flash-bullish 0.6s ease-out",
        "flash-bearish": "flash-bearish 0.6s ease-out",
        "pulse-dot": "pulse-dot 1.5s ease-in-out infinite",
        shimmer: "shimmer 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
        "scale-in": "scale-in 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
