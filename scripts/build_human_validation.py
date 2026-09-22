#!/usr/bin/env python3
"""Build data/human_validation.json from the frozen blinded re-annotation sources.

Provenance (authoritative inputs, held outside this repository):
  - NL2IR_222_FINAL_BLINDED_REANNOTATION_REPORT.md
  - NL2IR_222_FINAL_THREE_WAY_COMPARISON.csv
  - NL2IR_18_HUMAN_AGENT_DISAGREEMENTS.csv
  - NL2IR_ACL_complete_manuscript_v0.8_2026-09-22.docx (Tables 2 and B2)

The script is the only place that touches the raw per-row files. Its output is
the public-safe aggregate the site consumes, so the published page never
depends on any gitignored or internal artifact.

Privacy: source_key (model identity) and source_sample_id (internal dataset
paths) are read for validation only and are NEVER written to the output.
Free-text annotation reasons are replaced by sanitized mechanism summaries so
that no request text, contract text, IR, or internal identifier is published.

Every count is asserted against the numbers frozen in the report and the
manuscript; a mismatch aborts the build instead of publishing silently.
"""
from __future__ import annotations

import csv
import json

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "human_validation.json"
SRC = Path.home() / "Downloads"
THREE_WAY = SRC / "NL2IR_222_FINAL_THREE_WAY_COMPARISON.csv"
DISAGREEMENTS = SRC / "NL2IR_18_HUMAN_AGENT_DISAGREEMENTS.csv"

N_POPULATION = 222

# ---------------------------------------------------------------------------
# Frozen numbers from the report and manuscript Tables 2 / B2.
# ---------------------------------------------------------------------------
FROZEN = {
    "human_positive": 177,
    "human_negative": 45,
    "human_rate": 79.73,
    "wilson95": [73.96, 84.49],
    "cp95": [73.83, 84.81],
    "unsure_component_level": 3,
    "sensitivity_positive": 177,
    "sensitivity_n": 219,
    "sensitivity_rate": 80.82,
    "agent_positive": 165,
    "agent_negative": 57,
    "agent_rate": 74.32,
    "headline_agree": 204,
    "headline_rate": 91.89,
    "headline_kappa": 0.772,
    "applicability_agree": 177,
    "applicability_rate": 79.73,
    # Recomputed from the frozen 222-row table. The manuscript's Table B2 printed
    # 0.221 here and 0.777 on the violation row; neither reproduces. The violation
    # row cannot differ from the headline row at all, because the two are the same
    # binary decision on all 222 rows and therefore share one 2x2 table:
    #     162 / 15 / 3 / 42  ->  po = 0.918919, pe = 0.644631, kappa = 0.7718
    # Cohen's kappa is a function of that table alone, so a single table cannot
    # yield both 0.772 and 0.777. Both values below are asserted, not copied.
    "applicability_kappa": 0.203,
    "violation_agree": 204,
    "violation_rate": 91.89,
    "violation_kappa": 0.772,
    # Applicability-layer disagreement split, recomputed from the frozen table.
    # 45 rows differ at this layer, in two directions: 33 are human=no /
    # agent=yes and 12 are human=yes / agent=no. Of the 45, 30 still land on the
    # same headline because both sides judge negative for different stated
    # reasons; the remaining 15 (12 + 3) become headline disagreements.
    "applicability_disagree": 45,
    "mid_layer_same_headline": 30,
    "mid_layer_human_yes_agent_no": 12,
    "mid_layer_human_no_agent_yes": 33,
    # Where the 18 headline disagreements originate.
    "disagreement_from_applicability": 15,
    "disagreement_from_violation": 3,
    "legacy_mrf_agree": 207,
    "legacy_mrf_rate": 93.24,
    "legacy_mrf_kappa": 0.786,
    "legacy_m_agree": 186,
    "legacy_m_rate": 83.78,
    "legacy_m_kappa": 0.563,
    "legacy_m_yes": 159,
    "legacy_m_rate_of_population": 71.62,
    "legacy_mrf_yes": 180,
    "legacy_mrf_rate_of_population": 81.08,
    "confusion": {"yy": 162, "yn": 15, "ny": 3, "nn": 42},
    "disagreements": {"human_yes_agent_no": 15, "human_no_agent_yes": 3},
    # Detailed attribution, manuscript section 4.1.
    "attribution": {"M": 159, "representation": 12, "json_schema": 9, "ambiguity": 15, "gold_scoring": 27},
}

