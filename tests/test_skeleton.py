"""骨架回归测试（M0：装配 + 门禁 + 确定性 + 退出码契约）。

纪律：测试引用规则包的词面时**运行时从冻结规则包按下标取**，不在测试文件里
复制词面（否则测试自己变成第二份词表，规则包更新后与数据漂移）。
"""

from __future__ import annotations

import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from medreview import (  # noqa: E402
    check as check_mod, cli, constants, grade, model, normalize, pipeline,
    report as report_mod, ruleset, selftest, serialize,
)
from medreview.bench import cases as cases_mod, ledger as ledger_mod, runner  # noqa: E402


# --------------------------------------------------------------------------
# 退出码契约（K2）——端到端，断言退出码而非"函数抛了"
# --------------------------------------------------------------------------
def test_exit_code_ok_on_non_medical():
    code = cli.main(["check", "--text", "今天天气不错，适合出门散步。"])
    assert code == constants.EXIT_OK


def test_exit_code_finding_on_block():
    code = cli.main(["check", "--text", "XX医疗美容门诊部（虚构）保证治愈，无效退款。"])
    assert code == constants.EXIT_FINDING


def test_exit_code_input_on_missing_text():
    assert cli.main(["check"]) == constants.EXIT_INPUT


def test_exit_code_input_on_blank_text():
    assert cli.main(["check", "--text", "   "]) == constants.EXIT_INPUT


def test_exit_code_input_on_unknown_subcommand():
    assert cli.main(["nope"]) == constants.EXIT_INPUT


def test_exit_code_input_on_unknown_bench_suite():
    assert cli.main(["bench", "--only", "NOPE"]) == constants.EXIT_INPUT


def test_exit_code_ruleset_on_missing_package(tmp_path):
    missing = str(tmp_path / "nope")
    os.environ_backup = os.environ.get("MEDREVIEW_DATA_DIR")
    try:
        os.environ["MEDREVIEW_DATA_DIR"] = missing
        assert cli.main(["check", "--text", "测试内容"]) == constants.EXIT_RULESET
    finally:
        if os.environ_backup is None:
            os.environ.pop("MEDREVIEW_DATA_DIR", None)
        else:
            os.environ["MEDREVIEW_DATA_DIR"] = os.environ_backup


def test_selftest_all_green():
    stream = io.StringIO()
    code = selftest.run_selftest(stream)
    assert code == constants.EXIT_OK, stream.getvalue()
    assert "SELFTEST_OK" in stream.getvalue()


# --------------------------------------------------------------------------
# 规则包：锚点硬门 + 双重门控 + 未启用清单显式
# --------------------------------------------------------------------------
def test_every_enabled_rule_has_resolvable_anchor():
    engine = pipeline.build_engine()
    assert engine.rules
    clauses = ruleset.load_clauses(
        os.path.join(ROOT, "src", "medreview", "references", "clauses.json"))
    for rule in engine.rules:
        assert ruleset.require_anchor(rule, clauses) is True


def test_rule_with_unresolvable_quote_is_refused(tmp_path):
    """缺锚点/引文核不到的规则**拒绝加载**，并进未启用清单（可追溯性入口门）。"""
    rs = {
        "rules": [{
            "id": "X-1", "source": "advertising_law", "clause": "16", "item": "1",
            "anchor": "《中华人民共和国广告法》§16第（一）项",
            "quote": "这句话不在原文里",
            "quote_status": "verified", "anchor_status": "verified",
            "kind": "prohibited_term", "severity": "block",
            "applies_if": {"categories": ["medical"]},
        }]
    }
    rs_path = tmp_path / "ruleset.json"
    rs_path.write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
    clauses_path = tmp_path / "clauses.json"
    clauses_path.write_text(json.dumps({"clauses": [
        {"source": "advertising_law", "clause": "16", "text": "第十六条\n原文"}
    ]}, ensure_ascii=False), encoding="utf-8")

    enabled, not_enabled = ruleset.load_ruleset(str(rs_path), str(clauses_path))
    assert enabled == []
    assert len(not_enabled) == 1
    assert not_enabled[0]["code"] == "anchor_unresolved"


