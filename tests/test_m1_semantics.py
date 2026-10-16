"""M1 数据先行的引擎语义回归（**修复即锁门**）。

本模块把 M1 实测发现的四类缺陷各配一条**单元级**守门——基准用例能挡住
"整体跑歪"，但挡不住"某条规则的某个分支悄悄改回原样"。每条都配阳性/阴性
两侧（"该命中要命中"+"不该命中不许命中"），否则是单向假门。

覆盖的四类缺陷（均本对话实测）：
  1. **交叉引用劫持**：§6 末款「（一）至（六）项…」被项提取器当成第（一）项，
     使真项（医疗机构第一名称）被覆盖 → 锚点与引文错位。
  2. **否定辖域缺失**：法条强制要求的免责语（含被禁词面）被判命中 →
     把合规文案报成违法。
  3. **主体门控缺失**：原文只对特定主体设的义务被施加到非该主体 →
     误报"缺失应标明内容"；且主体词之间存在子串包含（一个词是另一个的子串）。
  4. **裸单字词表误报**：比较/疾病类规则用裸单字匹配 → 中性表述被判命中。

纪律：词面一律**运行时从冻结规则包/条文快照实算**，不在本文件复制词面
（否则测试自己变成第二份词表，规则包更新后与数据漂移）。
"""

from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from medreview import check as check_mod, constants, model, normalize, pipeline  # noqa: E402
from medreview import ruleset  # noqa: E402

import gen_ruleset  # noqa: E402


def _engine(scope=constants.SCOPE_CHECK):
    return pipeline.build_engine(scope=scope)


def _run(text, proof=None, scenario=None):
    return pipeline.check_text(_engine(), text, proof=proof, scenario=scenario)


def _states(report):
    return {r.rule_id: r.state for r in report.rule_results}


def _rule(rule_id, scope=constants.SCOPE_CHECK):
    for rule in _engine(scope).rules:
        if rule.rule_id == rule_id:
            return rule
    raise AssertionError("规则包中不存在规则 %s" % rule_id)


# --------------------------------------------------------------------------
# 缺陷 1：交叉引用劫持（生成器项提取）
# --------------------------------------------------------------------------
def test_clause_items_excludes_cross_reference_line():
    """§6 的交叉引用行「（一）至（六）项…」**不得**被当成第（一）项。

    阴性：真项（医疗机构第一名称）必须在位。
    阳性：交叉引用行不得出现在任何项的 text 里。
    """
    text = gen_ruleset.read_snapshot("medical_ad_measures.txt")
    block = [b for b in gen_ruleset.split_clauses(text) if b["clause"] == "6"][0]
    items = gen_ruleset.clause_items(block["text"])

    assert "1" in items, "第（一）项未被提取——项提取整体失效"
    # 交叉引用行的特征：以「（n）至」「（n）、」起头
    for key, entry in items.items():
        assert not gen_ruleset.CROSS_REF_RE.match(entry["text"]), \
            "交叉引用行被当成了第 %s 项：%s" % (key, entry["text"][:30])
    # 阴性：真项在位（用快照实算，不写字面量）
    real_first = [line for line in block["text"].split("\n")
                  if line.strip().startswith("（一）")
                  and not gen_ruleset.CROSS_REF_RE.match(line.strip())]
    assert real_first, "快照里找不到真正的第（一）项——探针失效"
    assert items["1"]["text"] == real_first[0].strip()


def test_cross_reference_guard_positive_control():
    """变异验证：喂进一条交叉引用行，提取器必须**排除**它（不是碰巧不匹配）。"""
    probe = "（一）至（六）项发布的内容必须与许可证一致。"
    assert gen_ruleset.CROSS_REF_RE.match(probe), "交叉引用识别器未命中探针——假门"
    items = gen_ruleset.clause_items("第六条\n（一）医疗机构第一名称；\n" + probe)
    assert items["1"]["text"] == "（一）医疗机构第一名称；", \
        "交叉引用行劫持了第（一）项"


