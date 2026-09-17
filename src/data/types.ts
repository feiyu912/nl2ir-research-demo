/**
 * NL2IR 展示 demo 数据类型定义。
 * 与 docs/SCHEMA.md 对齐。
 */

export type ModelId = '4B' | '9B' | 'API';

export type RunKind =
  | 'single-pass'
  | 'post-assertion'
  | 'repeated-blind'
  | 'checkpoint-blind'
  | 'in-train-diagnostic'
  | 'historical-dev'
  | 'reconciled'
  | 'joint';

export type Compatibility =
  | 'comparable-with-blind-v6'
  | 'comparable-with-old366'
  | 'comparable-with-c300'
  | 'historical-only'
  | 'diagnostic-only'
  | 'reference-only';

export type MetricName =
  | 'strict_json'
  | 'recoverable_json'
  | 'schema'
  | 'strict_where'
  | 'main_chain_where'
  | 'order_value_invariant_where'
  | 'semantic_exact'
  | 'main_chain_ir'
  | 'compiler_hard_exact'
  | 'executable_main_chain';

export const ALL_METRICS: MetricName[] = [
  'strict_json',
  'recoverable_json',
  'schema',
  'strict_where',
  'main_chain_where',
  'order_value_invariant_where',
  'semantic_exact',
  'main_chain_ir',
  'compiler_hard_exact',
  'executable_main_chain',
];

export const METRIC_LABEL: Record<MetricName, string> = {
  strict_json: 'Strict JSON',
  recoverable_json: 'Recoverable JSON',
  schema: 'Schema',
  strict_where: 'Strict Where',
  main_chain_where: 'Main Chain Where',
  order_value_invariant_where: 'Order/Value Invariant Where',
  semantic_exact: 'Semantic Exact',
  main_chain_ir: 'Main Chain IR',
  compiler_hard_exact: 'Compiler Hard',
  executable_main_chain: 'Executable Main Chain',
};

export const KIND_LABEL: Record<RunKind, string> = {
  'single-pass': '单次裸输出',
  'post-assertion': '门控后',
  'repeated-blind': '重复盲测',
  'checkpoint-blind': 'Checkpoint',
  'in-train-diagnostic': '训练内诊断',
  'historical-dev': '历史开发',
  'reconciled': '语义调和',
  'joint': '联合训练',
};

export type SourceRef = {
  kind: 'docx' | 'paper-ir' | 'student-eval' | 'student-audit' | 'tar' | 'server-path';
  label?: string;
  path: string;
  lineOrId?: string;
  excerpt?: string;
  date?: string;
  note?: string;
};

export type Run = {
  runId: string;
  date: string;
  model: ModelId;
  method: string;
  methodVersion: string;
  dataset: string;
  datasetVersion: string;
  sampleSize: number;
  kind: RunKind;
  compatibility: Compatibility[];
  sources: SourceRef[];
  tags: string[];
  notes?: string;
  shas?: Record<string, string | string[] | undefined>;
};

export type Metric = {
  runId: string;
  metric: MetricName;
  correct: number;
  total: number;
  accuracy: number;
  ci95?: [number, number];
};

export type Case = {
  caseId: string;
  runId: string;
  query: string;
  groupId: string;
  flags: Record<string, boolean>;
  gold: { where?: unknown; semantic?: unknown; sort?: unknown };
  prediction: { where?: unknown; semantic?: unknown; sort?: unknown; meta?: unknown };
  attribution?: 'M' | 'R' | 'P' | 'G' | 'F';
  attributionText?: string;
  issues?: unknown[];
  source: SourceRef;
};

export type StageEvent = {
  stage: string;
  order?: number;
  title: string;
  summary: string;
  date?: string;
  question?: string;
  assumption?: string;
  experiments?: Array<{ name: string; date?: string; note?: string; result?: string }>;
  results?: string[];
  findings?: string[];
  decisions?: string[];
  nextDecision?: string | string[];
  sources?: SourceRef[];
  chart?: { type: string; title: string; subtitle?: string } | null;
  caseIds?: string[];
  refs?: SourceRef[];
};

// 为研究主线阶段保留向后兼容（合并了 refs 与 sources）
export type ResearchStage = StageEvent & {
  mainDisplay?: {
    metric: string;
    rows: Array<{
      model: '4B' | '9B' | 'API' | string;
      subtype: string;
      old366: string | null;
      C300: string | null;
      blind_v6: string;
      kind: string;
      note?: string;
    }>;
  };
  conclusionsAccurate?: {
    headline: string;
    items: string[];
  };
};

export type PromptVersion = {
  label: string;
  stage?: string;
  status?: string;
  source?: string;
  file?: string | null;
  lines?: number | null;
  bytes?: number | null;
  linesMeasured?: number;
  notes?: string[];
  rulesFocus?: string;
  examplesTradeoff?: string;
  outputContract?: string;
  queryLabelChanged?: boolean;
  experiments?: string[];
  singleFactorCaveat?: string;
  sha256?: string;
  sha256_user_file?: string;
  sha256_runtime_stripped?: string;
};

