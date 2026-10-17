# HANDOFF-M5 — 交付（下一棒交接）

- **生成时间**：2026-10-17（M4 真值基准收尾）
- **上一棒**：M4 真值基准（四套件可证伪探活 + 卡阈值边界成对用例 + 覆盖声明双登记 + 三件齐备复核 + kind 双层断言测试面锁）
- **下一棒**：M5 交付（SKILL.md 主入口 + 分级报告双轨 + 契约块门禁）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M5.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M4）

| 交付物 | 位置 | 证据 |
|---|---|---|
| **四套件各自可证伪探活** | `tests/test_m4_benchmark.py` | B1/B2/B3/B4 各一条，全部打到端到端 `run_benchmarks` |
| **探针非空自证** | 同上 `_assert_probe_caught` | 断言失败**只能**来自目标套件比对（frozen / 非 not_enabled / 目标套件在 not_met） |
| 卡阈值边界**成对用例** | `gen_cases.py` 的 `form` 字段 | `threshold_exact`×3 + `near_miss`×5；真值库 **58 → 66** |
| 边界语义 **oracle 守卫** | `gen_cases.naive_oracle` | 退化边界用例（缺 hit / 缺 forbid / 非法 form）被生成守卫拒绝 |
| **覆盖声明双登记** | `manifest.benchmark_coverage` + `fixtures/cases.json#coverage` | 逐形态登记条目总数/采样数/采样清单 + 显式非穷举 |
| 非穷举**数值坐实** | `test_coverage_is_numerically_non_exhaustive` | 边界形态采样数 < 规则包条目总数（33） |
| kind 双层断言（**测试面**） | `test_dispatch_structural_layer_in_test_face` + `test_dispatch_runtime_layer_each_kind_runs` | 结构层 + 运行层 + 与 selftest S5 同源 |
| 真值库**三件齐备复核** | `test_truth_library_three_pieces_in_place` 等 | 入库件 + 位级守门 + CLI 通路真读 |
| M4 语义门禁 | `tests/test_m4_benchmark.py` | **24 项** |
| M4 留档 | `plan/M4-真值基准复核.md` | 9 类实测发现 + 边界三类逐条 + 10 组变异验证 |
| 真值库 | `src/medreview/fixtures/cases.json` | **66 用例**（B1×13 / B2×22 / B3×8 / B4×23），M3 为 58 |
| 规则包版本 | `references/manifest.json` | `ruleset-c7c2a6d1fd`（M4 **未改规则**，版本号不变） |
| 双解释器全量测试 | `tests/` | **172 项全绿**（3.8 与 3.12），M3 为 148 |
| 门禁自检 7 项 | `medreview selftest` | SELFTEST_OK |
| 基准四套件 | `medreview bench` | exit 0（B1 13 / B2 22 / B3 8 / B4 23） |
| M4 变异验证 | `.tmp/m4/mutate.py`（不入仓库） | **10 组**全部使门变红 |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **plan/03 §6.2 的"卡阈值边界"示例在本引擎上不成立（重要勘误）**：
   示例写「有效率 100%」恰命中 /「有效率达到 99%」边界，暗含"数值 `≥` 比较器"。
   但本引擎的规则是**词面/模式匹配**，**没有数值比较器**——实测 `有效率100%`
   与 `有效率99%` **同样命中** `MAM-7-3`（判据是"出现「有效率」这个词"，与数字无关）。
   **处置**：边界轴建在**真实判定线**上（literal 词形 / 排除语境 / 否定辖域），
   三类各成对（见 `plan/M4-真值基准复核.md` §三）。**下一棒若再加边界用例，
   须先确认该处**真有一条判定线**，别照抄 plan/03 的数值示例。
2. **探活必须打到端到端入口 `run_benchmarks`**：只断言 `_run_suite` 证明不了
   "用户敲的 `medreview bench` 真把缺陷跑出来了"（M3 遗留的 B4 探活就是弱探活）。
