import type { ReactNode } from 'react';

type Props = {
  title: string;
  hint?: ReactNode;
};

export default function EmptyState({ title, hint }: Props) {
  return (
    <div className="empty-state">
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{title}</div>
      {hint ? <div className="small">{hint}</div> : null}
    </div>
  );
}
