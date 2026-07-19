// Typed contract for the Atlas API. Mirrors the backend schema exactly.

export type RunStatus =
  | "pending"
  | "planning"
  | "executing"
  | "awaiting_approval"
  | "critiquing"
  | "replanning"
  | "completed"
  | "failed"
  | "cancelled";

export type PlanStepStatus =
  | "pending"
  | "ready"
  | "running"
  | "awaiting_approval"
  | "succeeded"
  | "failed"
  | "skipped";

export type ApprovalDecision = "approved" | "rejected" | "edited";

export interface RunSummary {
  id: string;
  goal: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  tags: string[];
}

export interface PlanStep {
  id: string;
  title: string;
  detail: string;
  depends_on: string[];
  allowed_tools: string[];
  requires_approval: boolean;
  status: PlanStepStatus;
}

export interface Plan {
  goal: string;
  rationale: string;
  steps: PlanStep[];
}

export interface ToolInvocation {
  tool: string;
  server: string;
  arguments: Record<string, unknown>;
  result: unknown;
  ok: boolean;
  error: string | null;
  duration_ms: number;
  blocked_by_guardrail: boolean;
}

export interface StepResult {
  step_id: string;
  attempt: number;
  output: string;
  tool_invocations: ToolInvocation[];
  citations: string[];
  tokens_used: number;
  succeeded: boolean;
  error: string | null;
}

export interface Critique {
  target: string;
  passed: boolean;
  score: number;
  issues: string[];
  suggestions: string[];
  retry_recommended: boolean;
}

export interface Citation {
  marker: string;
  source: string;
  title: string;
  url: string;
  snippet: string;
}

export interface Report {
  summary: string;
  body_markdown: string;
  citations: Citation[];
  confidence: number;
}

export interface ApprovalRequest {
  id: string;
  step_id: string;
  reason: string;
  proposed_action: string;
}

export interface RunDetail extends RunSummary {
  plan: Plan | null;
  results: Record<string, StepResult>;
  critiques: Critique[];
  report: Report | null;
  pending_approvals: ApprovalRequest[];
  error: string | null;
}

export interface RunListResponse {
  runs: RunSummary[];
  limit: number;
  offset: number;
}

export interface CreateRunBody {
  goal: string;
  auto_approve: boolean;
  max_steps?: number;
  tags?: string[];
}

export interface ApprovalDecisionInput {
  decision: ApprovalDecision;
  note?: string;
  edited_instruction?: string;
}

export interface ApprovalSubmission {
  decisions: Record<string, ApprovalDecisionInput>;
}

// ---- Server-sent events ----

export type EventType =
  | "run_created"
  | "run_status"
  | "plan_created"
  | "step_status"
  | "agent_token"
  | "agent_message"
  | "tool_call"
  | "tool_result"
  | "approval_requested"
  | "approval_resolved"
  | "critique"
  | "guardrail"
  | "report_ready"
  | "error"
  | "heartbeat";

export interface RunEventData {
  step_id: string | null;
  agent: string | null;
  payload: Record<string, unknown>;
}

// A normalized event used by the activity timeline. Each SSE frame becomes one.
export interface TimelineEvent extends RunEventData {
  id: string;
  type: EventType;
  at: string;
}
