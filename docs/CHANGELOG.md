# 变更日志（CHANGELOG）

> 数据提取脚本版本与母版变更。每次运行 `npm run extract` 后追加一行。

## v0.6.0 · 托管 API 三模型基线（独立实验）

### 动机
- 论文与实验需要回答"托管 API 用哪个模型"，此前只有 4B/9B LoRA 训练实验的展示。
- 该实验与 LoRA 实验**不是同一实验**：数据、指标、口径、结论都不同。

### 主要变更
- **新增同级导航页面 `/models`「三模型横向对比」**（入口在「实验依据」右侧），
  完整展示分片成绩、hard-F1、dropped/hallucinated、P50/P95、两套成本口径与计算口径、
  两两比较与 cluster CI、McNemar p 值、主要错误类型、当前选型结论，
  以及运行事故与有效性限制。
- 「当前模型验证」页**保持原有设计与内容不变**，仅在其顶部新增**一张紧凑摘要卡**
  （combined where / P50 / 标准化 ¥万次 / 结论）并链接到 `/models`；
  未改动该页原有组件结构、字号、颜色与间距。
- 首页「当前能力参考」之后保留三模型摘要卡片，并提供「查看完整对比」入口。
- 三模型摘要**统一使用同一尺度**（同一 906 条的 `main_chain_where` 正确率；
  成本为同一 token 工作量的标准化价格），**不使用分别归一化的进度条**。
- 两套成本口径并列展示，并明确 `observed_run_cost` **不是价格指数**。
- Arm A 属训练消融实验，**不在本页**；训练完成后再单独建立页面或模块。

### 新增数据
- `data/hosted_api_baselines.json`：托管 API 三模型基线（schema `hosted-api-baselines/v1`）
- `scripts/extract_hosted_api_baselines.py`：只读提取（不调用模型/API，不重新评分）
- `scripts/validate_data.py`：新增 `check_hosted_api_baselines` 严格校验

### 纪律
- 数字全部来自 JSON，不在 React 组件中硬编码；
- role_tenure 审计未冻结：只在 limitations 写"匹配策略仍在验证"，不写入实现结论。

## v0.5.0 · Prompt 与解析方案 + 历史实验扩充

### 主要变更
- 「方法演进」→「Prompt 与解析方案」4 部分：最初长 prompt / 首次压缩 / 后续关键规则优化 / 最终 v21 参考方案
- 每段含：方案描述、特点、设计要点、实验（含条件/数据/状态）、SHA、纪律
- 完整 prompt 原文可展开查看（构建期 vite glob 注入）
- 「实验与数据」加入「按问题的历史实验分组」视图：8 组（接手 8B 基线、资源适配、prompt 压缩对照、规则优化、泛化差距、难题诊断、审计 repair/gate、最终 v21）
- 每条实验含：模型、prompt、数据/Gold版本、指标（含分子分母）、状态、来源、备注
- 不同数据集/Gold/口径不连成一条曲线
- 历史 vs 正式纪律清单扩充

### 新增数据
- `data/prompt_solutions.json`：4 段 prompt 与解析方案
- `data/historical_experiments.json`：按问题分组的 8 组历史实验

---

## v0.4.0 · 领导汇报改版：4 部分 + 技术证据折叠

### 改版动机
- 不使用时间线、日期阶段导航或版本流水账
- 主页面面向领导汇报，少技术术语，突出价值、关键发现和结论
- 按研究问题归集（而非按日期）

### 主要变更
- 删除 `/timeline` 路由；旧链接重定向到首页
- 删除 `ResearchTimeline.tsx` 与 `Stage6LocalValidation.tsx`
- Overview 重写为 4 部分领导汇报：
  1. **为什么做**：目标 + 本地小模型价值 + 收益证据声明（无测量则不写成已验证）
  2. **解决了哪些关键问题**：按研究问题归集（本地资源限制 / 规则执行不稳定 / 旧集高分不能保证泛化 / 数据与评测存在歧义），每类含问题—采取的措施—证据—结论
  3. **现在达到什么水平**：强 API / 本地学生分组对比；纪律声明；已知能力与差距
  4. **下一步建议**：原则 + 优先补的证据 + 进入业务试用的条件
- 保留少量真实病例（≤4 例）解释复杂查询为何难
- 技术证据折叠区：训练配置、Prompt 演进概览、600/222/440 集合、证据来源
- 顶部导航精简：6 个 NavLink

### 关键纪律
- 收益不能默认是 prompt 单因素；成本/隐私/时延收益无实际测量则不写为已验证
- 「示例过多导致过拟合」等未证解释不写成事实
- 不默认更大模型或反复重训
- 下一阶段不编造计划；只列原则 + 待补证据 + 业务试用条件

### 数据新增
- `data/research_questions.json`：4 类研究问题 + 当前能力分组 + 下一步建议

---

## v0.3.0 · 合并「学生训练」到主线第 6 阶段

### 改版动机
- 训练细节只是证据，不需要独立占一个主导航页面
- 统一改称「本地模型验证」并合并到研究主线第 6 阶段

