/**
 * 前端等价 discipline 校验：App 启动时跑一次，把违规项推到顶部 banner。
 *
 * 与 scripts/validate_data.py 保持同语义。
 */

import { isMetricInvalid } from './selectors';
import type { DataSnapshot } from './types';

export type Violation = {
  level: 'error' | 'warning';
  message: string;
  ref?: string;
};

const DATE_MIN = '1970-01-01';
const DATE_MAX = '2999-12-31';

export function checkData(snap: DataSnapshot): Violation[] {
  const out: Violation[] = [];

  // runId 唯一
  const seen = new Set<string>();
  for (const r of snap.runs) {
    if (seen.has(r.runId)) {
      out.push({ level: 'error', message: `runId 重复: ${r.runId}`, ref: r.runId });
    }
    seen.add(r.runId);

    if (r.date < DATE_MIN || r.date > DATE_MAX) {
      out.push({ level: 'warning', message: `日期越界 [${DATE_MIN}, ${DATE_MAX}]: ${r.runId} ${r.date}`, ref: r.runId });
    }

    if (r.kind === 'in-train-diagnostic' && !r.notes) {
      out.push({ level: 'warning', message: `in-train-diagnostic 缺 notes: ${r.runId}`, ref: r.runId });
    }

    if (
      r.compatibility.includes('comparable-with-blind-v6') &&
      r.compatibility.includes('historical-only')
    ) {
      out.push({ level: 'error', message: `compat 互斥: ${r.runId}`, ref: r.runId });
    }
  }

  // metric 字段
  for (const m of snap.metrics) {
    if (isMetricInvalid(m)) {
      out.push({ level: 'error', message: `metric 不合法: ${m.runId} ${m.metric}`, ref: m.runId });
    }
  }

  // overlap
  const ov = snap.overlap;
  if (ov) {
    const required = ov.whereFailures + ov.semanticFailures - ov.totalFailedRows;
    if (ov.intersection !== Math.max(required, 0)) {
      out.push({ level: 'error', message: `overlap 不自洽: expected intersection=${Math.max(required, 0)}, got ${ov.intersection}` });
    }
    if (ov.totalFailedRows !== 600) {
      out.push({ level: 'warning', message: `totalFailedRows ≠ 600: ${ov.totalFailedRows}` });
    }
  }

  // training
  for (const p of snap.training.points) {
    if (!Number.isFinite(p.loss) || p.loss < 0) {
      out.push({ level: 'error', message: `training loss 不合法: ${p.runId} epoch=${p.epoch}` });
    }
  }

  return out;
}

export function summaryViolations(vs: Violation[]): { errors: number; warnings: number } {
  return {
    errors: vs.filter((v) => v.level === 'error').length,
    warnings: vs.filter((v) => v.level === 'warning').length,
  };
}