3. **探活必须自证"缺陷真打中目标套件"**：篡改须**重算摘要 + 同步台账**，
   否则被冻结台账门在套件比对之前拦下（证明的是台账门，不是套件判据）。
4. **"改一条输入"未必构成有效探针**：给输入追加「（改）」可能**判据不变**
   （期望对尾部追加不敏感）→ 探针空转。有效探针须**真改出结论差异**。
5. **生成器静默失败 = 变异空转**：变异驱动重生成后**必须断言生成器返回 0**
   （本棒实测：写坏生成器 → 抛错 → 产物未变 → 误判"门没红"）。
6. **变异驱动注入前必须 `assert_baseline_clean()`**：一次异常退出会把文件留在
   变异态，下一轮备份就备份脏状态，"还原"反而固化变异。
7. **覆盖声明双登记不能互相牵制（生成环）**：真值库采样数**不能**写进 manifest
   （会与 `gen_cases --check` 互相依赖）。数值各留单一实现源，跨件一致性交门禁。
8. **`data/README.md` 计数表已被漂移门禁看住（K26）**：改用例后必须同步该表；
   M4 新增"真值形态分布"行 + 同源门禁 `test_data_readme_form_counts_match`。
9. **B4 覆盖的"唯一覆盖"规则是 B4 探活的构造前提**：M4 实算为
   `IAM-7-2` / `AL-16-D3` / `AL-16-D4` / `AL-16-D5`（各 1 个 B4 用例覆盖）。
   探活会自动重算（不硬编码 id），但须确保仍存在"唯一覆盖"的规则。
10. **M4 未改规则 → 规则包版本号不变**（`ruleset-c7c2a6d1fd`）：M4 只改真值库与
    manifest 的覆盖登记。**若下一棒改规则，须重跑两个生成器**（见 §四.8）。
11. **`form` 字段已进真值库台账摘要**：改 `form` 会改 `case_digest` → 必须重跑
    `gen_cases.py` 并过 `--check`。`truth_field_violations` 只禁 `observed` 类字段
    （`form` 是形态登记，不是观测，允许）。

---

## 二、下一棒待办（M5 交付）

M4 已把**真值基准自身的强度**做扎实（探活可证伪 + 边界成对 + 覆盖双登记 + 三件齐备）。
M5 的重心是**交付面**：把 SKILL.md 主入口、分级报告双轨、契约块三方对齐做到位。

1. **SKILL.md 主入口定稿**（plan/03 §2）：
   - 入参表（`--text`/`--text-file`/`--channel`/`--subject`/`--hint`/`--proof`）；
   - **机器可解析契约块**（与 `constants.CONTRACT_FIELDS_*` + 实际输出字段序**三方对齐**，K15）；
   - 确定性纪律明写（LLM 不直接给结论；输入只本地处理不外发）。
2. **分级报告双轨**（plan/03 §5）：
   - 人读 Markdown + 机读 JSON **共用同一 `report_sections()`**（"两格式一致"是结构性质）；
   - **报告必备 8 章节**（缺一即断言失败，plan/03 §5.3）；
   - **报告层零判定 + 零外链**（AST 门禁三条：不 import 规则层 + 无算术 BinOp + 无政策数值字面量）。
