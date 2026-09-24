# 数据 Schema（8 类核心 JSON + 1 类独立实验数据）

> 全部 JSON 由 `scripts/*.py` 产出，不在 React 组件中硬编码数字。
>
> 字段级不变量在 `scripts/validate_data.py` 中强制；前端等价校验在 `src/data/discipline.ts`。

## 1. `data/datasets.json`

```ts
type Dataset = {
  datasetId: string;            // "blind-v6" / "C300" / "old366" / "C-hard240"
  label: string;                // 中文展示名
  sampleSize: number;
  purpose: 'sealed-blind' | 'in-train-diagnostic' | 'historical-dev' | 'in-train-supervision';
  goldVersion: string;
  notes?: string;
};
```

## 2. `data/runs.json`

```ts
type Model = '4B' | '9B' | 'API';
type Kind = 'single-pass' | 'post-assertion' | 'repeated-blind' | 'checkpoint-blind'
          | 'in-train-diagnostic' | 'historical-dev' | 'reconciled' | 'joint';
type Compat = 'comparable-with-blind-v6' | 'comparable-with-old366'
            | 'comparable-with-c300' | 'historical-only' | 'diagnostic-only'
            | 'reference-only';

type Run = {
  runId: string;
  date: string;                 // ISO YYYY-MM-DD
  model: Model;
  method: string;               // "paper_ir_v1" / "student-lora-9b" / ...
  methodVersion: string;
  dataset: string;
  datasetVersion: string;
  sampleSize: number;
  kind: Kind;
  compatibility: Compat[];
  sources: SourceRef[];
  tags: string[];
  notes?: string;
};
```

## 3. `data/metrics.json`

```ts
type MetricName = 'strict_json' | 'recoverable_json' | 'schema'
                | 'strict_where' | 'main_chain_where' | 'order_value_invariant_where'
                | 'semantic_exact' | 'main_chain_ir' | 'compiler_hard_exact'
                | 'executable_main_chain';

type Metric = {
  runId: string;
  metric: MetricName;
  correct: number;
  total: number;
  accuracy: number;             // 4 位小数
  ci95?: [number, number];
};
```

## 4. `data/stages.json`

```ts
type StageEvent = {
  stage: string;                // "2-prompt-iteration" / ...
  title: string;
  summary: string;
  decisions: string[];
  failures: string[];
  refs: SourceRef[];
};
```

> 阶段不是时间线，而是研究问题的归集点（标签）。不按日期排序，无 inMainScope 字段。

## 5. `data/training.json`

```ts
type TrainingPoint = {
  runId: string;                // "4b-lora" / "9b-lora"
  epoch: number;                // 1 / 2 / 3
  loss: number;                 // 该 epoch 平均 loss（不是虚构的 step 值）
  source: SourceRef;
  note?: string;                // "average-of-N-runs" / "no-NaN-confirmed"
};
```

## 6. 逐题测评数据（不公开）

公开发行版不包含逐题 query、Gold、模型预测或可还原 benchmark 的标识。页面只读取聚合指标和统计结论；CI 会拒绝 `data/cases.json` 与 `data/raw/`。

## 7. `data/conclusions.json`

```ts
type Conclusion = {
  stage: string;
  text: string;                 // 摘录或总结，≤200 字
  category: 'fact' | 'interpretation' | 'hypothesis' | 'plan';
  date?: string;
  source: SourceRef;
  refs?: SourceRef[];           // 交叉引用
};
```

## 8. `data/sources.json`

```ts
type SourceRef = {
  kind: 'docx' | 'paper-ir' | 'student-eval' | 'student-audit' | 'tar' | 'server-path';
  label: string;                // "主版 / 9B 训练检查 / 核验 overlay"
  path: string;                 // 绝对路径（仅本地）
  lineOrId?: string;
  excerpt?: string;             // ≤200 字
  date?: string;
  note?: string;                // "server-not-local" / "aggregated-only-in-docx"
};
```

---

## 辅助 JSON（`data/aux/`）

| 文件 | 字段摘要 |
|------|----------|
| `overlap_report.json` | `{totalFailed: 600, whereFailures: 222, semanticFailures: 440, intersectionWhereSemantic: 222+440-600, note}` |
| `error_codes.json` | 5 类主归因 `M`/`R`/`P`/`G`/`F` 含义 |
| `history_overview.json` | 14 个 tar.gz 包的只读清单 |
| `verified_overlay.json` | 核验补全版相对主版的独立段落 |

---

## 9. `data/hosted_api_baselines.json`（独立实验数据）

> **这是独立的托管 API 模型选型实验，不是 4B/9B LoRA 训练实验。**
> 展示时必须与 `runs.json` / `metrics.json` 的 LoRA 图表分开，不得混入同一组图。

由 `scripts/extract_hosted_api_baselines.py` 从
`semantic-search-service/docs/modeltest/nl2ir_api_ab_qwen37max_vs_deepseekv41flash_2026-09-17/`
的正式工件提取。**只读来源，不调用模型/API，不重新评分。**

