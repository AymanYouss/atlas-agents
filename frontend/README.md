# Atlas — frontend

The web control plane for Atlas, a self-hosted multi-agent platform. It lets you
submit goals, watch the planner / executor / critic agents work in real time over
a live event stream, review guardrail activity, approve gated actions, and read
the synthesized report with sourced citations.

Built with Vite, React 18, TypeScript (strict), Tailwind CSS, React Router,
TanStack Query, and Recharts.

## Requirements

- Node 20+
- pnpm

## Setup

```bash
pnpm install
cp .env.example .env   # optional; defaults to http://localhost:8000
pnpm dev
```

The dev server proxies `/api` and `/healthz` to the backend at
`http://localhost:8000`. To point at a different backend, set `VITE_API_BASE`.

## Scripts

| Script            | Purpose                                  |
| ----------------- | ---------------------------------------- |
| `pnpm dev`        | Start the Vite dev server                |
| `pnpm build`      | Type-check the project and build to `dist` |
| `pnpm preview`    | Serve the production build locally       |
| `pnpm typecheck`  | Run `tsc --noEmit`                       |
| `pnpm lint`       | Run ESLint                               |

## Environment

| Variable        | Default                 | Description               |
| --------------- | ----------------------- | ------------------------- |
| `VITE_API_BASE` | `http://localhost:8000` | Base URL for the Atlas API |

## Routes

- `/` — dashboard: run composer, benchmark metrics, recent runs
- `/runs` — paginated list of all runs
- `/runs/:id` — live run visualizer (plan / activity stream / report + approvals)
- `/benchmarks` — evaluation results (success by category, injection defense)
- `/demo` — the visualizer populated from a bundled sample run, no backend needed

## Structure

```
src/
  api/         typed API client and contract types
  components/   presentational + composite UI (visualizer, plan tree, timeline…)
  data/         bundled benchmark results and the demo run fixture
  hooks/        useRunStream — EventSource lifecycle + event reducer
  lib/          formatting and status helpers
  pages/        route-level screens
```

The run visualizer components take their data via props, so the live view
(`/runs/:id`) and the offline demo (`/demo`) share exactly the same rendering.
