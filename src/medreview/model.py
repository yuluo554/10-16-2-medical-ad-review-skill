"""数据结构（统一中间表示）。

分层纪律：本模块只放**数据结构**，零判定逻辑。判定一律在
``categorize`` / ``check`` / ``grade`` 三处（唯一实现源）。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from . import constants


class ContentItem(object):
    """标准化后的待审查内容对象（模块 1 的输出）。

    ``id`` 由原文哈希确定性派生（**不用随机数/时钟**），保证"同输入同 id"。
    """

    __slots__ = ("id", "text", "channel", "subject", "hint", "proof", "source_path",
                 "scenario", "proof_file")

    def __init__(self, item_id, text, channel=None, subject=None, hint=None,
                 proof=None, source_path=None, scenario=None, proof_file=None):
        self.id = item_id
        self.text = text
        self.channel = channel
        self.subject = subject
        self.hint = hint
        self.proof = proof
        self.source_path = source_path
        self.scenario = scenario
        self.proof_file = proof_file

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "channel": self.channel,
            "subject": self.subject,
            "hint": self.hint,
            "proof": self.proof,
            "source_path": self.source_path,
            "scenario": self.scenario,
            "proof_file": self.proof_file,
        }


class Rule(object):
    """一条冻结规则（规则包条目 → 对象）。

    ``quote`` / ``anchor`` 是**可追溯性的载体**：缺锚点或锚点解析不到的规则
    **拒绝被引擎加载**（见 ``ruleset.load_ruleset`` 的锚点硬门）。
    """

    __slots__ = (
        "rule_id", "source", "clause", "item", "anchor", "quote",
        "quote_status", "anchor_status", "kind", "severity", "applies_if",
        "pattern_id", "notes",
    )

    def __init__(self, rule_id, source, clause, item, anchor, quote, quote_status,
                 anchor_status, kind, severity, applies_if, pattern_id=None, notes=""):
        self.rule_id = rule_id
        self.source = source
        self.clause = clause
        self.item = item
        self.anchor = anchor
        self.quote = quote
        self.quote_status = quote_status
        self.anchor_status = anchor_status
        self.kind = kind
        self.severity = severity
        self.applies_if = applies_if or {}
        self.pattern_id = pattern_id
        self.notes = notes

    @property
    def categories(self):
        """本规则适用的品类集合（来自原文自带的主体限制，**不许写 any**）。"""
        return tuple(self.applies_if.get("categories", ()))

    @property
    def scenarios(self):
        """本规则适用的**情形**集合（原文自带的情形限制，空 = 不限情形）。

        例：某条款原文以"已经审查通过"为前提，则它只对**已发布**情形生效；
        发布前自查时该条不适用（记 ``skipped``），而不是记"待补材料"
        （具体条款锚点见规则包，本文件零词面）。
        """
        return tuple(self.applies_if.get("scenario", ()))

    @property
    def subject_signals(self):
        """本规则适用的**主体信号**词表（原文自带的主体限制，空 = 不限主体）。

        用途：原文对**特定主体**设的义务（如"某类广告应当显著标明…"）只在该主体
        成立时适用——主体未成立 → ``skipped``（"不适用"），而不是判命中。
        词面来自规则包（本文件零词面）；判定在 ``check.rule_applies``。
        """
        return tuple(self.applies_if.get("subject_signals", ()))

    @property
    def subject_excludes(self):
        """主体信号的**排除词表**（出现即该主体不成立，空 = 无排除）。

        用途：**子串包含**导致的误适用——一个主体词可能是另一个主体词的子串，
        若不做排除，后者的广告会因含前者的字面而被判"缺前者提示语"。
        排除词命中 → 主体不成立 → ``skipped``（**不判命中**）。
        """
        return tuple(self.applies_if.get("subject_excludes", ()))

    def to_dict(self):
        return {
            "id": self.rule_id,
            "source": self.source,
            "clause": self.clause,
            "item": self.item,
            "anchor": self.anchor,
            "quote": self.quote,
            "quote_status": self.quote_status,
            "anchor_status": self.anchor_status,
            "kind": self.kind,
            "severity": self.severity,
            "applies_if": self.applies_if,
            "pattern_id": self.pattern_id,
            "notes": self.notes,
        }


class Finding(object):
    """一条命中明细——**四要素齐备**是导出前的硬约束。

    四要素：``clause_anchor``（条款号）、``quote``（法条原文逐字）、
    ``evidence``（文案命中片段逐字）、``rule_id``。

    ``evidence_kind`` 区分证据的**两种性质**（导出前断言据此选判据）：
      - ``text_span``：证据是**文案里的片段**，必须逐字出现在输入文案中；
      - ``obligation_missing``：证据描述的是**"该写而没写"**（无条件义务缺失），
        它**不可能**出现在文案里——这类证据只要求非空且规则为义务类。
    把这两类混为一谈会让断言要么误红（义务缺失类），要么靠字符串前缀特判
    （脆弱：改一句措辞就绕过门禁）。
    """

    __slots__ = ("rule_id", "clause_anchor", "quote", "evidence", "severity",
                 "kind", "notes", "evidence_kind")

    def __init__(self, rule_id, clause_anchor, quote, evidence, severity, kind,
                 notes="", evidence_kind=constants.EVIDENCE_TEXT_SPAN):
        self.rule_id = rule_id
        self.clause_anchor = clause_anchor
        self.quote = quote
        self.evidence = evidence
        self.severity = severity
        self.kind = kind
        self.notes = notes
        self.evidence_kind = evidence_kind

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "clause_anchor": self.clause_anchor,
            "quote": self.quote,
            "evidence": self.evidence,
            "severity": self.severity,
            "kind": self.kind,
            "notes": self.notes,
        }


class RuleResult(object):
    """一条规则的判定结果（规则级三态 + 第三态 input_required）。"""

    __slots__ = ("rule_id", "state", "findings", "reason")

    def __init__(self, rule_id, state, findings=None, reason=""):
        self.rule_id = rule_id
        self.state = state
        self.findings = list(findings or ())
        self.reason = reason

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "state": self.state,
            "findings": [f.to_dict() for f in self.findings],
            "reason": self.reason,
        }


class Report(object):
    """一次审查的完整结论（报告层的唯一输入）。

    ``grade`` 由 ``grade.grade_results`` 产出，报告层**只渲染不重算**。
    """

    __slots__ = (
        "item", "categories", "grade", "rule_results", "applied_rule_count",
        "total_rule_count", "not_enabled", "advisories", "input_required",
        "ruleset_version", "ruleset_basis_date", "rule_sources",
    )

    def __init__(self, item, categories, grade, rule_results, applied_rule_count,
                 total_rule_count, not_enabled=None, advisories=None,
                 input_required=None, ruleset_version=None, ruleset_basis_date=None,
                 rule_sources=None):
        self.item = item
        self.categories = tuple(categories)
        self.grade = grade
        self.rule_results = list(rule_results)
        self.applied_rule_count = applied_rule_count
        self.total_rule_count = total_rule_count
        self.not_enabled = list(not_enabled or ())
        self.advisories = list(advisories or ())
        self.input_required = list(input_required or ())
        self.ruleset_version = ruleset_version
        self.ruleset_basis_date = ruleset_basis_date
        self.rule_sources = list(rule_sources or ())

    @property
    def findings(self):
        out = []  # type: List[Finding]
        for result in self.rule_results:
            out.extend(result.findings)
        return out

    def to_dict(self):
        return {
            "item": self.item.to_dict(),
            "categories": list(self.categories),
            "grade": self.grade,
            "findings": [f.to_dict() for f in self.findings],
            "rule_results": [r.to_dict() for r in self.rule_results],
            "applied_rule_count": self.applied_rule_count,
            "total_rule_count": self.total_rule_count,
            "not_enabled": list(self.not_enabled),
            "advisories": list(self.advisories),
            "input_required": list(self.input_required),
            "ruleset_version": self.ruleset_version,
            "ruleset_basis_date": self.ruleset_basis_date,
            "rule_sources": list(self.rule_sources),
        }
