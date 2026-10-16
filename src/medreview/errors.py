"""领域异常。

纪律：领域异常一律继承 ``ValueError``——CLI 的 ``except`` 集合是有限的，
继承裸 ``Exception`` 的异常会逃逸成未捕获 traceback（用户看到"程序崩了"
而不是"输入有问题，退出码 2"），而单元测试可能全绿。
"""

from __future__ import annotations


class MedReviewError(ValueError):
    """本包全部领域异常的基类（继承 ValueError 以便 CLI 捕获）。"""

    code = "error"

    def __init__(self, message, code=None):
        super(MedReviewError, self).__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class InputUnavailable(MedReviewError):
    """输入不可用：缺文件、坏格式、空文案等（→ 退出码 2）。"""

    code = "input_unavailable"


class UsageError(MedReviewError):
    """用法错误：未知子命令、未知套件名、参数组合非法（→ 退出码 2）。"""

    code = "usage_error"


class RulesetUnavailable(MedReviewError):
    """规则包不可用：文件缺失、锚点解析不到、manifest 缺失（→ 退出码 3）。"""

    code = "ruleset_unavailable"


class AnchorUnresolved(RulesetUnavailable):
    """规则锚点解析不到——该规则拒绝被引擎加载（进未启用清单）。"""

    code = "anchor_unresolved"


class ConfigMissing(RulesetUnavailable):
    """基准门槛缺失（配置错误，不回落代码默认值 → 退出码 2）。"""

    code = "config_missing"
