# HANDOFF-M4 — 真值基准（下一棒交接）

- **生成时间**：2026-10-17（M3 禁止情形核查收尾）
- **上一棒**：M3 禁止情形核查（§7 八项 + §6 白名单 + 广告法 §16/§18 逐款 + 互联网办法 §7/§8 + Finding 四要素导出前断言）
- **下一棒**：M4 真值基准（合成样例 + 真值库 + 四套件 + 探活）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M4.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M3）

| 交付物 | 位置 | 证据 |
|---|---|---|
| **四要素导出前常驻断言** | `pipeline.assert_findings_traceable` | 常驻在唯一导出点 `run_check`；不满足即抛 `FindingIncomplete`（exit 1） |
| 证据性质**结构化** | `model.Finding.evidence_kind` + `constants.EVIDENCE_*` | 取代字符串前缀特判（改措辞不再能绕过门禁） |
| **同段共现原语** | `src/medreview/phrase.py::cooccur_in_segment` | `check.match_rule` 支持 `segment_groups`；句读分隔符与否定辖域共用 |
| 比较类规则补**被比较对象**要件 | `AL-16-3` / `AL-18-4` | 实测误报消除：与其他机构合作／领先于行业标准／口感好于普通食品／最先进（无对象） |
| §7（一）**具体疾病名**召回修复 | `MAM-7-1B`（interpretive 分条） | 实测「专治糖尿病」零命中 → BLOCK；与 §18（二）疾病名族同源 |
| §16 款 2 并列宾语拆组 | `AL-16-D2`（`require_all_of` 两组） | 只标其一 → noncompliant（原为漏报） |
| 中性词形排除语境 | `AL-16-1`/`MAM-7-2`（根治性/根治术/根治率）、`AL-18-3`（必需氨基酸…） | 临床/营养学术语不再被判命中 |
| 斥否类极性词 | `constants.NEGATION_MARKERS` 补 `抵制` | 同极性表述结果一致（门禁断言） |
| §6 白名单外判定面补**商业促销方向** | `MAM-6-W` | 实测「八折优惠」「服务态度好」原零命中 |
| M3 语义门禁 | `tests/test_m3_semantics.py` | **39 项**（逐项/逐款/四要素变异/同段共现/中性词形/极性一致） |
| M3 留档 | `plan/M3-词表复核.md` | 6 类实测缺陷 + 逐条核对表 + 10 组变异验证 |
| 真值库 | `fixtures/cases.json` | **58 用例**（B1×13 / B2×14 / B3×8 / B4×23），M2 为 57 |
| 规则包版本 | `references/manifest.json` | `ruleset-c7c2a6d1fd`（当轮实测） |
| 双解释器全量测试 | `tests/` | **148 项全绿**（3.8 与 3.12），M2 为 109 |
| 门禁自检 7 项 | `medreview selftest` | SELFTEST_OK |
| 基准四套件 | `medreview bench` | exit 0（B4 用例 23） |
| M3 变异验证 | 见 `plan/M3-词表复核.md` §六 | **10 组**全部使门变红 |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **`git checkout` 会冲掉未提交改动（本棒实测踩坑）**：变异验证后还原**必须**用
   备份文件（`.tmp/mut/*.bak` + `.tmp/restore.sh`），**不得** `git checkout <file>`
   ——本棒实测把 pipeline.py 的三处四要素断言改动全冲掉了，需重新施加。
   **每棒变异验证前先备份、改完必须还原并复跑全量**。
2. **join 出来的证据串过不了"逐字在文案"断言**：`prohibited_pattern`/
   `whitelist_scope`/`variant_publish` 原先把多个命中项 `"、".join(...)` 成一条
   Finding，而「A、B」**不是文案片段**——四要素断言当场报红。已改**逐命中项
   各出一条**。**下一棒若新增判定处理器，不得 join 证据串**。
3. **义务缺失类证据必须走 `evidence_kind` 字段，不得靠字符串前缀特判**：
   "该写而没写"的证据**不可能**在文案里出现；用 `startswith("缺失应显著标明")`
   绕过门禁是脆弱的（改一句措辞即绕过）。已结构化。
4. **"规则存在"≠"规则抓得到目标形态"**：§7（一）字面匹配「疾病名称」时，
   对真实疾病名**零命中**——规则看着有、实际不工作（静默失效）。**下一棒建
   规则/用例时须用"该规则的目标形态"构造探针**，不要只测字面词。