def test_rule_without_applies_if_is_refused(tmp_path):
    """适用域必须落进规则数据（不许写 any）——空 categories 拒绝加载。"""
    rs = {"rules": [{
        "id": "X-2", "source": "advertising_law", "clause": "16", "item": "1",
        "anchor": "a", "quote": "原文", "quote_status": "verified",
        "anchor_status": "verified", "kind": "prohibited_term", "severity": "block",
        "applies_if": {},
    }]}
    rs_path = tmp_path / "ruleset.json"
    rs_path.write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
    clauses_path = tmp_path / "clauses.json"
    clauses_path.write_text(json.dumps({"clauses": [
        {"source": "advertising_law", "clause": "16", "text": "第十六条\n原文"}
    ]}, ensure_ascii=False), encoding="utf-8")
    enabled, not_enabled = ruleset.load_ruleset(str(rs_path), str(clauses_path))
    assert enabled == []
    assert not_enabled[0]["code"] == "missing_applies_if"


def test_pending_status_blocks_rule(tmp_path):
    """未核对（pending）的规则不得进引擎——双重门控的落地。"""
    rs = {"rules": [{
        "id": "X-3", "source": "advertising_law", "clause": "16", "item": "1",
        "anchor": "a", "quote": "原文", "quote_status": "pending",
        "anchor_status": "verified", "kind": "prohibited_term", "severity": "block",
        "applies_if": {"categories": ["medical"]},
    }]}
    rs_path = tmp_path / "ruleset.json"
    rs_path.write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
    clauses_path = tmp_path / "clauses.json"
    clauses_path.write_text(json.dumps({"clauses": [
        {"source": "advertising_law", "clause": "16", "text": "第十六条\n原文"}
    ]}, ensure_ascii=False), encoding="utf-8")
    enabled, not_enabled = ruleset.load_ruleset(str(rs_path), str(clauses_path))
    assert enabled == []
    assert not_enabled[0]["code"] == "quote_pending"


# --------------------------------------------------------------------------
# 判定语义（四态 + 第三态）
# --------------------------------------------------------------------------
def _engine():
    return pipeline.build_engine()


def _run(text, proof=None, scenario=None):
    return pipeline.check_text(_engine(), text, proof=proof, scenario=scenario)


def test_not_assessed_for_non_medical():
    rep = _run("今天天气不错，适合出门散步。")
    assert rep.grade == constants.GRADE_NOT_ASSESSED
    assert rep.grade != constants.GRADE_OK  # 未评估 ≠ 合规
    assert rep.categories == ()


def test_input_required_never_grades_ok():
    """**"缺材料"不得记成 OK**（否则"没查过"被读成"没问题"）。"""
    rep = _run("XX医疗美容门诊部（虚构）开展双眼皮手术。")
    assert rep.input_required
    assert rep.grade != constants.GRADE_OK


def test_proof_no_is_noncompliant_not_skipped():
    """明确未取得审查证明 = 无条件义务缺失 → BLOCK（不得记成"不适用"）。"""
    rep = _run("XX医疗美容门诊部（虚构）双眼皮手术。", proof="no")
    assert rep.grade == constants.GRADE_BLOCK
    hits = [f.rule_id for f in rep.findings]
    assert "IAM-7-1" in hits


def test_applies_domain_reverse():
    """保健食品内容不得被 §16（只管医疗/药品/器械）判命中。"""
    rep = _run("本品保健食品保证有效，绝对安全，无副作用。")
    for finding in rep.findings:
        assert not finding.rule_id.startswith("AL-16-"), finding.rule_id
    skipped = [r.rule_id for r in rep.rule_results
               if r.state == constants.RULE_SKIPPED and r.rule_id.startswith("AL-16-")]
    assert skipped


def test_multi_category_not_either_or():
    rep = _run("XX市第X医院（虚构）引进新型理疗仪，医疗器械注册证齐全。")
    assert "medical" in rep.categories and "device" in rep.categories


def test_scenario_gates_clause_7_2():
    """§7 第 2 款只对已发布情形生效——发布前自查应判不适用。"""
    pre = _run("XX医疗美容门诊部（虚构）双眼皮手术。")
    states = {r.rule_id: r.state for r in pre.rule_results}
    assert states.get("IAM-7-2") == constants.RULE_SKIPPED

    published = _run("XX医疗美容门诊部（虚构）双眼皮手术。", scenario="published")
    states = {r.rule_id: r.state for r in published.rule_results}
    assert states.get("IAM-7-2") == constants.RULE_INPUT_REQUIRED


def test_hint_never_changes_grade():
    """hint 只进报告 advisory，**永不改结论**（逐项相同的 BLOCK/WARN/OK 集合）。"""
    text = "XX医疗美容门诊部（虚构）保证治愈。"
    without = _run(text)
    with_hint = pipeline.check_text(_engine(), text, hint="疑似变相发布")
    assert without.grade == with_hint.grade
    assert [f.rule_id for f in without.findings] == [f.rule_id for f in with_hint.findings]
    assert with_hint.advisories and not without.advisories


