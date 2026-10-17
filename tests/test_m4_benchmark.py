"""M4 真值基准门禁：四套件可证伪探活 + 边界类 + 覆盖双登记 + 三件齐备 + kind 双层。

本文件是 M4 的**判定面**（plan/03 §6）。与 M1–M3 的语义门禁同一纪律：
每条断言都要能"被一个注入的缺陷打红"，且断言本身要自证"扫描面非空"
（探活可能空转：注入的缺陷没打中任何断言，也是永不红的一种）。

三条硬纪律（M4 当轮实测踩出来的）：

1. **探活必须打到端到端入口 ``run_benchmarks``**：只断言内部对账函数返回非空
   证明不了"用户敲的那条命令真把缺陷跑出来了"（M4 实测：B4 原探活只打
   ``_run_suite``，绕过了 ``run_benchmarks`` 的冻结件加载与汇总，属弱探活）。
2. **探活必须自证"缺陷真打中了目标套件"**：篡改若被**冻结台账**拦下（在
   套件比对之前），那证明的是台账门在起作用，不是套件判据在起作用——
   故探针必须**重算摘要 + 同步台账**，让失败只能来自套件比对。
3. **边界类必须成对**（``threshold_exact`` 恰命中 / ``near_miss`` 不到不命中）：
   只有一侧就退化成普通正/反例，"边界语义"这一轴等于没覆盖（假覆盖）。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from medreview import check as check_mod, constants, pipeline, selftest  # noqa: E402
from medreview.bench import cases as cases_mod, ledger as ledger_mod, runner  # noqa: E402

import gen_cases  # noqa: E402

CASES_PATH = os.path.join(SRC, "medreview", "fixtures", "cases.json")

# 形态轴（plan/03 §6.2）：与 manifest 的 benchmark_coverage.form_axes 同源断言对象
FORM_AXES = ("positive", "reverse", "threshold_exact", "near_miss")


def _engine():
    return pipeline.build_engine(scope=constants.SCOPE_BENCH)


def _payload():
    return runner.load_fixture_payload()[0]


def _write_payload(payload, directory):
    """把（可能被篡改的）真值库写进临时目录，供 ``run_benchmarks`` 端到端读取。"""
    target = os.path.join(directory, "cases.json")
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace("\r\n", "\n").rstrip("\n") + "\n")
    return target


def _tamper(payload, case_id, mutate):
    """改一条用例并**重算摘要 + 同步台账**（否则失败来自台账门而非套件判据）。

    返回被改的用例对象（供探针断言"改动真的落地了"）。
    """
    tampered = json.loads(json.dumps(payload))
    target = None
    for case in tampered["cases"]:
        if case["id"] == case_id:
            target = case
            break
    assert target is not None, "探针目标用例不存在：%s" % case_id
    mutate(target)
    target["sha256"] = ledger_mod.case_digest(target)
    for entry in tampered["ledger"]["entries"]:
        if entry["id"] == case_id:
            entry["sha256"] = target["sha256"]
    return tampered, target


def _run_on(payload):
    with tempfile.TemporaryDirectory() as tmp:
        _write_payload(payload, tmp)
        return runner.run_benchmarks(fixtures_dir=tmp)


def _assert_probe_caught(code, summary, suite):
    """探活共同断言：非 0 + 真声明未达标 + 失败**只能**来自该套件的比对。

    "只能来自套件比对"是可证伪性的关键：若 ``truth_source`` 缺失或 summary 里
    只有冻结台账类问题，那这次探活证明的是台账门，不是套件判据——必须报红。
    """
    assert code == runner.EXIT_NOT_MET, "注入缺陷后基准仍返回 0——探活是永绿门"
    assert summary["not_met"], "注入缺陷后未声明任何未达标套件——探活空转"
    assert suite in summary["not_met"], \
        "注入的缺陷没打中目标套件 %s（实际未达标：%s）——探针非空自证失败" \
        % (suite, summary["not_met"])
    assert summary.get("truth_source") == "frozen", \
        "失败来自冻结件加载而非套件比对（探活证明的不是套件判据）"
    assert not summary.get("not_enabled"), \
        "套件被判'未启用'——失败语义不是'跑了没过'"


def _first_case_of(payload, suite, predicate=None):
    for case in payload["cases"]:
        if case["suite"] != suite:
            continue
        if predicate is None or predicate(case):
            return case["id"]
    return None


# --------------------------------------------------------------------------
# 四套件各自的可证伪探活（每套件一条，各打一类缺陷，全部打到 run_benchmarks）
# --------------------------------------------------------------------------
def test_probe_b1_expectation_tamper_is_caught():
    """B1（品类判定）：篡改一条用例的期望 → 基准必须报 B1 未达标。

    B1 判据是**品类集合精确相等**，故把品类期望抹掉即可打中它。
    """
    payload = _payload()
    case_id = _first_case_of(payload, "b1_category")
    assert case_id, "B1 无任何用例——探活无法构造"
    tampered, case = _tamper(payload, case_id, lambda c: c.update(
        {"expect_keys": ["grade:NOT_ASSESSED"]}))
    assert case["expect_keys"] == ["grade:NOT_ASSESSED"], "探针未真正改写期望"
    code, summary = _run_on(tampered)
    _assert_probe_caught(code, summary, "b1_category")


def test_probe_b2_boundary_semantics_tamper_is_caught():
    """B2（禁止情形）：把 near_miss 用例的期望翻成"该命中" → B2 必未达标。

    打的是**边界语义**（plan/03 §6.4 的"边界语义改 `>`"）：若边界判据形同虚设，
    这种篡改就永远不会红。
    """
    payload = _payload()
    case_id = _first_case_of(payload, "b2_prohibited",
                             predicate=lambda c: c.get("form") == "near_miss")
    assert case_id, "B2 无 near_miss 边界用例——探活无法构造（边界轴未落地）"
    hit_key = None
    for case in payload["cases"]:
        if case["id"] == case_id:
            hit_key = sorted(k for k in case.get("forbid_keys") or ()
                             if k.startswith("hit:"))[0]
            break
    assert hit_key, "near_miss 用例未 forbid 任何 hit:*——边界探针无法构造"

    def mutate(case):
        case["expect_keys"] = [k for k in case["expect_keys"] if not k.startswith("grade:")]
        case["expect_keys"].append(hit_key)
        case["forbid_keys"] = [k for k in case.get("forbid_keys") or ()
                               if k != hit_key and k != "grade:BLOCK"]

    tampered, case = _tamper(payload, case_id, mutate)
    assert hit_key in case["expect_keys"], "探针未真正把边界期望翻面"
    code, summary = _run_on(tampered)
    _assert_probe_caught(code, summary, "b2_prohibited")


def test_probe_b3_applies_reverse_is_caught():
    """B3（适用域反向）：把"不该命中"翻成"该命中" → B3 必未达标。

    打的是**适用域写反**（plan/03 §6.4）：B3 的判据是"该规则不该命中"，
    把 forbid 键搬进 expect 即直接违反该判据。
    """
    payload = _payload()
    case_id = _first_case_of(payload, "b3_applies_reverse",
                             predicate=lambda c: any(k.startswith("hit:")
                                                     for k in c.get("forbid_keys") or ()))
    assert case_id, "B3 无任何 forbid hit:* 的用例——探活无法构造"

    def mutate(case):
        forbidden_hit = sorted(k for k in case.get("forbid_keys") or ()
                               if k.startswith("hit:"))[0]
        case["expect_keys"] = list(case["expect_keys"]) + [forbidden_hit]
        case["forbid_keys"] = [k for k in case["forbid_keys"] if k != forbidden_hit]

    tampered, case = _tamper(payload, case_id, mutate)
    assert any(k.startswith("hit:") for k in case["expect_keys"]), "探针未真正反转适用域"
    code, summary = _run_on(tampered)
    _assert_probe_caught(code, summary, "b3_applies_reverse")


def test_probe_b4_rule_coverage_deletion_is_caught():
    """B4（规则覆盖）：删掉某条规则的**唯一**覆盖用例 → B4 必未达标。

    先**实算**"哪条规则只被一个用例覆盖"（不硬编码规则 id：规则包会演化），
    删掉那个用例并同步台账——端到端过 ``run_benchmarks``（分母 = 生效规则数）。
    """
    engine = _engine()
    payload = _payload()

    coverage_map = {}
    for case in runner._cases_for(payload, "b4_rule_coverage"):
        rep = pipeline.check_text(engine, case["input"], proof=case.get("proof"),
                                  scenario=case.get("scenario"))
        for key in cases_mod.observed_keys(rep):
            if key.startswith("rule:skipped:"):
                continue
            if key.startswith("rule:") or key.startswith("hit:"):
                coverage_map.setdefault(key.split(":", 2)[-1], set()).add(case["id"])

    sole = sorted((rule_id, sorted(ids)[0]) for rule_id, ids in coverage_map.items()
                  if len(ids) == 1)
    assert sole, "没有'唯一覆盖'的规则——B4 探活无法构造（覆盖判据形同虚设）"
    rule_id, doomed = sole[0]

    tampered = json.loads(json.dumps(payload))
    tampered["cases"] = [c for c in tampered["cases"] if c["id"] != doomed]
    tampered["ledger"]["entries"] = [e for e in tampered["ledger"]["entries"]
                                     if e["id"] != doomed]
    tampered["ledger"]["count"] = len(tampered["cases"])
    assert not any(c["id"] == doomed for c in tampered["cases"]), "探针未真正删掉用例"

    code, summary = _run_on(tampered)
    _assert_probe_caught(code, summary, "b4_rule_coverage")
    assert rule_id in summary["suites"]["b4_rule_coverage"]["uncovered_rules"], \
        "删掉唯一覆盖用例后该规则未被记为未覆盖——覆盖判据假门"


def test_every_suite_has_a_probe():
    """**覆盖面自证**：四条探活函数必须真存在于本模块（防"少写一条也没人发现"）。

    判据落在"函数真存在且各自打不同套件"上，不是"注释里写了四条"。
    """
    probes = {
        "b1_category": "test_probe_b1_expectation_tamper_is_caught",
        "b2_prohibited": "test_probe_b2_boundary_semantics_tamper_is_caught",
        "b3_applies_reverse": "test_probe_b3_applies_reverse_is_caught",
        "b4_rule_coverage": "test_probe_b4_rule_coverage_deletion_is_caught",
    }
    assert set(probes) == set(runner.SUITES), "探活未覆盖全部套件"
    module_globals = globals()
    for suite, name in probes.items():
        assert name in module_globals, "套件 %s 缺探活函数 %s" % (suite, name)


# --------------------------------------------------------------------------
# 卡阈值边界类（plan/03 §6.2）：成对出现，且两侧都被真值库断言
# --------------------------------------------------------------------------
def test_boundary_forms_present_and_paired():
    """真值库必须含 threshold_exact 与 near_miss **两侧**，且各自非空。

    只有一侧 = 边界轴退化（"恰命中"没有"不到不命中"对照，判据分不清
    "词面判定线"与"任何数字都命中"）。
    """
    payload = _payload()
    forms = {}
    for case in payload["cases"]:
        forms.setdefault(case.get("form"), []).append(case)
    for form in ("threshold_exact", "near_miss"):
        assert forms.get(form), "真值库缺 %s 形态用例——边界轴未覆盖（假覆盖）" % form
    assert forms["threshold_exact"], "threshold_exact 为空"


def test_threshold_exact_cases_assert_a_hit():
    """threshold_exact = 恰在判定线上 → **必须**断言至少一条 hit:*。"""
    payload = _payload()
    checked = 0
    for case in payload["cases"]:
        if case.get("form") != "threshold_exact":
            continue
        assert any(k.startswith("hit:") for k in case["expect_keys"]), \
            "%s（threshold_exact）未断言任何 hit:*——未验'恰命中'" % case["id"]
        checked += 1
    assert checked, "threshold_exact 用例数为 0——扫描面为空（假门）"


def test_near_miss_cases_forbid_hit_and_block():
    """near_miss = 不到判定线 → **必须** forbid hit:* 且 forbid grade:BLOCK。"""
    payload = _payload()
    checked = 0
    for case in payload["cases"]:
        if case.get("form") != "near_miss":
            continue
        forbids = set(case.get("forbid_keys") or ())
        assert any(k.startswith("hit:") for k in forbids), \
            "%s（near_miss）未 forbid 任何 hit:*——未验'不到不命中'" % case["id"]
        assert "grade:BLOCK" in forbids, \
            "%s（near_miss）未 forbid grade:BLOCK——未验'不到不判禁止'" % case["id"]
        checked += 1
    assert checked, "near_miss 用例数为 0——扫描面为空（假门）"


def test_boundary_cases_actually_pass_the_engine():
    """边界用例必须**真过引擎**（不是"写了期望但从没跑"）。

    逐条实跑：threshold_exact 必须真出 hit，near_miss 必须真不出被 forbid 的 hit。
    这是"边界判据确实工作"的直接证据（期望与观测两侧独立）。
    """
    engine = _engine()
    payload = _payload()
    ran = {"threshold_exact": 0, "near_miss": 0}
    for case in payload["cases"]:
        form = case.get("form")
        if form not in ran:
            continue
        rep = pipeline.check_text(engine, case["input"], proof=case.get("proof"),
                                  scenario=case.get("scenario"))
        observed = cases_mod.observed_keys(rep)
        if form == "threshold_exact":
            assert any(k.startswith("hit:") for k in observed), \
                "%s 恰在判定线上却零命中——边界判据失效" % case["id"]
        else:
            for key in case.get("forbid_keys") or ():
                assert key not in observed, \
                    "%s（near_miss）被 forbid 的 %s 仍出现——边界判据失效" \
                    % (case["id"], key)
        ran[form] += 1
    assert ran["threshold_exact"] and ran["near_miss"], "边界用例未真跑（扫描面为空）"


# --------------------------------------------------------------------------
# 覆盖声明双登记（plan/03 §6.3）：manifest ↔ 真值库，且非穷举有数值坐实
# --------------------------------------------------------------------------
def test_coverage_declaration_is_double_registered():
    """两侧登记必须都在，且形态轴、非穷举声明一致。"""
    manifest = _engine().manifest
    payload = _payload()
    cov_manifest = manifest.get("benchmark_coverage")
    cov_cases = payload.get("coverage")
    assert cov_manifest, "manifest 缺 benchmark_coverage 登记——覆盖声明未双登记"
    assert cov_cases, "真值库缺 coverage 登记——覆盖声明未双登记"

    assert set(cov_manifest["form_axes"]) == set(cov_cases["by_form"]), \
        "形态轴两侧不一致：manifest %s vs 真值库 %s" \
        % (cov_manifest["form_axes"], sorted(cov_cases["by_form"]))
    assert set(cov_manifest["form_axes"]) == set(FORM_AXES), \
        "形态轴不是既定的四类：%s" % cov_manifest["form_axes"]
    assert cov_manifest["non_exhaustive"] is True and cov_cases["non_exhaustive"] is True, \
        "两侧都必须显式声明'抽样覆盖、非穷举'"


def test_coverage_counts_match_actual_cases():
    """真值库 coverage 块登记的采样数与采样清单必须与用例实算一致。"""
    payload = _payload()
    cov = payload["coverage"]
    cases = payload["cases"]
    assert cov["sampled_case_count"] == len(cases), \
        "coverage.sampled_case_count 与用例数漂移"
    assert sum(v["count"] for v in cov["by_form"].values()) == len(cases), \
        "逐形态计数之和与用例数不符"
    for form, entry in cov["by_form"].items():
        actual = sorted(c["id"] for c in cases if c.get("form") == form)
        assert entry["case_ids"] == actual, \
            "形态 %s 的采样清单与实算不符" % form
        assert entry["count"] == len(actual), \
            "形态 %s 的采样数与实算不符" % form


def test_coverage_is_numerically_non_exhaustive():
    """**非穷举有数值坐实**：边界形态的采样数必须远小于规则包条目总数。

    否则"抽样覆盖、非穷举"只是一句口号（采样数 ≥ 条目总数时，宣称"非穷举"
    与事实相反）。判据落在**数值**上，不落在措辞上。
    """
    manifest = _engine().manifest
    payload = _payload()
    total_items = manifest["benchmark_coverage"]["rule_pack_total_items"]
    assert total_items == manifest["total_rule_count"], \
        "登记条目总数与 manifest.total_rule_count 漂移"
    for form in ("threshold_exact", "near_miss"):
        count = payload["coverage"]["by_form"][form]["count"]
        assert count < total_items, \
            "形态 %s 采样数 %d 不小于规则包条目总数 %d——'非穷举'与事实相反" \
            % (form, count, total_items)


def test_data_readme_form_counts_match():
    """`data/README.md` 的**真值形态分布**行必须与真值库实算一致（K26 同源门禁）。

    M4 新增形态轴后，文档计数表若不跟着登记形态分布，"用例数对得上、
    形态分布早已漂移"就无人看着——与 K26 是同一类漂移缺陷。
    """
    import re
    payload = _payload()
    with open(os.path.join(ROOT, "data", "README.md"), "r", encoding="utf-8") as handle:
        text = handle.read()
    row = re.search(r"真值形态分布\s*\|(.*?)\|", text)
    assert row, "data/README.md 未登记真值形态分布——扫描面为空（假门）"
    cell = row.group(1)
    for form in FORM_AXES:
        match = re.search(r"%s\s*\*\*(\d+)\*\*" % re.escape(form), cell)
        assert match, "data/README.md 形态分布行缺 %s 计数" % form
        actual = payload["coverage"]["by_form"][form]["count"]
        assert int(match.group(1)) == actual, \
            "data/README.md 的 %s 计数与真值库漂移：文档 %s vs 实算 %d" \
            % (form, match.group(1), actual)


# --------------------------------------------------------------------------
# 真值库三件齐备复核（plan/03 §6.1）
# --------------------------------------------------------------------------
def test_truth_library_three_pieces_in_place():
    """三件齐备：① 入库件在位；② 冻结件内置台账一致；③ 生产入口真读冻结件。"""
    # ① 入库件（包内，随安装面）
    assert os.path.isfile(CASES_PATH), "真值库入库件不在包内：%s" % CASES_PATH
    # ② 位级守门：内置台账与用例逐条一致（生成器 --check 与运行时共用同一判定）
    payload = _payload()
    assert ledger_mod.check_frozen_ledger(payload) == [], "内置台账与用例不一致"
    # ③ 生产入口真读：bench 生产路径先过 check_frozen_ledger（不绕过）
    assert runner._load_frozen_cases.__module__ == "medreview.bench.runner"
    code, summary = runner.run_benchmarks(only="b1_category")
    assert code == runner.EXIT_OK and summary["truth_source"] == "frozen", \
        "生产入口未真读冻结件"


def test_truth_library_cli_path_reads_frozen_cases():
    """CLI 通路（``bench``）真读冻结件：篡改用例即报红（不是"另有旁路"）。

    探针必须**真改出结论差异**：把一个"断言了品类"的用例的输入换成非涉医内容
    （期望仍断言品类）→ 品类断言必红。只改标点/加字不构成有效探针
    （M4 实测：给输入追加"（改）"判据不变 → 该探针空转）。
    """
    payload = _payload()
    case_id = _first_case_of(payload, "b1_category",
                             predicate=lambda c: any(k.startswith("category:")
                                                     for k in c.get("expect_keys") or ()))
    assert case_id, "B1 无'断言品类'的用例——探活无法构造"

    def mutate(case):
        case["input"] = "今天天气不错，适合出门散步。"
        case["channel"] = None
        case["subject"] = None
        case["proof"] = None
        case["scenario"] = None

    tampered, case = _tamper(payload, case_id, mutate)
    assert case["input"] == "今天天气不错，适合出门散步。", "探针未真正改写输入"
    code, summary = _run_on(tampered)
    # 台账已同步 → 冻结件一致，故失败来自**套件比对**（证明用例真被喂进引擎）
    assert code == runner.EXIT_NOT_MET, "篡改输入后基准仍返回 0——CLI 通路没真读用例"
    assert summary["not_met"], "篡改输入后未声明未达标——CLI 通路没真读用例"


def test_ledger_gate_precedes_case_comparison():
    """冻结件门**先于**套件比对：只改内容不同步台账 → 报'冻结台账校验失败'。"""
    payload = _payload()
    tampered = json.loads(json.dumps(payload))
    tampered["cases"][0]["input"] = tampered["cases"][0]["input"] + "（不同步台账）"
    code, summary = _run_on(tampered)
    assert code == runner.EXIT_NOT_MET
    assert summary.get("problems"), "台账不同步却未报红——冻结件门形同虚设"
    assert "冻结台账校验失败" in summary.get("error", "")


# --------------------------------------------------------------------------
# kind 分派表**测试面**双层断言（结构层 + 运行层）
# --------------------------------------------------------------------------
def test_dispatch_structural_layer_in_test_face():
    """结构层：键集合 ↔ kind 常量集合一一对应，且各实现互不相同。"""
    keys = check_mod.dispatch_table_keys()
    assert keys, "分派表键为空——扫描面为空（假门）"
    assert set(keys) == set(constants.KINDS), \
        "分派表键与 kind 常量不一致：%s vs %s" % (keys, constants.KINDS)
    handlers = [check_mod.DISPATCH[k] for k in keys]
    assert len(set(handlers)) == len(handlers), "两个 kind 指向同一实现（复制粘贴型缺陷）"


def test_dispatch_runtime_layer_each_kind_runs():
    """运行层：每个 kind 用**真实规则**真跑一遍且不抛错（不是只查表里有键）。"""
    engine = _engine()
    by_kind = {}
    for rule in engine.rules:
        by_kind.setdefault(rule.kind, rule)
    missing = [k for k in constants.KINDS if k not in by_kind]
    assert not missing, "有 kind 无任何生效规则覆盖，运行层无法自证：%s" % missing
    for kind, rule in sorted(by_kind.items()):
        spec = engine.matches.get(rule.rule_id) or {}
        result = check_mod.check_rule(rule, spec, "测试内容，含药品片剂字样。",
                                      tuple(rule.categories), proof=None, scenario=None)
        assert result is not None, "kind %s 运行返回 None" % kind
        assert result.state in constants.RULE_STATES, \
            "kind %s 返回非法状态：%s" % (kind, result.state)


def test_dispatch_dual_layer_matches_selftest():
    """测试面与 selftest 的 S5 必须**同源同结论**（防两套口径漂移）。"""
    ok, note = selftest.s5_dispatch_table()
    assert ok, "selftest S5 未通过：%s" % note


# --------------------------------------------------------------------------
# 生成器边界守卫（M4 变异验证的探针来源）：oracle 必须真拒绝退化用例
# --------------------------------------------------------------------------
def test_oracle_rejects_threshold_exact_without_hit():
    """变异验证：threshold_exact 用例不写 hit:* → oracle 必须拒绝（不是假门）。"""
    case = {"id": "X", "suite": "b2_prohibited", "form": "threshold_exact",
            "input": "文本", "expect": ["grade:WARN", "category:medical"],
            "forbid": ["hit:AL-16-1", "grade:BLOCK"]}
    ok, why = gen_cases.naive_oracle(case)
    assert not ok, "退化 threshold_exact（无 hit:*）未被 oracle 拒绝——边界守卫假门"
    assert "threshold_exact" in why


def test_oracle_rejects_near_miss_without_forbid():
    """变异验证：near_miss 用例不 forbid hit:* → oracle 必须拒绝。"""
    case = {"id": "X", "suite": "b2_prohibited", "form": "near_miss",
            "input": "文本", "expect": ["grade:WARN", "category:medical"],
            "forbid": ["grade:BLOCK"]}
    ok, why = gen_cases.naive_oracle(case)
    assert not ok, "退化 near_miss（未 forbid hit:*）未被 oracle 拒绝——边界守卫假门"
    assert "near_miss" in why


def test_oracle_accepts_wellformed_boundary_pair():
    """阳性对照：合法的边界成对用例必须通过 oracle（防守卫过严误红）。"""
    exact = {"id": "X", "suite": "b2_prohibited", "form": "threshold_exact",
             "input": "文本", "expect": ["grade:BLOCK", "category:medical", "hit:AL-16-1"]}
    miss = {"id": "Y", "suite": "b2_prohibited", "form": "near_miss",
            "input": "文本", "expect": ["grade:WARN", "category:medical"],
            "forbid": ["hit:AL-16-1", "grade:BLOCK"]}
    assert gen_cases.naive_oracle(exact)[0], "合法 threshold_exact 被 oracle 误拒"
    assert gen_cases.naive_oracle(miss)[0], "合法 near_miss 被 oracle 误拒"


def test_oracle_rejects_illegal_form_value():
    """form 取值非法 → oracle 必须拒绝（防形态轴被写进未知值绕过边界守卫）。"""
    case = {"id": "X", "suite": "b2_prohibited", "form": "no_such_form",
            "input": "文本", "expect": ["grade:WARN", "category:medical"]}
    ok, why = gen_cases.naive_oracle(case)
    assert not ok, "非法 form 未被 oracle 拒绝——形态轴守卫假门"
    assert "form" in why


def test_every_case_has_a_declared_form():
    """每条用例都必须带 form，且取值在形态轴内（无 form = 未登记轴，覆盖声明不成立）。"""
    payload = _payload()
    assert payload["cases"], "真值库为空——扫描面为空（假门）"
    for case in payload["cases"]:
        assert case.get("form") in FORM_AXES, \
            "%s 的 form 缺失或非法：%r" % (case["id"], case.get("form"))