5. **并列宾语必须拆组**：原文「显著标明**禁忌、不良反应**」是两项义务；放进同一
   `require_all_of` 组 = 组内任一即可 = 只标一项也算履行（漏报）。**凡「、」并列
   的义务宾语，逐项拆组**。
6. **同段共现 vs 全局共现是两个语义**：全局共现会把分属两句的词面凑成一次命中。
   凡原文要件是"**同一句陈述里**的共现"（比较、变相发布），用 `segment_groups`。
7. **四要素断言只保证"可溯源"，不保证"判定正确"**：它拦的是引文写错／证据不在
   文案／规则不存在；判定语义由基准套件与语义门禁承担（M4 的重点）。
8. **改规则后必须重跑两个生成器**：`gen_ruleset.py`（版本号变）+ `gen_cases.py`
   （期望可能变），并过两个 `--check`。M3 实测：改规则 → 版本号 `b229857603` →
   `85e8f55716` → `c7c2a6d1fd`（两轮改动两次变号）。
9. **新增生效规则必须有 B4 覆盖用例**：B4 的分母是**生效规则数**，新增一条规则
   而不补用例 → B4 不达标（本棒实测：加 `MAM-7-1B` 后 B4 立刻红，补 B4-023 才绿）。
10. **`data/README.md` 计数表已被漂移门禁看住**（M2 的 K26）：改规则/用例后必须
    同步该表（版本号/生效数/总条目数/用例数），否则 `test_data_readme_counts_match_manifest` 红。

---

## 二、下一棒待办（M4 真值基准）

M3 已把**规则层**做扎实（判定语义 + 溯源断言 + 39 项门禁）；M4 的重心是
**真值基准自身的强度**——真值库已随 M1/M2/M3 扩展（58 用例），M4 要做的是
把"基准是假门"的所有通路堵死：

1. **四套件各自的可证伪探活**（plan/03 §6.4）：给**每套件**注入一个缺陷
   （坏锚点 / 期望篡改 / 适用域写反 / 边界语义改 `>`），断言 `run_benchmarks`
   **真返回非 0** 且文本同步声明未达标。当前只有 B1 与 B4 各一条探活
   （`test_probe_b1_defect_is_caught` / `test_probe_rule_coverage_defect_is_caught`）
   ——**B2/B3 缺探活**。
2. **探活的"探针非空"自证**：探活本身也可能空转（注入的缺陷没打中任何断言）。
   每条探活须断言"注入后**确实**有 non-zero 与 not_met"。
3. **真值库三件齐备复核**：入库件 + `--check` 位级守门 + **CLI 路径真读**
   （`bench` 先过 `check_frozen_ledger`）——三件当前都在，M4 复核并留档。
4. **边界类用例补齐**（plan/03 §6.2）：样本矩阵须含"卡阈值边界"
   （`threshold_exact` 验 `≥` 语义、`near_miss` 验"不到不命中"）。
   当前边界类用例形态需复核（如「有效率 100%」恰命中 / 「有效率达到 99%」边界）。
5. **覆盖声明双登记**（plan/03 §6.3）：manifest 逐形态登记"规则包条目总数 /
   真值库采样数 / 采样清单"，并显式声明"**抽样覆盖、非穷举**"。
6. **`kind` 分派表双层断言复核**（plan/03 §4.1）：结构层（键集合 ↔ 实现互异）
   + 运行层（每 kind 真跑不抛错）——当前 selftest S5 已覆盖，M4 复核并在
   测试面也锁一份。
7. **M4 收尾**：写 `plan/HANDOFF-M5.md`，回写 `plan/00`/`05`/`06` 状态。

> **注意**：M4 若增删用例，会改变 `cases.json`、B4 覆盖分母与
> `data/README.md` 计数。改用例后必须**重跑 `gen_cases.py`** 并过 `--check`。

---

## 三、既定口径清单（K 编号——**动了会打挂测试**）

