"""对账语义的**单一实现源**（既定口径 K7）。

真值库测试与基准 runner 共用本模块的函数——否则会出现"基准说达标、
测试说不过"的双口径漂移。

**真值库只存输入与期望**：``expect_keys`` 的键名**自带结论**
（``grade:BLOCK`` / ``hit:MAM-7-3`` / ``rule:skipped:AL-16-1``），取值恒为哑值
``ok``——状态一变键名就变，集合比对立刻看得见。
若真值库里出现 ``observed`` 一类字段即红（那说明"观测"没在运行时产生）。
"""

from __future__ import annotations

from .. import constants

DUMMY = "ok"
FORBIDDEN_TRUTH_FIELDS = ("observed", "actual", "engine_output", "computed")


def observed_keys(report):
    """把一次真实审查的结论摊成**自带结论的键名集合**（观测器实算）。"""
    keys = set()
    keys.add("grade:%s" % report.grade)

    for category in report.categories:
        keys.add("category:%s" % category)

    for finding in report.findings:
        keys.add("hit:%s" % finding.rule_id)
        keys.add("hit_severity:%s:%s" % (finding.rule_id, finding.severity))

    for result in report.rule_results:
        if result.state == constants.RULE_SKIPPED:
            keys.add("rule:skipped:%s" % result.rule_id)
        elif result.state == constants.RULE_INPUT_REQUIRED:
            keys.add("rule:input_required:%s" % result.rule_id)
        elif result.state == constants.RULE_COMPLIANT:
            keys.add("rule:compliant:%s" % result.rule_id)
        else:
            keys.add("rule:noncompliant:%s" % result.rule_id)

    for entry in report.input_required:
        keys.add("input_required:%s" % entry["rule_id"])

    for entry in report.not_enabled:
        keys.add("not_enabled:%s" % entry["rule_id"])

    return keys


def expect_keys_of(case):
    """真值用例的**正向**期望键集合（``expect_keys`` 列表 → 集合）。

    正向键的语义按前缀分区，**各自独立断言**（不做"断言全世界"的整集比对）：
      ``grade:``           —— 结论，**精确相等**
      ``category:``        —— 品类集合，**精确相等**（本次判定的品类不能多也不能少）
      ``hit:``             —— 必须命中（子集断言）
      ``rule:skipped:``    —— 必须判不适用（子集断言；这是适用域反向的核心）
      ``rule:input_required:`` —— 必须判待补材料（子集断言）
      ``rule:compliant:``  —— 必须判通过（子集断言）
      ``input_required:``  —— 待补材料清单必须含该条
    """
    return set(case.get("expect_keys") or ())


def forbid_keys_of(case):
    """**负向**期望键集合（``forbid_keys``）：必须**不出现**的结论。

    这是"这条规则不该命中"的机器可验形式（与适用域反向样例配套）。
    """
    return set(case.get("forbid_keys") or ())


def _partition(keys, prefix):
    return set(k for k in keys if k.startswith(prefix))


def compare_case(case, report):
    """单例对账：返回 ``(ok, failures)``。

    ``failures`` 是**逐分区**的失败说明列表（不是一整块集合差异）——
    判别口诀：**"我要验的是 X，断言里就只准出现 X"**。整集比对（``== []``）
    等于同时断言了所有判据，任何一条合法命中都会打红。
    """
    observed = observed_keys(report)
    expected = expect_keys_of(case)
    forbidden = forbid_keys_of(case)
    failures = []

    # 1) grade 精确
    exp_grades = _partition(expected, "grade:")
    obs_grades = _partition(observed, "grade:")
    if exp_grades and exp_grades != obs_grades:
        failures.append("grade 不符：期望 %s，实得 %s"
                        % (sorted(exp_grades), sorted(obs_grades)))

    # 2) categories 精确（本次品类集合）
    exp_cats = _partition(expected, "category:")
    obs_cats = _partition(observed, "category:")
    if exp_cats or obs_cats:
        if exp_cats != obs_cats:
            failures.append("品类不符：期望 %s，实得 %s"
                            % (sorted(exp_cats), sorted(obs_cats)))

    # 3) 正向子集断言（各分区独立）
    for prefix, label in (("hit:", "应命中而未命中"),
                          ("rule:skipped:", "应判不适用而未判"),
                          ("rule:input_required:", "应判待补材料而未判"),
                          ("rule:compliant:", "应判通过而未判"),
                          ("input_required:", "待补材料清单应含而未含")):
        for key in sorted(_partition(expected, prefix)):
            if key not in observed:
                failures.append("%s：%s" % (label, key))

    # 4) 负向断言（必须不出现）
    for key in sorted(forbidden):
        if key in observed:
            failures.append("不该出现却出现：%s" % key)

    return (not failures), failures


def truth_field_violations(cases_payload):
    """真值库不得含"观测类"字段（冻结件里出现观测 = 它没在运行时产生）。"""
    violations = []
    for case in cases_payload.get("cases", []):
        for field in FORBIDDEN_TRUTH_FIELDS:
            if field in case:
                violations.append("%s.%s" % (case.get("id", "?"), field))
    return violations
