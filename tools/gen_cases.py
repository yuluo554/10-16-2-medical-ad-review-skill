"""合成样例 + 真值库生成器（M4 核心，**开发期工具**）。

三条硬纪律：

1. **真值库只存输入与期望**：``expect_keys`` / ``forbid_keys`` 的键名自带结论，
   取值恒为哑值；**绝不写 ``observed``**（那说明观测没在运行时产生）。
2. **生成器带独立朴素 oracle**：期望值由**独立重写**的朴素校验算出，
   不借主实现的结构——主实现的系统性偏差不会自动变成"真值"。
   落库前跑生成守卫（每条用例过 oracle 才许写盘）。
3. **确定性生成**：禁 stdlib ``random``、禁 ``set`` 迭代序、禁系统时钟；
   本模块用固定顺序的显式用例表，两次运行逐字节一致。

用法：
    py -3.12 -X utf8 tools/gen_cases.py            # 生成/覆盖
    py -3.12 -X utf8 tools/gen_cases.py --check    # 位级一致守门
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# 摘要与台账校验**共用包内唯一实现源**（不在工具里写第二份口径）
from medreview.bench.ledger import case_digest  # noqa: E402

FIX_DIR = os.path.join(ROOT, "src", "medreview", "fixtures")
CASES_PATH = os.path.join(FIX_DIR, "cases.json")

# 假机构名白名单（题面 §四.1：一律虚构名；基准断言校验样例机构名在白名单内）
FAKE_ORGS = ["XX医疗美容门诊部（虚构）", "XX市第X医院（虚构）", "XX中医诊所（虚构）"]

# ---------------------------------------------------------------------------
# 用例表：``expect`` = 必须出现的键；``forbid`` = 必须不出现的键。
# 期望值一律按**法条语义**推导（不按引擎现状回填）——引擎不符即缺陷。
# ---------------------------------------------------------------------------
CASES = [
    # ---- B1 品类判定（含反向：非涉医内容 → NOT_ASSESSED） ----
    # 发布前自查 + 未提供审查证明 → IAM-7-1 记待补材料 → 结论 WARN（不得读作 OK）
    dict(id="B1-001", suite="b1_category",
         input="XX医疗美容门诊部（虚构）开展双眼皮手术，欢迎预约面诊。",
         expect=["grade:WARN", "category:medical", "input_required:IAM-7-1"]),
    # 保健食品缺"本品不能代替药物" → 无条件义务缺失 → BLOCK
    dict(id="B1-002", suite="b1_category",
         input="本品为保健食品，蓝帽子认证，每日一粒。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-D1"]),
    dict(id="B1-003", suite="b1_category",
         input="特殊医学用途配方食品，适用于术后营养支持。",
         expect=["grade:WARN", "category:fsmp", "input_required:IAM-7-1"]),
    # 非涉医内容：无适用规则 → NOT_ASSESSED（"没检查过"不是"合规"）
    dict(id="B1-004", suite="b1_category", input="今天天气不错，适合出门散步。",
         expect=["grade:NOT_ASSESSED"],
         forbid=["category:medical", "category:drug", "category:device",
                 "category:health_food", "category:fsmp"]),
    # 多品类并列：医疗 + 器械同时成立（不二选一）
    dict(id="B1-005", suite="b1_category",
         input="XX市第X医院（虚构）引进新型理疗仪，医疗器械注册证齐全，欢迎体验。",
         expect=["grade:WARN", "category:medical", "category:device",
                 "input_required:IAM-7-1"]),

    # ---- B2 禁止情形核查（正例命中） ----
    dict(id="B2-001", suite="b2_prohibited",
         input="XX医疗美容门诊部（虚构）双眼皮手术，保证治愈，无效退款。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-2"]),
    dict(id="B2-002", suite="b2_prohibited",
         input="XX市第X医院（虚构）肿瘤科，本院治疗有效率达到98%，欢迎咨询。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-3"]),
    dict(id="B2-003", suite="b2_prohibited",
         input="XX医疗美容门诊部（虚构）由某知名代言人倾情推荐，效果显著。",
         expect=["grade:BLOCK", "category:medical", "hit:AL-16-4"]),
    dict(id="B2-004", suite="b2_prohibited",
         input="本品保健食品可有效降血糖、降血压，是糖尿病患者的必需之选。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-2"]),
    dict(id="B2-005", suite="b2_prohibited",
         input="XX中医诊所（虚构）使用解放军专家团队技术，专治疑难杂症。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-7"]),
    # 白名单外表述 → WARN（**不得判 BLOCK**：白名单外是待复核，非明确禁止）
    dict(id="B2-006", suite="b2_prohibited",
         input="XX医疗美容门诊部（虚构）无痛双眼皮手术，专家坐诊，技术领先。",
         expect=["grade:WARN", "category:medical", "hit:MAM-6-W"],
         forbid=["grade:BLOCK", "hit:MAM-7-1", "hit:MAM-7-2", "hit:MAM-7-3"]),
    # 保健食品必须显著标明"本品不能代替药物"——已标明 → 该义务条 compliant
    dict(id="B2-007", suite="b2_prohibited",
         input="本品为保健食品，本品不能代替药物，每日一粒。",
         expect=["grade:WARN", "category:health_food",
                 "rule:compliant:AL-18-D1", "input_required:IAM-7-1"]),
    # 药品广告已显著标明禁忌、不良反应 → 义务条 compliant
    dict(id="B2-008", suite="b2_prohibited",
         input="本品为药品片剂，禁忌、不良反应详见说明书。",
         expect=["grade:WARN", "category:drug", "rule:compliant:AL-16-D2"]),
    # 保健食品宣称疾病预防/治疗 + 缺"不能代替药物" → 双命中
    dict(id="B2-009", suite="b2_prohibited",
         input="本品保健食品可预防疾病、治疗慢性病，抗肿瘤。",
         expect=["grade:BLOCK", "category:health_food",
                 "hit:AL-18-2", "hit:AL-18-D1"]),
    # 医疗广告涉及疾病名称/药物（literal 词面）
    dict(id="B2-010", suite="b2_prohibited",
         input="XX医疗美容门诊部（虚构）专治各类疾病名称所指病症，配合药物治疗。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-1"]),
    # 医疗器械：功效断言 + 与其他器械比较
    dict(id="B2-011", suite="b2_prohibited",
         input="本医疗器械保证有效，绝对安全，效果优于其他医疗器械。",
         expect=["grade:BLOCK", "category:device", "hit:AL-16-1", "hit:AL-16-3"]),

    # ---- B3 适用域反向（"这条规则不该命中"） ----
    # 保健食品内容不得被《广告法》§16（只管医疗/药品/器械）判命中
    dict(id="B3-001", suite="b3_applies_reverse",
         input="本品保健食品保证有效，绝对安全，无副作用。",
         expect=["category:health_food", "grade:BLOCK",
                 "rule:skipped:AL-16-1", "rule:skipped:AL-16-2",
                 "rule:skipped:AL-16-3", "rule:skipped:AL-16-4",
                 "hit:AL-18-1"],
         forbid=["hit:AL-16-1", "hit:AL-16-2", "hit:AL-16-3", "hit:AL-16-4"]),
    # 医疗内容不得被《广告法》§18（只管保健食品）判命中
    dict(id="B3-002", suite="b3_applies_reverse",
         input="XX医疗美容门诊部（虚构）宣传治愈率与有效率。",
         expect=["category:medical", "grade:BLOCK",
                 "rule:skipped:AL-18-1", "rule:skipped:AL-18-2",
                 "rule:skipped:AL-18-3", "rule:skipped:AL-18-4",
                 "rule:skipped:AL-18-5", "hit:MAM-7-3"],
         forbid=["hit:AL-18-1", "hit:AL-18-2", "hit:AL-18-3", "hit:AL-18-4", "hit:AL-18-5"]),
    # 非涉医内容：全部规则不适用 → NOT_ASSESSED，且**任何 hit 都不许出现**
    dict(id="B3-003", suite="b3_applies_reverse",
         input="这家餐厅的招牌菜味道很好。",
         expect=["grade:NOT_ASSESSED"],
         forbid=["hit:MAM-7-1", "hit:MAM-7-2", "hit:MAM-7-3", "hit:AL-16-1",
                 "hit:AL-18-1", "hit:IAM-8-1"]),
    # §7 第 2 款（按审查通过内容发布）**只对已发布情形生效**——发布前自查应判不适用
    dict(id="B3-004", suite="b3_applies_reverse",
         input="XX医疗美容门诊部（虚构）双眼皮手术，欢迎预约。",
         expect=["grade:WARN", "category:medical",
                 "rule:skipped:IAM-7-2", "input_required:IAM-7-1"]),

    # ---- B4 规则驱动覆盖（触达每条生效规则） ----
    dict(id="B4-001", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）内容淫秽、迷信、荒诞。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-4"]),
    dict(id="B4-002", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）贬低他人的技术水平。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-5"]),
    dict(id="B4-003", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）由患者现身说法，卫生技术人员作证明。",
         expect=["grade:BLOCK", "category:medical", "hit:MAM-7-6"]),
    dict(id="B4-004", suite="b4_rule_coverage",
         input="本品保健食品优于其他保健食品，人人必备，为保障健康所必需。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-3", "hit:AL-18-4"]),
    dict(id="B4-005", suite="b4_rule_coverage",
         input="本品保健食品由形象大使推荐，明星推荐值得信赖。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-5"]),
    # 药品广告未显著标明禁忌、不良反应 → §16 款 2 无条件义务缺失 → BLOCK；
    # 同时"不得与批准的说明书不一致"判不了（无说明书）→ 记待补材料
    dict(id="B4-006", suite="b4_rule_coverage",
         input="药品片剂，请按说明书服用，适应症详见说明。",
         expect=["grade:BLOCK", "category:drug",
                 "hit:AL-16-D2", "input_required:AL-16-D1"]),
    # §6 末款（内容须与执业许可证一致）判不了 → 待补材料（不是"命中"）
    dict(id="B4-007", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）执业许可证齐全，诊疗科目详见许可证。",
         expect=["grade:WARN", "category:medical", "input_required:MAM-6-LIC"]),
    # §8 变相发布属确定性禁止情形 → BLOCK（不是 WARN）
    dict(id="B4-008", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）养生知识科普：双眼皮术后如何保养，欢迎预约面诊。",
         expect=["grade:BLOCK", "category:medical", "hit:IAM-8-1",
                 "input_required:IAM-7-1"]),
    dict(id="B4-009", suite="b4_rule_coverage",
         input="XX中医诊所（虚构）健康知识科普，加微信咨询，或扫码了解详情。",
         expect=["grade:BLOCK", "category:medical", "hit:IAM-8-2",
                 "input_required:IAM-7-1"]),
    # 已发布情形：§7 两款（审查证明 + 审查通过内容）都参与判定
    dict(id="B4-010", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）双眼皮手术，欢迎预约。", scenario="published",
         expect=["grade:WARN", "category:medical",
                 "input_required:IAM-7-1", "input_required:IAM-7-2"]),
    # 明确未取得审查证明 → 无条件义务缺失 → BLOCK（不得记成"不适用"）
    dict(id="B4-011", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）双眼皮手术，欢迎预约。", proof="no",
         expect=["grade:BLOCK", "category:medical", "hit:IAM-7-1"]),
    # 明确已取得审查证明 → 该条 compliant（实质核验仍需原件，报告仍提示）
    dict(id="B4-012", suite="b4_rule_coverage",
         input="XX医疗美容门诊部（虚构）双眼皮手术，欢迎预约。", proof="yes",
         expect=["grade:WARN", "category:medical", "rule:compliant:IAM-7-1"]),
    # §16 第（二）项（治愈率/有效率）在器械品类同样适用
    dict(id="B4-013", suite="b4_rule_coverage",
         input="本医疗器械有效率达到95%，注册证齐全。",
         expect=["grade:BLOCK", "category:device", "hit:AL-16-2"]),
    # 药品功效断言（§16 第（一）项）
    dict(id="B4-014", suite="b4_rule_coverage",
         input="本品药品片剂，保证有效，绝对安全。",
         expect=["grade:BLOCK", "category:drug", "hit:AL-16-1"]),
    # 保健食品"为保障健康所必需"（§18 第（三）项）
    dict(id="B4-015", suite="b4_rule_coverage",
         input="本品保健食品是人人必备的保健品，本品不能代替药物。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-3"]),
    # 保健食品功效断言（§18 第（一）项）
    dict(id="B4-016", suite="b4_rule_coverage",
         input="本品保健食品保证有效，绝对安全，无副作用，本品不能代替药物。",
         expect=["grade:BLOCK", "category:health_food", "hit:AL-18-1"]),
    # §8 变相发布（第二款：养生知识 + 联系方式共现）
    dict(id="B4-017", suite="b4_rule_coverage",
         input="XX中医诊所（虚构）分享养生知识，欢迎致电预约，联系电话见文末。",
         expect=["grade:BLOCK", "category:medical", "hit:IAM-8-2",
                 "input_required:IAM-7-1"]),
]


def naive_oracle(case):
    """**独立朴素 oracle**：不 import 引擎，只按用例自带的期望重算自洽性。

    判据 = "把主实现的判定逻辑注释掉，生成器还能算出期望吗？"能 = 期望值有独立来源。

    校验的关系（全部由法条语义推导，不看引擎现状）：
      - ``grade:`` 必须恰好一个，且与其它键自洽；
      - 有 ``category:`` ⟺ grade ≠ NOT_ASSESSED；
      - 有 ``hit:`` ⟹ grade 为 BLOCK/WARN，且被 forbid 的 hit 不得同时出现在 expect；
      - ``grade:BLOCK`` ⟹ 至少一条 ``hit:``（BLOCK 必有确定性命中）；
      - ``grade:NOT_ASSESSED`` ⟹ 无 ``category:`` 且无 ``hit:``。
    """
    expects = set(case.get("expect") or ())
    forbids = set(case.get("forbid") or ())

    grades = [k.split(":", 1)[1] for k in expects if k.startswith("grade:")]
    if len(grades) != 1:
        return False, "expect 必须且只能含一个 grade:*（实得 %s）" % grades
    grade = grades[0]

    has_category = any(k.startswith("category:") for k in expects)
    has_hit = any(k.startswith("hit:") for k in expects)

    if has_category and grade == "NOT_ASSESSED":
        return False, "有品类命中却判 NOT_ASSESSED"
    if not has_category and grade != "NOT_ASSESSED":
        return False, "无品类命中却不是 NOT_ASSESSED"
    if grade == "BLOCK" and not has_hit:
        return False, "判 BLOCK 却无任何 hit:*"
    if grade == "NOT_ASSESSED" and (has_hit or has_category):
        return False, "判 NOT_ASSESSED 却含 category/hit"

    overlap = sorted(expects & forbids)
    if overlap:
        return False, "同一键同时出现在 expect 与 forbid：%s" % overlap
    for key in sorted(forbids):
        if not key.startswith(("hit:", "grade:", "category:")):
            return False, "forbid 只支持 hit:/grade:/category: 前缀（实得 %s）" % key
    return True, ""


def build():
    cases = []
    for case in CASES:
        ok, why = naive_oracle(case)
        if not ok:
            raise SystemExit("生成守卫失败（用例 %s）：%s" % (case["id"], why))
        entry = {
            "id": case["id"],
            "suite": case["suite"],
            "input": case["input"],
            "channel": case.get("channel"),
            "subject": case.get("subject"),
            "scenario": case.get("scenario"),
            "proof": case.get("proof"),
            "expect_keys": list(case["expect"]),
        }
        if case.get("forbid"):
            entry["forbid_keys"] = list(case["forbid"])
        entry["sha256"] = case_digest(entry)
        cases.append(entry)

    entries = [{"id": c["id"], "sha256": c["sha256"]} for c in cases]
    payload = {
        "basis_date": "2026-10-15",
        "generated_by": "tools/gen_cases.py",
        "fake_org_whitelist": FAKE_ORGS,
        "ledger": {"count": len(cases), "entries": entries},
        "coverage_note": "抽样覆盖、非穷举：按规则形态采样，非逐条穷举",
        "cases": cases,
    }
    return _dumps(payload)


def _dumps(payload):
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    return text.replace("\r\n", "\n").rstrip("\n") + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    text = build()
    if "--check" in argv:
        if not os.path.isfile(CASES_PATH):
            sys.stdout.write("FROZEN_TRUTH_MISSING\n")
            return 1
        with open(CASES_PATH, "r", encoding="utf-8", newline="") as handle:
            on_disk = handle.read()
        if on_disk != text:
            sys.stdout.write("FROZEN_TRUTH_DRIFT\n")
            return 1
        sys.stdout.write("FROZEN_TRUTH_OK\n")
        return 0

    if not os.path.isdir(FIX_DIR):
        os.makedirs(FIX_DIR)
    with open(CASES_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    sys.stdout.write("written: %s\n" % os.path.relpath(CASES_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
