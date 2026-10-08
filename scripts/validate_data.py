"""数据纪律校验脚本（前端 discipline.ts 等价）。

检查 8 类 JSON 是否满足不变量。

Usage:
    python3 scripts/validate_data.py --data data/ [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUX = DATA / "aux"

DATE_MIN = "1970-01-01"
DATE_MAX = "2999-12-31"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def exit_code(self, strict: bool) -> int:
        if self.errors:
            return 1
        if strict and self.warnings:
            return 2
        return 0


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def check_runs(report: Report, runs: list[dict]) -> None:
    seen: set[str] = set()
    for r in runs:
        rid = r.get("runId")
        if not rid:
            report.error("Run 缺 runId")
            continue
        if rid in seen:
            report.error(f"runId 重复: {rid}")
        seen.add(rid)

        date = r.get("date", "")
        if date and (date < DATE_MIN or date > DATE_MAX):
            report.warn(f"日期越界: {rid} {date}")

        if r.get("kind") == "in-train-diagnostic" and not r.get("notes"):
            report.warn(f"in-train-diagnostic 缺 notes: {rid}")

        compat = r.get("compatibility", [])
        if "comparable-with-blind-v6" in compat and "historical-only" in compat:
            report.error(f"compat 互斥: {rid}")


def check_metrics(report: Report, metrics: list[dict]) -> None:
    for m in metrics:
        correct = m.get("correct")
        total = m.get("total")
        acc = m.get("accuracy")
        if correct is None or total is None:
            report.error(f"metric 缺 correct/total: {m.get('runId')} {m.get('metric')}")
            continue
        if total == 0:
            continue
        if correct > total:
            report.error(f"correct > total: {m.get('runId')} {m.get('metric')} {correct}/{total}")
        expected = round(correct / total, 4)
        if abs(acc - expected) > 0.005:
            # 自动修复
            m["accuracy"] = expected
            report.warn(
                f"accuracy 不一致，已自动修复: {m.get('runId')} {m.get('metric')} {acc} -> {expected}"
            )
        ci = m.get("ci95")
        if ci and isinstance(ci, list) and len(ci) == 2:
            lo, hi = ci
            if lo < 0 or hi > 1 or lo > hi:
                report.warn(f"ci95 越界: {m.get('runId')} {m.get('metric')} {ci}")


def check_overlap(report: Report, overlap: dict) -> None:
    total = overlap.get("totalFailedRows", 0)
    where = overlap.get("whereFailures", 0)
    sem = overlap.get("semanticFailures", 0)
    intersection = overlap.get("intersection", 0)
    expected = max(where + sem - total, 0)
    if intersection != expected:
        report.error(
            f"overlap 不自洽: {where}+{sem}-{total}={expected} vs intersection={intersection}"
        )
    if total != 600:
        report.warn(f"totalFailedRows ≠ 600: {total}")


def check_training(report: Report, training: dict) -> None:
    for p in training.get("points", []):
        loss = p.get("loss")
        if loss is None or not isinstance(loss, (int, float)):
            report.error(f"training loss 类型错误: {p}")
            continue
        if loss != loss or loss == float("inf") or loss == float("-inf"):
            report.error(f"training loss 非有限: {p}")
        if loss < 0:
            report.error(f"training loss < 0: {p}")


def check_cases(report: Report, cases: list[dict]) -> None:
    valid_attribution = {"M", "R", "P", "G", "F"}
    for c in cases:
        attr = c.get("attribution")
        if attr is not None and attr not in valid_attribution:
            report.warn(f"case 归因不在 5 类内: {c.get('caseId')} {attr}")


def check_conclusions(report: Report, conclusions: list[dict]) -> None:
    valid_category = {"fact", "interpretation", "hypothesis", "plan"}
    for c in conclusions:
        if c.get("category") not in valid_category:
            report.warn(f"conclusion category 异常: {c}")
        if not c.get("source"):
            report.error(f"conclusion 缺 source: {c.get('text')[:50]}")


def check_hosted_api_baselines(report: Report, payload: dict) -> None:
    """托管 API 三模型基线（hosted_api_baselines.json）的不变量。

    这是独立的 API 模型选型实验，**不**与 4B/9B LoRA 图表混用。
    """
    if payload.get("schema") != "hosted-api-baselines/v1":
        report.error(f"hosted_api_baselines schema 异常: {payload.get('schema')}")
        return

    models = payload.get("models") or []
    by_id = {m.get("modelId"): m for m in models}

    # 三个冻结模型必须存在；允许追加带 provenance 的快照模型（2026-10-08 起）。
    frozen_ids = ["qwen3.7-max", "qwen3.8-flash", "deepseek-v4.1-flash"]
    snapshot_ids = ["qwen3.8-max-0902", "qwen3.7-plus", "qwen3.7-flash"]
    missing = [x for x in frozen_ids if x not in by_id]
    if missing:
        report.error(f"hosted_api_baselines 缺冻结模型: {missing}")
    unknown = [x for x in by_id if x not in frozen_ids + snapshot_ids]
    if unknown:
        report.error(f"hosted_api_baselines 出现未登记的模型 ID: {sorted(unknown)}")

    if payload.get("primaryMetric") != "main_chain_where":
        report.error(f"hosted_api_baselines primary 指标不符: {payload.get('primaryMetric')}")

    # 906 = 366 + 300 + 240
    if payload.get("n") != 906:
        report.error(f"hosted_api_baselines n != 906: {payload.get('n')}")
    ds = payload.get("datasets") or {}
    parts = [
        (ds.get("old366") or {}).get("n"),
        (ds.get("c300") or {}).get("n"),
        (ds.get("blindV6") or {}).get("n"),
    ]
    if parts != [366, 300, 240] or sum(x or 0 for x in parts) != 906:
        report.error(f"hosted_api_baselines 切分不符: {parts} (应 366+300+240=906)")

    # stress96 是 blind-v6 子集，不重复计入 combined
    split = (ds.get("blindV6") or {}).get("split") or {}
    if split.get("stress96") != 96 or split.get("realistic144") != 144:
        report.error(f"hosted_api_baselines blind 子集划分不符: {split}")
    if (split.get("stress96") or 0) + (split.get("realistic144") or 0) != (ds.get("blindV6") or {}).get("n"):
        report.error("hosted_api_baselines stress96 + realistic144 != blind-v6")

    expected_where = {"qwen3.7-max": 94.26, "qwen3.8-flash": 89.62, "deepseek-v4.1-flash": 86.20,
                     "qwen3.8-max-0902": 91.39, "qwen3.7-plus": 85.54, "qwen3.7-flash": 68.32}
    for mid, want in expected_where.items():
        m = by_id.get(mid)
        if not m:
            continue
        if abs(m.get("combinedWhere", -1) - want) > 0.005:
            report.error(f"hosted_api_baselines combined where 不符: {mid} {m.get('combinedWhere')} != {want}")
        # 切分不重复计入：combined 必须由三切片加权得到
        sl = m.get("slices") or {}
        num = sum((sl.get(k) or {}).get("where", 0) * (sl.get(k) or {}).get("n", 0)
                  for k in ("old366", "c300", "blindV6"))
        den = sum((sl.get(k) or {}).get("n", 0) for k in ("old366", "c300", "blindV6"))
        if den and abs(num / den - m["combinedWhere"]) > 0.02:
            report.error(f"hosted_api_baselines combined 与三切片不一致: {mid}")
        slice_correct = 0
        for key in ("old366", "c300", "blindV6"):
            part = sl.get(key) or {}
            correct, n = part.get("whereCorrect"), part.get("n")
            if not isinstance(correct, int) or not isinstance(n, int) or not 0 <= correct <= n:
                report.error(f"hosted_api_baselines {mid}.{key} 缺有效 whereCorrect/n")
                continue
            slice_correct += correct
            if abs(round(correct / n * 100, 2) - part.get("where", -1)) > 0.005:
                report.error(f"hosted_api_baselines {mid}.{key} where 与正确数不符")
        if slice_correct != m.get("combinedWhereCorrect"):
            report.error(f"hosted_api_baselines {mid} 分片正确数与总数不符")
        stress = sl.get("stress96") or {}
        if stress.get("n") != 96:
            report.error(f"hosted_api_baselines stress96 n 不符: {mid}")

    def tiers(mid: str, caliber: str) -> dict:
        m = by_id.get(mid) or {}
        return {t.get("tier"): t.get("cnyPer10k") for t in ((m.get("cost") or {}).get(caliber) or {}).get("tiers", [])}

    # 标准化每万次成本
    if tiers("qwen3.7-max", "standardized").get("standard") != 201.60:
        report.error("hosted_api_baselines 标准化成本不符: qwen3.7-max")
    if tiers("qwen3.8-flash", "standardized").get("standard") != 12.60:
        report.error("hosted_api_baselines 标准化成本不符: qwen3.8-flash")
    ds_std = tiers("deepseek-v4.1-flash", "standardized")
    if ds_std.get("idle") != 16.40 or ds_std.get("busy") != 32.80:
        report.error(f"hosted_api_baselines DeepSeek 标准化双档位不符: {ds_std}")

    # observed run cost
    if tiers("qwen3.7-max", "observedRun").get("standard") != 242.83:
        report.error("hosted_api_baselines 实测账单不符: qwen3.7-max")
    if tiers("qwen3.8-flash", "observedRun").get("standard") != 16.51:
        report.error("hosted_api_baselines 实测账单不符: qwen3.8-flash")
    ds_obs = tiers("deepseek-v4.1-flash", "observedRun")
    if ds_obs.get("idle") != 9.67 or ds_obs.get("busy") != 19.34:
        report.error(f"hosted_api_baselines DeepSeek 实测双档位不符: {ds_obs}")

    # qwen3.8 标准化成本必须低于 DeepSeek 闲时
    q38_std = tiers("qwen3.8-flash", "standardized").get("standard")
    if q38_std is None or ds_std.get("idle") is None or not q38_std < ds_std["idle"]:
        report.error(f"hosted_api_baselines qwen3.8 标准化成本未低于 DeepSeek 闲时: {q38_std} vs {ds_std.get('idle')}")

    # observed cost 不得命名为 price index：
    # 允许且仅允许 "not a price index" 这一否定式声明，其余出现一律视为违规命名。
    blob = json.dumps(payload, ensure_ascii=False)
    lowered = blob.lower()
    if "price_index" in lowered:
        report.error("hosted_api_baselines 出现被禁止的命名: price_index")
    # 中文：仅允许「不是价格指数」这一否定式
    if blob.count("价格指数") != blob.count("不是价格指数"):
        report.error("hosted_api_baselines 把 observed_run_cost 命名为价格指数")
    # 英文：允许且仅允许 "not a price index" 否定式
    allowed_negation = lowered.count("not a price index")
    if lowered.count("price index") != allowed_negation:
        report.error("hosted_api_baselines 把 observed_run_cost 命名为 price index")
    if allowed_negation < 1 or blob.count("不是价格指数") < 1:
        report.error("hosted_api_baselines observed_run_cost 未声明 not a price index / 不是价格指数")

    # 两套口径必须同时存在且不同
    for m in models:
        cost = m.get("cost") or {}
        if m.get("cost") is None:
            # 快照模型允许未取价目，但必须显式声明原因（缺数据 ≠ 0）
            if not (m.get("costUnavailableReason") or "").strip():
                report.error(f"hosted_api_baselines 成本缺失但未声明原因: {m.get('modelId')}")
            if not (m.get("provenance") or {}).get("runDate"):
                report.error(f"hosted_api_baselines 快照模型缺 provenance.runDate: {m.get('modelId')}")
            continue
        if not (cost.get("standardized") or {}).get("tiers"):
            report.error(f"hosted_api_baselines 缺 standardized 口径: {m.get('modelId')}")
        if not (cost.get("observedRun") or {}).get("tiers"):
            report.error(f"hosted_api_baselines 缺 observedRun 口径: {m.get('modelId')}")

    # 必须声明的结论
    concl = payload.get("conclusions") or {}
    if concl.get("qwen37DropVsQwen38Pp") != 4.64:
        report.error(f"hosted_api_baselines qwen3.8 相对 qwen3.7 下降应为 4.64pp: {concl.get('qwen37DropVsQwen38Pp')}")
    if concl.get("qwen37DropVsDeepseekPp") != 8.06:
        report.error(f"hosted_api_baselines DeepSeek 相对 qwen3.7 下降应为 8.06pp: {concl.get('qwen37DropVsDeepseekPp')}")
    if concl.get("qwen38StandardizedShareOfQwen37Pct") != 6.25:
        report.error(f"hosted_api_baselines qwen3.8 标准化占比应为 6.25%: {concl.get('qwen38StandardizedShareOfQwen37Pct')}")
    if concl.get("qwen38StandardizedReductionPct") != 93.75:
        report.error(f"hosted_api_baselines qwen3.8 标准化降幅应为 93.75%: {concl.get('qwen38StandardizedReductionPct')}")
    if concl.get("qwen38CheaperThanDeepseekIdlePct") != 23.2:
        report.error(f"hosted_api_baselines qwen3.8 较 DeepSeek 闲时便宜应为 23.2%: {concl.get('qwen38CheaperThanDeepseekIdlePct')}")

    # 配对统计：聚类区间跨 0 的方向不得宣称显著
    for pw in payload.get("pairwise") or []:
        lo, hi = (pw.get("ciCluster") or [0, 0])[:2]
        if (lo < 0 < hi) != bool(pw.get("clusterCrossesZero")):
            report.error(f"hosted_api_baselines clusterCrossesZero 与区间不一致: {pw.get('key')}")

    # 来源与哈希必须齐全
    for f in ("THREE_MODEL_RESULTS.md", "three_model_table.json", "three_model_pairwise.json",
              "cost_model.json", "manifest.json", "PUBLICATION_SUMMARY.md"):
        rec = (payload.get("sourceFiles") or {}).get(f) or {}
        if len(rec.get("sha256") or "") != 64:
            report.error(f"hosted_api_baselines 来源文件缺 SHA256: {f}")

    # ---- 判定标准（sealed blind v6）与 router 块 ----
    std = payload.get("judgmentStandard") or {}
    if std.get("name") != "sealed blind v6" or std.get("n") != 240 or std.get("metric") != "main_chain_where":
        report.error(f"hosted_api_baselines 判定标准不符: {std}")
    blind = payload.get("blindModels") or []
    if len(blind) != len(models):
        report.error(f"hosted_api_baselines blindModels 与 models 数量不一致: {len(blind)} vs {len(models)}")
    if {b.get("modelId") for b in blind} != set(by_id):
        report.error("hosted_api_baselines blindModels 模型集合与 models 不一致")
    for b in blind:
        mid = b.get("modelId")
        if not (0 <= b.get("blindWhereCorrect", -1) <= b.get("n", 0)):
            report.error(f"hosted_api_baselines blind 正确数非法: {mid}")
        if abs(round(b.get("blindWhereCorrect", 0) / max(1, b.get("n", 1)) * 100, 2) - b.get("blindWhere", -1)) > 0.005:
            report.error(f"hosted_api_baselines blind 百分比与正确数不符: {mid}")
        ci = b.get("clusterCi95Pp") or [0, 0]
        if (ci[0] < 0 < ci[1]) != bool(b.get("clusterCrossesZero")):
            report.error(f"hosted_api_baselines blind clusterCrossesZero 与区间不一致: {mid}")
        if mid != "qwen3.7-max" and b.get("mcnemarP", 1) >= 0.05 and not b.get("clusterCrossesZero"):
            report.error(f"hosted_api_baselines blind 显著性标注自相矛盾: {mid}")
    routers = payload.get("routers") or []
    if not routers:
        report.error("hosted_api_baselines 缺 routers 块")
    max_cost = (payload.get("maxBaseline") or {}).get("cnyPer10kStandardized")
    for r in routers:
        tiers = r.get("tiers") or []
        if not tiers or any(t not in {"max", "q38", "ds", "0902", "plus", "q37f"} for t in tiers):
            report.error(f"hosted_api_baselines router 层级非法: {r.get('policy')}")
        if max_cost and abs(r.get("cnyPer10kStandardized", 0) / max_cost - r.get("shareOfMaxCost", -1)) > 0.01:
            report.error(f"hosted_api_baselines router 成本占比不自洽: {r.get('policy')}")
        if not 0 <= r.get("acceptancePrecision", -1) <= 1 or not 0 <= r.get("escalationRate", -1) <= 1:
            report.error(f"hosted_api_baselines router 比率越界: {r.get('policy')}")

    # ---- 完全不用 max 的策略块 ----
    nomax = payload.get("routersNoMax") or {}
    strats = nomax.get("strategies") or []
    if not strats:
        report.error("hosted_api_baselines 缺 routersNoMax.strategies")
    allowed_nomax = {"q38", "ds", "0902", "plus", "q37f"}
    for r in strats:
        tiers = r.get("tiers") or []
        if not tiers or any(t not in allowed_nomax for t in tiers) or r.get("escalationTarget") in {None, "max"} and r.get("escalationTarget") is not None:
            report.error(f"hosted_api_baselines 无 max 策略层级非法: {r.get('policy')}")
        if max_cost and abs(r.get("cnyPer10kStandardized", 0) / max_cost - r.get("shareOfMaxCost", -1)) > 0.01:
            report.error(f"hosted_api_baselines 无 max 策略成本占比不自洽: {r.get('policy')}")
        ci = r.get("clusterCi95Pp") or [0, 0]
        if (ci[0] < 0 < ci[1]) != bool(r.get("clusterCrossesZero")):
            report.error(f"hosted_api_baselines 无 max 策略 clusterCrossesZero 不一致: {r.get('policy')}")
    best = max((r.get("blindWhere", 0) for r in strats), default=0)
    if nomax.get("oracleNonMax", 0) < best:
        report.error("hosted_api_baselines 无 max oracle 低于最佳可部署策略（不可能是上界）")

    # role_tenure 审计未冻结：不得写入实现结论
    for m in models:
        text = f"{m.get('role','')}{m.get('conclusion','')}"
        if "role_tenure" in text or "任职" in text:
            report.error(f"hosted_api_baselines 模型结论不得包含 role_tenure 实现结论: {m.get('modelId')}")
    if not any("role_tenure" in x and "仍在验证" in x for x in (payload.get("limitations") or [])):
        report.error("hosted_api_baselines limitations 缺 role_tenure 待验证声明")


def check_api_stability(report: Report, payload: dict) -> None:
    """只允许发布稳定性实验的聚合计数。"""
    if payload.get("schema") != "api-stability-public/v1":
        report.error("api_stability: schema 不符")
    n, repeats = payload.get("sampleItems"), payload.get("repeats")
    if (n, repeats, payload.get("totalCalls"), payload.get("completedCalls"), payload.get("failedRequests")) != (50, 3, 600, 600, 0):
        report.error("api_stability: 样本/重复/请求数不符")
    if payload.get("metric") != "main_chain_where" or not payload.get("intervalMethod", "").startswith("Wilson 95%"):
        report.error("api_stability: 指标或区间口径不符")
    models = payload.get("models") or []
    expected = {"qwen3.7-max": 5, "qwen3.8-max": 3, "qwen3.8-flash": 11, "deepseek-v4.1-flash": 9}
    if {m.get("modelId") for m in models} != set(expected) or len(models) != 4:
        report.error("api_stability: 模型集合不符")
    for model in models:
        mid = model.get("modelId")
        if model.get("flipCount") != expected.get(mid):
            report.error(f"api_stability: {mid} 翻转数不符")
        ci = model.get("flipWilson95Pct") or []
        if len(ci) != 2 or not ci[0] <= 100 * model["flipCount"] / n <= ci[1]:
            report.error(f"api_stability: {mid} Wilson 区间不含点估计")
        counts = model.get("whereCorrectPerRepeat") or []
        if len(counts) != repeats or any(not isinstance(c, int) or not 0 <= c <= n for c in counts):
            report.error(f"api_stability: {mid} 三次正确数无效")
    pairs = payload.get("flipPairs") or {}
    if (pairs.get("total"), pairs.get("leafLevelDifference"), pairs.get("polarityEncodingDifference")) != (28, 24, 4):
        report.error("api_stability: 翻转归因计数不符")
    for digest in (payload.get("sourceSha256") or {}).values():
        if len(digest) != 64:
            report.error("api_stability: 来源哈希无效")
    forbidden = ("query", "gold", "prediction", "raw", "responses", "items")
    if any(key in (payload.keys() | set().union(*(m.keys() for m in models))) for key in forbidden):
        report.error("api_stability: 聚合数据含逐题字段")


HUMAN_VALIDATION_N = 222

# 内部标识与评测资产：出现在公开发布数据里即为泄露。
HUMAN_VALIDATION_FORBIDDEN = (
    "source_key", "source_sample_id", "nl2ir_v21", "dev_old366", "dev_c300",
    "blind_v6_240", "/dat/", "adapter", "checkpoint-",
)


def check_human_validation(report: Report, hv: dict) -> None:
    """人工盲复核聚合结果的数字关系与脱敏检查。"""
    n = hv.get("population", {}).get("n")
    if n != HUMAN_VALIDATION_N:
        report.error(f"human_validation: population.n={n} != {HUMAN_VALIDATION_N}")

    head = hv.get("headline", {})
    if head.get("positive", 0) + head.get("negative", 0) != HUMAN_VALIDATION_N:
        report.error("human_validation: human positive + negative != 222")
    if round(head.get("positive", 0) / HUMAN_VALIDATION_N * 100, 2) != head.get("rate"):
        report.error("human_validation: human rate 与 177/222 不一致")

    agent = hv.get("agent", {})
    if agent.get("positive", 0) + agent.get("negative", 0) != HUMAN_VALIDATION_N:
        report.error("human_validation: agent positive + negative != 222")

    cm = hv.get("confusion", {})
    cells = [cm.get(k, 0) for k in
             ("humanYesAgentYes", "humanYesAgentNo", "humanNoAgentYes", "humanNoAgentNo")]
    if sum(cells) != HUMAN_VALIDATION_N:
        report.error(f"human_validation: 混淆矩阵合计 {sum(cells)} != 222")
    if cells[0] != cm.get("humanYesAgentYes") or cm.get("n") != HUMAN_VALIDATION_N:
        report.error("human_validation: 混淆矩阵结构异常")
    agree = cells[0] + cells[3]
    if round(agree / HUMAN_VALIDATION_N * 100, 2) != hv.get("agreement", {}).get("headline", {}).get("rate"):
        report.error("human_validation: headline agreement 与 204/222 不一致")
    if agree != hv.get("agreement", {}).get("headline", {}).get("agree"):
        report.error("human_validation: headline agreement 计数不一致")
    if cells[1] != 15 or cells[2] != 3:
        report.error("human_validation: 分歧应为 human+/agent- 15 与 human-/agent+ 3")

    rec = hv.get("reconciliation", [])
    want = {"legacyM": 159, "legacyMRF": 180, "human": 177, "agent": 165}
    got = {r.get("key"): r.get("yes") for r in rec}
    if got != want:
        report.error(f"human_validation: 四种口径计数 {got} != {want}")
    if len(rec) != 4:
        report.error("human_validation: reconciliation 应为 4 项")

    # Keep the three-category component comparisons distinct from the derived
    # binary headline comparison. Their kappas need not be equal.
    ct = hv.get("componentTable", {})
    rows_ct = ct.get("rows", [])
    if len(rows_ct) != 5:
        report.error(f"human_validation: componentTable 应列 5 项比较，实际 {len(rows_ct)}")
    byk = {r.get("key"): r for r in rows_ct}
    expected_keys = {"headline", "ruleApplicability", "ruleViolation", "legacyMRF", "legacyMOnly"}
    if set(byk) != expected_keys:
        report.error(f"human_validation: componentTable 行键异常 {sorted(byk)}")
    else:
        for key, agree, kappa, rate, labels in (
            ("ruleApplicability", 177, 0.221, 79.73, "3-cat"),
            ("ruleViolation", 204, 0.777, 91.89, "3-cat"),
            ("headline", 204, 0.772, 91.89, "binary"),
            ("legacyMRF", 207, 0.786, 93.24, "binary"),
            ("legacyMOnly", 186, 0.563, 83.78, "multi"),
        ):
            r = byk[key]
            if (r.get("agree"), r.get("kappa"), r.get("rate"), r.get("labels")) != (agree, kappa, rate, labels):
                report.error(
                    f"human_validation: componentTable[{key}] 期望 "
                    f"{agree}/{kappa}/{rate}/{labels}，实际 "
                    f"{r.get('agree')}/{r.get('kappa')}/{r.get('rate')}/{r.get('labels')}"
                )
    if not ct.get("note"):
        report.error("human_validation: componentTable 缺少标签空间说明")

    dis = hv.get("disagreements", [])
    if len(dis) != 18:
        report.error(f"human_validation: 分歧条数 {len(dis)} != 18")
    if hv.get("disagreementCounts", {}).get("humanYesAgentNo") != 15:
        report.error("human_validation: disagreementCounts.humanYesAgentNo != 15")
    if hv.get("disagreementCounts", {}).get("humanNoAgentYes") != 3:
        report.error("human_validation: disagreementCounts.humanNoAgentYes != 3")
    for c in dis:
        for key in ("id", "human", "agent", "mechanism", "humanReason", "agentReason"):
            if not c.get(key):
                report.error(f"human_validation: 分歧 {c.get('id')} 缺少字段 {key}")
        if c.get("human") not in ("yes", "no") or c.get("agent") not in ("yes", "no"):
            report.error(f"human_validation: 分歧 {c.get('id')} 判定非二元")

    # 结论方向：必须写明是辅助检查，且不得称人工一致性
    emphasis = " ".join(hv.get("methodNotes", [])) + " " + str(agent.get("role", ""))
    if "辅助可靠性检查" not in emphasis:
        report.error("human_validation: 必须声明 agent 为辅助可靠性检查")
    if "不是人工一致性" not in emphasis:
        report.error("human_validation: 必须声明 agent 对照不是人工一致性")

    # 脱敏
    blob = json.dumps(hv, ensure_ascii=False)
    for bad in HUMAN_VALIDATION_FORBIDDEN:
        if bad in blob:
            report.error(f"human_validation: 公开发布数据含内部标识 {bad!r}")


RERANK_FORBIDDEN_KEYS = {
    "query", "queries", "docId", "doc_id", "resume", "candidateId",
    "gold", "prediction", "predictions", "items", "responses",
}


def _walk_keys(node: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(str(k))
            keys |= _walk_keys(v)
    elif isinstance(node, list):
        for v in node:
            keys |= _walk_keys(v)
    return keys


def check_rerank_model_selection(report: Report, payload: dict) -> None:
    """精排（rerank）模型选型与路由回测的公开聚合数据不变量。

    独立实验：生产检索链路的精排选型，**不**与 NL2IR 解析评测混用。
    """
    if payload.get("schema") != "rerank-model-selection/v1":
        report.error(f"rerank_model_selection schema 异常: {payload.get('schema')}")
        return

    models = payload.get("models") or []
    by_id = {m.get("modelId"): m for m in models}
    expected_ids = {"qwen3.7-max", "qwen3.7-plus", "qwen3.8-flash", "qwen3.7-flash",
                    "deepseek-v4.1-flash", "qwen3.8-max-0902", "qwen3.6-flash"}
    if set(by_id) != expected_ids:
        report.error(f"rerank_model_selection 模型集合不符: {sorted(by_id)}")
        return

    if payload.get("primaryMetric") != "judgeScore10":
        report.error(f"rerank_model_selection primary 指标不符: {payload.get('primaryMetric')}")

    # 质量：3.7 Max 最高、3.6 Flash（现役）最低；分数落在 0–10
    for m in models:
        score = m.get("judgeScore10")
        if not isinstance(score, (int, float)) or not 0 <= score <= 10:
            report.error(f"rerank_model_selection judgeScore10 越界: {m.get('modelId')} {score}")
    best = max(models, key=lambda m: m.get("judgeScore10", -1)).get("modelId")
    worst = min(models, key=lambda m: m.get("judgeScore10", 99)).get("modelId")
    if best != "qwen3.7-max":
        report.error(f"rerank_model_selection 质量最高应为 qwen3.7-max，实际 {best}")
    if worst != "qwen3.6-flash":
        report.error(f"rerank_model_selection 质量最低应为 qwen3.6-flash，实际 {worst}")

    # 成本单调性（占基线百分比）：max 档 > ds > plus > 现役 flash > 3.8 flash > 3.7 flash
    order = ["qwen3.7-max", "qwen3.8-max-0902", "deepseek-v4.1-flash", "qwen3.7-plus",
             "qwen3.6-flash", "qwen3.8-flash", "qwen3.7-flash"]
    shares = [by_id[k].get("costShareOfBaselinePct", -1) for k in order]
    if any(c is None or c <= 0 for c in shares):
        report.error("rerank_model_selection 成本占比缺失或非正")
    elif shares != sorted(shares, reverse=True):
        report.error(f"rerank_model_selection 成本占比排序不符: {list(zip(order, shares))}")
    if by_id["qwen3.7-max"].get("costShareOfBaselinePct") != 100.0:
        report.error("rerank_model_selection 基线成本占比应为 100")

    # 批量耗时范围必须与逐模型值一致
    rng = payload.get("batchWallRangeS") or {}
    walls = [m.get("batchWallP50S") for m in models]
    if rng.get("min") != min(walls) or rng.get("max") != max(walls):
        report.error(f"rerank_model_selection batchWallRangeS 与逐模型值不一致: {rng} vs {min(walls)}-{max(walls)}")

    # 兼容性：只有现役能在生产形态原样跑；其余 400；deepseek 连结构化输出变体也不支持
    for mid, m in by_id.items():
        compat = m.get("compatibility") or {}
        want = 200 if mid == "qwen3.6-flash" else 400
        if compat.get("productionShape") != want:
            report.error(f"rerank_model_selection 生产形态兼容性不符: {mid} {compat.get('productionShape')}")
    if (by_id["deepseek-v4.1-flash"].get("compatibility") or {}).get("structuredOutputVariant") != 400:
        report.error("rerank_model_selection deepseek 结构化输出变体仍应不可用")

    # 校准：现役与 3.7 Flash 中位数虚高；其余 ≤ 0.2；合格线不可平移必须显式声明
    cal = payload.get("calibration") or {}
    med = cal.get("medianScoreByModel") or {}
    if med.get("qwen3.6-flash") != 0.5 or med.get("qwen3.7-flash") != 0.5:
        report.error(f"rerank_model_selection 弱池中位数不符（现役/3.7 Flash 应为 0.50）: {med}")
    others = [v for k, v in med.items() if k not in ("qwen3.6-flash", "qwen3.7-flash")]
    if any(v is None or v > 0.2 for v in others):
        report.error(f"rerank_model_selection 新一代模型弱池中位数应 ≤0.2: {med}")
    if cal.get("scaleNotPortable") is not True:
        report.error("rerank_model_selection 必须声明现役合格线不可平移")

    # 路由：结论的事实必须是「干净子集上没有任何低成本策略追平 max」
    router = payload.get("router") or {}
    base = router.get("baseline") or {}
    base_clean = base.get("judgeClean16")
    if not isinstance(base_clean, (int, float)):
        report.error("rerank_model_selection router.baseline 缺 clean16 基线")
    else:
        for s in router.get("strategies") or []:
            clean = s.get("judgeClean16")
            if clean is None:
                report.error(f"rerank_model_selection 策略缺干净子集指标（不得跳过校验）: {s.get('key')}")
                continue
            if clean >= base_clean:
                report.error(f"rerank_model_selection 结论与数据矛盾：策略追平/超过 max {s.get('key')} {clean} >= {base_clean}")

    # 非劣口径：界限与两种口径的通过判定必须自洽，且 verdict 必须携带计算出的差距
    ni = router.get("nonInferiority") or {}
    margin = ni.get("margin")
    if not isinstance(margin, (int, float)):
        report.error("rerank_model_selection 缺非劣界限 margin")
    else:
        for key, pass_key in (("gapClean16", "passesClean16"), ("gapAll20", "passesAll20")):
            gap = ni.get(key)
            if not isinstance(gap, (int, float)):
                report.error(f"rerank_model_selection 缺 {key}")
                continue
            if bool(ni.get(pass_key)) != (gap <= margin):
                report.error(f"rerank_model_selection {pass_key} 与 {key}/{margin} 不自洽")
    verdict = str(router.get("verdict") or "")
    for key in ("gapClean16", "gapAll20"):
        gap = ni.get(key)
        if isinstance(gap, (int, float)) and f"{gap:.2f}" not in verdict:
            report.error(f"rerank_model_selection verdict 未携带计算出的 {key}={gap:.2f}（结论必须由聚合值生成）")
    if router.get("bestNoMaxKey") not in {s.get("key") for s in router.get("strategies") or []}:
        report.error(f"rerank_model_selection bestNoMaxKey 不在策略集合中: {router.get('bestNoMaxKey')}")
    if router.get("truncatedSessions") != 4 or router.get("cleanSubsetN") != 16:
        report.error(f"rerank_model_selection 截断/干净子集数不符: "
                     f"{router.get('truncatedSessions')}/{router.get('cleanSubsetN')}")

    # 必须声明的三类风险
    limits = " ".join(payload.get("limitations") or [])
    for need in ("post-hoc", "留出集", "翻转"):
        if need not in limits:
            report.error(f"rerank_model_selection limitations 缺风险声明: {need}")
    if "judgeNoiseNote" not in router or "postHocNote" not in router:
        report.error("rerank_model_selection router 缺 judge 噪声 / post-hoc 说明")

    # Codex 复核记录与结论下调必须写进 provenance
    review = (payload.get("provenance") or {}).get("codexReview") or {}
    if not review.get("date") or "下调" not in str(review.get("effect", "")):
        report.error("rerank_model_selection provenance 缺独立复核记录（含结论下调说明）")

    # 脱敏：不得出现逐题/候选人级字段
    leaked = _walk_keys(payload) & RERANK_FORBIDDEN_KEYS
    if leaked:
        report.error(f"rerank_model_selection 含逐题字段: {sorted(leaked)}")
    # 脱敏：不得出现内部项目名 / 路径 / 系统参数
    blob = json.dumps(payload, ensure_ascii=False)
    # 通用模式：内部服务名（*-service）、内部路径、内部步骤/参数名——不在此处写出任何真实内部标识
    internal_leaks = [t for t in ("-service", "/tmp/", "/dat/", "hard-fail", "hard_fail",
                                  "uniqueItems", "min_confidence", "minConfidence", "审计库", "0.75")
                      if t in blob]
    if internal_leaks:
        report.error(f"rerank_model_selection 含内部信息: {internal_leaks}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/")
    parser.add_argument("--strict", action="store_true", help="把 warning 也视为失败")
    args = parser.parse_args()

    data_dir = (ROOT / args.data).resolve()
    if not data_dir.exists():
        print(f"[ERR] 数据目录不存在: {data_dir}")
        return 1

    report = Report()

    # 各文件
    try:
        runs = load_json(data_dir / "runs.json") or []
        check_runs(report, runs)
    except Exception as e:
        report.error(f"runs.json: {e}")

    try:
        metrics = load_json(data_dir / "metrics.json") or []
        check_metrics(report, metrics)
        # 自动修复 accuracy 后回写
        if any("accuracy" in m for m in metrics):
            # 已在检查中就地修改
            (data_dir / "metrics.json").write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2)
            )
    except Exception as e:
        report.error(f"metrics.json: {e}")

    # 公开仓库只允许聚合指标。本机可以保留逐题证据，但不得被 Git 跟踪。
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "--", "data/cases.json", "data/raw"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if tracked:
        report.error(f"公开发行版禁止跟踪逐题测评数据: {tracked}")

    try:
        conclusions = load_json(data_dir / "conclusions.json") or []
        check_conclusions(report, conclusions)
    except Exception as e:
        report.error(f"conclusions.json: {e}")

    hosted_path = data_dir / "hosted_api_baselines.json"
    if hosted_path.exists():
        try:
            hosted = load_json(hosted_path) or {}
            check_hosted_api_baselines(report, hosted)
        except Exception as e:
            report.error(f"hosted_api_baselines.json: {e}")

    stability_path = data_dir / "api_stability.json"
    if stability_path.exists():
        try:
            check_api_stability(report, load_json(stability_path) or {})
        except Exception as e:
            report.error(f"api_stability.json: {e}")

    rerank_path = data_dir / "rerank_model_selection.json"
    if rerank_path.exists():
        try:
            check_rerank_model_selection(report, load_json(rerank_path) or {})
        except Exception as e:
            report.error(f"rerank_model_selection.json: {e}")

    # aux
    overlap_path = data_dir / "aux" / "overlap_report.json"
    if overlap_path.exists():
        try:
            overlap = load_json(overlap_path) or {}
            check_overlap(report, overlap)
        except Exception as e:
            report.error(f"overlap_report.json: {e}")

    training_path = data_dir / "training.json"
    if training_path.exists():
        try:
            training = load_json(training_path) or {}
            check_training(report, training)
        except Exception as e:
            report.error(f"training.json: {e}")

    hv_path = data_dir / "human_validation.json"
    if hv_path.exists():
        try:
            check_human_validation(report, load_json(hv_path) or {})
        except Exception as e:
            report.error(f"human_validation.json: {e}")
    else:
        report.error("human_validation.json: 缺少人工盲复核聚合数据")

    # 输出
    print(f"\n=== 校验报告 ===")
    print(f"错误: {len(report.errors)}")
    for e in report.errors:
        print(f"  [ERROR] {e}")
    print(f"警告: {len(report.warnings)}")
    for w in report.warnings[:20]:
        print(f"  [WARN] {w}")
    if len(report.warnings) > 20:
        print(f"  ... 还有 {len(report.warnings) - 20} 条警告")

    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main())
