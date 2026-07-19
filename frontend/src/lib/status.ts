import type { PlanStepStatus, RunStatus } from "@/api/types";

interface StatusVisual {
  label: string;
  /** dot / text color as a hex value */
  color: string;
  /** whether the status represents an in-flight, animated state */
  active: boolean;
}

export const RUN_STATUS_META: Record<RunStatus, StatusVisual> = {
  pending: { label: "pending", color: "#71717A", active: false },
  planning: { label: "planning", color: "#22D3EE", active: true },
  executing: { label: "executing", color: "#22D3EE", active: true },
  awaiting_approval: { label: "awaiting approval", color: "#F59E0B", active: true },
  critiquing: { label: "critiquing", color: "#60A5FA", active: true },
  replanning: { label: "replanning", color: "#60A5FA", active: true },
  completed: { label: "completed", color: "#34D399", active: false },
  failed: { label: "failed", color: "#F87171", active: false },
  cancelled: { label: "cancelled", color: "#71717A", active: false },
};

export const STEP_STATUS_META: Record<PlanStepStatus, StatusVisual> = {
  pending: { label: "pending", color: "#71717A", active: false },
  ready: { label: "ready", color: "#A1A1AA", active: false },
  running: { label: "running", color: "#F59E0B", active: true },
  awaiting_approval: { label: "awaiting", color: "#F59E0B", active: true },
  succeeded: { label: "succeeded", color: "#34D399", active: false },
  failed: { label: "failed", color: "#F87171", active: false },
  skipped: { label: "skipped", color: "#71717A", active: false },
};

const TERMINAL: ReadonlySet<RunStatus> = new Set([
  "completed",
  "failed",
  "cancelled",
]);

export function isTerminal(status: RunStatus): boolean {
  return TERMINAL.has(status);
}
