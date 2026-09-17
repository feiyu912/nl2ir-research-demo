/**
 * 静态数据加载器：使用 import.meta.glob 把 data/*.json 与 data/aux/*.json
 * 一次性打包到前端 bundle，运行时无网络请求。
 */

import type {
  Case,
  Conclusion,
  Dataset,
  DataSnapshot,
  ErrorCodes,
  HistoricalExperiments,
  Metric,
  OverlapReport,
  PromptEvolution,
  ResearchQuestions,
  Run,
  SourceRef,
  StageEvent,
  ResearchStage,
  TrainingPoint,
} from './types';

// Vite 的 import.meta.glob：eager + import default + JSON 解析
const jsonModules = import.meta.glob<{ default: unknown }>('../../data/*.json', {
  eager: true,
  import: 'default',
});

const auxModules = import.meta.glob<{ default: unknown }>('../../data/aux/*.json', {
  eager: true,
  import: 'default',
});

function read<T>(path: string): T {
  const key = `../../data/${path}`;
  const m = jsonModules[key];
  if (!m) {
    throw new Error(`数据文件未加载: ${path}`);
  }
  return m as unknown as T;
}

function readAux<T>(path: string): T {
  const key = `../../data/aux/${path}`;
  const m = auxModules[key];
  if (!m) {
    throw new Error(`aux 文件未加载: ${path}`);
  }
  return m as unknown as T;
}

function readDatasets(): Dataset[] {
  return (read<{ datasets: Dataset[] }>('datasets.json')).datasets;
}

function readRuns(): Run[] {
  return read<Run[]>('runs.json');
}

function readMetrics(): Metric[] {
  return read<Metric[]>('metrics.json');
}

function readStages(): StageEvent[] {
  const blob = read<{ stages: StageEvent[] }>('stages.json');
  return blob.stages ?? [];
}

function readResearchTimeline(): ResearchStage[] {
  const blob = read<{ stages: ResearchStage[] }>('research_timeline.json');
  return blob.stages ?? [];
}

function readPromptEvolution(): PromptEvolution {
  return read<PromptEvolution>('prompt_evolution.json');
}

function readResearchQuestions(): ResearchQuestions {
  return read<ResearchQuestions>('research_questions.json');
}

function readHistoricalExperiments(): HistoricalExperiments {
  return read<HistoricalExperiments>('historical_experiments.json');
}

function readTraining(): {
  points: TrainingPoint[];
  config?: Record<string, unknown>;
  caveats?: string[];
  checkpointCompare?: unknown;
} {
  return read<{
    points: TrainingPoint[];
    config?: Record<string, unknown>;
    caveats?: string[];
    checkpointCompare?: unknown;
  }>('training.json');
}

function readCases(): Case[] {
  return read<Case[]>('cases.json');
}

function readConclusions(): Conclusion[] {
  return read<Conclusion[]>('conclusions.json');
}

function readSources(): SourceRef[] {
  return read<SourceRef[]>('sources.json');
}

function readOverlap(): OverlapReport {
  return readAux<OverlapReport>('overlap_report.json');
}

function readErrorCodes(): ErrorCodes {
  return readAux<ErrorCodes>('error_codes.json');
}

function readApiSealedV6(): Record<string, unknown> | undefined {
  try {
    return readAux<Record<string, unknown>>('api_sealed_v6.json');
  } catch {
    return undefined;
  }
}

function readHistoryBundles() {
  try {
    const blob = readAux<{ bundles: Array<{ file: string; path: string; size?: number; entryCount?: number; note?: string }> }>(
      'history_overview.json'
    );
    return blob.bundles;
  } catch {
    return [];
  }
}

function readVerifiedOverlay() {
  try {
    return readAux<{ paragraphs: Array<{ text: string; stage?: string; date?: string }> }>(
      'verified_overlay.json'
    );
  } catch {
    return undefined;
  }
}

let _snapshot: DataSnapshot | null = null;

export function loadSnapshot(): DataSnapshot {
  if (_snapshot) return _snapshot;
  _snapshot = {
    datasets: readDatasets(),
    runs: readRuns(),
    metrics: readMetrics(),
    stages: readStages(),
    researchTimeline: readResearchTimeline(),
    promptEvolution: readPromptEvolution(),
    researchQuestions: readResearchQuestions(),
    historicalExperiments: readHistoricalExperiments(),
    training: readTraining(),
    cases: readCases(),
    conclusions: readConclusions(),
    sources: readSources(),
    overlap: readOverlap(),
    errorCodes: readErrorCodes(),
    apiSealedV6: readApiSealedV6(),
    historyBundles: readHistoryBundles(),
    verifiedOverlay: readVerifiedOverlay(),
  };
  return _snapshot;
}

export function getRunById(runId: string): Run | undefined {
  return loadSnapshot().runs.find((r) => r.runId === runId);
}

export function getMetricsByRun(runId: string): Metric[] {
  return loadSnapshot().metrics.filter((m) => m.runId === runId);
}
