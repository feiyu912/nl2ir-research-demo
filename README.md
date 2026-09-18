# NL2IR 研究展示 Demo

NL2IR 与 executable semantic parsing 研究展示站。

线上地址：[https://feiyu912.github.io/nl2ir-research-demo/](https://feiyu912.github.io/nl2ir-research-demo/)

> **纪律**：不挑最高分；不静默混用 Gold/盲测/口径；指标不可加和；缺数据 ≠ 0；600/222/440 是重叠集合，不可相加。
>
> **不下载模型、不 SSH、不调用 API、不修改源研究文件。**

---

## 启动

```bash
# 1. 安装依赖（仅一次）
npm install

# 2. 开发模式
npm run dev
# 浏览器打开 http://127.0.0.1:5173

# 3. 生产构建
npm run build
# 产物在 dist/

# 4. 本地预览生产构建
npm run preview
```

`main` 分支更新后，`.github/workflows/deploy-pages.yml` 会自动构建并发布到 GitHub Pages。

## 数据校验

```bash
npm run validate
```

原始证据与提取工具只保留在本机，不进入公开仓库。

---

## 目录结构

```
nl2ir-research-demo/
├── README.md                    # 本文件
├── docs/
│   ├── SCHEMA.md                # JSON schema（8 类核心 + 1 类独立实验）
│   ├── DATA_DISCIPLINE.md       # 数据纪律（红线）
│   ├── STAGES.md                # 8 阶段字典
│   ├── SOURCES.md               # 来源映射表
│   └── CHANGELOG.md             # 提取脚本与母版变更
├── scripts/
│   └── validate_data.py         # 数据纪律与公开边界校验
├── data/
│   ├── datasets.json
│   ├── runs.json                # 8 条 Run（2 API + 6 student）
│   ├── metrics.json             # 80 行（10 指标 × 8 Run）
│   ├── hosted_api_baselines.json # 托管 API 三模型基线（独立实验，不与 LoRA 混用）
│   ├── stages.json             # 8 个阶段分类标签（不是时间线）
│   ├── training.json            # 6 个真实 loss 点
│   ├── conclusions.json         # 跨阶段结论
│   ├── sources.json             # 来源映射
│   ├── stages.json              # 6 阶段简短摘要
│   ├── research_timeline.json   # 6 阶段完整叙事（核心入口）
│   ├── prompt_evolution.json    # Original → compact → v21 prompt 对照
│   ├── aux/
│   │   ├── overlap_report.json  # 600/222/440 + intersection
│   │   ├── error_codes.json     # M/R/P/G/F
│   │   └── api_sealed_v6.json   # 强 API 摘要
└── src/
    ├── main.tsx                 # 入口
    ├── App.tsx                  # 路由 + 顶部 banner
    ├── styles/
    │   ├── theme.css
    │   └── typography.css
    ├── data/
    │   ├── types.ts
    │   ├── loaders.ts           # import.meta.glob
    │   ├── selectors.ts
    │   └── discipline.ts        # 前端校验
    ├── components/              # 12 个共享组件
    └── pages/                   # 7 个视图
        ├── Overview.tsx
        ├── PromptEvolution.tsx
        ├── SystemEvolution.tsx
        ├── ExperimentsData.tsx
        ├── DiagnosticsCases.tsx
        └── SummaryEvidence.tsx
```

## 公开数据边界

本仓库只发布聚合指标、统计结论和允许公开的 Prompt。逐题测评 query、Gold、模型预测、候选人数据及原始研究母版不进入仓库。本机通过 `.gitignore` 保留这些文件；`npm run validate` 会在它们被 Git 跟踪时直接失败，阻止 CI/CD 发布。

---

## 5 个视图

| 视图 | 路由 | 内容 |
|------|------|------|
| 总览 | `/` | 研究动机、关键发现、当前能力和下一步建议 |
| Prompt 演进 | `/prompts` | 五层 Prompt 范式、修改工作流、长度门禁与 v12–v21 版本演进逻辑；不公开完整原文 |
| 实验与数据 | `/experiments` | 当前 8 Run 完整指标矩阵 + 按问题分组的历史实验（8 组） |
| 三模型横向对比 | `/models` | 质量、成本、延迟、分片表现和统计检验 |
| 错误诊断 | `/diagnostics` | 只展示聚合错误归因，不公开逐题测评数据 |

> 旧 `/training` 与 `/timeline` 自动重定向到首页。

> 不使用时间线、阶段导航或版本流水账；时间只作为证据元数据。

---

## 数据纪律（必须遵守）

详见 `docs/DATA_DISCIPLINE.md`。核心红线：

1. **指标不可加和** —— 永远渲染 `correct/total (xx.xx%)`
2. **600/222/440 重叠集合，禁相加** —— `OverlapReportCard` 始终可见
3. **训练 loss 仅 3 真实点** —— 不虚构 291 步曲线
4. **缺数据 ≠ 0** —— 渲染 `数据缺失`
5. **不混用 Gold/盲测/口径** —— 每个 Run 必须有 `kind` + `compatibility[]`
6. **历史 ≠ 正式** —— 旧 356/366、C300 历史 271/300 是开发/历史口径

---

## 仍缺的原始证据

按"如果确需补文件，列出最小缺失清单让我提供"的要求：

| 缺失项 | 影响 | 现状 |
|--------|------|------|
| 9B 重复 blind 原始 metrics/responses | 无法在本地展开 checkpoint 后重跑 | 仅引用 DOCX 聚合（198/240） |
| 9B checkpoint-200 blind 原始 metrics/responses | 同上 | 仅引用 DOCX 聚合 |
| 4B/9B trainer_state.json 逐 step loss | loss 图仅有 3 个真实点 | 仅引用 3 轮平均 |
| 9B trainer_log.jsonl 完整 NaN/Inf 日志 | 训练检查细节 | 引用 DOCX 聚合声明 |

未提供时按 prompt 要求：仅引用 DOCX 聚合记录，UI 显式标注「原始数据不在本机」。

---

## 本机环境

- Python 3.9.6+（仅需标准库：zipfile + xml.etree.ElementTree）
- Node 24+ 与 npm 11+
- macOS（其他平台未测试，但应兼容）

不需要：pandoc、python-docx、CUDA、付费 API、服务器连接。

---

## 数据来源

公开仓库保留聚合口径、日期和来源哈希。内部目录、逐题文件及提取工具不公开。
## 托管 API 三模型基线（独立实验）

`data/hosted_api_baselines.json` 是一个**独立于 4B/9B LoRA 训练实验**的模型选型数据集：
在同一份冻结 v21 契约（同一 prompt、同一 `json_object` 解码、同一冻结 scorer）下比较
`qwen3.7-max` / `qwen3.8-flash` / `deepseek-v4.1-flash`，共 906 条
（old366 366 + c300 300 + blind-v6 240；stress96 为 blind-v6 子集，不重复计入）。

| 模型 | combined where | hard-F1 | 标准化 ¥/万次 | 实测 ¥/万次 | 当前结论 |
|------|---------------|---------|--------------|-------------|----------|
| qwen3.7-max | 94.26% | 95.44% | 201.60 | 242.83 | 质量基线 |
| qwen3.8-flash | 89.62% | 94.93% | 12.60 | 16.51 | Tier B 低成本候选，尚未替换生产 |
| deepseek-v4.1-flash | 86.20% | 94.29% | 16.40（闲）/ 32.80（忙） | 9.67（闲）/ 19.34（忙） | Tier C，当前不替换 |

- 相对 qwen3.7-max：qwen3.8 下降 **4.64pp**；DeepSeek 下降 **8.06pp**。
- qwen3.8 标准化成本为 qwen3.7-max 的 **6.25%**（降低 **93.75%**），
  同 token 成本比 DeepSeek 闲时低 **23.2%**。
- **两套成本口径必须并列**：`standardized_cost` 是相同 token 工作量的纯价格比较；
  `observed_run_cost` 是本次真实账单，**不是价格指数**。DeepSeek 本次账单低来自更高
  缓存命中与更短输出，**不代表单位价格低**。
- DeepSeek → qwen3.8 的 +3.42pp 在 family-aware cluster CI 下**跨 0**，该方向不得宣称显著。

### 展示位置

- **`/models`「三模型横向对比」**：完整对比页（分片、红线、延迟、两套成本口径、
  配对统计与 cluster CI、错误类型、选型结论、有效性限制）。导航入口位于「实验依据」右侧。
- **`/experiments` →「当前模型验证」**：保持原有设计不变，仅顶部新增一张紧凑摘要卡
  （combined where / P50 / 标准化 ¥万次 / 结论），并提供「查看完整对比 →」入口。
- 三模型摘要统一使用同一尺度，不使用分别归一化的进度条。
- Arm A/B 训练消融**已并入本页**：**A/B（C-hard 训练包消融）在 `/experiments` →「历史研究实验」
  新增一组 `chard`**；**27B 规模臂（C）在 `/experiments` →「当前模型验证」**新增三条 run
  （old366 / C300 / blind-v6），并在 `/` 总览的「当前能力参考」中一并显示。
  数据由 `scripts/build_presentation.mjs` 从
  `docs/modeltest/nl2ir_stage1_chard_ablation_prereg_2026-09-16/stage1_arm_a_results_20260917/`
  读取并**断言**（数值漂移会直接构建失败）。
- **27B 底座（C0，无 SFT）**在 `/experiments` →「当前模型验证」的**底座核验区**新增三条
  （`27B 底座`：old366 61/366、C300 58/300、blind-v6 37/240）。**它的协议与 4B/9B 底座不同**
  （`qwen3_8_nothink` / 4096 / batch 10 对官方 hard-off / 1024），页面上已显式标注：
  不可与 4B/9B 底座并列相减；**只有 C0 与 C（27B+SFT）之差才是同口径的 SFT 对照**。
  该对照的 batch 混淆**已收口**（batch 15 与 30 对规范化 IR 的效应判定为 0），
  残余限制是代际（C0 属 Qwen3.8、4B/9B 底座属 Qwen3.5）与约 4% 的逐次采样噪声。

### Stage-1 A/B 消融与 27B 规模臂的口径边界

- **`/experiments` →「历史研究实验」的 `chard` 组**只判定 **A vs B 的训练包效应**。
  预注册 §4 的灰区判据看 `stress96` 净修复题数：**+6 题 → 灰区 → 补 2 个配对 seed，不进 Stage 2**。
  同时必须一并呈现相反方向的更宽视图：全量 blind-v6（186→211）与 realistic144（119→138）
  在两种口径下均为稳健提升。**这一张力是结论本身的一部分，不得只引用其中一侧。**
- **27B 臂不参与 A/B 判决**：它是事后追加的 secondary **scale** arm（与 B 同数据、只变模型规模），
  **不得**套用 §4 判据；且 `C−A` 同时变规模与数据，**不可**用于估计训练包效应。
- **27B 推理 `per_device_eval_batch_size=15`，A/B 为 30**（已登记的协议偏差）；
  其逐条一致性检查尚未收口，结论页已显式标注为待收口项。
- **`compiler_hard_exact` 不等于 `main_chain_where`**：B 在 `language_exam_dual` 上为 4/8 对 6/8。
  两指标不得互相替代引用。

更新数据：

```bash
python3 scripts/extract_hosted_api_baselines.py   # 托管 API 基线
node scripts/build_presentation.mjs              # 重建 presentation.json（含脱敏，见 scripts/ 内的公开边界处理）
npm run validate                                 # 数据纪律校验（--strict）
```
