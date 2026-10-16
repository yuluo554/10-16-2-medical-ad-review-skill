# HANDOFF-M2 — 品类判定器（下一棒交接）

- **生成时间**：2026-10-16（M1 数据先行收尾）
- **上一棒**：M1 数据先行（快照入仓 + 条文块 + 规则包冻结 + manifest + 台账 + 词表复核）
- **下一棒**：M2 品类判定器（品类关键词表 + 场景判定 + 反向样例）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M2.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M1）

| 交付物 | 位置 | 证据 |
|---|---|---|
| 三源快照入仓（`-text` 字节冻结） | `data/knowledge/raw/*.txt` | LF 无 CRLF；sha256 入 `data/ledger.csv`（**本轮实测三份逐份 ALL_MATCH**） |
| 三源可获取性复测 | `data/README.md` §二.4 | live 字节数 == 入仓字节数（32858 / 16130 / 7413），**页面未改版 → 基准日维持 2026-10-15** |
| 条文块 + 规则包 + manifest | `src/medreview/references/` | **生效 29 条**（M0 为 25）+ 3 条兜底（显式不建规则）；锚点核不到即拒绝加载（未启用 0） |
| §6 白名单结构化登记 | `ruleset.json` `whitelist_items` | **8 项**（从快照实算，不手抄）；`whitelist_item_count: 8` |
| §16 款 2 提示语义务补齐 | `AL-16-D3/D4/D5/D6` | 处方药/非处方药/个人自用器械三条无条件义务 + 器械禁忌前提条（input_required） |
| 词表复核留档 | `plan/M1-词表复核.md` | 13 条 interpretive 逐条复核；5 条修正；四类缺陷记录 |
| 真值库 | `src/medreview/fixtures/cases.json` | **49 用例**（B1×5 / B2×14 / B3×8 / B4×22），M0 为 37 |
| 基准四套件 | `src/medreview/bench/` | **全部达标**（`medreview bench` exit 0；B4 覆盖 29 条生效规则） |
| 门禁自检 7 项 | `medreview selftest` | SELFTEST_OK |
| 测试套件 | `tests/` | **91 项全绿**（3.8 与 3.12 双解释器） |
| M1 语义回归门禁 | `tests/test_m1_semantics.py` | 26 项（否定辖域/主体门控/交叉引用/共现/排除语境/契约/计数） |
| CLI 材料回传通路 | `src/medreview/cli.py` `--proof-file` | 只记文件名+sha256+字节数（不落本地路径） |
| 契约三方对齐 | `SKILL.md` + `constants.CONTRACT_FIELDS_*` | `proof_file` 已加入；`test_skill_contract.py` 绿 |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **交叉引用会劫持项提取（真缺陷，已修）**：《医疗广告管理办法》§6 末款「（一）至（六）项…一致。」被 `clause_items` 当成**第（一）项**，覆盖真项（医疗机构第一名称）。M0 未触发（无逐项 §6 规则），但**建 §6 逐项规则即爆**。已加 `CROSS_REF_RE` 排除「（n）至」「（n）、」起头的行。
2. **法条强制要求的免责语含被禁词面**：实测「不能保证治愈」被判 BLOCK（`保证治愈`+`治愈` 双命中）、「不能代替药物治疗」被判 BLOCK（裸 `治疗`）。**这类误报比漏报更坏**——用户按提示改文案反而改错。已引入否定辖域抑制（D15）。
3. **否定辖域判据返工两次**：首版"片段内出现否定词即抑制"→ 漏报（「不**少**患者保证治愈」的「不」属"不少"）；次版"否定词紧贴"→ 又漏报（「不能**保证**治愈」中间隔着动词）。定版 = 片段内存在**真否定词** + 排除「不」开头的非否定词（`constants.NON_NEGATION_WORDS`）。
4. **裸单字词面必误报**：裸 `第一`（「第一时间」「医疗机构第一名称」）、裸 `治疗`/`预防` 均实测误报。已删裸字、改复合词面，并落成门禁「interpretive 词面长度 ≥ 2」。
5. **角色词 ≠ 代言证明**：§7（六）原文是「利用<主体>的名义、形象**作证明**的」——「为患者提供优质服务」曾被裸角色词判 BLOCK。已改**两组共现**（`match.groups`）。
6. **品类信号词过宽**：药品品类原含 `说明书`/`适应症`（通用词）→ 器械广告「请仔细阅读产品**说明书**」把器械误判成药品品类。已移出，补入 `处方药`/`非处方药` 等强信号。
7. **子串包含会误适用**：「**非处方药**」含子串「处方药」→ 非处方药广告被判"缺处方药提示语"。已引入 `subject_excludes`。
8. **主体未成立 ≠ 该写没写**：普通器械广告不含"个人自用"信号，却被判"缺个人自用器械提示语"。主体未成立一律记 **`skipped`（不适用）**，不记命中。
9. **外部前提类义务不能建无条件义务条**：器械禁忌提示语的前提（"注册证明文件中有禁忌内容**的**"）在外部材料里，无条件判"缺提示语"会让器械广告一律违规。改 `input_required`（D18）。
10. **零字面量门禁会拦 docstring**：判定模块的 docstring 里写领域词（如"处方药""保证治愈""患者"）会被门禁当场拦下。**写文档时用结构性描述**（"特定主体""被禁词面"），词面只在规则包。
11. **报告层新增字段必须同步契约块**：加 `proof_file` 时改了 `constants.CONTRACT_FIELDS_ITEM` + `SKILL.md` 契约块 + 字段表三处，缺一即 `test_skill_contract.py` 红（三方对齐门禁真的在工作）。

