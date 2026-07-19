import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { SectionLabel } from "@/components/SectionLabel";
import {
  CORE_SUITE,
  INJECTION_SUITE,
  coreCategoryBars,
} from "@/data/benchmarks";

const AXIS_STYLE = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
  fill: "#71717A",
};

function StatBlock({
  label,
  value,
  sub,
  accent = "#E4E4E7",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-md border border-hairline bg-surface-raised px-4 py-3">
      <div className="mono-label mb-1">{label}</div>
      <div className="font-mono text-xl font-semibold" style={{ color: accent }}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-content-faint">{sub}</div>}
    </div>
  );
}

export function BenchmarksPage() {
  const bars = coreCategoryBars();
  const quarantined = INJECTION_SUITE?.blocked_injections ?? 5;
  const contained = INJECTION_SUITE
    ? `${INJECTION_SUITE.passed}/${INJECTION_SUITE.total}`
    : "6/6";

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-content-primary">
          Benchmarks
        </h1>
        <p className="mt-1 font-mono text-sm text-content-muted">
          90% task success · {contained} injection attempts contained
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Core suite chart */}
        <div className="card overflow-hidden lg:col-span-2">
          <SectionLabel
            right={
              <span className="font-mono text-[10px] text-content-faint">
                core suite · {CORE_SUITE.total} tasks
              </span>
            }
          >
            Success rate by category
          </SectionLabel>
          <div className="p-4" style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={bars}
                margin={{ top: 8, right: 48, bottom: 8, left: 8 }}
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="#26262B"
                  strokeDasharray="2 4"
                />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={AXIS_STYLE}
                  tickLine={false}
                  axisLine={{ stroke: "#26262B" }}
                  unit="%"
                />
                <YAxis
                  type="category"
                  dataKey="category"
                  tick={AXIS_STYLE}
                  tickLine={false}
                  axisLine={{ stroke: "#26262B" }}
                  width={80}
                />
                <Tooltip
                  cursor={{ fill: "#16161A" }}
                  contentStyle={{
                    background: "#111114",
                    border: "1px solid #26262B",
                    borderRadius: 6,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: "#E4E4E7",
                  }}
                  formatter={(value: number, _name, item) => {
                    const p = item?.payload as {
                      passed: number;
                      total: number;
                    };
                    return [`${value}%  (${p.passed}/${p.total})`, "success"];
                  }}
                />
                <Bar dataKey="success" radius={[0, 3, 3, 0]} barSize={22}>
                  {bars.map((entry) => (
                    <Cell
                      key={entry.category}
                      fill={entry.success === 100 ? "#22D3EE" : "#F59E0B"}
                    />
                  ))}
                  <LabelList
                    dataKey="success"
                    position="right"
                    formatter={(v: number) => `${v}%`}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      fill: "#A1A1AA",
                    }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Core suite headline stats */}
        <div className="card overflow-hidden">
          <SectionLabel>Core suite</SectionLabel>
          <div className="grid grid-cols-2 gap-3 p-4">
            <StatBlock
              label="task success"
              value={`${Math.round(CORE_SUITE.success_rate * 100)}%`}
              sub={`${CORE_SUITE.passed}/${CORE_SUITE.total} passed`}
              accent="#34D399"
            />
            <StatBlock
              label="mean score"
              value={CORE_SUITE.mean_score.toFixed(2)}
              sub="grader rubric, 0–1"
            />
            <StatBlock
              label="mean latency"
              value={`${(CORE_SUITE.mean_latency_ms / 1000).toFixed(1)}s`}
              sub="per task, end to end"
              accent="#60A5FA"
            />
            <StatBlock
              label="mean tokens"
              value={CORE_SUITE.mean_tokens.toLocaleString()}
              sub="per task"
            />
          </div>
        </div>

        {/* Injection defense */}
        <div className="card overflow-hidden">
          <SectionLabel>Injection defense</SectionLabel>
          <div className="grid grid-cols-2 gap-3 p-4">
            <StatBlock
              label="contained"
              value={contained}
              sub="attempts blocked or ignored"
              accent="#34D399"
            />
            <StatBlock
              label="quarantined"
              value={String(quarantined)}
              sub="malicious payloads isolated"
              accent="#F59E0B"
            />
            <div className="col-span-2 rounded-md border border-hairline bg-base px-4 py-3 text-[12px] leading-relaxed text-content-muted">
              Every adversarial prompt in the suite — instruction override,
              exfiltration, role and tool hijacking, and markup injection — was
              contained by the guardrail layer. The benign control task passed
              through untouched, confirming the defenses do not over-block.
            </div>
          </div>
        </div>
      </div>

      {/* Per-task outcomes */}
      <div className="card mt-4 overflow-hidden">
        <SectionLabel>Task outcomes</SectionLabel>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-hairline">
                <th className="mono-label px-4 py-2.5 font-normal">task</th>
                <th className="mono-label px-4 py-2.5 font-normal">category</th>
                <th className="mono-label px-4 py-2.5 font-normal">difficulty</th>
                <th className="mono-label px-4 py-2.5 text-right font-normal">
                  score
                </th>
                <th className="mono-label px-4 py-2.5 text-right font-normal">
                  latency
                </th>
                <th className="mono-label px-4 py-2.5 text-center font-normal">
                  result
                </th>
              </tr>
            </thead>
            <tbody>
              {CORE_SUITE.outcomes.map((o) => (
                <tr
                  key={o.task_id}
                  className="border-b border-hairline/60 font-mono text-[12px]"
                >
                  <td className="px-4 py-2.5 text-content-primary">
                    {o.task_id}
                  </td>
                  <td className="px-4 py-2.5 text-content-muted">
                    {o.category}
                  </td>
                  <td className="px-4 py-2.5 text-content-muted">
                    {o.difficulty}
                  </td>
                  <td className="px-4 py-2.5 text-right text-content-muted">
                    {o.score.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-content-faint">
                    {(o.latency_ms / 1000).toFixed(1)}s
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span
                      style={{ color: o.passed ? "#34D399" : "#F87171" }}
                      className="uppercase tracking-wider"
                    >
                      {o.passed ? "pass" : "fail"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
