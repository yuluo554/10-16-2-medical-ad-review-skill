"""分级映射（模块 4 的映射层，**唯一实现源** K3）。

映射表由规则包 ``severity`` 字段驱动，版本化冻结；报告层只渲染，不重算。

判定优先级：BLOCK > WARN > OK > NOT_ASSESSED。

四态语义（见 plan/03 §1.1）：
  - BLOCK：至少一条 severity=block 的规则被判 noncompliant
  - WARN：无 BLOCK，且至少一条 severity=warn 规则命中
  - OK：有适用规则且全部通过（无命中、无待补材料）
  - NOT_ASSESSED：**一条适用规则都没有**（非涉医内容 / 全部规则因品类被 skipped）
    ——"没查出问题"与"没检查过"必须可区分

**另有第五种呈现态（不改变 grade，独立成节）**：有适用规则但存在
``input_required``（需用户补材料）→ grade 记 ``OK`` 会虚高，故此处单独暴露
``has_input_required``，报告**独立成节**呈现"待补材料"，且该节的存在会阻断
"全部通过"的表述。
"""

from __future__ import annotations

from . import constants


class GradeResult(object):
    """分级结果：结论 + 触发依据 + 覆盖面。"""

    __slots__ = ("grade", "block_count", "warn_count", "applied_count",
                 "input_required_count", "reason")

    def __init__(self, grade, block_count, warn_count, applied_count,
                 input_required_count, reason):
        self.grade = grade
        self.block_count = block_count
        self.warn_count = warn_count
        self.applied_count = applied_count
        self.input_required_count = input_required_count
        self.reason = reason

    def to_dict(self):
        return {
            "grade": self.grade,
            "block_count": self.block_count,
            "warn_count": self.warn_count,
            "applied_count": self.applied_count,
            "input_required_count": self.input_required_count,
            "reason": self.reason,
        }


def grade_results(rule_results):
    """按规则级结果算结论（唯一实现源）。"""
    block = 0
    warn = 0
    applied = 0
    input_required = 0

    for result in rule_results:
        if result.state == constants.RULE_SKIPPED:
            continue
        applied += 1
        if result.state == constants.RULE_INPUT_REQUIRED:
            input_required += 1
            continue
        if result.state != constants.RULE_NONCOMPLIANT:
            continue
        for finding in result.findings:
            if finding.severity == constants.SEVERITY_BLOCK:
                block += 1
            elif finding.severity == constants.SEVERITY_WARN:
                warn += 1

    if block:
        grade = constants.GRADE_BLOCK
        reason = "命中 %d 条确定性禁止情形" % block
    elif warn:
        grade = constants.GRADE_WARN
        reason = "命中 %d 条待复核/白名单外表述" % warn
    elif input_required:
        # **有规则判不了** → 不得报 OK（OK 的语义是"查过且没问题"）。
        # 归入 WARN（题面分级口径明示 WARN 含"语境存疑待人工复核项"），
        # 并由报告"待补材料清单"节逐条列明缺什么、为什么判不了。
        grade = constants.GRADE_WARN
        reason = ("已评估 %d 条规则无命中，但有 %d 条规则需补材料后方可判定——"
                  "结论不完整，不得读作合规" % (applied, input_required))
    elif applied:
        grade = constants.GRADE_OK
        reason = "已评估 %d 条规则，全部通过" % applied
    else:
        grade = constants.GRADE_NOT_ASSESSED
        reason = "无适用规则（非涉医内容或全部规则不适用）——未评估，不等于合规"

    return GradeResult(grade, block, warn, applied, input_required, reason)


def has_finding(grade):
    """该结论是否应让 CLI 返回 EXIT_FINDING（"查出了问题"的既定语义）。"""
    return grade in constants.GRADES_WITH_FINDING
