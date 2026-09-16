"use client";

import { useEffect, type ReactNode } from "react";
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
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Prevent body scroll when modal is open
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handler);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handler);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-end sm:items-center justify-center p-0 sm:p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, y: 60, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className={cn(
              "relative z-10 w-full max-w-lg rounded-t-2xl sm:rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-2xl safe-area-bottom",
              "max-h-[80vh] sm:max-h-[85vh] overflow-y-auto scroll-touch",
              className
            )}
          >
            {/* Drag handle on mobile */}
            <div className="sm:hidden mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
            {title && (
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
                <button
                  onClick={onClose}
                  className="rounded-full p-2.5 text-text-secondary transition hover:bg-elevated hover:text-text-primary"
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
    </AnimatePresence>
  );
}
