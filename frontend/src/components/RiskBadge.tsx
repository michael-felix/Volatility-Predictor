import { RISK_CONFIG, type RiskLevel } from "@/lib/riskLevel";

/** Icon (dot) + label pairing — status color never carries meaning alone. */
export function RiskBadge({ level }: { level: RiskLevel }) {
  const { label, color } = RISK_CONFIG[level];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ borderColor: `color-mix(in srgb, ${color} 40%, transparent)`, color }}
    >
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
