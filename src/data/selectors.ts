/**
 * 派生 selector：按 model/dataset/kind 过滤、做指标聚合。
 * 不修改原始数据。
 */

import type { Metric, MetricName, ModelId, Run, RunKind } from './types';

export function filterRuns(runs: Run[], opts: {
  models?: ModelId[];
  datasets?: string[];
  kinds?: RunKind[];
}): Run[] {
  return runs.filter((r) => {
    if (opts.models && !opts.models.includes(r.model)) return false;
    if (opts.datasets && !opts.datasets.includes(r.dataset)) return false;
    if (opts.kinds && !opts.kinds.includes(r.kind)) return false;
    return true;
  });
}

export function metricsByRun(metrics: Metric[]): Map<string, Metric[]> {
  const map = new Map<string, Metric[]>();
  for (const m of metrics) {
    const arr = map.get(m.runId) ?? [];
    arr.push(m);
    map.set(m.runId, arr);
  }
  return map;
}

export function getMetric(metrics: Metric[], runId: string, metric: MetricName): Metric | undefined {
  return metrics.find((m) => m.runId === runId && m.metric === metric);
}

/**
 * Canonical Where 派生。
 *
 * 不同管线走过的 canonicalization 阶段不同：
 * - 学生（未跑 deterministic_where_canonicalization 阶段）→ main_chain_where
 * - 强 API（candidate_v4 含 4 阶段含 deterministic_where_canonicalization）→ order_value_invariant_where
 *
 * 这是口径差异，不是数据问题。Overview / 6 组评测表使用此函数。
 */
export function getCanonicalWhere(
  metrics: Metric[],
  runId: string,
  model?: '4B' | '9B' | 'API'
): Metric | undefined {
  // 模型信息不在这里查（避免循环依赖）；调用方传 model
  const metricName: MetricName =
    model === 'API' ? 'order_value_invariant_where' : 'main_chain_where';
  return getMetric(metrics, runId, metricName);
}

/**
 * 不允许 sum_accuracy：仅返回每行的 correct/total + accuracy。
 */
export function formatRatio(correct: number, total: number, digits = 2): string {
  if (total === 0) return '数据缺失';
  const pct = (correct / total) * 100;
  return `${correct}/${total} (${pct.toFixed(digits)}%)`;
}

/**
 * 校验 single 行（被前端 discipline.ts 复用）。
 */
export function isMetricInvalid(m: Metric): boolean {
  if (m.correct > m.total) return true;
  if (m.total === 0) return false;
  if (Math.abs(m.accuracy - m.correct / m.total) > 0.005) return true;
  if (m.ci95) {
    const [lo, hi] = m.ci95;
    if (lo < 0 || hi > 1 || lo > hi) return true;
  }
  return false;
}
