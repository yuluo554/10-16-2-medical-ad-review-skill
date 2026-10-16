"""内建自检（``medreview selftest``）。

本模块是**门禁的阳性对照**：每个门禁都必须证明"注入缺陷 → 报红"，
否则"全绿"可能只是"门禁什么都没查"（空转的假门）。

自检项（全部必须通过）：
  S1 装配完整性：规则包可加载、生效规则数 > 0、每条规则锚点可解析
  S2 零字面量门禁阳性对照：注入一个政策词面 → 扫描器必须报红
  S3 网络导入门禁阳性对照：注入一个网络导入 → 扫描器必须报红
  S4 报告零外链常驻断言阳性对照：注入一个 URL → 渲染出口必须抛错
  S5 kind 分派表结构+运行双层断言：键集合一致 + 各实现互不相同 + 逐 kind 真跑
  S6 序列化确定性：同输入双跑逐字节一致
  S7 适用域反向自证：构造"不该命中"的输入，断言该规则确实未命中
"""

from __future__ import annotations

import ast
import os
import sys
from typing import List, Tuple

from . import check as check_mod
from . import constants, grade, normalize, pipeline, report as report_mod, serialize
from .errors import MedReviewError

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# 零字面量门禁的扫描面 = **参与判定的模块**（含 docstring/注释一起扫）。
# 展示/工具模块（report.py 渲染、cli.py 帮助文本、selftest.py 门禁工装）
# 不进判定词表扫描面——但 report.py 仍受"渲染层零判定"的 AST 门禁约束；
# selftest 的探针串在运行时从规则包实算（本文件零词面）。
JUDGMENT_MODULES = ("constants.py", "model.py", "normalize.py", "ruleset.py",
                    "categorize.py", "check.py", "phrase.py", "grade.py",
                    "serialize.py", "paths.py", "pipeline.py")

# 网络能力导入的扫描面 = 全部引擎源码（含展示层，防"展示层偷偷出网"）
SCAN_TARGETS = JUDGMENT_MODULES + ("report.py", "cli.py", "selftest.py")

# 网络能力导入（"纯本地不上传文案"的静态可核验形态）
NETWORK_MODULES = ("socket", "ssl", "urllib", "http", "ftplib", "telnetlib",
                   "smtplib", "requests", "httpx", "aiohttp", "asyncio")


class SelfTestError(MedReviewError):
    code = "selftest_failed"


def _read_source(name):
    path = os.path.join(SRC_DIR, name)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def scan_network_imports(source):
    """扫描源码里的网络能力导入（AST 级，含函数体内导入）。"""
    found = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in NETWORK_MODULES:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in NETWORK_MODULES:
                found.append(node.module or "")
    return found


def scan_policy_tokens(source, tokens):
    """扫描源码里的政策词面（**含 docstring/注释**，因为它们是字符串/文本的一部分）。

    ``tokens`` 运行时由规则包实算——扫描器源码自身零词面（否则扫描器自己
    就是"抄进代码的第二份真相"）。
    """
    found = []
    for token in tokens:
        if token and token in source:
            found.append(token)
    return found


