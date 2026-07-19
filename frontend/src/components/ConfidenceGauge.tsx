interface ConfidenceGaugeProps {
  value: number; // 0..1
  size?: number;
}

function colorFor(value: number): string {
  if (value >= 0.8) return "#34D399";
  if (value >= 0.6) return "#F59E0B";
  return "#F87171";
}

export function ConfidenceGauge({ value, size = 44 }: ConfidenceGaugeProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = circumference * clamped;
  const color = colorFor(clamped);

  return (
    <div className="flex items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#26262B"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
          />
        </svg>
        <span
          className="absolute inset-0 flex items-center justify-center font-mono text-[11px] font-medium"
          style={{ color }}
        >
          {Math.round(clamped * 100)}
        </span>
      </div>
      <div className="leading-tight">
        <div className="mono-label">confidence</div>
        <div className="font-mono text-xs" style={{ color }}>
          {clamped >= 0.8 ? "high" : clamped >= 0.6 ? "moderate" : "low"}
        </div>
      </div>
    </div>
  );
}
