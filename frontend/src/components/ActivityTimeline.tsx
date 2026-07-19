import { useEffect, useRef } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  FileText,
  GitBranch,
  ListChecks,
  ShieldAlert,
  Wrench,
  XCircle,
} from "lucide-react";
import type { EventType, TimelineEvent } from "@/api/types";
import { clockTime, previewJson } from "@/lib/format";

interface ActivityTimelineProps {
  events: TimelineEvent[];
  autoScroll?: boolean;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}
function bool(v: unknown): boolean {
  return v === true;
}
function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}

interface RowChrome {
  label: string;
  color: string;
  icon: typeof Brain;
}

function chromeFor(type: EventType, payload: Record<string, unknown>): RowChrome {
  switch (type) {
    case "agent_message":
      return { label: "think", color: "#60A5FA", icon: Brain };
    case "tool_call":
      return { label: "tool", color: "#D946EF", icon: Wrench };
    case "tool_result":
      return bool(payload.ok)
        ? { label: "result", color: "#34D399", icon: CheckCircle2 }
        : { label: "result", color: "#F87171", icon: XCircle };
    case "critique":
      return bool(payload.passed)
        ? { label: "critique", color: "#34D399", icon: ListChecks }
        : { label: "critique", color: "#F59E0B", icon: ListChecks };
    case "guardrail":
      return { label: "guardrail", color: "#F87171", icon: ShieldAlert };
    case "step_status":
      return { label: "step", color: "#A1A1AA", icon: ArrowRight };
    case "plan_created":
      return { label: "plan", color: "#22D3EE", icon: ListChecks };
    case "run_status":
      return { label: "status", color: "#22D3EE", icon: GitBranch };
    case "report_ready":
      return { label: "report", color: "#22D3EE", icon: FileText };
    case "error":
      return { label: "error", color: "#F87171", icon: AlertTriangle };
    default:
      return { label: type, color: "#71717A", icon: GitBranch };
  }
}

function EventBody({ event }: { event: TimelineEvent }) {
  const p = event.payload;
  switch (event.type) {
    case "agent_message":
      return (
        <p className="text-[13px] leading-relaxed text-content-primary">
          {str(p.text)}
        </p>
      );
    case "tool_call":
      return (
        <div className="space-y-0.5">
          <div className="text-[13px] text-content-primary">
            <span className="text-content-muted">call</span>{" "}
            <span className="font-medium">{str(p.tool)}</span>
            {p.server ? (
              <span className="text-content-faint"> @ {str(p.server)}</span>
            ) : null}
          </div>
          {p.arguments != null && (
            <code className="block truncate text-[11px] text-content-muted">
              {previewJson(p.arguments, 160)}
            </code>
          )}
        </div>
      );
    case "tool_result": {
      const ok = bool(p.ok);
      const dur = num(p.duration_ms);
      return (
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 text-[13px]">
            <span style={{ color: ok ? "#34D399" : "#F87171" }}>
              {ok ? "ok" : "failed"}
            </span>
            <span className="text-content-primary">{str(p.tool)}</span>
            {dur != null && (
              <span className="font-mono text-[11px] text-content-faint">
                {dur}ms
              </span>
            )}
          </div>
          {(p.result != null || p.error != null) && (
            <code className="block truncate text-[11px] text-content-muted">
              {previewJson(p.error ?? p.result, 160)}
            </code>
          )}
        </div>
      );
    }
    case "critique": {
      const passed = bool(p.passed);
      const score = num(p.score);
      const issues = Array.isArray(p.issues) ? (p.issues as unknown[]) : [];
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[13px]">
            <span style={{ color: passed ? "#34D399" : "#F59E0B" }}>
              {passed ? "passed" : "flagged"}
            </span>
            {score != null && (
              <span className="font-mono text-[11px] text-content-muted">
                score {score.toFixed(2)}
              </span>
            )}
            <span className="text-content-faint">→ {str(p.target)}</span>
          </div>
          {issues.length > 0 && (
            <ul className="ml-3 list-disc text-[12px] text-content-muted">
              {issues.map((issue, i) => (
                <li key={i}>{str(issue)}</li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    case "guardrail":
      return (
        <div className="space-y-0.5">
          <div className="text-[13px] text-content-primary">
            <span className="font-medium">{str(p.guardrail)}</span>
            {p.action ? (
              <span className="text-accent-amber"> · {str(p.action)}</span>
            ) : null}
          </div>
          {p.detail != null && (
            <p className="text-[12px] leading-relaxed text-content-muted">
              {str(p.detail)}
            </p>
          )}
        </div>
      );
    case "step_status":
      return (
        <div className="flex items-center gap-2 text-[13px] text-content-muted">
          <span className="font-mono text-content-faint">{event.step_id}</span>
          <span>{str(p.from)}</span>
          <ArrowRight className="h-3 w-3" />
          <span className="text-content-primary">{str(p.to)}</span>
        </div>
      );
    case "plan_created":
      return (
        <p className="text-[13px] text-content-primary">
          plan created · {num(p.steps) ?? "?"} steps
        </p>
      );
    case "run_status":
      return (
        <p className="text-[13px] text-content-primary">
          run status → {str(p.status)}
        </p>
      );
    case "report_ready":
      return (
        <p className="text-[13px] text-content-primary">
          report synthesized
          {num(p.confidence) != null
            ? ` · confidence ${Math.round((num(p.confidence) ?? 0) * 100)}%`
            : ""}
        </p>
      );
    case "run_created":
      return <p className="text-[13px] text-content-muted">run created</p>;
    case "error":
      return (
        <p className="text-[13px] text-semantic-danger">
          {str(p.message ?? p.error ?? "error")}
        </p>
      );
    default:
      return (
        <code className="block truncate text-[12px] text-content-muted">
          {previewJson(p, 160)}
        </code>
      );
  }
}

function TimelineRow({ event }: { event: TimelineEvent }) {
  const chrome = chromeFor(event.type, event.payload);
  const Icon = chrome.icon;
  return (
    <li className="flex animate-fade-in gap-3 px-4 py-2 hover:bg-surface-raised/40">
      <span className="mt-0.5 shrink-0 font-mono text-[10px] tabular-nums text-content-faint">
        {clockTime(event.at)}
      </span>
      <span
        className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center"
        style={{ color: chrome.color }}
      >
        <Icon className="h-3.5 w-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex items-center gap-2">
          <span
            className="font-mono text-[10px] uppercase tracking-wider"
            style={{ color: chrome.color }}
          >
            {chrome.label}
          </span>
          {event.agent && (
            <span className="font-mono text-[10px] text-content-faint">
              {event.agent}
            </span>
          )}
        </div>
        <EventBody event={event} />
      </div>
    </li>
  );
}

export function ActivityTimeline({
  events,
  autoScroll = true,
}: ActivityTimelineProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [events.length, autoScroll]);

  if (events.length === 0) {
    return (
      <div className="px-4 py-8 text-center font-mono text-xs text-content-faint">
        no activity yet — events will stream here
      </div>
    );
  }

  return (
    <ul className="divide-y divide-hairline/60">
      {events.map((event) => (
        <TimelineRow key={event.id} event={event} />
      ))}
      <div ref={bottomRef} />
    </ul>
  );
}
