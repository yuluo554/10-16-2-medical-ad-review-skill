"""禁止情形核查（模块 3）。

**唯一实现源**：全部判定在此处，报告层不重算。

三条硬纪律：

1. **分派表结构 + 运行双层断言**（skill 定稿形态）：只断言"表里有三个键"是假门——
   分派表可以齐备而判定路径从不查它。故：① 结构层断言"表键集合与 kind 常量集合
   一一对应且各实现互不相同"；② 运行层对每个 kind 真跑一遍且不抛错；③ 变异自检
   （摘掉一个 kind → 必须报错）。
2. **词面/模式一律来自冻结规则包**：本模块零政策字面量（K9）。匹配规格是数据
   （``match.any_of`` / ``all_of`` / ``none_of`` / ``groups``），不是代码。
3. **否定辖域抑制**（M1 新增）：命中项若处于否定辖域内（同一句读段内、命中项之前
   出现否定词），**不算命中**——否则会把法条**强制要求的免责语**报成违法
   （免责语恰含被禁词面）。否定词表是语言层构造（见 ``constants.NEGATION_MARKERS``）。
"""

from __future__ import annotations

from . import constants
from . import phrase
from .model import Finding, RuleResult

# 词面匹配原语**共用唯一实现源**（``phrase`` 模块）——规则核查与品类判定
# 必须用同一份"是否有效命中"的判据，否则同一份语义在两处各写一份即漂移源。
# 保留私有别名是为了让既有调用点与测试零改动（改名会打断 M1 的守门断言）。
_is_negated = phrase.is_negated
_excluded_context = phrase.excluded_context
_term_is_live = phrase.term_is_live
_any_of = phrase.any_of
_all_of = phrase.all_of
_none_of = phrase.none_of


def match_rule(rule, match_spec, text):
    """通用匹配：返回命中项列表（空 = 未命中）。

    ``match_spec`` 结构：``{"any_of": [...], "all_of": [...], "none_of": [...],
    "groups": [[...], [...]], "segment_groups": [[...], [...]]}``——全部字段可选；
    各字段之间是**与**关系（any_of 命中 && all_of 全中 && none_of 全空 &&
    每个 group 至少命中一项 && 每个 segment_group 至少命中一项）。

    ``groups`` 是**共现语义**：每组的词表是"任一即可"，但**组与组之间必须同时
    成立**（如某条要求"主体词"与"证明标记"共现，光有主体词不算）。

    ``segment_groups`` 是**同段共现**（比 ``groups`` 更严）：各组的命中必须落在
    **同一个句读段**内。用途：原文的构成要件是"**同一句**里出现了比较标记与被
    比较对象"时，全局共现会把**分属两句**的词面凑成一次命中（如"本院技术更好。
    另售其他商品。"被读成"更好 + 其他商品"的比较），同段共现能拦住这类凑合。

    ``exclude_contexts``（可选，顶层）是**排除语境**词表：命中项若落在这些更大
    词形内部即不算命中（防裸词与中性词形碰撞）。
    """
    spec = match_spec or {}
    contexts = spec.get("exclude_contexts") or ()
    any_hits = _any_of(text, spec.get("any_of") or (), contexts)
    all_hits = _all_of(text, spec.get("all_of") or (), contexts)
    none_hits = _none_of(text, spec.get("none_of") or (), contexts)

    group_hits = []
    for group in spec.get("groups") or ():
        hits = _any_of(text, group or (), contexts)
        if not hits:
            return []
        group_hits.extend(hits)

    segment_groups = spec.get("segment_groups") or ()
    segment_hits = []
    if segment_groups:
        segment_hits = phrase.cooccur_in_segment(text, segment_groups, contexts)
        if not segment_hits:
            return []

    if spec.get("all_of") and not all_hits:
        return []
    if none_hits:
        return []
    if spec.get("any_of") and not any_hits:
        return []
    if spec.get("groups") and not group_hits:
        return []
    if not (spec.get("any_of") or spec.get("all_of") or spec.get("groups")
            or spec.get("segment_groups")):
        # 没有正向条件 = 规格缺失，绝不"空规格恒命中"
        return []
    return any_hits + all_hits + group_hits + segment_hits


