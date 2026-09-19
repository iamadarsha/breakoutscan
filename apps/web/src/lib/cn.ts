import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Without this, tailwind-merge reads `text-kpi` / `text-label` (our type scale,
// see tailwind.config.ts) as text *colours* and silently drops one when it is
// combined with a real colour such as `text-text-primary`.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["micro", "label", "data", "panel", "title", "kpi"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
