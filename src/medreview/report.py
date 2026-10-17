"""分级报告（模块 4）。

**渲染层零判定**（既定口径 D12）：本模块只消费 ``Report`` 既有结论，
不重算任何判定、不新增结论。判别：把报告单独发给一个没有引擎的人，
他看不出这份报告是"渲染"的还是"计算"的。

**单一渲染源**：``report_sections()`` 产出结构化章节，单件 Markdown 渲染器、
批量 Markdown 渲染器与 JSON 渲染器各自读它——"多格式内容一致"于是是
**结构性质**，不是人工比对；``_section_lines()`` 是章节正文的唯一实现源。

**零判定可静态核验**（AST 门禁三条，见 ``selftest`` 的 S8/S9/S10）：
本模块**不 import 任何引擎模块**（只许标准库）、**不做算术**（模板式字符串
格式化与字符串拼接除外）、**不内联政策数值**（条款号引用形态与百分比阈值
形态一律不得出现，数值只从 ``Report`` 数据来）。

**无外链**：报告正文不得含 URL（断网可开、可归档）；规则的官方 URL 只出现在
机读产物的 ``rule_sources`` 字段里（供核证，非链接）。报告出口即断言
``assert_no_external_links``（常驻断言，不是"记得跑那条测试"）。
"""

from __future__ import annotations

import re

DISCLAIMER = (
    "**免责声明**：本报告为发布前**辅助自查**参考，不构成法律意见，"
    "不替代广告审查机关的官方审查。判定结果依赖本工具内置的冻结规则包"
    "（基准日见报告头部），法规更新后须重新核对。发布前请以官方审查结论为准。"
)

_HTTP_RE = re.compile(r"https?://", re.IGNORECASE)


class RenderError(ValueError):
    """渲染出口断言失败（属输入/配置类，CLI 捕获为退出码 2）。"""


def assert_no_external_links(text):
    """渲染出口常驻硬断言：报告正文无 http(s) 外链（断网可开）。"""
    found = _HTTP_RE.findall(text)
    if found:
        raise RenderError("报告正文含外链（断网不可开）: %s" % found[:3])
    return True


def report_sections(report):
    """结构化章节（**单一渲染源**，两种格式共用）。"""
    sections = []

    proof_file = getattr(report.item, "proof_file", None)
    if proof_file:
        proof_desc = "%s（sha256 %s…，%d 字节；只记摘要，实质核验以原件为准）" % (
            proof_file.get("name", "?"), (proof_file.get("sha256") or "")[:12],
            proof_file.get("bytes", 0))
    else:
        proof_desc = "未提供"

    sections.append({
        "id": "input_facts",
        "title": "一、输入事实",
        "rows": [
            ("内容 ID", report.item.id),
            ("发布渠道", report.item.channel or "未提供"),
            ("主体类型", report.item.subject or "未提供"),
            ("审查证明", report.item.proof or "未提供"),
            ("证明材料文件", proof_desc),
            ("原文", report.item.text),
        ],
    })

    coverage_rows = [
        ("规则包版本", report.ruleset_version or "未派生"),
        ("规则包基准日", report.ruleset_basis_date or "未提供"),
        ("本次适用规则数", str(report.applied_rule_count)),
        ("规则包总条目数", str(report.total_rule_count)),
    ]
    sections.append({
        "id": "coverage",
        "title": "二、本次评估覆盖",
        "rows": coverage_rows,
        "not_enabled": list(report.not_enabled),
    })

    sections.append({
        "id": "grade",
        "title": "三、分级结论",
        "grade": report.grade,
        "categories": list(report.categories),
    })

    findings = report.findings
    sections.append({
        "id": "findings",
        "title": "四、逐条命中明细",
        "findings": [f.to_dict() for f in findings],
    })

    sections.append({
        "id": "input_required",
        "title": "五、待补材料清单",
        "items": list(report.input_required),
    })

    sections.append({
        "id": "advisory",
        "title": "六、语境提示（advisory，不参与分级）",
        "items": list(report.advisories),
    })

    sections.append({
        "id": "sources",
        "title": "七、规则来源",
        "items": list(report.rule_sources),
    })

    sections.append({
        "id": "disclaimer",
        "title": "八、免责声明",
        "text": DISCLAIMER,
    })

    return sections


def _fmt_rows(rows):
    if not rows:
        return "（无）"
    return "\n".join("- **%s**：%s" % (key, value) for key, value in rows)


# 标题层级查表（**不用字符串乘法**：报告层不做算术，AST 门禁会核）
_HEADING_PREFIX = {1: "#", 2: "##", 3: "###"}