def _ruleset_tokens():
    """从冻结规则包实算全部词面（条款号形态 + 匹配词 + 关键词）。

    这样扫描器**不持有任何词面字面量**（源码零政策字面量）。
    """
    engine = pipeline.build_engine(scope=constants.SCOPE_RULES)
    tokens = set()
    for rule in engine.rules:
        for group_key in ("any_of", "all_of", "none_of", "require_all_of",
                          "knowledge_terms", "commerce_terms", "groups",
                          "exclude_contexts"):
            value = engine.matches.get(rule.rule_id, {}).get(group_key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        tokens.add(item)
                    elif isinstance(item, list):
                        tokens.update(x for x in item if isinstance(x, str))
        if rule.pattern_id:
            tokens.add(rule.pattern_id)
    for entry in engine.category_rules:
        tokens.update(t for t in entry.get("terms", []) if t)
        # 品类的**反例结构**也是政策词面（写进判定模块 docstring 同样算抄词表）
        tokens.update(t for t in entry.get("exclude_contexts", []) if t)
    for entry in engine.variant_rules:
        tokens.update(t for t in entry.get("knowledge_terms", []) if t)
        tokens.update(t for t in entry.get("commerce_terms", []) if t)
    # 只保留足够长的词面（短词误伤无关标识符；阈值是"判定词表"不是参数值）
    return tuple(sorted(t for t in tokens if len(t) >= 2))


def s1_assembly():
    engine = pipeline.build_engine()
    if not engine.rules:
        return False, "生效规则数为 0（规则包未装配成功）"
    if engine.not_enabled and len(engine.not_enabled) > 3:
        # 未启用条目只应是显式登记的三条兜底条款
        return False, "未启用条目异常偏多：%d" % len(engine.not_enabled)
    return True, "生效规则 %d 条，未启用 %d 条" % (len(engine.rules), len(engine.not_enabled))


def s2_policy_token_positive_control():
    """阴性对照 0 命中 + 阳性对照（注入真实词面）必报红——证明门禁不是空转。

    探针串**运行时从规则包实算**（本文件零词面字面量）。
    """
    tokens = _ruleset_tokens()
    if not tokens:
        return False, "词面集合为空——门禁是空转的（分母为 0）"

    clean_hits = []
    for name in JUDGMENT_MODULES:
        clean_hits.extend(scan_policy_tokens(_read_source(name), tokens))
    if clean_hits:
        return False, "判定模块竟含判定词表词面：%s" % clean_hits[:3]

    probe = sorted(tokens, key=len)[-1]  # 取一个真实词面（非字面量）
    injected = _read_source("model.py") + "\n# " + probe + "\n"
    dirty_hits = scan_policy_tokens(injected, tokens)
    if not dirty_hits:
        return False, "注入词面后扫描器仍报绿——假门"
    return True, "阴性对照 0 命中；阳性对照命中 %d 个词面" % len(dirty_hits)


def s3_network_import_positive_control():
    clean = []
    for name in SCAN_TARGETS:
        clean.extend(scan_network_imports(_read_source(name)))
    if clean:
        return False, "引擎源码含网络导入：%s" % clean
    injected = "import socket\nimport urllib.request\n"
    hits = scan_network_imports(injected)
    if len(hits) < 2:
        return False, "注入网络导入后扫描器仍报绿——假门"
    return True, "阴性对照 0 命中；阳性对照命中 %s" % hits


def s4_report_no_link_positive_control():
    text = "正文无链接"
    try:
        report_mod.assert_no_external_links(text)
    except report_mod.RenderError:
        return False, "阴性对照被误判为含外链"
    try:
        report_mod.assert_no_external_links(text + " https://example.com")
    except report_mod.RenderError:
        return True, "阴性对照通过；阳性对照正确报错"
    return False, "注入 URL 后常驻断言未触发——假门"


def s5_dispatch_table():
    keys = check_mod.dispatch_table_keys()
    if set(keys) != set(constants.KINDS):
        return False, "分派表键与 kind 常量集合不一致：%s vs %s" % (keys, constants.KINDS)
    handlers = [check_mod.DISPATCH[k] for k in keys]
    if len(set(handlers)) != len(handlers):
        return False, "两个 kind 指向同一实现（复制粘贴型缺陷）"
    # 运行层：逐 kind 真跑一遍不抛错
    engine = pipeline.build_engine()
    rule_by_kind = {}
    for rule in engine.rules:
        rule_by_kind.setdefault(rule.kind, rule)
    missing = [k for k in constants.KINDS if k not in rule_by_kind]
    for kind in keys:
        rule = rule_by_kind.get(kind)
        if rule is None:
            continue
        try:
            check_mod.check_rule(rule, engine.matches.get(rule.rule_id),
                                 "XX医疗美容门诊部（虚构）测试文本", ("medical",))
        except Exception as exc:  # noqa: BLE001 - 自检要报告任何异常
            return False, "kind %s 运行期抛错：%s" % (kind, exc)
    note = "" if not missing else "（无规则覆盖的 kind：%s，待 M3 建规则）" % missing
    return True, "%d 个 kind 键一致、实现互异、逐条真跑通过%s" % (len(keys), note)


def s6_serialization_determinism():
    payload = {"b": 2, "a": "中文", "list": [1, 2, 3]}
    first = serialize.dumps_json(payload)
    second = serialize.dumps_json(payload)
    if first != second:
        return False, "同输入两次序列化不一致"
    if "\r" in first:
        return False, "序列化含 CR（跨平台字节漂移）"
    if not first.endswith("\n"):
        return False, "序列化缺结尾换行"
    return True, "双跑一致、LF、有结尾换行"


def s7_applies_reverse_selfcheck():
    """适用域反向自证：只对保健食品生效的规则，不得被判命中医疗类内容。

    探针文本与规则前缀**运行时实算**（本文件零词面字面量）。
    """
    engine = pipeline.build_engine()
    health_rules = [r for r in engine.rules
                    if r.categories == (constants.CATEGORY_HEALTH_FOOD,)]
    if not health_rules:
        return False, "找不到只适用保健食品的规则——反向自证无对象"
    health_ids = {r.rule_id for r in health_rules}

    # 构造一段**医疗**品类文本（用医疗信号词实算），断言保健食品专属规则全部 skipped
    medical_terms = []
    for entry in engine.category_rules:
        if entry["category"] == constants.CATEGORY_MEDICAL:
            medical_terms = list(entry["terms"])[:2]
    probe = "".join(medical_terms) + "推广内容"
    item = normalize.normalize_text(probe)
    rep = pipeline.run_check(engine, item)

    for finding in rep.findings:
        if finding.rule_id in health_ids:
            return False, "只适用保健食品的规则误命中医疗内容（适用域写错）：%s" % finding.rule_id
    skipped = [r.rule_id for r in rep.rule_results
               if r.state == constants.RULE_SKIPPED and r.rule_id in health_ids]
    if not skipped:
        return False, "保健食品专属规则未被判不适用——适用域反向无观测"
    return True, "保健食品专属规则对医疗内容判不适用 %d 条，零误命中" % len(skipped)


CHECKS = [
    ("S1 装配完整性", s1_assembly),
    ("S2 零字面量门禁阳性对照", s2_policy_token_positive_control),
    ("S3 网络导入门禁阳性对照", s3_network_import_positive_control),
    ("S4 报告零外链阳性对照", s4_report_no_link_positive_control),
    ("S5 kind 分派表双层断言", s5_dispatch_table),
    ("S6 序列化确定性", s6_serialization_determinism),
    ("S7 适用域反向自证", s7_applies_reverse_selfcheck),
]


def run_selftest(stream=None):
    stream = stream or sys.stdout
    failed = []
    for label, func in CHECKS:
        try:
            ok, detail = func()
        except Exception as exc:  # noqa: BLE001 - 自检要报告任何异常
            ok, detail = False, "异常：%s" % exc
        stream.write("[%s] %s —— %s\n" % ("PASS" if ok else "FAIL", label, detail))
        if not ok:
            failed.append(label)
    if failed:
        stream.write("SELFTEST_FAILED：%s\n" % "、".join(failed))
        return constants.EXIT_FINDING
    stream.write("SELFTEST_OK\n")
    return constants.EXIT_OK
