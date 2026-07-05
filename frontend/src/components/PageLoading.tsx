"use client";

import { motion } from "framer-motion";

/**
 * Shown automatically by Next.js (via loading.tsx files) while a route's
 * server-side data fetch is in flight. Without this, clicking a link felt
 * completely unresponsive whenever the backend was slow to answer (e.g. a
 * cold start after Render's free tier spins the instance down) -- there
 * was no visual acknowledgment the click even registered.
 */
export function PageLoading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="mx-auto flex max-w-4xl items-center justify-center py-24">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
        className="flex items-center gap-3 text-sm text-[var(--text-secondary)]"
      >
        <motion.span
          aria-hidden
          className="inline-block h-5 w-5 rounded-full border-2 border-current border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
        />
        {label}
      </motion.div>
    </div>
  );
}
