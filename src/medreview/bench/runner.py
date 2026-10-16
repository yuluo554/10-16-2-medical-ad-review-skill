"""基准 runner（B1–B4，退出码 0/1/2）。

三条硬纪律：

1. **先过冻结件再跑**：``_load_frozen_cases()`` 先跑 ``check_frozen_ledger()``
   再 ``load_ground_truth()``——任一不一致即 fail-fast（exit 1 + 逐条列出缺失/
   多余/内容不符的用例 id）。这是"用户敲的那条命令真读了冻结台账"的落地。
2. **观测由观测器运行时实算**：把用例内联输入**真喂引擎**（``run_check``），
   不与真值库比"两份预先算好的答案"。
3. **门槛随数据下发**：阈值只从 manifest 读；缺失即配置错误（exit 2），
   **不得回落代码默认值**。
"""

from __future__ import annotations

import json
import os
import sys

from .. import constants, normalize, pipeline
from ..errors import ConfigMissing
from ..paths import manifest_path, package_fixtures_dir
from . import cases as cases_mod
from . import ledger as ledger_mod

SUITES = ("b1_category", "b2_prohibited", "b3_applies_reverse", "b4_rule_coverage")

EXIT_OK = 0
EXIT_NOT_MET = 1
EXIT_USAGE = 2


