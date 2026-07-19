import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  accent?: string;
}

export function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "#22D3EE",
}: MetricCardProps) {
  return (
    <div className="card flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between">
        <span className="mono-label">{label}</span>
        {Icon && <Icon className="h-4 w-4" style={{ color: accent }} />}
      </div>
      <div className="font-mono text-2xl font-semibold text-content-primary">
        {value}
      </div>
      {hint && <div className="text-[11px] text-content-faint">{hint}</div>}
    </div>
  );
}
