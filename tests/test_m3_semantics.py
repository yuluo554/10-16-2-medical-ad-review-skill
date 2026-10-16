"""M3 禁止情形核查的引擎语义回归（**规则层验收 + 四要素导出前断言**）。

本模块把 M3 的六类风险各配单元级守门。判据一律**运行时从冻结规则包实算**，
不在本文件复制词表（否则测试自己变成第二份词表，规则包更新后与数据漂移）。

覆盖的六类风险（均 M3 当轮实测）：

  1. **§7 八项逐项到位**：第（一）至（七）项各有一条可机读判定规则；第（八）项
     兜底**显式不建规则**（D9）——"少建了某项"与"某项是兜底"必须能分辨。
  2. **§6 白名单**：8 项结构化登记 + 汇总式 `MAM-6-W`；"超出白名单"的判定面须
     覆盖**两个方向**（医疗宣称类 + 商业促销/服务类），实测「八折优惠」曾零命中。
  3. **广告法 §16/§18 逐款**：款 1 四项各有规则、款 2 义务条齐备、兜底项不建规则；
     且**比较类**规则必须带"被比较对象"要件（实测「与其他机构合作」误报）。
  4. **互联网办法 §7/§8**：审查证明三态 + 情形门控（`scenario`）+ 变相发布两款。
  5. **Finding 四要素导出前常驻断言**：quote 逐字在快照 / evidence 逐字在文案 /
     锚点可解析 / rule_id 存在——**不满足即拒绝导出**（不是"记得跑那条测试"）。
  6. **同段共现原语**：全局共现会把分属两句的词面凑成一次命中，同段共现能拦住。
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

from medreview import (  # noqa: E402
    check as check_mod, constants, errors, model, normalize, phrase, pipeline, ruleset,
)

import gen_ruleset  # noqa: E402

REFERENCES = os.path.join(SRC, "medreview", "references")


def _engine(scope=constants.SCOPE_CHECK):
    return pipeline.build_engine(scope=scope)


def _run(text, proof=None, scenario=None):
    return pipeline.check_text(_engine(), text, proof=proof, scenario=scenario)


def _states(report):
    return {r.rule_id: r.state for r in report.rule_results}


def _rule_pack():
    with open(os.path.join(REFERENCES, "ruleset.json"), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _rules_of(source, clause):
    payload = _rule_pack()
    return [r for r in payload["rules"]
            if r["source"] == source and str(r["clause"]) == str(clause)]


def _excluded_of(source, clause):
    payload = _rule_pack()
    return [e for e in payload["excluded_clauses"]
            if e["source"] == source and str(e["clause"]) == str(clause)]


# --------------------------------------------------------------------------
# 风险 1：§7 八项逐项到位（第（一）至（七）项建规则；第（八）项兜底不建）
# --------------------------------------------------------------------------
def test_mam_clause_7_items_one_to_seven_each_have_a_rule():
    """《医疗广告管理办法》§7 第（一）至（七）项**每项都有可机读判定规则**。

    判据：项号 → 规则 id 的映射齐备（不是"总共七条规则"——两条规则挂在同一项上
    也能凑够七条，而漏掉一项不红）。这是"逐项建规则"的机器可验形态。
    """
    rules = _rules_of("medical_ad_measures", 7)
    items = sorted({r["item"] for r in rules if r.get("item")})
    assert items == [str(n) for n in range(1, 8)], \
        "§7 第（一）至（七）项未逐项建规则：实得项号 %s" % items
    # 每项恰有 ≥1 条规则，且规则引文必须锚到该项（quote 含该项序号形态）
    for rule in rules:
        assert rule["kind"] in constants.KINDS, "§7 规则 kind 非法：%s" % rule["id"]
        assert rule["applies_if"]["categories"] == ["medical"], \
            "§7 是医疗广告专条，适用域应为 medical：%s" % rule["id"]


def test_mam_clause_7_item_8_is_catch_all_and_not_a_rule():
    """§7 第（八）项是兜底条款 → **显式不建规则**，但必须在未启用清单可见（D9）。

    两个方向都断：① 不存在挂在第（八）项上的规则；② 兜底条款在
    `excluded_clauses` 里带 reason 与 code 登记（"不建"不等于"消失"）。
    """
    rules = _rules_of("medical_ad_measures", 7)
    assert not [r for r in rules if r.get("item") == "8"], \
        "兜底条款（第（八）项）被建了规则——违反 D9（无可机读判定要素）"
    excluded = _excluded_of("medical_ad_measures", 7)
    assert [e for e in excluded if e["item"] == "8"], \
        "§7 第（八）项兜底条款未进未启用清单（不建规则 ≠ 不可见）"
    entry = [e for e in excluded if e["item"] == "8"][0]
    assert entry["reason"] and entry["code"] == "catch_all_clause", \
        "兜底条款登记缺 reason/code（不可追溯）"


def test_every_catch_all_clause_is_registered():
    """三处兜底条款（§7（八）/§16（五）/§18（六））**全部**显式登记为不建规则。"""
    expected = {("medical_ad_measures", "7", "8"),
                ("advertising_law", "16", "5"),
                ("advertising_law", "18", "6")}
    payload = _rule_pack()
    actual = {(e["source"], str(e["clause"]), e["item"]) for e in payload["excluded_clauses"]}
    assert actual == expected, "兜底条款登记集合不符：%s" % sorted(actual)
    # 反向：兜底项上不得出现任何规则
    for source, clause, item in expected:
        offenders = [r["id"] for r in _rules_of(source, clause) if r.get("item") == item]
        assert not offenders, "兜底项被建了规则：%s" % offenders


def test_clause_7_1_medical_technology_rule_has_verbatim_terms():
    """§7（一）「涉及医疗技术、诊疗方法、疾病名称、药物」——四个词面逐字在原文中。"""
    rule = [r for r in _rules_of("medical_ad_measures", 7) if r["item"] == "1"][0]
    assert rule["terms_basis"] == "literal", "§7（一）是原文逐字枚举，应为 literal"
    terms = rule["match"]["any_of"]
    clauses = ruleset.load_clauses(os.path.join(REFERENCES, "clauses.json"))
    clause_text = clauses[("medical_ad_measures", "7")]
    for term in terms:
        assert term in clause_text, "§7（一）词面未逐字在原文中：%s" % term


# --------------------------------------------------------------------------
# 风险 2：§6 白名单（8 项登记 + 超出白名单判定面**两个方向**）
# --------------------------------------------------------------------------
def test_whitelist_scope_covers_medical_claims_direction():
    """超出白名单方向①：**医疗宣称类**表述（疗效/无痛/专家坐诊…）应判 warn。"""
    engine = _engine()
    spec = engine.matches.get("MAM-6-W") or {}
    terms = spec.get("any_of") or []
    assert terms, "MAM-6-W 词表为空——超出白名单判定面空转"
    # 用词表实算构造探针（本文件零词面）：每个词单独出现必须命中
    for term in terms:
        rep = _run("XX医疗美容门诊部（虚构）%s，欢迎咨询。" % term)
        assert "MAM-6-W" in [f.rule_id for f in rep.findings], \
            "白名单外表述 %r 未判 warn（判定面缺口）" % term


def test_whitelist_scope_covers_commercial_promotion_direction():
    """超出白名单方向②：**商业促销/服务类**表述同样不在 8 项白名单内。

    M3 实测缺口：原词表只覆盖医疗宣称方向，「本月八折优惠」「服务态度好」
    零命中——而 §6 是**穷举式**白名单（"内容**仅限于**以下项目"），
    促销与服务信息同样超出范围。两个方向都必须有判定面。
    """
    engine = _engine()
    terms = (engine.matches.get("MAM-6-W") or {}).get("any_of") or []
    # 用**白名单项之外**的商业词实算构造探针：取词表里不含白名单项字样的词
    whitelist_words = ["名称", "地址", "所有制", "类别", "科目", "床位", "时间", "电话"]
    commercial = [t for t in terms
                  if not any(w in t for w in whitelist_words)
                  and any(k in t for k in ("优惠", "折扣", "促销", "限时", "免费"))]
    assert commercial, "MAM-6-W 未覆盖商业促销方向（白名单外判定面缺口）"
    for term in commercial:
        rep = _run("XX医疗美容门诊部（虚构）%s，欢迎光临。" % term)
        assert "MAM-6-W" in [f.rule_id for f in rep.findings], \
            "白名单外促销表述 %r 未判 warn" % term


def test_whitelist_inside_items_are_not_flagged():
    """白名单**项内**内容（8 项本身）不得被判超出白名单。

    用 §6 快照实算的 8 项文本构造探针——"白名单项被判违规"是方向性错误
    （把允许的内容当禁止的），比漏报更坏。
    """
    payload = _rule_pack()
    items = payload["whitelist_items"]
    assert len(items) == 8, "白名单项数 != 8（实测勘误口径被改）"
    for entry in items:
        # 取项文本里的核心名词（去掉序号与标点）构造探针
        core = entry["text"].strip("；。").split("）")[-1]
        rep = _run("XX医疗美容门诊部（虚构）%s，欢迎咨询。" % core)
        offenders = [f.rule_id for f in rep.findings
                     if f.rule_id in ("MAM-6-W", "MAM-7-1", "MAM-7-3")]
        assert not offenders, "白名单项内内容被判命中：%s → %s" % (core, offenders)


# --------------------------------------------------------------------------
# 风险 3：广告法 §16/§18 逐款（含比较类规则的**被比较对象**要件）
# --------------------------------------------------------------------------
def test_al_clause_16_items_one_to_four_each_have_a_rule():
    """§16 第（一）至（四）项各有一条规则；第（五）项兜底不建。

    适用域断言只加在**项级规则**（款 1 的主体限制是"医疗、药品、医疗器械"）；
    条款级义务条（`AL-16-D*`）原文自带**更窄的主体限制**（处方药/非处方药/
    个人自用器械），适用域本就该窄于项级——断言"所有规则同域"会把 D16 的主体
    门控判成缺陷（那是特性，不是 bug）。
    """
    rules = _rules_of("advertising_law", 16)
    items = sorted({r["item"] for r in rules if r.get("item")})
    assert items == ["1", "2", "3", "4"], "§16 项号覆盖不符：%s" % items
    for rule in rules:
        if not rule.get("item"):
            continue  # 条款级义务条另有主体限制（见 docstring）
        assert set(rule["applies_if"]["categories"]) == {"medical", "drug", "device"}, \
            "§16 项级规则适用域应为医疗/药品/器械：%s" % rule["id"]


def test_al_clause_18_items_one_to_five_each_have_a_rule():
    """§18 第（一）至（五）项各有一条规则；第（六）项兜底不建。"""
    rules = _rules_of("advertising_law", 18)
    items = sorted({r["item"] for r in rules if r.get("item")})
    assert items == ["1", "2", "3", "4", "5"], "§18 项号覆盖不符：%s" % items
    for rule in rules:
        assert rule["applies_if"]["categories"] == ["health_food"], \
            "§18 只管保健食品广告：%s" % rule["id"]


def test_al_16_3_comparison_requires_comparison_target():
    """§16（三）**必须带"被比较对象"要件**——原文是"与其他…**比较**"。

    M3 实测误报：裸比较标记把「与其他机构开展学术交流」「领先于行业标准」
    「最先进」（无任何被比较对象）判 BLOCK。故规则须落成**同段共现**
    （比较标记 × 同类指向对象）。
    """
    rule = [r for r in _rules_of("advertising_law", 16) if r["item"] == "3"][0]
    spec = rule["match"]
    assert spec.get("segment_groups"), \
        "§16（三）未落成同段共现——缺被比较对象要件（实测误报源）"
    assert len(spec["segment_groups"]) >= 2, "同段共现须含「标记组 + 对象组」两组"
    # 阴性：非比较语义的搭配不得命中
    engine = _engine()
    for probe in ("XX医疗美容门诊部（虚构）与其他机构开展学术交流。",
                  "XX医疗美容门诊部（虚构）领先于行业标准，服务规范。",
                  "本医疗器械最先进，值得信赖。"):
        rep = _run(probe)
        assert "AL-16-3" not in [f.rule_id for f in rep.findings], \
            "非比较语义被误判为比较：%s" % probe


def test_al_16_3_comparison_true_positive_still_hits():
    """阳性对照：真正"与其他药品/器械/医疗机构比较"仍必须命中（防改哑）。"""
    for probe in ("本医疗器械效果优于其他医疗器械。",
                  "本医疗器械最先进，领先于其他医疗机构。",
                  "本院服务水平超过其他医疗机构。"):
        rep = _run(probe)
        assert "AL-16-3" in [f.rule_id for f in rep.findings], \
            "真比较语义未命中（规则被改哑）：%s" % probe


def test_al_18_4_comparison_requires_target():
    """§18（四）「与**药品、其他保健食品**进行比较」——对象同样是构成要件。

    M3 实测误报：裸「好于」把「本品保健食品**口感好于普通食品**」判 BLOCK
    （对象是普通食品，不是药品/其他保健食品）。
    """
    rule = [r for r in _rules_of("advertising_law", 18) if r["item"] == "4"][0]
    assert rule["match"].get("segment_groups"), \
        "§18（四）未落成同段共现——缺被比较对象要件"
    rep = _run("本品保健食品口感好于普通食品，每日一粒。")
    assert "AL-18-4" not in [f.rule_id for f in rep.findings], \
        "与普通食品的口感比较被误判（对象不在原文点名范围内）"
    # 阳性对照
    rep = _run("本品保健食品优于其他保健食品，本品不能代替药物。")
    assert "AL-18-4" in [f.rule_id for f in rep.findings], \
        "与其他保健食品比较未命中（规则被改哑）"


def test_al_16_d2_requires_both_contraindication_and_adverse_reaction():
    """§16 款 2「应当显著标明**禁忌、不良反应**」——并列宾语，**两项都要标**。

    原实现把两项放进同一组（组内任一即可）→「只标禁忌、未标不良反应」被判
    compliant（漏报）。M3 改拆两组：缺任一组即 noncompliant。
    """
    rule = [r for r in _rules_of("advertising_law", 16) if r["id"] == "AL-16-D2"][0]
    groups = rule["match"]["require_all_of"]
    assert len(groups) == 2, \
        "并列宾语未拆成两组（组内任一即可 = 只标一项也算履行，漏报）"
    # 只标其一 → 命中；两项都标 → 通过
    only_one = _run("本品为药品片剂，禁忌详见说明书。")
    assert "AL-16-D2" in [f.rule_id for f in only_one.findings], \
        "只标禁忌、未标不良反应却判通过（漏报）"
    both = _run("本品为药品片剂，禁忌、不良反应详见说明书。")
    assert "AL-16-D2" not in [f.rule_id for f in both.findings], \
        "两项均已标明却判命中（误报）"


def test_terms_basis_literal_terms_are_verbatim_in_clause():
    """`terms_basis=literal` 的规则，其**全部**匹配词面须逐字在原文条款中。

    这是分级口径的可机器核验形态：literal 声称"逐字来自原文"，就必须真逐字；
    否则"分级"只是标签（把解释层冒充成原文层）。
    """
    engine = _engine(constants.SCOPE_RULES)
    clauses = ruleset.load_clauses(os.path.join(REFERENCES, "clauses.json"))
    offenders = []
    for rule in engine.rules:
        payload = _rule_pack()
        basis = [r for r in payload["rules"] if r["id"] == rule.rule_id][0].get("terms_basis")
        if basis != "literal":
            continue
        clause_text = clauses.get((rule.source, str(rule.clause)), "")
        spec = engine.matches.get(rule.rule_id) or {}
        terms = list(spec.get("any_of") or [])
        for group in spec.get("groups") or []:
            terms.extend(group)
        for group in spec.get("segment_groups") or []:
            terms.extend(group)
        for group in spec.get("require_all_of") or []:
            terms.extend(group)
        terms.extend(spec.get("knowledge_terms") or [])
        terms.extend(spec.get("commerce_terms") or [])
        for term in terms:
            if term and term not in clause_text:
                offenders.append("%s:%s" % (rule.rule_id, term))
    assert not offenders, "literal 词面未逐字在原文中（分级口径失真）：%s" % offenders


# --------------------------------------------------------------------------
# 风险 4：互联网办法 §7/§8（三态 + 情形门控 + 变相发布两款）
# --------------------------------------------------------------------------
def test_iam_7_1_review_proof_three_states():
    """§7 审查证明**三态可判定**（不是"缺材料垃圾桶"）。

    `proof=no` → noncompliant（无条件义务缺失，**不许记成不适用**）；
    未提供 → input_required（**绝不静默判 compliant**）；
    `proof=yes` → compliant。
    """
    text = "XX医疗美容门诊部（虚构）双眼皮手术。"
    assert _states(_run(text, proof="no")).get("IAM-7-1") == constants.RULE_NONCOMPLIANT
    assert _states(_run(text)).get("IAM-7-1") == constants.RULE_INPUT_REQUIRED
    assert _states(_run(text, proof="yes")).get("IAM-7-1") == constants.RULE_COMPLIANT
    # proof=no 的结论必须是 BLOCK（"查出了问题"），不是 WARN
    assert _run(text, proof="no").grade == constants.GRADE_BLOCK


def test_iam_7_2_scenario_gate():
    """§7 款 2（按审查通过内容发布）**只对已发布情形生效**。

    原文以"已经审查通过"为前提 → 发布前自查时该条不适用（skipped），
    而不是记"待补材料"（把"不适用"与"判不了"混为一谈会虚高结论）。
    """
    text = "XX医疗美容门诊部（虚构）双眼皮手术。"
    pre = _states(_run(text))
    assert pre.get("IAM-7-2") == constants.RULE_SKIPPED, \
        "发布前自查时 §7 款 2 被判适用（情形门控失效）"
    published = _states(_run(text, scenario="published"))
    assert published.get("IAM-7-2") == constants.RULE_INPUT_REQUIRED, \
        "已发布情形下 §7 款 2 未参与判定"


def test_iam_7_scenario_values_come_from_rule_data():
    """情形门控读的是规则数据（`applies_if.scenario`），不是代码里的情形判断。"""
    rule = [r for r in _rules_of("internet_ad_measures", 7) if r["id"] == "IAM-7-2"][0]
    assert rule["applies_if"].get("scenario") == ["published"], \
        "情形限制未落进规则数据"
    engine = _engine()
    loaded = [r for r in engine.rules if r.rule_id == "IAM-7-2"][0]
    assert loaded.scenarios == ("published",)
    assert check_mod.rule_applies(loaded, ("medical",), "prepublication", "文本") is False
    assert check_mod.rule_applies(loaded, ("medical",), "published", "文本") is True


def test_iam_8_both_paragraphs_have_rules():
    """§8 两款各有一条 `variant_publish` 规则（款 1 商品信息 / 款 2 联系方式）。"""
    rules = _rules_of("internet_ad_measures", 8)
    assert len(rules) == 2, "§8 未按两款各建一条规则：实得 %d" % len(rules)
    for rule in rules:
        assert rule["kind"] == constants.KIND_VARIANT_PUBLISH
        spec = rule["match"]
        assert spec.get("knowledge_terms") and spec.get("commerce_terms"), \
            "变相发布规则缺共现词表：%s" % rule["id"]
    # 两款的对象词表必须**不同**（款 1 是商品/服务信息，款 2 是联系方式/购物链接）
    first = set(rules[0]["match"]["commerce_terms"])
    second = set(rules[1]["match"]["commerce_terms"])
    assert first != second, "§8 两款用了同一份对象词表（未分款建规则）"


def test_variant_publish_is_block_not_warn():
    """§8 变相发布是**确定性禁止情形** → BLOCK（不是 WARN）。"""
    rep = _run("XX中医诊所（虚构）分享养生知识，欢迎致电预约。")
    assert rep.grade == constants.GRADE_BLOCK
    assert "IAM-8-1" in [f.rule_id for f in rep.findings]


def test_variant_publish_requires_cooccurrence_end_to_end():
    """共现语义端到端：只有知识形态、无商品/服务信息 → 不得命中。

    探针用**词表实算**构造（本文件零词面），且刻意把两类词**分置两句**——
    同一句里同时出现知识形态与商品信息才算共现（"XX诊所分享养生知识，欢迎
    致电预约"才是真共现形态）。
    """
    engine = _engine()
    knowledge = engine.matches["IAM-8-1"]["knowledge_terms"][0]
    commerce = engine.matches["IAM-8-1"]["commerce_terms"][0]
    # 阴性：只有知识形态
    only_knowledge = _run("本节%s分享内容，欢迎阅读。" % knowledge)
    assert "IAM-8-1" not in [f.rule_id for f in only_knowledge.findings], \
        "仅知识形态即判变相发布（共现语义失效）"
    # 阳性对照：两类词同现 → 必须命中
    both = _run("本节%s分享内容，欢迎%s。" % (knowledge, commerce))
    assert "IAM-8-1" in [f.rule_id for f in both.findings], \
        "知识形态与商品信息共现却未命中（共现判定失效）"


# --------------------------------------------------------------------------
# 风险 5：Finding 四要素**导出前常驻断言**（不满足即拒绝导出）
# --------------------------------------------------------------------------
def test_assert_findings_traceable_rejects_broken_quote():
    """变异验证：伪造引文（quote 不在快照中）→ 断言必须拒绝导出。"""
    engine = _engine()
    item = normalize.normalize_text("XX医疗美容门诊部（虚构）保证治愈。")
    rep = pipeline.run_check(engine, item)
    rule = [r for r in engine.rules if r.rule_id == "MAM-7-2"][0]
    bogus = model.Finding(rule.rule_id, rule.anchor, "这句原文不存在于任何快照中",
                          "保证治愈", rule.severity, rule.kind)
    rep.rule_results = [r for r in rep.rule_results if r.rule_id != rule.rule_id]
    rep.rule_results.append(model.RuleResult(rule.rule_id,
                                             constants.RULE_NONCOMPLIANT, [bogus]))
    with pytest.raises(errors.FindingIncomplete):
        pipeline.assert_findings_traceable(rep, engine, item.text)


def test_assert_findings_traceable_rejects_foreign_evidence():
    """变异验证：evidence 不是文案片段（引用用户没写过的文字）→ 拒绝导出。"""
    engine = _engine()
    text = "XX医疗美容门诊部（虚构）保证治愈。"
    item = normalize.normalize_text(text)
    rep = pipeline.run_check(engine, item)
    rule = [r for r in engine.rules if r.rule_id == "MAM-7-2"][0]
    foreign = model.Finding(rule.rule_id, rule.anchor, rule.quote,
                            "用户从未写过的字面", rule.severity, rule.kind)
    rep.rule_results = [model.RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT,
                                         [foreign])]
    with pytest.raises(errors.FindingIncomplete):
        pipeline.assert_findings_traceable(rep, engine, text)


def test_assert_findings_traceable_rejects_unknown_rule_id():
    """变异验证：rule_id 不在生效规则包中 → 拒绝导出。"""
    engine = _engine()
    text = "XX医疗美容门诊部（虚构）保证治愈。"
    item = normalize.normalize_text(text)
    rep = pipeline.run_check(engine, item)
    ghost = model.Finding("NO-SUCH-RULE", "《某法》§1", "任意", "保证治愈",
                          constants.SEVERITY_BLOCK, constants.KIND_PROHIBITED_TERM)
    rep.rule_results = [model.RuleResult("NO-SUCH-RULE", constants.RULE_NONCOMPLIANT,
                                         [ghost])]
    with pytest.raises(errors.FindingIncomplete):
        pipeline.assert_findings_traceable(rep, engine, text)


def test_assert_findings_traceable_rejects_mismatched_anchor():
    """变异验证：锚点与规则条款不符（条款号写错）→ 拒绝导出。"""
    engine = _engine()
    text = "XX医疗美容门诊部（虚构）保证治愈。"
    item = normalize.normalize_text(text)
    rep = pipeline.run_check(engine, item)
    rule = [r for r in engine.rules if r.rule_id == "MAM-7-2"][0]
    wrong = model.Finding(rule.rule_id, "《中华人民共和国广告法》§999", rule.quote,
                          "保证治愈", rule.severity, rule.kind)
    rep.rule_results = [model.RuleResult(rule.rule_id, constants.RULE_NONCOMPLIANT,
                                         [wrong])]
    with pytest.raises(errors.FindingIncomplete):
        pipeline.assert_findings_traceable(rep, engine, text)


def test_assert_findings_traceable_passes_on_real_report():
    """阴性对照：真实报告的四要素断言必须通过（断言不是永红）。"""
    engine = _engine()
    text = "XX医疗美容门诊部（虚构）保证治愈，无效退款。"
    item = normalize.normalize_text(text)
    rep = pipeline.run_check(engine, item)
    assert rep.findings, "探针未产生任何命中——扫描面为空（假门）"
    assert pipeline.assert_findings_traceable(rep, engine, text) is True


def test_cli_exit_code_on_traceability_failure(monkeypatch):
    """端到端：断言失败时 CLI 返回 EXIT_FINDING（1），**不是**静默出件。"""
    from medreview import cli

    def boom(report, engine, text):
        raise errors.FindingIncomplete("注入缺陷：四要素不全", code="finding_incomplete")

    monkeypatch.setattr(pipeline, "assert_findings_traceable", boom)
    code = cli.main(["check", "--text", "XX医疗美容门诊部（虚构）保证治愈。"])
    assert code == constants.EXIT_FINDING


def test_evidence_kind_is_structural_not_string_prefix():
    """证据性质是**结构字段**（`evidence_kind`），不靠字符串前缀特判。

    判据：义务缺失类的证据字符串**改措辞**后仍应被正确分类——若分类靠
    `evidence.startswith("缺失应显著标明")`，改一句文案就能绕过门禁。
    """
    assert constants.EVIDENCE_TEXT_SPAN in constants.EVIDENCE_KINDS
    assert constants.EVIDENCE_OBLIGATION_MISSING in constants.EVIDENCE_KINDS
    rep = _run("本品为保健食品，蓝帽子认证，每日一粒。")
    missing = [f for f in rep.findings if f.rule_id == "AL-18-D1"]
    assert missing, "探针未触发义务缺失类命中"
    assert all(f.evidence_kind == constants.EVIDENCE_OBLIGATION_MISSING for f in missing), \
        "义务缺失类命中的证据性质未被结构化标注"


# --------------------------------------------------------------------------
# 风险 6：同段共现原语（分属两句的词面不得凑成一次命中）
# --------------------------------------------------------------------------
def test_cooccur_in_segment_requires_same_segment():
    """同一句读段内的共现 → 命中；**分属两句**的词面 → 不命中。"""
    groups = [["甲"], ["乙"]]
    assert phrase.cooccur_in_segment("本店有甲和乙。", groups), \
        "同段共现未命中（原语失效）"
    assert not phrase.cooccur_in_segment("本店有甲，也有乙。", groups), \
        "跨句读的词面被凑成一次命中（同段约束失效）"


def test_cooccur_in_segment_positive_control():
    """阳性对照：同一段里两组齐备必须命中（防"永假"）。"""
    groups = [["比较标记"], ["对象"]]
    hits = phrase.cooccur_in_segment("效果比较标记优于对象，欢迎咨询。", groups)
    assert hits, "同段共现恒不命中——原语被改哑"


def test_match_rule_segment_groups_end_to_end():
    """`match_rule` 的 `segment_groups` 与 `phrase` 原语同源（不另写一份）。"""
    spec = {"segment_groups": [["甲"], ["乙"]]}
    rule = model.Rule("R", "s", "1", None, "a", "q", "verified", "verified",
                      constants.KIND_PROHIBITED_PATTERN, constants.SEVERITY_BLOCK,
                      {"categories": ["medical"]})
    assert check_mod.match_rule(rule, spec, "本店有甲和乙。")
    assert check_mod.match_rule(rule, spec, "本店有甲，也有乙。") == []


def test_segment_delimiters_shared_with_negation_scope():
    """同段共现与否定辖域**共用同一套句读分隔符**（一个定义，不是两份）。"""
    assert phrase.constants.SEGMENT_DELIMITERS is constants.SEGMENT_DELIMITERS
    # 两者对"句读"的切分必须一致：同一文本的段数相同
    text = "第一句，第二句。第三句；第四句"
    assert len(phrase.segments(text)) == 4, "句读切分口径不符"


# --------------------------------------------------------------------------
# 中性词形排除语境：临床/营养学术语不得被判命中（M3 实测）
# --------------------------------------------------------------------------
def test_clinical_terms_are_not_flagged():
    """临床术式名（含被禁词面）不得被判命中：根治性手术/根治术/根治率。"""
    engine = _engine()
    spec = engine.matches["AL-16-1"]
    contexts = spec.get("exclude_contexts") or []
    assert contexts, "AL-16-1 未登记排除语境"
    probes = [c for c in contexts if c in ("根治性", "根治术", "根治率")]
    assert probes, "临床术式类排除语境缺失（实测误报源未处置）"
    for context in probes:
        rep = _run("XX市第X医院（虚构）开展肿瘤%s手术，术后护理规范。" % context)
        offenders = [f.rule_id for f in rep.findings if f.rule_id in ("AL-16-1", "MAM-7-2")]
        assert not offenders, "临床术语 %r 被判疗效承诺命中：%s" % (context, offenders)


def test_nutrition_terms_are_not_flagged():
    """营养学术语（含「必需」）不得被判"为保障健康所必需"的声称。"""
    engine = _engine()
    spec = engine.matches["AL-18-3"]
    contexts = spec.get("exclude_contexts") or []
    assert contexts, "AL-18-3 未登记排除语境（营养学术语碰撞未处置）"
    probes = [c for c in contexts if "必需" in c]
    assert probes, "营养学术语类排除语境缺失"
    for context in probes:
        rep = _run("本品保健食品含人体%s，本品不能代替药物。" % context)
        assert "AL-18-3" not in [f.rule_id for f in rep.findings], \
            "营养学术语 %r 被判必需声称命中" % context


def test_polarity_marker_consistency():
    """斥否类动词与「严禁」同族：同极性的否定表述结果必须一致。

    M3 实测不一致：一句被抑制、另一句被判命中（同一极性、两种结果）。
    """
    engine = _engine()
    spec = engine.matches["MAM-7-4"]
    terms = spec.get("any_of") or []
    assert terms, "MAM-7-4 词表为空"
    term = terms[0]
    markers = [m for m in constants.NEGATION_MARKERS if m in ("严禁", "抵制")]
    assert len(markers) == 2, "斥否类动词表不完整（同族不一致）"
    results = []
    for marker in markers:
        rep = _run("XX医疗美容门诊部（虚构）%s%s低俗内容。" % (marker, term))
        results.append("MAM-7-4" in [f.rule_id for f in rep.findings])
    assert len(set(results)) == 1, \
        "同极性否定表述结果不一致（%s）——极性词表缺项" % dict(zip(markers, results))
    assert results[0] is False, "斥否类表述被判命中（合规表态被报成违法）"


# --------------------------------------------------------------------------
# 规则包与真值库冻结一致（M3 收尾复跑）
# --------------------------------------------------------------------------
def test_manifest_counts_match_after_m3():
    """manifest 计数**当轮实算**（M3 改规则后必须与实算一致）。"""
    engine = _engine(constants.SCOPE_RULES)
    manifest = engine.manifest
    assert manifest["enabled_rule_count"] == len(engine.rules)
    assert manifest["excluded_clause_count"] == len(_rule_pack()["excluded_clauses"])
    assert manifest["total_rule_count"] == (manifest["enabled_rule_count"]
                                            + manifest["excluded_clause_count"])
    assert engine.not_enabled == [], "有规则被锚点硬门拒绝加载：%s" % engine.not_enabled
    literal = sum(1 for r in _rule_pack()["rules"] if r.get("terms_basis") == "literal")
    interpretive = sum(1 for r in _rule_pack()["rules"]
                       if r.get("terms_basis") == "interpretive")
    counts = manifest["terms_basis_counts"]
    assert counts["literal"] == literal and counts["interpretive"] == interpretive, \
        "词表溯源分级计数与实算不符：%s" % counts


def test_ruleset_version_fingerprints_rule_data():
    """版本号指纹到**全部判定数据**（改任一词表/规则 → 版本号必变）。

    判据：用与生成器同源的规范化方式重算哈希，必须等于 manifest 的版本号。
    """
    import hashlib
    payload = _rule_pack()
    rules = [{k: v for k, v in r.items() if k not in ("official_url", "basis_date")}
             for r in payload["rules"]]
    content = json.dumps({"rules": rules, "excluded": payload["excluded_clauses"],
                          "whitelist": payload["whitelist_items"],
                          "category_rules": payload["category_rules"],
                          "variant_rules": payload["variant_rules"]},
                         sort_keys=True, ensure_ascii=False)
    expected = "ruleset-" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    assert payload["ruleset_version"] == expected, \
        "版本号未指纹到全部判定数据（版本化冻结假门）"