3. **契约块三方对齐门禁**（K15）：改输出字段必须**同时**改三处
   （`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + SKILL.md 字段表）——
   注意 `Finding.evidence_kind` **刻意不进契约字段**（内部判定字段，不是输出字段）。
4. **`scan` 批量通路演示**（习题面）：出 Markdown + JSON 报告。
5. **报告免责声明与红线**：强制附免责（题面 §六.1）；不做药品推荐（§六.2）；
   报告**不引用真实机构违规案例**（D4）。
6. **M5 收尾**：写 `plan/HANDOFF-M6.md`，回写 `plan/00`/`05`/`06` 状态。

> **注意**：M5 若只改报告层（不改规则/用例），**不需要**重跑生成器；
> 但若改了输出字段，须同步 `constants.CONTRACT_FIELDS_*` + `SKILL.md` 两处
> （K15 三方对齐测试会红）。

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
| K28 | **Finding 四要素导出前常驻断言** | `pipeline.assert_findings_traceable` + `errors.FindingIncomplete` | 4 条变异门禁 + 接线自证 |
| K29 | **证据性质是结构字段**（不得字符串前缀特判；证据不得 join 成串） | `model.Finding.evidence_kind` + `constants.EVIDENCE_KINDS` | `test_evidence_kind_is_structural_not_string_prefix` |
| K30 | **同段共现**：`match.segment_groups`；句读分隔符与否定辖域共用 | `phrase.cooccur_in_segment` | `test_cooccur_in_segment_requires_same_segment` |
| K31 | **并列义务宾语须拆组**（组内"任一即可"只用于同义词面） | `AL-16-D2` 的 `require_all_of` | `test_al_16_d2_requires_both_contraindication_and_adverse_reaction` |
| K32 | **逐项/逐款结构门禁**：§7 项 1–7；§16 项 1–4；§18 项 1–5；兜底集合恰三处 | `ruleset.json` 的 `item` + `excluded_clauses` | `test_mam_clause_7_items_one_to_seven_...` + `test_every_catch_all_clause_is_registered` |
| **K33**（M4 新增） | **每套件配可证伪探活，打到端到端 `run_benchmarks`；探针自证"缺陷真打中目标套件"（重算摘要 + 同步台账，失败只能来自套件比对）** | `tests/test_m4_benchmark.py` 四条探活 + `_tamper` / `_assert_probe_caught` | 变异 G1（对账器变盲 → 四套件全红）+ G2（删探活 → 覆盖自证红） |
| **K34**（M4 新增） | **卡阈值边界须成对且两侧都被真值库断言**（本引擎判定线 = literal 词形 / 排除语境 / 否定辖域，**无数值比较器**） | `gen_cases.py` 的 `form` + `naive_oracle` 边界守卫 | `test_boundary_forms_present_and_paired` + `test_boundary_cases_actually_pass_the_engine` + 变异 G3/G4/G10 |
| **K35**（M4 新增） | **覆盖声明双登记**（规则包侧记条目总数/形态轴；真值库侧记逐形态采样数/采样清单）；非穷举须有**数值**坐实 | `manifest.benchmark_coverage` + `fixtures/cases.json#coverage` | `test_coverage_declaration_is_double_registered` + `test_coverage_is_numerically_non_exhaustive` + 变异 G5/G6 |
| **K36**（M4 新增） | **kind 双层断言在测试面也锁一份**（结构层 + 运行层），且与 selftest S5 同源 | `test_dispatch_structural_layer_in_test_face` + `test_dispatch_runtime_layer_each_kind_runs` | 变异 G8/G9 |
| **K37**（M4 新增） | **真值形态分布纳入文档漂移门禁** | `data/README.md` §一之二 新增行 | `test_data_readme_form_counts_match` + 变异 G7 |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；代码内入口仍有 `_ensure_utf8_stdio()`（CI 是 cp1252）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）。
5. **Git Bash 下 `$?` 会被管道吃掉**：判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）。**变异验证前先备份**。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）。
8. **改规则/词表必须重跑两个生成器**——`gen_ruleset.py`（版本号变）+ `gen_cases.py`
   （期望可能变）；只跑一个会 `--check` 红。**M4 未改规则**，故版本号不变。
9. **`git checkout <file>` 会冲掉未提交改动（M3 实测）**：变异验证还原用备份，别用 git checkout。
10. **M4 新增坑：变异驱动注入前必须 `assert_baseline_clean()`**——异常退出会把文件
    留在变异态，下一轮备份即脏状态，"还原"反而固化变异（本棒实测踩到）。
