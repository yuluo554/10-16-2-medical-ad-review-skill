"""M5 交付面门禁：报告层零判定（AST 三条）+ 分级报告双轨 + 契约三方对齐 + 批量通路。

M5 的重心是**交付面**（SKILL.md 主入口 / 分级报告双轨 / 契约块门禁），
不是判定语义（那是 M1–M4）。本文件每条门都配**阳性对照或阴性对照**——
证明"绿"不是门在空转：阳性对照证明门**抓得住**缺陷，阴性对照证明门**不过宽**
（不会把结构性常量误判成政策数值、把模板渲染误判成算术）。

判别口诀：**"交付面承诺的东西，有没有一条测试让'改任何一侧'必红？"**
"""

from __future__ import annotations

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from medreview import (  # noqa: E402
    cli, constants, normalize, pipeline, report as report_mod, selftest, serialize,
)
from medreview.bench import ledger as ledger_mod  # noqa: E402

MEDICAL_BLOCK_TEXT = "XX医疗美容门诊部（虚构）保证治愈，无效退款。"
HEALTH_FOOD_TEXT = "本品保健食品可有效降血糖、降血压。"
NON_MEDICAL_TEXT = "今天天气不错，适合出门散步。"

# 报告必备 8 章节（plan/03 §5.3；与 SKILL.md 的 report-sections 声明同源）
MANDATORY_SECTIONS = ("input_facts", "coverage", "grade", "findings",
                      "input_required", "advisory", "sources", "disclaimer")
MANDATORY_TITLES = ("一、输入事实", "二、本次评估覆盖", "三、分级结论", "四、逐条命中明细",
                    "五、待补材料清单", "六、语境提示", "七、规则来源", "八、免责声明")


def _engine():
    return pipeline.build_engine()


def _report(text=MEDICAL_BLOCK_TEXT):
    return pipeline.run_check(_engine(), normalize.normalize_text(text))


def _report_source():
    return selftest._read_source(selftest.REPORT_MODULE)


def _run_scan(argv):
    """跑一次 CLI 并捕获三个流（cli.main 既写 stdout 也写 stderr）。"""
    old_out, old_err = sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out, err
    try:
        code = cli.main(argv)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return code, out.getvalue(), err.getvalue()


def _write_samples(directory, items):
    for name, text in items:
        with open(os.path.join(str(directory), name), "w", encoding="utf-8") as handle:
            handle.write(text)


# --------------------------------------------------------------------------
# 一、报告层零判定：AST 门禁三条（S8/S9/S10）+ 双面对照
# --------------------------------------------------------------------------
def test_report_layer_imports_no_engine_module():
    """报告层只许标准库：判定数据只能由调用方注入，渲染层不得自己取。"""
    assert selftest.scan_engine_imports(_report_source()) == []


def test_report_layer_engine_import_gate_catches_injection():
    """阳性对照：注入一个引擎相对导入 → 必须报红（否则门在空转）。"""
    dirty = _report_source() + "\nfrom . import grade\n"
    assert selftest.scan_engine_imports(dirty), "注入引擎导入后仍报绿——假门"


def test_report_layer_has_no_arithmetic():
    assert selftest.scan_arithmetic_binops(_report_source()) == []


def test_report_layer_arithmetic_gate_allows_templating_only():
    """阴性对照：模板式 `%` 格式化与字符串拼接**不是**算术（否则门过宽会误红）。"""
    allowed = 'label = "%s 件" % count\njoined = "a" + "b"\n'
    assert selftest.scan_arithmetic_binops(allowed) == []


def test_report_layer_arithmetic_gate_catches_real_arithmetic():
    """阳性对照：真算术（加法/乘法）必须报红。"""
    hits = selftest.scan_arithmetic_binops("total = applied_count + total_count\nscale = n * 2\n")
    assert len(hits) == 2, "真算术未被检出——假门：%s" % hits


def test_report_layer_has_no_policy_numeric_literals():
    assert selftest.scan_policy_numeric_literals(_report_source()) == []


def test_report_layer_policy_number_gate_is_not_too_wide():
    """阴性对照：结构性常量（层级查表 / 切片宽度）不得被误判为政策数值。"""
    structural = "levels = {1: '#', 2: '##'}\nwidth = text[:12]\n"
    assert selftest.scan_policy_numeric_literals(structural) == []


def test_report_layer_policy_number_gate_catches_citation_and_threshold():
    """阳性对照：条款号引用形态与百分比阈值形态必须报红。"""
    assert selftest.scan_policy_numeric_literals("引用 §1 与阈值 1%\n")


def test_report_layer_gates_match_selftest_s8_s9_s10():
    """测试面与 selftest 的 S8/S9/S10 **同源同结论**（防两套口径漂移）。"""
    for check in (selftest.s8_report_no_engine_imports,
                  selftest.s9_report_no_arithmetic,
                  selftest.s10_report_no_policy_numbers):
        ok, note = check()
        assert ok, "selftest %s 未通过：%s" % (check.__name__, note)