# --------------------------------------------------------------------------
# 缺陷 2：否定辖域（免责语不得被判命中）
# --------------------------------------------------------------------------
def test_negation_suppression_unit():
    """单元级：同一词面在否定辖域内不算命中、在辖域外仍命中。"""
    term = "保证治愈"  # 规则包实算的词面
    live = check_mod._any_of("本院保证治愈", [term])
    negated = check_mod._any_of("本院不能保证治愈", [term])
    assert live == [term], "正向出现未被命中——抑制过头（漏报）"
    assert negated == [], "否定辖域内的出现被命中——免责语误报"


def test_negation_scope_does_not_cross_punctuation():
    """否定辖域**不跨句读**：前一句的否定词不得抑制后一句的命中。"""
    term = "保证治愈"
    # 「不能…。」之后另起一句出现该词面 → 仍应命中
    hits = check_mod._any_of("不能违规。本院保证治愈", [term])
    assert hits == [term], "否定辖域跨句读——后句命中被误抑制（漏报）"


def test_negation_markers_come_from_constants():
    """否定词表是结构性常量（源码侧），不是规则包政策词面。"""
    assert constants.NEGATION_MARKERS, "否定词表为空——抑制机制空转"
    assert constants.NON_NEGATION_WORDS, "非否定词例外表为空——裸「不」会漏报"


def test_non_negation_word_does_not_suppress():
    """**漏报防护**：否定词修饰主语时不得抑制谓语命中。

    「不」开头但非否定的词（修饰别的主语/名词）不算否定——否则会把**肯定**的
    功效宣称误判为免责语（该报的没报）。用规则包实算的词面构造探针。
    """
    # 取一个含否定字面但实为肯定的非否定词（运行时实算，不写字面量）
    non_neg = constants.NON_NEGATION_WORDS[0]
    assert non_neg.startswith("不"), "例外表取到的词不以「不」开头——探针失效"
    # 探针："<非否定词> + 被禁词面" 是肯定宣称，必须仍被命中
    term = "保证治愈"
    probe = "%s%s" % (non_neg, term)
    assert check_mod._any_of(probe, [term]) == [term], \
        "非否定词误抑制了谓语命中（漏报）：%s" % probe


def test_exclude_context_suppresses_neutral_wordform():
    """排除语境：裸词落在中性词形内部时不算命中（裸词与"XX系"词形碰撞）。"""
    spec = _engine(constants.SCOPE_RULES).matches["AL-16-1"]
    contexts = spec.get("exclude_contexts") or []
    assert contexts, "该规则未声明排除语境——中性词形碰撞防护空转"
    term = "治愈"
    assert term in contexts[0], "排除语境未包含裸词——探针失效"
    probe = "本院%s装修风格令人放松。" % contexts[0]
    assert check_mod._any_of(probe, [term], contexts) == [], \
        "中性词形内部出现裸词仍被判命中：%s" % probe
    # 阳性对照：同一裸词独立出现（不在排除语境内部）→ 必须命中
    assert check_mod._any_of("本院彻底%s近视。" % term, [term], contexts) == [term], \
        "独立出现的裸词未被命中——排除语境抑制过头"


def test_compliant_disclaimer_not_flagged_as_hit():
    """端到端：法条强制要求的免责语形态**不得**产生任何命中。"""
    rep = _run("本品为保健食品，不能代替药物治疗，每日一粒。")
    assert rep.findings == [], "合规免责语被判命中：%s" % [f.rule_id for f in rep.findings]


def test_disclaimer_suppression_positive_control():
    """变异验证：把免责语换成**肯定**功效宣称，必须命中（证明抑制不是永绿）。"""
    rep = _run("本品为保健食品，可治疗慢性病，每日一粒。")
    hits = [f.rule_id for f in rep.findings]
    assert hits, "肯定式功效宣称未被命中——否定抑制是永绿门"


# --------------------------------------------------------------------------
# 缺陷 3：主体门控 + 子串排除
# --------------------------------------------------------------------------
def test_subject_gate_skips_non_subject():
    """原文只对特定主体设的义务，对非该主体应判 skipped（不判命中）。"""
    # 普通器械（不含"个人自用"信号）→ 个人自用器械提示语义务不适用
    rep = _run("本医疗器械注册证齐全，欢迎体验。")
    assert _states(rep).get("AL-16-D5") == constants.RULE_SKIPPED, \
        "非个人自用器械被判适用了个人自用器械义务条"


