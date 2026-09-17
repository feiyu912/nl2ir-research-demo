import type { OverlapReport } from '../data/types';

type Props = {
  overlap: OverlapReport;
};

export default function OverlapReportCard({ overlap }: Props) {
  const { totalFailedRows, whereFailures, semanticFailures, intersection } = overlap;
  return (
    <div className="callout">
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <div className="tiny fg-2">失败记录（跨 6 组）</div>
          <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>{totalFailedRows}</div>
        </div>
        <div>
          <div className="tiny fg-2">Canonical Where 失败</div>
          <div className="num" style={{ fontSize: 20, fontWeight: 600, color: 'var(--c-4b)' }}>{whereFailures}</div>
        </div>
        <div>
          <div className="tiny fg-2">Semantic 失败</div>
          <div className="num" style={{ fontSize: 20, fontWeight: 600, color: 'var(--c-api)' }}>{semanticFailures}</div>
        </div>
        <div>
          <div className="tiny fg-2">交集</div>
          <div className="num" style={{ fontSize: 20, fontWeight: 600, color: 'var(--warn)' }}>{intersection}</div>
        </div>
      </div>
      <div className="small fg-2" style={{ marginTop: 10 }}>
        三者是重叠集合，禁相加：{whereFailures} + {semanticFailures} − {totalFailedRows} = {Math.max(whereFailures + semanticFailures - totalFailedRows, 0)}（交集）。
      </div>
    </div>
  );
}