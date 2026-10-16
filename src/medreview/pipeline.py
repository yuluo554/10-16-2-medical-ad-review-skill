"""编排层（公开函数组）——CLI / 基准 / 测试共用同一分派点。

纪律（"单件与批量必须共用同一分派点"）：``run_check`` 是**唯一**审查入口；
CLI 的 ``check`` 与 ``scan`` 都调它，``benchmark`` 的观测器也调它。两条通路各写
一套分派会对同一内容给出不同结论（最隐蔽的口径漂移）。
"""

from __future__ import annotations

import os
from typing import List

from . import categorize, check, constants, grade, normalize, ruleset
from .errors import FindingIncomplete, RulesetUnavailable
from .paths import clauses_path, manifest_path, ruleset_path


class Engine(object):
    """装配好的审查引擎（规则包 + 判定规格 + 品类词表）。"""

    __slots__ = ("rules", "not_enabled", "matches", "category_rules",
                 "variant_rules", "manifest", "ruleset_version", "basis_date",
                 "rule_sources", "total_rule_count")

    def __init__(self, rules, not_enabled, matches, category_rules, variant_rules,
                 manifest, rule_sources):
        self.rules = list(rules)
        self.not_enabled = list(not_enabled)
        self.matches = dict(matches or {})
        self.category_rules = list(category_rules or ())
        self.variant_rules = list(variant_rules or ())
        self.manifest = dict(manifest or {})
        self.ruleset_version = self.manifest.get("ruleset_version")
        self.basis_date = self.manifest.get("basis_date")
        self.rule_sources = list(rule_sources or ())
        self.total_rule_count = self.manifest.get(
            "total_rule_count", len(self.rules) + len(self.not_enabled))


def build_engine(data_dir=None, scope=constants.SCOPE_CHECK):
    """装配引擎（唯一装配点）。

    规则包文件缺失 → 退出码 3 语义（``RulesetUnavailable``）。
    """
    rs_path = ruleset_path(data_dir)
    cl_path = clauses_path(data_dir)
    if not os.path.isfile(rs_path):
        raise RulesetUnavailable("规则包不存在: %s" % rs_path, code="ruleset_missing")

    payload = ruleset._read_json(rs_path)
    enabled, not_enabled = ruleset.load_ruleset(rs_path, cl_path, scope=scope)

    matches = {}
    for raw in payload.get("rules", []):
        if "match" in raw:
            matches[raw["id"]] = raw["match"]

    manifest = {}
    if os.path.isfile(manifest_path(data_dir)):
        manifest = ruleset.load_manifest(manifest_path(data_dir))

    rule_sources = []
    for raw in payload.get("rules", []):
        rule_sources.append({
            "rule_id": raw["id"],
            "source_title": raw.get("source_title", raw.get("source", "")),
            "anchor": raw.get("anchor", ""),
            "official_url": raw.get("official_url", ""),
            "basis_date": raw.get("basis_date", ""),
        })

    return Engine(
        rules=enabled,
        not_enabled=not_enabled,
        matches=matches,
        category_rules=payload.get("category_rules", []),
        variant_rules=payload.get("variant_rules", []),
        manifest=manifest,
        rule_sources=rule_sources,
    )


def run_check(engine, item):
    """**唯一审查入口**：内容 → ``Report``。

    品类判定 → 规则核查 → 分级，全部经既有实现（本函数零判定逻辑）。
    """
    cat_result = categorize.categorize(item, engine.category_rules, engine.variant_rules)
    categories = cat_result.categories

    rule_results = check.check_all(engine.rules, engine.matches, item.text,
                                   categories, proof=item.proof,
                                   scenario=item.scenario)
    grade_result = grade.grade_results(rule_results)

    advisories = []
    if item.hint:
        # hint 只进报告 advisory 分节，**永不改结论**
        advisories.append({
            "kind": "hint",
            "text": item.hint,
            "note": "语境提示，由宿主 agent/人工提供；不参与 BLOCK/WARN/OK 分级计算",
        })
    if cat_result.variant_suspect:
        # 把品类层实算到的**命中信号 + 条款锚点**一并带进 advisory：提示要可核验，
        # 不能只是一句散文（否则读者无法判断"疑似"从何而来）。
        variant_evidence = [e for e in cat_result.evidence
                            if e.get("signal_id", "").startswith("variant_")]
        advisories.append({
            "kind": "variant_publish_suspect",
            "text": "疑似变相发布（知识形态与商品/服务信息共现）",
            "signals": variant_evidence,
            "note": "提示性结论，**不参与分级**；最终由 §8 对应规则判定（锚点见 signals）",
        })

    input_required = [
        {"rule_id": r.rule_id, "reason": r.reason}
        for r in rule_results
        if r.state == constants.RULE_INPUT_REQUIRED
    ]

    report = build_report(item, categories, grade_result, rule_results, engine,
                          advisories, input_required)
    # **导出前常驻断言**（plan/03 §4.3）：四要素不齐备即拒绝出件——不留"半溯源"报告。
    assert_findings_traceable(report, engine, item.text)
    return report


