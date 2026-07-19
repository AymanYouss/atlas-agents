import clsx from "clsx";
import { Lock } from "lucide-react";
import type { Plan, PlanStep } from "@/api/types";
import { STEP_STATUS_META } from "@/lib/status";

interface PlanTreeProps {
  plan: Plan | null;
}

function depthOf(step: PlanStep, byId: Map<string, PlanStep>): number {
  // Depth = longest dependency chain length, capped so indentation stays sane.
  let depth = 0;
  const seen = new Set<string>();
  const walk = (id: string, level: number) => {
    if (seen.has(id)) return;
    seen.add(id);
    const s = byId.get(id);
    if (!s) return;
    for (const dep of s.depends_on) {
      depth = Math.max(depth, level + 1);
      walk(dep, level + 1);
    }
  };
  walk(step.id, 0);
  return Math.min(depth, 3);
}

function StepNode({ step, depth }: { step: PlanStep; depth: number }) {
  const meta = STEP_STATUS_META[step.status];
  const isRunning = step.status === "running";
  return (
    <li
      className={clsx(
        "relative rounded-md border bg-surface-raised px-3 py-2.5 transition-colors",
        isRunning ? "border-accent-cyan/60" : "border-hairline",
      )}
      style={{ marginLeft: depth * 16 }}
    >
      {isRunning && (
        <span className="absolute inset-y-0 left-0 w-0.5 rounded-l bg-accent-cyan" />
      )}
      <div className="flex items-start gap-2.5">
        <span
          className={clsx(
            "status-dot mt-1.5",
            meta.active && "animate-pulse-dot",
          )}
          style={{ backgroundColor: meta.color }}
          aria-label={`status ${meta.label}`}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-content-faint">
              {step.id}
            </span>
            <span className="truncate text-[13px] font-medium text-content-primary">
              {step.title}
            </span>
            {step.requires_approval && (
              <Lock
                className="h-3 w-3 shrink-0 text-accent-amber"
                aria-label="requires approval"
              />
            )}
          </div>
          {step.allowed_tools.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {step.allowed_tools.map((tool) => (
                <span key={tool} className="chip">
                  {tool}
                </span>
              ))}
            </div>
          )}
        </div>
        <span
          className="mt-0.5 shrink-0 font-mono text-[10px] uppercase tracking-wide"
          style={{ color: meta.color }}
        >
          {meta.label}
        </span>
      </div>
    </li>
  );
}

export function PlanTree({ plan }: PlanTreeProps) {
  if (!plan) {
    return (
      <div className="px-4 py-8 text-center font-mono text-xs text-content-faint">
        awaiting plan…
      </div>
    );
  }

  const byId = new Map(plan.steps.map((s) => [s.id, s]));

  return (
    <div className="space-y-3 p-4">
      {plan.rationale && (
        <p className="rounded-md border border-hairline bg-base px-3 py-2 text-xs leading-relaxed text-content-muted">
          {plan.rationale}
        </p>
      )}
      <ol className="space-y-2">
        {plan.steps.map((step) => (
          <StepNode key={step.id} step={step} depth={depthOf(step, byId)} />
        ))}
      </ol>
    </div>
  );
}
