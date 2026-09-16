import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "var(--bg-page)",
        sidebar: "var(--bg-sidebar)",
        card: "var(--bg-card)",
        elevated: "var(--bg-elevated)",
        border: "var(--border)",
        "border-subtle": "var(--border-subtle)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          glow: "var(--accent-glow)",
        },
        bullish: "var(--bullish)",
        bearish: "var(--bearish)",
        warning: "var(--warning)",
        info: "var(--info)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-muted": "var(--text-muted)",
      },
      boxShadow: {
        card: "0 4px 24px rgba(0, 0, 0, 0.5)",
        glass: "inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 4px 16px rgba(0, 0, 0, 0.25)",
        accent: "0 4px 20px rgba(124, 92, 252, 0.25)",
        glow: "0 0 20px rgba(124, 92, 252, 0.15)",
      },
      borderRadius: {
        panel: "20px",
      },
      fontFamily: {
        sans: ["var(--font-inter)"],
        mono: ["var(--font-jetbrains-mono)"],
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