def load_fixture_payload(explicit_dir=None):
    directory = explicit_dir or package_fixtures_dir()
    path = os.path.join(directory, "cases.json")
    if not os.path.isfile(path):
        raise FileNotFoundError("真值库不存在: %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle), path


def _load_frozen_cases(explicit_dir=None):
    """生产入口的冻结件加载：**先校验台账再加载**（fail-fast）。"""
    payload, path = load_fixture_payload(explicit_dir)
    problems = ledger_mod.check_frozen_ledger(payload)
    if problems:
        raise FrozenLedgerError(problems)
    violations = cases_mod.truth_field_violations(payload)
    if violations:
        raise FrozenLedgerError(["真值库含观测类字段（观测必须在运行时产生）: %s" % v
                                 for v in violations])
    return payload


class FrozenLedgerError(Exception):
    """冻结台账校验失败（→ 退出码 1，逐条列出问题）。"""

    def __init__(self, problems):
        super(FrozenLedgerError, self).__init__("冻结台账校验失败")
        self.problems = list(problems)


def load_thresholds(engine):
    """门槛只从 manifest 读（缺失 → ConfigMissing → exit 2）。"""
    manifest = engine.manifest or {}
    thresholds = manifest.get("benchmark_thresholds")
    if not thresholds:
        raise ConfigMissing("manifest 缺 benchmark_thresholds（门槛必须随数据下发）",
                            code="thresholds_missing")
    return thresholds


def run_benchmarks(only=None, fixtures_dir=None):
    """跑基准，返回 ``(exit_code, summary)``。

    **探活打在这一层**：``run_benchmarks`` 返回非 0 才算"基准真的把缺陷跑出来了"
    （只断言内部对账函数返回非空证明不了这一点）。
    """
    if only is not None and only not in SUITES:
        return EXIT_USAGE, {"error": "未知套件名: %s" % only, "suites": list(SUITES)}

    engine = pipeline.build_engine(scope=constants.SCOPE_BENCH)
    try:
        thresholds = load_thresholds(engine)
    except ConfigMissing as exc:
        return EXIT_USAGE, {"error": exc.message, "code": "config_missing"}

    try:
        payload = _load_frozen_cases(fixtures_dir)
    except FrozenLedgerError as exc:
        return EXIT_NOT_MET, {"error": "冻结台账校验失败", "problems": exc.problems,
                              "truth_source": "frozen"}
    except FileNotFoundError as exc:
        return EXIT_NOT_MET, {"error": str(exc), "not_enabled": True,
                              "truth_source": "missing",
                              "notes": "真值库文件缺失：整套件未启用（与'跑了没过'同码不同义）"}

    selected = [only] if only else list(SUITES)
    summary = {
        "truth_source": "frozen",
        "ruleset_version": engine.ruleset_version,
        "thresholds": thresholds,
        "suites": {},
        "not_enabled": [],
    }
    not_met = []

    for suite in selected:
        result = _run_suite(suite, engine, payload, thresholds)
        summary["suites"][suite] = result
        if result.get("not_enabled"):
            summary["not_enabled"].append(suite)
        if not result.get("passed"):
            not_met.append(suite)

    summary["passed"] = not not_met
    summary["not_met"] = not_met
    return (EXIT_OK if not not_met else EXIT_NOT_MET), summary


def _cases_for(payload, suite):
    return [c for c in payload.get("cases", []) if c.get("suite") == suite]


def _run_suite(suite, engine, payload, thresholds):
    items = _cases_for(payload, suite)
    if not items:
        # 空分母不冒充通过：not_enabled + notes 写明 + 判未达标
        return {"suite": suite, "passed": False, "not_enabled": True,
                "notes": "该类用例未生成（不假装覆盖）", "total": 0}

    mismatches = []
    checked = 0
    for case in items:
        item = normalize.normalize_text(case["input"], channel=case.get("channel"),
                                        subject=case.get("subject"),
                                        proof=case.get("proof"),
                                        scenario=case.get("scenario"))
        report = pipeline.run_check(engine, item)
        ok, failures = cases_mod.compare_case(case, report)
        checked += 1
        if not ok:
            mismatches.append({"id": case["id"], "failures": failures})

    if suite == "b1_category":
        accuracy = (len(items) - len(mismatches)) / float(len(items))
        passed = accuracy >= thresholds.get("b1_min_accuracy", 1.0)
        return {"suite": suite, "passed": passed, "accuracy": accuracy,
                "total": len(items), "mismatches": mismatches}

    if suite == "b2_prohibited":
        # 误报数：把"不该出现的命中"（forbid_keys 命中）与"品类不符"计为误报
        false_block = sum(
            1 for m in mismatches
            if any("不该出现却出现" in f or "品类不符" in f for f in m["failures"]))
        passed = false_block <= thresholds.get("b2_false_block_max", 0) and not mismatches
        return {"suite": suite, "passed": passed, "false_block": false_block,
                "total": len(items), "mismatches": mismatches}

    if suite == "b3_applies_reverse":
        # 反向套件：断言"这条规则不该命中"的用例全部不被命中
        passed = not mismatches
        rate = (len(items) - len(mismatches)) / float(len(items))
        passed = passed and rate >= thresholds.get("b3_reverse_pass_min", 1.0)
        return {"suite": suite, "passed": passed, "reverse_pass_rate": rate,
                "total": len(items), "mismatches": mismatches}

    # b4 规则驱动覆盖：每条生效规则至少被一个用例触达（分母 = 生效规则数）
    touched = set()
    for case in items:
        item = normalize.normalize_text(case["input"], proof=case.get("proof"),
                                        scenario=case.get("scenario"))
        report = pipeline.run_check(engine, item)
        for key in cases_mod.observed_keys(report):
            # **只认"真被判过"的规则**：skipped 是"不适用"（规则没参与判定），
            # 把它算作"已覆盖"会让覆盖数虚高（删掉覆盖用例也不会红 = 假门）。
            if key.startswith("rule:skipped:"):
                continue
            if key.startswith("rule:") or key.startswith("hit:"):
                touched.add(key.split(":", 2)[-1])
    enabled_ids = set(r.rule_id for r in engine.rules)
    uncovered = sorted(enabled_ids - touched)
    coverage = (len(enabled_ids) - len(uncovered)) / float(len(enabled_ids)) if enabled_ids else 0.0
    passed = coverage >= thresholds.get("b4_min_coverage", 1.0) and not mismatches
    return {"suite": suite, "passed": passed, "coverage": coverage,
            "total": len(items), "uncovered_rules": uncovered, "mismatches": mismatches}


def format_summary(summary):
    """人读汇总（文本里同步声明未达标与未启用）。"""
    lines = ["基准结果"]
    if "error" in summary:
        lines.append("错误：%s" % summary["error"])
        for problem in summary.get("problems", []):
            lines.append("  - %s" % problem)
        return "\n".join(lines) + "\n"

    lines.append("真值来源：%s" % summary.get("truth_source"))
    lines.append("规则包版本：%s" % summary.get("ruleset_version"))
    lines.append("")
    for suite in SUITES:
        result = summary["suites"].get(suite)
        if result is None:
            continue
        mark = "达标" if result.get("passed") else "未达标"
        if result.get("not_enabled"):
            mark = "未启用（该类用例未生成）"
        lines.append("- %s：%s（用例 %d）" % (suite, mark, result.get("total", 0)))
        if result.get("mismatches"):
            for mismatch in result["mismatches"][:8]:
                lines.append("    - %s：" % mismatch["id"])
                for failure in mismatch["failures"][:4]:
                    lines.append("        %s" % failure)
        if result.get("uncovered_rules"):
            lines.append("    - 未覆盖规则：%s" % result["uncovered_rules"])
    lines.append("")
    if summary.get("not_met"):
        lines.append("未达标套件：%s" % "、".join(summary["not_met"]))
    else:
        lines.append("全部套件达标")
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = None
    if "--only" in argv:
        idx = argv.index("--only")
        if idx + 1 >= len(argv):
            sys.stderr.write("--only 需要一个套件名\n")
            return EXIT_USAGE
        only = argv[idx + 1]

    code, summary = run_benchmarks(only=only)
    text = format_summary(summary)
    stream = sys.stderr if code == EXIT_USAGE else sys.stdout
    stream.write(text)
    return code
