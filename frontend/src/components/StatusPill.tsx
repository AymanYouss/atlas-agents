import clsx from "clsx";
import type { RunStatus } from "@/api/types";
import { RUN_STATUS_META } from "@/lib/status";

interface StatusPillProps {
  status: RunStatus;
  size?: "sm" | "lg";
  className?: string;
}

export function StatusPill({ status, size = "sm", className }: StatusPillProps) {
  const meta = RUN_STATUS_META[status];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-2 rounded border font-mono uppercase tracking-wider",
        size === "lg" ? "px-3 py-1 text-xs" : "px-2 py-0.5 text-[10px]",
        className,
      )}
      style={{
        color: meta.color,
        borderColor: `${meta.color}44`,
        backgroundColor: `${meta.color}12`,
      }}
    >
      <span
        className={clsx("status-dot", meta.active && "animate-pulse-dot")}
        style={{ backgroundColor: meta.color }}
        aria-hidden
      />
      {meta.label}
    </span>
  );
}
