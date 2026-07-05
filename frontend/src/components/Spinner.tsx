"use client";

import { motion } from "framer-motion";

/** Small inline loading spinner — pairs with button labels during async actions. */
export function Spinner() {
  return (
    <motion.span
      aria-hidden
      className="inline-block h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent"
      animate={{ rotate: 360 }}
      transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
    />
  );
}
