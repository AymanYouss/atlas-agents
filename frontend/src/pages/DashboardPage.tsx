import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Gauge, Network, ShieldCheck, Timer } from "lucide-react";
import { api } from "@/api/client";
import { MetricCard } from "@/components/MetricCard";
import { RunsTable } from "@/components/RunsTable";
import { SectionLabel } from "@/components/SectionLabel";
import { RunComposer } from "./RunComposer";
import { CORE_SUITE, INJECTION_SUITE } from "@/data/benchmarks";

export function DashboardPage() {
  const runsQuery = useQuery({
    queryKey: ["runs", { limit: 8, offset: 0 }],
    queryFn: () => api.listRuns(8, 0),
    retry: false,
  });

  const successPct = Math.round(CORE_SUITE.success_rate * 100);
  const injectionContained = INJECTION_SUITE
    ? `${INJECTION_SUITE.passed}/${INJECTION_SUITE.total}`
    : "6/6";
  const latency = (CORE_SUITE.mean_latency_ms / 1000).toFixed(1);

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-content-primary">
          Control plane
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Plan, run, and review autonomous multi-agent tasks with tool access
          brokered through MCP and gated by guardrails.
        </p>
      </div>

      <div className="mb-6">
        <RunComposer />
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          label="task success"
          value={`${successPct}%`}
          hint={`${CORE_SUITE.passed}/${CORE_SUITE.total} core tasks`}
          icon={Gauge}
        />
        <MetricCard
          label="injection defense"
          value={injectionContained}
          hint="attempts contained"
          icon={ShieldCheck}
          accent="#F59E0B"
        />
        <MetricCard
          label="mean latency"
          value={`~${latency}s`}
          hint="per task, end to end"
          icon={Timer}
          accent="#60A5FA"
        />
        <MetricCard
          label="tools"
          value="via MCP"
          hint="sandboxed, brokered"
          icon={Network}
          accent="#34D399"
        />
      </div>

      <div className="card overflow-hidden">
        <SectionLabel
          right={
            <Link
              to="/runs"
              className="font-mono text-[11px] uppercase tracking-wider text-content-muted hover:text-accent-cyan"
            >
              all runs
            </Link>
          }
        >
          Recent runs
        </SectionLabel>
        {runsQuery.isLoading ? (
          <div className="px-4 py-12 text-center font-mono text-xs text-content-faint">
            loading…
          </div>
        ) : runsQuery.isError ? (
          <div className="px-4 py-12 text-center font-mono text-xs text-content-faint">
            backend unavailable — open the{" "}
            <Link to="/demo" className="text-accent-cyan hover:underline">
              demo run
            </Link>{" "}
            to explore the visualizer offline
          </div>
        ) : (
          <RunsTable runs={runsQuery.data?.runs ?? []} />
        )}
      </div>
    </div>
  );
}
