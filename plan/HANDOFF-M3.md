# HANDOFF-M3 — 禁止情形核查（下一棒交接）

- **生成时间**：2026-10-16（M2 品类判定器收尾）
- **上一棒**：M2 品类判定器（品类词表扩充 + 每类反例结构 + 共用语面原语 + §8 两款变相信号）
- **下一棒**：M3 禁止情形核查（§7 八项 + §6 白名单 + 广告法 §16/§18 逐款 + 互联网办法 §7/§8）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M3.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M2）

| 交付物 | 位置 | 证据 |
|---|---|---|
| 品类信号词表扩充（5 品类） | `tools/gen_ruleset.py::CATEGORY_RULES` | medical 18 / drug 13 / device 11 / health_food 6 / fsmp 3 词 |
| **每类反例结构**（`exclude_contexts`） | 同上 | 5 类共 18 条；门禁断言"非空 + 非装饰性" |
| 品类判定共用语面原语 | `src/medreview/phrase.py`（**新模块**） | `check.py` 六原语改为其别名；`categorize.py` 经它做命中 |
| §8 两款变相发布疑似信号 | `tools/gen_ruleset.py::VARIANT_RULES` | **2 条**（款 1 商品信息 / 款 2 联系方式） |
| 变相发布 advisory 可核验 | `pipeline.run_check` + `report.render_markdown` | advisory 带 `signals`（命中词 + 条款锚点），Markdown 逐条呈现 |
| advisory 进基准观测集合 | `bench/cases.observed_keys` | `advisory:<kind>` 观测键 + `compare_case` 正向断言 |
| B1 真值库扩充（5 → 13） | `fixtures/cases.json` | 多品类并列正例 + 似是而非边界例（B1-006…013） |
| manifest 品类计数 | `references/manifest.json` | `category_rule_count` / `category_signal_counts` / `category_exclude_counts` / `variant_rule_count` |
| **版本号指纹到品类词表** | `tools/gen_ruleset.py::build` | 哈希输入含 `category_rules` + `variant_rules`（M2 修 K8 实质缺陷） |
| M2 语义门禁 | `tests/test_m2_semantics.py` | **18 项**（词表/反例/共用语面/advisory/多品类/原文逐字/文档计数） |
| 文档计数漂移门禁 | 同上 | `test_data_readme_counts_match_manifest`（M2 实测发现旧版本号漂移后新加） |
| M2 留档 | `plan/M2-词表复核.md` | 5 条实测缺陷 + 逐类词表复核 + 两款信号分工 |
| 规则包版本 | `references/manifest.json` | `ruleset-b229857603`（当轮实测） |
| 真值库 | `fixtures/cases.json` | **57 用例**（B1×13 / B2×14 / B3×8 / B4×22），M1 为 49 |
| 双解释器全量测试 | `tests/` | **109 项全绿**（3.8 与 3.12 双解释器），M1 为 91 |
| 门禁自检 7 项 | `medreview selftest` | SELFTEST_OK |
| 基准四套件 | `medreview bench` | exit 0（B1 用例 13） |
| M2 变异验证 | 见 `plan/M2-词表复核.md` §七 | 四组变异全部使门变红 |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **裸词面 = 品类误报之源（M2 主线，7 例实测）**：裸「医院」判「宠物医院」为医疗、
   裸「挂号」判「挂号信」为医疗、裸「器械」判「健身器械/办公器械」为器械、
   裸「药品」判「国家药品监督管理局/药品监管」为药品、裸「医美」判「医美护肤品」
   为医疗。**这类误报比漏报更坏**——品类判错会**连带把不适用的规则套上来**
   （实测：「国家药品监督管理局发布通告」被判 drug 后直接命中药品标明义务判 BLOCK）。
   已引入 `exclude_contexts` 反例结构，7 例全消除。
2. **反例结构会"装饰性"**：只断言"非空"是假门——写一条与词表无关的排除词同样非空，
   却拦不住任何命中。已加门禁断言"**反例必须确实包住本类某个正向词**"。
3. **版本号不指纹品类词表 = K8 假门（实质缺陷）**：`ruleset_version` 原哈希输入
   不含 `category_rules`/`variant_rules`，故只改词表时**版本号不动**。已修 + 加门禁。
4. **advisory 不进观测集合 = 提示逻辑永不红**：真值库断言了 suspect 却无从观测。
   已把 `advisory:<kind>` 纳入 `observed_keys`。