def _section_lines(section):
    """单个章节的正文行（单件渲染器与批量渲染器的**唯一实现源**）。"""
    lines = []
    if section["id"] == "grade":
        cats = section["categories"]
        lines.append("- 判定品类：%s" % ("、".join(cats) if cats else "非涉医内容（未评估）"))
    elif section["id"] == "findings":
        if not section["findings"]:
            lines.append("（无命中）")
        for finding in section["findings"]:
            lines.append("- **[%s]** `%s`" % (finding["severity"], finding["rule_id"]))
            lines.append("  - 条款锚点：%s" % finding["clause_anchor"])
            lines.append("  - 法条原文：%s" % finding["quote"])
            lines.append("  - 命中证据：%s" % finding["evidence"])
    elif section["id"] == "coverage":
        lines.append(_fmt_rows(section["rows"]))
        if section["not_enabled"]:
            lines.append("**未启用清单**（不参与本次判定）：")
            for entry in section["not_enabled"]:
                lines.append("- `%s`：%s" % (entry["rule_id"], entry["reason"]))
        else:
            lines.append("未启用清单：（空）")
    elif section["id"] == "input_required":
        if not section["items"]:
            lines.append("（无）")
        for entry in section["items"]:
            lines.append("- `%s`：%s" % (entry["rule_id"], entry["reason"]))
    elif section["id"] == "advisory":
        if not section["items"]:
            lines.append("（无）")
        for entry in section["items"]:
            # advisory 有两种形态：纯提示（hint）与带**实算信号**的疑似项。
            # 后者必须把命中词与条款锚点一并呈现（提示要可核验，不是散文）。
            label = entry.get("text", "")
            signals = entry.get("signals") or []
            lines.append("- %s" % label)
            for signal in signals:
                lines.append("  - 命中信号：%s（%s）"
                             % ("、".join(signal.get("matched_terms") or ()),
                                signal.get("anchor", "")))
            if entry.get("note"):
                lines.append("  - 说明：%s" % entry["note"])
    elif section["id"] == "sources":
        if not section["items"]:
            lines.append("（无）")
        for entry in section["items"]:
            # **人读报告零外链**（断网可开）：URL 只出现在机读产物字段里
            lines.append("- `%s`｜%s｜%s｜基准日 %s"
                         % (entry["rule_id"], entry["source_title"],
                            entry["anchor"], entry["basis_date"] or "未提供"))
    elif section["id"] == "disclaimer":
        lines.append(section["text"])
    else:
        lines.append(_fmt_rows(section.get("rows") or []))
    lines.append("")
    return lines


def _render_sections(sections, level):
    """把结构化章节渲染成 Markdown 行（``level`` = 标题井号层级）。"""
    prefix = _HEADING_PREFIX[level]
    lines = []
    for section in sections:
        lines.append("%s %s" % (prefix, section["title"]))
        lines.append("")
        lines.extend(_section_lines(section))
    return lines


def render_markdown(report):
    """人读 Markdown 渲染器（只读 ``report_sections``）。"""
    lines = [
        "# 医疗广告合规预审报告",
        "",
        "- 内容 ID：`%s`" % report.item.id,
        "- 结论：**%s**" % report.grade,
        "",
    ]
    lines.extend(_render_sections(report_sections(report), 2))
    text = "\n".join(lines).rstrip("\n") + "\n"
    assert_no_external_links(text)
    return text


def render_markdown_batch(entries, summary):
    """批量人读报告（**同一 ``report_sections`` 渲染源**，逐件出全必备章节）。

    ``entries`` = ``pipeline.scan_items`` 的返回（``ok`` / ``report`` / ``id`` / ``error``）。
    ``summary`` 由调用方实算（**报告层不重算分级**），键：``total`` / ``failed`` / ``finding``。
    """
    lines = [
        "# 医疗广告合规预审报告（批量）",
        "",
        "- 总件数：%d" % summary.get("total", len(entries)),
        "- 处理失败：%d" % summary.get("failed", 0),
        "- 检出命中：%s" % ("是" if summary.get("finding") else "否"),
        "",
    ]
    total = len(entries)
    for index, entry in enumerate(entries, 1):
        if not entry.get("ok"):
            lines.append("## 件 %d/%d：`%s`（**处理失败**）"
                         % (index, total, entry.get("id", "?")))
            lines.append("")
            lines.append("- 失败原因：%s" % entry.get("error", ""))
            lines.append("")
            continue
        report = entry["report"]
        lines.append("## 件 %d/%d：`%s`" % (index, total, report.item.id))
        lines.append("")
        lines.append("- 结论：**%s**" % report.grade)
        lines.append("")
        lines.extend(_render_sections(report_sections(report), 3))
    text = "\n".join(lines).rstrip("\n") + "\n"
    assert_no_external_links(text)
    return text


def render_json(report):
    """机读 JSON 载荷（与 Markdown **同一渲染源**；由 serialize 单点落盘）。"""
    payload = report.to_dict()
    payload["sections"] = [
        {k: v for k, v in section.items()} for section in report_sections(report)
    ]
    payload["disclaimer"] = DISCLAIMER
    return payload
