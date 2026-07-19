import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/api/client";
import type { ApprovalSubmission, RunDetail } from "@/api/types";
import { RunVisualizer } from "@/components/RunVisualizer";
import { useRunStream } from "@/hooks/useRunStream";
import { isTerminal } from "@/lib/status";

export function RunViewPage() {
  const { id = "" } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const runQuery = useQuery<RunDetail>({
    queryKey: ["run", id],
    queryFn: () => api.getRun(id),
    enabled: Boolean(id),
    // Refetch while the run is in flight so plan/report/status stay fresh
    // alongside the SSE stream.
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 4000;
      return isTerminal(data.status) ? false : 4000;
    },
    retry: false,
  });

  const run = runQuery.data;
  const streamActive = Boolean(run && !isTerminal(run.status));

  const stream = useRunStream(id, { enabled: streamActive });
  const { hydrate } = stream;

  // Merge each fresh fetch into the live view state.
  useEffect(() => {
    if (run) hydrate(run);
  }, [run, hydrate]);

  const approvalMutation = useMutation<RunDetail, Error, ApprovalSubmission>({
    mutationFn: (submission) => api.submitApprovals(id, submission),
    onSuccess: (updated) => {
      queryClient.setQueryData(["run", id], updated);
      void queryClient.invalidateQueries({ queryKey: ["run", id] });
    },
  });

  if (runQuery.isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center font-mono text-sm text-content-faint">
        loading run…
      </div>
    );
  }

  if (runQuery.isError || !run) {
    return (
      <div className="mx-auto max-w-lg px-6 py-24 text-center">
        <p className="font-mono text-sm text-content-muted">
          could not load run <span className="text-content-primary">{id}</span>
        </p>
        <p className="mt-2 text-xs text-content-faint">
          {runQuery.error instanceof Error
            ? runQuery.error.message
            : "the backend may be offline"}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/runs" className="btn btn-ghost">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to runs
          </Link>
          <Link to="/demo" className="btn btn-primary">
            Open demo run
          </Link>
        </div>
      </div>
    );
  }

  // Prefer live stream state where it exists, falling back to the fetched run.
  const status = stream.status ?? run.status;
  const plan = stream.plan ?? run.plan;
  const report = run.report ?? stream.report;

  return (
    <RunVisualizer
      run={run}
      status={status}
      plan={plan}
      report={report}
      draft={stream.draft}
      timeline={stream.timeline}
      connection={stream.connection}
      pendingApprovals={run.pending_approvals}
      approvalSubmitting={approvalMutation.isPending}
      onApprove={(submission) => approvalMutation.mutate(submission)}
    />
  );
}