---

## 二、下一棒待办（M2 品类判定器）

M1 已把品类判定的**机制**预置好（`categorize.py` + 规则包 `category_rules` / `variant_rules`）。M2 的重心是**扩充与验收**：

1. **扩充品类信号词表**（`tools/gen_ruleset.py::CATEGORY_RULES`）：
   - 当前 5 品类（medical/drug/device/health_food/fsmp）词表偏小，需按首期条款覆盖面补词（如 medical 的机构形态、drug 的剂型/批准文号形态、device 的器械名/注册证形态）；
   - **每类词表须有反例**（不该判成该类的内容）——否则"信号词表写错"永不红。
2. **补场景判定（`variant_publish_suspect`）**：当前 `variant_rules` 只 1 条；§8 的两款（知识形态+商品信息 / 知识形态+联系方式）已各有规则，但**品类层的 suspect 信号**可再细。
3. **品类判定的反向样例进真值库**：B1 套件当前 5 例，需补"多品类并列不二选一"的正例与"似是而非"的边界例（如"医美护肤品的化妆品"不该判 medical）。
4. **M2 收尾**：写 `plan/HANDOFF-M3.md`，回写 `plan/00`/`05`/`06` 状态。

> **注意**：M2 的改动会**改变品类集合**，进而改变 B1/B2/B3 套件的期望。改词表后必须**重跑 `gen_cases.py` 的朴素 oracle 守卫**并重生成冻结件（`--check` 位级一致）。

---

## 三、既定口径清单（K 编号——**动了会打挂测试**）

