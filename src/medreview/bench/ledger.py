"""冻结台账校验（**与生成器 ``--check`` 共用同一判定**，不实现第二份）。

三件齐备的第三件：用户敲的 ``medreview bench`` 命令**真读冻结件**——
``runner._load_frozen_cases`` 先跑本模块的 ``check_frozen_ledger`` 再加载。
"""

from __future__ import annotations

import hashlib
import json
import os
import re

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


def load_fake_org_whitelist(path=None):
    """读取**仓库内**的假机构名白名单文件（每行一个，``#`` 注释与空行忽略）。

    白名单是**手编**资产（人工判断类）；样例机构名必须在名单内，
    出现名单外的机构名形态即红（题面 §四.1 的硬要求）。

    **注意**：本函数定位的是仓库开发态的 ``data/``，安装态取不到（该目录不随包）。
    运行时的白名单取真值库内嵌字段（见 ``check_fake_org_whitelist``）；
    本文件是手编主本，与内嵌名单的一致性由测试守门（漂移即红）。
    """
    if path is None:
        path = os.path.join(ROOT, "data", "fake_org_whitelist.txt")
    if not os.path.isfile(path):
        return []
    names = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            names.append(line)
    return names


# 机构名形态的识别模式（结构性特征，非具体机构名）
ORG_PATTERNS = (
    r"[一-鿿]{2,10}(?:门诊部|医院|诊所|卫生院|医疗美容机构)",
)


def scan_org_names(text, patterns=None):
    """扫出一段文本里的"机构名形态"片段（用于白名单校验）。"""
    found = []
    for pattern in (patterns or ORG_PATTERNS):
        for match in re.finditer(pattern, text):
            found.append(match.group(0))
    return found


def check_fake_org_whitelist(payload, whitelist=None):
    """校验全部样例的机构名都在白名单内。

    返回问题列表（空 = 合规）。这是"合成数据纪律"的机器可验形态：
    只测"该命中的用例"，白名单纪律写错永远不会红——故必须做成断言。

    白名单来源优先级（**安装态与源码态必须同源**）：
      1. 显式入参 ``whitelist``（测试注入用）；
      2. 真值库内嵌的 ``fake_org_whitelist``——随 ``cases.json`` 进 wheel，
         这是安装态唯一可取到的来源；
      3. 仓库开发态文件 ``data/fake_org_whitelist.txt``（仅当 payload 无内嵌字段，
         如 ``samples/`` 的临时 payload）。
    空名单一律报错（不是静默放行）。
    """
    if whitelist is not None:
        names = list(whitelist)
    elif payload.get("fake_org_whitelist") is not None:
        # 内嵌字段**存在即为准**：空列表也必须报错（不得回落仓库文件把口径放宽）
        names = list(payload["fake_org_whitelist"])
    else:
        names = load_fake_org_whitelist()
    if not names:
        return ["假机构名白名单为空（纪律未落地：无法校验）"]
    problems = []
    for case in payload.get("cases", []):
        for found in scan_org_names(case.get("input", "")):
            if not any(name.startswith(found[:4]) or found in name for name in names):
                problems.append("用例 %s 含白名单外的机构名形态：%s" % (case["id"], found))
    return problems


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
