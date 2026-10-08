import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList } from 'recharts';
import data from '../../data/rerank_model_selection.json';

/**
 * 独立实验页：生产检索链路的精排（rerank）情况——模型选型 + 路由回测。
 * 数字全部来自 data/rerank_model_selection.json（由内部提取脚本生成，只含脱敏聚合）。
 * 与 NL2IR 解析评测无关，两者不得混入同一组图。
 */

type ModelRow = (typeof data.models)[number];
type StrategyRow = (typeof data.router.strategies)[number];

const TONE_COLOR: Record<string, string> = {
  baseline: '#335cff',
  candidate: '#15968f',
  value: '#e0a458',
  hold: '#c08ca0',
  incumbent: '#8090aa',
};
const tone = (t: string) => TONE_COLOR[t] ?? '#8090aa';
const f2 = (v: number) => v.toFixed(2);
const share = (v: number) => `${v < 10 ? v.toFixed(1) : Math.round(v)}%`;

function Heading({ tag, title, text }: { tag: string; title: string; text: string }) {
  return (
    <header className="page-heading">
      <span className="eyebrow">{tag}</span>
      <h1>{title}</h1>
      <p>{text}</p>
    </header>
  );
}

function Title({ tag, title, text }: { tag: string; title: string; text?: string }) {
  return (
    <div className="panel-title">
      <span className="eyebrow">{tag}</span>
      <h2>{title}</h2>
      {text && <p>{text}</p>}
    </div>
  );
}

function HBars({ rows, max, caption, height = 250 }: {
  rows: { name: string; value: number; color: string; label: string }[];
  max: number; caption: string; height?: number;
}) {
  return (
    <>
      <div className="research-chart" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 10, right: 78, bottom: 8, left: 0 }} barSize={22}>
            <CartesianGrid stroke="#edf0f6" horizontal={false} />
            <XAxis type="number" domain={[0, max]} axisLine={false} tickLine={false} tick={{ fill: '#8792a8', fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={150} axisLine={false} tickLine={false} tick={{ fill: '#42516b', fontSize: 12 }} />
            <Tooltip cursor={{ fill: '#f5f7fc' }} content={({ active, payload }) => active && payload?.length ? (
              <div className="chart-tip"><strong>{payload[0].payload.name}</strong><span>{payload[0].payload.label}</span></div>
            ) : null} />
            <Bar dataKey="value" radius={[0, 5, 5, 0]} background={{ fill: '#f3f5fa', radius: 5 }} isAnimationActive={false}>
              {rows.map((r) => <Cell key={r.name} fill={r.color} />)}
              <LabelList dataKey="label" position="right" fill="#243858" fontSize={12} fontWeight={600} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-caption">{caption}</p>
    </>
  );
}

