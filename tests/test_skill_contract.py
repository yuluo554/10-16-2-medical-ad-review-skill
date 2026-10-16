"""SKILL.md 机器契约块 ↔ 代码字段 双向一致性门禁。

（Skill/文档型交付的硬门）SKILL.md 内嵌机器可解析契约块
（``<!-- contract-fields: ... -->``）后，必须有三条结构断言：
 ① 契约块唯一性；
 ② 契约块字段集合 == 代码字段常量（**双向**：文档不许多、不许少）；
 ③ 字段序 == 输出 JSON 实际字段序。

没有这条门，"文档说明的字段"与"代码真的输出的字段"各自漂移，
agent 消费者按文档取字段会静默取空。

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

from medreview import constants, normalize, pipeline, report as report_mod  # noqa: E402

CONTRACT_RE = re.compile(r"<!--\s*contract-fields:\s*(.*?)\s*-->")


def _skill_text():
    with open(os.path.join(ROOT, "SKILL.md"), "r", encoding="utf-8") as handle:
        return handle.read()


def contract_fields():
    matches = CONTRACT_RE.findall(_skill_text())
    assert len(matches) == 1, "SKILL.md 的契约块必须唯一（实得 %d 个）" % len(matches)
    return matches[0].split()


def test_contract_block_is_unique_and_nonempty():
    fields = contract_fields()
    assert fields, "契约块字段为空（扫描面为空 = 假门）"


def test_contract_fields_match_code_fields():
    """契约块 ↔ 代码字段常量**双向**一致（文档不许多、不许少）。"""
    documented = set(contract_fields())
    # 代码侧字段常量：报告顶层字段 + 输入项字段 + 命中四要素
    code_fields = set()
    for name in dir(constants):
        if name.startswith("CONTRACT_FIELDS_"):
            code_fields.update(getattr(constants, name))
    assert code_fields, "代码侧缺契约字段常量（constants.CONTRACT_FIELDS_*）"

    only_in_doc = sorted(documented - code_fields)
    only_in_code = sorted(code_fields - documented)
    assert not only_in_doc, "契约块声明了代码没有的字段：%s" % only_in_doc
    assert not only_in_code, "代码有字段但契约块未声明：%s" % only_in_code


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
