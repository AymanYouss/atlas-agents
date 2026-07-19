import raw from "./benchmarks.json";

export interface CategoryStat {
  total: number;
  passed: number;
  success_rate: number;
}

export interface BenchmarkOutcome {
  task_id: string;
  category: string;
  difficulty: string;
  passed: boolean;
  score: number;
  steps: number;
  tokens: number;
  latency_ms: number;
  citations: number;
  blocked_injections: number;
  notes: string[];
}

export interface BenchmarkSuite {
  suite: string;
  created_at: string;
  total: number;
  passed: number;
  success_rate: number;
  mean_score: number;
  mean_tokens: number;
  mean_latency_ms: number;
  blocked_injections: number;
  by_category: Record<string, CategoryStat>;
  by_difficulty: Record<string, CategoryStat>;
  outcomes: BenchmarkOutcome[];
}

const suites = raw as unknown as BenchmarkSuite[];

export const CORE_SUITE: BenchmarkSuite =
  suites.find((s) => s.suite === "core") ?? suites[0];

export const INJECTION_SUITE: BenchmarkSuite | undefined = suites.find(
  (s) => s.suite === "injection",
);

export function coreCategoryBars(): { category: string; success: number; passed: number; total: number }[] {
  return Object.entries(CORE_SUITE.by_category).map(([category, stat]) => ({
    category,
    success: Math.round(stat.success_rate * 100),
    passed: stat.passed,
    total: stat.total,
  }));
}
