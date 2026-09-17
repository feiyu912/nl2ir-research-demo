# 研究展示重建说明

当前入口为 `src/ResearchDashboard.tsx`，使用 `data/presentation.json`；旧页面与旧JSON保留，但不再作为展示数据来源。原研究仓库文件未改动。

运行 `node scripts/build_presentation.mjs` 重新提取当前8组原始指标、真实prompt、Gold与预测病例及失败集合。脚本检查分子分母和主要锚点，缺失源文件会报错，不补造数值。

历史10组图表按研究问题组织，来源为原报告及母版对应记录，保留原指标名称与限制。前人8B交接与当前实验分开；早期compact-v3并非v19；v12–v16实际调用强API，不是4B。未把各阶段连成可比的单一准确率曲线。

修正：old366和C300不在当前最终训练中；Where与Semantic交集82、并集580，不能由全部600失败记录推导交集62；Original严重截断不等于模型无法训练；v19 355/370是95.95%，约97%是研究者确认的进一步放宽口径，明细待补。

最新9B重复/ckpt200聚合成绩来自母版追加记录，原始服务器文件未导入。没有训练期间验证loss，不能排除更早过拟合。C-hard训练内正式诊断、v21底座对照、Windows部分配置待补。

使用 `npm run dev`（127.0.0.1:5173）预览；`npm run build` 构建。旧 /system 重定向Prompt，旧 /training、/summary、/timeline 重定向总览。没有数据库、在线模型、训练或API依赖。
