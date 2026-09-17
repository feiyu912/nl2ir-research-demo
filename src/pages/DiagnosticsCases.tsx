import { useMemo, useState } from 'react';
import type { Case, DataSnapshot } from '../data/types';
import OverlapReportCard from '../components/OverlapReportCard';
import AttributionDonut from '../components/AttributionDonut';
import CaseCard from '../components/CaseCard';
import FilterBar from '../components/FilterBar';

type Props = { data: DataSnapshot };

export default function DiagnosticsCases({ data }: Props) {
  const [modelFilter, setModelFilter] = useState<string>('all');
  const [splitFilter, setSplitFilter] = useState<string>('all');
  const [attrFilter, setAttrFilter] = useState<string>('all');

  const errorCodeLabels: Record<string, string> = data.errorCodes?.categories ?? {
    M: 'prompt 明确规则未执行',
    R: '表示不合规但语义未变',
    P: 'prompt/输入歧义',
    G: 'Gold/严格评分差异',
    F: '非法 JSON 或 Schema',
  };

  const attrCounts = data.overlap?.categoryCounts ?? {};

  const cases = useMemo(() => {
    return data.cases.filter((c) => {
      const model = c.runId.startsWith('4b') || c.runId.includes('-4B') ? '4B'
        : c.runId.startsWith('9b') || c.runId.includes('-9B') ? '9B'
        : c.runId.startsWith('api') ? 'API' : 'other';
      if (modelFilter !== 'all' && model !== modelFilter) return false;
      if (splitFilter !== 'all' && !c.runId.includes(splitFilter)) return false;
      if (attrFilter !== 'all' && c.attribution !== attrFilter) return false;
      return true;
    });
  }, [data.cases, modelFilter, splitFilter, attrFilter]);

  return (
    <>
      <div className="page-header">
        <h1>诊断与病例</h1>
        <div className="subtitle">
          跨阶段真实病例，按模型/数据集/归因过滤。
        </div>
      </div>

      <div className="takeaway">
        <strong>关键发现：</strong>
        600 行失败记录中 222 是 Canonical Where 失败（其中 5 类主归因 M/R/P/G/F 见下表）。
        主归因 71.62% 为「prompt 明确规则未执行」(M) 与「prompt/输入歧义」(P)；门控与契约侧修复不能完全覆盖这两类。
      </div>

      <section className="section">
        <OverlapReportCard overlap={data.overlap} />
      </section>

      <section className="section">
        <h2>222 Canonical Where 失败的主归因</h2>
        <div className="grid grid-2" style={{ marginTop: 12 }}>
          <div>
            <AttributionDonut data={attrCounts} labelMap={errorCodeLabels} />
          </div>
          <div>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 80 }}>类别</th>
                  <th>定义</th>
                  <th className="num" style={{ width: 70 }}>n</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(attrCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([k, v]) => (
                    <tr key={k}>
                      <td>
                        <span className="badge" style={{ fontSize: 11 }}>{k}</span>
                      </td>
                      <td className="small">{errorCodeLabels[k] ?? k}</td>
                      <td className="num">{v}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>病例库（{cases.length} 条匹配）</h2>
        <FilterBar>
          <label>
            模型：
            <select value={modelFilter} onChange={(e) => setModelFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="4B">4B</option>
              <option value="9B">9B</option>
              <option value="API">API</option>
            </select>
          </label>
          <label>
            数据集：
            <select value={splitFilter} onChange={(e) => setSplitFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="old">old</option>
              <option value="c300">c300</option>
              <option value="blind">blind</option>
            </select>
          </label>
          <label>
            主归因：
            <select value={attrFilter} onChange={(e) => setAttrFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="M">M · prompt 未执行</option>
              <option value="R">R · 表示不合规</option>
              <option value="P">P · 歧义</option>
              <option value="G">G · Gold 差异</option>
              <option value="F">F · JSON/Schema 失败</option>
            </select>
          </label>
          <span className="muted small">展示 {Math.min(cases.length, 20)} / {cases.length}</span>
        </FilterBar>

        <div className="flex-col">
          {cases.slice(0, 20).map((c: Case) => (
            <CaseCard key={c.caseId} caseData={c} />
          ))}
        </div>
        {cases.length > 20 ? (
          <div className="small muted" style={{ marginTop: 8, textAlign: 'center' }}>
            其余 {cases.length - 20} 条未展示；可在「总结与证据」按来源筛选或下载原始
            <code> cases.json</code>。
          </div>
        ) : null}
      </section>

      <section className="section">
        <h2>典型病例（适合讲解）</h2>
        <div className="small fg-2" style={{ marginBottom: 8 }}>
          抽样代表性：4B 履历否定反转、9B 语言考试双路由、复合 NOT 作用域、optional 证书与工具遗漏、空档次数与月数、年龄边界 Gold 差异、交换律排序、语义词面 vs 真实意图。
        </div>
        <div className="callout warn">
          <strong>9B 布尔否定表示形式差异 ≠ 4B 否定反转</strong>；缺失字段下 ES 等价性未核验时不能宣称完全执行等价。
        </div>
      </section>
    </>
  );
}