import type { ReactNode } from 'react';

type Props = {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: 'default' | 'warn' | 'error' | 'ok';
};

export default function NumberCard({ label, value, sub, tone = 'default' }: Props) {
  const valueStyle: React.CSSProperties = {};
  if (tone === 'warn') valueStyle.color = 'var(--warn)';
  if (tone === 'error') valueStyle.color = 'var(--error)';
  if (tone === 'ok') valueStyle.color = 'var(--ok)';

  return (
    <div className="card metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value num" style={valueStyle}>
        {value}
      </div>
      {sub ? <div className="tiny fg-2" style={{ marginTop: 6 }}>{sub}</div> : null}
    </div>
  );
}