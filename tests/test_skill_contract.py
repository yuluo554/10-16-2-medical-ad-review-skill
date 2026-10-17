"""SKILL.md 机器契约块 ↔ 代码字段 双向一致性门禁。

（Skill/文档型交付的硬门）SKILL.md 内嵌机器可解析契约块
（``<!-- contract-fields: ... -->``）后，必须有三条结构断言：
 ① 契约块唯一性；
 ② 契约块字段集合 == 代码字段常量（**双向**：文档不许多、不许少）；
 ③ 字段序 == 输出 JSON 实际字段序。

**M5 补强**：K15 的"三处"必须都真的被看住——契约块只是其一；
SKILL.md 的**人读字段表**是第二处，报告**必备章节声明**是第三处
（``<!-- report-sections: ... -->``）。只守其中一处时，另两处会各自漂移：
agent 按契约块取字段、人按字段表读文档、读者按章节声明核报告，三者会不一致。

判别口诀：**"文档承诺给机器读的结构，有没有一条测试让'改任何一侧'必红？"**
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from medreview import (  # noqa: E402
    constants, model, normalize, pipeline, report as report_mod,
)

CONTRACT_RE = re.compile(r"<!--\s*contract-fields:\s*(.*?)\s*-->")
REPORT_SECTIONS_RE = re.compile(r"<!--\s*report-sections:\s*(.*?)\s*-->")
FIELD_TABLE_ROW_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", re.M)
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _skill_text():
    with open(os.path.join(ROOT, "SKILL.md"), "r", encoding="utf-8") as handle:
        return handle.read()


def contract_fields():
    matches = CONTRACT_RE.findall(_skill_text())
    assert len(matches) == 1, "SKILL.md 的契约块必须唯一（实得 %d 个）" % len(matches)
    return matches[0].split()


def _code_contract_fields():
    fields = set()
    for name in dir(constants):
        if name.startswith("CONTRACT_FIELDS_"):
            fields.update(getattr(constants, name))
    assert fields, "代码侧缺契约字段常量（constants.CONTRACT_FIELDS_*）"
    return fields


def _skill_field_table_fields():
    """解析 SKILL.md「输出契约」下的**人读字段表**，取字段名集合。

    只取第一列的反引号标识符（``item.`` 前缀去掉）；``findings`` 行的
    说明列额外登记命中子字段（命中子字段不在第一列，只有该行列了它们）。
    """
    text = _skill_text()
    start = text.index("## 输出契约")
    end = text.index("### 报告必备章节")
    block = text[start:end]
    fields = set()
    for match in FIELD_TABLE_ROW_RE.finditer(block):
        first, _type_cell, third = match.groups()
        if set(first.strip()) <= set("-: "):  # 表头分隔行
            continue
        names = [name.split(".", 1)[1] if name.startswith("item.") else name
                 for name in BACKTICK_RE.findall(first)]
        fields.update(n for n in names if n)
        if names == ["findings"]:
            fields.update(BACKTICK_RE.findall(third))
    return fields


def test_contract_block_is_unique_and_nonempty():
    fields = contract_fields()
    assert fields, "契约块字段为空（扫描面为空 = 假门）"


def test_contract_fields_match_code_fields():
    """契约块 ↔ 代码字段常量**双向**一致（文档不许多、不许少）。"""
    documented = set(contract_fields())
    code_fields = _code_contract_fields()

    only_in_doc = sorted(documented - code_fields)
    only_in_code = sorted(code_fields - documented)
    assert not only_in_doc, "契约块声明了代码没有的字段：%s" % only_in_doc
    assert not only_in_code, "代码有字段但契约块未声明：%s" % only_in_code


def test_skill_field_table_matches_code_fields():
    """SKILL.md **人读字段表** ↔ 代码字段常量（K15 的第二处，同样双向）。"""
    documented = _skill_field_table_fields()
    assert documented, "字段表解析为空（解析面为空 = 假门）"
    code_fields = _code_contract_fields()
    only_in_doc = sorted(documented - code_fields)
    only_in_code = sorted(code_fields - documented)
    assert not only_in_doc, "SKILL.md 字段表列了代码没有的字段：%s" % only_in_doc
    assert not only_in_code, "SKILL.md 字段表漏了代码字段：%s" % only_in_code


def test_contract_field_order_matches_output():
    """字段序 == 输出 JSON 实际字段序（三方对齐的第三面）。"""
    documented = contract_fields()
    item = normalize.normalize_text("XX医疗美容门诊部（虚构）保证治愈。")
    rep = pipeline.run_check(pipeline.build_engine(), item)
    payload = report_mod.render_json(rep)

    # 顶层输出顺序 = payload 的键插入顺序（报告渲染器决定）
    top_order = [k for k in payload.keys()
                 if k in set(constants.CONTRACT_FIELDS_TOP)]
    expected_top = [f for f in documented if f in set(constants.CONTRACT_FIELDS_TOP)]
    assert top_order == expected_top, \
        "契约块顶层字段序与输出不一致：文档 %s vs 输出 %s" % (expected_top, top_order)

    finding_order = list(payload["findings"][0].keys()) if payload["findings"] else []
    expected_finding = [f for f in documented if f in set(constants.CONTRACT_FIELDS_FINDING)]
    if finding_order:
        assert finding_order == expected_finding, \
            "契约块命中字段序与输出不一致：文档 %s vs 输出 %s" % (expected_finding, finding_order)


def test_evidence_kind_is_internal_not_a_contract_field():
    """``Finding.evidence_kind`` **刻意不进契约字段**——它是内部判定字段（导出前四要素
    断言据此选判据），不是输出字段。混进契约字段会把内部实现暴露成对外承诺。"""
    assert "evidence_kind" not in set(constants.CONTRACT_FIELDS_ALL), \
        "evidence_kind 混进了契约字段（它是内部判定字段，不是输出字段）"
    finding = model.Finding("R-TEST", "某条锚点", "某条原文", "某段证据",
                            constants.SEVERITY_BLOCK, constants.KIND_PROHIBITED_TERM)
    assert "evidence_kind" not in finding.to_dict(), \
        "命中输出竟带上了内部字段 evidence_kind"


def test_skill_report_sections_marker_matches_renderer():
    """SKILL.md 的「报告必备章节」声明 ↔ 渲染器实际章节（id 与**序**都须一致）。"""
    matches = REPORT_SECTIONS_RE.findall(_skill_text())
    assert len(matches) == 1, "SKILL.md 的章节声明必须唯一（实得 %d 个）" % len(matches)
    declared = matches[0].split()
    assert declared, "章节声明为空（扫描面为空 = 假门）"
    assert len(declared) == 8, "报告必备章节必须恰 8 节（实得 %d）" % len(declared)

    item = normalize.normalize_text("XX医疗美容门诊部（虚构）保证治愈。")
    rep = pipeline.run_check(pipeline.build_engine(), item)
    actual = [section["id"] for section in report_mod.report_sections(rep)]
    assert declared == actual, \
        "SKILL.md 章节声明与渲染器不一致：文档 %s vs 渲染 %s" % (declared, actual)
