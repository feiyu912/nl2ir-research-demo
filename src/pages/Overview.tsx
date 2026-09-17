import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { DataSnapshot } from '../data/types';
import OverlapReportCard from '../components/OverlapReportCard';
import GroupedMetricChart from '../components/GroupedMetricChart';

type Props = { data: DataSnapshot };

export default function Overview({ data }: Props) {
  const [openTech, setOpenTech] = useState(false);

  return (
    <>
      <div className="page-header">
        <h1>NL2IR 研究汇报</h1>
        <div className="subtitle">
          自然语言招聘查询转为可执行检索条件。本地小模型方案下的研究过程、当前能力与下一步建议。
        </div>
      </div>

      {/* 关键结论 */}
      <div className="takeaway">
        <strong>结论：</strong>
        强 API 参考管线在 sealed blind-v6 上达到 <strong>95–97%</strong>（单次与门控后），
        本地 4B 裸输出 <strong>88%</strong>、9B <strong>82%</strong>；
        9B 在当前实验中没有稳定优于 4B，不能推断更大模型必然更好。学生模型在复杂规则（边界、路由、复合 NOT 作用域、年龄边界等）上仍有差距，
        未做训练期间验证，未微调底座对照待补。
      </div>

      <section className="section">
        <h2>当前水平（sealed blind-v6, 240 条）</h2>
        <p className="small fg-2" style={{ marginBottom: 14 }}>
          按数据集分组，比较 4B/9B 裸输出与 API 单次、API 门控后的 Canonical Where。
          门控是额外 8 次 API 调用 + 条件修复，不是裸模型能力。
        </p>
        <GroupedMetricChart data={data} />
      </section>

      <section className="section">
        <h2>600 / 222 / 440</h2>
        <OverlapReportCard overlap={data.overlap} />
      </section>

      <section className="section">
        <h2>当前差距</h2>
        <ul className="small" style={{ paddingLeft: 20 }}>
          <li>学生模型在复杂规则（边界、路由、复合 NOT、年龄边界、optional 证书与工具遗漏、语义词面 vs 真实意图等）上仍有差距。</li>
          <li>9B 在当前实验中没有稳定优于 4B；不能推断更大模型必然更好。</li>
          <li>本地学生裸输出与 API 门控后差距约 8 个百分点（234→211）。</li>
          <li>未做训练期间验证：训练 loss 低不能等同于泛化良好。</li>
          <li>尚未在生产流量下验证；未做未微调底座对照。</li>
        </ul>
      </section>

      <section className="section">
        <h2>下一步</h2>
        <p className="small" style={{ marginBottom: 12 }}>
          <strong>原则：</strong>不默认更大模型或反复重训；优先补可证伪证据。
        </p>
        <p className="small"><strong>待补证据：</strong></p>
        <ul className="small" style={{ paddingLeft: 20 }}>
          <li>未微调底座对照（Qwen3.5-4B/9B 原底座在同 blind 上的真实表现）。</li>
          <li>独立 dev 集（同分布且未参与训练）。</li>
          <li>C-hard 训练监督是否泛化（C-hard 进入当前训练，需要独立验证）。</li>
          <li>API 门控机制在新数据上的稳定性（部署期 dev 监控）。</li>
        </ul>
        <div className="callout ok" style={{ marginTop: 14 }}>
          <strong>进入业务试用的条件：</strong>
          frozen 管线在独立 dev 集上复现接近 frozen blind-v6 数字 + 端到端延迟与稳定性达到部署基线 + 异常查询降级策略确定。
        </div>
      </section>

      <section className="section">
        <h2>相关专题</h2>
        <div className="flex" style={{ gap: 12, flexWrap: 'wrap' }}>
          <Link to="/prompts" className="badge">Prompt 演进</Link>
          <Link to="/system" className="badge">解析方案</Link>
          <Link to="/experiments" className="badge">实验与数据</Link>
          <Link to="/diagnostics" className="badge">诊断与病例</Link>
          <Link to="/summary" className="badge">总结与证据</Link>
        </div>
      </section>

      {/* 技术证据 - 来源与训练详情等 */}
      <section className="section">
        <button
          onClick={() => setOpenTech(!openTech)}
          className="fold-trigger"
        >
          <span>来源与技术细节</span>
          <span className="chev">{openTech ? '收起' : '展开'}</span>
        </button>
        {openTech ? (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ marginTop: 0 }}>研究主线摘要</h3>
            <p className="small">
              自然语言招聘查询 → 可执行检索条件（IR）；本地小模型方案降低外部 API 依赖、支持本地运行。
              研究从接手 8B 基线、压缩 prompt、规则迭代、独立 blind、严格审计，到 v21 + candidate_v4 冻结与本地 4B/9B 训练与评测。
            </p>

            <h3>当前学生训练（4B / 9B LoRA）</h3>
            <ul className="small" style={{ paddingLeft: 20 }}>
              <li>训练集：1303 常规 + 240 C-hard = 1543。C300/old366 是开发回归/诊断集；C-hard240 才进入训练。</li>
              <li>3 轮、291 步、4-bit BNB QLoRA + LoRA r16 α32；bf16；cutoff 4096；enable_thinking=false。</li>
              <li>未开启训练期间验证（eval_strategy=NO），只有 3 轮平均 loss。</li>
              <li>9B checkpoint-200 与最终盲测 Where 持平（198/240）；不支持最后 91 步整体退化；不能排除 200 步前过拟合。</li>
            </ul>

            <h3>Prompt 演进概览</h3>
            <ul className="small" style={{ paddingLeft: 20 }}>
              <li>压缩系列：Original 336 行 / 24193 B → compact-v1/v2/v3（仅替换 system；1303 训练数据 SHA-256 不变）。</li>
              <li>研究主线系列：v12–v16 规则迭代（含回落）→ v17 数据契约（106 条修正）→ v18 3072-token 门禁 → v19 最小一般化增补 → v20 末尾检查重排 → v21 candidate-v4 冻结。</li>
            </ul>

            <h3>证据来源</h3>
            <ul className="small" style={{ paddingLeft: 20 }}>
              <li>研究主版：<span className="mono">~/Downloads/NL2IR_全部研究材料汇总母版.docx</span></li>
              <li>9B 训练检查母版：<span className="mono">~/Downloads/NL2IR_全部研究材料汇总母版_追加9B训练检查结论.docx</span></li>
              <li>强 API 配置：<span className="mono">nl2ir_strong_api_pipeline_candidate_v4.json</span></li>
              <li>学生六评估审计：<span className="mono">nl2ir_student_six_eval_prompt_audit/</span></li>
              <li>学生评测数据：<span className="mono">audit-inputs/Qwen3.5-4B-Base/lora/</span> 与 <span className="mono">Qwen3.5-9B-Base/lora/</span></li>
            </ul>

            <h3>口径与边界</h3>
            <ul className="small" style={{ paddingLeft: 20 }}>
              <li>Canonical Where：4B/9B 取 main_chain_where；API 取 order_value_invariant_where（canonicalizer 之后）。</li>
              <li>门控 API 与裸学生是不同流程，不可直接混用。</li>
              <li>old366 / C300 是开发回归/诊断集，未进入训练。</li>
              <li>C-hard240 是训练监督，不是独立验证。</li>
            </ul>
          </div>
        ) : null}
      </section>
    </>
  );
}