def test_grade_priority_block_over_warn():
    results = [
        model.RuleResult("R1", constants.RULE_NONCOMPLIANT, [
            model.Finding("R1", "a", "q", "e", constants.SEVERITY_WARN, "k")]),
        model.RuleResult("R2", constants.RULE_NONCOMPLIANT, [
            model.Finding("R2", "a", "q", "e", constants.SEVERITY_BLOCK, "k")]),
    ]
    assert grade.grade_results(results).grade == constants.GRADE_BLOCK


# --------------------------------------------------------------------------
# 报告：零外链常驻断言 + 双轨同源 + 确定性
# --------------------------------------------------------------------------
def test_report_markdown_has_no_external_links():
    rep = _run("XX医疗美容门诊部（虚构）保证治愈，无效退款。")
    text = report_mod.render_markdown(rep)
    assert "http://" not in text and "https://" not in text


def test_report_assert_no_external_links_raises():
    with pytest.raises(report_mod.RenderError):
        report_mod.assert_no_external_links("见 https://example.com")


def test_report_json_carries_official_urls():
    """URL 只出现在机读产物的 rule_sources 字段（供核证）。"""
    rep = _run("XX医疗美容门诊部（虚构）保证治愈。")
    payload = report_mod.render_json(rep)
    urls = [entry["official_url"] for entry in payload["rule_sources"]]
    assert urls and all(u.startswith("https://") for u in urls)


def test_report_json_deterministic():
    rep = _run("XX医疗美容门诊部（虚构）保证治愈。")
    first = serialize.dumps_json(report_mod.render_json(rep))
    second = serialize.dumps_json(report_mod.render_json(rep))
    assert first == second


def test_serialize_lf_and_trailing_newline():
    text = serialize.dumps_json({"a": "中文", "b": [1, 2]})
    assert "\r" not in text
    assert text.endswith("\n")
    assert "\\u" not in text  # ensure_ascii=False：中文原样


# --------------------------------------------------------------------------
# 基准：四套件 + 冻结台账真读 + 未启用不冒充通过
# --------------------------------------------------------------------------
def test_benchmarks_all_pass():
    code, summary = runner.run_benchmarks()
    assert code == constants.EXIT_OK, summary
    assert summary["truth_source"] == "frozen"
    assert not summary["not_met"]


def test_bench_unknown_suite_is_usage_error():
    code, summary = runner.run_benchmarks(only="NOPE")
    assert code == runner.EXIT_USAGE
    assert "未知套件名" in summary["error"]


def test_frozen_ledger_detects_tampering():
    """**变异验证**：手改一条用例 → 冻结台账必须报红（不是假门）。"""
    payload, _ = runner.load_fixture_payload()
    assert ledger_mod.check_frozen_ledger(payload) == []

    tampered = json.loads(json.dumps(payload))
    tampered["cases"][0]["input"] = tampered["cases"][0]["input"] + "（被改动）"
    problems = ledger_mod.check_frozen_ledger(tampered)
    assert problems, "改动用例内容后台账未报红——假门"
    assert any("内容与台账不符" in p for p in problems)


def test_frozen_ledger_detects_missing_case():
    payload, _ = runner.load_fixture_payload()
    tampered = json.loads(json.dumps(payload))
    tampered["cases"] = tampered["cases"][1:]
    problems = ledger_mod.check_frozen_ledger(tampered)
    assert any("缺失" in p for p in problems)


def test_fake_org_whitelist_enforced():
    """合成数据纪律：全部样例机构名必须在白名单内（题面 §四.1）。"""
    payload, _ = runner.load_fixture_payload()
    assert ledger_mod.check_fake_org_whitelist(payload) == []


def test_fake_org_whitelist_catches_violation():
    """**变异验证**：样例里塞进一个白名单外的真实机构名 → 必须报红。"""
    payload, _ = runner.load_fixture_payload()
    tampered = json.loads(json.dumps(payload))
    tampered["cases"][0]["input"] = "某某第一人民医院推广内容，保证治愈。"
    tampered["cases"][0]["sha256"] = ledger_mod.case_digest(tampered["cases"][0])
    problems = ledger_mod.check_fake_org_whitelist(tampered)
    assert problems, "白名单外的机构名未被检出——假门"


def test_fake_org_whitelist_empty_is_an_error():
    """白名单为空 = 纪律未落地，必须报错（不是静默放行）。"""
    payload, _ = runner.load_fixture_payload()
    assert ledger_mod.check_fake_org_whitelist(payload, whitelist=[])