| 编号 | 口径 | 实现点 | 守门 |
|---|---|---|---|
| K1 | 条款号锚点 + 法条原文 | `references/ruleset.json` | 锚点核不到原文的规则**拒绝加载**，进未启用清单 |
| K2 | 退出码 0/1/2/3 | `cli.main` 单一分派 | `tests/test_skeleton.py` 的端到端断言 |
| K3 | BLOCK/WARN/OK/NOT_ASSESSED 映射 | `grade.grade_results` | `test_grade_priority_block_over_warn` |
| K4 | 判定三态 + `input_required` 第三态 | `check.py` + `constants.RULE_STATES` | 反向样例 + `test_input_required_never_grades_ok` |
| K5 | 序列化参数（sort_keys + ensure_ascii=False + LF + 尾换行） | `serialize.write_text_atomic` | `test_serialize_lf_and_trailing_newline` |
| K6 | 基准门槛随 manifest 下发（**代码零默认值**） | `bench/runner.load_thresholds` | 缺门槛 → exit 2 |
| K7 | 对账语义单一实现源 | `bench/cases.compare_case` | 真值库测试与基准共用 |
| K8 | 版本号由 manifest 派生 | `medreview/__init__.py` + `manifest.json` | 代码内零版本字面量。**M2 补：哈希输入须含品类/变相发布词表** |
| K9 | 词面只存在于规则包 | `references/ruleset.json` | 零字面量门禁（`selftest.JUDGMENT_MODULES`）+ 阳性对照。**写判定模块 docstring 用结构性描述** |
| K10 | 报告层零判定 + 零外链 | `report.py` | `assert_no_external_links` 常驻断言 |
| K11 | 真值库只存输入与期望（**禁 `observed` 字段**） | `fixtures/cases.json` | `cases.truth_field_violations` 守门 |
| K12 | 基准套件在包内（**不得放仓库顶层**） | `src/medreview/bench/` | `test_face5_bench_is_in_package` |
| K13 | 用例摘要单一实现源 | `bench/ledger.case_digest` | 生成器 import 它 |
| K14 | `applies_if` 必须落品类（**不许写 any**） | `ruleset.load_ruleset` 硬门 | 空 categories → 拒绝加载 |
| K15 | 契约块 ↔ 代码字段 ↔ 输出字段序 三方对齐 | `constants.CONTRACT_FIELDS_*` + `SKILL.md` | `tests/test_skill_contract.py`。**改输出字段必须同时改三处** |
| K16 | 否定辖域抑制 | `phrase.is_negated` | `test_negation_suppression_unit` + 漏报防护 |
| K17 | 主体门控 | `check.rule_applies` + `model.Rule` | `test_subject_gate_skips_non_subject` + 子串排除门 |
| K18 | 共现语义：`match.groups` 各组必须同时成立 | `check.match_rule` | `test_role_word_alone_is_not_endorsement` + 阳性对照 |
| K19 | 排除语境：`match.exclude_contexts` | `phrase.excluded_context` | `test_exclude_context_suppresses_neutral_wordform` |
| K20 | interpretive 词面不得为裸单字（长度 ≥ 2） | `tools/gen_ruleset.py` RULE_DEFS | `test_bare_single_char_terms_are_gone` |
| K21 | 交叉引用行不进项提取 | `tools/gen_ruleset.py::clause_items` + `CROSS_REF_RE` | `test_clause_items_excludes_cross_reference_line` |
| K22 | manifest 计数与实算一致（当轮实测） | `tools/gen_ruleset.py::build` | `test_manifest_counts_match_actual_rules` |
| K23 | 品类词表须配反例结构，且反例非装饰性 | `category_rules[*].exclude_contexts` | `test_exclude_contexts_are_not_decorative` |
| K24 | 品类判定复用规则核查的词面原语 | `src/medreview/phrase.py` | `test_category_matching_reuses_shared_primitive` |
| K25 | 变相发布疑似只进 advisory、不改结论；advisory 进观测集合 | `categorize` + `pipeline` + `bench/cases.observed_keys` | `test_variant_suspect_is_advisory_not_conclusion` |
| K26 | 文档计数表纳入漂移门禁 | `data/README.md` §一之二 | `test_data_readme_counts_match_manifest` |
| K27 | 品类/变相发布条目同样逐条挂原文 | `tools/gen_ruleset.py::build` | 生成器拒绝出件 + `test_category_and_variant_quotes_are_verbatim_in_snapshot` |
| **K28**（M3 新增） | **Finding 四要素导出前常驻断言**（rule_id 存在／anchor 可解析／quote 逐字在快照／evidence 逐字在文案）；不满足即**拒绝导出**（exit 1） | `pipeline.assert_findings_traceable` + `errors.FindingIncomplete` | 4 条变异门禁 + `test_run_check_invokes_traceability_assertion`（接线自证） |
| **K29**（M3 新增） | **证据性质是结构字段**（`text_span` / `obligation_missing`），**不得**靠字符串前缀特判；且**证据不得 join 成串** | `model.Finding.evidence_kind` + `constants.EVIDENCE_KINDS` | `test_evidence_kind_is_structural_not_string_prefix` + `test_finding_evidence_verbatim_in_input` |
| **K30**（M3 新增） | **同段共现**：原文要件是"同一句读段内共现"时用 `match.segment_groups`（全局共现会跨句凑合）；句读分隔符与否定辖域**共用** `constants.SEGMENT_DELIMITERS` | `phrase.cooccur_in_segment` + `check.match_rule` | `test_cooccur_in_segment_requires_same_segment` + `test_segment_delimiters_shared_with_negation_scope` |
| **K31**（M3 新增） | **并列义务宾语须拆组**（「禁忌、不良反应」= 两组，缺一即 noncompliant）；组内"任一即可"只用于**同义/别名**词面 | `AL-16-D2` 的 `require_all_of` | `test_al_16_d2_requires_both_contraindication_and_adverse_reaction` |
| **K32**（M3 新增） | **逐项/逐款结构门禁**：§7 项号集合恰为 1–7（第（八）项兜底不建）；§16 项 1–4；§18 项 1–5；兜底登记集合恰为三处 | `ruleset.json` 的 `item` + `excluded_clauses` | `test_mam_clause_7_items_one_to_seven_...` + `test_every_catch_all_clause_is_registered` |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；代码内入口仍有 `_ensure_utf8_stdio()`（CI 是 cp1252）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）。
5. **Git Bash 下 `$?` 会被管道吃掉**：判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）。**变异验证前先备份**
   （`cp <file> .tmp/xxx.bak`），改完必须还原并复跑全量。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）。
