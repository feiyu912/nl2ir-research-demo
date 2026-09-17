import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DataSnapshot, ModelId } from '../data/types';
import { getCanonicalWhere } from '../data/selectors';

type Props = {
  data: DataSnapshot;
  height?: number;
};

const COLOR: Record<ModelId, string> = {
  '4B': '#2563EB',
  '9B': '#EA580C',
  API: '#047857',
};

const COLOR_API_GATED = '#0F766E'; // 门控后用更深的青绿，与 API 单次区分

/**
 * 按数据集分组的横向条形图：
 * 每个数据集一行；每个组组（4B / 9B / API 单次 / API 门控）一根条。
 * 条尾直接标注 correct/total + 百分比。
 */
export default function GroupedMetricChart({ data, height = 280 }: Props) {
  const datasets = ['blind-v6', 'C300', 'old366'] as const;
  const datasetLabels: Record<typeof datasets[number], string> = {
    'blind-v6': 'sealed blind-v6（240 条）',
    C300: 'C300 诊断集（300 条）',
    old366: 'old366 诊断集（366 条）',
  };

  const rows = datasets.map((d) => {
    const apiOnePass = getCanonicalWhere(data.metrics, 'api-blindv6-one-pass', 'API');
    const apiAssert = getCanonicalWhere(data.metrics, 'api-blindv6-assertion-v7', 'API');
    const stu4b = d === 'blind-v6' ? getCanonicalWhere(data.metrics, '4b-blindv6', '4B') :
      d === 'C300' ? getCanonicalWhere(data.metrics, '4b-c300', '4B') :
      getCanonicalWhere(data.metrics, '4b-old366', '4B');
    const stu9b = d === 'blind-v6' ? getCanonicalWhere(data.metrics, '9b-blindv6-initial', '9B') :
      d === 'C300' ? getCanonicalWhere(data.metrics, '9b-c300', '9B') :
      getCanonicalWhere(data.metrics, '9b-old366', '9B');

    const items = [
      { key: '4B', label: '4B 裸输出', val: stu4b?.accuracy ?? null, total: stu4b?.total ?? null, correct: stu4b?.correct ?? null, color: COLOR['4B'] },
      { key: '9B', label: '9B 裸输出', val: stu9b?.accuracy ?? null, total: stu9b?.total ?? null, correct: stu9b?.correct ?? null, color: COLOR['9B'] },
      { key: 'API', label: 'API 单次', val: apiOnePass?.accuracy ?? null, total: apiOnePass?.total ?? null, correct: apiOnePass?.correct ?? null, color: COLOR.API },
      { key: 'API-gated', label: 'API 门控后', val: apiAssert?.accuracy ?? null, total: apiAssert?.total ?? null, correct: apiAssert?.correct ?? null, color: COLOR_API_GATED },
    ];
    return { dataset: datasetLabels[d], shortKey: d, items };
  });

  // 把每行拆出 4 条 bar，并给唯一 key
  const flat: Array<{ label: string; ds: string; val: number; total: number; correct: number; color: string }> = [];
  for (const r of rows) {
    for (const it of r.items) {
      if (it.val === null) {
        flat.push({ label: `${r.shortKey} · ${it.label}`, ds: r.dataset, val: 0, total: it.total ?? 0, correct: 0, color: it.color });
      } else {
        flat.push({
          label: `${r.shortKey} · ${it.label}`,
          ds: r.dataset,
          val: it.val * 100,
          total: it.total ?? 0,
          correct: it.correct ?? 0,
          color: it.color,
        });
      }
    }
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={flat}
          layout="vertical"
          margin={{ top: 8, right: 80, bottom: 8, left: 16 }}
          barCategoryGap={6}
        >
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12, fill: '#94A3B8' }} />
          <YAxis type="category" dataKey="label" tick={{ fontSize: 12, fill: '#475569' }} width={150} />
          <Tooltip
            formatter={(value: number, _name: unknown, props: unknown) => {
              const p = (props as { payload?: { correct: number; total: number; ds: string } }).payload;
              if (!p || !p.total) return [`${value}`, ''];
              return [`${p.correct}/${p.total} (${((p.correct / p.total) * 100).toFixed(2)}%)`, p.ds];
            }}
            contentStyle={{ fontSize: 13, borderRadius: 6, border: '1px solid #E2E8F0' }}
          />
          <Bar dataKey="val" radius={[0, 4, 4, 0]} barSize={14}>
            {flat.map((f, i) => (
              <Cell key={i} fill={f.color} />
            ))}
            <LabelList
              dataKey="val"
              position="right"
              formatter={(v: number, _n: unknown, props: unknown) => {
                const p = (props as { payload?: { correct: number; total: number } }).payload;
                if (!p) return '';
                return `${p.correct}/${p.total} · ${v.toFixed(1)}%`;
              }}
              style={{ fontSize: 12, fill: '#1F2328', fontWeight: 500 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="small fg-2" style={{ marginTop: 6 }}>
        指标：Canonical Where（4B/9B = main_chain_where；API = order_value_invariant_where）。门控后是额外 8 次 API 调用 + 条件修复。
      </div>
    </div>
  );
}