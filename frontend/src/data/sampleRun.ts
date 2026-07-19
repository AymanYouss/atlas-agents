import type { RunDetail, TimelineEvent } from "@/api/types";

// A realistic, completed run used by the /demo route so the product can be
// shown end-to-end without a backend. The visualizer components consume this
// through the same props as a live run.

const BASE = "2026-07-19T14:02:00.000Z";
function at(offsetSec: number): string {
  return new Date(new Date(BASE).getTime() + offsetSec * 1000).toISOString();
}

export const SAMPLE_RUN: RunDetail = {
  id: "run_7Qk2Xf9d",
  goal: "Compare managed Kubernetes offerings across AWS, GCP and Azure and recommend one for a 20-person startup",
  status: "completed",
  created_at: at(0),
  updated_at: at(214),
  tags: ["research", "kubernetes", "infra"],
  error: null,
  plan: {
    goal: "Compare managed Kubernetes offerings across AWS, GCP and Azure and recommend one for a 20-person startup",
    rationale:
      "Gather current pricing and control-plane details for EKS, GKE and AKS, weigh them against the operational constraints of a small team, then synthesize a recommendation with sourced evidence.",
    steps: [
      {
        id: "s1",
        title: "Collect control-plane pricing and SLAs",
        detail:
          "Retrieve per-cluster control-plane fees, node pricing model, and published SLAs for EKS, GKE Standard/Autopilot, and AKS.",
        depends_on: [],
        allowed_tools: ["web.search", "web.fetch"],
        requires_approval: false,
        status: "succeeded",
      },
      {
        id: "s2",
        title: "Assess operational burden for a small team",
        detail:
          "Compare upgrade automation, add-on management, autoscaling defaults, and day-2 operations across the three platforms.",
        depends_on: ["s1"],
        allowed_tools: ["web.search", "web.fetch"],
        requires_approval: false,
        status: "succeeded",
      },
      {
        id: "s3",
        title: "Score against startup constraints",
        detail:
          "Rank each option on cost-at-low-scale, time-to-productivity, ecosystem lock-in, and hiring pool, given a 20-person org.",
        depends_on: ["s1", "s2"],
        allowed_tools: ["compute.python"],
        requires_approval: false,
        status: "succeeded",
      },
      {
        id: "s4",
        title: "Synthesize recommendation report",
        detail:
          "Produce a sourced, decision-ready report with a single recommendation and the conditions under which it changes.",
        depends_on: ["s3"],
        allowed_tools: [],
        requires_approval: false,
        status: "succeeded",
      },
    ],
  },
  results: {
    s1: {
      step_id: "s1",
      attempt: 1,
      output:
        "EKS charges $0.10/hr per cluster control plane (~$73/mo) plus node cost. GKE Autopilot bills per pod resource with no per-cluster fee on the first cluster; GKE Standard charges $0.10/hr per cluster after the free tier. AKS charges no control-plane fee on the Free tier (best-effort SLA) and $0.10/hr for the Standard tier with a 99.95% uptime SLA.",
      tool_invocations: [
        {
          tool: "web.search",
          server: "search-mcp",
          arguments: { query: "EKS GKE AKS control plane pricing 2026" },
          result: { hits: 8 },
          ok: true,
          error: null,
          duration_ms: 1420,
          blocked_by_guardrail: false,
        },
        {
          tool: "web.fetch",
          server: "search-mcp",
          arguments: { url: "https://cloud.google.com/kubernetes-engine/pricing" },
          result: { bytes: 48213 },
          ok: true,
          error: null,
          duration_ms: 980,
          blocked_by_guardrail: false,
        },
      ],
      citations: ["1", "2"],
      tokens_used: 2100,
      succeeded: true,
      error: null,
    },
    s2: {
      step_id: "s2",
      attempt: 1,
      output:
        "GKE Autopilot removes node management entirely and auto-upgrades with maintenance windows. EKS requires managing node groups (or Fargate/Karpenter) and add-ons are largely opt-in. AKS sits in between with managed node upgrades and a curated add-on set.",
      tool_invocations: [
        {
          tool: "web.search",
          server: "search-mcp",
          arguments: { query: "GKE Autopilot vs EKS managed node upgrades day-2 ops" },
          result: { hits: 6 },
          ok: true,
          error: null,
          duration_ms: 1310,
          blocked_by_guardrail: false,
        },
      ],
      citations: ["3"],
      tokens_used: 1800,
      succeeded: true,
      error: null,
    },
    s3: {
      step_id: "s3",
      attempt: 1,
      output:
        "Weighted scoring (cost-at-low-scale 0.3, time-to-productivity 0.35, lock-in 0.15, hiring pool 0.2): GKE Autopilot 8.4, AKS 7.1, EKS 6.9. Autopilot wins on operational leverage for a small team despite a modest premium at scale.",
      tool_invocations: [
        {
          tool: "compute.python",
          server: "sandbox-mcp",
          arguments: { snippet: "score(weights, matrix)" },
          result: { gke: 8.4, aks: 7.1, eks: 6.9 },
          ok: true,
          error: null,
          duration_ms: 640,
          blocked_by_guardrail: false,
        },
      ],
      citations: [],
      tokens_used: 1500,
      succeeded: true,
      error: null,
    },
    s4: {
      step_id: "s4",
      attempt: 1,
      output: "Report synthesized.",
      tool_invocations: [],
      citations: ["1", "2", "3"],
      tokens_used: 2400,
      succeeded: true,
      error: null,
    },
  },
  critiques: [
    {
      target: "s1",
      passed: true,
      score: 0.91,
      issues: [],
      suggestions: ["Note the GKE Autopilot free-cluster caveat explicitly."],
      retry_recommended: false,
    },
    {
      target: "s4",
      passed: true,
      score: 0.88,
      issues: [],
      suggestions: [
        "State the break-even scale where EKS becomes cost-competitive.",
      ],
      retry_recommended: false,
    },
  ],
  report: {
    summary:
      "For a 20-person startup optimizing for operational leverage and time-to-productivity, GKE Autopilot is the recommended managed Kubernetes offering, with AKS Standard as the pragmatic fallback for Azure-centric teams.",
    confidence: 0.86,
    citations: [
      {
        marker: "1",
        source: "cloud.google.com",
        title: "Google Kubernetes Engine pricing",
        url: "https://cloud.google.com/kubernetes-engine/pricing",
        snippet:
          "Autopilot clusters are billed for the CPU, memory and storage that your Pods request while running.",
      },
      {
        marker: "2",
        source: "aws.amazon.com",
        title: "Amazon EKS pricing",
        url: "https://aws.amazon.com/eks/pricing/",
        snippet:
          "You pay $0.10 per hour for each Amazon EKS cluster that you create.",
      },
      {
        marker: "3",
        source: "learn.microsoft.com",
        title: "AKS pricing tiers and SLA",
        url: "https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers",
        snippet:
          "The Standard tier provides a financially backed uptime SLA of 99.95% for the Kubernetes API server.",
      },
    ],
    body_markdown: `## Recommendation

For a 20-person startup, adopt **GKE Autopilot**. It removes node-pool management and day-2 upgrade toil, which is the scarcest resource on a small team, at a control-plane cost comparable to the alternatives [1].

## How the three compare

| Offering | Control-plane cost | Ops burden | Best fit |
| --- | --- | --- | --- |
| GKE Autopilot | Per-Pod resource billing [1] | Lowest — no nodes to manage | Small teams, fast iteration |
| Amazon EKS | ~$73/mo per cluster [2] | Highest — node groups + add-ons | AWS-committed teams |
| AKS Standard | ~$73/mo, 99.95% SLA [3] | Moderate — managed upgrades | Azure-centric teams |

## Why Autopilot wins for this profile

- **Time-to-productivity.** There are no node pools to size, patch, or bin-pack. The team ships workloads on day one instead of building platform tooling.
- **Cost at low scale.** Per-Pod billing means you pay for requested resources rather than idle node headroom, which favors the spiky, low-utilization workloads typical early on [1].
- **Reliability.** The managed control plane and automatic upgrades reduce the surface area a small on-call rotation must cover.

## When to reconsider

- If the company is already AWS-committed with existing IAM, VPC and data-gravity there, **EKS** avoids a second cloud and its per-cluster fee is marginal at that point [2].
- At sustained high, steady utilization, self-managed node pools on EKS or GKE Standard can undercut Autopilot's per-Pod premium. Model the break-even before scaling past a few dozen always-on nodes.
- Azure-centric teams that want a financially backed SLA should pick **AKS Standard**, which offers a 99.95% API-server uptime guarantee [3].

## Bottom line

Start on GKE Autopilot, keep workloads portable with vanilla Kubernetes manifests, and revisit the decision only if cloud commitment or steady-state scale changes the economics.`,
  },
  pending_approvals: [],
};

