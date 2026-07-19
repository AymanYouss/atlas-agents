import { Clock, Copy } from "lucide-react";
import type {
  ApprovalRequest,
  ApprovalSubmission,
  Plan,
  Report,
  RunDetail,
  RunStatus,
  TimelineEvent,
} from "@/api/types";
import { StatusPill } from "./StatusPill";
import { PlanTree } from "./PlanTree";
import { ActivityTimeline } from "./ActivityTimeline";
import { ReportPanel } from "./ReportPanel";
import { ApprovalGate } from "./ApprovalGate";
import { SectionLabel } from "./SectionLabel";
import { elapsedBetween, relativeTime } from "@/lib/format";
import { isTerminal } from "@/lib/status";

export interface RunVisualizerProps {
  run: RunDetail;
  status: RunStatus;
  plan: Plan | null;
  report: Report | null;
  draft: string;
  timeline: TimelineEvent[];
  connection?: string;
  pendingApprovals: ApprovalRequest[];
  approvalSubmitting?: boolean;
  onApprove?: (submission: ApprovalSubmission) => void;
}

export function RunVisualizer({
  run,
  status,
  plan,
  report,
  draft,
  timeline,
  connection,
  pendingApprovals,
  approvalSubmitting = false,
  onApprove,
}: RunVisualizerProps) {
  const live = !isTerminal(status);
  const showApproval = status === "awaiting_approval" && pendingApprovals.length > 0;

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-[1600px] flex-col px-6 py-4">
      {/* Header */}
      <div className="mb-4 shrink-0">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex items-center gap-3">
              <StatusPill status={status} size="lg" />
              <button
                type="button"
                className="inline-flex items-center gap-1.5 font-mono text-[11px] text-content-faint transition-colors hover:text-content-muted"
                onClick={() => void navigator.clipboard?.writeText(run.id)}
                aria-label="Copy run id"
              >
                {run.id}
                <Copy className="h-3 w-3" />
              </button>
              {connection && live && (
                <span className="font-mono text-[10px] uppercase tracking-wider text-content-faint">
                  stream: {connection}
                </span>
              )}
            </div>
            <h1 className="max-w-4xl text-lg font-semibold leading-snug text-content-primary">
              {run.goal}
            </h1>
            <div className="mt-1.5 flex items-center gap-4 font-mono text-[11px] text-content-faint">
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-3 w-3" />
                {elapsedBetween(run.created_at, run.updated_at)} elapsed
              </span>
              <span>updated {relativeTime(run.updated_at)}</span>
              {run.tags.length > 0 && (
                <span className="flex gap-1">
                  {run.tags.map((t) => (
                    <span key={t} className="chip">
                      {t}
                    </span>
                  ))}
                </span>
              )}
            </div>
          </div>
        </div>

        {run.error && (
          <div className="mt-3 rounded-md border border-semantic-danger/40 bg-semantic-danger/[0.08] px-3 py-2 font-mono text-[12px] text-semantic-danger">
            {run.error}
          </div>
        )}
      </div>

      {/* Three columns */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)_minmax(0,1fr)]">
        {/* PLAN */}
        <section className="card flex min-h-0 flex-col overflow-hidden">
          <SectionLabel>Plan</SectionLabel>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <PlanTree plan={plan} />
          </div>
        </section>

        {/* ACTIVITY */}
        <section className="card flex min-h-0 flex-col overflow-hidden">
          <SectionLabel
            right={
              <span className="font-mono text-[10px] text-content-faint">
                {timeline.length} events
              </span>
            }
          >
            Activity
          </SectionLabel>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ActivityTimeline events={timeline} autoScroll={live} />
          </div>
        </section>

        {/* REPORT + APPROVAL */}
        <section className="flex min-h-0 flex-col gap-4">
          {showApproval && onApprove && (
            <div className="card overflow-hidden">
              <SectionLabel>Approval gate</SectionLabel>
              <div className="p-4">
                <ApprovalGate
                  requests={pendingApprovals}
                  submitting={approvalSubmitting}
                  onSubmit={onApprove}
                />
              </div>
            </div>
          )}
          <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
            <SectionLabel
              right={
                report ? (
                  <span className="font-mono text-[10px] text-content-faint">
                    {report.citations.length} sources
                  </span>
                ) : undefined
              }
            >
              Report
            </SectionLabel>
            <div className="min-h-0 flex-1 overflow-hidden">
              <ReportPanel report={report} draft={draft} streaming={live} />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
