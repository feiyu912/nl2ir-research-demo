import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DataSnapshot, Metric, MetricName, ModelId } from '../data/types';
import { METRIC_LABEL } from '../data/types';

type Props = {
  data: DataSnapshot;
  metric: MetricName;
  selectedRunIds: string[];
  height?: number;
};

const MODEL_COLOR: Record<ModelId, string> = {
  '4B': '#2563EB',
  '9B': '#D97706',
  API: '#059669',
};

export default function MetricBarChart({ data, metric, selectedRunIds, height = 280 }: Props) {
  const rows = useMemo(() => {
    const runs = data.runs.filter((r) => selectedRunIds.includes(r.runId));
    return runs.map((r) => {
      const m: Metric | undefined = data.metrics.find(
        (x) => x.runId === r.runId && x.metric === metric
      );
      return {
        runId: r.runId,
        label: `${r.model}·${r.dataset}`,
        model: r.model,
        kind: r.kind,
        correct: m?.correct ?? 0,
        total: m?.total ?? 0,
        accuracy: m?.accuracy ?? 0,
      };
    });
  }, [data, metric, selectedRunIds]);

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} margin={{ top: 12, right: 16, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            angle={-15}
            textAnchor="end"
            height={48}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            domain={[0, 1]}
          />
          <Tooltip
            formatter={(_value: number, _name, props) => {
              const r = props.payload;
              if (!r) return [''];
              return [
                `${r.correct}/${r.total} (${(r.accuracy * 100).toFixed(2)}%)`,
                METRIC_LABEL[metric],
              ];
            }}
            labelFormatter={(l) => `Run: ${l}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="accuracy" name={METRIC_LABEL[metric]}>
            {rows.map((r, i) => (
              <Cell key={i} fill={MODEL_COLOR[r.model as ModelId]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="small muted" style={{ marginTop: 6 }}>
        分母与样本数在 tooltip 中显示。所有指标渲染为 <code>correct/total (xx.xx%)</code>，从不加和。
      </div>
    </div>
  );
}
