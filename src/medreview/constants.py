"""结构性常量（**非政策字面量**）。

本模块只放"工程结构"类常量：结论状态、规则 kind、品类枚举、退出码、severity。
**政策词面/条款号/阈值一律不在此处**——它们只存在于冻结规则包
（``references/ruleset.json``），由引擎运行时实算（既定口径 K1/K9）。

判别口诀：这个常量换个国家/换部法规还成立吗？成立 = 结构性，可留源码；
只有本领域原文才有 = 政策字面量，必须进规则包。
"""

from __future__ import annotations

# ---- 退出码契约（K2，锁进 CLI 端到端测试） ----
EXIT_OK = 0            # 完成且未命中（OK / NOT_ASSESSED）
EXIT_FINDING = 1       # 检出命中（BLOCK / WARN）——"查出了问题"的既定语义，非故障
EXIT_INPUT = 2         # 输入/用法错误
EXIT_RULESET = 3       # 规则包不可用

# ---- 结论状态（K3，报告四态，NOT_ASSESSED 独立呈现不与 OK 合并） ----
GRADE_BLOCK = "BLOCK"
GRADE_WARN = "WARN"
GRADE_OK = "OK"
GRADE_NOT_ASSESSED = "NOT_ASSESSED"

GRADES = (GRADE_BLOCK, GRADE_WARN, GRADE_OK, GRADE_NOT_ASSESSED)
# 报告分列顺序：先坏后好，未评估垫底（显式可见）
GRADE_ORDER = (GRADE_BLOCK, GRADE_WARN, GRADE_OK, GRADE_NOT_ASSESSED)
# 会改变退出码为 EXIT_FINDING 的状态
GRADES_WITH_FINDING = (GRADE_BLOCK, GRADE_WARN)

# ---- 规则级判定状态（与结论状态是两个层次，见 plan/03 §1.2） ----
RULE_COMPLIANT = "compliant"        # 规则适用且未命中
RULE_NONCOMPLIANT = "noncompliant"  # 规则适用且命中（无条件义务缺失也归此）
RULE_SKIPPED = "skipped"            # 不适用——**只在原文自带主体/情形限制时使用**
RULE_INPUT_REQUIRED = "input_required"  # 判定需外部材料，本次未提供（绝不静默判 compliant）

RULE_STATES = (RULE_COMPLIANT, RULE_NONCOMPLIANT, RULE_SKIPPED, RULE_INPUT_REQUIRED)

# ---- 规则 kind（判定分派表的键；结构层断言要求与实现一一对应且互不相同） ----
KIND_PROHIBITED_TERM = "prohibited_term"
KIND_PROHIBITED_PATTERN = "prohibited_pattern"
KIND_MANDATORY_DISCLOSURE = "mandatory_disclosure"
KIND_WHITELIST_SCOPE = "whitelist_scope"
KIND_VARIANT_PUBLISH = "variant_publish"
KIND_INPUT_REQUIRED = "input_required"
# 审查证明情形（三态可判定：明确未附 → noncompliant；未提供 → input_required；已附 → compliant）
KIND_REVIEW_PROOF = "review_proof"

KINDS = (
    KIND_PROHIBITED_TERM,
    KIND_PROHIBITED_PATTERN,
    KIND_MANDATORY_DISCLOSURE,
    KIND_WHITELIST_SCOPE,
    KIND_VARIANT_PUBLISH,
    KIND_INPUT_REQUIRED,
    KIND_REVIEW_PROOF,
)

# ---- severity（规则包字段 → 分级映射的唯一输入） ----
SEVERITY_BLOCK = "block"
SEVERITY_WARN = "warn"
SEVERITIES = (SEVERITY_BLOCK, SEVERITY_WARN)

# ---- 品类枚举（品类判定器的输出域；关键词表在规则包里） ----
CATEGORY_MEDICAL = "medical"
CATEGORY_DRUG = "drug"
CATEGORY_DEVICE = "device"
CATEGORY_HEALTH_FOOD = "health_food"
CATEGORY_FSMP = "fsmp"
CATEGORY_NON_MEDICAL = "non_medical"

CATEGORIES = (
    CATEGORY_MEDICAL,
    CATEGORY_DRUG,
    CATEGORY_DEVICE,
    CATEGORY_HEALTH_FOOD,
    CATEGORY_FSMP,
)
# 非涉医内容不是"品类规则的作用对象"，而是"无适用规则"的标记
ALL_CATEGORIES = CATEGORIES + (CATEGORY_NON_MEDICAL,)

# ---- 门控作用域（K，见 plan/04 §4.3；分作用域防无关 pending 阻断判定路径） ----
SCOPE_CHECK = "check"
SCOPE_BENCH = "bench"
SCOPE_RULES = "rules"
SCOPES = (SCOPE_CHECK, SCOPE_BENCH, SCOPE_RULES)

# ---- 审查情形（原文自带的情形限制；默认发布前自查） ----
SCENARIO_PREPUBLICATION = "prepublication"
SCENARIO_PUBLISHED = "published"
SCENARIOS = (SCENARIO_PREPUBLICATION, SCENARIO_PUBLISHED)

# ---- 机器契约字段（SKILL.md 契约块 ↔ 代码 ↔ 实际输出的三方对齐源） ----
CONTRACT_FIELDS_ITEM = ("id", "text", "channel", "subject", "hint", "proof", "scenario")
CONTRACT_FIELDS_TOP = ("categories", "grade", "findings", "applied_rule_count",
                       "total_rule_count", "not_enabled", "advisories",
                       "input_required", "ruleset_version", "rule_sources")
CONTRACT_FIELDS_FINDING = ("rule_id", "clause_anchor", "quote", "evidence",
                           "severity", "kind", "notes")
CONTRACT_FIELDS_ALL = CONTRACT_FIELDS_ITEM + CONTRACT_FIELDS_TOP + CONTRACT_FIELDS_FINDING

# ---- status 值 ----
STATUS_VERIFIED = "verified"
STATUS_PENDING = "pending"