# ---------------------------------------------------------------------------
# Sanitized mechanism summaries, keyed by annotation id.
# Deliberately generic: no query text, no company/tenant data, no identifiers.
# ---------------------------------------------------------------------------
MECHANISMS = {
    "boundary": "连续量边界方向",
    "invalid-json": "输出不是合法 JSON",
    "over-constrain": "过度约束 / 擅加条件",
    "missing-requirement": "遗漏条款明确要求",
    "ambiguous-contract": "契约未定义或存在歧义",
}

SANITIZED = {
    # --- human positive / agent negative -------------------------------------
    "H014": ("boundary",
             "边界排除方向错误：生成用包含式上界，保留了本应被排除的边界值；按条款应改为对下界取反。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H018": ("invalid-json",
             "源输出不是合法 JSON，无法构成契约要求的合法 AST，因此违反了输出契约。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    "H035": ("boundary",
             "边界方向错误：生成用包含式上界保留了本应排除的边界值；参考侧取值同样不符合连续量规则。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H050": ("boundary",
             "生成用对下界取反，反而排除了恰好等于阈值的记录；该阈值本身应为包含式上界。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H067": ("boundary",
             "生成用等值匹配替代了下界约束；双方共有的空窗上界同样不符合连续量规则。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H072": ("over-constrain",
             "请求只排除了某一细分渠道，生成擅自补入了请求未规定的近义或下位词，违反不得增补未规定别名的规则。",
             "认为该条款适用且生成结果遵循了该条款，所显示的差异不构成违反。"),
    "H102": ("missing-requirement",
             "条款明确要求的最小匹配数约束缺失。仅凭该项即可判违反，不依赖单元素 all 与等值之间的争议。",
             "认为该条款适用且生成结果遵循了该条款，所显示的差异不构成违反。"),
    "H103": ("invalid-json",
             "源输出不是合法 JSON，无法构成契约要求的合法 AST，因此违反了输出契约。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    "H119": ("boundary",
             "生成用对下界取反，排除了恰好等于阈值的记录；按条款应为包含式上界。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H135": ("invalid-json",
             "源输出不是合法 JSON，无法构成契约要求的合法 AST，因此违反了输出契约。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    "H148": ("over-constrain",
             "偏好性表述被并入 required=true 的合取条件，偏好被硬化成了必填要求。",
             "认为该条款适用且生成结果遵循了该条款，所显示的差异不构成违反。"),
    "H155": ("invalid-json",
             "源输出不是合法 JSON，无法构成契约要求的合法 AST，因此违反了输出契约。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    "H162": ("boundary",
             "条款的阈值含边界，生成却把下界加一，违反含边界且不得加一的规则。",
             "认为该条款并未明确管辖所显示的差异，因此该差异不构成对该条款的违反。"),
    "H181": ("invalid-json",
             "原始文本虽非合法 JSON，但否定只包裹了其中一项、其余项另作肯定条件已明确可见，违反完整复合排除规则。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    "H184": ("invalid-json",
             "源输出不是合法 JSON，无法构成契约要求的合法 AST，因此违反了输出契约。",
             "没有可用生成结果，也未检索到明确条款，认为两个判断都无法由该证据包支持。"),
    # --- human negative / agent positive ------------------------------------
    "H092": ("ambiguous-contract",
             "契约未解决某一岗位名是否必须转写为职位，以及该经历指职位还是业务背景；参考标签未必权威。",
             "认为条款要求把所述既往角色编码为职位，而生成遗漏或将该角色路由进了语义字段。"),
    "H151": ("ambiguous-contract",
             "契约未定义名称模式中用户给出的下划线是字面数据还是通配语法。",
             "认为条款要求原样保留所述名称模式的字符，而生成丢弃了该字符。"),
    "H189": ("ambiguous-contract",
             "某一领域经验既可指结构化技能，也可指产品或业务背景；契约未要求唯一表示。",
             "认为条款管辖具名工具与技术的技能路由并排除泛化经验或特质，而生成遗漏或错误路由了该内容。"),
}

def fail(msg: str) -> None:
    print(f"ABORT: {msg}", file=sys.stderr)
    raise SystemExit(1)

def check(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)

def binz(v: str) -> str:
    """Frozen derivation: only an explicit yes is positive; unsure is negative."""
    return "yes" if v == "yes" else "no"

def pct(n: int, d: int) -> float:
    return round(n / d * 100, 2)

def kappa(yy: int, yn: int, ny: int, nn: int) -> float:
    n = yy + yn + ny + nn
    po = (yy + nn) / n
    yes_a, no_a = yy + yn, ny + nn
    yes_b, no_b = yy + ny, yn + nn
    pe = (yes_a / n) * (yes_b / n) + (no_a / n) * (no_b / n)
    return round((po - pe) / (1 - pe), 3)

def load_rows(path: Path) -> list[dict]:
    check(path.exists(), f"缺少权威输入 {path}")
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))

def main() -> int:
    rows = load_rows(THREE_WAY)
    check(len(rows) == N_POPULATION, f"三向表行数 {len(rows)} != {N_POPULATION}")

    for col in ("human_headline", "agent_headline", "legacy_m_only_headline", "legacy_explicit_rule_headline"):
        vals = {r[col] for r in rows}
        check(vals <= {"yes", "no"}, f"{col} 存在非二元值: {vals}")

    human_pos = sum(1 for r in rows if r["human_headline"] == "yes")
    agent_pos = sum(1 for r in rows if r["agent_headline"] == "yes")
    legacy_m = sum(1 for r in rows if r["legacy_m_only_headline"] == "yes")
    legacy_mrf = sum(1 for r in rows if r["legacy_explicit_rule_headline"] == "yes")

    # ---- number relationships the brief requires ---------------------------
    check(human_pos + FROZEN["human_negative"] == N_POPULATION, "177 + 45 != 222")
    check(agent_pos + FROZEN["agent_negative"] == N_POPULATION, "165 + 57 != 222")
    check(human_pos == FROZEN["human_positive"], f"human positive {human_pos} != 177")
    check(agent_pos == FROZEN["agent_positive"], f"agent positive {agent_pos} != 165")
    check(legacy_m == FROZEN["legacy_m_yes"], f"legacy M {legacy_m} != 159")
    check(legacy_mrf == FROZEN["legacy_mrf_yes"], f"legacy M/R/F {legacy_mrf} != 180")
    check(pct(human_pos, N_POPULATION) == FROZEN["human_rate"], "human rate != 79.73")
    check(pct(agent_pos, N_POPULATION) == FROZEN["agent_rate"], "agent rate != 74.32")
    check(pct(legacy_m, N_POPULATION) == FROZEN["legacy_m_rate_of_population"], "legacy M rate != 71.62")
    check(pct(legacy_mrf, N_POPULATION) == FROZEN["legacy_mrf_rate_of_population"], "legacy M/R/F rate != 81.08")

    # ---- headline 2x2 ------------------------------------------------------
    yy = sum(1 for r in rows if r["human_headline"] == "yes" and r["agent_headline"] == "yes")
    yn = sum(1 for r in rows if r["human_headline"] == "yes" and r["agent_headline"] == "no")
    ny = sum(1 for r in rows if r["human_headline"] == "no" and r["agent_headline"] == "yes")
    nn = sum(1 for r in rows if r["human_headline"] == "no" and r["agent_headline"] == "no")
    c = FROZEN["confusion"]
    check((yy, yn, ny, nn) == (c["yy"], c["yn"], c["ny"], c["nn"]),
          f"混淆矩阵 {(yy, yn, ny, nn)} != {(c['yy'], c['yn'], c['ny'], c['nn'])}")
    check(yy + yn + ny + nn == N_POPULATION, "162+15+3+42 != 222")
    check(pct(yy + nn, N_POPULATION) == FROZEN["headline_rate"], "agreement != 91.89")
    check(kappa(yy, yn, ny, nn) == FROZEN["headline_kappa"], "kappa != 0.772")

    # ---- component-level agreement (unsure derives to negative) ------------
    def agree2(kind: str) -> tuple[int, float]:
        pairs = [(binz(r[f"human_{kind}"]), binz(r[f"agent_{kind}"])) for r in rows]
        a = sum(1 for h, g in pairs if h == "yes" and g == "yes")
        b = sum(1 for h, g in pairs if h == "yes" and g == "no")
        cc = sum(1 for h, g in pairs if h == "no" and g == "yes")
        d = sum(1 for h, g in pairs if h == "no" and g == "no")
        check(a + b + cc + d == N_POPULATION, f"{kind} 2x2 合计 != 222")
        return a + d, kappa(a, b, cc, d)

    app_agree, app_kappa = agree2("rule")
    vio_agree, vio_kappa = agree2("violation")
    check(app_agree == FROZEN["applicability_agree"], f"applicability agree {app_agree} != 177")
    check(vio_agree == FROZEN["violation_agree"], f"violation agree {vio_agree} != 204")
    check(app_kappa == FROZEN["applicability_kappa"], f"applicability kappa {app_kappa} != 0.203")
    check(vio_kappa == FROZEN["violation_kappa"], f"violation kappa {vio_kappa} != 0.772")

    # The violation layer is the same binary decision as the headline on every
    # row, so both reduce to one 2x2 table and must yield one kappa. Asserting
    # this makes the manuscript's 0.777 / 0.772 pairing unbuildable.
    headline_pairs = [(binz(r["human_headline"]), binz(r["agent_headline"])) for r in rows]
    violation_pairs = [(binz(r["human_violation"]), binz(r["agent_violation"])) for r in rows]
    check(violation_pairs == headline_pairs, "违反层与 headline 层不是同一个判断")
    check(vio_kappa == FROZEN["headline_kappa"], "同一张 2x2 表却得出不同的 kappa")
    check(app_agree + FROZEN["applicability_disagree"] == N_POPULATION, "177 + 45 != 222")

    # ---- mid-layer disagreement split --------------------------------------
    mid = [r for r in rows if binz(r["human_rule"]) != binz(r["agent_rule"])]
    check(len(mid) == FROZEN["applicability_disagree"], f"中间层分歧 {len(mid)} != 45")
    check(sum(1 for r in mid if binz(r["human_headline"]) == binz(r["agent_headline"]))
          == FROZEN["mid_layer_same_headline"], "中间层结论仍相同的 != 30")
    check(sum(1 for r in mid if binz(r["human_rule"]) == "yes" and binz(r["agent_rule"]) == "no")
          == FROZEN["mid_layer_human_yes_agent_no"], "中间层 human yes/agent no != 12")
    check(sum(1 for r in mid if binz(r["human_rule"]) == "no" and binz(r["agent_rule"]) == "yes")
          == FROZEN["mid_layer_human_no_agent_yes"], "中间层 human no/agent yes != 3")

    # ---- legacy comparison agreement ---------------------------------------
    def legacy_agree(col: str) -> int:
        return sum(1 for r in rows if r["human_headline"] == r[col])

    check(legacy_agree("legacy_explicit_rule_headline") == FROZEN["legacy_mrf_agree"], "M/R/F agree != 207")
    check(legacy_agree("legacy_m_only_headline") == FROZEN["legacy_m_agree"], "M-only agree != 186")

    # ---- unsure count and sensitivity --------------------------------------
    unsure = sum(1 for r in rows if "unsure" in (r["human_rule"], r["human_violation"]))
    check(unsure == FROZEN["unsure_component_level"], f"unsure {unsure} != 3")
    check(FROZEN["sensitivity_positive"] + (FROZEN["sensitivity_n"] - FROZEN["sensitivity_positive"])
          == FROZEN["sensitivity_n"], "sensitivity arithmetic")
    check(pct(177, 219) == FROZEN["sensitivity_rate"], "177/219 != 80.82")

    # ---- detailed attribution sums to the same 222 -------------------------
    attr = FROZEN["attribution"]
    check(sum(attr.values()) == N_POPULATION, f"归因分类合计 {sum(attr.values())} != 222")
    check(attr["M"] == legacy_m, "归因 M != 159")

    print(f"数字校验通过：human {human_pos}/222、agent {agent_pos}/222、"
          f"agreement {yy + nn}/222、混淆矩阵 {yy}/{yn}/{ny}/{nn}、legacy M {legacy_m}、M/R/F {legacy_mrf}")

    # ---- disagreements (sanitized) -----------------------------------------
    dis = load_rows(DISAGREEMENTS)
    check(len(dis) == 18, f"分歧行数 {len(dis)} != 18")
    d_hyn = sum(1 for r in dis if r["human_headline"] == "yes" and r["agent_headline"] == "no")
    d_nyy = sum(1 for r in dis if r["human_headline"] == "no" and r["agent_headline"] == "yes")
    check(d_hyn == FROZEN["disagreements"]["human_yes_agent_no"], f"human yes/agent no {d_hyn} != 15")
    check(d_nyy == FROZEN["disagreements"]["human_no_agent_yes"], f"human no/agent yes {d_nyy} != 3")
    check(d_hyn + d_nyy == 18, "15 + 3 != 18")

    # Which layer each headline disagreement comes from.
    from_app = sum(1 for r in dis if binz(r["human_rule"]) != binz(r["agent_rule"]))
    from_vio = sum(1 for r in dis
                   if binz(r["human_rule"]) == binz(r["agent_rule"])
                   and binz(r["human_violation"]) != binz(r["agent_violation"]))
    check(from_app == FROZEN["disagreement_from_applicability"],
          f"来自适用性层的分歧 {from_app} != 15")
    check(from_vio == FROZEN["disagreement_from_violation"],
          f"来自违反层的分歧 {from_vio} != 3")
    check(from_app + from_vio == 18, "分歧来源层合计 != 18")

    # cross-check: the disagreement file and the three-way file must agree
    head = {r["annotation_id"]: (r["human_headline"], r["agent_headline"]) for r in rows}
    for r in dis:
        aid = r["annotation_id"]
        check(aid in head, f"{aid} 不在三向表中")
        check(head[aid] == (r["human_headline"], r["agent_headline"]),
              f"{aid} 在两张表中的判定不一致")

    cases = []
    for r in dis:
        aid = r["annotation_id"]
        check(aid in SANITIZED, f"{aid} 缺少脱敏摘要")
        mech, human_reason, agent_reason = SANITIZED[aid]
        check(mech in MECHANISMS, f"{aid} 机制标签未知: {mech}")
        cases.append({
            "id": aid,
            "human": r["human_headline"],
            "agent": r["agent_headline"],
            "mechanism": MECHANISMS[mech],
            "humanReason": human_reason,
            "agentReason": agent_reason,
        })

    counts: dict[str, int] = {}
    for cse in cases:
        counts[cse["mechanism"]] = counts.get(cse["mechanism"], 0) + 1

    payload = {
        "title": "人工盲复核确认多数失败涉及明确规则",
        "titleEn": "Blinded Human Re-annotation of 222 Canonical-Where Failures",
        "population": {
            "n": N_POPULATION,
            "label": "冻结的 Canonical-Where 失败",
            "note": "六组冻结运行的完整 Where 失败集合（4B/9B × old366 / C300 / blind-v6），不是抽样。",
        },
        "headline": {
            "label": "人工判定存在明确且适用的规则被违反",
            "positive": human_pos,
            "negative": FROZEN["human_negative"],
            "n": N_POPULATION,
            "rate": FROZEN["human_rate"],
            "wilson95": FROZEN["wilson95"],
            "cp95": FROZEN["cp95"],
            "unsureComponentLevel": FROZEN["unsure_component_level"],
            "sensitivity": {
                "positive": FROZEN["sensitivity_positive"],
                "n": FROZEN["sensitivity_n"],
                "rate": FROZEN["sensitivity_rate"],
                "note": "3 条组件级 unsure 按冻结规则计为 headline 阴性；排除它们后的敏感性结果。",
            },
        },
        "agent": {
            "label": "最早封存的 blinded agent 判定",
            "positive": agent_pos,
            "negative": FROZEN["agent_negative"],
            "n": N_POPULATION,
            "rate": FROZEN["agent_rate"],
            "role": "辅助可靠性检查（auxiliary reliability check），不是人工一致性",
        },
        "agreement": {
            "headline": {"n": N_POPULATION, "agree": yy + nn, "rate": FROZEN["headline_rate"], "kappa": FROZEN["headline_kappa"]},
            "ruleApplicability": {"n": N_POPULATION, "agree": app_agree, "rate": FROZEN["applicability_rate"], "kappa": FROZEN["applicability_kappa"]},
            "ruleViolation": {"n": N_POPULATION, "agree": vio_agree, "rate": FROZEN["violation_rate"], "kappa": FROZEN["violation_kappa"]},
            "legacyMRF": {"n": N_POPULATION, "agree": FROZEN["legacy_mrf_agree"], "rate": FROZEN["legacy_mrf_rate"], "kappa": FROZEN["legacy_mrf_kappa"]},
            "legacyMOnly": {"n": N_POPULATION, "agree": FROZEN["legacy_m_agree"], "rate": FROZEN["legacy_m_rate"], "kappa": FROZEN["legacy_m_kappa"]},
        },
        "confusion": {
            "humanYesAgentYes": yy,
            "humanYesAgentNo": yn,
            "humanNoAgentYes": ny,
            "humanNoAgentNo": nn,
            "n": N_POPULATION,
        },
        "twoLayer": {
            "steps": [
                {"key": "applicability", "label": "规则是否明确且适用？", "agreement": FROZEN["applicability_rate"], "kappa": FROZEN["applicability_kappa"]},
                {"key": "violation", "label": "预测是否违反了该规则？", "agreement": FROZEN["violation_rate"], "kappa": FROZEN["violation_kappa"]},
            ],
            "rule": "两个判断均为 yes 时，headline 才为阳性；unsure 按冻结规则计为阴性。",
            "note": "中间判断的分歧明显更多（规则适用性），而最终 headline 仍有较强一致；只报最终一致率会掩盖组件层面的差异。",
        },
        "componentTable": {
            # 只列两个真正不同的层级。冻结数据里 legacy 的"是否违反规则"列与
            # headline 在 222 行上逐行相同，单独成行会与 headline 行一字不差地
            # 重复（同一张 2x2 表、同一个一致率、同一个 κ），因此不列出。
            "rows": [
                {
                    "key": "headline",
                    "label": "最终 headline（规则适用且被违反）",
                    "agree": yy + nn,
                    "n": N_POPULATION,
                    "rate": FROZEN["headline_rate"],
                    "kappa": FROZEN["headline_kappa"],
                    "tone": "headline",
                },
                {
                    "key": "applicability",
                    "label": "规则是否明确且适用",
                    "agree": app_agree,
                    "n": N_POPULATION,
                    "rate": FROZEN["applicability_rate"],
                    "kappa": FROZEN["applicability_kappa"],
                    "tone": "mid",
                    "note": "中间层一致率明显更低，差异集中在“规则是否适用”这一步。",
                },
            ],
            "omittedRow": {
                "label": "是否违反规则",
                "agree": vio_agree,
                "n": N_POPULATION,
                "rate": FROZEN["violation_rate"],
                "kappa": FROZEN["violation_kappa"],
                "reason": "该列与 headline 是同一个二元判断：222 行逐行相同，共用一张 2×2 表，一致率与 κ 都与 headline 相同，因此不单独列出。",
            },
            "midLayer": {
                "disagree": FROZEN["applicability_disagree"],
                "sameHeadline": FROZEN["mid_layer_same_headline"],
                "humanYesAgentNo": FROZEN["mid_layer_human_yes_agent_no"],
                "humanNoAgentYes": FROZEN["mid_layer_human_no_agent_yes"],
            },
            "disagreementOrigin": {
                "applicability": FROZEN["disagreement_from_applicability"],
                "violation": FROZEN["disagreement_from_violation"],
            },
        },
        "reconciliation": [
            {"key": "legacyM", "label": "旧详细归因 M 类", "yes": legacy_m, "rate": FROZEN["legacy_m_rate_of_population"],
             "scope": "较窄：只统计实质规则未执行", "binary": False, "tone": "legacyNarrow"},
            {"key": "legacyMRF", "label": "旧 M/R/F 二元口径", "yes": legacy_mrf, "rate": FROZEN["legacy_mrf_rate_of_population"],
             "scope": "二元 explicit-rule", "binary": True, "tone": "legacyWide"},
            {"key": "human", "label": "人工盲复核二元", "yes": human_pos, "rate": FROZEN["human_rate"],
             "scope": "二元 explicit-rule", "binary": True, "tone": "human"},
            {"key": "agent", "label": "最早封存 agent 二元", "yes": agent_pos, "rate": FROZEN["agent_rate"],
             "scope": "二元 explicit-rule", "binary": True, "tone": "agent"},
        ],
        "reconciliationNote": (
            "旧 159/222 是详细归因分类中的 M 类，只统计实质规则未执行；人工盲复核采用更宽的二元问题，"
            "也包含明确的 representation / schema 规则。因此 159 与 177 不能直接相减解释为“提升”。"
            "把旧 M/R/F 合并为同一口径后得到 180/222 的兼容基线，人工与旧口径的一致率为 93.24%（κ=0.786）。"
            "论文同时保留 159 的机制分类与 177 的人类二元验证。"
        ),
        "attribution": {
            "M": attr["M"],
            "representation": attr["representation"],
            "jsonSchema": attr["json_schema"],
            "ambiguity": attr["ambiguity"],
            "goldScoring": attr["gold_scoring"],
            "n": N_POPULATION,
        },
        "disagreementCounts": {
            "total": len(cases),
            "humanYesAgentNo": d_hyn,
            "humanNoAgentYes": d_nyy,
            "byMechanism": counts,
        },
        "disagreements": cases,
        "methodNotes": [
            "证据包只含匿名 ID、请求、相关的生成与参考 IR 片段、一个中性的结构差异说明，以及至多 5 条带位置的冻结契约条款；不含模型身份、seed、数据集名、旧标签、旧家族归属、agent 结论与裁决结果。",
            "人工复核者与最早封存的 agent 都在揭盲前独立完成“规则适用性 / 预测违反 / 置信度”三项判断。",
            "没有第二位人工标注者参与，因此这是 blinded human re-annotation，不是 human-human inter-annotator agreement。",
            "agent 对照使用最初封存的 222 行标注文件。后来一份第二遍替换文件被排除在一致性分析之外。",
            "组件层 κ 按冻结的 222 行表复算。违反规则层与 headline 层在 222 行上是同一个判断，共用一张 2×2 表，κ 同为 0.772；规则适用性层为 0.203。",
        ],
        "sourceNote": "聚合数字来自冻结的复标注报告与论文 Table 2 / Table B2；逐题原始材料与内部标识不随网站发布。",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写出 {OUT.relative_to(REPO)}（{OUT.stat().st_size} 字节，18 条脱敏分歧）")
    print(f"机制分布：{counts}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())