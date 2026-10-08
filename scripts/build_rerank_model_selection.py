#!/usr/bin/env python3
"""Build data/rerank_model_selection.json from the frozen offline evaluation artifacts.

This is an INDEPENDENT experiment (production rerank model selection), separate from the
NL2IR parsing evaluation. It never calls models or APIs: it reads local artifacts produced by
the internal benchmark scripts and distills them into aggregate numbers only.

Inputs (local, not published):
  /tmp/rerank_model_bench_full/    7-model round: judge.json, session_*.json, compat_probe.json
  /tmp/rerank_router_backtest/     20-session router round: judge_qwen3max.json, session_*.json, features.json

Usage:
  python3 scripts/build_rerank_model_selection.py
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rerank_model_selection.json"

BENCH = Path(os.environ.get("RERANK_BENCH_DIR", "/tmp/rerank_model_bench_full"))
ROUTER = Path(os.environ.get("RERANK_ROUTER_DIR", "/tmp/rerank_router_backtest"))

# 公开价目（元/百万 tokens，2026-10-08 抓取；限时折扣按抓取当日显示价）
PRICE_DATE = "2026-10-08"
PRICE_SOURCE = "百炼模型广场价格页（公开价目；限时折扣按当日显示）"
PRICES = {
    "qwen3.7-flash": {"input": 0.2, "output": 0.8},
    "qwen3.8-flash": {"input": 0.8, "output": 2.7},
    "qwen3.6-flash": {"input": 1.2, "output": 7.2},
    "qwen3.7-plus": {"input": 1.6, "output": 6.4},
    "deepseek-v4.1-flash": {"input": 2.0, "output": 8.0},
    "qwen3.7-max": {"input": 12.0, "output": 36.0},
    "qwen3.8-max-0902": {"input": 12.0, "output": 36.0},
}
ALIAS = {
    "qwen3.7-max": "Qwen 3.7 Max",
    "qwen3.8-flash": "Qwen 3.8 Flash",
    "qwen3.7-flash": "Qwen 3.7 Flash",
    "qwen3.7-plus": "Qwen 3.7 Plus",
    "qwen3.8-max-0902": "Qwen 3.8 Max 0902",
    "deepseek-v4.1-flash": "DeepSeek V4.1 Flash",
    "qwen3.6-flash": "Qwen 3.6 Flash（现役）",
}
TONE = {
    "qwen3.7-max": "baseline",
    "qwen3.8-flash": "candidate",
    "qwen3.7-flash": "value",
    "qwen3.7-plus": "candidate",
    "qwen3.8-max-0902": "hold",
    "deepseek-v4.1-flash": "hold",
    "qwen3.6-flash": "incumbent",
}
ROLE = {
    "qwen3.7-max": "质量基线",
    "qwen3.8-flash": "弱池行为修正候选",
    "qwen3.7-flash": "最低成本候选",
    "qwen3.7-plus": "中间档候选",
    "qwen3.8-max-0902": "同价位不划算",
    "deepseek-v4.1-flash": "不建议（幻觉 + 偶发 400）",
    "qwen3.6-flash": "现役对照",
}
FALLBACK = "满足硬条件召回"


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"缺少工件: {path}（先跑内部基准脚本，或用 RERANK_*_DIR 指定目录）")
    return json.loads(path.read_text())


def judge_means(payload: dict, keys: list[str]) -> dict[str, dict[str, float]]:
    """session -> model -> mean(ranking, reasons) over seeds."""
    out: dict[str, dict[str, float]] = {}
    for key in keys:
        calls = payload.get(key) or []
        acc: dict[str, list[float]] = {}
        for call in calls:
            blind = call.get("blindMap") or {}
            for r in call.get("ratings") or []:
                model = blind.get(str(r.get("label")), str(r.get("label")))
                acc.setdefault(model, []).extend([float(r.get("ranking") or 0), float(r.get("reasons") or 0)])
        out[key] = {m: round(sum(v) / len(v), 2) for m, v in acc.items()}
    return out


def session_usage(bench_dir: Path, session_id: int, model: str) -> dict:
    data = load(bench_dir / f"session_{session_id}.json")["models"][model]
    api = data.get("api") or {}
    price = PRICES[model]
    prompt = int(api.get("promptTokens") or 0)
    completion = int(api.get("completionTokens") or 0)
    cost = prompt / 1e6 * price["input"] + completion / 1e6 * price["output"]
    return {
        "wallMs": int(data.get("wallMs") or 0),
        "callP50Ms": int((api.get("latencyMs") or {}).get("p50") or 0),
        "promptTokens": prompt,
        "completionTokens": completion,
        "costCny": round(cost, 4),
    }


def build_models() -> tuple[list[dict], dict]:
    """7-model round: judge score (3 sessions x 2 seeds) + per-search cost/latency on 200-pool sessions."""
    judge = load(BENCH / "judge.json")
    sessions = sorted(judge.keys())
    means = judge_means(judge, sessions)
    models = list(means[sessions[0]].keys())
    pool200 = [s for s in sessions if load(BENCH / f"session_{s}.json")["poolInfo"]["poolSize"] == 200]

    rows = []
    for model in models:
        scores = [means[s][model] for s in sessions if model in means[s]]
        costs, walls, p50s = [], [], []
        for s in pool200:
            usage = session_usage(BENCH, int(s), model)
            costs.append(usage["costCny"])
            walls.append(usage["wallMs"])
            p50s.append(usage["callP50Ms"])
        rows.append({
            "modelId": model,
            "alias": ALIAS.get(model, model),
            "tone": TONE.get(model, "candidate"),
            "role": ROLE.get(model, ""),
            "judgeScore10": round(statistics.mean(scores), 2),
            "judgeSessions": len(scores),
            "costPerSearchCny": round(statistics.mean(costs), 4),
            "wallP50S": round(statistics.median(walls) / 1000, 1),
            "wallMaxS": round(max(walls) / 1000, 1),
            "shardCallP50S": round(statistics.median(p50s) / 1000, 1),
            "priceCnyPerMTok": PRICES[model],
        })
    rows.sort(key=lambda r: -r["judgeScore10"])

    # calibration probe on the weak pool (session 5242): median score by model
    weak = "5242"
    weak_medians = {}
    for model in models:
        items = [it for it in load(BENCH / f"session_{weak}.json")["models"][model]["items"]
                 if FALLBACK not in it["reason"]]
        scores = [it["confidence"] for it in items]
        weak_medians[model] = round(statistics.median(scores), 2) if scores else None
    calibration = {
        "weakPool": {"poolSize": 200, "note": "池内几乎无查询所要求的实质条件（技能条件全池零命中）"},
        "medianScoreByModel": weak_medians,
        "minConfidenceNotPortable": True,
        "note": "现役 0.75 合格线是按 Qwen 3.6 Flash 的虚高刻度校准的；同池中位数：3.6 Flash 与 3.7 Flash 为 0.50（虚高），"
                "其余模型仅 0.10–0.16。strict 模式下直接换模型会让弱池查询返回空结果页，换模型前必须重校准阈值。",
    }
    return rows, calibration


def rule_of(features: dict, name: str) -> str:
    if name == "cheapOnly":
        return "qwen3.7-flash"
    if name == "flash38Only":
        return "qwen3.8-flash"
    if name == "softN":
        return "qwen3.8-flash" if features["softN"] >= 2 else "qwen3.7-flash"
    if name == "softN_hardN":
        if features["softN"] >= 2:
            return "qwen3.8-flash"
        return "qwen3.7-max" if features["hardN"] >= 4 else "qwen3.7-flash"
    raise ValueError(name)


def build_router() -> dict:
    judge = load(ROUTER / "judge_qwen3max.json")
    features = {int(k): v for k, v in load(ROUTER / "features.json").items()}
    sessions = sorted(judge.keys(), key=int)
    scores = judge_means(judge, sessions)
    sessions_int = [int(s) for s in sessions]

    invalid, valid, truncated_saved = [], [], []
    for sid in sessions_int:
        data = load(ROUTER / f"session_{sid}.json")
        saved = min(len(r["items"]) for r in data["models"].values())
        if saved < features[sid]["pool"]:
            invalid.append(sid)
            truncated_saved.append(saved)
        else:
            valid.append(sid)
    truncated_min = min(truncated_saved) if truncated_saved else None
    truncated_max = max(truncated_saved) if truncated_saved else None

    def lat_cost(sid: int, model: str) -> tuple[float, float]:
        data = load(ROUTER / f"session_{sid}.json")["models"][model]
        api = data.get("api") or {}
        price = PRICES[model]
        cost = (int(api.get("promptTokens") or 0) / 1e6 * price["input"]
                + int(api.get("completionTokens") or 0) / 1e6 * price["output"])
        return data.get("wallMs", 0) / 1000, cost

    def evaluate(pick, subset: list[int]) -> dict:
        vals, walls, costs = [], [], []
        for sid in subset:
            model = pick(sid)
            if model not in scores[str(sid)]:
                continue
            vals.append(scores[str(sid)][model])
            if model in ("qwen3.7-flash", "qwen3.8-flash", "qwen3.7-max"):
                wall, cost = lat_cost(sid, model)
                walls.append(wall)
                costs.append(cost)
        return {
            "judgeAll20": round(statistics.mean(vals), 2) if subset == sessions_int else None,
            "mean": round(statistics.mean(vals), 2),
            "min": round(min(vals), 2),
            "wallP50S": round(statistics.median(walls), 1) if walls else None,
            "costCny": round(statistics.mean(costs), 3) if costs else None,
            "n": len(vals),
        }

    def pick_fn(name: str):
        return lambda sid: rule_of(features[sid], name)

    strategies = []
    for name, policy in (("cheapOnly", "纯便宜：全部走 Qwen 3.7 Flash"),
                         ("flash38Only", "全部走 Qwen 3.8 Flash"),
                         ("softN", "softN≥2 → 3.8 Flash，其余 → 3.7 Flash"),
                         ("softN_hardN", "softN≥2 → 3.8 Flash；hardN≥4 → 3.7 Max；其余 → 3.7 Flash")):
        all20 = evaluate(pick_fn(name), sessions_int)
        clean = evaluate(pick_fn(name), valid)
        strategies.append({
            "policy": policy,
            "key": name,
            "judgeAll20": all20["mean"],
            "judgeAll20Min": all20["min"],
            "judgeClean16": clean["mean"],
            "judgeClean16Min": clean["min"],
            "costCny": all20["costCny"],
            "wallP50S": all20["wallP50S"],
        })

    # Borda merge of the two flash models (parallel wall assumption)
    merge_all, merge_clean, merge_costs, merge_walls = [], [], [], []
    for sid in sessions_int:
        key = str(sid)
        if "BordaMerge(3.7f+3.8f)" not in scores[key]:
            continue
        value = scores[key]["BordaMerge(3.7f+3.8f)"]
        merge_all.append(value)
        if sid in valid:
            merge_clean.append(value)
        w1, c1 = lat_cost(sid, "qwen3.7-flash")
        w2, c2 = lat_cost(sid, "qwen3.8-flash")
        merge_walls.append(max(w1, w2))
        merge_costs.append(c1 + c2)
    strategies.append({
        "policy": "Borda 融合：3.7 Flash + 3.8 Flash 排名合并（并行）",
        "key": "bordaMerge",
        "usesMax": False,
        "judgeAll20": round(statistics.mean(merge_all), 2),
        "judgeAll20Min": round(min(merge_all), 2),
        "judgeClean16": round(statistics.mean(merge_clean), 2),
        "judgeClean16Min": round(min(merge_clean), 2),
        "costCny": round(statistics.mean(merge_costs), 3),
        "wallP50S": round(statistics.median(merge_walls), 1),
    })

    # baseline + LOO
    base_all = evaluate(lambda sid: "qwen3.7-max", sessions_int)
    base_clean = evaluate(lambda sid: "qwen3.7-max", valid)
    report = load(ROUTER / "router_report.json") if (ROUTER / "router_report.json").exists() else {}
    loo_mean = report.get("looMean")

    for s in strategies:
        s.setdefault("usesMax", s["key"] == "softN_hardN")

    # 结论由聚合值算出，不写死
    nomax = [s for s in strategies if not s["usesMax"]]
    best_nomax = max(nomax, key=lambda s: s["judgeClean16"])
    gap_clean = round(base_clean["mean"] - best_nomax["judgeClean16"], 2)
    gap_all = round(base_all["mean"] - best_nomax["judgeAll20"], 2)
    withmax = [s for s in strategies if s["usesMax"]]
    gap_clean_withmax = round(base_clean["mean"] - withmax[0]["judgeClean16"], 2) if withmax else None
    margin = 0.5

    def phrase(gap: float) -> str:
        return f"达标（差 {gap:.2f} ≤ 界限 {margin:.1f}）" if gap <= margin else f"未达标（差 {gap:.2f} > 界限 {margin:.1f}）"

    verdict = (
        f"不用 max 的最优策略（按干净子集）是「{best_nomax['policy']}」：干净子集 {best_nomax['judgeClean16']:.2f} 对基线 "
        f"{base_clean['mean']:.2f}，{phrase(gap_clean)}；全集口径差 {gap_all:.2f}，{phrase(gap_all)}。"
        f"成本仅为基线的 {best_nomax['costCny'] / base_all['costCny'] * 100:.0f}%。"
        + (f"允许在 hardN≥4 时调用 max 的变体差 {gap_clean_withmax:.2f} 分（该策略已不属于「不用 max」）。"
           if gap_clean_withmax is not None else "")
        + f"以「打平 max」为目标不成立；以「接近 max」为目标则取决于预先设定的非劣界限——"
        f"本页把界限设为 {margin:.1f} 分并给出两种口径的通过情况；规则为事后提出，定论仍需独立 holdout。"
    )
    return {
        "caliber": "20 条真实审计会话（脱敏），冻结召回池，逐 shard 精排；判定 = 独立模型盲评（0–10，2 轮/会话）",
        "baseline": {
            "modelId": "qwen3.7-max",
            "alias": ALIAS["qwen3.7-max"],
            "judgeAll20": base_all["mean"],
            "judgeAll20Min": base_all["min"],
            "judgeClean16": base_clean["mean"],
            "judgeClean16Min": base_clean["min"],
            "costCny": base_all["costCny"],
            "wallP50S": base_all["wallP50S"],
        },
        "strategies": strategies,
        "cleanSubsetN": len(valid),
        "truncatedSessions": len(invalid),
        "truncatedRange": {"min": truncated_min, "max": truncated_max},
        "looMean": loo_mean,
        "bestNoMaxKey": best_nomax["key"],
        "nonInferiority": {
            "margin": margin,
            "gapClean16": gap_clean,
            "gapAll20": gap_all,
            "passesClean16": gap_clean <= margin,
            "passesAll20": gap_all <= margin,
            "note": "「接近 max」是否算成功取决于预先设定的非劣界限；本页不代替该业务判断，只给出两种口径下的差距。",
        },
        "verdict": verdict,
        "judgeNoiseNote": "同一 prompt 重跑，单场 Qwen 3.7 Flash 的判定在 9/8 与 3/4 之间翻转；"
                          "单轮 1 分级别的差异不可解读为模型优劣。",
        "postHocNote": "softN 分流规则是在看过这批会话之后提出的，leave-one-out 不能消除规则族的选择偏差；"
                       "落地前需要在预先冻结规则与预先设定非劣界限的前提下，用独立 holdout 会话复验。",
        "oracleNote": "上限参考：逐会话取最优模型（oracle）显著高于任一固定策略，说明信息存在但当前可计算的"
                      "特征尚不足以稳定地利用它。",
    }


def main() -> None:
    compat = load(BENCH / "compat_probe.json")
    models, calibration = build_models()
    judge7 = load(BENCH / "judge.json")
    judge_rounds = max(len(v) for v in judge7.values())
    pool_size = max(load(BENCH / f"session_{s}.json")["poolInfo"]["poolSize"] for s in judge7)
    for row in models:
        probe = compat["results"].get(row["modelId"], {})
        row["compatibility"] = {
            "productionShape": probe.get("prodStrictSchema", {}).get("status"),
            "schemaNoUniqueItems": probe.get("schemaNoUniqueItems", {}).get("status"),
            "jsonObject": probe.get("jsonObject", {}).get("status"),
        }
        if row["modelId"] == "deepseek-v4.1-flash":
            row["conclusion"] = "理由幻觉与偶发 400（两轮 124 shard 挂 8）；不建议替换现役。"
        elif row["modelId"] == "qwen3.7-max":
            row["conclusion"] = "质量最稳（无低于 7 的轮次），但单次成本约为 Qwen 3.7 Flash 的 57 倍。"
        elif row["modelId"] == "qwen3.8-flash":
            row["conclusion"] = "弱池排序最正确，但结构化条件场景会误标院校；成本约为 3.7 Flash 的 3.9 倍。"
        elif row["modelId"] == "qwen3.7-flash":
            row["conclusion"] = "单次成本最低（约为基线的 1/57）；结构化条件场景最强，但弱池上复现现役的评分虚高与模板化理由。"
        elif row["modelId"] == "qwen3.7-plus":
            row["conclusion"] = "全场景中庸、无重大缺陷；适合作为中间档观察。"
        elif row["modelId"] == "qwen3.8-max-0902":
            row["conclusion"] = "与 3.7 Max 同价位但结构化场景表现明显更差。"
        elif row["modelId"] == "qwen3.6-flash":
            row["conclusion"] = "现役对照：弱池评分失真最严重（理由自述不相关却给 0.95），延迟最低。"

    payload = {
        "schema": "rerank-model-selection/v1",
        "experimentDate": "2026-10-08",
        "scope": "生产检索链路的 LLM 精排（rerank）模型选型与路由回测；离线冻结召回池；"
                 "与 NL2IR 解析评测无关，两者不得混入同一组图。",
        "primaryMetric": "judgeScore10",
        "track": {
            "frozenRecallPools": True,
            "judge": f"独立评审模型盲评（匿名乱序，{judge_rounds} 轮/会话，排序合理性 + 理由质量，0–10）",
            "shardSize": 8,
            "poolSize": pool_size,
            "judgeRounds": judge_rounds,
            "costCaliber": "实测 token × 公开价目（元/百万 tokens）；不含缓存命中折扣",
            "noPerItemData": "不发布 query、候选人、逐题输出或任何可还原评测集的标识",
        },
        "priceList": {"date": PRICE_DATE, "source": PRICE_SOURCE, "unit": "元/百万 tokens", "entries": PRICES},
        "models": models,
        "wallRangeS": {
            "min": min(m["wallP50S"] for m in models),
            "max": max(m["wallP50S"] for m in models),
        },
        "calibration": calibration,
        "router": build_router(),
        "limitations": [
            "单库单时间段的小样本（路由回测 20 条会话；模型对比 3 条会话），来自同一公司同一审计库，不可外推为线上整体效果。",
            "判定为单一评审模型（qwen3-max），未做第二评审交叉验证；同 prompt 重跑存在翻转，±1 分级差异不可解读。",
            "路由规则为看数据后提出（post-hoc），leave-one-out 不能消除规则族选择偏差；需要预先冻结规则 + 独立 holdout 复验。",
            "4 场会话的候选名单被生产校准（hard-fail）过滤截断，judge 只看到 2–22 人；全集数字因此偏高。",
            "成本按公开价目当日折扣价计算，且未计入隐式缓存命中；实际账单会低于表中数字。",
            "0.75 合格线不可平移（校准代际差），阈值迁移与排名分位方案尚未验证。",
            "生产调用形态（strict JSON Schema 含 uniqueItems）下 3.7/3.8 全系 400，deepseek 不支持 json_schema；启用前必须改代码。",
        ],
        "provenance": {
            "evaluatedBy": "内部离线评估（semantic-search-service 精排基准脚本；冻结池复现与审计记录逐条一致）",
            "codexReview": {
                "date": "2026-10-08",
                "scope": "独立复核回测结论：复算全部数字一致；指出候选名单截断、冻结池未持久化、计数竞态与缺现役对照",
                "effect": "结论由「router 与 max 持平」下调为「证据不足，需 holdout」",
            },
            "artifacts": [
                "内部工件（未随站发布）：7 模型对比（3 会话）+ 20 会话路由回测的逐场分数与用量记录",
            ],
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"written {OUT}")
    for row in models:
        print(f"  {row['alias']:24s} judge={row['judgeScore10']:5.2f} ¥/次={row['costPerSearchCny']:.4f} "
              f"wallP50={row['wallP50S']}s prodShape={row['compatibility']['productionShape']}")
    r = payload["router"]
    print(f"  baseline(max) all20={r['baseline']['judgeAll20']} clean16={r['baseline']['judgeClean16']}")
    for s in r["strategies"]:
        print(f"  {s['policy'][:44]:46s} all20={s['judgeAll20']:5.2f} clean16={s['judgeClean16']} ¥={s['costCny']}")


if __name__ == "__main__":
    main()