5. **`data/README.md` 计数表抄了旧版本号（跨棒遗留）**：文档写 `ruleset-28a4cfd991`，
   manifest 实为 `ruleset-f20a805f89`——漂移了整整一棒且**无门看着**。已按当轮实测重写 +
   新增漂移门禁（版本号/生效数/总条目数/用例数四项）。
6. **品类层与规则层的变相信号是两层，别混**：规则层（`IAM-8-1/2`）是**确定性判定**
   （命中即 BLOCK）；品类层（`variant_rules`）**只出 advisory 疑似、不改结论**。
   两层词表宽度不同是有意的（判定要窄而准，提示要宽而全）。
7. **`phrase.py` 进了零字面量扫描面**：它是判定模块，docstring **不能写领域词**；
   且 `selftest._ruleset_tokens` 已把品类**反例结构**也收进扫描词表——写文档时
   用结构性描述（"反例结构""中性词形"），词面只在规则包。
8. **改品类词表后必须重跑两个 `--check`**：`gen_ruleset --check`（版本号变了）与
   `gen_cases --check`（B1 期望可能变）。M2 实测：改词表 → 版本号 `f20a805f89` → `b229857603`。
9. **品类层引文此前无核验（M2 收尾实测发现）**：`category_rules`/`variant_rules` 有
   `anchor`+`quote` 字段，但生成器**只对规则层**做逐字包含断言——品类层引文写错不会红。
   已补 `source`/`clause` 字段 + 生成器回读校验 + 门禁 `test_category_and_variant_quotes_are_verbatim_in_snapshot`。
   **下一棒若加品类/变相信号，必须填 `source`/`clause`，否则生成器拒绝出件。**

---

## 二、下一棒待办（M3 禁止情形核查）

M2 已把品类判定器（模块 2）做扎实；M3 的重心是**模块 3 的规则层验收与收口**：

1. **§7 八项逐条建规则**（当前 7 条生效 + 1 条兜底）：核对 §7 第（一）至（七）项
   是否各有可机读判定要素；第（八）项兜底维持"显式不建规则"（D9）。
2. **§6 白名单**：M1 已按实测 8 项结构化登记（D14 决策：**不逐项建规则**，
   汇总式 `MAM-6-W` 覆盖）。M3 需复核"超出白名单"的判定面是否够用。
3. **广告法 §16/§18 逐款**：当前 §16 有 4 项 + 款 2 四条义务，§18 有 5 项 + 款 2 一条义务；
   M3 复核每款的判定语义与 `terms_basis` 分级（literal / interpretive）。
4. **互联网办法 §7/§8**：`IAM-7-1`（审查证明三态）/`IAM-7-2`（按审查内容发布）/
   `IAM-8-1`/`IAM-8-2`（变相发布两款）——M3 复核三态语义与情形门控（`scenario`）。
5. **Finding 四要素导出前断言**（plan/03 §4.3）：`quote` 逐字在快照、`evidence`
   逐字在文案、`clause_anchor` 可解析、`rule_id` 存在——当前只有零散测试，M3 应做成
   **导出前常驻断言**（不满足即拒绝导出）。
6. **M3 收尾**：写 `plan/HANDOFF-M4.md`，回写 `plan/00`/`05`/`06` 状态。