export default function RerankOverview() {
  const models: ModelRow[] = data.models;
  const byQuality = [...models].sort((a, b) => b.judgeScore10 - a.judgeScore10);
  const byCost = [...models].sort((a, b) => a.costShareOfBaselinePct - b.costShareOfBaselinePct);
  const cheapest = byCost[0];
  const fastest = [...models].sort((a, b) => a.batchWallP50S - b.batchWallP50S)[0];
  const best = byQuality[0];
  const incumbent = models.find((m) => m.tone === 'incumbent')!;
  const candidates = models.filter((m) => m.tone !== 'incumbent');
  const router = data.router;
  const base = router.baseline;
  const ni = router.nonInferiority;
  const medianMap = data.calibration.medianScoreByModel as Record<string, number>;

  return (
    <>
      <Heading
        tag={`独立实验 · ${data.experimentDate} · 生产检索链路`}
        title="精排模型横向对比与路由回测"
        text={`离线冻结候选池上的精排（rerank）选型：${candidates.length} 个候选 + 现役对照（共 ${models.length} 个模型），质量由独立模型盲评（0–10），成本按公开价目折算为相对基线的比例。与 NL2IR 解析评测无关，两者不得混入同一组图。`}
      />

      <div className="api-callout">
        <strong>口径边界</strong>
        <span>
          评测在固定规模的冻结候选池上复现生产精排路径（只替换模型）；不调线上流量、不发布查询、候选人、逐题输出或可还原评测集的标识。
          判定为独立评审模型盲评（匿名乱序，2 轮/会话），成本口径为{data.track.costCaliber}。
        </span>
      </div>

      <div className="api-insight-grid">
        <article className="api-insight api-insight-primary">
          <span>质量最高（盲评）</span>
          <strong>{f2(best.judgeScore10)}<small> / 10</small></strong>
          <h3>{best.alias}</h3>
          <p>{best.conclusion}</p>
        </article>
        <article className="api-insight api-insight-value">
          <span>成本最低</span>
          <strong>{share(cheapest.costShareOfBaselinePct)}<small> 基线</small></strong>
          <h3>{cheapest.alias}</h3>
          <p>{cheapest.conclusion}</p>
        </article>
        <article className="api-insight api-insight-fast">
          <span>批量耗时最低</span>
          <strong>{fastest.batchWallP50S.toFixed(1)}<small>s P50</small></strong>
          <h3>{fastest.alias}</h3>
          <p>{fastest.conclusion}</p>
        </article>
      </div>

      <div className="two-column api-chart-grid">
        <section className="panel">
          <Title tag="决策图 01 · 质量" title="盲评得分（0–10）" text="同一批冻结候选池、同一评审口径，越高越好" />
          <HBars
            rows={byQuality.map((m) => ({ name: m.alias, value: m.judgeScore10, color: tone(m.tone), label: f2(m.judgeScore10) }))}
            max={10}
            caption="分 · 每场 2 轮盲评取均值（排序合理性 + 理由质量）"
          />
          <p className="chart-caption">
            {best.alias} 以 {f2(best.judgeScore10)} 分居首；现役对照 {incumbent.alias} 为 {f2(incumbent.judgeScore10)} 分，
            差距主要来自弱池查询上的评分失真。
          </p>
        </section>

        <section className="panel">
          <Title tag="决策图 02 · 成本" title="相对基线的成本占比" text="按公开价目折算；不公布绝对金额与 token 量级" />
          <HBars
            rows={byCost.map((m) => ({
              name: m.alias, value: m.costShareOfBaselinePct, color: tone(m.tone), label: share(m.costShareOfBaselinePct),
            }))}
            max={100}
            caption="占基线成本的百分比 · 未计入缓存命中，实际支出更低"
          />
          <p className="chart-caption">
            成本跨两个数量级：最高与最低相差约 {Math.round(100 / cheapest.costShareOfBaselinePct)} 倍；成本只反映单价，不等于质量。
          </p>
        </section>
      </div>

      <section className="panel">
        <Title tag="决策图 03 · 延迟" title="批量精排耗时" text="同一批候选并行处理的观测耗时；不是端到端搜索延迟" />
        <HBars
          rows={models.map((m) => ({
            name: m.alias, value: m.batchWallP50S, color: tone(m.tone), label: `${m.batchWallP50S}s`,
          }))}
          max={Math.ceil(data.batchWallRangeS.max) + 2}
          caption="秒 · 批量 P50"
        />
        <p className="chart-caption">
          批量耗时范围 {data.batchWallRangeS.min}–{data.batchWallRangeS.max}s（现役最低 {incumbent.batchWallP50S}s）。延迟为本次观测，不是生产 SLA。
        </p>
      </section>

      <section className="panel api-section">
        <Title
          tag="决策总表"
          title="单模型与路由放在一起看：质量、价格、延迟"
          text={`基线 = ${base.alias} 直连：干净子集 ${f2(base.judgeClean16)} 分、全集 ${f2(base.judgeAll20)} 分`}
        />
        <h3 className="api-subhead">A · 单模型（含公开价目）</h3>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead>
              <tr>
                <th>模型</th><th>盲评 0–10</th><th>公开价目 ¥/百万 tok（入 / 出）</th>
                <th>成本占基线</th><th>批量 P50</th><th>生产形态</th><th>角色</th>
              </tr>
            </thead>
            <tbody>
              {byQuality.map((m) => (
                <tr key={m.modelId}>
                  <th scope="row"><i className="api-dot" style={{ background: tone(m.tone) }} />{m.alias}</th>
                  <td className="api-strong">{f2(m.judgeScore10)}</td>
                  <td>{m.priceCnyPerMTok.input} / {m.priceCnyPerMTok.output}</td>
                  <td>{share(m.costShareOfBaselinePct)}</td>
                  <td>{m.batchWallP50S}s</td>
                  <td className={m.compatibility.productionShape === 400 ? 'api-bad' : ''}>
                    {m.compatibility.productionShape === 200 ? '可直接跑' : '请求被拒'}
                  </td>
                  <td>{m.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="chart-caption">
          价目为公开信息（{data.priceList.date}，{data.priceList.unit}）。现有结构化输出请求格式不被部分候选支持——
          <strong>任何候选上线前都要先改代码</strong>。
        </p>

        <h3 className="api-subhead">B · 路由策略（同样按成本占比）</h3>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead>
              <tr>
                <th>策略</th><th>是否用 max</th><th>干净子集 {router.cleanSubsetN} 场</th>
                <th>全集 {router.cleanSubsetN + router.truncatedSessions} 场</th><th>成本占基线</th><th>批量 P50</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row"><i className="api-dot" style={{ background: tone('baseline') }} />基线：全部走 {base.alias}</th>
                <td>—</td>
                <td className="api-strong">{f2(base.judgeClean16)}</td>
                <td className="api-strong">{f2(base.judgeAll20)}</td>
                <td>{share(base.costShareOfBaselinePct)}</td>
                <td>{base.wallP50S}s</td>
              </tr>
              {router.strategies.map((s: StrategyRow) => (
                <tr key={s.key}>
                  <th scope="row">
                    {s.policy}
                    {s.key === router.bestNoMaxKey && <b className="api-flag">不用 max 最优</b>}
                  </th>
                  <td>{s.usesMax ? '是' : '否'}</td>
                  <td className={s.judgeClean16 < base.judgeClean16 ? 'api-bad' : ''}>{f2(s.judgeClean16)}</td>
                  <td className={s.judgeAll20 < base.judgeAll20 ? 'api-bad' : ''}>{f2(s.judgeAll20)}</td>
                  <td>{share(s.costShareOfBaselinePct)}</td>
                  <td>{s.wallP50S}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="api-callout api-callout-block">
          <strong>结论</strong>
          <span>{router.verdict}</span>
        </div>

        <div className="two-column api-chart-grid">
          <div className="panel api-subpanel">
            <Title tag="非劣口径" title={`「接近 max」= 差距 ≤ ${ni.margin.toFixed(1)} 分？`} text={ni.note} />
            <div className="api-table-scroll">
              <table className="api-table">
                <thead><tr><th>口径</th><th>不用 max 最优差距</th><th>是否达标</th></tr></thead>
                <tbody>
                  <tr>
                    <th scope="row">干净子集（{router.cleanSubsetN} 场）</th>
                    <td>{f2(ni.gapClean16)} 分</td>
                    <td className={ni.passesClean16 ? '' : 'api-bad'}>{ni.passesClean16 ? '达标' : '未达标'}</td>
                  </tr>
                  <tr>
                    <th scope="row">全集（{router.cleanSubsetN + router.truncatedSessions} 场）</th>
                    <td>{f2(ni.gapAll20)} 分</td>
                    <td className={ni.passesAll20 ? '' : 'api-bad'}>{ni.passesAll20 ? '达标' : '未达标'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="chart-caption">界限由本页显式设定为 {ni.margin.toFixed(1)} 分，便于替换成业务口径后重读上表。</p>
          </div>
          <div className="panel api-subpanel">
            <Title tag="必须知道的两个风险" title="数字之外，还有两件事" />
            <div className="interpretation"><span>评审噪声</span><p>{router.judgeNoiseNote}</p></div>
            <div className="interpretation"><span>规则来源</span><p>{router.postHocNote}</p></div>
            <p className="chart-caption">{router.oracleNote}</p>
          </div>
        </div>

        <div className="interpretation">
          <span>为什么全集数字更好看</span>
          <p>
            {router.truncatedSessions} 场评测的候选名单被生产后处理过滤截断，评审只看到少量候选人（{router.truncatedRange.min}–{router.truncatedRange.max} 人），
            这些场次的分差不可比；剔除后得到干净子集。
          </p>
        </div>
        <p className="chart-caption">leave-one-out 选规则均值 {router.looMean} 分（低于基线）。</p>
      </section>

      <div className="two-column">
        <section className="panel">
          <Title tag="刻度代际差" title="现役合格线不可平移" text={data.calibration.probeNote} />
          <div className="api-table-scroll">
            <table className="api-table">
              <thead><tr><th>模型</th><th>该池上的分数中位数</th></tr></thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.modelId}>
                    <th scope="row"><i className="api-dot" style={{ background: tone(m.tone) }} />{m.alias}</th>
                    <td className={medianMap[m.modelId] === 0.5 ? 'api-bad' : ''}>
                      {medianMap[m.modelId] != null ? medianMap[m.modelId].toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="interpretation">
            <span>换模型前必须做的一件事</span>
            <p>{data.calibration.note}</p>
          </div>
        </section>

        <section className="panel">
          <Title tag="兼容性矩阵" title="请求形态 × 模型" text="同一小样本请求，三种响应格式档位" />
          <div className="api-table-scroll">
            <table className="api-table">
              <thead><tr><th>模型</th><th>生产形态</th><th>结构化输出变体</th><th>json_object</th></tr></thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.modelId}>
                    <th scope="row"><i className="api-dot" style={{ background: tone(m.tone) }} />{m.alias}</th>
                    <td className={m.compatibility.productionShape === 400 ? 'api-bad' : ''}>{m.compatibility.productionShape}</td>
                    <td>{m.compatibility.structuredOutputVariant}</td>
                    <td>{m.compatibility.jsonObject}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="chart-caption">200 = 通过并返回合法 JSON；400 = 请求被拒。现役是唯一能原样跑通的模型。</p>
        </section>
      </div>

      <section className="panel final-note">
        <Title tag="边界与来源" title="这页能说明什么、不能说明什么" text="离线小样本结论，不能外推为线上效果" />
        <div className="api-limits">
          {data.limitations.map((x: string, i: number) => (
            <div key={i}><span>{String(i + 1).padStart(2, '0')}</span><p>{x}</p></div>
          ))}
        </div>
        <div className="interpretation">
          <span>独立复核</span>
          <p>
            {data.provenance.codexReview.date} 由独立代码评审代理复核：{data.provenance.codexReview.scope}；
            复核结果：{data.provenance.codexReview.effect}。
          </p>
        </div>
        <p className="chart-caption">
          数据由内部提取脚本从离线评估工件生成（脚本与原始工件不发布），只保留脱敏聚合数字；{data.provenance.artifacts.join('')}。
          价目来源：{data.priceList.source}（{data.priceList.date}）。
        </p>
      </section>
    </>
  );
}
