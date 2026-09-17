import { useState } from 'react';
import type { Case } from '../data/types';
import RunBadge from './RunBadge';

type Props = {
  caseData: Case;
};

export default function CaseCard({ caseData }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card" style={{ marginBottom: 8 }}>
      <div className="flex" style={{ justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <div className="flex" style={{ gap: 6, marginBottom: 4 }}>
            <span className="mono small muted">{caseData.caseId}</span>
            <RunBadge model={modelFromRunId(caseData.runId)} kind={undefined} />
            {caseData.attribution ? (
              <span className="badge" style={{ fontSize: 10.5 }}>
                主归因 {caseData.attribution}
              </span>
            ) : null}
          </div>
          <div style={{ fontWeight: 500, fontSize: 13 }}>
            {caseData.query || <em className="muted">（无 query）</em>}
          </div>
        </div>
        <button
          onClick={() => setOpen(!open)}
          style={{
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 4,
            padding: '2px 8px',
            fontSize: 11,
          }}
        >
          {open ? '折叠' : '展开'}
        </button>
      </div>

      {open ? (
        <div style={{ marginTop: 10 }}>
          <h4>Flags</h4>
          <div className="flex" style={{ gap: 6 }}>
            {Object.entries(caseData.flags).map(([k, v]) => (
              <span
                key={k}
                className="badge"
                style={{
                  fontSize: 10.5,
                  background: v ? '#DCFCE7' : '#FEE2E2',
                  color: v ? '#166534' : '#991B1B',
                  borderColor: v ? '#BBF7D0' : '#FECACA',
                }}
              >
                {v ? '✓' : '✗'} {k}
              </span>
            ))}
          </div>

          <h4 style={{ marginTop: 12 }}>Gold</h4>
          <pre>{JSON.stringify(caseData.gold, null, 2)}</pre>

          <h4 style={{ marginTop: 12 }}>Prediction</h4>
          <pre>{JSON.stringify(caseData.prediction, null, 2)}</pre>

          <h4 style={{ marginTop: 12 }}>Source</h4>
          <div className="small mono">
            [{caseData.source.kind}] {caseData.source.label ?? ''} {caseData.source.lineOrId ?? ''}
            <br />
            {caseData.source.path}
            {caseData.source.note ? <span className="muted"> · {caseData.source.note}</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function modelFromRunId(runId: string): '4B' | '9B' | 'API' | undefined {
  if (runId.startsWith('4b') || runId.includes('-4B') || runId.includes(':4B')) return '4B';
  if (runId.startsWith('9b') || runId.includes('-9B') || runId.includes(':9B')) return '9B';
  if (runId.startsWith('api')) return 'API';
  return undefined;
}