def test_selftest_now_covers_ten_checks():
    """门禁自检面必须含新增三条（否则"加了 AST 门"只是文档承诺）。"""
    labels = [label for label, _ in selftest.CHECKS]
    for probe in ("S8", "S9", "S10"):
        assert any(label.startswith(probe) for label in labels), "selftest 缺 %s" % probe


# --------------------------------------------------------------------------
# 二、分级报告双轨：同一 report_sections 渲染源 + 8 章节 + 免责两轨都在
# --------------------------------------------------------------------------
def test_mandatory_sections_are_exactly_eight_in_order():
    ids = [section["id"] for section in report_mod.report_sections(_report())]
    assert ids == list(MANDATORY_SECTIONS), "必备章节缺失/错序：%s" % ids


def test_both_tracks_share_the_single_section_source():
    """"两格式内容一致"是**结构性质**：机读章节 == 结构源；人读标题来自同源。"""
    rep = _report()
    sections = report_mod.report_sections(rep)
    payload = report_mod.render_json(rep)
    assert payload["sections"] == sections, "机读章节与结构源不一致（会静默漂移）"
    markdown = report_mod.render_markdown(rep)
    for section in sections:
        assert ("## %s" % section["title"]) in markdown, \
            "人读报告缺章节标题：%s" % section["title"]


def test_markdown_carries_every_mandatory_title():
    markdown = report_mod.render_markdown(_report())
    for title in MANDATORY_TITLES:
        assert title in markdown, "人读报告缺必备章节：%s" % title


def test_disclaimer_present_in_both_tracks_and_nonempty():
    rep = _report()
    payload = report_mod.render_json(rep)
    assert payload["disclaimer"].strip(), "机读产物缺免责声明"
    section = [s for s in report_mod.report_sections(rep) if s["id"] == "disclaimer"][0]
    assert section["text"] == payload["disclaimer"], "两轨免责声明不一致"
    assert payload["disclaimer"] in report_mod.render_markdown(rep), "人读报告缺免责声明"


def test_disclaimer_text_covers_required_red_lines():
    """免责须点明三要件：辅助自查 / 不构成法律意见 / 不替代官方审查（题面 §六.1）。"""
    for phrase in ("辅助自查", "不构成法律意见", "不替代"):
        assert phrase in report_mod.DISCLAIMER, "免责声明缺要件：%s" % phrase


def test_json_carries_rule_sources_with_official_url_but_markdown_does_not():
    """溯源可达性的两轨分工：URL 只进机读字段，人读报告零外链。"""
    rep = _report()
    payload = report_mod.render_json(rep)
    urls = [entry["official_url"] for entry in payload["rule_sources"]]
    assert urls and all(u.startswith("https://") for u in urls)
    markdown = report_mod.render_markdown(rep)
    report_mod.assert_no_external_links(markdown)
    assert "http" not in markdown


# --------------------------------------------------------------------------
# 三、批量通路（scan）：逐件出全章节；空输入不产出"跑过了"的空报告
# --------------------------------------------------------------------------
def test_scan_markdown_renders_every_item(tmp_path):
    """**实测缺陷回归**：早先 scan 的人读分支只渲染第一件，多件静默丢失。"""
    _write_samples(tmp_path, [("a.txt", MEDICAL_BLOCK_TEXT),
                              ("b.txt", HEALTH_FOOD_TEXT),
                              ("c.txt", NON_MEDICAL_TEXT)])
    code, out, _ = _run_scan(["scan", "--dir", str(tmp_path), "--format", "markdown"])
    assert code == constants.EXIT_FINDING
    for index in (1, 2, 3):
        assert ("件 %d/3" % index) in out, "批量报告缺第 %d 件" % index
    for title in MANDATORY_TITLES:
        assert out.count(title) == 3, "第 %d 件未出全章节（%s 出现 %d 次）" % (
            index, title, out.count(title))
    assert out.count(report_mod.DISCLAIMER) == 3, "批量报告未逐件附免责声明"


def test_scan_json_covers_every_item(tmp_path):
    _write_samples(tmp_path, [("a.txt", MEDICAL_BLOCK_TEXT),
                              ("b.txt", HEALTH_FOOD_TEXT),
                              ("c.txt", NON_MEDICAL_TEXT)])
    code, out, _ = _run_scan(["scan", "--dir", str(tmp_path), "--format", "json"])
    assert code == constants.EXIT_FINDING
    payload = json.loads(out)
    assert payload["summary"] == {"total": 3, "failed": 0, "finding": True}
    assert len(payload["results"]) == 3
    for entry in payload["results"]:
        assert len(entry["sections"]) == 8, "机读逐件未出全 8 章节"


def test_scan_batch_markdown_has_no_external_links(tmp_path):
    _write_samples(tmp_path, [("a.txt", MEDICAL_BLOCK_TEXT)])
    _code, out, _ = _run_scan(["scan", "--dir", str(tmp_path), "--format", "markdown"])
    report_mod.assert_no_external_links(out)  # 批量出口同样受常驻断言约束
    assert "http" not in out