def test_truth_library_has_no_observed_fields():
    """真值库只存输入与期望——出现 observed 一类字段即红。"""
    payload, _ = runner.load_fixture_payload()
    assert cases_mod.truth_field_violations(payload) == []


def test_truth_case_digest_matches_package_implementation():
    """生成器与运行时**共用同一摘要实现**（不在工具里写第二份口径）。"""
    payload, _ = runner.load_fixture_payload()
    for case in payload["cases"]:
        assert case["sha256"] == ledger_mod.case_digest(case)


def test_probe_b1_defect_is_caught():
    """**探活**：给 B1 注入"期望被篡改"→ 基准必须报未达标（打到端到端入口）。"""
    payload, path = runner.load_fixture_payload()
    tampered = json.loads(json.dumps(payload))
    for case in tampered["cases"]:
        if case["suite"] == "b1_category":
            case["expect_keys"] = ["grade:NOT_ASSESSED"]
            case["sha256"] = ledger_mod.case_digest(case)
            break
    for entry in tampered["ledger"]["entries"]:
        for case in tampered["cases"]:
            if case["id"] == entry["id"]:
                entry["sha256"] = case["sha256"]

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "cases.json")
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(tampered, sort_keys=True, ensure_ascii=False, indent=2))
        code, summary = runner.run_benchmarks(fixtures_dir=tmp)
    assert code == runner.EXIT_NOT_MET, "注入缺陷后基准仍达标——探活是永绿门"
    assert summary["not_met"]


def test_probe_rule_coverage_defect_is_caught():
    """探活：删掉某条规则的**唯一**覆盖用例 → B4 必不达标（分母 = 生效规则数）。

    先**实算**"哪条规则只被一个用例覆盖"（不硬编码规则 id：规则包会演化），
    再删掉那个用例——删掉后仍达标即假门。
    """
    engine = pipeline.build_engine(scope=constants.SCOPE_BENCH)
    payload, _ = runner.load_fixture_payload()
    thresholds = runner.load_thresholds(engine)

    # 实算每条规则被哪些用例覆盖
    coverage_map = {}
    for case in runner._cases_for(payload, "b4_rule_coverage"):
        item = normalize.normalize_text(case["input"], proof=case.get("proof"),
                                        scenario=case.get("scenario"))
        rep = pipeline.run_check(engine, item)
        for key in cases_mod.observed_keys(rep):
            if key.startswith("rule:skipped:"):
                continue
            if key.startswith("rule:") or key.startswith("hit:"):
                coverage_map.setdefault(key.split(":", 2)[-1], set()).add(case["id"])

    sole = [(rule_id, ids) for rule_id, ids in coverage_map.items() if len(ids) == 1]
    assert sole, "没有'唯一覆盖'的规则——B4 探活无法构造"
    rule_id, ids = sorted(sole)[0]
    doomed = sorted(ids)[0]

    original = runner._cases_for
    try:
        runner._cases_for = lambda p, s: (
            [c for c in original(p, s) if c["id"] != doomed] if s == "b4_rule_coverage"
            else original(p, s))
        result = runner._run_suite("b4_rule_coverage", engine, payload, thresholds)
    finally:
        runner._cases_for = original

    assert not result["passed"], "删掉唯一覆盖用例后 B4 仍达标——假门"
    assert rule_id in result["uncovered_rules"]


# --------------------------------------------------------------------------
# 门禁：零字面量 + 网络导入（含变异验证）
# --------------------------------------------------------------------------
def test_engine_sources_have_zero_policy_tokens():
    """判定模块零判定词面（展示/工具模块不在该面内，见 selftest 的扫描面定义）。"""
    tokens = selftest._ruleset_tokens()
    assert tokens, "词面集合为空 = 门禁空转"
    for name in selftest.JUDGMENT_MODULES:
        hits = selftest.scan_policy_tokens(selftest._read_source(name), tokens)
        assert not hits, "%s 含判定词面：%s" % (name, hits)


def test_engine_sources_have_no_network_imports():
    for name in selftest.SCAN_TARGETS:
        assert not selftest.scan_network_imports(selftest._read_source(name))


def test_network_gate_positive_control():
    """变异验证：注入网络导入 → 扫描器必须报红。"""
    hits = selftest.scan_network_imports("import socket\n")
    assert hits == ["socket"]


def test_policy_token_gate_positive_control():
    """变异验证：注入真实词面 → 扫描器必须报红。"""
    tokens = selftest._ruleset_tokens()
    probe = sorted(tokens, key=len)[-1]  # 取一个真实词面（运行时实算，非字面量）
    hits = selftest.scan_policy_tokens("前缀 " + probe + " 后缀", tokens)
    assert probe in hits


