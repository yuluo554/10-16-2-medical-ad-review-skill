"""品类判定器（模块 2）。

判定路径规则表驱动：**关键词表与判定规则只存在于冻结规则包**，源码零词面
（既定口径 K9）。多品类并列时**全部保留**，不做"二选一"猜测——各品类规则
分别适用，报告显式列出本文案同时构成的全部品类。

命中多条品类时按固定优先级排序输出（medical > drug > device > health_food >
fsmp），排序只影响呈现顺序，不影响适用集合。
"""

from __future__ import annotations

from . import constants

# 呈现优先级（结构常量，非政策词面）
_CATEGORY_RANK = {
    constants.CATEGORY_MEDICAL: 0,
    constants.CATEGORY_DRUG: 1,
    constants.CATEGORY_DEVICE: 2,
    constants.CATEGORY_HEALTH_FOOD: 3,
    constants.CATEGORY_FSMP: 4,
}


class CategoryResult(object):
    """品类判定结果：品类集合 + 判定依据（命中的规则行 + 条款锚点）。"""

    __slots__ = ("categories", "evidence", "variant_suspect")

    def __init__(self, categories, evidence, variant_suspect=False):
        self.categories = tuple(categories)
        self.evidence = list(evidence)
        self.variant_suspect = variant_suspect

    def to_dict(self):
        return {
            "categories": list(self.categories),
            "evidence": list(self.evidence),
            "variant_suspect": self.variant_suspect,
        }


def categorize(item, category_rules, variant_rules=None):
    """按规则包的品类信号词表判定品类。

    ``category_rules``：``[{"category": ..., "signal_id": ..., "terms": [...],
    "anchor": ..., "quote": ...}]``——词表来自冻结规则包，**不在此处硬编码**。

    判定为"非涉医内容"（无任何品类信号）时返回空 categories —— 这是
    ``NOT_ASSESSED`` 的触发条件（"没查出问题"与"没检查过"必须可区分）。
    """
    text = item.text
    evidence = []
    hits = set()

    for entry in category_rules or ():
        terms = entry.get("terms") or ()
        matched = [term for term in terms if term and term in text]
        if matched:
            hits.add(entry["category"])
            evidence.append({
                "category": entry["category"],
                "signal_id": entry.get("signal_id", ""),
                "anchor": entry.get("anchor", ""),
                "quote": entry.get("quote", ""),
                "matched_terms": matched,
            })

    ordered = sorted(hits, key=lambda c: (_CATEGORY_RANK.get(c, 99), c))

    variant_suspect = False
    for entry in variant_rules or ():
        # 变相发布：知识形态 + 商品/服务信息共现（**不直接定品类**）
        if not entry:
            continue
        knowledge_terms = [t for t in (entry.get("knowledge_terms") or ()) if t and t in text]
        commerce_terms = [t for t in (entry.get("commerce_terms") or ()) if t and t in text]
        if knowledge_terms and commerce_terms:
            variant_suspect = True
            evidence.append({
                "category": None,
                "signal_id": entry.get("signal_id", ""),
                "anchor": entry.get("anchor", ""),
                "quote": entry.get("quote", ""),
                "matched_terms": knowledge_terms + commerce_terms,
                "note": "变相发布疑似（知识形态 + 商品/服务信息共现），不直接定品类",
            })
            break

    return CategoryResult(ordered, evidence, variant_suspect)


def applicable_categories(result):
    """报告用：品类集合；空集合 = 非涉医内容（→ NOT_ASSESSED）。"""
    return tuple(result.categories)
