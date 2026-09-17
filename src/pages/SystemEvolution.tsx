import type { DataSnapshot } from '../data/types';
import { Link } from 'react-router-dom';

type Props = { data: DataSnapshot };

/**
 * 解析方案（非 prompt 内容）：校验、编译、repair、断言门控。
 * prompt 内容请去 /prompts（与 /prompts 不重复）。
 */
export default function SystemEvolution({ data }: Props) {
  const ap = data.apiSealedV6;
  const pipeline = (ap?.pipeline as string[] | undefined) ?? [];

  return (
    <>
      <div className="page-header">
        <h1>解析方案</h1>
        <div className="subtitle">
          非 prompt 部分：NL→IR 之后的校验、编译、repair、断言门控与规范化流程。
          prompt 的版本演进（Original / compact-v3 / v12–v21）请见 <Link to="/prompts">Prompt 演进</Link>。
        </div>
      </div>

      <section className="section">
        <h2>主链职责</h2>
        <div
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'stretch',
            flexWrap: 'wrap',
            marginTop: 8,
          }}
        >
          {[
            { name: 'NL', desc: '用户自然语言查询', color: 'var(--fg)' },
            { name: 'Prompt', desc: 'prompt specification + contract', color: 'var(--c-4b)' },
            { name: 'IR', desc: 'paper_ir_v1 candidate_v4 输出', color: 'var(--c-api)' },
            { name: '断言门控 v7', desc: 'gold-free 高精度条件修复', color: 'var(--warn)' },
            { name: 'Canonicalizer', desc: '确定性 where 规范化', color: 'var(--c-9b)' },
            { name: 'Compiler / ES', desc: 'executable main chain', color: 'var(--ok)' },
          ].map((step, i, arr) => (
            <div key={step.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div
                className="card"
                style={{
                  minWidth: 140,
                  borderColor: step.color,
                  borderTop: `3px solid ${step.color}`,
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{i + 1}. {step.name}</div>
                <div className="small muted" style={{ marginTop: 4 }}>{step.desc}</div>
              </div>
              {i < arr.length - 1 ? <span className="muted">→</span> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>Pipeline（candidate_v4 实际）</h2>
        <div className="small muted" style={{ marginBottom: 8 }}>
          模型：<code>qwen3.7-max</code>。Pipeline 4 阶段；本机无 prompt 原文（v21）。
        </div>
        <ol style={{ paddingLeft: 20 }}>
          {pipeline.map((p, i) => (
            <li key={i} className="mono small" style={{ marginBottom: 4 }}>{p}</li>
          ))}
        </ol>
      </section>

      <section className="section">
        <h2>各组件职责与边界</h2>
        <div className="grid grid-2">
          <div className="card">
            <h4>Prompt specification</h4>
            <p className="small">定义 NL → IR 的输出契约：JSON 形状、字段、表示规则。详见 <Link to="/prompts">Prompt 演进</Link>。</p>
          </div>
          <div className="card">
            <h4>Contract（v21）</h4>
            <p className="small">where AST-only；顶层四键 + meta 基础键；operator 仅限 eq/any/all/not/gte/lte/range；range 必须恰两个 values。</p>
          </div>
          <div className="card">
            <h4>Gold-free 高精度断言</h4>
            <p className="small">
              不依赖 Gold；基于 query 与输出断言判断是否需要修复。
              <strong>只读 query/输出</strong>，不读 Gold。
            </p>
          </div>
          <div className="card">
            <h4>Repair（reason-specific）</h4>
            <p className="small">仅在断言命中时按 reason 触发；不做全量 cascade；保留原始分数并报告逐题 fixed/broken。</p>
          </div>
          <div className="card">
            <h4>Assertion Gate（v7）</h4>
            <p className="small">
              冻结的 assertion_v7 门控：在最终输出前调用额外 API 条件触发 Where 修复；
              sealed blind-v6 仅 8/240 次调用，修复 5、破坏 0。
            </p>
          </div>
          <div className="card">
            <h4>Canonicalizer</h4>
            <p className="small">
              deterministic_where_canonicalization：排序与交换律归一；
              canonical_where = order_value_invariant_where。
            </p>
          </div>
          <div className="card">
            <h4>Compiler / ES</h4>
            <p className="small">IR → ES 查询的可执行管线；executable_main_chain 与 compiler_hard_exact 是不同指标口径。</p>
          </div>
          <div className="card">
            <h4>删去的做法</h4>
            <p className="small">
              全量 repair cascade 反而是反例；
              最终 candidate_v4 明确删除 cascade，只对高精度断言命中项做 reason-specific repair。
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>门控 vs 裸输出（不同流程，不可混比）</h2>
        <div className="callout warn">
          <strong>门控 API 与裸学生是不同流程</strong>。
          门控后额外触发 8 次调用 + 条件修复；不是裸模型能力。
          不同评分口径（strict_where / main_chain_where / canonical_where / order_value_invariant_where）区分展示。
        </div>
        <table>
          <thead>
            <tr>
              <th>流程</th>
              <th>sealed blind-v6 (240) Canonical Where</th>
              <th>额外调用</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>API 单次裸输出</strong></td>
              <td className="mono">229/240 (95.42%)</td>
              <td className="mono">0</td>
              <td className="small">order/value-invariant；canonicalizer 后等价</td>
            </tr>
            <tr>
              <td><strong>API 门控后</strong></td>
              <td className="mono">234/240 (97.50%)</td>
              <td className="mono">8/240</td>
              <td className="small">修复 5、破坏 0；额外检查 + 条件修复，不是裸模型能力</td>
            </tr>
            <tr>
              <td><strong>4B 裸输出</strong></td>
              <td className="mono">211/240 (87.92%)</td>
              <td className="mono">0</td>
              <td className="small">main_chain_where；与 API 不同口径</td>
            </tr>
            <tr>
              <td><strong>9B 裸输出（初次）</strong></td>
              <td className="mono">197/240 (82.08%)</td>
              <td className="mono">0</td>
              <td className="small">main_chain_where；重复 198/240（82.50%）</td>
            </tr>
          </tbody>
        </table>
      </section>
    </>
  );
}