def assert_findings_traceable(report, engine, text):
    """**导出前常驻断言**：每条 Finding 的四要素齐备且可机器核验（plan/03 §4.3）。

    判据（不是"字段非空"——那挡不住"引文写错"）：
      ① ``rule_id`` 非空且**存在于规则包**（引擎装配的生效规则集合）；
      ② ``clause_anchor`` 非空且**可解析**（含条款号形态，且与规则的 source/clause 一致）；
      ③ ``quote`` **逐字出现在该条款的官方快照切片中**（回读条文块校验）；
      ④ ``evidence`` 非空；``evidence_kind == text_span`` 时还须**逐字出现在输入文案**中
         （防"引用用户没写过的文字"）；``obligation_missing`` 类（义务缺失）只要求非空
         ——这类证据描述的是"该写而没写"，**不可能**在文案里。

    任一条不满足 → ``FindingIncomplete``（退出码 1），**拒绝导出**。
    这是"每条结论可溯源"的落地：断言常驻在唯一导出点，不是"记得跑那条测试"。
    """
    by_id = {rule.rule_id: rule for rule in engine.rules}
    clauses = ruleset.load_clauses(clauses_path())
    problems = []

    for finding in report.findings:
        rule = by_id.get(finding.rule_id)
        if rule is None:
            problems.append("rule_id %r 不在生效规则包中" % finding.rule_id)
            continue
        if not finding.clause_anchor:
            problems.append("%s 的 clause_anchor 为空" % finding.rule_id)
        else:
            anchor = finding.clause_anchor
            if ("§%s" % rule.clause) not in anchor:
                problems.append("%s 的 clause_anchor 与规则条款不符（锚点 %r / 条款 §%s）"
                                % (finding.rule_id, anchor, rule.clause))
        clause_text = clauses.get((rule.source, str(rule.clause)))
        if clause_text is None:
            problems.append("%s 的条款不在条文快照中：%s §%s"
                            % (finding.rule_id, rule.source, rule.clause))
        elif not finding.quote or finding.quote not in clause_text:
            problems.append("%s 的 quote 未逐字出现在 §%s 快照中"
                            % (finding.rule_id, rule.clause))
        if not finding.evidence:
            problems.append("%s 的 evidence 为空" % finding.rule_id)
        elif finding.evidence_kind == constants.EVIDENCE_TEXT_SPAN                 and finding.evidence not in text:
            problems.append("%s 的 evidence 未逐字出现在输入文案中" % finding.rule_id)

    if problems:
        raise FindingIncomplete(
            "命中四要素断言失败（拒绝导出半溯源报告）：%s" % "；".join(problems),
            code="finding_incomplete")
    return True


def build_report(item, categories, grade_result, rule_results, engine,
                 advisories, input_required):
    """构造 ``Report``（薄封装，便于测试注入）。"""
    from .model import Report
    applied = sum(1 for r in rule_results if r.state != constants.RULE_SKIPPED)
    return Report(
        item=item,
        categories=categories,
        grade=grade_result.grade,
        rule_results=rule_results,
        applied_rule_count=applied,
        total_rule_count=engine.total_rule_count,
        not_enabled=engine.not_enabled,
        advisories=advisories,
        input_required=input_required,
        ruleset_version=engine.ruleset_version,
        ruleset_basis_date=engine.basis_date,
        rule_sources=engine.rule_sources,
    )


def check_text(engine, text, channel=None, subject=None, hint=None, proof=None,
               source_path=None, scenario=None, proof_file=None):
    """便捷入口：文本 → Report。"""
    item = normalize.normalize_text(text, channel=channel, subject=subject,
                                    hint=hint, proof=proof, source_path=source_path,
                                    scenario=scenario, proof_file=proof_file)
    return run_check(engine, item)


def scan_items(engine, items):
    """批量通路：逐件调 ``run_check``（**与单件共用同一分派点**）。

    失败隔离：单件异常不中断整批——该件记 ``failed`` 并继续。
    """
    results = []
    for item in items:
        try:
            results.append({"id": item.id, "ok": True, "report": run_check(engine, item)})
        except ValueError as exc:
            results.append({"id": item.id, "ok": False, "error": str(exc)})
    return results
