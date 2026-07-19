import { Link } from "react-router-dom";
import { Inbox } from "lucide-react";
import type { RunSummary } from "@/api/types";
import { StatusPill } from "./StatusPill";
import { relativeTime, truncate } from "@/lib/format";

interface RunsTableProps {
  runs: RunSummary[];
  emptyHint?: string;
}

export function RunsTable({ runs, emptyHint }: RunsTableProps) {
  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <Inbox className="h-6 w-6 text-content-faint" />
        <p className="font-mono text-xs text-content-faint">
          {emptyHint ?? "no runs yet — start one from the composer above"}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-hairline">
            <th className="mono-label px-4 py-2.5 font-normal">status</th>
            <th className="mono-label px-4 py-2.5 font-normal">goal</th>
            <th className="mono-label px-4 py-2.5 font-normal">tags</th>
            <th className="mono-label px-4 py-2.5 text-right font-normal">
              updated
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              className="group border-b border-hairline/60 transition-colors hover:bg-surface-raised/50"
            >
              <td className="px-4 py-3 align-middle">
                <StatusPill status={run.status} />
              </td>
              <td className="px-4 py-3 align-middle">
                <Link
                  to={`/runs/${run.id}`}
                  className="text-[13px] text-content-primary group-hover:text-accent-cyan"
                >
                  {truncate(run.goal, 90)}
                </Link>
                <div className="mt-0.5 font-mono text-[10px] text-content-faint">
                  {run.id}
                </div>
              </td>
              <td className="px-4 py-3 align-middle">
                <div className="flex flex-wrap gap-1">
                  {run.tags.map((tag) => (
                    <span key={tag} className="chip">
                      {tag}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-3 text-right align-middle font-mono text-[11px] text-content-muted">
                {relativeTime(run.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
