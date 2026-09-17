# 来源映射（Sources）

> 每个数据点都对应至少一条 SourceRef。展示组件 `SourceLinker` 渲染完整路径与摘录。

## 8 条 Run（runs.json）

| runId | model | dataset | kind | 来源文件 |
|-------|-------|---------|------|----------|
| `api-blindv6-one-pass` | API | blind-v6 | single-pass | `paper_ir_v1_blind_v6_qwen37max_candidate_v4_one_pass/metrics.json` |
| `api-blindv6-assertion-v7` | API | blind-v6 | post-assertion | `paper_ir_v1_blind_v6_qwen37max_candidate_v4_assertion_v7/metrics.json` |
| `4b-old366` | 4B | old366 | in-train-diagnostic | `audit-inputs/Qwen3.5-4B-Base/lora/eval_4b-old366/task_scores/metrics.json` |
| `4b-c300` | 4B | C300 | in-train-diagnostic | `audit-inputs/Qwen3.5-4B-Base/lora/eval_4b-c300/task_scores/metrics.json` |
| `4b-blindv6` | 4B | blind-v6 | single-pass | `audit-inputs/Qwen3.5-4B-Base/lora/eval_4b-blindv6/task_scores/metrics.json` |
| `9b-old366` | 9B | old366 | in-train-diagnostic | `audit-inputs/Qwen3.5-9B-Base/lora/eval_9b-old366/task_scores/metrics.json` |
| `9b-c300` | 9B | C300 | in-train-diagnostic | `audit-inputs/Qwen3.5-9B-Base/lora/eval_9b-c300/task_scores/metrics.json` |
| `9b-blindv6-initial` | 9B | blind-v6 | single-pass | `audit-inputs/Qwen3.5-9B-Base/lora/eval_9b-blindv6-initial/task_scores/metrics.json` |

> 9B 重复 blind 与 checkpoint-200 blind 原始数据在服务器 `[服务器来源路径未公开]`，本机不可访问，仅引用 DOCX 聚合。

## 关键结论来源

| 阶段 | 关键结论 | 来源 |
|------|----------|------|
| 5-assertion-gate | 8/240 额外 API 调用，修复 5 条、破坏 0 条 | `nl2ir_strong_api_pipeline_candidate_v4_2026-09-14.json` → sealed_blind_v6_untouched |
| 5-assertion-gate | blind v5 是 post-hoc development，不是 untouched | 同上 → blind_v5_diagnostic.warning |
| 6-strong-api | qwen3.7-max 管线 4 阶段 | 同上 → pipeline |
| 6-strong-api | sealed blind v6 摘要（单次 229/240 等） | 同上 → sealed_blind_v6_untouched |
| 6-strong-api | next_required_experiment | 同上 → next_required_experiment |
| 7-student-training | 1543 = 1303 + 240 C-hard | 核验补全版母版 |
| 7-student-training | 3 轮 loss 平均 | 核验补全版母版 + 9B 训练检查母版 |
| 9b-training-audit | 291 步无 NaN/Inf | 9B 训练检查母版 |
| 9b-training-audit | checkpoint-200 vs 最终盲测持平 | 同上 |
| 9b-training-audit | 600 / 222 / 440 / intersection=62 | `nl2ir_student_six_eval_prompt_audit/attribution.json` |

## 5 类主归因（error_codes.json）

| 码 | 含义 | 来源 |
|----|------|------|
| M | prompt 已有明确规则：实质内容未执行 | `summary.json.categories.M` |
| R | prompt 已有明确表示规则：表达不合规，但意图未发现实质改变 | `summary.json.categories.R` |
| P | prompt/输入契约不充分或表达存在歧义 | `summary.json.categories.P` |
| G | Gold/严格评分差异：不能据此认定模型未执行 prompt | `summary.json.categories.G` |
| F | 非法 JSON 或 Schema：输出契约未执行 | `summary.json.categories.F` |

## 训练数据

| 项 | 值 | 来源 |
|----|----|------|
| 训练集大小 | 1543 (1303 + 240 C-hard) | 核验补全版 |
| 4B Epoch 1/2/3 平均 loss | 0.05076 / 0.01895 / 0.01115 | 核验补全版 |
| 9B Epoch 1/2/3 平均 loss | 0.04889 / 0.01836 / 0.01098 | 9B 训练检查母版 |
| 优化器步数 | 291 | 9B 训练检查母版 |
| Checkpoint-200 vs 最终盲测 Where | 198/240（持平） | 9B 训练检查母版 |
| Checkpoint-200 vs 最终盲测 compiler-hard | 209/240 | 9B 训练检查母版 |

## 服务器路径（不可访问，仅引用）

| 路径 | 内容 | 引用 |
|------|------|------|
| `[服务器来源路径未公开]` | 9B 训练目录 | 仅在 `training.json.checkpointCompare` 引用 |
| `[服务器来源路径未公开]` | 4B 训练目录 | 同上 |
| `[服务器来源路径未公开]` | 9B 重复 blind | `training.json.checkpointCompare.repeatedBlind.rawData` |
| `[服务器来源路径未公开]` | 9B checkpoint-200 blind | `training.json.checkpointCompare.checkpoint200_vs_final.rawData` |
## 托管 API 三模型基线（hosted_api_baselines.json）

独立实验，**不属于**上面的 8 条 Run。来源目录：

`[内部来源路径未公开]`

| 数据点 | 来源文件 |
|--------|----------|
| 分片/总体 Where、hard-F1、红线计数、延迟、token | `three_model_table.json` |
| 配对统计（McNemar、普通与 cluster bootstrap CI） | `three_model_pairwise.json` |
| 两套成本口径与价目、superseded 旧口径 | `cost_model.json` |
| 数据集/prompt/scorer/契约 SHA256、解码契约 | `manifest.json` |
| 人读结果表 | `THREE_MODEL_RESULTS.md` |
| 可引用摘要（结论、限制） | `PUBLICATION_SUMMARY.md` |

提取脚本：`scripts/extract_hosted_api_baselines.py`（只读，不调用模型/API，不重新评分）。

### 冻结资产

| 资产 | SHA256 |
|------|--------|
| v21 eval prompt | `7ca4dea91a7371cd6214469f26439b3084475b23c7dc31d61c0f509af0e29fd0` |
| 冻结 scorer | `3f4b75f9127fcc073285985d3d44fcd776ce35bc6972012de7c9a2b344fba70f` |
| v21 字段契约 | `45e909d94f1f04165a82dc37fc7b951209613bad68d71bc08bcadb33055805a9` |

### 必须随数字一起展示的口径

- **两套成本口径并列**：`standardized_cost`（相同 token 工作量，纯价格比较）与
  `observed_run_cost`（本次真实账单）。**后者不是价格指数**，会随缓存命中率与输出长度浮动。
- DeepSeek 本次账单低来自更高缓存命中（96.1%）与更短输出（138.6 token/请求），
  **不代表单位价格低**；标准化同 token 下它（¥16.40）反而高于 qwen3.8-flash（¥12.60）。
- DeepSeek → qwen3.8 的 +3.42pp **在 family-aware cluster CI 下跨 0**，该方向不得宣称显著。
- 三模型运行时段不同、非交错并发；延迟为本次观察值，**不是生产 SLA**。
- 本实验**不是** Arm A/B 训练消融，**不回答** C-hard 监督的因果作用；
  Arm A 尚未有结果。
