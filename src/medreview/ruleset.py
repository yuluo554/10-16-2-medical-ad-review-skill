"""规则包加载 + 锚点硬门 + status 作用域门控（既定口径 K1）。

三条硬纪律：

1. **锚点硬门**：缺锚点、锚点状态非 verified、或 ``quote`` 无法在对应条文快照中
   **逐字**找到的规则，**拒绝被加载进引擎**——并在"未启用清单"里显式列出原因
   （可追溯性不能只靠字段存在）。
2. **双重门控**：``quote_status``（原文核对）与 ``anchor_status``（条款号核对）
   是两个独立状态，都在产物里显式可见。
3. **分作用域门控**：一份规则包承载多用途参数时，"整包全 verified"当唯一门会让
   与判定无关的 pending 阻断判定路径——故按 ``check`` / ``bench`` / ``rules``
   三个作用域各校验自己引用的条目。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from . import constants
from .errors import AnchorUnresolved, ConfigMissing, RulesetUnavailable
from .model import Rule


def _read_json(path):
    if not os.path.isfile(path):
        raise RulesetUnavailable("规则包文件不存在: %s" % path, code="ruleset_missing")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError as exc:
        raise RulesetUnavailable("规则包 JSON 解析失败: %s (%s)" % (path, exc),
                                 code="ruleset_bad_json")


def load_clauses(path):
    """加载条文块（锚点解析的比对基准）。

    返回 ``{(source, clause): text}``。
    """
    payload = _read_json(path)
    out = {}  # type: Dict[Tuple[str, str], str]
    for block in payload.get("clauses", []):
        out[(block["source"], str(block["clause"]))] = block["text"]
    return out


def load_manifest(path):
    """加载 manifest（含基准门槛，K6：门槛是数据不是代码）。"""
    return _read_json(path)


def _anchor_resolvable(rule, clauses):
    """锚点是否可解析：条款存在 + ``quote`` 逐字出现在该条文文本中。

    **回读原文逐字校验**（不只信一个 ``located`` 布尔）——这是"假装定位成功"
    类缺陷的唯一可靠拦截手段。
    """
    key = (rule.source, str(rule.clause))
    text = clauses.get(key)
    if text is None:
        return False, "条款不存在于条文快照: %s §%s" % (rule.source, rule.clause)
    if not rule.quote:
        return False, "规则缺法条原文引用（quote 为空）"
    if rule.quote not in text:
        return False, "quote 未逐字出现在条文快照中（%s §%s）" % (rule.source, rule.clause)
    return True, ""


def load_ruleset(ruleset_file, clauses_file, scope=constants.SCOPE_CHECK):
    """加载规则包，返回 ``(enabled_rules, not_enabled)``。

    ``not_enabled`` 是**显式可见的未启用清单**：每项含 ``rule_id`` + ``reason``。
    零生效规则不是"跑挂了"而是"没有可判项"——由调用方按 NOT_ASSESSED 呈现。
    """
    if scope not in constants.SCOPES:
        raise RulesetUnavailable("未知门控作用域: %s" % scope, code="bad_scope")

    payload = _read_json(ruleset_file)
    clauses = load_clauses(clauses_file)

    enabled = []  # type: List[Rule]
    not_enabled = []  # type: List[dict]

    for raw in payload.get("rules", []):
        rule = _to_rule(raw)
        if rule.quote_status != constants.STATUS_VERIFIED:
            not_enabled.append({
                "rule_id": rule.rule_id,
                "reason": "法条原文核对状态为 %s（未核对不得生效）" % rule.quote_status,
                "code": "quote_pending",
            })
            continue
        if rule.anchor_status != constants.STATUS_VERIFIED:
            not_enabled.append({
                "rule_id": rule.rule_id,
                "reason": "条款号核对状态为 %s（未核对不得生效）" % rule.anchor_status,
                "code": "anchor_pending",
            })
            continue
        if rule.kind not in constants.KINDS:
            not_enabled.append({
                "rule_id": rule.rule_id,
                "reason": "未知判定 kind: %s" % rule.kind,
                "code": "unknown_kind",
            })
            continue
        if rule.severity not in constants.SEVERITIES:
            not_enabled.append({
                "rule_id": rule.rule_id,
                "reason": "未知 severity: %s" % rule.severity,
                "code": "unknown_severity",
            })
            continue
        if not rule.categories:
            # 适用域必须落进规则数据（不许写 any）——空集合 = 没写主体限制 = 拒绝加载
            not_enabled.append({
                "rule_id": rule.rule_id,
                "reason": "规则缺 applies_if.categories（适用域不许写 any）",
                "code": "missing_applies_if",
            })
            continue
        for category in rule.categories:
            if category not in constants.CATEGORIES:
                not_enabled.append({
                    "rule_id": rule.rule_id,
                    "reason": "未知品类: %s" % category,
                    "code": "unknown_category",
                })
                break
        else:
            ok, why = _anchor_resolvable(rule, clauses)
            if not ok:
                # 锚点解析不到 = 拒绝加载（不是静默照常判）
                not_enabled.append({
                    "rule_id": rule.rule_id,
                    "reason": why,
                    "code": "anchor_unresolved",
                })
                continue
            enabled.append(rule)

    if scope == constants.SCOPE_BENCH:
        # 基准作用域额外校验门槛条目在位（缺即配置错误，不回落默认值）
        manifest = load_manifest(os.path.join(os.path.dirname(ruleset_file), "manifest.json"))
        if "benchmark_thresholds" not in manifest:
            raise ConfigMissing("manifest 缺 benchmark_thresholds（门槛必须随数据下发）",
                                code="thresholds_missing")

    return enabled, not_enabled


def require_anchor(rule, clauses):
    """给单条规则做锚点断言（供测试与生成器共用，单一实现源）。"""
    ok, why = _anchor_resolvable(rule, clauses)
    if not ok:
        raise AnchorUnresolved(why)
    return True


def _to_rule(raw):
    return Rule(
        rule_id=raw["id"],
        source=raw["source"],
        clause=str(raw["clause"]),
        item=raw.get("item"),
        anchor=raw.get("anchor", ""),
        quote=raw.get("quote", ""),
        quote_status=raw.get("quote_status", constants.STATUS_PENDING),
        anchor_status=raw.get("anchor_status", constants.STATUS_PENDING),
        kind=raw.get("kind", ""),
        severity=raw.get("severity", ""),
        applies_if=raw.get("applies_if", {}),
        pattern_id=raw.get("pattern_id"),
        notes=raw.get("notes", ""),
    )
