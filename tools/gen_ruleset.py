"""规则包生成器（M1 核心交付物，**开发期工具，不在测试/CI 路径上**）。

管线：官方快照（已入仓）→ 条文块 → 规则包 + manifest + 台账。

四条硬纪律：

1. **禁手抄**：条文块由脚本从入仓快照切分，每处抽取值断言**原文逐字包含**。
2. **条号只认定义位**：官方文本里条号一律起于行首，交叉引用不参与切分。
3. **禁手改产物**：``references/*.json`` 与 ``data/ledger.csv`` 都是生成物；
   改需求走本脚本整目录重生成，``--check`` 断言"再生成位级一致"。
4. **词表溯源分级**：规则的匹配词表带 ``terms_basis``：
   ``literal`` = 词面**逐字出现在该条文原文中**（生成器硬断言）；
   ``interpretive`` = 法定情形的解释性词面（**不逐字在原文中**，属解释层，
   须人工复核后定稿）。两级都在 manifest 里计数登记，**不把解释层冒充成原文**。

用法：
    py -3.12 -X utf8 tools/gen_ruleset.py            # 生成/覆盖
    py -3.12 -X utf8 tools/gen_ruleset.py --check    # 位级一致守门（不写盘）
    py -3.12 -X utf8 tools/gen_ruleset.py --update-ledger
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "knowledge", "raw")
REF_DIR = os.path.join(ROOT, "src", "medreview", "references")
LEDGER_PATH = os.path.join(ROOT, "data", "ledger.csv")

BASIS_DATE = "2026-10-15"

SOURCES = [
    {
        "id": "advertising_law",
        "title": "《中华人民共和国广告法》",
        "url": ("https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/"
                "art_5474cf75173c45d6a0379730fb4e8d97.html"),
        "snapshot": "advertising_law.txt",
    },
    {
        "id": "internet_ad_measures",
        "title": "《互联网广告管理办法》",
        "url": ("https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/"
                "art_d93a579afd45413e8576e4623fab348f.html"),
        "snapshot": "internet_ad_measures.txt",
    },
    {
        "id": "medical_ad_measures",
        "title": "《医疗广告管理办法》",
        "url": ("https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ggjgs/art/2023/"
                "art_6584dc1c94c2408db7c73f0b5e3d225a.html"),
        "snapshot": "medical_ad_measures.txt",
    },
]

CN_NUM = "一二三四五六七八九十"
CLAUSE_RE = re.compile(r"^第([" + CN_NUM + r"]+)条$")
ITEM_RE = re.compile(r"^（([" + CN_NUM + r"]+)）(.*)$")


def read_snapshot(name):
    path = os.path.join(RAW_DIR, name)
    if not os.path.isfile(path):
        raise SystemExit("快照不存在（先跑 tools/make_snapshots.py）: %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def split_clauses(text):
    """按**行首条号**切分条文块（交叉引用不参与切分）。

    返回 ``[{"clause": "7", "numeral": "七", "text": "..."}]``——
    ``text`` 含条号行本身，便于逐字包含断言。
    """
    lines = text.split("\n")
    blocks = []
    current = None
    for line in lines:
        stripped = line.strip()
        match = CLAUSE_RE.match(stripped)
        if match:
            if current is not None:
                blocks.append(current)
            current = {"clause": _cn_to_int(match.group(1)),
                       "numeral": match.group(1), "lines": [stripped]}
            continue
        if current is not None:
            current["lines"].append(stripped)
    if current is not None:
        blocks.append(current)

    out = []
    for block in blocks:
        body = [line for line in block["lines"] if line]
        out.append({
            "clause": str(block["clause"]),
            "numeral": block["numeral"],
            "text": "\n".join(body),
        })
    return out


def _cn_to_int(numeral):
    """中文数字 → 整数（本项目条号最大 74，支持十/百位组合）。"""
    if numeral == "十":
        return 10
    total = 0
    section = 0
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    for ch in numeral:
        if ch in digits:
            section = digits[ch]
        elif ch == "十":
            section = (section or 1) * 10
            total += section
            section = 0
    return total + section


def clause_items(clause_text):
    """提取条内中文序号项。

    返回 ``{"1": {"text": "（一）涉及…的；", "numeral": "一"}}``——``numeral``
    保留原文字形，用于锚点（``第（三）项``）而非阿拉伯数字。
    """
    items = {}
    for line in clause_text.split("\n"):
        match = ITEM_RE.match(line.strip())
        if match:
            items[str(_cn_to_int(match.group(1)))] = {
                "text": line.strip(),
                "numeral": match.group(1),
            }
    return items


def find_line(clause_text, contains):
    """取条文中**包含指定子串**的那一行（条款级 quote 的定位器）。

    用途：同一「条」内含多个独立义务（如《广告法》§16 的三款），条款级规则
    必须锚到**承载该义务的那一句**，而不是笼统取首句——否则引文与义务对不上。
    """
    for line in clause_text.split("\n"):
        if contains and contains in line:
            return line.strip()
    return None


# --------------------------------------------------------------------------
# 规则定义（**转写源**：引文一律从快照实算，不在此处手写）
#
# 每条规则给出 (source, clause, item)，quote 由生成器从快照提取——
# 杜绝"手抄引文"引入不可复现的转写漂移。
# --------------------------------------------------------------------------
RULE_DEFS = [
    # ---- 《医疗广告管理办法》§7（8 项，其中第（八）项为兜底，不建规则） ----
    {
        "id": "MAM-7-1", "source": "medical_ad_measures", "clause": "7", "item": "1",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["医疗技术", "诊疗方法", "疾病名称", "药物"],
        "pattern_id": "involves_tech_disease_drug",
    },
    {
        "id": "MAM-7-2", "source": "medical_ad_measures", "clause": "7", "item": "2",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["medical"], "terms_basis": "interpretive",
        "terms": ["保证治愈", "彻底治愈", "根治", "包治", "无效退款", "永不复发"],
        "pattern_id": "guaranteed_cure",
    },
    {
        "id": "MAM-7-3", "source": "medical_ad_measures", "clause": "7", "item": "3",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["治愈率", "有效率", "诊疗效果"],
        "pattern_id": "cure_rate_claim",
    },
    {
        "id": "MAM-7-4", "source": "medical_ad_measures", "clause": "7", "item": "4",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["淫秽", "迷信", "荒诞"],
        "pattern_id": "obscene_superstitious",
    },
    {
        "id": "MAM-7-5", "source": "medical_ad_measures", "clause": "7", "item": "5",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["贬低"],
        "pattern_id": "disparage_others",
    },
    {
        "id": "MAM-7-6", "source": "medical_ad_measures", "clause": "7", "item": "6",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical"], "terms_basis": "interpretive",
        "terms": ["患者", "卫生技术人员", "医学教育科研机构", "社会社团"],
        "pattern_id": "endorsement_by_patient_or_org",
    },
    {
        "id": "MAM-7-7", "source": "medical_ad_measures", "clause": "7", "item": "7",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["解放军", "武警部队"],
        "pattern_id": "military_name",
    },
    # ---- 《医疗广告管理办法》§6 白名单（**实测 8 项**，见 plan/PRECHECK-M0 E-1） ----
    {
        "id": "MAM-6-W", "source": "medical_ad_measures", "clause": "6", "item": None,
        "kind": "whitelist_scope", "severity": "warn",
        "categories": ["medical"], "terms_basis": "interpretive",
        "terms": ["疗效", "无痛", "专家坐诊", "设备先进", "技术领先", "成功率"],
        "pattern_id": "beyond_whitelist",
    },
    {
        "id": "MAM-6-LIC", "source": "medical_ad_measures", "clause": "6", "item": None,
        "kind": "input_required", "severity": "block",
        "categories": ["medical"], "terms_basis": "literal",
        "terms": ["执业许可证"], "quote_contains": "执业许可证",
        "required_input": "《医疗机构执业许可证》或其副本（核对第（一）至（六）项内容一致性）",
    },
    # ---- 《广告法》§16（第（五）项为兜底，不建规则） ----
    {
        "id": "AL-16-1", "source": "advertising_law", "clause": "16", "item": "1",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["medical", "drug", "device"], "terms_basis": "interpretive",
        "terms": ["包治", "根治", "治愈", "安全无副作用", "绝对安全", "保证有效", "100%有效"],
        "pattern_id": "efficacy_safety_assertion",
    },
    {
        "id": "AL-16-2", "source": "advertising_law", "clause": "16", "item": "2",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["medical", "drug", "device"], "terms_basis": "literal",
        "terms": ["治愈率", "有效率"],
        "pattern_id": "cure_or_response_rate",
    },
    {
        "id": "AL-16-3", "source": "advertising_law", "clause": "16", "item": "3",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["medical", "drug", "device"], "terms_basis": "interpretive",
        "terms": ["优于", "好于", "第一", "最先进", "其他医院"],
        "pattern_id": "comparison_with_others",
    },
    {
        "id": "AL-16-4", "source": "advertising_law", "clause": "16", "item": "4",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["medical", "drug", "device"], "terms_basis": "interpretive",
        "terms": ["代言人", "形象大使", "明星推荐", "倾情推荐"],
        "pattern_id": "ad_endorser",
    },
    {
        "id": "AL-16-D1", "source": "advertising_law", "clause": "16", "item": None,
        "kind": "input_required", "severity": "block",
        "categories": ["drug"], "terms_basis": "literal",
        "terms": ["说明书"], "quote_contains": "说明书",
        "required_input": "国务院药品监督管理部门批准的药品说明书（核对内容一致性）",
    },
    {
        "id": "AL-16-D2", "source": "advertising_law", "clause": "16", "item": None,
        "kind": "mandatory_disclosure", "severity": "block",
        "categories": ["drug"],
        "terms_basis": "literal", "quote_contains": "禁忌、不良反应",
        "require_all_of": [["禁忌", "不良反应"]],
        "pattern_id": "drug_must_mark_contraindication",
    },
    # ---- 《广告法》§18（第（六）项为兜底，不建规则） ----
    {
        "id": "AL-18-1", "source": "advertising_law", "clause": "18", "item": "1",
        "kind": "prohibited_pattern", "severity": "block",
        "categories": ["health_food"], "terms_basis": "interpretive",
        "terms": ["包治", "根治", "绝对安全", "保证有效", "无副作用"],
        "pattern_id": "health_food_efficacy_assertion",
    },
    {
        "id": "AL-18-2", "source": "advertising_law", "clause": "18", "item": "2",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["health_food"], "terms_basis": "interpretive",
        "terms": ["预防", "治疗", "抗肿瘤", "降血压", "降血糖"],
        "pattern_id": "disease_prevention_treatment",
    },
    {
        "id": "AL-18-3", "source": "advertising_law", "clause": "18", "item": "3",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["health_food"], "terms_basis": "interpretive",
        "terms": ["必需", "必不可少", "人人必备"],
        "pattern_id": "claim_indispensable",
    },
    {
        "id": "AL-18-4", "source": "advertising_law", "clause": "18", "item": "4",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["health_food"], "terms_basis": "interpretive",
        "terms": ["优于", "好于", "其他保健食品"],
        "pattern_id": "health_food_comparison",
    },
    {
        "id": "AL-18-5", "source": "advertising_law", "clause": "18", "item": "5",
        "kind": "prohibited_term", "severity": "block",
        "categories": ["health_food"], "terms_basis": "interpretive",
        "terms": ["代言人", "形象大使", "明星推荐"],
        "pattern_id": "health_food_endorser",
    },
    {
        "id": "AL-18-D1", "source": "advertising_law", "clause": "18", "item": None,
        "kind": "mandatory_disclosure", "severity": "block",
        "categories": ["health_food"], "terms_basis": "literal",
        "quote_contains": "不能代替药物",
        "require_all_of": [["不能代替药物"]],
        "pattern_id": "health_food_must_mark_not_drug",
    },
    # ---- 《互联网广告管理办法》§7 / §8 ----
    {
        "id": "IAM-7-1", "source": "internet_ad_measures", "clause": "7", "item": None,
        "kind": "review_proof", "severity": "block",
        "categories": ["medical", "drug", "device", "health_food", "fsmp"],
        "terms_basis": "literal", "terms": ["审查"], "quote_contains": "未经审查，不得发布",
        "required_input": "广告审查机关出具的广告审查证明（未审查不得发布）",
    },
    {
        "id": "IAM-7-2", "source": "internet_ad_measures", "clause": "7", "item": None,
        "kind": "input_required", "severity": "block", "scenario": ["published"],
        "categories": ["medical", "drug", "device", "health_food", "fsmp"],
        "terms_basis": "literal", "terms": ["剪辑", "拼接", "修改"],
        "quote_contains": "剪辑、拼接、修改",
        "required_input": "审查通过的广告内容原文（核对是否被剪辑、拼接、修改）",
    },
    {
        "id": "IAM-8-1", "source": "internet_ad_measures", "clause": "8", "item": None,
        "kind": "variant_publish", "severity": "block",
        "categories": ["medical", "drug", "device", "health_food", "fsmp"],
        "terms_basis": "interpretive",
        "knowledge_terms": ["养生知识", "健康知识", "科普"],
        "commerce_terms": ["门诊部", "医院", "诊所", "购买", "预约"],
        "quote_contains": "变相发布",
        "pattern_id": "variant_publish_health_knowledge",
    },
    {
        "id": "IAM-8-2", "source": "internet_ad_measures", "clause": "8", "item": None,
        "kind": "variant_publish", "severity": "block",
        "categories": ["medical", "drug", "device", "health_food", "fsmp"],
        "terms_basis": "interpretive",
        "knowledge_terms": ["养生知识", "健康知识", "科普"],
        "commerce_terms": ["联系方式", "购物链接", "扫码", "加微信", "电话"],
        "quote_contains": "购物链接",
        "pattern_id": "variant_publish_commerce_info",
    },
]

# 兜底条款：**显式不建规则**（无可机读判定要素），但必须在未启用清单里可见（D9）
EXCLUDED_CLAUSES = [
    {"source": "medical_ad_measures", "clause": "7", "item": "8",
     "reason": "兜底条款「法律、行政法规规定禁止的其他情形」，无可机读判定要素，不建规则"},
    {"source": "advertising_law", "clause": "16", "item": "5",
     "reason": "兜底条款「法律、行政法规规定禁止的其他内容」，无可机读判定要素，不建规则"},
    {"source": "advertising_law", "clause": "18", "item": "6",
     "reason": "兜底条款「法律、行政法规规定禁止的其他内容」，无可机读判定要素，不建规则"},
]

# 品类判定词表（**只存在于规则包**，引擎源码零词面）
CATEGORY_RULES = [
    {"category": "medical", "signal_id": "cat_medical",
     "anchor": "《医疗广告管理办法》§2",
     "quote": "本办法所称医疗广告，是指利用各种媒介或者形式直接或间接介绍医疗机构或医疗服务的广告。",
     "terms": ["门诊部", "医院", "诊所", "医疗美容", "医美", "整形", "诊疗", "科室", "挂号"]},
    {"category": "drug", "signal_id": "cat_drug",
     "anchor": "《广告法》§16",
     "quote": "医疗、药品、医疗器械广告不得含有下列内容：",
     "terms": ["药品", "片剂", "胶囊", "口服液", "国药准字", "说明书", "适应症"]},
    {"category": "device", "signal_id": "cat_device",
     "anchor": "《广告法》§16",
     "quote": "医疗、药品、医疗器械广告不得含有下列内容：",
     "terms": ["医疗器械", "器械", "注册证", "械字号", "理疗仪", "血压计"]},
    {"category": "health_food", "signal_id": "cat_health_food",
     "anchor": "《广告法》§18",
     "quote": "保健食品广告不得含有下列内容：",
     "terms": ["保健食品", "保健品", "蓝帽子", "保健功能", "膳食补充"]},
    {"category": "fsmp", "signal_id": "cat_fsmp",
     "anchor": "《互联网广告管理办法》§7",
     "quote": "发布医疗、药品、医疗器械、农药、兽药、保健食品、特殊医学用途配方食品广告等法律、行政法规规定应当进行审查的广告",
     "terms": ["特殊医学用途配方食品", "特医食品"]},
]

VARIANT_RULES = [
    {"signal_id": "variant_health_knowledge",
     "anchor": "《互联网广告管理办法》§8",
     "quote": "禁止以介绍健康、养生知识等形式，变相发布医疗、药品、医疗器械、保健食品、特殊医学用途配方食品广告。",
     "knowledge_terms": ["养生", "健康知识", "科普", "调理", "保养"],
     "commerce_terms": ["门诊部", "医院", "诊所", "购买", "预约", "联系方式", "购物链接", "扫码", "加微信"]},
]


# --------------------------------------------------------------------------
def build():
    """生成全部产物（内存态，返回 dict path → text）。"""
    clauses_payload = {"basis_date": BASIS_DATE, "sources": [], "clauses": []}
    snapshot_text = {}

    for source in SOURCES:
        text = read_snapshot(source["snapshot"])
        snapshot_text[source["id"]] = text
        blocks = split_clauses(text)
        clauses_payload["sources"].append({
            "id": source["id"], "title": source["title"],
            "url": source["url"], "snapshot": source["snapshot"],
            "clause_count": len(blocks),
        })
        for block in blocks:
            clauses_payload["clauses"].append({
                "source": source["id"], "clause": block["clause"],
                "numeral": block["numeral"], "text": block["text"],
            })

    clause_index = {(c["source"], c["clause"]): c["text"] for c in clauses_payload["clauses"]}
    source_title = {s["id"]: s["title"] for s in SOURCES}
    source_url = {s["id"]: s["url"] for s in SOURCES}

    rules = []
    for definition in RULE_DEFS:
        key = (definition["source"], definition["clause"])
        clause_text = clause_index.get(key)
        if clause_text is None:
            raise SystemExit("规则 %s 的条款不在快照中: %s §%s"
                             % (definition["id"], definition["source"], definition["clause"]))

        if definition.get("item"):
            items = clause_items(clause_text)
            entry = items.get(definition["item"])
            if entry is None:
                raise SystemExit("规则 %s 的项不在该条中: §%s 第（%s）项"
                                 % (definition["id"], definition["clause"], definition["item"]))
            quote = entry["text"]
            item_numeral = entry["numeral"]
        else:
            item_numeral = None
            contains = definition.get("quote_contains")
            if contains:
                quote = find_line(clause_text, contains)
                if quote is None:
                    raise SystemExit("规则 %s 的 quote_contains「%s」在 §%s 中定位不到"
                                     % (definition["id"], contains, definition["clause"]))
            else:
                quote = _first_sentence(clause_text)

        # 逐字包含断言（禁手抄的落地）
        if quote not in clause_text:
            raise SystemExit("规则 %s 的 quote 未逐字出现在条文快照中" % definition["id"])

        if definition.get("terms_basis") == "literal":
            literal_terms = list(definition.get("terms") or [])
            for group in definition.get("require_all_of") or []:
                literal_terms.extend(group)
            literal_terms.extend(definition.get("knowledge_terms") or [])
            literal_terms.extend(definition.get("commerce_terms") or [])
            for term in literal_terms:
                if term not in clause_text:
                    raise SystemExit("规则 %s 的 literal 词面「%s」未逐字出现在 §%s 原文中"
                                     % (definition["id"], term, definition["clause"]))

        anchor = "%s§%s%s" % (
            source_title[definition["source"]],
            definition["clause"],
            ("第（%s）项" % item_numeral) if item_numeral else "",
        )

        rule = {
            "id": definition["id"],
            "source": definition["source"],
            "source_title": source_title[definition["source"]],
            "clause": definition["clause"],
            "item": definition.get("item"),
            "anchor": anchor,
            "quote": quote,
            "quote_status": "verified",
            "anchor_status": "verified",
            "kind": definition["kind"],
            "severity": definition["severity"],
            "applies_if": _applies_if(definition),
            "terms_basis": definition.get("terms_basis", "literal"),
            "official_url": source_url[definition["source"]],
            "basis_date": BASIS_DATE,
            "notes": "",
        }
        if definition.get("pattern_id"):
            rule["pattern_id"] = definition["pattern_id"]

        match = {}
        if definition["kind"] == "variant_publish":
            match = {"knowledge_terms": definition.get("knowledge_terms") or [],
                     "commerce_terms": definition.get("commerce_terms") or []}
        elif definition["kind"] == "mandatory_disclosure":
            match = {"require_all_of": definition.get("require_all_of") or []}
        elif definition["kind"] in ("input_required", "review_proof"):
            match = {"required_input": definition.get("required_input", "")}
        else:
            match = {"any_of": definition.get("terms") or []}
        rule["match"] = match
        rules.append(rule)

    rules.sort(key=lambda r: (r["source"], int(r["clause"]),
                              int(r["item"]) if r.get("item") else 0))

    excluded = []
    for entry in EXCLUDED_CLAUSES:
        clause_text = clause_index.get((entry["source"], entry["clause"]), "")
        items = clause_items(clause_text)
        excluded.append({
            "rule_id": "%s-%s-%s" % (entry["source"], entry["clause"], entry["item"]),
            "source": entry["source"],
            "clause": entry["clause"],
            "item": entry["item"],
            "quote": items.get(entry["item"], ""),
            "reason": entry["reason"],
            "code": "catch_all_clause",
        })

    literal_count = sum(1 for r in rules if r["terms_basis"] == "literal")
    interpretive_count = sum(1 for r in rules if r["terms_basis"] == "interpretive")

    content_for_version = json.dumps(
        {"rules": [{k: v for k, v in r.items() if k not in ("official_url", "basis_date")}
                   for r in rules], "excluded": excluded},
        sort_keys=True, ensure_ascii=False)
    version = "ruleset-" + hashlib.sha256(content_for_version.encode("utf-8")).hexdigest()[:10]

    ruleset_payload = {
        "ruleset_version": version,
        "basis_date": BASIS_DATE,
        "generated_by": "tools/gen_ruleset.py",
        "rules": rules,
        "excluded_clauses": excluded,
        "category_rules": CATEGORY_RULES,
        "variant_rules": VARIANT_RULES,
    }

    manifest = {
        "ruleset_version": version,
        "basis_date": BASIS_DATE,
        "total_rule_count": len(rules) + len(excluded),
        "enabled_rule_count": len(rules),
        "excluded_clause_count": len(excluded),
        "terms_basis_counts": {"literal": literal_count, "interpretive": interpretive_count},
        "sources": [{"id": s["id"], "title": s["title"], "url": s["url"],
                     "snapshot": s["snapshot"], "basis_date": BASIS_DATE} for s in SOURCES],
        "benchmark_thresholds": {
            "b1_min_accuracy": 1.0,
            "b2_false_block_max": 0,
            "b3_reverse_pass_min": 1.0,
            "b4_min_coverage": 1.0,
        },
        "coverage_note": "抽样覆盖、非穷举：真值库按规则形态采样，见 benchmark/manifest 登记",
    }

    ledger_rows = ["asset_id,path,sha256,source_url,captured_date,notes"]
    for source in SOURCES:
        data = open(os.path.join(RAW_DIR, source["snapshot"]), "rb").read()
        digest = hashlib.sha256(data).hexdigest()
        ledger_rows.append("%s,data/knowledge/raw/%s,%s,%s,%s,%s"
                           % (source["id"], source["snapshot"], digest, source["url"],
                              BASIS_DATE, "官方全文快照（-text 冻结）"))

    return {
        "clauses": _dumps(clauses_payload),
        "ruleset": _dumps(ruleset_payload),
        "manifest": _dumps(manifest),
        "ledger": "\n".join(ledger_rows) + "\n",
    }


def _applies_if(definition):
    """适用域（**原文自带的主体/情形限制**，不许写 any）。"""
    applies = {"categories": list(definition["categories"])}
    if definition.get("scenario"):
        applies["scenario"] = list(definition["scenario"])
    return applies


def _first_sentence(clause_text):
    """条款级 quote：取条号行的下一行（该条首句），保证逐字在原文中。"""
    lines = [line for line in clause_text.split("\n") if line]
    if len(lines) >= 2:
        return lines[1]
    return lines[0]


def _dumps(payload):
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    return text.replace("\r\n", "\n").rstrip("\n") + "\n"


TARGETS = {
    "clauses": os.path.join(REF_DIR, "clauses.json"),
    "ruleset": os.path.join(REF_DIR, "ruleset.json"),
    "manifest": os.path.join(REF_DIR, "manifest.json"),
    "ledger": LEDGER_PATH,
}


def write_all(products):
    for key, path in TARGETS.items():
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(products[key])
        sys.stdout.write("written: %s\n" % os.path.relpath(path, ROOT))


def check_frozen(products):
    """位级一致守门：再生成结果与在盘产物逐字节比对。"""
    problems = []
    for key, path in TARGETS.items():
        if not os.path.isfile(path):
            problems.append("missing: %s" % os.path.relpath(path, ROOT))
            continue
        with open(path, "r", encoding="utf-8", newline="") as handle:
            on_disk = handle.read()
        if on_disk != products[key]:
            problems.append("drift: %s" % os.path.relpath(path, ROOT))
    if problems:
        sys.stdout.write("FROZEN_TRUTH_DRIFT\n")
        for item in problems:
            sys.stdout.write("  - %s\n" % item)
        return 1
    sys.stdout.write("FROZEN_TRUTH_OK\n")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    products = build()
    if "--check" in argv:
        return check_frozen(products)
    write_all(products)
    if "--update-ledger" in argv:
        sys.stdout.write("ledger updated\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
