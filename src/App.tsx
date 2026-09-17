import { useEffect, useMemo, useState } from 'react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { loadSnapshot } from './data/loaders';
import { checkData, summaryViolations, type Violation } from './data/discipline';

import Overview from './pages/Overview';
import PromptEvolution from './pages/PromptEvolution';
import SystemEvolution from './pages/SystemEvolution';
import ExperimentsData from './pages/ExperimentsData';
import DiagnosticsCases from './pages/DiagnosticsCases';
import SummaryEvidence from './pages/SummaryEvidence';

export default function App() {
  const [violations, setViolations] = useState<Violation[]>([]);

  // 一次性加载 + 校验
  const snapshot = useMemo(() => loadSnapshot(), []);
  useEffect(() => {
    const vs = checkData(snapshot);
    setViolations(vs);
    if (vs.length > 0) {
      // eslint-disable-next-line no-console
      console.warn('[discipline] 校验违规：', vs);
    }
  }, [snapshot]);

  const summary = summaryViolations(violations);

  return (
    <div className="app-shell">
      <header className="top-nav">
        <NavLink to="/" className="brand" end>
          NL2IR 研究展示
          <small>local demo</small>
        </NavLink>
        <nav>
          <NavLink to="/" end>
            总览
          </NavLink>
          <NavLink to="/prompts">Prompt 演进</NavLink>
          <NavLink to="/system">方法演进</NavLink>
          <NavLink to="/experiments">实验与数据</NavLink>
          <NavLink to="/diagnostics">诊断与病例</NavLink>
          <NavLink to="/summary">总结与证据</NavLink>
        </nav>
      </header>

      <main className="main">
        {summary.errors > 0 ? (
          <div className="discipline-banner" role="alert">
            <strong>数据纪律校验失败：</strong>发现 {summary.errors} 条错误
            {summary.warnings > 0 ? `与 ${summary.warnings} 条警告` : ''}。下方各页面仍可查看，但展示数据已被标记。
            <ul>
              {violations.slice(0, 6).map((v, i) => (
                <li key={i}>
                  [{v.level}] {v.message}
                </li>
              ))}
            </ul>
          </div>
        ) : summary.warnings > 0 ? (
          <div className="discipline-banner" style={{ background: '#FEF3C7', borderColor: '#FDE68A', color: '#92400E' }}>
            <strong>数据纪律警告：</strong>发现 {summary.warnings} 条警告（无错误）。详见控制台。
          </div>
        ) : null}

        <Routes>
          <Route path="/" element={<Overview data={snapshot} />} />
          <Route path="/prompts" element={<PromptEvolution data={snapshot} />} />
          <Route path="/system" element={<SystemEvolution data={snapshot} />} />
          <Route path="/experiments" element={<ExperimentsData data={snapshot} />} />
          <Route path="/diagnostics" element={<DiagnosticsCases data={snapshot} />} />
          {/* 旧 /training 重定向到首页（训练内容已合并到本地模型验证主展示） */}
          <Route path="/training" element={<Navigate to="/" replace />} />
          {/* 旧 /timeline 重定向到首页（已按领导汇报 4 部分重组） */}
          <Route path="/timeline" element={<Navigate to="/" replace />} />
          <Route path="/summary" element={<SummaryEvidence data={snapshot} />} />
        </Routes>
      </main>
    </div>
  );
}