| 编号 | 口径 | 实现点 | 守门 |
|---|---|---|---|
| K1 | 条款号锚点 + 法条原文 | `references/ruleset.json` | 锚点核不到原文的规则**拒绝加载**（`ruleset.load_ruleset`），进未启用清单 |
| K2 | 退出码 0/1/2/3 | `cli.main` 单一分派 | `tests/test_skeleton.py` 的 6 条端到端断言 |
| K3 | BLOCK/WARN/OK/NOT_ASSESSED 映射 | `grade.grade_results` | `test_grade_priority_block_over_warn` 等 |
| K4 | 判定三态 + `input_required` 第三态 | `check.py` + `constants.RULE_STATES` | 反向样例（`b3_applies_reverse`）+ `test_input_required_never_grades_ok` |
| K5 | 序列化参数（sort_keys + ensure_ascii=False + LF + 尾换行） | `serialize.write_text_atomic` | `test_serialize_lf_and_trailing_newline` |
| K6 | 基准门槛随 manifest 下发（**代码零默认值**） | `bench/runner.load_thresholds` | 缺门槛 → exit 2 |
| K7 | 对账语义单一实现源 | `bench/cases.compare_case` | 真值库测试与基准共用 |
| K8 | 版本号由 manifest 派生 | `medreview/__init__.py` + `manifest.json` | 代码内零版本字面量 |
| K9 | 词面只存在于规则包 | `references/ruleset.json` | 零字面量门禁（`selftest.JUDGMENT_MODULES` 扫描面）+ 阳性对照。**写判定模块 docstring 时用结构性描述，不写领域词** |
| K10 | 报告层零判定 + 零外链 | `report.py` | `assert_no_external_links` 常驻断言 |
| K11 | 真值库只存输入与期望（**禁 `observed` 字段**） | `fixtures/cases.json` | `cases.truth_field_violations` 守门 |
| K12 | 基准套件在包内（**不得放仓库顶层**） | `src/medreview/bench/` | `test_face5_bench_is_in_package` |
| K13 | 用例摘要单一实现源 | `bench/ledger.case_digest` | 生成器 import 它 |
| K14 | `applies_if` 必须落品类（**不许写 any**） | `ruleset.load_ruleset` 硬门 | 空 categories → 拒绝加载 |
| K15 | 契约块 ↔ 代码字段 ↔ 输出字段序 三方对齐 | `constants.CONTRACT_FIELDS_*` + `SKILL.md` | `tests/test_skill_contract.py`。**改输出字段必须同时改三处** |
| **K16**（M1 新增） | **否定辖域抑制**：命中项处于否定辖域内不算命中 | `check._is_negated` + `constants.NEGATION_MARKERS` / `NON_NEGATION_WORDS` | `test_negation_suppression_unit` + 漏报防护 `test_non_negation_word_does_not_suppress`（变异验证过） |
| **K17**（M1 新增） | **主体门控**：`applies_if.subject_signals` / `subject_excludes`；主体未成立 → `skipped` | `check.rule_applies` + `model.Rule.subject_signals/subject_excludes` | `test_subject_gate_skips_non_subject` + `test_subject_excludes_prevents_substring_match`（变异验证过） |
| **K18**（M1 新增） | **共现语义**：`match.groups` 各组必须同时成立 | `check.match_rule` | `test_role_word_alone_is_not_endorsement` + 阳性对照 |
| **K19**（M1 新增） | **排除语境**：`match.exclude_contexts`，命中项落在更大词形内部不算命中 | `check._excluded_context` | `test_exclude_context_suppresses_neutral_wordform` |
| **K20**（M1 新增） | **interpretive 词面不得为裸单字**（长度 ≥ 2） | `tools/gen_ruleset.py` RULE_DEFS | `test_bare_single_char_terms_are_gone` |
| **K21**（M1 新增） | **交叉引用行不进项提取** | `tools/gen_ruleset.py::clause_items` + `CROSS_REF_RE` | `test_clause_items_excludes_cross_reference_line` + 阳性对照（变异验证过） |
| **K22**（M1 新增） | **manifest 计数与实算一致**（当轮实测，非抄） | `tools/gen_ruleset.py::build` | `test_manifest_counts_match_actual_rules` + `test_whitelist_items_are_eight_and_verbatim`（变异验证过） |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；代码内入口仍有 `_ensure_utf8_stdio()`（CI 是 cp1252）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）。
5. **Git Bash 下 `$?` 会被管道吃掉**：判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）。
8. **`.gitattributes` 双半**：源码 `* text=auto eol=lf`；快照 `data/knowledge/raw/** -text`。
9. **M1 新增坑：改判定模块 docstring 会撞零字面量门禁**——判定模块（`constants/model/normalize/ruleset/categorize/check/grade/serialize/paths/pipeline`）的 docstring **连同注释一起被扫**。写说明时用结构性描述（"特定主体""被禁词面""阴性词形"），**不要引用规则包里的词**。撞了会看到 `AssertionError: check.py 含判定词面：[...]`。
10. **M1 新增坑：改输出字段要同步三处**——`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块（`<!-- contract-fields: ... -->`）+ SKILL.md 字段表。只改代码会红 `test_contract_fields_match_code_fields`。

---

## 五、DoD 逐项 checklist（M1）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 1-1 | 三源快照入仓 + 台账 sha256 | `data/ledger.csv`（本轮浅克隆内 **ALL_MATCH**） | ✅ |
| 1-2 | 三源可获取性复测（基准日维持） | `data/README.md` §二.4（live == 入仓字节数） | ✅ |
| 1-3 | 交叉引用不劫持项提取（实测缺陷已修 + 门禁 + 变异验证） | `test_clause_items_excludes_cross_reference_line` | ✅ |
| 1-4 | 每条规则挂条款号+原文+URL+基准日；锚点核不到拒绝加载 | `medreview rules`（生效 29 / 未启用 0） | ✅ |
| 1-5 | §6 白名单按**实测 8 项**建（结构化 + 逐字断言） | `ruleset.whitelist_items` + 白名单门禁 | ✅ |
| 1-6 | §16 款 2 三条提示语义务补齐 | `AL-16-D3/D4/D5` + `AL-16-D6` | ✅ |
| 1-7 | 13 条 interpretive 词表逐条复核 | `plan/M1-词表复核.md` §三 | ✅ |
| 1-8 | 真值库随规则扩展（49 用例；B4 覆盖 29 条） | `bench` 全达标 | ✅ |
| 1-9 | `data/README.md` 与 manifest 计数联动（当轮实测） | `data/README.md` §一之二 + 计数门禁 | ✅ |
| 1-10 | `input_required` 运行时索取体验（`--proof-file`） | CLI 入参 + 报告"证明材料文件"行 | ✅ |
| 1-11 | 冻结产物位级一致（双解释器） | `gen_ruleset/gen_cases --check` → FROZEN_TRUTH_OK | ✅ |
| 1-12 | 双解释器全量测试 | 3.8 与 3.12 各 **91 passed** | ✅ |
| 1-13 | 门禁自检绿 + 基准四套件达标 | `selftest` SELFTEST_OK；`bench` exit 0 | ✅ |
| 1-14 | 变异验证（守门非假门） | M1 五组变异全部使门变红 | ✅ |
| 1-15 | 干净 venv 安装 + 裸 console script + 非仓库根 CWD | `.venv-test` 内 91 项绿、`medreview.exe selftest` OK、`bench` exit 0 | ✅ |
| 1-16 | CI 检出形态本地复现 | 浅克隆内 91 项绿 + sha256 ALL_MATCH + 冻结产物位级一致 + 干净 venv bench exit 0 | ✅ |
| 1-17 | `plan/HANDOFF-M2.md` 已落盘 | 本文件 | ✅ |
| 1-18 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径（M1 同 M0）**：1-16 只能写"本地等价校验"，因为 `on: push` 从未被 GitHub 执行过（**本项目当前无远端**）。M6 首推后据实补记真实 run id。

---

## 六、关键命令速查

```bash
# 环境
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

# 跑测试（双解释器）
py -3.12 -X utf8 -m pytest tests -q
py -3.8  -X utf8 -m pytest tests -q
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
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M2.md" 继续完成任务
```