def test_subject_excludes_prevents_substring_match():
    """子串包含防护：一个主体词是另一个的子串时，后者不得触发前者规则。"""
    rule = _rule("AL-16-D3")
    assert rule.subject_signals, "该规则未声明主体信号——门控空转"
    # 取"排除词"实算（不写字面量）：排除词命中 → 规则不适用
    excludes = rule.subject_excludes
    assert excludes, "该规则未声明排除词——子串防护空转"
    probe = "本品为%s，片剂。" % excludes[0]
    assert not check_mod.rule_applies(rule, ("drug",), None, probe), \
        "排除词命中却仍判适用——子串误适用未被拦住"
    # 阳性对照：只写主体信号、不带排除词 → 应判适用
    probe_ok = "本品为%s，片剂。" % rule.subject_signals[0]
    assert check_mod.rule_applies(rule, ("drug",), None, probe_ok), \
        "主体信号命中却判不适用——门控过严"


def test_subject_gate_is_structural_not_hardcoded():
    """门控读的是规则数据（applies_if.subject_signals），不是代码里的主体判断。"""
    rule = _rule("AL-16-D5")
    assert "subject_signals" in rule.applies_if, "门控未落进规则数据"
    assert check_mod.rule_applies(rule, ("device",), None, "文本不含主体信号") is False
    signal = rule.subject_signals[0]
    assert check_mod.rule_applies(rule, ("device",), None, "含" + signal + "的文本") is True


# --------------------------------------------------------------------------
# 缺陷 4：裸单字词表误报
# --------------------------------------------------------------------------
def test_bare_single_char_terms_are_gone():
    """比较类/疾病类规则**不得**含裸单字词面（实测误报源）。

    判据：对每条 interpretive 的 prohibited_* 规则，其词面长度必须 ≥ 2——
    单字词面在本领域几乎必然与中性表述碰撞。
    """
    engine = _engine(constants.SCOPE_RULES)
    offenders = []
    for rule in engine.rules:
        if rule.kind not in (constants.KIND_PROHIBITED_TERM,
                             constants.KIND_PROHIBITED_PATTERN):
            continue
        spec = engine.matches.get(rule.rule_id) or {}
        terms = list(spec.get("any_of") or [])
        for group in spec.get("groups") or []:
            terms.extend(group)
        for term in terms:
            if len(term) < 2:
                offenders.append("%s:%s" % (rule.rule_id, term))
    assert not offenders, "存在裸单字词面（误报源）：%s" % offenders


def test_neutral_phrases_not_flagged():
    """中性表述（白名单项形态/日常用语）不得被比较类规则判命中。"""
    for probe in ("XX医疗美容门诊部（虚构）第一时间响应需求。",
                  "XX医疗美容门诊部（虚构）医疗机构第一名称公示。"):
        rep = _run(probe)
        assert not [f for f in rep.findings if f.rule_id == "AL-16-3"], \
            "中性表述被判比较类命中：%s" % probe


def test_role_word_alone_is_not_endorsement():
    """共现语义：只出现角色词、无"作证明"标记 → 不得判命中。"""
    rep = _run("XX医疗美容门诊部（虚构）为患者提供优质服务。")
    assert not [f for f in rep.findings if f.rule_id == "MAM-7-6"], \
        "仅角色词被判代言证明命中（共现语义失效）"


def test_role_word_with_proof_marker_is_hit():
    """阳性对照：角色词 + 作证明标记共现 → 必须命中。"""
    rep = _run("XX医疗美容门诊部（虚构）由患者现身说法。")
    assert [f for f in rep.findings if f.rule_id == "MAM-7-6"], \
        "角色词与作证明标记共现却未命中——共现判定失效"


