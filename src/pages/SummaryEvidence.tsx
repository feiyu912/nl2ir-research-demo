import { useMemo, useState } from 'react';
import type { Conclusion, DataSnapshot, SourceRef } from '../data/types';
import FilterBar from '../components/FilterBar';
import SourceLinker from '../components/SourceLinker';

type Props = { data: DataSnapshot };

const CATEGORY_LABEL: Record<Conclusion['category'], string> = {
  fact: '已证实事实',
  interpretation: '解释边界',
  hypothesis: '待验证假设',
  plan: '后续计划',
};

const CATEGORY_TONE: Record<Conclusion['category'], string> = {
  fact: 'var(--ok)',
  interpretation: 'var(--c-4b)',
  hypothesis: 'var(--warn)',
  plan: 'var(--muted)',
};

export default function SummaryEvidence({ data }: Props) {
  const [stageFilter, setStageFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [showSources, setShowSources] = useState(false);

  const stages = useMemo(
    () => Array.from(new Set(data.conclusions.map((c) => c.stage))).sort(),
    [data.conclusions]
  );

  const filtered = useMemo(() => {
    return data.conclusions.filter((c) => {
      if (stageFilter !== 'all' && c.stage !== stageFilter) return false;
      if (categoryFilter !== 'all' && c.category !== categoryFilter) return false;
      if (search && !c.text.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [data.conclusions, stageFilter, categoryFilter, search]);

  // 来源按 kind 分组（紧凑）
  const sourcesByKind = useMemo(() => {
    const m = new Map<string, SourceRef[]>();
    for (const r of data.sources) {
      const arr = m.get(r.kind) ?? [];
      arr.push(r);
      m.set(r.kind, arr);
    }
    return m;
  }, [data.sources]);

  // 阶段摘要：6 阶段 × 已证实/解释/待验证 计数
  const stageSummary = useMemo(() => {
    const researchStages = data.researchTimeline ?? [];
    const byStage: Record<string, Record<Conclusion['category'], number>> = {};
    for (const s of researchStages) {
      byStage[s.stage] = { fact: 0, interpretation: 0, hypothesis: 0, plan: 0 };
    }
    for (const c of data.conclusions) {
      if (!byStage[c.stage]) {
        byStage[c.stage] = { fact: 0, interpretation: 0, hypothesis: 0, plan: 0 };
      }
      byStage[c.stage][c.category] = (byStage[c.stage][c.category] ?? 0) + 1;
    }
    return researchStages.map((s) => ({
      stage: s,
      counts: byStage[s.stage] ?? { fact: 0, interpretation: 0, hypothesis: 0, plan: 0 },
    }));
  }, [data.conclusions, data.researchTimeline]);

  const totalByCategory = useMemo(() => {
    const m: Record<Conclusion['category'], number> = { fact: 0, interpretation: 0, hypothesis: 0, plan: 0 };
    for (const c of data.conclusions) {
      m[c.category] = (m[c.category] ?? 0) + 1;
    }
    return m;
  }, [data.conclusions]);

  return (
    <>
      <div className="page-header">
        <h1>总结与证据</h1>
        <div className="subtitle">
          按研究主线 6 阶段组织的结论摘要与来源索引。仅展示有真实记录的条目。
        </div>
      </div>

      {/* 关键结论摘要表（按阶段） */}
      <section className="section">
        <h2>阶段结论摘要</h2>
        <div className="small muted" style={{ marginBottom: 8 }}>
          数字为该阶段的结论条目数；不同分类反映证据强度与可推广性。
        </div>
        <table>
          <thead>
            <tr>
              <th>阶段</th>
              <th className="mono">已证实</th>
              <th className="mono">解释边界</th>
              <th className="mono">待验证</th>
              <th className="mono">后续计划</th>
            </tr>
          </thead>
          <tbody>
            {stageSummary.map((row) => (
              <tr key={row.stage.stage}>
                <td>
                  <div className="small mono muted">{row.stage.stage}</div>
                  <div style={{ fontWeight: 500 }}>{row.stage.title}</div>
                </td>
                <td className="mono" style={{ color: 'var(--ok)' }}>{row.counts.fact}</td>
                <td className="mono" style={{ color: 'var(--c-4b)' }}>{row.counts.interpretation}</td>
                <td className="mono" style={{ color: 'var(--warn)' }}>{row.counts.hypothesis}</td>
                <td className="mono muted">{row.counts.plan}</td>
              </tr>
            ))}
            <tr style={{ background: 'var(--surface-2)' }}>
              <td><strong>合计</strong></td>
              <td className="mono"><strong>{totalByCategory.fact}</strong></td>
              <td className="mono"><strong>{totalByCategory.interpretation}</strong></td>
              <td className="mono"><strong>{totalByCategory.hypothesis}</strong></td>
              <td className="mono"><strong>{totalByCategory.plan}</strong></td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* 筛选区 */}
      <section className="section">
        <h2>按条件浏览</h2>
        <FilterBar>
          <label>
            阶段：
            <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}>
              <option value="all">全部</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            类别：
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="fact">{CATEGORY_LABEL.fact}</option>
              <option value="interpretation">{CATEGORY_LABEL.interpretation}</option>
              <option value="hypothesis">{CATEGORY_LABEL.hypothesis}</option>
              <option value="plan">{CATEGORY_LABEL.plan}</option>
            </select>
          </label>
          <label>
            搜索：
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="关键词"
              style={{ minWidth: 160 }}
            />
          </label>
          <span className="muted small" style={{ marginLeft: 'auto' }}>
            匹配 {filtered.length} / {data.conclusions.length}
          </span>
        </FilterBar>

        <ConclusionTable items={filtered} />
      </section>

      {/* 来源索引（折叠） */}
      <section className="section">
        <button
          onClick={() => setShowSources(!showSources)}
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '10px 16px',
            width: '100%',
            textAlign: 'left',
            fontWeight: 600,
            fontSize: 14,
            color: 'var(--fg)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
          }}
        >
          <span>证据来源索引（{data.sources.length} 条，按 kind 分组）</span>
          <span style={{ color: 'var(--muted)', fontWeight: 400, fontSize: 12 }}>
            {showSources ? '收起' : '展开'}
          </span>
        </button>
        {showSources ? <SourcesTable sourcesByKind={sourcesByKind} /> : null}
      </section>
    </>
  );
}

/* 结论表格 */
function ConclusionTable({ items }: { items: Conclusion[] }) {
  if (items.length === 0) {
    return (
      <div className="empty-state" style={{ marginTop: 8 }}>
        无匹配条目。
      </div>
    );
  }
  return (
    <table>
      <thead>
        <tr>
          <th style={{ width: 90 }}>类别</th>
          <th style={{ width: 160 }}>阶段</th>
          <th>结论</th>
          <th style={{ width: 220 }}>来源</th>
        </tr>
      </thead>
      <tbody>
        {items.map((c, i) => (
          <tr key={i}>
            <td>
              <span
                style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  borderRadius: 12,
                  fontSize: 11,
                  fontWeight: 500,
                  background: 'var(--surface-2)',
                  color: CATEGORY_TONE[c.category],
                  border: `1px solid ${CATEGORY_TONE[c.category]}`,
                }}
              >
                {CATEGORY_LABEL[c.category]}
              </span>
            </td>
            <td className="small mono muted">{c.stage}</td>
            <td>{c.text}</td>
            <td>
              <SourceChip source={c.source} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* 来源紧凑标签 */
function SourceChip({ source }: { source: SourceRef }) {
  const label = source.label ?? source.kind;
  return (
    <div className="flex-col" style={{ gap: 2 }}>
      <span className="badge" style={{ fontSize: 10.5 }}>{label}</span>
      {source.path ? (
        <span className="small mono muted" style={{ wordBreak: 'break-all', fontSize: 11 }}>
          …/{source.path.split('/').slice(-2).join('/')}
        </span>
      ) : null}
      {source.lineOrId ? <span className="small muted mono" style={{ fontSize: 11 }}>· {source.lineOrId}</span> : null}
    </div>
  );
}

/* 来源索引表 */
function SourcesTable({ sourcesByKind }: { sourcesByKind: Map<string, SourceRef[]> }) {
  return (
    <div style={{ marginTop: 12 }}>
      <table>
        <thead>
          <tr>
            <th style={{ width: 160 }}>kind</th>
            <th style={{ width: 80 }}>数量</th>
            <th>说明 / 路径</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(sourcesByKind.entries()).map(([kind, refs]) => (
            <tr key={kind}>
              <td>
                <span className="badge" style={{ fontSize: 11 }}>{kind}</span>
              </td>
              <td className="mono">{refs.length}</td>
              <td>
                <div className="flex-col" style={{ gap: 4 }}>
                  {refs.slice(0, 6).map((r, i) => (
                    <SourceLinker key={i} source={r} compact />
                  ))}
                  {refs.length > 6 ? (
                    <div className="small muted">
                      其余 {refs.length - 6} 条省略；详见 data/sources.json。
                    </div>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}