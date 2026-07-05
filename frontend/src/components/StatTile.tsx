"use client";

import { AnimatePresence, motion } from "framer-motion";

interface StatTileProps {
  label: string;
  value: string;
  sublabel?: string;
}

/**
 * Stat tile per the project's dataviz conventions: sentence-case label (no
 * trailing colon), semibold value in proportional (non-tabular) figures —
 * tabular-nums is reserved for columns that must align vertically, which a
 * standalone tile value never is.
 *
 * The value is keyed on its own string, so a fresh prediction replacing an
 * old one crossfades rather than silently snapping to the new number —
 * a visible cue that this tile just updated.
 */
export function StatTile({ label, value, sublabel }: StatTileProps) {
  return (
    <div className="card overflow-hidden px-4 py-3">
      <div className="text-sm text-[var(--text-secondary)]">{label}</div>
      <AnimatePresence mode="wait">
        <motion.div
          key={value}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="mt-1 text-2xl font-semibold"
        >
          {value}
        </motion.div>
      </AnimatePresence>
      {sublabel && <div className="mt-0.5 text-xs text-[var(--text-muted)]">{sublabel}</div>}
    </div>
  );
}