8. **`.gitattributes` 双半**：源码 `* text=auto eol=lf`；快照 `data/knowledge/raw/** -text`。
9. **改判定模块 docstring 会撞零字面量门禁**——判定模块（`constants/model/normalize/ruleset/categorize/check/phrase/grade/serialize/paths/pipeline`）的 docstring **连同注释一起被扫**。写说明用结构性描述，**不要引用规则包里的词**。**M3 实测**：`constants.py` 的注释里引用了两个政策词面 → S2 门禁当场红。
10. **改输出字段要同步三处**——`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + SKILL.md 字段表。**注意 `Finding.evidence_kind` 刻意不进契约字段**（它是内部判定字段，不是输出字段）。
11. **改规则/词表必须重跑两个生成器**——`gen_ruleset.py`（版本号变）+ `gen_cases.py`（期望可能变）；只跑一个会 `--check` 红。
12. **`phrase.py` 也受零字面量门禁约束**——它是判定模块，词面只准在规则包。
13. **`rm -rf .tmp/clone` 偶发 "Device or resource busy"**——换个目录名或先 `cd` 出该目录再删。
14. **M3 新增坑：`git checkout <file>` 会冲掉未提交改动**——变异验证还原用备份脚本，别用 git checkout（见 §一.1）。
15. **M3 新增坑：新增生效规则必须同时补 B4 用例**——B4 分母 = 生效规则数，漏补即 `bench` 不达标（不是"漏个用例"，是整套件红）。

---

## 五、DoD 逐项 checklist（M3）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 3-1 | §7 八项逐条核对（第（一）至（七）项各有规则；第（八）项兜底不建） | `ruleset.json` 项号集合恰为 1–7 + `excluded_clauses` 三处登记 | ✅ |
| 3-2 | §6 白名单复核（8 项登记 + 超出白名单判定面**两个方向**） | `MAM-6-W` 词表 + `test_whitelist_scope_covers_commercial_promotion_direction` | ✅ |
| 3-3 | 广告法 §16 逐款（项 1–4 + 款 2 六条义务；项 5 兜底不建） | `AL-16-*` 共 10 条 + 项号门禁 | ✅ |
| 3-4 | 广告法 §18 逐款（项 1–5 + 款 2 一条义务；项 6 兜底不建） | `AL-18-*` 共 6 条 + 项号门禁 | ✅ |
| 3-5 | 互联网办法 §7/§8（三态 + 情形门控 + 变相发布两款） | `test_iam_7_1_review_proof_three_states` + `test_iam_7_2_scenario_gate` + `test_iam_8_both_paragraphs_have_rules` | ✅ |
| 3-6 | **每条 Finding 四要素齐备且可机器核验**（quote 逐字在快照、evidence 逐字在文案） | `pipeline.assert_findings_traceable`（导出前常驻）+ 4 条变异门禁 | ✅ |
| 3-7 | **导出前常驻断言**（不满足即拒绝导出，不留半溯源报告） | `errors.FindingIncomplete` → CLI exit 1 + `test_cli_exit_code_on_traceability_failure` | ✅ |
| 3-8 | **适用域反向样例必红** | B3 套件 8 用例 + `test_al_16_3_comparison_requires_comparison_target` 等阴性断言 | ✅ |
| 3-9 | `terms_basis` 分级可核验（literal 词面逐字在原文） | `test_terms_basis_literal_terms_are_verbatim_in_clause` | ✅ |
| 3-10 | 双解释器全量测试 | 3.8 与 3.12 各 **148 passed** | ✅ |
| 3-11 | 冻结产物位级一致（双解释器） | `gen_ruleset/gen_cases --check` → FROZEN_TRUTH_OK | ✅ |
| 3-12 | 门禁自检绿 + 基准四套件达标 | `selftest` SELFTEST_OK；`bench` exit 0（B4 用例 23） | ✅ |
| 3-13 | **变异验证（守门非假门）** | M3 **10 组**（拆断言接线/退化共现/摘对象组/退回单组/删项规则/摘两类排除语境/摘极性词/摘促销词/删疾病名条）全部使门变红 | ✅ |
| 3-14 | 干净 venv 安装 + 裸 console script + 非仓库根 CWD | `.venv-test` 内 `selftest` OK、`bench` exit 0、`check` exit 1/0 符合声明语义 | ✅ |
| 3-15 | CI 检出形态本地复现 | 浅克隆内 148 项绿 + 快照 sha256 全对 + 冻结产物位级一致 | ✅ |
| 3-16 | `plan/M3-词表复核.md` 已落盘 | 本棒留档（6 类缺陷 + 逐条核对 + 10 组变异） | ✅ |
| 3-17 | `plan/HANDOFF-M4.md` 已落盘 | 本文件 | ✅ |
| 3-18 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径（M3 同 M0/M1/M2）**：3-15 只能写"本地等价校验"，因为 `on: push`
从未被 GitHub 执行过（**本项目当前无远端**）。M6 首推后据实补记真实 run id。

---

## 六、关键命令速查

```bash
# 环境
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

