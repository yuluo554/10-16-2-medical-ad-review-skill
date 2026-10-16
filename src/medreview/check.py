"""禁止情形核查（模块 3）。

**唯一实现源**：全部判定在此处，报告层不重算。

两条硬纪律：

1. **分派表结构 + 运行双层断言**（skill 定稿形态）：只断言"表里有三个键"是假门——
   分派表可以齐备而判定路径从不查它。故：① 结构层断言"表键集合与 kind 常量集合
   一一对应且各实现互不相同"；② 运行层对每个 kind 真跑一遍且不抛错；③ 变异自检
   （摘掉一个 kind → 必须报错）。
2. **词面/模式一律来自冻结规则包**：本模块零政策字面量（K9）。匹配规格是数据
   （``match.any_of`` / ``all_of`` / ``none_of``），不是代码。
"""

from __future__ import annotations

from . import constants
from .model import Finding, RuleResult


def _any_of(text, terms):
    """命中任一（返回命中项列表，保持规则包给出的顺序）。"""
    return [t for t in terms if t and t in text]


def _all_of(text, terms):
    """全部命中才命中（返回命中项；未全中返回空）。"""
    if not terms:
        return []
    hits = [t for t in terms if t and t in text]
    return hits if len(hits) == len(terms) else []


def _none_of(text, terms):
    """必须一个都不出现（返回空列表表示"通过"）。"""
    return [t for t in terms if t and t in text]


def match_rule(rule, match_spec, text):
    """通用匹配：返回命中项列表（空 = 未命中）。

    ``match_spec`` 结构：``{"any_of": [...], "all_of": [...], "none_of": [...]}``
    ——全部字段可选；三者是**与**关系（any_of 命中 && all_of 全中 && none_of 全空）。
    """
    spec = match_spec or {}
    any_hits = _any_of(text, spec.get("any_of") or ())
    all_hits = _all_of(text, spec.get("all_of") or ())
    none_hits = _none_of(text, spec.get("none_of") or ())

    if spec.get("all_of") and not all_hits:
        return []
    if none_hits:
        return []
    if spec.get("any_of") and not any_hits:
        return []
    if not spec.get("any_of") and not spec.get("all_of"):
        # 没有正向条件 = 规格缺失，绝不"空规格恒命中"
        return []
    return any_hits + all_hits


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
    """结构性禁止模式（共现/顺序类）——与 prohibited_term 共用匹配器但语义独立。"""
    hits = match_rule(rule, match_spec, text)
    if not hits:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    evidence = "、".join(hits)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, evidence, rule.severity, rule.kind)
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_mandatory_disclosure(rule, match_spec, text, proof=None):
    """**无条件义务**：必须出现某提示语；缺失 → noncompliant（绝不记成"不适用"）。

    ``match_spec.require_all_of`` 是"每一组内至少出现一个"的列表；缺任一组即命中。
    """
    spec = match_spec or {}
    groups = spec.get("require_all_of") or []
    if not groups:
        # 没有可判定的义务组 = 规格缺失，记 input_required 而非猜
        return RuleResult(rule.rule_id, constants.RULE_INPUT_REQUIRED, (),
                          "规则缺 require_all_of 规格，无法判定")
    missing = []
    for group in groups:
        if not any(t and t in text for t in group):
            missing.append(group)
    if not missing:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote,
                "缺失应显著标明的内容（第 %d 组）" % (idx + 1),
                rule.severity, rule.kind)
        for idx, _ in enumerate(missing)
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_whitelist_scope(rule, match_spec, text, proof=None):
    """超出白名单范围的表述 → warn（非明确禁止）。"""
    hits = match_rule(rule, match_spec, text)
    if not hits:
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    evidence = "、".join(hits)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, evidence, rule.severity, rule.kind)
    ]
    return RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT, findings)


def _check_variant_publish(rule, match_spec, text, proof=None):
    """变相发布情形：知识形态 + 商品/服务信息**共现**（条款号见规则锚点）。"""
    spec = match_spec or {}
    knowledge = _any_of(text, spec.get("knowledge_terms") or ())
    commerce = _any_of(text, spec.get("commerce_terms") or ())
    if not (knowledge and commerce):
        return RuleResult(rule.rule_id, constants.RULE_COMPLIANT)
    evidence = "、".join(knowledge + commerce)
    findings = [
        Finding(rule.rule_id, rule.anchor, rule.quote, evidence, rule.severity, rule.kind)
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
                    rule.severity, rule.kind)
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


def rule_applies(rule, categories, scenario=None):
    """适用域判定：品类交集 **且** 情形命中才适用。

    两维都来自**原文自带的主体/情形限制**——无交集 → ``skipped``
    （这是"不适用"的**唯一合法来源**："我没看到材料"或"用户没做"**不算**不适用）。
    """
    rule_cats = set(rule.categories)
    if not rule_cats:
        return False
    if not (rule_cats & set(categories)):
        return False
    rule_scenarios = set(rule.scenarios)
    if rule_scenarios and scenario not in rule_scenarios:
        return False
    return True


def check_rule(rule, match_spec, text, categories, proof=None, scenario=None):
    """判定单条规则。"""
    if not rule_applies(rule, categories, scenario):
        return RuleResult(rule.rule_id, constants.RULE_SKIPPED, (),
                          "不适用：规则限定品类 %s/情形 %s，本次品类 %s/情形 %s"
                          % (list(rule.categories), list(rule.scenarios),
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
