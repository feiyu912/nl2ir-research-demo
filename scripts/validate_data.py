"""数据纪律校验脚本（前端 discipline.ts 等价）。

检查 8 类 JSON 是否满足不变量。

Usage:
    python3 scripts/validate_data.py --data data/ [--strict]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUX = DATA / "aux"

DATE_MIN = "1970-01-01"
DATE_MAX = "2999-12-31"


# ---------------------------------------------------------------------------
# 公开发布物脱敏守卫
#
# 只描述"形状"（路径/网段/邮箱/主机名），不列举任何真实内部标识，避免守卫
# 本身成为泄露源。data/ 下仅本地保留、永不发布的文件不参与扫描。
# ---------------------------------------------------------------------------
LOCAL_ONLY_PARTS = (
    "data/cases.json", "data/raw/", "data/private/", "data/tmp/", "data/tmp_export/",
    "data/exports/", "data/aux/history_overview.json",
)

SANITIZE_PATTERNS = (
    # 前边界用"非字母数字"而不是空白/标点白名单：Markdown 反引号包裹的路径
    # （`/dat/...`）曾经正是漏检的那一处。
    ("本地绝对路径", re.compile(r"(?<![A-Za-z0-9])/(?:Users|home|mnt|workspace|Volumes|dat)/")),
    ("Windows 绝对路径", re.compile(r"[A-Za-z]:\\")),
    ("家目录相对路径", re.compile(r"~/[^\s]")),
    # 私有网段要求完整四段 IPv4，且两侧不得贴字母数字：否则 v10.1.2 这类版本号会误报。
    # 192.168 与 172.x 分支自带两段，只需再补两段；裸 10 分支自带一段，需再补三段。
    ("私有网段 IP", re.compile(
        r"(?<![0-9A-Za-z.])(?:192\.168(?:\.\d{1,3}){2}"
        r"|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
        r"|10(?:\.\d{1,3}){3})(?![0-9A-Za-z.])")),
    ("邮箱地址", re.compile(r"\b[\w.+-]+@[\w-]+\.[A-Za-z]{2,}\b")),
    ("内部主机名", re.compile(r"\b[\w-]+\.(?:internal|corp|lan)\b")),
)


def _local_denylist() -> tuple[str, ...]:
    """本机私有黑名单（永不入库）：覆盖无法用"形状"识别的内部名字。

    来源：环境变量 NL2IR_PUBLIC_DENYLIST（逗号分隔）与 gitignored 的
    scripts/denylist.local（每行一个 token，# 开头为注释）。
    """
    tokens: list[str] = [
        t.strip() for t in os.environ.get("NL2IR_PUBLIC_DENYLIST", "").split(",") if t.strip()
    ]
    path = ROOT / "scripts" / "denylist.local"
    if path.exists():
        tokens.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return tuple(dict.fromkeys(tokens))


def _published_text_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("data/**/*.json", "docs/**/*.md", "src/**/*.ts", "src/**/*.tsx"):
        files.extend(ROOT.glob(pattern))
    readme = ROOT / "README.md"
    if readme.exists():
        files.append(readme)
    published = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if any(rel == part.rstrip("/") or rel.startswith(part) for part in LOCAL_ONLY_PARTS):
            continue
        published.append(path)
    return sorted(set(published))


def check_public_sanitization(report: Report) -> None:
    """公开发布物不得出现本地路径、内网地址或内部主机名。"""
    denylist = _local_denylist()
    if not denylist:
        # 形状正则抓不到内部仓库名/公司域名这类"名字"。没有私有黑名单时必须明说
        # 覆盖不到，不能让"全局脱敏"在没有配置的 CI / 新 clone 里静默通过。
        msg = ("sanitization: 未加载私有黑名单（scripts/denylist.local 或 "
               "NL2IR_PUBLIC_DENYLIST）——本次只覆盖路径/网段/邮箱/主机名等形状，内部名称类标识未检查")
        if os.environ.get("NL2IR_REQUIRE_DENYLIST") == "1":
            report.error(msg)
        else:
            # 只做信息输出：CI 是干净 clone（黑名单被 gitignore），不能因此把它判红。
            print(f"  [INFO] {msg}")
    for path in _published_text_files():
        rel = path.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for label, pattern in SANITIZE_PATTERNS:
                if pattern.search(line):
                    report.error(f"sanitization: {rel}:{lineno} 含{label}")
            for token in denylist:
                if token in line:
                    report.error(f"sanitization: {rel}:{lineno} 含私有黑名单词条（{len(token)} 字符）")


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

    # 冻结批次日期必须非空（不校验格式）：口径随日期/形态变化，缺失后读者无法判断数字归属。
    if not str(payload.get("experimentDate") or "").strip():
        report.error("hosted_api_baselines 缺 experimentDate（冻结批次日期不得为空）")

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
            if not str((m.get("provenance") or {}).get("batch") or "").strip():
                report.error(f"hosted_api_baselines 快照模型缺 provenance.batch: {m.get('modelId')}")
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
        if (lo <= 0 <= hi) != bool(pw.get("clusterCrossesZero")):
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
        if (ci[0] <= 0 <= ci[1]) != bool(b.get("clusterCrossesZero")):
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
        if (ci[0] <= 0 <= ci[1]) != bool(r.get("clusterCrossesZero")):
            report.error(f"hosted_api_baselines 无 max 策略 clusterCrossesZero 不一致: {r.get('policy')}")
    best = max((r.get("blindWhere", 0) for r in strats), default=0)
    if nomax.get("oracleNonMax", 0) < best:
        report.error("hosted_api_baselines 无 max oracle 低于最佳可部署策略（不可能是上界）")

    # ---- 新口径评测块：统一 thinking-off、max 事故与恢复、参考 = pin 快照 0902 ----
    he = payload.get("holdoutEvaluation") or {}
    if not he:
        report.error("hosted_api_baselines 缺 holdoutEvaluation")
    else:
        if "thinking-off" not in str(he.get("shape", "")):
            report.error("holdoutEvaluation.shape 必须声明为统一 thinking-off 口径")
        if not he.get("shapeNote"):
            report.error("holdoutEvaluation 缺形态对照说明（该开关效果模型特有，排名会翻转）")
        inc = he.get("incidentNote") or {}
        if inc.get("model") != "qwen3.7-max":
            report.error(f"holdoutEvaluation.incidentNote 应记录 qwen3.7-max: {inc.get('model')}")
        obs = inc.get("observed") or {}
        rate = obs.get("corruptRatePct")
        if not isinstance(rate, (int, float)) or rate < 10:
            report.error(f"holdoutEvaluation.incidentNote 缺损坏率证据: {rate}")
        if len((inc.get("control") or {}).get("sameShapeSameBatchOtherModels") or {}) < 4:
            report.error("holdoutEvaluation.incidentNote 缺「同形态其他模型对照」")
        if "恢复" not in str(inc.get("recovery", "")):
            report.error("holdoutEvaluation.incidentNote 必须写明已恢复（事故≠永久退化）")
        if len(inc.get("whyNotReference") or []) < 2 or not inc.get("handling"):
            report.error("holdoutEvaluation.incidentNote 需 ≥2 条「为何不当参考」+ 处理方式")
        ref = he.get("reference") or {}
        if ref.get("modelId") != "qwen3.8-max-0902":
            report.error(f"holdoutEvaluation 参考应为 qwen3.8-max-0902: {ref.get('modelId')}")
        rows_ = he.get("singleModel") or []
        if len(rows_) < 5:
            report.error(f"hosted_api_baselines holdoutEvaluation 单模型行过少: {len(rows_)}")
        refrow = next((r for r in rows_ if r.get("modelId") == ref.get("modelId")), None)
        if refrow is None:
            report.error("hostoutEvaluation 参考模型不在单模型表中")
        elif refrow.get("deltaVsRefPp") != 0:
            report.error("hostoutEvaluation 参考行 deltaVsRefPp 应为 0")
        for r in rows_:
            a = r.get("acc750Pct")
            if not isinstance(a, (int, float)) or not 0 < a <= 100:
                report.error(f"hostoutEvaluation acc750 越界: {r.get('modelId')} {a}")
        # max 必须在表内、且必须带 measuredAt 与事故说明（它已从「排除」改为「对照行」）
        mx = next((r for r in rows_ if r.get("modelId") == "qwen3.7-max"), None)
        if mx is None:
            report.error("hostoutEvaluation 缺 qwen3.7-max 行（事故已恢复，须作为对照行保留）")
        else:
            if not str(mx.get("measuredAt", "")).strip():
                report.error("hostoutEvaluation 的 qwen3.7-max 行必须带 measuredAt")
            if "事故" not in str(mx.get("note", "")):
                report.error("hostoutEvaluation 的 qwen3.7-max 行必须说明 10-08 事故")
        # 隔日重跑：结论「无显著差异」必须与数据一致
        rt = he.get("runToRun") or {}
        by = rt.get("byModel") or []
        if len(by) < 5:
            report.error(f"hostoutEvaluation.runToRun 需 ≥5 个模型: {len(by)}")
        for r in by:
            p_ = r.get("mcnemarP")
            if not isinstance(p_, (int, float)) or p_ < 0.05:
                report.error(f"hostoutEvaluation.runToRun 出现显著差异（需重跑该模型）: {r.get('modelId')} p={p_}")
        if "没有证据" not in str(rt.get("note", "")):
            report.error("hostoutEvaluation.runToRun 必须写明「没有证据表明被系统性压低」")
        if not he.get("q38StabilityNote"):
            report.error("hostoutEvaluation 缺 qwen3.8-flash 稳定度说明")
        oc = he.get("oracleCheapOnly") or {}
        best_single = max((r.get("acc750Pct", 0) for r in rows_), default=0)
        if not isinstance(oc.get("merged750Pct"), (int, float)) or oc["merged750Pct"] + 1e-9 < best_single:
            report.error(f"oracle 低于最佳单模型（不可能是上界）: {oc.get('merged750Pct')} < {best_single}")
        rules_ = he.get("deployableRules") or []
        base_rule = next((r for r in rules_ if str(r.get("rule", "")).startswith("★ R6s")), None)
        if base_rule is None:
            report.error("hostoutEvaluation 缺 R6s 基准行")
        elif base_rule.get("deltaVsR6sPp") != 0:
            report.error("hostoutEvaluation R6s 基准行 deltaVsR6sPp 应为 0")
        for r in rules_:
            a = r.get("acc750Pct")
            if isinstance(a, (int, float)) and a > oc.get("merged750Pct", 100) + 1e-9:
                report.error(f"hostoutEvaluation 规则超过 oracle（不可能）: {r.get('rule')}")
            pct = r.get("oracleHeadroomClosedPct")
            if isinstance(pct, (int, float)) and pct > 100:
                report.error(f"hostoutEvaluation 空间占比 >100%: {r.get('rule')} {pct}")
        if not he.get("r6sMechanism") or not he.get("r6sWeakness"):
            report.error("hostoutEvaluation 缺 R6s 机制说明或局限说明")
        concl = str(he.get("conclusion", ""))
        if not concl.strip():
            report.error("hostoutEvaluation 缺结论")
        best_row = max(rows_, key=lambda r: r.get("acc750Pct", 0), default={})
        if best_row.get("modelId") and best_row["modelId"] not in concl:
            report.error(f"hostoutEvaluation 结论未提到实际最高模型 {best_row['modelId']}（叙述与数据脱节）")
        if not str((payload.get("routersNoMax") or {}).get("supersededNote", "")).strip():
            report.error("hosted_api_baselines.routersNoMax 缺「旧仲裁结论已作废」的指向说明")

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


RERANK_EXPECTED_CANDIDATES = {"qwen3.8-flash", "qwen3.7-max", "qwen3.7-flash", "bordaMerge"}
RERANK_EXPECTED_STRATEGIES = {"cheapOnly", "flash38Only", "softN", "softN_hardN"}
RERANK_ORDER_TOLERANCE = 15.0


RERANK_EXPECTED_CANDIDATES = {"qwen3.8-flash", "qwen3.7-max", "qwen3.7-plus", "qwen3.7-flash",
                              "deepseek-v4.1-flash", "qwen3.8-max-0902", "bordaMerge"}
RERANK_EXPECTED_STRATEGIES = {"cheapOnly", "flash38Only", "softN", "softN_hardN"}
RERANK_ORDER_TOLERANCE = 15.0


def check_rerank_model_selection(report: Report, payload: dict) -> None:
    """精排（rerank）模型选型的公开聚合数据不变量。

    独立实验：生产检索链路的精排选型，**不**与 NL2IR 解析评测混用。
    质量口径 = 对现役的成对偏好（双向 + 重复）；只认两个方向一致的结论。
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
    if payload.get("primaryMetric") != "pairwisePreferenceVsIncumbent":
        report.error(f"rerank_model_selection primary 指标不符: {payload.get('primaryMetric')}")
    if any("judgeScore10" in m for m in models):
        report.error("rerank_model_selection 仍带已作废的盲评评分字段")

    # 成本：现役 = 100%；更便宜 / 更贵必须与结论方向一致
    if by_id["qwen3.6-flash"].get("costShareOfIncumbentPct") != 100.0:
        report.error("rerank_model_selection 现役成本占比应为 100")
    for m in models:
        for key in ("costShareOfBaselinePct", "costShareOfIncumbentPct", "batchWallP50S"):
            v = m.get(key)
            if not isinstance(v, (int, float)) or v <= 0:
                report.error(f"rerank_model_selection {m.get('modelId')} 的 {key} 非法: {v}")
    for mid in ("qwen3.7-flash", "qwen3.8-flash"):
        if (by_id[mid].get("costShareOfIncumbentPct") or 1e9) >= 100:
            report.error(f"rerank_model_selection {mid} 应比现役便宜（占现役 <100%）")
    for mid in ("qwen3.7-plus", "deepseek-v4.1-flash"):
        if (by_id[mid].get("costShareOfIncumbentPct") or 0) <= 100:
            report.error(f"rerank_model_selection {mid} 应比现役更贵（占现役 >100%）")
    order = ["qwen3.7-max", "qwen3.8-max-0902", "deepseek-v4.1-flash", "qwen3.7-plus",
             "qwen3.6-flash", "qwen3.8-flash", "qwen3.7-flash"]
    shares = [by_id[k].get("costShareOfBaselinePct", -1) for k in order]
    if shares != sorted(shares, reverse=True):
        report.error(f"rerank_model_selection 成本占比排序不符: {list(zip(order, shares))}")

    rng = payload.get("batchWallRangeS") or {}
    walls = [m.get("batchWallP50S") for m in models]
    if rng.get("min") != min(walls) or rng.get("max") != max(walls):
        report.error(f"rerank_model_selection batchWallRangeS 不一致: {rng} vs {min(walls)}-{max(walls)}")
    for mid, m in by_id.items():
        compat = m.get("compatibility") or {}
        want = 200 if mid == "qwen3.6-flash" else 400
        if compat.get("productionShape") != want:
            report.error(f"rerank_model_selection 生产形态兼容性不符: {mid} {compat.get('productionShape')}")
    if (by_id["deepseek-v4.1-flash"].get("compatibility") or {}).get("structuredOutputVariant") != 400:
        report.error("rerank_model_selection deepseek 结构化输出变体仍应不可用")

    cal = payload.get("calibration") or {}
    med = cal.get("medianScoreByModel") or {}
    if med.get("qwen3.6-flash") != 0.5 or med.get("qwen3.7-flash") != 0.5:
        report.error(f"rerank_model_selection 弱池中位数不符（现役/3.7 Flash 应为 0.50）: {med}")
    if any(v is None or v > 0.2 for k, v in med.items() if k not in ("qwen3.6-flash", "qwen3.7-flash")):
        report.error(f"rerank_model_selection 新一代模型弱池中位数应 ≤0.2: {med}")
    if cal.get("scaleNotPortable") is not True:
        report.error("rerank_model_selection 必须声明现役合格线不可平移")

    # ---- 成对偏好块 ----
    pw = payload.get("pairwise") or {}
    sessions = pw.get("sessions")
    if sessions != 16:
        report.error(f"rerank_model_selection pairwise.sessions 应为 16: {sessions}")
    cands = {c.get("key"): c for c in (pw.get("candidates") or [])}
    if set(cands) != RERANK_EXPECTED_CANDIDATES:
        report.error(f"rerank_model_selection 成对候选集合不符: {sorted(cands)}")
    for key, c in cands.items():
        w, l, t = c.get("wins"), c.get("losses"), c.get("ties")
        if not all(isinstance(x, int) and x >= 0 for x in (w, l, t)):
            report.error(f"rerank_model_selection {key} 场次计数非法: {w}/{l}/{t}")
            continue
        if w + l + t != sessions:
            report.error(f"rerank_model_selection {key} 场次合计 {w + l + t} != {sessions}")
        rates = []
        for bucket in ("incumbentFirst", "candidateFirst"):
            b = c.get(bucket) or {}
            cw, iw = b.get("candidateWins"), b.get("incumbentWins")
            if not isinstance(cw, int) or not isinstance(iw, int) or cw + iw <= 0:
                report.error(f"rerank_model_selection {key}.{bucket} 计数非法")
                continue
            want = round(100 * cw / (cw + iw), 1)
            if abs((b.get("winRatePct") or -1) - want) > 0.15:
                report.error(f"rerank_model_selection {key}.{bucket} 胜率与计数不符")
            rates.append(want)
        if rates:
            cons = min(rates)
            if abs((c.get("conservativeWinRatePct") or -1) - cons) > 0.15:
                report.error(f"rerank_model_selection {key} 保守胜率应为两个方向的最小值")
            if abs(rates[0] - rates[1]) <= RERANK_ORDER_TOLERANCE:
                span_ok = True
            else:
                span_ok = False
            c["orderConsistent"] = span_ok  # 供页面直接消费

    # 结论必须与数据一致：这三个判定是页面的核心主张，翻转即报错
    flat, d37, borda, mx = (cands.get("qwen3.8-flash") or {}, cands.get("qwen3.7-flash") or {},
                            cands.get("bordaMerge") or {}, cands.get("qwen3.7-max") or {})
    if not flat.get("orderConsistent") or (flat.get("conservativeWinRatePct") or 0) < 50:
        report.error("rerank_model_selection 3.8 Flash 不再满足「两向一致且不劣于现役」，结论需重写")
    if d37.get("orderConsistent"):
        report.error("rerank_model_selection 3.7 Flash 变成两向一致了，结论需重写")
    if borda.get("orderConsistent"):
        report.error("rerank_model_selection Borda 变成两向一致了，结论需重写")
    if not mx.get("orderConsistent"):
        report.error("rerank_model_selection 3.7 Max 不再两向一致，结论需重写")

    strats = {s.get("key"): s for s in (pw.get("strategies") or [])}
    if set(strats) != RERANK_EXPECTED_STRATEGIES:
        report.error(f"rerank_model_selection 策略集合不符: {sorted(strats)}")
    for key, s in strats.items():
        if any(not isinstance(s.get(x), int) for x in ("wins", "losses", "ties")):
            report.error(f"rerank_model_selection 策略 {key} 计数非法")
            continue
        if s["wins"] + s["losses"] + s["ties"] != sessions:
            report.error(f"rerank_model_selection 策略 {key} 场次合计不符")
    if strats.get("flash38Only") and strats.get("softN") and strats.get("softN_hardN"):
        base_edge = strats["flash38Only"]["wins"] - strats["flash38Only"]["losses"]
        for key in ("softN", "softN_hardN"):
            if strats[key]["wins"] - strats[key]["losses"] > base_edge:
                report.error(f"rerank_model_selection 「{key} 不优于全走 3.8 Flash」已不成立，结论需重写")

    val = pw.get("validation") or {}
    for tag in ("afterFix", "beforeFix"):
        blk = val.get(tag) or {}
        if not blk:
            report.error(f"rerank_model_selection 缺定标对照 {tag}")
            continue
        if blk.get("identicalPairAllTie") != "16/16":
            report.error(f"rerank_model_selection {tag} 相同方案对照未全判平: {blk.get('identicalPairAllTie')}")
    if (val.get("afterFix") or {}).get("degradedOrderInverted") != "0/16":
        report.error("rerank_model_selection 修复后仍出现「偏好更差排序」的对照结果")
    if (val.get("beforeFix") or {}).get("degradedOrderInverted") in (None, "0/16"):
        report.error("rerank_model_selection 缺「修复前会误判」的证据，根因声明不成立")
    if "截断" not in str(pw.get("rootCause") or ""):
        report.error("rerank_model_selection 必须声明评审输入曾被截断的根因")

    verdict = str(pw.get("verdict") or "")
    if len(verdict) < 80:
        report.error("rerank_model_selection 缺结论文本")
    # 不可用的候选必须在结论里被点名，不能悄悄留在表里当备选项
    for key, c in cands.items():
        usable = c.get("orderConsistent") and (c.get("conservativeWinRatePct") or 0) >= 50
        if not usable and c.get("alias") and c["alias"] not in verdict:
            report.error(f"rerank_model_selection 结论未点名不可用候选: {key}")

    limits = " ".join(payload.get("limitations") or [])
    for need in ("不劣于", "位置敏感", "编造"):
        if need not in limits:
            report.error(f"rerank_model_selection limitations 缺风险声明: {need}")
    review = (payload.get("provenance") or {}).get("codexReview") or {}
    if "截断" not in str(review.get("scope", "")):
        report.error("rerank_model_selection provenance 缺独立复核记录（含输入截断）")

    leaked = _walk_keys(payload) & RERANK_FORBIDDEN_KEYS
    if leaked:
        report.error(f"rerank_model_selection 含逐题字段: {sorted(leaked)}")
    blob = json.dumps(payload, ensure_ascii=False)
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

    # 公开发布物脱敏（先跑：任何内部路径/网段/主机名都直接失败）
    check_public_sanitization(report)

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