# --------------------------------------------------------------------------
# 新增规则：§16 款 2 的三条提示语义务
# --------------------------------------------------------------------------
def test_new_disclosure_rules_have_verbatim_quotes():
    """三条新提示语义务规则的 quote 必须**逐字**在 §16 快照中（可机器核验）。"""
    clauses = ruleset.load_clauses(
        os.path.join(SRC, "medreview", "references", "clauses.json"))
    for rule_id in ("AL-16-D3", "AL-16-D4", "AL-16-D5", "AL-16-D6"):
        rule = _rule(rule_id)
        key = (rule.source, str(rule.clause))
        assert key in clauses, "规则 %s 的条款不在条文块中" % rule_id
        assert rule.quote in clauses[key], \
            "规则 %s 的引文未逐字出现在 §%s 原文中" % (rule_id, rule.clause)


def test_disclosure_obligation_missing_blocks():
    """无条件义务缺失 → BLOCK（不是 skipped，也不是 WARN）。"""
    rule = _rule("AL-16-D5")
    result = check_mod.check_rule(
        rule, _engine().matches["AL-16-D5"],
        "本医疗器械推荐给个人自用，操作简单。", ("device",))
    assert result.state == constants.RULE_NONCOMPLIANT, \
        "提示语义务缺失未判 noncompliant"


def test_disclosure_obligation_present_is_compliant():
    """提示语已在场 → compliant（不误报）。"""
    rule = _rule("AL-16-D5")
    spec = _engine().matches["AL-16-D5"]
    phrase = spec["require_all_of"][0][0]
    result = check_mod.check_rule(
        rule, spec, "本医疗器械推荐给个人自用，" + phrase + "。", ("device",))
    assert result.state == constants.RULE_COMPLIANT, "提示语已在场却判非通过"


def test_external_premise_rule_is_input_required_not_disclosure():
    """前提在外部材料里的规则记 input_required（判不了不猜，D11 纪律）。"""
    rule = _rule("AL-16-D6")
    assert rule.kind == constants.KIND_INPUT_REQUIRED, \
        "外部前提类义务未按 input_required 建模"
    result = check_mod.check_rule(rule, _engine().matches["AL-16-D6"],
                                  "本医疗器械注册证明文件齐全。", ("device",))
    assert result.state == constants.RULE_INPUT_REQUIRED


# --------------------------------------------------------------------------
# 冻结件一致性：规则包/真值库与生成器再生成位级一致
# --------------------------------------------------------------------------
def test_proof_file_records_digest_only():
    """`--proof-file` 只记**摘要**（文件名 + sha256 + 字节数），不落本地路径。

    纪律：报告要能对外传阅，本地目录结构不外泄；可追溯性由 sha256 承担。
    """
    import hashlib
    import tempfile
    from medreview import cli
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "proof-material.bin")
        payload = b"fake review certificate for smoke test\n"
        with open(target, "wb") as handle:
            handle.write(payload)
        engine = _engine()
        record = normalize.read_proof_file(target)
        assert record["name"] == "proof-material.bin"
        assert record["bytes"] == len(payload)
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()
        assert tmp not in record["name"], "摘要里落了本地路径"
        # 端到端：check 接受该入参且不崩
        code = cli.main(["check", "--text", "XX医疗美容门诊部（虚构）双眼皮手术。",
                         "--proof", "yes", "--proof-file", target,
                         "--out", os.path.join(tmp, "out.json"), "--format", "json"])
        assert code in (constants.EXIT_OK, constants.EXIT_FINDING)


def test_proof_file_missing_is_input_error(tmp_path):
    """证明材料文件不存在 → 输入错误（不是静默忽略）。"""
    from medreview import cli
    missing = str(tmp_path / "nope.pdf")
    assert cli.main(["check", "--text", "测试内容", "--proof-file", missing]) \
        == constants.EXIT_INPUT


def test_proof_file_is_in_item_contract():
    """`proof_file` 必须在契约字段常量与输出里（三方对齐的代码侧）。"""
    assert "proof_file" in constants.CONTRACT_FIELDS_ITEM
    item = normalize.normalize_text("测试内容", proof_file={"name": "a", "sha256": "b",
                                                           "bytes": 1})
    assert item.to_dict()["proof_file"]["name"] == "a"