// A pre-rendered activity timeline that mirrors what the SSE stream would have
// produced for the sample run. Ordered chronologically.
export const SAMPLE_TIMELINE: TimelineEvent[] = [
  {
    id: "e1",
    type: "run_created",
    at: at(0),
    step_id: null,
    agent: "orchestrator",
    payload: { goal: SAMPLE_RUN.goal },
  },
  {
    id: "e2",
    type: "run_status",
    at: at(1),
    step_id: null,
    agent: "orchestrator",
    payload: { status: "planning" },
  },
  {
    id: "e3",
    type: "agent_message",
    at: at(4),
    step_id: null,
    agent: "planner",
    payload: {
      text: "Breaking the goal into evidence gathering, an operational assessment, a weighted scoring pass, and a synthesis step. Pricing and ops details must come before scoring.",
    },
  },
  {
    id: "e4",
    type: "plan_created",
    at: at(7),
    step_id: null,
    agent: "planner",
    payload: { steps: 4 },
  },
  {
    id: "e5",
    type: "run_status",
    at: at(8),
    step_id: null,
    agent: "orchestrator",
    payload: { status: "executing" },
  },
  {
    id: "e6",
    type: "step_status",
    at: at(9),
    step_id: "s1",
    agent: "executor",
    payload: { from: "ready", to: "running" },
  },
  {
    id: "e7",
    type: "agent_message",
    at: at(11),
    step_id: "s1",
    agent: "executor",
    payload: {
      text: "Searching for current control-plane pricing across the three providers, then fetching the primary pricing pages to confirm figures.",
    },
  },
  {
    id: "e8",
    type: "tool_call",
    at: at(12),
    step_id: "s1",
    agent: "executor",
    payload: {
      tool: "web.search",
      server: "search-mcp",
      arguments: { query: "EKS GKE AKS control plane pricing 2026" },
    },
  },
  {
    id: "e9",
    type: "tool_result",
    at: at(14),
    step_id: "s1",
    agent: "executor",
    payload: { tool: "web.search", ok: true, duration_ms: 1420, result: { hits: 8 } },
  },
  {
    id: "e10",
    type: "tool_call",
    at: at(15),
    step_id: "s1",
    agent: "executor",
    payload: {
      tool: "web.fetch",
      server: "search-mcp",
      arguments: { url: "https://cloud.google.com/kubernetes-engine/pricing" },
    },
  },
  {
    id: "e11",
    type: "tool_result",
    at: at(16),
    step_id: "s1",
    agent: "executor",
    payload: { tool: "web.fetch", ok: true, duration_ms: 980, result: { bytes: 48213 } },
  },
  {
    id: "e12",
    type: "guardrail",
    at: at(17),
    step_id: "s1",
    agent: "guardrail",
    payload: {
      guardrail: "prompt-injection",
      action: "quarantined",
      detail: "Fetched page contained an embedded instruction to ignore prior context; content was quarantined and not executed.",
    },
  },
  {
    id: "e13",
    type: "critique",
    at: at(21),
    step_id: "s1",
    agent: "critic",
    payload: { target: "s1", passed: true, score: 0.91, issues: [] },
  },
  {
    id: "e14",
    type: "step_status",
    at: at(22),
    step_id: "s1",
    agent: "executor",
    payload: { from: "running", to: "succeeded" },
  },
  {
    id: "e15",
    type: "step_status",
    at: at(23),
    step_id: "s2",
    agent: "executor",
    payload: { from: "ready", to: "running" },
  },
  {
    id: "e16",
    type: "agent_message",
    at: at(25),
    step_id: "s2",
    agent: "executor",
    payload: {
      text: "Comparing upgrade automation and add-on management. Autopilot abstracts nodes entirely; EKS pushes node lifecycle onto the operator.",
    },
  },
  {
    id: "e17",
    type: "tool_call",
    at: at(26),
    step_id: "s2",
    agent: "executor",
    payload: {
      tool: "web.search",
      server: "search-mcp",
      arguments: { query: "GKE Autopilot vs EKS managed node upgrades day-2 ops" },
    },
  },
  {
    id: "e18",
    type: "tool_result",
    at: at(28),
    step_id: "s2",
    agent: "executor",
    payload: { tool: "web.search", ok: true, duration_ms: 1310, result: { hits: 6 } },
  },
  {
    id: "e19",
    type: "step_status",
    at: at(31),
    step_id: "s2",
    agent: "executor",
    payload: { from: "running", to: "succeeded" },
  },
  {
    id: "e20",
    type: "step_status",
    at: at(32),
    step_id: "s3",
    agent: "executor",
    payload: { from: "ready", to: "running" },
  },
  {
    id: "e21",
    type: "tool_call",
    at: at(34),
    step_id: "s3",
    agent: "executor",
    payload: {
      tool: "compute.python",
      server: "sandbox-mcp",
      arguments: { snippet: "score(weights, matrix)" },
    },
  },
  {
    id: "e22",
    type: "tool_result",
    at: at(35),
    step_id: "s3",
    agent: "executor",
    payload: {
      tool: "compute.python",
      ok: true,
      duration_ms: 640,
      result: { gke: 8.4, aks: 7.1, eks: 6.9 },
    },
  },
  {
    id: "e23",
    type: "agent_message",
    at: at(37),
    step_id: "s3",
    agent: "executor",
    payload: {
      text: "Weighted scores: GKE Autopilot 8.4, AKS 7.1, EKS 6.9. Operational leverage dominates the outcome at this team size.",
    },
  },
  {
    id: "e24",
    type: "step_status",
    at: at(39),
    step_id: "s3",
    agent: "executor",
    payload: { from: "running", to: "succeeded" },
  },
  {
    id: "e25",
    type: "step_status",
    at: at(40),
    step_id: "s4",
    agent: "writer",
    payload: { from: "ready", to: "running" },
  },
  {
    id: "e26",
    type: "critique",
    at: at(200),
    step_id: "s4",
    agent: "critic",
    payload: {
      target: "s4",
      passed: true,
      score: 0.88,
      issues: [],
      suggestions: ["State the break-even scale where EKS becomes cost-competitive."],
    },
  },
  {
    id: "e27",
    type: "report_ready",
    at: at(210),
    step_id: "s4",
    agent: "writer",
    payload: { confidence: 0.86 },
  },
  {
    id: "e28",
    type: "run_status",
    at: at(214),
    step_id: null,
    agent: "orchestrator",
    payload: { status: "completed" },
  },
];
