"""M2 品类判定器的引擎语义回归（**词表即数据，数据即门禁**）。

本模块把 M2 的三类风险各配单元级守门——基准用例能挡住"整体跑歪"，
但挡不住"某类词表被删空/反例被摘掉"这类**静默失效**（判定仍在跑，只是永远
判不出品类，全量落 NOT_ASSESSED）。每条都配阳性/阴性两侧。

覆盖的三类风险（均 M2 当轮实测）：
  1. **信号词表静默失效**：某品类词表被清空/删减 → 该类内容一律判不出品类
     （不报错，只是结论变 NOT_ASSESSED）。故门禁断言"每品类词表非空 + 每个
     正向词真能判出该品类"（用词表实算探针，不在测试里复制词面）。
  2. **反例结构缺失/装饰性**：只有正向词表时"信号词表写错"永不红——实测
     「宠物医院」被判医疗品类、「健身器械」被判器械品类、「国家药品监督管理
     局」被判药品品类。故门禁断言"每类都有反例结构，且反例确实包住本类某个
     正向词"（防装饰性排除：写一条与词表无关的排除词也满足"非空"）。
  3. **品类判定的词面原语与规则核查分家**：品类命中若不走否定辖域/排除语境，
     会自成第二套口径。故门禁断言"品类判定确实受排除语境约束"（阴性 + 阳性）。

纪律：词面一律**运行时从冻结规则包实算**，不在本文件复制词表（否则测试自己
变成第二份词表，规则包更新后与数据漂移）。
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

from medreview import categorize, constants, normalize, pipeline, phrase  # noqa: E402

import gen_ruleset  # noqa: E402


def _engine(scope=constants.SCOPE_RULES):
    return pipeline.build_engine(scope=scope)


def _run(text):
    return pipeline.check_text(pipeline.build_engine(), text)


def _category_entry(category, engine=None):
    engine = engine or _engine()
    for entry in engine.category_rules:
        if entry["category"] == category:
            return entry
    raise AssertionError("规则包中不存在品类条目 %s" % category)


def _rule_pack():
    with open(os.path.join(SRC, "medreview", "references", "ruleset.json"),
              "r", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------
# 风险 1：信号词表静默失效（词表被删空 → 永远判不出该品类）
# --------------------------------------------------------------------------
def test_every_category_has_signal_terms():
    """每个品类的信号词表非空（词表清空是**静默失效**：判定仍跑，只是判不出）。"""
    engine = _engine()
    categories = {e["category"] for e in engine.category_rules}
    assert categories == set(constants.CATEGORIES), \
        "品类条目未覆盖全部品类枚举：%s" % sorted(categories)
    for entry in engine.category_rules:
        assert entry.get("terms"), "品类 %s 的信号词表为空" % entry["category"]


def test_signal_terms_actually_categorize():
    """**词表实算探针**：每个品类的每个正向词，单独出现在文本里必须判出该品类。

    阳性对照（缺了就是"词表写了但从不生效"的假门）：逐词构造探针，
    断言该词真能触发本品类。用**词表自身**构造探针，不在测试里复制词面。
    """
    engine = _engine()
    for entry in engine.category_rules:
        category = entry["category"]
        contexts = entry.get("exclude_contexts") or ()
        for term in entry["terms"]:
            # 若该词本身落在某个排除语境内部，则它**天然无法**单独命中——
            # 这是设计使然（该词面只在中性词形里出现），跳过而非误报。
            if phrase.excluded_context(term, term, 0, contexts):
                continue
            item = normalize.normalize_text("本节讨论%s相关内容。" % term)
            result = categorize.categorize(item, engine.category_rules, None)
            assert category in result.categories, \
                "词表词面 %r 未能判出品类 %s（词表写了但不生效）" % (term, category)


def test_manifest_category_counts_match_actual():
    """manifest 的品类计数**当轮实算**（词表被删空/缩水必须红）。"""
    engine = _engine()
    manifest = engine.manifest
    actual_signals = {e["category"]: len(e["terms"]) for e in engine.category_rules}
    actual_excludes = {e["category"]: len(e.get("exclude_contexts") or ())
                       for e in engine.category_rules}
    assert manifest["category_rule_count"] == len(engine.category_rules), \
        "manifest 品类条目数与实算不符"
    assert manifest["category_signal_counts"] == actual_signals, \
        "manifest 品类信号词计数与实算不符：%s vs %s" \
        % (manifest["category_signal_counts"], actual_signals)
    assert manifest["category_exclude_counts"] == actual_excludes, \
        "manifest 品类反例计数与实算不符：%s vs %s" \
        % (manifest["category_exclude_counts"], actual_excludes)
    assert manifest["variant_rule_count"] == len(engine.variant_rules), \
        "manifest 变相发布条目数与实算不符"


def test_ruleset_version_fingerprints_category_tables():
    """版本号必须**指纹到品类/变相发布词表**（只改词表版本号也得变）。

    判据：版本号的哈希输入里若不含这两张表，"版本化冻结"就是假门——
    词表改了版本号不动，消费者无法据版本号判断判定数据是否变过。
    """
    import hashlib
    payload = _rule_pack()
    # 用与生成器**同源**的规范化方式重算（生成器口径：sort_keys + 排除 url/basis_date）
    rules = [{k: v for k, v in r.items() if k not in ("official_url", "basis_date")}
             for r in payload["rules"]]
    content = json.dumps({"rules": rules, "excluded": payload["excluded_clauses"],
                          "whitelist": payload["whitelist_items"],
                          "category_rules": payload["category_rules"],
                          "variant_rules": payload["variant_rules"]},
                         sort_keys=True, ensure_ascii=False)
    expected = "ruleset-" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    assert payload["ruleset_version"] == expected, \
        "版本号未指纹到品类/变相发布词表（改词表版本号不动 = 版本化冻结假门）"


# --------------------------------------------------------------------------
# 风险 2：反例结构缺失 / 装饰性（信号词表写错永不红）
# --------------------------------------------------------------------------
def test_every_category_has_exclude_contexts():
    """每个品类都必须登记**反例结构**（否则"信号词表写错"永不红）。"""
    engine = _engine()
    for entry in engine.category_rules:
        assert entry.get("exclude_contexts"), \
            "品类 %s 未登记反例结构（信号词表写错将永不红）" % entry["category"]


def test_exclude_contexts_are_not_decorative():
    """反例结构必须**确实包住本类某个正向词**——防装饰性排除。

    判据：若一条排除语境里不含本类任何正向词，它就拦不住任何本类命中
    （等于没写）。写一条与词表无关的排除词也能满足"非空"，故必须查这层。
    """
    engine = _engine()
    for entry in engine.category_rules:
        terms = entry["terms"]
        for context in entry["exclude_contexts"]:
            assert any(t in context for t in terms), \
                "品类 %s 的排除语境 %r 未包住任何本类正向词（装饰性排除）" \
                % (entry["category"], context)


def test_exclude_context_suppresses_category_hit():
    """端到端：正向词落在反例结构内部 → **不得**判出该品类。

    阳性对照在下一函数（同一词独立出现必须判出）。探针用词表与排除语境
    **实算**构造（本文件零词面）。
    """
    engine = _engine()
    for entry in engine.category_rules:
        for context in entry["exclude_contexts"]:
            item = normalize.normalize_text("本节讨论%s相关话题。" % context)
            result = categorize.categorize(item, engine.category_rules, None)
            assert entry["category"] not in result.categories, \
                "反例结构 %r 未拦住品类 %s 的误判" % (context, entry["category"])


def test_exclude_context_positive_control():
    """变异验证：把反例结构换成**独立出现**的正向词 → 必须判出该品类。

    证明上一函数的"不命中"不是永绿（排除机制真的在工作，而非整体失效）。
    """
    engine = _engine()
    checked = 0
    for entry in engine.category_rules:
        contexts = entry.get("exclude_contexts") or ()
        for term in entry["terms"]:
            if phrase.excluded_context(term, term, 0, contexts):
                continue
            item = normalize.normalize_text("本节讨论%s相关话题。" % term)
            result = categorize.categorize(item, engine.category_rules, None)
            assert entry["category"] in result.categories, \
                "独立出现的正向词 %r 未判出品类 %s（排除机制过度抑制）" \
                % (term, entry["category"])
            checked += 1
    assert checked, "未构造出任何阳性对照探针——扫描面为空（假门）"


def test_known_neutral_wordforms_are_not_categorized():
    """实测反例：中性/跨行业词形不得被判成本品类（M2 实测清单）。

    词面由规则包实算构造（取每类的一条反例结构 + 一条正向词），
    故本文件不持有政策字面量。
    """
    engine = _engine()
    probes = []
    for entry in engine.category_rules:
        for context in entry["exclude_contexts"]:
            probes.append((entry["category"], context))
    assert probes, "未取到任何反例探针——扫描面为空（假门）"
    for category, context in probes:
        rep = _run("本节介绍%s。" % context)
        assert category not in rep.categories, \
            "反例词形 %r 被判成品类 %s" % (context, category)


# --------------------------------------------------------------------------
# 风险 3：品类判定与规则核查**共用词面原语**（不自成第二套口径）
# --------------------------------------------------------------------------
def test_category_matching_reuses_shared_primitive():
    """品类判定必须复用 ``phrase`` 原语（唯一实现源），不自写一份匹配。"""
    # 原语本体来自 phrase 模块（品类层只是薄封装，不是第二份实现）
    assert categorize.phrase is phrase, "品类判定未复用共用词面原语"
    # 阴性/阳性：否定辖域在品类层同样生效（同一原语 → 同一语义）
    assert phrase.any_of("本节包含某词", ["某词"]) == ["某词"], \
        "肯定语境下的词面未被命中——探针自身含否定词或原语失效"
    assert phrase.any_of("本节不涉及某词", ["某词"]) == [], \
        "否定语境下的词面仍被命中——否定辖域未生效"


def test_check_module_aliases_shared_primitive():
    """规则核查模块的私有原语必须是 ``phrase`` 的别名（不是各自一份实现）。"""
    from medreview import check as check_mod
    assert check_mod._any_of is phrase.any_of
    assert check_mod._term_is_live is phrase.term_is_live
    assert check_mod._is_negated is phrase.is_negated


# --------------------------------------------------------------------------
# 文档计数联动：data/README 的计数表 ↔ manifest（防"文档抄旧数"漂移）
# --------------------------------------------------------------------------
def test_data_readme_counts_match_manifest():
    """`data/README.md` §一之二 的计数必须与 manifest 实算一致。

    为什么必须门禁：M2 当轮实测发现该表**抄了上一棒的旧版本号**（文档说
    `ruleset-28a4cfd991`，manifest 实为 `ruleset-f20a805f89`）——文档计数与
    数据漂移没有任何门看着，靠人记得改就会漏。故把该表纳入守门。
    """
    import re
    manifest = _engine().manifest
    with open(os.path.join(ROOT, "data", "README.md"), "r", encoding="utf-8") as handle:
        text = handle.read()

    version = re.search(r"规则包版本\s*\|\s*`([^`]+)`", text)
    assert version, "data/README.md 未登记规则包版本——扫描面为空（假门）"
    assert version.group(1) == manifest["ruleset_version"], \
        "data/README.md 的版本号与 manifest 漂移：文档 %s vs 实算 %s" \
        % (version.group(1), manifest["ruleset_version"])

    enabled = re.search(r"生效规则数\s*\|\s*\*\*(\d+)\*\*", text)
    assert enabled and int(enabled.group(1)) == manifest["enabled_rule_count"], \
        "data/README.md 的生效规则数与 manifest 漂移"

    total = re.search(r"总条目数\s*\|\s*\*\*(\d+)\*\*", text)
    assert total and int(total.group(1)) == manifest["total_rule_count"], \
        "data/README.md 的总条目数与 manifest 漂移"

    cases = json.load(open(os.path.join(SRC, "medreview", "fixtures", "cases.json"),
                           "r", encoding="utf-8"))
    case_count = re.search(r"真值用例数\s*\|\s*\*\*(\d+)\*\*", text)
    assert case_count and int(case_count.group(1)) == len(cases["cases"]), \
        "data/README.md 的真值用例数与真值库漂移"


# --------------------------------------------------------------------------
# 场景判定：§8 变相发布疑似（advisory 可观测 + 不改结论）
# --------------------------------------------------------------------------
def test_variant_suspect_is_advisory_not_conclusion():
    """变相发布疑似**只进 advisory**：不得改 grade、不得凭空定品类。

    判据：同一文案有/无 suspect 时 grade 与 categories 完全一致
    （把 suspect 逻辑当结论用，是最隐蔽的"提示越权"）。
    """
    text = "分享养生知识，扫码加微信了解详情。"
    rep = _run(text)
    kinds = [a["kind"] for a in rep.advisories]
    assert "variant_publish_suspect" in kinds, "疑似信号未出 advisory"
    assert rep.grade == constants.GRADE_NOT_ASSESSED, \
        "疑似信号越权改了结论（无品类却非 NOT_ASSESSED）"
    assert rep.categories == (), "疑似信号凭空定了品类"


def test_variant_rules_cover_both_clause_paragraphs():
    """§8 两款各有一条 suspect 信号（款 1 商品信息 / 款 2 联系方式）。"""
    engine = _engine()
    assert len(engine.variant_rules) >= 2, \
        "变相发布疑似信号未覆盖 §8 两款（实得 %d 条）" % len(engine.variant_rules)
    for entry in engine.variant_rules:
        assert entry.get("knowledge_terms"), "变相信号缺知识形态词表"
        assert entry.get("commerce_terms"), "变相信号缺商品/服务信息词表"
        assert entry.get("anchor"), "变相信号缺条款锚点"


def test_variant_suspect_requires_cooccurrence():
    """共现语义：只有知识形态、无商品/服务信息 → **不得**出疑似。

    阴性 + 阳性两侧（只判"该出要出"是单向假门）。
    """
    engine = _engine()
    knowledge = engine.variant_rules[0]["knowledge_terms"][0]
    commerce = engine.variant_rules[0]["commerce_terms"][0]
    only_knowledge = categorize.categorize(
        normalize.normalize_text(knowledge + "分享。"), engine.category_rules,
        engine.variant_rules)
    assert only_knowledge.variant_suspect is False, \
        "仅知识形态即出疑似——共现语义失效（误报）"
    both = categorize.categorize(
        normalize.normalize_text(knowledge + "分享，" + commerce + "咨询。"),
        engine.category_rules, engine.variant_rules)
    assert both.variant_suspect is True, \
        "知识形态与商品信息共现却未出疑似——共现判定失效"


# --------------------------------------------------------------------------
# 多品类并列：不二选一、不降维
# --------------------------------------------------------------------------
def test_multi_category_preserved_end_to_end():
    """多品类并列**全部保留**（各品类规则分别适用），不做二选一猜测。"""
    engine = _engine()
    # 用两类的正向词实算构造探针（不复制词面）
    medical = _category_entry(constants.CATEGORY_MEDICAL, engine)["terms"][0]
    device = _category_entry(constants.CATEGORY_DEVICE, engine)["terms"][0]
    result = categorize.categorize(
        normalize.normalize_text("%s与%s并列。" % (medical, device)),
        engine.category_rules, None)
    assert constants.CATEGORY_MEDICAL in result.categories
    assert constants.CATEGORY_DEVICE in result.categories


def test_category_order_is_deterministic():
    """品类呈现顺序**确定性**（固定优先级），不随命中顺序/集合迭代序漂移。"""
    engine = _engine()
    medical = _category_entry(constants.CATEGORY_MEDICAL, engine)["terms"][0]
    device = _category_entry(constants.CATEGORY_DEVICE, engine)["terms"][0]
    first = categorize.categorize(
        normalize.normalize_text("%s与%s。" % (medical, device)),
        engine.category_rules, None).categories
    second = categorize.categorize(
        normalize.normalize_text("%s与%s。" % (device, medical)),
        engine.category_rules, None).categories
    assert first == second, "品类呈现顺序随文案词序漂移：%s vs %s" % (first, second)
