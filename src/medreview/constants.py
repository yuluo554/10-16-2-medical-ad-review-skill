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

# ---- 否定语境抑制（**语言层**构造，非本领域政策词面） ----
# 判别：这些是**中文否定前缀**，换任何一部中文法规都成立——属"结构性"而非
# "本领域政策词面"，故留源码而不进规则包（K9 的判别口诀同源）。
#
# 为什么必须有它：本领域的法条**强制要求**写免责语，而免责语里恰好含被禁止的
# 词面。实测反例（M1）：一段"否定 + 功效承诺"形态的合规免责语会被功效类规则
# 判命中——把**合规的免责声明**报成违法，是比漏报更坏的误报（用户按提示改文案
# 反而改错）。故命中须先排除"处于否定辖域内"的出现位置。
NEGATION_MARKERS = ("不能", "不得", "不可", "无法", "不保证", "不承诺",
                    "不用于", "并非", "不予", "严禁", "不构成", "未有",
                    "不做", "不宣传", "不宣称", "无", "不", "没", "非")
# 否定辖域**不跨句读**（否定词的作用范围止于句读）——按这些字符切分定位辖域。
# 判据是"**片段内存在真否定词**"：否定词与命中项同处一个句读段即算被否定
# （「否定词 + 动词 + 被禁词面」的免责语形态，中间隔着动词，故不能只判紧贴）；
# 但「不」开头的**非否定词**（见下表）要排除——它们修饰别的主语，不是否定谓语。
NEGATION_MARKERS = ("不能", "不得", "不可", "无法", "不保证", "不承诺",
                    "不用于", "并非", "不予", "严禁", "不构成", "未有",
                    "不做", "不宣传", "不宣称", "无", "不", "没", "非")
# 「不」开头但**不是否定**的常见词——它们修饰别的主语/名词，不否定谓语。
# 没有这张例外表，裸「不」会把"否定词修饰主语"的**肯定**宣称误抑制（漏报）。
NON_NEGATION_WORDS = ("不少", "不断", "不仅", "不但", "不只", "不良", "不妨",
                      "不过", "不论", "不管", "不如", "不久", "不再", "不同",
                      "不够", "不足", "不会", "不需", "不限", "不定", "不便")
SEGMENT_DELIMITERS = "，。；！？、,.;!?\n\r"

# ---- 机器契约字段（SKILL.md 契约块 ↔ 代码 ↔ 实际输出的三方对齐源） ----
CONTRACT_FIELDS_ITEM = ("id", "text", "channel", "subject", "hint", "proof",
                        "scenario", "proof_file")
CONTRACT_FIELDS_TOP = ("categories", "grade", "findings", "applied_rule_count",
                       "total_rule_count", "not_enabled", "advisories",
                       "input_required", "ruleset_version", "rule_sources")
CONTRACT_FIELDS_FINDING = ("rule_id", "clause_anchor", "quote", "evidence",
                           "severity", "kind", "notes")
CONTRACT_FIELDS_ALL = CONTRACT_FIELDS_ITEM + CONTRACT_FIELDS_TOP + CONTRACT_FIELDS_FINDING

# ---- status 值 ----
STATUS_VERIFIED = "verified"
STATUS_PENDING = "pending"