def _check_prohibited_term(rule, match_spec, text, proof=None):
    hits = match_rule(rule, match_spec, text)
    if not hits:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, hit, rule.severity, rule.kind)
        for hit in hits
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_prohibited_pattern(rule, match_spec, text, proof=None):
    """结构性禁止模式（共现/顺序类）——与 prohibited_term 共用匹配器但语义独立。

    **逐命中项各出一条 Finding**（不把多项 join 成一个字符串）：join 出来的
    "A、B" 并不是文案里的片段，会让"evidence 逐字在文案"的导出前断言无法成立
    （M3 实测：某条规则把两个命中词 join 成一个串，导出前断言当场报红）。
    逐项出条既保住可核验性，也让报告能逐词指认。
    """
    hits = match_rule(rule, match_spec, text)
    if not hits:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, hit,
                rule.severity, rule.kind)
        for hit in hits
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_mandatory_disclosure(rule, match_spec, text, proof=None):
    """**无条件义务**：必须出现某提示语；缺失 → noncompliant（绝不记成"不适用"）。

    ``match_spec.require_all_of`` 是"每一组内至少出现一个"的列表；缺任一组即命中。
    提示语本身也过否定辖域抑制——**否定形态的表述**不算已履行标明义务
    （否则"我没写"会被读成"我写了"）。
    """
    spec = match_spec or {}
    groups = spec.get("require_all_of") or []
    if not groups:
        # 没有可判定的义务组 = 规格缺失，记 input_required 而非猜
        return RuleResult(rule.rule_id, constants.RULE_INPUT_REQUIRED, (),
                          "规则缺 require_all_of 规格，无法判定")
    missing = []
    for group in groups:
        if not _any_of(text, group):
            missing.append(group)
    if not missing:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote,
                "缺失应显著标明的内容（第 %d 组）" % (idx + 1),
                rule.severity, rule.kind,
                evidence_kind=constants.EVIDENCE_OBLIGATION_MISSING)
        for idx, _ in enumerate(missing)
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_whitelist_scope(rule, match_spec, text, proof=None):
    """超出白名单范围的表述 → warn（非明确禁止）。

    同样**逐命中项各出一条 Finding**（join 出的 "A、B" 不是文案片段，
    过不了"evidence 逐字在文案"的导出前断言）。
    """
    hits = match_rule(rule, match_spec, text)
    if not hits:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, hit,
                rule.severity, rule.kind)
        for hit in hits
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_variant_publish(rule, match_spec, text, proof=None):
    """变相发布情形：知识形态 + 商品/服务信息**共现**（条款号见规则锚点）。

    证据**逐命中项各出一条**：共现是判定条件，但引证必须是文案里的逐字片段
    （join 出来的串过不了导出前断言）。
    """
    spec = match_spec or {}
    knowledge = _any_of(text, spec.get("knowledge_terms") or ())
    commerce = _any_of(text, spec.get("commerce_terms") or ())
    if not (knowledge and commerce):
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, hit,
                rule.severity, rule.kind)
        for hit in (knowledge + commerce)
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_input_required(rule, match_spec, text, proof=None):
    """判定需外部材料（许可/审查/批准类证明，具体项见规则的 required_input）。

    **绝不静默判 compliant，也绝不猜**——材料缺失一律记 input_required，
    由报告"待补材料"节显式索要。
    """
    note = (match_spec or {}).get("required_input") or "需外部材料"
    return RuleResult(rule.rule_id, constants.RULE_INPUT_REQUIRED, (), note)


