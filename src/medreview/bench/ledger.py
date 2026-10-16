"""冻结台账校验（**与生成器 ``--check`` 共用同一判定**，不实现第二份）。

三件齐备的第三件：用户敲的 ``medreview bench`` 命令**真读冻结件**——
``runner._load_frozen_cases`` 先跑本模块的 ``check_frozen_ledger`` 再加载。
"""

from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


# 摘要计算时排除的字段：摘要自身（否则自我指涉）
DIGEST_EXCLUDED_FIELDS = ("sha256", "ledger_sha256")


def case_digest(case):
    """用例内容摘要（**全项目唯一实现源**，生成器亦调它）。

    判据 = "同一份口径，在几个地方各写了一份？"——两份以上就是漂移源。
    """
    payload = {k: v for k, v in case.items() if k not in DIGEST_EXCLUDED_FIELDS}
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_frozen_ledger(payload):
    """校验真值库与其内置台账逐条一致。

    返回问题列表（空 = 一致）。四类问题：缺件 / 多余件 / 内容不符 / 台账缺条目。
    """
    problems = []
    ledger = payload.get("ledger")
    if not ledger:
        problems.append("真值库缺内置台账（ledger 字段）")
        return problems

    cases = payload.get("cases", [])
    by_id = {c["id"]: c for c in cases}
    recorded = {entry["id"]: entry for entry in ledger.get("entries", [])}

    missing = sorted(set(recorded) - set(by_id))
    extra = sorted(set(by_id) - set(recorded))
    for case_id in missing:
        problems.append("台账登记但真值库缺失的用例: %s" % case_id)
    for case_id in extra:
        problems.append("真值库多出台账未登记的用例: %s" % case_id)

    for case_id in sorted(set(recorded) & set(by_id)):
        digest = case_digest(by_id[case_id])
        if recorded[case_id].get("sha256") != digest:
            problems.append("用例内容与台账不符: %s" % case_id)

    if ledger.get("count") != len(cases):
        problems.append("台账计数 %s != 真值库用例数 %d"
                        % (ledger.get("count"), len(cases)))
    return problems