export type PromptEvolution = {
  note: string;
  series: Array<{
    label: string;
    title: string;
    notes?: string;
    earlyVersions?: { label: string; status: string; note?: string };
    versions: PromptVersion[];
  }>;
  blindEvolution?: {
    note: string;
    items: Array<{ label: string; samples: number | null; firstSeen: string; fate: string }>;
  };
  dataInvariance?: Record<string, string>;
  tokenCaveats?: string[];
};

export type ResearchQuestion = {
  id: string;
  title: string;
  problem: string;
  actions: string[];
  evidence: string[];
  conclusion: string;
};

export type ResearchQuestions = {
  note: string;
  why: {
    goal: string;
    localValue: string;
    evidenceStatus: {
      costSaving: string;
      privacyGain: string;
      latencyGain: string;
    };
  };
  problems: ResearchQuestion[];
  currentLevel: {
    headline: string;
    discipline: string[];
    groups: Array<{
      label: string;
      rows: Array<{
        label: string;
        where: string;
        schema: string | null;
        kind: string;
        note?: string;
      }>;
    }>;
    knownLimits: string[];
  };
  nextSteps: {
    principles: string[];
    evidentiaryNeeds: string[];
    businessTrialCondition: string;
  };
};

export type PromptSolution = {
  id: string;
  title: string;
  stage: string;
  file?: string | null;
  lines?: number | null;
  bytes?: number | null;
  linesMeasured?: number;
  sha256?: string;
  sha256_user_file?: string;
  sha256_runtime_stripped?: string;
  excerpt?: string;
  features?: string[];
  whatChanged?: string;
  approach?: string[];
  dataInvariance?: Record<string, string>;
  tokenGate?: string;
  description?: string;
  rules?: Array<{
    version: string;
    change: string;
    experiment: Array<{
      name: string;
      condition?: string;
      dataset?: string;
      result: string;
      status: string;
    }>;
  }>;
  responsibilities?: string[];
  pipeline?: string[];
  experiment?: Array<{
    name: string;
    condition?: string;
    dataset?: string;
    result: string;
    status: string;
  }>;
  shas?: string[];
  caveats?: string[];
  discipline?: string[];
};

export type PromptSolutions = {
  note: string;
  solutions: PromptSolution[];
};

export type HistoricalExperiment = {
  label: string;
  model?: string;
  prompt?: string;
  dataset?: string;
  metric?: string;
  status: string;
  source?: string;
  note?: string;
};

export type HistoricalExperimentGroup = {
  id: string;
  title: string;
  purpose?: string;
  experiments: HistoricalExperiment[];
};

export type HistoricalExperiments = {
  note: string;
  groups: HistoricalExperimentGroup[];
};

export type Conclusion = {
  stage: string;
  category: 'fact' | 'interpretation' | 'hypothesis' | 'plan';
  text: string;
  source: SourceRef;
  date?: string;
};

export type TrainingPoint = {
  runId: string;
  epoch: number;
  loss: number;
  source: SourceRef;
  note?: string;
};

export type Dataset = {
  datasetId: string;
  label: string;
  sampleSize: number;
  purpose: 'sealed-blind' | 'in-train-diagnostic' | 'historical-dev' | 'in-train-supervision';
  goldVersion: string;
  sealedDate?: string;
  notes?: string;
};

export type OverlapReport = {
  totalFailedRows: number;
  whereFailures: number;
  semanticFailures: number;
  intersection: number;
  categoryCounts: Record<string, number>;
  note: string;
  source?: string;
};

export type ErrorCodes = {
  scope: string;
  interpretation: string;
  categories: Record<'M' | 'R' | 'P' | 'G' | 'F', string>;
  warning: string;
  executionBoundaries: {
    noApiCalls?: boolean;
    noGpuInference?: boolean;
    noGoldChanges?: boolean;
    noScoreChanges?: boolean;
    promptSha256?: string;
  };
};

export type DataSnapshot = {
  datasets: Dataset[];
  runs: Run[];
  metrics: Metric[];
  stages: StageEvent[];
  researchTimeline: ResearchStage[];
  researchQuestions: ResearchQuestions;
  promptEvolution: PromptEvolution;
  historicalExperiments: HistoricalExperiments;
  training: { points: TrainingPoint[]; config?: Record<string, unknown>; caveats?: string[]; checkpointCompare?: unknown };
  cases: Case[];
  conclusions: Conclusion[];
  sources: SourceRef[];
  overlap: OverlapReport;
  errorCodes: ErrorCodes;
  apiSealedV6?: Record<string, unknown>;
  historyBundles?: Array<{ file: string; path: string; size?: number; entryCount?: number; note?: string }>;
  verifiedOverlay?: { paragraphs: Array<{ text: string; stage?: string; date?: string }> };
};