def _check_review_proof(rule, match_spec, text, proof=None):
    """审查证明三态（**可判定的第三态**，不是"缺材料"垃圾桶）。

    依据事前审查要求（条款锚点见规则）：须经审查的品类，
    **未经审查不得发布**。三态语义：

    - ``proof == "no"``（用户明确表示未取得）→ **noncompliant**（无条件义务缺失，
      不许记成"不适用"）；
    - ``proof`` 未提供 → ``input_required``（**绝不静默判 compliant**）；
    - ``proof == "yes"`` → compliant（已声明取得；实质核验仍需审查证明原件，
      报告在待补材料节保留提示）。
    """
    value = (proof or "").strip().lower()
    if value in ("no", "none", "false", "未取得", "否"):
        findings = [
            Finding(rule.rule_id, rule.anchor, rule.quote,
                    "用户声明未取得广告审查证明（未经审查不得发布）",
                    rule.severity, rule.kind,
                    evidence_kind=constants.EVIDENCE_OBLIGATION_MISSING)
        ]
        return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)
    if value in ("yes", "true", "已取得", "是"):
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT, (),
                          "用户声明已取得审查证明（实质核验以审查证明原件为准）")
    return RuleResult(rule.rule_id, constants.RULE_INPUT_REQUIRED, (),
                      (match_spec or {}).get("required_input") or "需外部材料")


# ---- 分派表（结构层断言的对象） ----
DISPATCH = {
    constants.KIND_PROHIBITED_TERM: _check_prohibited_term,
    constants.KIND_PROHIBITED_PATTERN: _check_prohibited_pattern,
    constants.KIND_MANDATORY_DISCLOSURE: _check_mandatory_disclosure,
    constants.KIND_WHITELIST_SCOPE: _check_whitelist_scope,
    constants.KIND_VARIANT_PUBLISH: _check_variant_publish,
    constants.KIND_INPUT_REQUIRED: _check_input_required,
    constants.KIND_REVIEW_PROOF: _check_review_proof,
}


def rule_applies(rule, categories, scenario=None, text=""):
    """适用域判定：品类交集 **且** 情形命中 **且** 主体信号命中才适用。

    三维都来自**原文自带的主体/情形限制**——任一维不成立 → ``skipped``
    （这是"不适用"的**唯一合法来源**："我没看到材料"或"用户没做"**不算**不适用）。

    ``subject_signals`` 的用途：原文只对**特定主体**设的义务（如某细分品类的
    提示语义务），若本文案不含该主体信号 → 该义务条**不适用**（skipped），
    而不是"缺失 → 判命中"。把"不适用"和"该写没写"混为一谈会把非该主体的文案
    误报为违规。
    """
    rule_cats = set(rule.categories)
    if not rule_cats:
        return False
    if not (rule_cats & set(categories)):
        return False
    rule_scenarios = set(rule.scenarios)
    if rule_scenarios and scenario not in rule_scenarios:
        return False
    signals = rule.subject_signals
    if signals:
        if not any(s and s in text for s in signals):
            return False
        # 排除词命中 → 主体不成立（防"一个主体词是另一个主体词的子串"型误适用）
        excludes = rule.subject_excludes
        if excludes and any(e and e in text for e in excludes):
            return False
    return True


def check_rule(rule, match_spec, text, categories, proof=None, scenario=None):
    """判定单条规则。"""
    if not rule_applies(rule, categories, scenario, text):
        return RuleResult(rule.rule_id, constants.RULE_SKIPPED, (),
                          "不适用：规则限定品类 %s/情形 %s/主体 %s，本次品类 %s/情形 %s"
                          % (list(rule.categories), list(rule.scenarios),
                             list(rule.subject_signals) or "不限",
                             list(categories), scenario))
    handler = DISPATCH.get(rule.kind)
    if handler is None:
        # 未知 kind 不得静默放过
        raise ValueError("未知判定 kind: %s（规则 %s）" % (rule.kind, rule.rule_id))
    return handler(rule, match_spec, text, proof)


def check_all(rules, matches, text, categories, proof=None, scenario=None):
    """对全部生效规则做核查，返回 ``[RuleResult]``。"""
    results = []
    for rule in rules:
        results.append(check_rule(rule, matches.get(rule.rule_id), text, categories,
                                  proof, scenario))
    return results


def dispatch_table_keys():
    """供结构层断言使用（单一实现源）。"""
    return tuple(sorted(DISPATCH.keys()))
