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

    expected_ids = ["qwen3.7-max", "qwen3.8-flash", "deepseek-v4.1-flash"]
    if sorted(by_id) != sorted(expected_ids):
        report.error(f"hosted_api_baselines 模型 ID 不符: {sorted(by_id)}")

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

    expected_where = {"qwen3.7-max": 94.26, "qwen3.8-flash": 89.62, "deepseek-v4.1-flash": 86.20}
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

    # role_tenure 审计未冻结：不得写入实现结论
    for m in models:
        text = f"{m.get('role','')}{m.get('conclusion','')}"
        if "role_tenure" in text or "任职" in text:
            report.error(f"hosted_api_baselines 模型结论不得包含 role_tenure 实现结论: {m.get('modelId')}")
    if not any("role_tenure" in x and "仍在验证" in x for x in (payload.get("limitations") or [])):
        report.error("hosted_api_baselines limitations 缺 role_tenure 待验证声明")


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
