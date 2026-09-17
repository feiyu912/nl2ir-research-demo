import type { SourceRef } from '../data/types';

type Props = {
  source: SourceRef;
  compact?: boolean;
};

export default function SourceLinker({ source, compact = false }: Props) {
  return (
    <div className={`small mono ${compact ? '' : 'card'}`} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div>
        <span className="badge" style={{ fontSize: 10 }}>{source.kind}</span>
        {source.label ? <span style={{ marginLeft: 6 }}>{source.label}</span> : null}
        {source.lineOrId ? <span className="muted" style={{ marginLeft: 6 }}>· {source.lineOrId}</span> : null}
      </div>
      <div className="muted" style={{ wordBreak: 'break-all' }}>{source.path}</div>
      {source.excerpt ? <div style={{ marginTop: 4 }}>{source.excerpt}</div> : null}
      {source.note ? <div className="muted" style={{ fontStyle: 'italic' }}>{source.note}</div> : null}
    </div>
  );
}
