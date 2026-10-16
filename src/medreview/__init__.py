"""medreview —— 医疗/医美/药品/器械/保健食品广告合规预审体检（确定性规则引擎）。

版本号**由冻结规则包的 manifest 派生**（既定口径 K8），不在代码里写版本字面量——
否则版本号与规则包本体成了两份可能不一致的真相，而"同版本 + 同输入 = 同输出"
的可复现承诺正是挂在版本号上的。
"""

from __future__ import annotations

import json
import os

__all__ = ["ruleset_version", "basis_date", "RULESET_VERSION", "BASIS_DATE"]


def _read_manifest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "references", "manifest.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


_MANIFEST = _read_manifest()

#: 规则包版本（由 manifest 派生；缺失时为 None，调用方须显式处理而非回落常量）
RULESET_VERSION = _MANIFEST.get("ruleset_version")
#: 规则包基准日（同上）
BASIS_DATE = _MANIFEST.get("basis_date")


def ruleset_version():
    """当前规则包版本（报告与 CLI 双出口取同一派生值）。"""
    return RULESET_VERSION


def basis_date():
    """当前规则包基准日。"""
    return BASIS_DATE
