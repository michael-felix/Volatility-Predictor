"use client";

import { motion } from "framer-motion";
import { RISK_CONFIG, type RiskLevel } from "@/lib/riskLevel";

/** Icon (dot) + label pairing — status color never carries meaning alone.
 * The dot pulses gently for "high" risk only: a legitimate attention cue
 * for elevated risk, not decoration, so it's the one badge state that
 * earns continuous motion. */
export function RiskBadge({ level }: { level: RiskLevel }) {
  const { label, color } = RISK_CONFIG[level];
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.06 }}
      transition={{ duration: 0.25 }}
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ borderColor: `color-mix(in srgb, ${color} 40%, transparent)`, color }}
    >
      <motion.span
        aria-hidden
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
        animate={
          level === "high" ? { opacity: [1, 0.4, 1] } : undefined
        }
        transition={
          level === "high" ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" } : undefined
        }
      />
      {label}
    </motion.span>
  );
}
