import { useState } from 'react';
import type {
  DataSnapshot,
  HistoricalExperiment,
  HistoricalExperimentGroup,
  Metric,
  MetricName,
} from '../data/types';
import { ALL_METRICS, METRIC_LABEL } from '../data/types';
import FilterBar from '../components/FilterBar';
import RunBadge, { KindBadge } from '../components/RunBadge';

type Props = { data: DataSnapshot };

export default function ExperimentsData({ data }: Props) {
  const [tab, setTab] = useState<'groups' | 'runs'>('groups');
  const [metric, setMetric] = useState<MetricName>('main_chain_where');
  const groups = data.historicalExperiments?.groups ?? [];

  return (
    <>
      <div className="page-header">
        <h1>实验与数据</h1>
        <div className="subtitle">
          覆盖前人交接、压缩对照、规则优化、诊断、最终 v21 等不同阶段的实验与证据；
          按研究问题分组（不按时间线）。
        </div>
      </div>

      <div className="takeaway">
        <strong>分组浏览：</strong>
        按 8 个研究问题分组（接手 8B 基线、资源适配、prompt 压缩对照、规则优化、泛化差距、难题诊断、审计 repair/gate、最终 v21）。
        每个分组含关键对照与配套实验；完整指标矩阵在折叠区。
      </div>

      <section className="section">
        <FilterBar>
          <label>
            视图：
            <select value={tab} onChange={(e) => setTab(e.target.value as 'groups' | 'runs')}>
              <option value="groups">按问题分组的实验</option>
              <option value="runs">当前 8 Run 完整指标矩阵</option>
            </select>
          </label>
        </FilterBar>

        {tab === 'groups' ? (
          <HistoricalGroups groups={groups} />
        ) : (
          <FullRunsMatrix data={data} metric={metric} setMetric={setMetric} />
        )}
      </section>

      {/* 历史 vs 正式纪律 */}
      <section className="section">
        <h2>历史 vs 正式（口径红线）</h2>
        <HistoricalDiscipline />
      </section>
    </>
  );
}