```ts
type HostedApiBaselines = {
  schema: 'hosted-api-baselines/v1';
  experimentDate: string;              // "2026-09-17"
  track: string;                       // Track A: frozen v21 prompt + json_object + frozen scorer
  primaryMetric: 'main_chain_where';
  n: 906;                              // old366 366 + c300 300 + blind-v6 240
  sourceDir: string;                   // 本地绝对路径（仅本地）
  sourceLabel: string;                 // 展示用相对路径
  sourceFiles: Record<string, {sha256: string; bytes: number}>;
  frozenAssets: {
    prompt: {path: string; sha256: string};
    scorer: {path: string; sha256: string};
    contract: {path: string; sha256: string; nFields: number};
    datasets: Record<string, {rows: number; sha256: string}>;
  };
  datasets: {
    old366: {n: 366; purpose: string};
    c300: {n: 300; purpose: string};
    blindV6: {n: 240; purpose: string; split: {stress96: 96; realistic144: 144}};
    combined: {n: 906; note: string};
  };
  models: Array<{
    alias: 'qwen' | 'qwen38' | 'deepseek';
    modelId: 'qwen3.7-max' | 'qwen3.8-flash' | 'deepseek-v4.1-flash';
    role: string;                      // 冻结措辞：质量基线 / 低成本候选 / 当前不建议替换
    conclusion: string;
    tone: 'baseline' | 'candidate' | 'hold';
    n: 906;
    combinedWhere: number;             // 百分数，如 94.26
    combinedWhereCorrect: number;
    slices: {
      old366: {n: number; where: number; whereCorrect: number};
      c300: {n: number; where: number; whereCorrect: number};
      blindV6: {n: number; where: number; whereCorrect: number};
      stress96: {n: 96; where: number; note: string};   // blind-v6 子集，不重复计入 combined
    };
    hardF1: number;
    hardCondition: {goldTotal: number; tp: number; precision: number; recall: number};
    redlines: {
      trueDroppedRequired: number;     // 真删除必填条件（无替代过滤）——安全口径
      allRequiredMissingItems: number;
      allRequiredMissingIds: string[];
      fieldSubstitution: number;
      notFlippedPositive: number;
      numericDirectionFlip: number;
      hallucinatedConditions: number;
      invalidWhereNodeItems: number;
    };
    latency: {p50: number; p95: number; transportFailureRequests: number};
    cost: {
      standardized: {caliber: string; tiers: Array<{tier: string; cnyPer10k: number}>};
      observedRun: {caliber: string; tiers: Array<{tier: string; cnyPer10k: number;
                    cacheHitRate: number; completionTokensPerRequest: number}>};
    };
  }>;
  pairwise: Array<{
    key: string; a: string; b: string;
    netFixesBMinusA: number;
    aOnlyCorrect: number; bOnlyCorrect: number; bothCorrect: number; bothWrong: number;
    qualityChangePp: number;
    mcnemarExactP: number;
    ciPlain: [number, number];
    ciCluster: [number, number];
    clusterCrossesZero: boolean;       // true ⇒ 该方向不得宣称显著
  }>;
  threeWay: Record<string, number>;
  conclusions: Record<string, number | string>;
  limitations: string[];
  costNotes: string[];
};
```

### 硬性不变量（`scripts/validate_data.py` → `check_hosted_api_baselines`）

- `n = 906` 且 `366 + 300 + 240`；`stress96 + realistic144 = 240`，**不重复计入 combined**；
- 三个模型 ID 必须正好是 `qwen3.7-max` / `qwen3.8-flash` / `deepseek-v4.1-flash`；
- primary 必须是 `main_chain_where`；
- `combinedWhere` = 94.26 / 89.62 / 86.20，且必须与三切片加权一致；
- **两套成本口径必须同时存在**：`standardized` 与 `observedRun`；
  - 标准化 ¥/万次：201.60 / 12.60 / 16.40（闲）· 32.80（忙）；
  - 实测 ¥/万次：242.83 / 16.51 / 9.67（闲）· 19.34（忙）；
  - qwen3.8 标准化成本必须**低于** DeepSeek 闲时；
- **`observed_run_cost` 不得命名为 price index**（只允许 `not a price index` 这一否定式声明）；
- `clusterCrossesZero` 必须与 `ciCluster` 区间自洽；
- 六个来源文件的 SHA256 必须齐全；
- `limitations` 必须包含 role_tenure 的"仍在验证"声明；模型结论中不得出现 role_tenure 实现结论。

## 10. `data/api_stability.json`（API 重复推理，独立实验）

- 仅发布聚合计数：4 个模型 × 50 条偏难查询 × 3 次，600 次请求完成；不发布逐题 query、Gold 或响应。
- `models[]` 保存逐字一致、规范化 IR 一致、Where 对错翻转、Wilson 95% 区间、三次正确数及格式异常题数。
- `qwen3.8-max` 仅属于该稳定性实验，未参加上方 906 条三模型质量与成本对比。
- 原始实验报告中的 `flip_cp_ci` 因缺少 SciPy 回退为 Wilson；公开页明确按 Wilson 标注。
- 只测 API 直调端点和偏难样本；不得外推为线上故障率或本地小模型的稳定性结论。
