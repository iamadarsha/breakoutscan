"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Modal({ open, onClose, title, children, className }: ModalProps) {
  // Callers pass inline arrows; keep the latest one in a ref so the effect
  // below only runs when the modal opens or closes, not on every parent render.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    // Prevent body scroll while open; scrollbar-gutter (globals.css) stops the page shifting.
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handler);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", handler);
    };
  }, [open]);

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  // Portal to <body>: a `fixed` overlay inside the page's transformed/clipped
  // containers is positioned and clipped relative to them, not the viewport.
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-end sm:items-center justify-center p-0 sm:p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/45"
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ opacity: 0, y: 60, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className={cn(
              "relative z-10 w-full max-w-lg rounded-t-xl sm:rounded-xl border border-border bg-card p-4 sm:p-5 shadow-pop safe-area-bottom",
              "max-h-[80vh] sm:max-h-[85vh] overflow-y-auto scroll-touch",
              className
            )}
          >
            {/* Drag handle on mobile */}
            <div className="sm:hidden mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
            {title && (
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-panel font-semibold text-text-primary">{title}</h3>
                <button
                  onClick={onClose}
                  className="rounded-lg p-2 text-text-secondary transition-colors hover:bg-elevated hover:text-text-primary"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            )}
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