def test_scan_empty_dir_produces_no_report(tmp_path):
    """"根本没得查" ≠ "查了没问题"：空输入不产出空报告（会被当"跑过了"）。"""
    code, out, err = _run_scan(["scan", "--dir", str(tmp_path), "--format", "markdown"])
    assert code == constants.EXIT_INPUT
    assert out == "", "空输入竟产出了报告：%r" % out[:120]
    assert "没有可审查" in err


def test_scan_failed_item_is_listed_not_silently_swallowed(tmp_path):
    """单件处理失败要**单列**（不静默吞掉、不改变退出码）。"""
    _write_samples(tmp_path, [("good.txt", MEDICAL_BLOCK_TEXT)])
    with open(os.path.join(str(tmp_path), "bad.txt"), "wb") as handle:
        handle.write(b"\xff\xfe\x00 bad")
    code, out, _ = _run_scan(["scan", "--dir", str(tmp_path), "--format", "json"])
    payload = json.loads(out)
    assert payload["summary"]["failed"] == 1
    failed = [e for e in payload["results"] if e.get("kind") == "failed"]
    assert len(failed) == 1 and failed[0]["error"]
    assert code == constants.EXIT_FINDING, "失败件不得改变退出码语义"


# --------------------------------------------------------------------------
# 四、红线：合成数据纪律（不引用真实机构案例）+ 确定性纪律明写
# --------------------------------------------------------------------------
def test_samples_use_whitelisted_org_names():
    """合成数据纪律（D4）：samples/ 下的样例机构名必须在假机构名白名单内。"""
    samples_dir = os.path.join(ROOT, "samples")
    cases = []
    for name in sorted(os.listdir(samples_dir)):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(samples_dir, name), "r", encoding="utf-8") as handle:
            cases.append({"id": name, "input": handle.read()})
    assert cases, "samples/ 下无非空样例（扫描面为空 = 假门）"
    assert ledger_mod.check_fake_org_whitelist({"cases": cases}) == []


def test_rendered_report_contains_only_whitelisted_org_names():
    """报告不引用真实机构违规案例：渲染产物里的机构名形态须全在白名单内。"""
    markdown = report_mod.render_markdown(_report())
    payload = {"cases": [{"id": "rendered", "input": markdown}]}
    found = ledger_mod.scan_org_names(markdown)
    assert found, "渲染产物竟无机构名形态——本门无观测面（假门）"
    assert ledger_mod.check_fake_org_whitelist(payload) == []


def test_markdown_coverage_rows_separated_from_not_enabled_line():
    """格式要件回归：覆盖表的行与「未启用清单」行之间必须留一个空行。

    实测（M5 重构踩到）：缺了空行，Markdown 会把「未启用清单：（空）」
    吸进上一条列表项（列表项与后续段落必须空行分隔）——报告排版静默走形。
    """
    lines = report_mod.render_markdown(_report()).splitlines()
    rows_index = next(i for i, line in enumerate(lines)
                      if line.startswith("- **规则包总条目数**"))
    assert lines[rows_index + 1] == "", "覆盖表与未启用清单之间缺空行（Markdown 会吸行）"


def test_readme_and_skill_declare_no_drug_recommendation():
    """红线声明门：不做药品推荐（题面 §六.2）须在对外文档明写。"""
    for path in (os.path.join(ROOT, "README.md"), os.path.join(ROOT, "SKILL.md")):
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        assert "药品推荐" in text, "%s 未声明'不做药品推荐'" % os.path.basename(path)


def _skill_text():
    with open(os.path.join(ROOT, "SKILL.md"), "r", encoding="utf-8") as handle:
        return handle.read()


def test_skill_states_determinism_discipline():
    """确定性纪律须在 SKILL.md 明写（plan/03 §2.2）。"""
    text = _skill_text()
    assert "零 LLM" in text or "零LLM" in text, "SKILL.md 未明写'引擎零 LLM 调用'"
    assert "纯本地" in text, "SKILL.md 未明写纯本地"


def test_skill_input_table_covers_all_cli_check_params():
    """入参表须与 CLI 的 check 参数面对齐（文档不许漏参数）。"""
    text = _skill_text()
    for param in ("--text", "--text-file", "--channel", "--subject", "--scenario",
                  "--proof", "--proof-file", "--hint"):
        assert param in text, "SKILL.md 入参表缺参数：%s" % param


def test_skill_declares_scan_batch_both_formats():
    text = _skill_text()
    assert "medreview scan" in text, "SKILL.md 未声明批量通路"
    assert "--format markdown" in text and "--format json" in text, \
        "SKILL.md 未声明批量的两种格式"


# --------------------------------------------------------------------------
# 五、确定性：序列化出口（双跑逐字节一致；批量通路同样成立）
# --------------------------------------------------------------------------
def test_batch_json_is_byte_reproducible():
    report_a = _report(MEDICAL_BLOCK_TEXT)
    report_b = _report(MEDICAL_BLOCK_TEXT)
    payload_a = {"results": [report_a.to_dict()], "summary": {"total": 1}}
    payload_b = {"results": [report_b.to_dict()], "summary": {"total": 1}}
    assert serialize.dumps_json(payload_a) == serialize.dumps_json(payload_b)