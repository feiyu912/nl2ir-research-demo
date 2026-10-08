import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList, ReferenceLine } from 'recharts';
import data from '../../data/rerank_model_selection.json';

/**
 * 独立实验页：生产检索链路的精排（rerank）情况——模型选型（客观面）+ 对现役的成对偏好。
 * 数字全部来自 data/rerank_model_selection.json（由内部提取脚本生成，只含脱敏聚合）。
 * 与 NL2IR 解析评测无关，两者不得混入同一组图。
 */

type ModelRow = (typeof data.models)[number];
type CandidateRow = (typeof data.pairwise.candidates)[number];
type StrategyRow = (typeof data.pairwise.strategies)[number];

const TONE_COLOR: Record<string, string> = {
  baseline: '#335cff',
  candidate: '#15968f',
  value: '#e0a458',
  hold: '#c08ca0',
  incumbent: '#8090aa',
};
const tone = (t: string) => TONE_COLOR[t] ?? '#8090aa';
const share = (v: number) => `${v < 10 ? v.toFixed(1) : Math.round(v)}%`;
const TOL = data.pairwise.orderTolerancePct;

const orderConsistent = (c: CandidateRow) =>
  Math.abs(c.incumbentFirst.winRatePct - c.candidateFirst.winRatePct) <= TOL;

function candidateVerdict(c: CandidateRow): { text: string; bad: boolean } {
  if (!orderConsistent(c)) return { text: '不可用（位置敏感）', bad: true };
  if (c.conservativeWinRatePct >= 50) return { text: '不劣于现役', bad: false };
  return { text: '劣于现役', bad: true };
}

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

function HBars({ rows, max, caption, height = 250, unit = '' }: {
  rows: { name: string; value: number; color: string; label: string }[];
  max: number; caption: string; height?: number; unit?: string;
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
      <p className="chart-caption">{caption}{unit}</p>
    </>
  );
}

