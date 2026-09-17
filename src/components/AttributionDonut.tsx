import { useMemo } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

type Props = {
  data: Record<string, number>;
  labelMap: Record<string, string>;
};

const COLORS = ['#2563EB', '#D97706', '#059669', '#DC2626', '#7C3AED', '#6B7280'];

export default function AttributionDonut({ data, labelMap }: Props) {
  const rows = useMemo(() => {
    const entries = Object.entries(data)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1]);
    return entries.map(([k, v]) => ({
      key: k,
      label: labelMap[k] ?? k,
      value: v,
    }));
  }, [data, labelMap]);

  const total = rows.reduce((s, r) => s + r.value, 0);

  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="label" innerRadius={50} outerRadius={80}>
            {rows.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number, n: string) => [`${v} (${((v / total) * 100).toFixed(1)}%)`, n]}
            contentStyle={{ fontSize: 12 }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="small muted" style={{ marginTop: 4 }}>
        总计 {total} 条；按 5 类主归因分解。
      </div>
    </div>
  );
}
