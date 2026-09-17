import type { ModelId, RunKind } from '../data/types';
import { KIND_LABEL } from '../data/types';

type Props = {
  model?: ModelId;
  kind?: RunKind;
  size?: 'sm' | 'md';
};

export function ModelBadge({ model }: { model: ModelId; size?: 'sm' | 'md' }) {
  const fontSize = 12;
  return (
    <span className={`badge b-${model.toLowerCase()}`} style={{ fontSize }}>
      {model}
    </span>
  );
}

export function KindBadge({ kind }: { kind: RunKind; size?: 'sm' | 'md' }) {
  const cls =
    kind === 'in-train-diagnostic'
      ? 'badge b-warn'
      : kind === 'single-pass'
      ? 'badge b-ok'
      : 'badge';
  const fontSize = 12;
  return (
    <span className={cls} style={{ fontSize }}>
      {KIND_LABEL[kind]}
    </span>
  );
}

export default function RunBadge({ model, kind }: Props) {
  return (
    <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
      {model ? <ModelBadge model={model} size="sm" /> : null}
      {kind ? <KindBadge kind={kind} size="sm" /> : null}
    </span>
  );
}