def test_dispatch_table_keys_match_constants():
    assert set(check_mod.dispatch_table_keys()) == set(constants.KINDS)


def test_dispatch_handlers_are_distinct():
    handlers = [check_mod.DISPATCH[k] for k in sorted(check_mod.DISPATCH)]
    assert len(set(handlers)) == len(handlers)


def test_unknown_kind_raises():
    """变异自检：未知 kind 不得静默放过。"""
    rule = model.Rule("R", "s", "1", None, "a", "q", "verified", "verified",
                      "no_such_kind", "block", {"categories": ["medical"]})
    with pytest.raises(ValueError):
        check_mod.check_rule(rule, {}, "文本", ("medical",))


def test_mandatory_disclosure_missing_is_noncompliant():
    """无条件义务缺失 → noncompliant（**不是 skipped**）。"""
    rule = [r for r in _engine().rules if r.rule_id == "AL-18-D1"][0]
    result = check_mod.check_rule(rule, {"require_all_of": [["不能代替药物"]]},
                                  "本品保健食品，增强免疫力。", ("health_food",))
    assert result.state == constants.RULE_NONCOMPLIANT


def test_mandatory_disclosure_present_is_compliant():
    rule = [r for r in _engine().rules if r.rule_id == "AL-18-D1"][0]
    result = check_mod.check_rule(rule, {"require_all_of": [["不能代替药物"]]},
                                  "本品保健食品，本品不能代替药物。", ("health_food",))
    assert result.state == constants.RULE_COMPLIANT


# --------------------------------------------------------------------------
# 输入层
# --------------------------------------------------------------------------
def test_content_id_is_deterministic():
    assert normalize.content_id("同一段文本") == normalize.content_id("同一段文本")
    assert normalize.content_id("a") != normalize.content_id("b")


def test_empty_text_is_input_unavailable():
    with pytest.raises(ValueError):
        normalize.normalize_text("")


def test_read_text_file_bad_encoding(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe\x00 bad")
    with pytest.raises(ValueError):
        normalize.read_text_file(str(path))


# --------------------------------------------------------------------------
# 报告契约（章节齐备）
# --------------------------------------------------------------------------
def test_report_sections_include_required_blocks():
    rep = _run("XX医疗美容门诊部（虚构）保证治愈。")
    ids = [s["id"] for s in report_mod.report_sections(rep)]
    for required in ("input_facts", "coverage", "grade", "findings",
                     "input_required", "advisory", "sources", "disclaimer"):
        assert required in ids


def test_finding_has_four_elements():
    """每条命中四要素齐备：条款锚点 / 法条原文 / 命中证据 / rule_id。"""
    rep = _run("XX医疗美容门诊部（虚构）保证治愈，无效退款。")
    assert rep.findings
    for finding in rep.findings:
        assert finding.rule_id
        assert finding.clause_anchor
        assert finding.quote
        assert finding.evidence


def test_finding_quote_verbatim_in_clause_snapshot():
    """法条原文必须**逐字出现在官方快照**中（可机器核验的溯源）。"""
    clauses = ruleset.load_clauses(
        os.path.join(ROOT, "src", "medreview", "references", "clauses.json"))
    rep = _run("XX医疗美容门诊部（虚构）保证治愈，无效退款。")
    engine = _engine()
    for finding in rep.findings:
        rule = [r for r in engine.rules if r.rule_id == finding.rule_id][0]
        assert finding.quote in clauses[(rule.source, str(rule.clause))]


def test_finding_evidence_verbatim_in_input():
    """命中证据必须**逐字出现在输入文案**中（防引用用户没写过的文字）。

    证据分两种**性质**（`evidence_kind` 结构性字段，不靠字符串前缀特判）：
    ``text_span`` 须逐字在文案里；``obligation_missing`` 描述的是"该写而没写"，
    **不可能**在文案里出现，故只要求非空。
    """
    text = "XX医疗美容门诊部（虚构）保证治愈，无效退款。"
    rep = _run(text)
    for finding in rep.findings:
        if finding.evidence_kind == constants.EVIDENCE_OBLIGATION_MISSING:
            assert finding.evidence, "义务缺失类证据不得为空"
            continue
        assert finding.evidence in text, finding.evidence


# --------------------------------------------------------------------------
# 品类判定词表来自规则包（源码零词面）
# --------------------------------------------------------------------------
def test_category_rules_come_from_ruleset():
    engine = _engine()
    assert engine.category_rules
    for entry in engine.category_rules:
        assert entry["terms"]
        assert entry["anchor"]
        assert entry["quote"]
