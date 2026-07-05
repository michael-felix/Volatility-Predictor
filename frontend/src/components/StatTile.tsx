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
 */
export function StatTile({ label, value, sublabel }: StatTileProps) {
  return (
    <div className="card px-4 py-3">
      <div className="text-sm text-[var(--text-secondary)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {sublabel && <div className="mt-0.5 text-xs text-[var(--text-muted)]">{sublabel}</div>}
    </div>
  );
}