### 主要变更
- 第 6 阶段标题：「v21 与当前成果」→「v21 与本地模型验证」
- 第 6 阶段新增 `mainDisplay`：4B/9B/API × 三个数据集的核心对比
- 第 6 阶段新增 `conclusionsAccurate`：9B 检查与训练结论准确表述
- 新增 `Stage6LocalValidation` 组件：主展示 + 训练详情折叠
- 「训练与检查详情」折叠：数据构成、训练配置、loss、checkpoint 对照、9B 检查、证据来源
- 删除 `/training` 路由；旧链接自动重定向到 `/timeline`
- 删除 `src/pages/StudentTraining.tsx`
- 顶部导航移除「学生训练」入口

### 9B 检查结论（准确表述）
- 未发现误开 thinking、混用模型、训练中断或权重非有限值
- checkpoint-200 与最终模型盲测 Where 均为 198/240，不支持最后 91 步整体退化
- 不能排除更早过拟合；checkpoint-200 与最终持平只说明「最后 91 步未退化」
- 未做训练期间验证：eval_strategy=NO、load_best_model_at_end=false
- 不能仅凭训练 loss 低判断泛化良好或确定差距来源
- 「微调有效」引用有底座对照的历史实验；当前 v21 未完成未微调底座对照

### 数据复用
- 主线、实验对比、证据区引用同一份 runs.json / metrics.json
- 数字不再重复维护

---

## v0.2.0 · 改版：6 阶段研究主线为核心

### 改版动机
- 不再以最终盲测 4 个数字统领首页
- 研究主线作为汇报核心入口，按因果顺序 6 阶段叙述
- 新增 Prompt 演进展示（Original → compact → v21）

### 6 阶段（按因果顺序）
1. **接手与资源适配**：Qwen3 8B → RTX 5070 Ti 16GB → Qwen3.5 4B/9B
2. **长 prompt 与首次压缩**：Original 336 行 / 24193 B；compact-v3 81 行 / 10493 B；token 门禁与 SHA-256
3. **共享 prompt 迭代与旧集提升**：v12→v19 非单调；v19 API 旧集 355/370；v19 4B 旧集 323/370；4B/9B 配对评测
4. **未见 blind 暴露差距**：首次 blind-v2 (248)：API 213/248 vs 4B 162/248；API 降约 10pp / 4B 降约 20pp
5. **C-hard 与严格审计**：C-hard240 早期 API 39.17% / 4B 11.25%；Gold/contract/scope/routing 严格审计
6. **v21 与当前成果**：冻结盲测 blind-v6 229/240 → 234/240；4B 211/240、9B 197/240；checkpoint-200 vs 最终持平

### 新增视图
- `/timeline` 研究主线（6 阶段叙事）
- `/prompts` Prompt 演进（5 版本对照 + SHA-256 + token 免责）

### 关键纪律保留
- 指标渲染统一为 `correct/total (xx.xx%)`，从不加和
- 600/222/440 重叠集合 `OverlapReportCard` 始终可见
- 训练 loss 仅 3 个真实点（4B/9B × 3 epoch）
- 历史 vs 正式分开（v19 旧集 355/370 与最终盲测分开展示）
- blind v2 / C-hard 早期数字与最终 blind-v6 数字明确分组
- Prompt 演进中 token 统计注明 tokenizer / 模板 / 统计范围
- compact-v3 收益不默认是 prompt 单因素

### 数据新增
- `data/research_timeline.json`：6 阶段完整叙事
- `data/prompt_evolution.json`：5 版本 prompt 对照（含 SHA-256）

---

## v0.1.0 · 初次实现

### 范围
- NL2IR 研究主线
- 6 个视图、8 类 JSON 数据、5 个提取脚本、1 个校验脚本
- 3 个 DOCX 母版、2 个 paper_ir_v1 目录、6 组学生评测、1 个学生六评估审计目录、19 个 tar.gz 清单索引

### 数据集
- 8 条 Run：2 API（one_pass / assertion_v7）+ 6 student（4B/9B × old366/C300/blind-v6）
- 80 个 metric 行：10 指标 × 8 Run
- 685 条病例：660 取样 + 25 审计取样
- 8 阶段事件
- 6 个真实 loss 点（4B/9B × 3 epoch）
- 600 / 222 / 440 + intersection=62 重叠报告
- 5 类主归因定义
- 19 个历史 bundle 清单

### 关键纪律实现
- 指标渲染统一为 `correct/total (xx.xx%)`，从不加和
- 600/222/440 重叠集合 `OverlapReportCard` 始终可见
- 训练 loss 仅 3 个真实点 + "无原始逐 step loss" 提示
- 历史 vs 正式口径分开（356/366、271/300 标为开发/历史口径，不混入当前排名）
- 每个 Run 有 `kind` + `compatibility[]`，前端 discipline 在 mount 时校验

### 不修改源研究文件
- 仅读 DOCX、JSON、tar.gz 流
- 不下载模型、不 SSH、不调用 API
- 服务器路径（`[服务器来源路径未公开]`）仅引用，标 `server-not-local`

### 已知缺项
- 9B 重复 blind、checkpoint-200 blind 原始数据不在本机（DOCX 聚合引用）
- trainer_state.json 逐 step loss 不在本机（仅 3 轮平均）
- 9B trainer_log.jsonl 完整 NaN/Inf 日志（仅 DOCX 聚合声明）