> **注意**：M3 若增删规则，会改变 `manifest` 计数、`ruleset_version`、B4 覆盖分母与
> B2/B3 期望。改规则后必须**重跑 `gen_ruleset.py` 与 `gen_cases.py`** 并过两个 `--check`。

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
| K8 | 版本号由 manifest 派生 | `medreview/__init__.py` + `manifest.json` | 代码内零版本字面量。**M2 补：哈希输入须含品类/变相发布词表**（`test_ruleset_version_fingerprints_category_tables`） |
| K9 | 词面只存在于规则包 | `references/ruleset.json` | 零字面量门禁（`selftest.JUDGMENT_MODULES`）+ 阳性对照。**写判定模块 docstring 用结构性描述** |
| K10 | 报告层零判定 + 零外链 | `report.py` | `assert_no_external_links` 常驻断言 |
| K11 | 真值库只存输入与期望（**禁 `observed` 字段**） | `fixtures/cases.json` | `cases.truth_field_violations` 守门 |
| K12 | 基准套件在包内（**不得放仓库顶层**） | `src/medreview/bench/` | `test_face5_bench_is_in_package` |
| K13 | 用例摘要单一实现源 | `bench/ledger.case_digest` | 生成器 import 它 |
| K14 | `applies_if` 必须落品类（**不许写 any**） | `ruleset.load_ruleset` 硬门 | 空 categories → 拒绝加载 |
| K15 | 契约块 ↔ 代码字段 ↔ 输出字段序 三方对齐 | `constants.CONTRACT_FIELDS_*` + `SKILL.md` | `tests/test_skill_contract.py`。**改输出字段必须同时改三处** |
| K16 | 否定辖域抑制：命中项处于否定辖域内不算命中 | `phrase.is_negated`（M2 迁出，原 `check._is_negated`） | `test_negation_suppression_unit` + 漏报防护 |
| K17 | 主体门控：`applies_if.subject_signals` / `subject_excludes`；主体未成立 → `skipped` | `check.rule_applies` + `model.Rule` | `test_subject_gate_skips_non_subject` + 子串排除门 |
| K18 | 共现语义：`match.groups` 各组必须同时成立 | `check.match_rule` | `test_role_word_alone_is_not_endorsement` + 阳性对照 |
| K19 | 排除语境：`match.exclude_contexts`，命中项落在更大词形内部不算命中 | `phrase.excluded_context`（M2 迁出） | `test_exclude_context_suppresses_neutral_wordform` |
| K20 | interpretive 词面不得为裸单字（长度 ≥ 2） | `tools/gen_ruleset.py` RULE_DEFS | `test_bare_single_char_terms_are_gone` |
| K21 | 交叉引用行不进项提取 | `tools/gen_ruleset.py::clause_items` + `CROSS_REF_RE` | `test_clause_items_excludes_cross_reference_line` + 阳性对照 |
| K22 | manifest 计数与实算一致（当轮实测，非抄） | `tools/gen_ruleset.py::build` | `test_manifest_counts_match_actual_rules` + `test_whitelist_items_are_eight_and_verbatim` |
| **K23**（M2 新增） | **品类词表须配反例结构，且反例非装饰性**（必须包住本类某个正向词） | `category_rules[*].exclude_contexts` | `test_every_category_has_exclude_contexts` + `test_exclude_contexts_are_not_decorative`（变异验证过） |
| **K24**（M2 新增） | **品类判定复用规则核查的词面原语**（唯一实现源，不自成第二套口径） | `src/medreview/phrase.py` | `test_category_matching_reuses_shared_primitive` + `test_check_module_aliases_shared_primitive` |
| **K25**（M2 新增） | **变相发布疑似只进 advisory、不改结论；advisory 进观测集合** | `categorize.categorize` + `pipeline.run_check` + `bench/cases.observed_keys` | `test_variant_suspect_is_advisory_not_conclusion` + `test_variant_suspect_requires_cooccurrence` |
| **K26**（M2 新增） | **文档计数表纳入漂移门禁**（`data/README.md` ↔ manifest 实算） | `data/README.md` §一之二 | `test_data_readme_counts_match_manifest`（变异验证过） |
| **K27**（M2 新增） | **品类/变相发布条目同样逐条挂原文**（quote 须逐字在快照中） | `tools/gen_ruleset.py::build` + `category_rules`/`variant_rules` 的 `source`/`clause` | 生成器拒绝出件 + `test_category_and_variant_quotes_are_verbatim_in_snapshot`（变异验证过） |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；代码内入口仍有 `_ensure_utf8_stdio()`（CI 是 cp1252）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）。
5. **Git Bash 下 `$?` 会被管道吃掉**：判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）。**变异验证前先备份**（`cp <file> .tmp/xxx.bak`），改完必须还原并复跑全量。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）。
8. **`.gitattributes` 双半**：源码 `* text=auto eol=lf`；快照 `data/knowledge/raw/** -text`。
9. **改判定模块 docstring 会撞零字面量门禁**——判定模块（`constants/model/normalize/ruleset/categorize/check/**phrase**/grade/serialize/paths/pipeline`）的 docstring **连同注释一起被扫**。写说明用结构性描述，**不要引用规则包里的词**。
10. **改输出字段要同步三处**——`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + SKILL.md 字段表。
11. **M2 新增坑：改品类词表必须重跑两个生成器**——`gen_ruleset.py`（版本号变了）+ `gen_cases.py`（B1 期望可能变）；只跑一个会 `--check` 红。
12. **M2 新增坑：`phrase.py` 也受零字面量门禁约束**——它是判定模块，词面只准在规则包。
13. **M2 新增坑：`rm -rf .tmp/clone` 偶发 "Device or resource busy"**（浅克隆复现用）——换个目录名或先 `cd` 出该目录再删。

---

## 五、DoD 逐项 checklist（M2）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 2-1 | 品类信号词表扩充（5 品类，词数当轮实测） | `manifest.category_signal_counts`（medical 18/drug 13/device 11/health_food 6/fsmp 3） | ✅ |
| 2-2 | 每类词表配反例结构 | `category_rules[*].exclude_contexts`（共 18 条）+ 门禁 | ✅ |
| 2-3 | 反例结构非装饰性（包住本类正向词） | `test_exclude_contexts_are_not_decorative`（变异验证过） | ✅ |
| 2-4 | 品类判定复用共用词面原语 | `phrase.py` + `test_category_matching_reuses_shared_primitive` | ✅ |
| 2-5 | §8 两款变相信号就位 | `variant_rules` 2 条 + `test_variant_rules_cover_both_clause_paragraphs` | ✅ |
| 2-6 | 变相发布疑似只进 advisory、不改结论 | `test_variant_suspect_is_advisory_not_conclusion` + `test_variant_suspect_requires_cooccurrence` | ✅ |
| 2-7 | 品类反向样例进真值库（B1 5 → 13） | `fixtures/cases.json` + `bench` B1 达标 | ✅ |
| 2-8 | 版本号指纹到品类/变相发布词表 | `test_ruleset_version_fingerprints_category_tables`（变异验证过） | ✅ |
| 2-9 | manifest 品类计数当轮实算 | `test_manifest_category_counts_match_actual`（变异验证过） | ✅ |
| 2-10 | 文档计数漂移门禁 | `test_data_readme_counts_match_manifest`（变异验证过） | ✅ |
| 2-11 | 双解释器全量测试 | 3.8 与 3.12 各 **109 passed** | ✅ |
| 2-12 | 冻结产物位级一致（双解释器） | `gen_ruleset/gen_cases --check` → FROZEN_TRUTH_OK | ✅ |
| 2-13 | 门禁自检绿 + 基准四套件达标 | `selftest` SELFTEST_OK；`bench` exit 0 | ✅ |
| 2-14 | 变异验证（守门非假门） | M2 **五组**（摘反例/装饰性反例/清空词表/观测器摘 advisory/伪造引文）全部使门变红 | ✅ |
| 2-15 | 干净 venv 安装 + 裸 console script + 非仓库根 CWD | `.venv-test` 内 109 项绿、`medreview.exe selftest` OK、`bench` exit 0 | ✅ |
| 2-16 | CI 检出形态本地复现 | 浅克隆内 109 项绿 + 快照 sha256 全对 + 冻结产物位级一致 | ✅ |
| 2-17 | `plan/HANDOFF-M3.md` 已落盘 | 本文件 | ✅ |
| 2-18 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径（M2 同 M0/M1）**：2-16 只能写"本地等价校验"，因为 `on: push` 从未被
GitHub 执行过（**本项目当前无远端**）。M6 首推后据实补记真实 run id。

---

## 六、关键命令速查

```bash
# 环境
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

# 跑测试（双解释器）
py -3.12 -X utf8 -m pytest tests -q
py -3.8  -X utf8 -m pytest tests -q
py -3.12 -X utf8 -m pytest tests/test_m2_semantics.py -q   # M2 语义门禁（18 项）
py -3.12 -X utf8 -m pytest tests/test_m1_semantics.py -q   # M1 语义门禁（26 项）

# 门禁自检 / 基准
py -3.12 -X utf8 -m medreview.cli selftest
py -3.12 -X utf8 -m medreview.cli bench
py -3.12 -X utf8 -m medreview.cli rules
py -3.12 -X utf8 -m medreview.cli rules --format json      # 计数与锚点（机读）

# 单条审查（人读 / 机读 / 带材料）
py -3.12 -X utf8 -m medreview.cli check --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --format json --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --text "<文案>" --proof yes --proof-file ./审查证明.pdf

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
```

---

## 七、下一棒启动提示词

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M3.md" 继续完成任务
```
