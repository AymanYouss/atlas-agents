import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/api/client";
import { RunsTable } from "@/components/RunsTable";
import { SectionLabel } from "@/components/SectionLabel";

const PAGE_SIZE = 20;

export function RunsListPage() {
  const [offset, setOffset] = useState(0);

  const query = useQuery({
    queryKey: ["runs", { limit: PAGE_SIZE, offset }],
    queryFn: () => api.listRuns(PAGE_SIZE, offset),
    retry: false,
  });

  const runs = query.data?.runs ?? [];
  const canPrev = offset > 0;
  const canNext = runs.length === PAGE_SIZE;

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-8">
      <div className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-semibold text-content-primary">Runs</h1>
          <p className="mt-1 text-sm text-content-muted">
            Every task submitted to the control plane.
          </p>
        </div>
        <Link
          to="/"
          className="font-mono text-[12px] uppercase tracking-wider text-content-muted hover:text-accent-cyan"
        >
          new run
        </Link>
      </div>

      <div className="card overflow-hidden">
        <SectionLabel
          right={
            <span className="font-mono text-[10px] text-content-faint">
              page {Math.floor(offset / PAGE_SIZE) + 1}
            </span>
          }
        >
          All runs
        </SectionLabel>

        {query.isLoading ? (
          <div className="px-4 py-12 text-center font-mono text-xs text-content-faint">
            loading…
          </div>
        ) : query.isError ? (
          <div className="px-4 py-12 text-center font-mono text-xs text-content-faint">
            backend unavailable — open the{" "}
            <Link to="/demo" className="text-accent-cyan hover:underline">
              demo run
            </Link>{" "}
            to explore offline
          </div>
        ) : (
          <RunsTable runs={runs} />
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!canPrev}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Prev
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!canNext}
          onClick={() => setOffset((o) => o + PAGE_SIZE)}
        >
          Next
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