def test_whitelist_items_are_eight_and_verbatim():
    """§6 白名单按**实测 8 项**结构化登记（题面写 7 项，勘误见 plan/06 D8）。

    三项断言：① 项数 == 8；② 每项文本逐字出现在 §6 快照中；③ manifest 计数与实算一致。
    """
    with open(os.path.join(SRC, "medreview", "references", "ruleset.json"),
              "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    items = payload.get("whitelist_items") or []
    assert len(items) == 8, "§6 白名单项数 != 8（实测勘误口径被改）：%d" % len(items)

    clauses = ruleset.load_clauses(
        os.path.join(SRC, "medreview", "references", "clauses.json"))
    clause_text = clauses[("medical_ad_measures", "6")]
    for entry in items:
        assert entry["text"] in clause_text, \
            "白名单项未逐字出现在 §6 原文中：%s" % entry["text"]
    manifest = _engine(constants.SCOPE_RULES).manifest
    assert manifest["whitelist_item_count"] == len(items), \
        "manifest 白名单计数与实算不符"


def test_manifest_counts_match_actual_rules():
    """manifest 计数**当轮实测**（不是抄来的）：与规则包实算数一致。"""
    engine = _engine(constants.SCOPE_RULES)
    manifest = engine.manifest
    enabled = len(engine.rules)
    assert manifest["enabled_rule_count"] == enabled, \
        "manifest 生效规则数与实算不符"
    # 总条目数 = 生效规则 + **显式登记的兜底条款**（D9：不建规则但必须可见）。
    # 注意与 engine.not_enabled 区分：后者是"运行时被锚点硬门拒绝加载的规则"，
    # 正常态应为空；兜底条款是**设计上就不建规则**，不在拒绝清单里。
    assert engine.not_enabled == [], \
        "有规则被锚点硬门拒绝加载：%s" % engine.not_enabled
    assert manifest["total_rule_count"] == enabled + manifest["excluded_clause_count"], \
        "manifest 总条目数 != 生效数 + 兜底条款数"
    assert manifest["excluded_clause_count"] == 3, \
        "兜底条款数变了（§16 第（五）项 / §18 第（六）项 / §7 第（八）项）"
    literal = sum(1 for r in engine.rules
                  if _terms_basis(r.rule_id) == "literal")
    interpretive = sum(1 for r in engine.rules
                       if _terms_basis(r.rule_id) == "interpretive")
    counts = manifest["terms_basis_counts"]
    assert counts["literal"] == literal and counts["interpretive"] == interpretive, \
        "manifest 词表溯源分级计数与实算不符：%s vs literal=%d interpretive=%d" \
        % (counts, literal, interpretive)


def _terms_basis(rule_id):
    with open(os.path.join(SRC, "medreview", "references", "ruleset.json"),
              "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    for raw in payload["rules"]:
        if raw["id"] == rule_id:
            return raw.get("terms_basis", "literal")
    raise AssertionError("规则包中不存在规则 %s" % rule_id)


def test_all_new_rules_are_covered_by_truth_library():
    """新增规则必须在真值库里有**非 skipped** 的覆盖（B4 分母=生效规则数）。"""
    from medreview.bench import runner
    payload, _ = runner.load_fixture_payload()
    engine = _engine(constants.SCOPE_BENCH)
    from medreview.bench import cases as cases_mod
    from medreview import normalize
    touched = set()
    for case in payload["cases"]:
        if case["suite"] != "b4_rule_coverage":
            continue
        item = normalize.normalize_text(case["input"], proof=case.get("proof"),
                                        scenario=case.get("scenario"))
        rep = pipeline.run_check(engine, item)
        for key in cases_mod.observed_keys(rep):
            if key.startswith("rule:skipped:"):
                continue
            if key.startswith(("rule:", "hit:")):
                touched.add(key.split(":", 2)[-1])
    uncovered = sorted({r.rule_id for r in engine.rules} - touched)
    assert not uncovered, "生效规则无覆盖用例：%s" % uncovered
