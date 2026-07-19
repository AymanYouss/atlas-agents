# Architecture

Atlas turns a natural-language goal into a verified, citation-backed report through a
planner–executor–critic loop running on a durable orchestration graph.

![Architecture](portfolio/01-architecture.png)

## Request lifecycle

1. **Create** — `POST /api/runs` persists a `RunRecord` and launches the run in the
   background. The client opens `GET /api/runs/{id}/events` (Server-Sent Events) to
   stream the timeline.
2. **Plan** — the **Planner** (a strong reasoning model) decomposes the goal into a
   validated DAG of steps. Each step declares its dependencies, an allow-list of
   tools it may call, and whether it needs human approval.
3. **Execute** — independent steps run concurrently. Each **Executor** runs a
   provider-agnostic **ReAct loop**: think → call one allow-listed tool → observe →
   repeat, until it produces a final answer. Every tool result is scanned for prompt
   injection and fenced as untrusted data before it re-enters the model context.
4. **Verify** — the **Critic** independently scores each step. A failing step with a
   recommended retry runs again with the critic's guidance; a blocked plan triggers a
   **replan**.
5. **Synthesize** — once the plan resolves, the **Synthesizer** streams the final
   Markdown report token-by-token and attaches the numbered citations that were
   actually referenced. The critic reviews the report and assigns a confidence score.

## Durable execution

The orchestrator is a [LangGraph](https://langchain-ai.github.io/langgraph/) state
machine: `plan → execute → (retry | replan | synthesize) → finalize`. State is
checkpointed after every node to Postgres (`AsyncPostgresSaver`). If the process
crashes mid-run, another process rebuilds the run context and resumes from the last
committed checkpoint — no work is repeated.

Non-serializable per-run objects (LLM clients, the tool registry, the budget) live in
a process-local `RunContext` keyed by `run_id`, keeping the checkpointed state small
and JSON-clean.

## Human-in-the-loop

When a ready step is flagged `requires_approval` (and auto-approve is off), the graph
calls LangGraph's `interrupt`, which durably suspends the run. The API surfaces the
pending request; a reviewer approves, rejects, or edits the instruction, and the run
resumes with `Command(resume=...)`.

## The tool layer (MCP)

Executors never touch tools directly — they go through the **Tool Registry**, the
single choke point that enforces per-step allow-lists, records every invocation with
latency and outcome, and emits metrics.

Tools come from two interchangeable sources:

- **Built-in** (`web_search`, `http_fetch`, `code_exec`, `file_io`) — in-process for
  low latency.
- **MCP** — the `MCPClientManager` attaches any stdio/SSE Model Context Protocol
  server, discovers its tools, and wraps each as a native Atlas tool. Atlas also runs
  *as* an MCP server (`python -m atlas.mcp.server`), exposing its own tools to other
  MCP clients.

## Code sandbox

`code_exec` runs untrusted, model-generated code in a throwaway Docker container that
is hardened by default: `--network none`, dropped Linux capabilities,
`no-new-privileges`, a read-only root filesystem with a size-capped tmpfs workspace,
CPU/memory/PID limits, a non-root user, and a hard wall-clock timeout enforced by
killing the container. The driver interface is transport-agnostic, so a Firecracker
or gVisor backend can replace Docker without touching any caller.

## Guardrails

- **Prompt-injection scanner** — inspects untrusted tool output against explainable,
  categorized rules (instruction override, role manipulation, system-prompt leak,
  exfiltration, tool hijack). High-severity content is quarantined rather than fed
  back to the model. All untrusted text is additionally fenced with a non-forgeable
  boundary marking it as data.
- **Runtime budgets** — hard ceilings on steps, retries per step, tokens, and
  wall-clock time, plus runaway-loop detection via repeated action fingerprints.

## Observability

Every meaningful moment is published as a typed `RunEvent` through an in-process
broker with a replay buffer, fanned out to browsers over SSE and persisted to Postgres
for durable replay (`Last-Event-ID` reconnects resume cleanly). Prometheus metrics are
exposed at `/metrics`.

## Evaluation

The eval harness (`atlas.eval`) runs benchmark tasks through the real orchestrator and
scores them with deterministic, dependency-free rule-based scorers (keyword coverage,
citation adequacy, safety), aggregating task-success rate, cost, and injection-defense
metrics by category and difficulty. See [`benchmarks/results.json`](benchmarks/results.json).
