# 数据纪律（Data Discipline）

> 这是 NL2IR 研究展示 demo 的**红线**。任何组件、任何脚本、任何 prompt 不得违反。
>
> 详细字段不变量见 `scripts/validate_data.py` 与 `src/data/discipline.ts`。

## 不可破的纪律

| # | 纪律 | 落地方式 |
|---|------|----------|
| 1 | **不挑最高分** | 所有 run 默认在数据矩阵里全显示；只有可比性 chip 区分；不允许默认隐藏低分 |
| 2 | **不静默混用 Gold/盲测/评分口径** | 每个 run 必须有 `kind` + `compatibility[]`；同色相不同明度或不同线型 |
| 3 | **指标不可加和** | 永远渲染 `correct/total (accuracy)`；分组聚合时显式标 `n=` 与口径 |
| 4 | **不编造数据** | 训练 loss 只能有 3 个真实点；240 之外的数字必须有显式 source |
| 5 | **不改源研究文件** | 提取只读；绝不覆写 `[内部来源路径未公开]`、`/dat/...`、`[内部来源路径未公开]` |
| 6 | **缺数据 ≠ 0** | 卡片渲染 `数据缺失 / not in local input`；门控列没有则显式空 |

## 指标口径

### 10 个核心指标

| 指标 | 含义（从评分脚本读取） |
|------|------------------------|
| `strict_json` | 严格 JSON 解析 |
| `recoverable_json` | 可恢复 JSON |
| `schema` | Schema 合规 |
| `strict_where` | WHERE 子句严格匹配 |
| `main_chain_where` | 主链 WHERE 匹配 |
| `order_value_invariant_where` | 顺序与值不敏感 WHERE |
| `semantic_exact` | 语义精确匹配 |
| `canonical_where`（额外） | 主链 WHERE + canonical where（与 prompt 锚点 222/240 匹配） |
| `main_chain_ir` | 主链 IR 匹配 |
| `compiler_hard_exact` | 编译器硬精度（ES 代理） |
| `executable_main_chain` | 可执行主链 |

> 注意：`canonical_where` 由 `main_chain_where` 推断；本 demo 在前端派生，不在 `metrics.json` 中独立存储。

### 指标 vs 总分

**绝不**对指标求和作为总分。任何"总和"渲染都需要去掉。

## 600 / 222 / 440 关系

```
600 全部失败记录（跨运行记录，不是 600 条独立题目）
├── 222 Canonical Where 失败主归因
└── 440 Semantic 失败
    intersection = 222 + 440 - 600
```

- 是**重叠集合**，不是分层；
- 任何 `count + count` 渲染必须改为维恩草图；
- 前端 `OverlapReportCard` 必须始终可见。

## 训练 Loss

- **真实数据点**：4B/9B 各 3 轮平均 loss（每轮一个真实点）。
- **不画完整曲线**：无原始逐 step loss 在本机。
- **额外声明**：291 步完整连续、日志 loss 与梯度无 NaN/Inf、checkpoint-200 vs 最终模型 blind 持平（198/240 + 209/240）。
- **不宣称**：低 loss 推泛化好、9B 差距是过拟合/欠拟合、相同参数更大模型更好。

## 训练内 vs 独立验证

| 数据集 | 用途 | 标签 | 备注 |
|--------|------|------|------|
| `old366` | 训练内诊断 | `in-train-diagnostic` | 历史 356/366 是开发口径，不是新 blind |
| `C300` | 训练内诊断 | `in-train-diagnostic` | 历史 271/300 是 v19 口径，不是 v21 Gold 重评 |
| `blind-v6` | 正式盲测 | `single-pass` / `post-assertion` | sealed 240 |
| `C-hard240` | 训练监督 | `in-train-supervision` | **不是独立验证**；训练内 100% 不等于泛化 100% |

## 历史 vs 正式

- 旧集 API 的 356/366、97.27%：**开发口径**，不是新 blind。
- C300 历史 API 的 271/300、90.33%：v19 口径，不是 v21 Gold 重评。
- blind v4 单次 217/240、冻结 repair-v1 后 231/240、后验改进 237/240：237/240 不是正式 untouched blind。
- 盲测开发期间已查看数据集的运行，其后续改进不能继续冒充 untouched。

## 数据集与盲测区分

| 区分维度 | 描述 |
|----------|------|
| **数据集身份** | 优先依据 `coverage.json.actual_dataset` 与输入内容核验，不只信 WebUI 改写的配置 |
| **模型底座** | 目录 `*-Base` 命名仅是命名，不足以证明底座是 Base 版本；需独立核实 |
| **盲测冻结** | 独立 blind 运行时冻结 vs 已查看数据集状态分开说明；历史 blind 可保留当时性质，后续开发不能冒充 |

## 来源优先级

`原始结果与配置 > 对应审计报告 > 研究母版 > 本提示词锚点`

冲突时记录并解释，**不静默选更高数字**。对历史结果保留当时口径，不用后验 Gold 覆盖。

## 校验脚本行为

| 检查项 | 期望 | 失败处理 |
|--------|------|----------|
| `correct ≤ total` | 强制 | run 标红 `invalid` |
| `accuracy == correct/total` | 强制 | 自动修复 + 警告 |
| `ci95 ∈ [0,1]` | 强制 | 移除 ci + 警告 |
| `runId` 全局唯一 | 强制 | 报错 |
| `date` 形如 YYYY-MM-DD 且非空 | 强制 | 警告 |
| `sources[].path` 存在 | 强制 | 改 `note: 'not-in-local'` |
| `kind=in-train-diagnostic` 必须有 `note` | 强制 | 警告 |
| `compat` 不可同时含 `comparable-with-blind-v6` 与 `historical-only` | 强制 | 报错 |
| 不存在 `data/cases.json` 与 `data/raw/` | 强制 | 报错并停止公开部署 |
| `overlap_report` `222+440 ≥ 600` 且 `intersection=222+440-600` | 强制 | 报错 |
| `training.json` step 整数、loss float、无 NaN | 强制 | 报错 |
| 6 组学生评测 n=240 与 `coverage.json` n 一致 | 强制 | 警告 |