/* 按研究问题分组的实验 */
function HistoricalGroups({ groups }: { groups: HistoricalExperimentGroup[] }) {
  return (
    <div>
      <div className="small fg-2" style={{ marginBottom: 14 }}>
        每组展示关键对照与结论；点击展开看完整记录（模型 / prompt / 数据 / 指标 / 状态 / 来源 / 备注）。
      </div>
      <div className="flex-col" style={{ gap: 12 }}>
        {groups.map((g) => (
          <div key={g.id} className="card">
            <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
              <h3 style={{ margin: 0 }}>{g.title}</h3>
              <span className="badge">{g.experiments.length} 条</span>
            </div>
            {g.purpose ? (
              <div className="small fg-2" style={{ marginTop: 4 }}>{g.purpose}</div>
            ) : null}
            <table style={{ marginTop: 12 }}>
              <thead>
                <tr>
                  <th style={{ width: '34%' }}>实验</th>
                  <th>条件 / 结果</th>
                </tr>
              </thead>
              <tbody>
                {g.experiments.map((e, i) => (
                  <ExpRow key={i} exp={e} />
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExpRow({ exp }: { exp: HistoricalExperiment }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr>
        <td>
          <strong>{exp.label}</strong>
          {exp.note ? (
            <div className="small fg-2" style={{ marginTop: 2 }}>{exp.note}</div>
          ) : null}
        </td>
        <td>
          <div className="kv-row" style={{ paddingTop: 4 }}>
            <span className="kv-key">{exp.model ?? '—'}</span>
            <span className="kv-val">{exp.metric ?? '—'}</span>
          </div>
          <div style={{ marginTop: 6 }}>
            <span className="badge" style={{ fontSize: 11 }}>{exp.status}</span>
          </div>
        </td>
      </tr>
      {open ? (
        <tr>
          <td colSpan={2} style={{ background: 'var(--surface-2)', padding: 14 }}>
            <div className="kv-row"><span className="kv-key">模型</span><span className="kv-val">{exp.model ?? '—'}</span></div>
            <div className="kv-row"><span className="kv-key">Prompt</span><span className="kv-val">{exp.prompt ?? '—'}</span></div>
            <div className="kv-row"><span className="kv-key">数据集 / Gold</span><span className="kv-val">{exp.dataset ?? '—'}</span></div>
            <div className="kv-row"><span className="kv-key">指标</span><span className="kv-val">{exp.metric ?? '—'}</span></div>
            {exp.source ? (
              <div className="kv-row">
                <span className="kv-key">来源</span>
                <span className="kv-val small mono">{exp.source}</span>
              </div>
            ) : null}
          </td>
        </tr>
      ) : null}
      <tr>
        <td colSpan={2} style={{ padding: 0, border: 'none' }}>
          <button
            onClick={() => setOpen(!open)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--primary)',
              cursor: 'pointer',
              fontSize: 12,
              padding: '4px 0 12px 0',
              width: '100%',
              textAlign: 'left',
            }}
          >
            {open ? '收起详情' : '展开详情（来源 / 备注）'}
          </button>
        </td>
      </tr>
    </>
  );
}

/* 当前 8 Run 完整指标矩阵（折叠区） */
function FullRunsMatrix({ data, metric, setMetric }: { data: DataSnapshot; metric: MetricName; setMetric: (m: MetricName) => void }) {
  return (
    <div>
      <FilterBar>
        <label>
          指标：
          <select value={metric} onChange={(e) => setMetric(e.target.value as MetricName)}>
            {ALL_METRICS.map((m) => (
              <option key={m} value={m}>
                {METRIC_LABEL[m]}
              </option>
            ))}
          </select>
        </label>
      </FilterBar>

      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>数据集</th>
            <th>Kind</th>
            {ALL_METRICS.map((m) => (
              <th key={m} style={{ whiteSpace: 'nowrap' }}>
                {METRIC_LABEL[m]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.runs.map((r) => (
            <tr key={r.runId}>
              <td>
                <RunBadge model={r.model} />
                <div className="small num muted">{r.runId}</div>
              </td>
              <td>
                <span className="badge">{r.dataset}</span>
                <div className="small fg-2">{r.sampleSize} 条 · {r.datasetVersion}</div>
              </td>
              <td>
                <KindBadge kind={r.kind} size="sm" />
              </td>
              {ALL_METRICS.map((m) => {
                const row: Metric | undefined = data.metrics.find((x) => x.runId === r.runId && x.metric === m);
                if (!row) {
                  return (
                    <td key={m} className="muted-cell">—</td>
                  );
                }
                return (
                  <td key={m} className="num">
                    {row.correct}/{row.total}
                    <div className="small fg-2">{(row.accuracy * 100).toFixed(2)}%</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoricalDiscipline() {
  return (
    <ul className="small" style={{ paddingLeft: 20 }}>
      <li><strong>接手 8B 基线</strong>：明确标为前人交接实验；不在本机复跑，仅引用原始记录。</li>
      <li><strong>未微调底座对照</strong>：本机无原始预测；当前 v21 未完成未微调底座对照。</li>
      <li><strong>旧集 API 的 356/366 (97.27%)</strong>：开发口径，不是新 blind。</li>
      <li><strong>C300 历史 API 的 271/300 (90.33%)</strong>：v19 口径，不是 v21 Gold 重评分。</li>
      <li><strong>blind-v4 post-hoc 237/240 (98.75%)</strong>：不能标为正式 untouched blind。</li>
      <li><strong>C-hard240</strong>：是训练监督，不是独立验证；训练内 100% ≠ 泛化 100%。</li>
      <li><strong>old366 / C300</strong>：开发回归/诊断集；C-hard240 才进入联合训练；blind-v6 未进入训练。</li>
      <li><strong>不同数据集 / Gold / 评分口径不连成一条曲线</strong>。</li>
      <li><strong>API 门控 ≠ 学生裸输出</strong>（不同流程）。</li>
      <li><strong>旧集 API「约97%」</strong>是 v19 final 在 old370 上的放宽口径 355/370 (95.95%)，不是后来 v21 的 356/366。</li>
    </ul>
  );
}