11. **M4 新增坑：变异驱动重生成后必须断言生成器返回 0**——生成器静默抛错会让
    "门没红"被误判成假门（本棒实测：`[]  # MUTANT` 吞尾逗号致生成器语法错）。
12. **M4 新增坑：`form` 字段进台账摘要**——改 `form` 必须重跑 `gen_cases.py` 并过 `--check`。
13. **改判定模块 docstring 会撞零字面量门禁**——写说明用结构性描述，不引用规则包词面。
14. **改输出字段要同步三处**——`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + SKILL.md 字段表。
15. **`rm -rf .tmp/clone` 偶发 "Device or resource busy"**——换个目录名或先 `cd` 出该目录再删。
16. **新增生效规则必须同时补 B4 用例**——B4 分母 = 生效规则数，漏补即 `bench` 不达标。

---

## 五、DoD 逐项 checklist（M4）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 4-1 | 四套件各自可证伪探活（打到端到端入口） | `test_m4_benchmark.py` 4 条探活 | ✅ |
| 4-2 | 探活"探针非空"自证 | `_assert_probe_caught` + `assert_baseline_clean` | ✅ |
| 4-3 | 真值库三件齐备复核 | 入库件 + 位级守门 + CLI 通路真读 | ✅ |
| 4-4 | 卡阈值边界类成对补齐 | `form` 字段 + 8 条边界用例 + oracle 守卫 | ✅ |
| 4-5 | 覆盖声明双登记（非穷举有数值坐实） | `manifest.benchmark_coverage` + `fixtures#coverage` | ✅ |
| 4-6 | `kind` 分派表双层断言在测试面锁一份 | 结构层 + 运行层 + 与 selftest S5 同源 | ✅ |
| 4-7 | 双解释器全量测试 | 3.8 与 3.12 各 **172 passed** | ✅ |
| 4-8 | 冻结产物位级一致（双解释器） | `gen_ruleset/gen_cases --check` → FROZEN_TRUTH_OK | ✅ |
| 4-9 | 门禁自检绿 + 基准四套件达标 | `selftest` SELFTEST_OK；`bench` exit 0（B1 13 / B2 22 / B3 8 / B4 23） | ✅ |
| 4-10 | **变异验证（守门非假门）** | M4 **10 组**全部使门变红 | ✅ |
| 4-11 | 干净 venv 安装 + 裸 console script + 非仓库根 CWD | `.venv-m4` 内 `selftest` OK、`bench` exit 0、`check` exit 1/0 | ✅ |
| 4-12 | CI 检出形态本地复现 | 浅克隆内 172 项绿 + 快照 sha256 全对 + 冻结产物位级一致 | ✅ |
| 4-13 | `plan/M4-真值基准复核.md` 已落盘 | 9 类实测发现 + 边界三类逐条 + 10 组变异 | ✅ |
| 4-14 | `plan/HANDOFF-M5.md` 已落盘 | 本文件 | ✅ |
| 4-15 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径（M4 同 M0–M3）**：4-12 只能写"本地等价校验"，因为 `on: push`
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
py -3.12 -X utf8 -m pytest tests/test_m4_benchmark.py -q   # M4 语义门禁（24 项）
py -3.12 -X utf8 -m pytest tests/test_m3_semantics.py -q   # M3 语义门禁（39 项）

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
py -3.12 -m venv .venv-m4
./.venv-m4/Scripts/python.exe -m pip install -U pip
NO_PROXY="*" no_proxy="*" ./.venv-m4/Scripts/python.exe -m pip install -e ".[dev]"
./.venv-m4/Scripts/medreview.exe selftest

# CI 检出形态复现（浅克隆）
rm -rf .tmp/clone3 && git clone -q --depth 1 --no-tags "file:///<仓库绝对路径>" .tmp/clone3

# 变异验证（M4 驱动，**不入仓库**；必须用备份还原，别用 git checkout）
py -3.12 -X utf8 .tmp/m4/mutate.py
```

---

## 七、下一棒启动提示词

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M5.md" 继续完成任务
```
</content>