# 跑测试（双解释器）
py -3.12 -X utf8 -m pytest tests -q
py -3.8  -X utf8 -m pytest tests -q
py -3.12 -X utf8 -m pytest tests/test_m3_semantics.py -q   # M3 语义门禁（39 项）
py -3.12 -X utf8 -m pytest tests/test_m2_semantics.py -q   # M2 语义门禁（18 项）
py -3.12 -X utf8 -m pytest tests/test_m1_semantics.py -q   # M1 语义门禁（26 项）

# 门禁自检 / 基准
py -3.12 -X utf8 -m medreview.cli selftest
py -3.12 -X utf8 -m medreview.cli bench
py -3.12 -X utf8 -m medreview.cli rules
py -3.12 -X utf8 -m medreview.cli rules --format json      # 计数与锚点（机读）

# 单条审查（人读 / 机读 / 带材料 / 已发布情形）
py -3.12 -X utf8 -m medreview.cli check --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --format json --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --text "<文案>" --proof yes --proof-file ./审查证明.pdf
py -3.12 -X utf8 -m medreview.cli check --text "<文案>" --scenario published

# 冻结产物重生成与位级守门
py -3.12 -X utf8 tools/make_snapshots.py            # 重新抓快照（需要网络）
py -3.12 -X utf8 tools/gen_ruleset.py               # 重生成规则包/manifest/台账
py -3.12 -X utf8 tools/gen_ruleset.py --check       # 位级一致守门
py -3.12 -X utf8 tools/gen_cases.py                 # 重生成真值库
py -3.12 -X utf8 tools/gen_cases.py --check         # 位级一致守门

# CI workflow 结构守门
py -3.12 -X utf8 tests/check_workflows.py

# 干净环境验证（照 README 那条安装通路）
py -3.12 -m venv .venv-test
./.venv-test/Scripts/python.exe -m pip install -U pip
NO_PROXY="*" no_proxy="*" ./.venv-test/Scripts/python.exe -m pip install -e ".[dev]"
./.venv-test/Scripts/medreview.exe selftest

# CI 检出形态复现（浅克隆）
rm -rf .tmp/clone2 && git clone -q --depth 1 --no-tags "file:///<仓库绝对路径>" .tmp/clone2

# 变异验证（**必须**用备份还原，别用 git checkout）
mkdir -p .tmp/mut && cp <file> .tmp/mut/<file>.bak
# …注入缺陷、跑目标测试、确认变红…
cp .tmp/mut/<file>.bak <file>   # 还原后复跑全量
```

---

## 七、下一棒启动提示词

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M4.md" 继续完成任务
```
