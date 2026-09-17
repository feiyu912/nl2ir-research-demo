import { useState } from 'react';
import type { DataSnapshot } from '../data/types';

type Props = { data: DataSnapshot };

export default function PromptEvolution({ data }: Props) {
  const series = data.promptEvolution?.series ?? [];
  const original = series.find((s) => s.label === 'compression')?.versions.find((v) => v.label === 'Original');
  const compactV3 = series.find((s) => s.label === 'compression')?.versions.find((v) => v.label === 'compact-v3');
  const v21 = series.find((s) => s.label === 'research-series')?.versions.find((v) => v.label === 'v21 candidate-v4 (current)');

  return (
    <>
      <div className="page-header">
        <h1>Prompt 演进</h1>
        <div className="subtitle">
          从最早接手的完整长 prompt，到压缩版本、研究主线系列（v12–v21），再到最终 v21 参考方案。
          主展示 Original vs compact-v3 对照；完整版本序列与原文折叠在详情区。
        </div>
      </div>

      <div className="takeaway">
        <strong>关键变化：</strong>
        Original（336 行 / 24193 B）含大量示例，Qwen3.5 包装下输入 6470–6499 tokens，全部 370 条超 3072 训练门禁；
        compact-v3 删去大部分示例但保留边界示例，新增输出契约与字段白名单，81 行 / 10493 B，
        训练 1303 max 3060 tokens（通过门禁）；仅替换 system，1303 训练数据 SHA-256 不变。
      </div>

      {/* Original vs compact-v3 对照 */}
      <section className="section">
        <h2>Original vs compact-v3 对照</h2>
        <div className="grid grid-3" style={{ marginBottom: 16 }}>
          <KV label="行" v1={original?.lines} v2={compactV3?.lines} />
          <KV label="字节" v1={original?.bytes ? `${original.bytes}` : '—'} v2={compactV3?.bytes ? `${compactV3.bytes}` : '—'} />
          <KV label="示例策略" v1="大量 query→JSON 示例" v2="仅保留边界示例" />
        </div>

        <table>
          <thead>
            <tr>
              <th style={{ width: 220 }}>维度</th>
              <th>Original（前序完整）</th>
              <th>compact-v3（首次压缩）</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>文件</td>
              <td className="small mono" style={{ wordBreak: 'break-all' }}>{original?.file ?? '—'}</td>
              <td className="small mono" style={{ wordBreak: 'break-all' }}>{compactV3?.file ?? '—'}</td>
            </tr>
            <tr>
              <td>行 / 字节</td>
              <td>336 行 / 24193 B</td>
              <td>81 行 / 10493 B</td>
            </tr>
            <tr>
              <td>Qwen3.5 包装下输入</td>
              <td>约 6470–6499 tokens（仅 system）</td>
              <td>见下方 token 门禁表</td>
            </tr>
            <tr>
              <td>训练门禁 3072</td>
              <td>370/370 全部超过</td>
              <td>训练 1303 max 3060（0 超）</td>
            </tr>
            <tr>
              <td>示例策略</td>
              <td>大量 query→JSON 示例</td>
              <td>删除大部分示例，保留边界示例（Java 工程师、玛氏背景、团队管理等）</td>
            </tr>
            <tr>
              <td>输出契约</td>
              <td>where AST；Schema 在 compact 系列中收紧</td>
              <td>顶层 4 键 + meta 5 基础键；where 只允许 and/or/not/leaf AST；operator 限 eq/any/all/not/gte/lte/range</td>
            </tr>
            <tr>
              <td>字段路由</td>
              <td>长字段说明</td>
              <td>分组：身份 / 教育 / 地点与意向 / 经历实体；work_state 与 compiler 映射；work_segment_count 不得映射为 work_years</td>
            </tr>
            <tr>
              <td>query / label</td>
              <td>—</td>
              <td>不变（仅替换 system）</td>
            </tr>
            <tr>
              <td>数据不变性</td>
              <td>—</td>
              <td>替换前后 1303 训练 SHA-256 一致</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* 关键实验 */}
      <section className="section">
        <h2>compact-v3 关键实验</h2>
        <p className="small fg-2" style={{ marginBottom: 12 }}>
          实验结果配套 v18 训练运行；详细数字见「实验与数据」。
        </p>
        <div className="grid grid-2">
          <div className="kv-row" style={{ borderBottom: '1px solid var(--divider)' }}>
            <span className="kv-key">训练运行（v18 4B）</span>
            <span className="kv-val">GPU 99% · 显存 15874/16303 MiB · 吞吐 1046→1498 tokens/s</span>
          </div>
          <div className="kv-row" style={{ borderBottom: '1px solid var(--divider)' }}>
            <span className="kv-key">结构覆盖</span>
            <span className="kv-val">32 condition.field + 5 semantic.fields 全部覆盖</span>
          </div>
          <div className="kv-row" style={{ borderBottom: '1px solid var(--divider)' }}>
            <span className="kv-key">数据不变性 SHA</span>
            <span className="kv-val">35ac78dc…（1303 训练）</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">压缩收益</span>
            <span className="kv-val">不是 prompt 单因素（同时 v17 修 106 条 / Gold / repair）</span>
          </div>
        </div>
      </section>

      {/* 后续系列折叠 */}
      <section className="section">
        <h2>v12–v21 研究主线系列（折叠）</h2>
        <SeriesFold series={series} />
      </section>

      {/* 完整 Prompt 原文折叠 */}
      <section className="section">
        <h2>完整 Prompt 原文（折叠）</h2>
        <PromptFiles />
      </section>

      {/* 盲测版本折叠 */}
      {data.promptEvolution?.blindEvolution ? (
        <section className="section">
          <h2>盲测 / 诊断集版本演进</h2>
          <table>
            <thead>
              <tr>
                <th>标签</th>
                <th>样本数</th>
                <th>首次发现 / 数字</th>
                <th>命运</th>
              </tr>
            </thead>
            <tbody>
              {data.promptEvolution.blindEvolution.items.map((it, i) => (
                <tr key={i}>
                  <td className="mono">{it.label}</td>
                  <td className="num">{it.samples ?? '—'}</td>
                  <td className="small">{it.firstSeen}</td>
                  <td className="small">{it.fate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {/* v21 参考方案摘要 */}
      {v21 ? (
        <section className="section">
          <h2>v21 candidate-v4（最终参考方案）</h2>
          <p className="small">
            v21 是当前 frozen prompt + implementation 的联合标识。生成 + 断言门控 v7 + 条件修复 + 确定性 where 规范化构成 4 阶段 pipeline。
            sealed blind-v6（240 条）API 单次 229/240 (95.42%)；门控后 234/240 (97.50%)。
          </p>
          <p className="small fg-2">
            本机无 v21 完整 prompt 原文（属于工作机密 / 后续部署约束）；prompt 与 implementation SHA-256 已在 candidate_v4 配置中冻结。
          </p>
        </section>
      ) : null}

      {/* 关键纪律 */}
      <section className="section">
        <h2>关键纪律</h2>
        <ul className="small" style={{ paddingLeft: 20 }}>
          <li>字节数 ≠ 字符数 ≠ token 数；token 统计须注明 tokenizer / 模板 / 统计范围。</li>
          <li>没有原始记录的标「待补」，不为展示下载模型。</li>
          <li>收益不能默认是 prompt 单因素；同时重训、改 Gold 或加 repair 时按实际实验标记。</li>
          <li>共享 system prompt 不是所有历史训练数据与模板始终一致的证明。</li>
        </ul>
      </section>
    </>
  );
}

function KV({ label, v1, v2 }: { label: string; v1?: string | number | null; v2?: string | number | null }) {
  return (
    <div>
      <div className="metric-label">{label}</div>
      <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
        <div className="num" style={{ fontSize: 18, fontWeight: 600 }}>{v1 ?? '—'}</div>
        <div style={{ alignSelf: 'center', color: 'var(--muted)' }}>→</div>
        <div className="num" style={{ fontSize: 18, fontWeight: 600, color: 'var(--primary)' }}>{v2 ?? '—'}</div>
      </div>
    </div>
  );
}

function SeriesFold({ series }: { series: DataSnapshot['promptEvolution']['series'] }) {
  const [open, setOpen] = useState(false);
  const researchSeries = series.find((s) => s.label === 'research-series');
  const versions = researchSeries?.versions ?? [];

  return (
    <div>
      <button onClick={() => setOpen(!open)} className="fold-trigger">
        <span>研究主线系列版本（v12–v21）</span>
        <span className="chev">{open ? '收起' : '展开'}</span>
      </button>
      {open ? (
        <div style={{ marginTop: 14 }}>
          {researchSeries?.earlyVersions ? (
            <div className="callout warn" style={{ marginBottom: 12 }}>
              <strong>{researchSeries.earlyVersions.label}</strong>：{researchSeries.earlyVersions.status}
              {researchSeries.earlyVersions.note ? <div className="small">{researchSeries.earlyVersions.note}</div> : null}
            </div>
          ) : null}
          <table>
            <thead>
              <tr>
                <th style={{ width: 100 }}>版本</th>
                <th>关键变化</th>
                <th>实验数字</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.label}>
                  <td><strong>{v.label}</strong></td>
                  <td className="small">{v.rulesFocus ?? v.notes?.[0] ?? '—'}</td>
                  <td className="small">{v.experiments?.[0] ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

/* 完整 Prompt 原文 - 通过构建期 vite glob 注入 */
function PromptFiles() {
  const knownFiles = import.meta.glob('../../scripts/infofromhr/fine_tuning/prompts/*.txt', {
    eager: true,
    query: '?raw',
    import: 'default',
  }) as Record<string, string>;

  const files = [
    { label: 'Original', path: 'scripts/infofromhr/fine_tuning/prompts/nl2ir_where_ast_original_1303.txt', note: '336 行 / 24193 B · 第 112 行起为示例区' },
    { label: 'compact-v1', path: 'scripts/infofromhr/fine_tuning/prompts/nl2ir_where_ast_compact_v1.txt', note: '86 行 / 8883 B' },
    { label: 'compact-v2', path: 'scripts/infofromhr/fine_tuning/prompts/nl2ir_where_ast_compact_v2.txt', note: '72 行 / 9316 B' },
    { label: 'compact-v3', path: 'scripts/infofromhr/fine_tuning/prompts/nl2ir_where_ast_compact_v3.txt', note: '81 行 / 10493 B · 训练运行时 SHA 已在审计中' },
  ];

  return (
    <div className="flex-col" style={{ gap: 8 }}>
      {files.map((f) => (
        <PromptFileBlock key={f.path} label={f.label} note={f.note} content={knownFiles[`../../${f.path}`]} />
      ))}
    </div>
  );
}

function PromptFileBlock({ label, note, content }: { label: string; note: string; content: string | undefined }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)} className="fold-trigger">
        <span><strong>{label}</strong> <span className="small fg-2" style={{ marginLeft: 8 }}>{note}</span></span>
        <span className="chev">{open ? '收起' : '展开全文'}</span>
      </button>
      {open ? (
        <pre style={{ marginTop: 6, maxHeight: 480, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 12 }}>
          {content ?? <em className="muted">文件未在 bundle 中；仅以文件路径引用。</em>}
        </pre>
      ) : null}
    </div>
  );
}