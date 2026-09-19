"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Toaster } from "sonner";

type Theme = "dark" | "light";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

// Everyone lands on light mode; the toggle only changes the current visit.
const DEFAULT_THEME: Theme = "light";

const ThemeContext = createContext<ThemeContextValue>({
  theme: DEFAULT_THEME,
  toggleTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(DEFAULT_THEME);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    const meta = document.getElementById("theme-color-meta") as HTMLMetaElement | null;
    if (meta) meta.content = theme === "dark" ? "#0a0e1a" : "#f0f2f8";
  }, [theme]);

  const toggleTheme = () =>
    setTheme((t) => (t === "dark" ? "light" : "dark"));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

/** Toasts follow the active theme through the same CSS variables as the rest of the UI. */
export function ThemedToaster() {
  const { theme } = useTheme();
  return (
    <Toaster
      theme={theme}
      position="bottom-right"
      toastOptions={{
        style: {
          background: "var(--bg-elevated)",
          border: "1px solid var(--border)",
          color: "var(--text-primary)",
          backdropFilter: "blur(12px)",
        },
      }}
    />
  );
}
