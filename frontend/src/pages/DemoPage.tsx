import { RunVisualizer } from "@/components/RunVisualizer";
import { SAMPLE_RUN, SAMPLE_TIMELINE } from "@/data/sampleRun";

export function DemoPage() {
  return (
    <div>
      <div className="mx-auto max-w-[1600px] px-6 pt-4">
        <div className="rounded-md border border-hairline bg-surface-raised px-3 py-2 font-mono text-[11px] text-content-muted">
          demo · a completed run rendered from a bundled fixture, no backend
          required
        </div>
      </div>
      <RunVisualizer
        run={SAMPLE_RUN}
        status={SAMPLE_RUN.status}
        plan={SAMPLE_RUN.plan}
        report={SAMPLE_RUN.report}
        draft={SAMPLE_RUN.report?.body_markdown ?? ""}
        timeline={SAMPLE_TIMELINE}
        pendingApprovals={SAMPLE_RUN.pending_approvals}
      />
    </div>
  );
}
