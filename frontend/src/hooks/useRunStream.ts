import { useCallback, useEffect, useReducer, useRef } from "react";
import { api } from "@/api/client";
import type {
  EventType,
  Plan,
  PlanStep,
  PlanStepStatus,
  Report,
  RunDetail,
  RunStatus,
  TimelineEvent,
} from "@/api/types";

type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

export interface RunStreamState {
  status: RunStatus | null;
  plan: Plan | null;
  report: Report | null;
  /** Streamed report text accumulated from agent_token events. */
  draft: string;
  timeline: TimelineEvent[];
  connection: ConnectionState;
}

type Action =
  | { type: "hydrate"; detail: RunDetail }
  | { type: "connection"; value: ConnectionState }
  | { type: "event"; event: TimelineEvent };

const EVENT_TYPES: readonly EventType[] = [
  "run_created",
  "run_status",
  "plan_created",
  "step_status",
  "agent_token",
  "agent_message",
  "tool_call",
  "tool_result",
  "approval_requested",
  "approval_resolved",
  "critique",
  "guardrail",
  "report_ready",
  "error",
  "heartbeat",
];

// Events that are noise in the visible timeline.
const HIDDEN_IN_TIMELINE: ReadonlySet<EventType> = new Set([
  "heartbeat",
  "agent_token",
]);

const initialState: RunStreamState = {
  status: null,
  plan: null,
  report: null,
  draft: "",
  timeline: [],
  connection: "idle",
};

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function applyStepStatus(
  plan: Plan | null,
  stepId: string | null,
  to: PlanStepStatus | undefined,
): Plan | null {
  if (!plan || !stepId || !to) return plan;
  let changed = false;
  const steps: PlanStep[] = plan.steps.map((step) => {
    if (step.id === stepId && step.status !== to) {
      changed = true;
      return { ...step, status: to };
    }
    return step;
  });
  return changed ? { ...plan, steps } : plan;
}

function reducer(state: RunStreamState, action: Action): RunStreamState {
  switch (action.type) {
    case "hydrate": {
      const { detail } = action;
      return {
        ...state,
        status: detail.status,
        plan: detail.plan,
        report: detail.report,
        draft: detail.report?.body_markdown ?? state.draft,
      };
    }
    case "connection":
      return { ...state, connection: action.value };
    case "event": {
      const ev = action.event;
      let next = state;

      switch (ev.type) {
        case "run_status": {
          const status = asString(ev.payload.status) as RunStatus | undefined;
          if (status) next = { ...next, status };
          break;
        }
        case "step_status": {
          const to = asString(ev.payload.to) as PlanStepStatus | undefined;
          const plan = applyStepStatus(next.plan, ev.step_id, to);
          if (plan !== next.plan) next = { ...next, plan };
          break;
        }
        case "agent_token": {
          const token = asString(ev.payload.token) ?? asString(ev.payload.text);
          if (token) next = { ...next, draft: next.draft + token };
          break;
        }
        case "report_ready": {
          // The full report arrives via refetch; here we just note completion.
          break;
        }
        default:
          break;
      }

      if (HIDDEN_IN_TIMELINE.has(ev.type)) {
        return next;
      }
      return { ...next, timeline: [...next.timeline, ev] };
    }
    default:
      return state;
  }
}

export interface UseRunStreamResult extends RunStreamState {
  /** Merge a freshly fetched RunDetail into the live view state. */
  hydrate: (detail: RunDetail) => void;
}

/**
 * Manages an EventSource for a run, normalizing named SSE events into a
 * timeline and reducing status/plan/report into view state. Handles reconnect
 * with backoff and stops once the run reaches a terminal state.
 */
export function useRunStream(
  runId: string | null,
  options: { enabled?: boolean } = {},
): UseRunStreamResult {
  const { enabled = true } = options;
  const [state, dispatch] = useReducer(reducer, initialState);
  const sourceRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);
  const seqRef = useRef(0);
  const closedRef = useRef(false);

  const hydrate = useCallback((detail: RunDetail) => {
    dispatch({ type: "hydrate", detail });
  }, []);

  useEffect(() => {
    if (!runId || !enabled) return;

    closedRef.current = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (closedRef.current) return;
      dispatch({ type: "connection", value: "connecting" });

      const es = new EventSource(api.eventsUrl(runId));
      sourceRef.current = es;

      es.onopen = () => {
        retryRef.current = 0;
        dispatch({ type: "connection", value: "open" });
      };

      const handle = (type: EventType) => (msg: MessageEvent<string>) => {
        seqRef.current += 1;
        let parsed: {
          step_id?: string | null;
          agent?: string | null;
          payload?: Record<string, unknown>;
        } = {};
        try {
          parsed = JSON.parse(msg.data) as typeof parsed;
        } catch {
          parsed = {};
        }
        const event: TimelineEvent = {
          id: `${type}-${seqRef.current}`,
          type,
          at: new Date().toISOString(),
          step_id: parsed.step_id ?? null,
          agent: parsed.agent ?? null,
          payload: parsed.payload ?? {},
        };
        dispatch({ type: "event", event });
      };

      for (const type of EVENT_TYPES) {
        es.addEventListener(type, handle(type) as EventListener);
      }

      es.onerror = () => {
        es.close();
        if (closedRef.current) return;
        dispatch({ type: "connection", value: "error" });
        retryRef.current += 1;
        const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closedRef.current = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      sourceRef.current?.close();
      sourceRef.current = null;
      dispatch({ type: "connection", value: "closed" });
    };
  }, [runId, enabled]);

  return { ...state, hydrate };
}
