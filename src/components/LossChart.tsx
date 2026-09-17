import { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { TrainingPoint } from '../data/types';

type Props = {
  points: TrainingPoint[];
};

export default function LossChart({ points }: Props) {
  const { p4b, p9b } = useMemo(() => {
    const p4b = points.filter((p) => p.runId.includes('4b')).map((p) => ({ x: p.epoch, y: p.loss }));
    const p9b = points.filter((p) => p.runId.includes('9b')).map((p) => ({ x: p.epoch, y: p.loss }));
    return { p4b, p9b };
  }, [points]);

  // 合并数据用于 LineChart
  const data = useMemo(() => {
    const epochs = [1, 2, 3];
    return epochs.map((e) => ({
      epoch: e,
      '4B': p4b.find((p) => p.x === e)?.y,
      '9B': p9b.find((p) => p.x === e)?.y,
    }));
  }, [p4b, p9b]);

  return (
    <div>
      <div className="callout warn">
        <strong>仅 3 个真实数据点</strong>（4B / 9B 各 3 轮平均 loss）。本机无原始逐 step loss，不画完整曲线。
        291 步完整连续、日志 loss 与梯度无 NaN/Inf 仅作为聚合声明，详见 <code>data/training.json</code>。
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 16, right: 24, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="epoch"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            label={{ value: 'Epoch', position: 'insideBottom', offset: -12, fontSize: 12, fill: '#6B7280' }}
            type="number"
            domain={[0.5, 3.5]}
            ticks={[1, 2, 3]}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#6B7280' }}
            label={{ value: 'Loss（轮平均）', angle: -90, position: 'insideLeft', fontSize: 12, fill: '#6B7280' }}
          />
          <Tooltip
            formatter={(v: number) => v.toFixed(5)}
            labelFormatter={(l) => `Epoch ${l}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="4B" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} connectNulls={false} name="4B（轮平均）" />
          <Line type="monotone" dataKey="9B" stroke="#D97706" strokeWidth={2} dot={{ r: 4 }} connectNulls={false} name="9B（轮平均）" />
        </LineChart>
      </ResponsiveContainer>
      <table style={{ marginTop: 12 }}>
        <thead>
          <tr>
            <th>Epoch</th>
            <th>4B</th>
            <th>9B</th>
          </tr>
        </thead>
        <tbody>
          {[1, 2, 3].map((e) => (
            <tr key={e}>
              <td>{e}</td>
              <td className="mono">{p4b.find((p) => p.x === e)?.y?.toFixed(5) ?? '—'}</td>
              <td className="mono">{p9b.find((p) => p.x === e)?.y?.toFixed(5) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