/** 每个候选两根条：现役在前 / 候选在前。50% 为"没有差别"的基准线。 */
function PreferenceChart() {
  const rows = data.pairwise.candidates.map((c) => ({
    name: c.alias.split('（')[0],
    first: c.incumbentFirst.winRatePct,
    second: c.candidateFirst.winRatePct,
    consistent: Math.abs(c.incumbentFirst.winRatePct - c.candidateFirst.winRatePct) <= TOL,
  }));
  const asPct = (v: React.ReactNode) => `${Number(v).toFixed(0)}%`;
  return (
    <>
      <div className="research-chart" style={{ height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 10, right: 62, bottom: 8, left: 0 }}
                    barSize={11} barGap={5} barCategoryGap="32%">
            <CartesianGrid stroke="#edf0f6" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`}
                   axisLine={false} tickLine={false} tick={{ fill: '#8792a8', fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={124} axisLine={false} tickLine={false}
                   tick={{ fill: '#42516b', fontSize: 12 }} />
            <ReferenceLine x={50} stroke="#c0392b" strokeDasharray="4 3" />
            <Tooltip cursor={{ fill: '#f5f7fc' }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const r = payload[0].payload;
              return (
                <div className="chart-tip">
                  <strong>{r.name}</strong>
                  <span>现役在前 {r.first}% · 候选在前 {r.second}%</span>
                  <span>{r.consistent ? '两个方向一致' : '两个方向不一致（位置敏感）'}</span>
                </div>
              );
            }} />
            <Bar dataKey="first" fill="#335cff" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              <LabelList dataKey="first" position="right" formatter={asPct} fill="#335cff" fontSize={10} />
            </Bar>
            <Bar dataKey="second" fill="#8b72dc" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              <LabelList dataKey="second" position="right" formatter={asPct} fill="#8b72dc" fontSize={10} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-caption">
        候选方案在两个方向上的胜率（对现役）。红色虚线 = 50%。<strong>两根条都落在同一侧才算结论</strong>；
        分居两侧说明结果由位置决定，不进入结论。Borda 融合 = 两个 Flash 的排名合并。
      </p>
      <div className="hv-legend">
        <span><i style={{ background: '#335cff' }} />现役写在前面</span>
        <span><i style={{ background: '#8b72dc' }} />候选写在前面</span>
        <span><i style={{ background: '#c0392b' }} />50% 无差别线</span>
      </div>
    </>
  );
}

export default function RerankOverview() {
  const models: ModelRow[] = data.models;
  const byIncumbentCost = [...models].sort((a, b) => a.costShareOfIncumbentPct - b.costShareOfIncumbentPct);
  const cheapest = byIncumbentCost[0];
  const fastest = [...models].sort((a, b) => a.batchWallP50S - b.batchWallP50S)[0];
  const incumbent = models.find((m) => m.tone === 'incumbent')!;
  const midTier = models.find((m) => m.modelId === 'qwen3.7-plus')!;
  const ds = models.find((m) => m.modelId === 'deepseek-v4.1-flash')!;
  const pw = data.pairwise;
  const cands = pw.candidates;
  const medianMap = data.calibration.medianScoreByModel as Record<string, number>;

  /** 更便宜、且两个方向都不劣于现役的候选 —— 这才是"值得换"的定义 */
  const switchable = cands
    .filter((c) => orderConsistent(c) && c.conservativeWinRatePct >= 50)
    .map((c) => ({ c, m: models.find((mm) => mm.modelId === c.modelKey) }))
    .filter((x) => x.m && x.m.costShareOfIncumbentPct < 100)
    .sort((a, b) => (a.m!.costShareOfIncumbentPct - b.m!.costShareOfIncumbentPct));
  const bestSwitch = switchable[0];

  return (
    <>
      <Heading
        tag={`独立实验 · ${data.experimentDate} · 生产检索链路`}
        title="精排模型横向对比与路由回测"
        text={`离线冻结候选池上的精排（rerank）选型：成本与兼容性是客观测量；质量用「对现役的成对偏好」衡量——${pw.sessions} 场真实检索、每场两个方向各重复 3 次，只看两个方向一致的结论。与 NL2IR 解析评测无关。`}
      />

      <div className="api-callout">
        <strong>口径边界</strong>
        <span>
          评测在固定规模的冻结候选池上复现生产精排路径（只替换模型）；不调线上流量、不发布查询、候选人、逐题输出或可还原评测集的标识。
          成本口径为{data.track.costCaliber}。
        </span>
      </div>

      <div className="api-insight-grid">
        <article className="api-insight api-insight-primary">
          <span>更便宜且不劣于现役</span>
          <strong>{bestSwitch ? share(bestSwitch.c.conservativeWinRatePct) : '—'}<small> 对现役胜率</small></strong>
          <h3>{bestSwitch?.c.alias ?? '—'}</h3>
          <p>{bestSwitch?.m?.conclusion ?? ''}</p>
        </article>
        <article className="api-insight api-insight-value">
          <span>成本最低</span>
          <strong>{share(cheapest.costShareOfIncumbentPct)}<small> 占现役</small></strong>
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
          <Title tag="决策图 01 · 质量" title="对现役的成对偏好" text="每场只有两个方案在场；同一对调换 A/B 顺序各评 3 次" />
          <PreferenceChart />
        </section>

        <section className="panel">
          <Title tag="决策图 02 · 成本" title="相对现役的成本占比" text="按公开价目折算；不公布绝对金额与 token 量级" />
          <HBars
            rows={byIncumbentCost.map((m) => ({
              name: m.alias, value: Math.min(m.costShareOfIncumbentPct, 100),
              color: tone(m.tone), label: share(m.costShareOfIncumbentPct),
            }))}
            max={100}
            caption="占现役成本的百分比，超出 100% 的按 100% 封顶显示 · 未计入缓存命中，实际支出更低"
          />
          <p className="chart-caption">
            以<strong>现役</strong>为分母，而不是质量天花板：中间档（{share(midTier.costShareOfIncumbentPct)}）与 DeepSeek（{share(ds.costShareOfIncumbentPct)}）
            <strong>看着便宜、实际比现役还贵</strong>。
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
          title="先看客观面，再看质量"
          text={`现役 = ${incumbent.alias}，成本分母。7 个候选的质量都测过（表 B），但差异都不显著——真正区分它们的是成本。`}
        />

        <h3 className="api-subhead">A · 单模型（成本 / 延迟 / 兼容性，均为客观测量）</h3>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead>
              <tr>
                <th>模型</th><th>公开价目 ¥/百万 tok（入 / 出）</th><th>占现役</th><th>占 max</th>
                <th>批量 P50</th><th>生产形态</th><th>角色</th>
              </tr>
            </thead>
            <tbody>
              {byIncumbentCost.map((m) => (
                <tr key={m.modelId}>
                  <th scope="row"><i className="api-dot" style={{ background: tone(m.tone) }} />{m.alias}</th>
                  <td>{m.priceCnyPerMTok.input} / {m.priceCnyPerMTok.output}</td>
                  <td className={m.costShareOfIncumbentPct > 100 ? 'api-bad' : ''}>{share(m.costShareOfIncumbentPct)}</td>
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
          <strong>任何候选上线前都要先改代码</strong>。红色 = 比现役更贵。
        </p>

        <h3 className="api-subhead">B · 对现役的成对偏好（质量，{pw.sessions} 场 × 每场 {pw.callsPerPair} 次调用）</h3>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead>
              <tr>
                <th>候选</th><th>场次（胜 / 负 / 平）</th>
                <th>现役在前 胜率</th><th>候选在前 胜率</th><th>两向一致</th><th>判定</th>
              </tr>
            </thead>
            <tbody>
              {cands.map((c: CandidateRow) => {
                const v = candidateVerdict(c);
                const ok = orderConsistent(c);
                return (
                  <tr key={c.key}>
                    <th scope="row">{c.alias}</th>
                    <td>{c.wins} / {c.losses} / {c.ties}</td>
                    <td>{c.incumbentFirst.candidateWins}–{c.incumbentFirst.incumbentWins}（{c.incumbentFirst.winRatePct}%）</td>
                    <td className={ok ? '' : 'api-bad'}>{c.candidateFirst.candidateWins}–{c.candidateFirst.incumbentWins}（{c.candidateFirst.winRatePct}%）</td>
                    <td className={ok ? '' : 'api-bad'}>{ok ? '一致' : '不一致'}</td>
                    <td className={v.bad ? 'api-bad' : 'api-strong'}>{v.text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="chart-caption">
          「现役在前 / 候选在前」是同一对的两种呈现顺序。<strong>两向相差超过 {TOL} 个百分点即判为位置敏感、结论不可用</strong>
          （表格保留原始数字，不做平滑）。判定按两个方向里对候选最不利的胜率给出。
        </p>

        <h3 className="api-subhead">C · 路由策略（由模型胜负推导，无需额外评审）</h3>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead><tr><th>策略</th><th>是否调用 max</th><th>场次（胜 / 负 / 平）</th><th>对照</th></tr></thead>
            <tbody>
              {pw.strategies.map((s: StrategyRow) => (
                <tr key={s.key}>
                  <th scope="row">
                    {s.policy}
                    {s.key === pw.bestStrategyKey && <b className="api-flag">本表最高</b>}
                  </th>
                  <td>{s.usesMax ? '是' : '否'}</td>
                  <td className={s.wins < s.losses ? 'api-bad' : ''}>{s.wins} / {s.losses} / {s.ties}</td>
                  <td>{s.key === 'flash38Only' ? '即"全部走 3.8 Flash"' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="chart-caption">
          策略每场选了哪个模型，就等于该模型在本场对现役的胜负——所以不需要再评一遍。
          <strong>没有任何分流策略优于「全部走 Qwen 3.8 Flash」</strong>。
        </p>

        <div className="api-callout api-callout-block">
          <strong>结论</strong>
          <span>{pw.verdict}</span>
        </div>

        <div className="two-column api-chart-grid">
          <div className="panel api-subpanel">
            <Title tag="方法学 · 为什么这次的数字可以用" title="评审自己先过了定标对照" text={pw.rootCause} />
            <div className="api-table-scroll">
              <table className="api-table">
                <thead><tr><th>对照</th><th>修复前</th><th>修复后</th></tr></thead>
                <tbody>
                  <tr>
                    <th scope="row">两侧完全相同（应全判平）</th>
                    <td>{pw.validation.beforeFix?.identicalPairAllTie}</td>
                    <td className="api-strong">{pw.validation.afterFix?.identicalPairAllTie}</td>
                  </tr>
                  <tr>
                    <th scope="row">故意排坏（应被认出）</th>
                    <td>{pw.validation.beforeFix?.degradedOrderDetected}</td>
                    <td className="api-strong">{pw.validation.afterFix?.degradedOrderDetected}</td>
                  </tr>
                  <tr>
                    <th scope="row">反而认为坏排序更好</th>
                    <td className="api-bad">{pw.validation.beforeFix?.degradedOrderInverted}</td>
                    <td className="api-strong">{pw.validation.afterFix?.degradedOrderInverted}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="chart-caption">
              「故意排坏」= 把同一份排序按置信度升序重排（最不相关的排最前）。修复前评审看不出来、还会 2/16 场反着判；
              修复后不再出现反向误判。定标不过关的数字不写进结论。
            </p>
          </div>
          <div className="panel api-subpanel">
            <Title tag="必须知道的三个限制" title="数字之外" />
            <div className="interpretation">
              <span>只能说「不劣于」</span>
              <p>全部差异都不显著（{cands.map((c) => `${c.alias.split('（')[0]} p=${c.signP}`).join('、')}），16 场会话的样本量支撑不了「更好」。</p>
            </div>
            <div className="interpretation">
              <span>单一评审</span>
              <p>{pw.caliber}</p>
            </div>
            <div className="interpretation">
              <span>截断场次被排除</span>
              <p>有评测场的候选名单被生产后处理过滤截断，评审只看到极少数候选人，这些场次不参与质量对比。</p>
            </div>
          </div>
        </div>
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