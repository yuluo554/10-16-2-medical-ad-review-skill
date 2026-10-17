# HANDOFF-M6 — 发布（下一棒交接）

- **生成时间**：2026-10-17（M5 交付收尾）
- **上一棒**：M5 交付（SKILL.md 三方对齐补强 + 报告层零判定三条 AST 门禁 + 分级报告双轨 + scan 批量通路修复）
- **下一棒**：M6 发布（脱敏四步 + 干净环境验证 + 建仓首推 + tag/Release + 收尾固化）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M6.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M5）

| 交付物 | 位置 | 证据 |
|---|---|---|
| **SKILL.md 契约三处对齐** | `SKILL.md` + `constants.CONTRACT_FIELDS_*` | 契约块 + **人读字段表** + 输出字段序，三处各有门（`tests/test_skill_contract.py`，6 项） |
| **报告必备 8 章节机器可解析声明** | `SKILL.md` `<!-- report-sections: ... -->` | 8 节 id 与**序** ↔ `report_sections()` 实算逐 id 对齐 |
| **报告层零判定三条 AST 门禁** | `src/medreview/selftest.py` S8/S9/S10 | 不 import 引擎模块 / 不做算术 / 不内联政策数值；**阳性 + 阴性对照齐备** |
| **分级报告双轨（单一渲染源）** | `report.py::report_sections` + `_section_lines` | 机读 `sections` **逐字段等于**结构源；人读标题来自同源；批量同源 |
| **批量通路逐件渲染** | `report.py::render_markdown_batch` + `cli.cmd_scan` | `scan --format markdown` 逐件出全 8 章节（3 件 → 每章节标题出现 3 次） |
| **批量读入阶段失败隔离** | `cli.cmd_scan` | 一个坏编码件只记 `failed`，不再拖垮整批 |
| **批量机读结构同形** | `cli.cmd_scan`（改走 `render_json`） | 批量逐件含 `sections`（8 节）+ `disclaimer` |
| 免责三要件 | `report.py::DISCLAIMER` | 辅助自查 / 不构成法律意见 / 不替代官方审查 |
| 合成数据纪律 | `samples/`（3 件）+ 假机构名白名单 | `samples/` 与**渲染产物**机构名形态全在白名单内 |
| M5 语义门禁 | `tests/test_m5_delivery.py` | **29 项** |
| M5 变异验证 | `.tmp/m5/mutate.py`（不入仓库） | **13 组**全部使门变红，还原后全量绿 |
| M5 留档 | `plan/M5-交付复核.md` | 12 类实测发现 + 三处对齐表 + 三条门禁对照 + 批量演示 + 13 组变异 |
| 规则包 / 真值库 | `references/manifest.json` / `fixtures/cases.json` | **M5 未改规则与用例**：版本号仍 `ruleset-c7c2a6d1fd`，真值库仍 **66 用例** |
| 双解释器全量测试 | `tests/` | **204 项全绿**（3.8 与 3.12），M4 为 172 |
| 门禁自检 | `medreview selftest` | **10 项** SELFTEST_OK（M4 为 7 项） |
| 基准四套件 | `medreview bench` | exit 0（B1 13 / B2 22 / B3 8 / B4 23） |
| 冻结产物位级一致 | `gen_ruleset/gen_cases --check` | FROZEN_TRUTH_OK（双解释器） |
| 干净 venv | `.venv-m5`（已进 `.gitignore`） | `selftest` OK、`bench` exit 0、`check` exit 1/0、`scan` 两格式 exit 1 |
| CI 检出形态本地复现 | 浅克隆 | **204 项**绿 + 快照 sha256 3/3 全对 + 冻结产物位级一致 |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **`scan` 人读分支只渲染第一件（真缺陷，已修）**：原 `render_markdown(results[0]["report"])`
   ——多件时第 2 件起静默丢失。修：`render_markdown_batch` 逐件渲染。
2. **`scan` 读入阶段无失败隔离（真缺陷，已修）**：一个坏编码件让整批 exit 2 且不产出报告，
   与"失败件单列，不中断整批"的宣称矛盾。修：读入阶段逐件 try/except。
3. **批量机读与单件机读不同形（真缺陷，已修）**：批量原用 `to_dict()`（无 `sections`/`disclaimer`）。
   修：批量逐件也走 `render_json`。
4. **SKILL.md 字段表漏 `notes`（K15 的"三处"实际只守一处）**：已修 + 新增字段表门禁。
5. **"零政策数值"不能按裸数字判（重要勘误）**：`report.py` 有结构性常量 0/3/12，政策号集合含 1–8
   ——裸判必误红。定案判据：**条款号引用形态**（§+数字 / 第+数字）+ **百分比阈值形态**。
6. **"无算术"必须豁免模板 `%` 与字符串拼接**：不豁免则门过宽、一开就红（等于没门）。
7. **`\d+\s*%` 会误伤 `sha256 %s`**：用 `%(?![sdfr%])` 排除模板占位符。
8. **报告层原挂一根无用引擎线**（`from . import constants`，全文件未用）：删掉后"不 import 引擎模块"
   才从"大概没有"变成可静态核验为零。
9. **新增 AST 门禁必须配阴性对照**：只有阳性对照会漏"门过宽"，修缺陷会变成改代码迎合门。
11. **渲染重构必须做"逐字节等价"核验（M5 实测踩到）**：抽出章节正文唯一源时丢了覆盖表后的
    空行 → Markdown 把「未启用清单」行吸进上一条列表项；已修 + 锁门 + 变异 G11。
12. **M6 提示**：`git tag` / `Release` / 建仓都是**对外动作**，且 P1–P8 仍按"推荐默认；未执行"留档
    （用户未逐项答复）——M6 动手前须按 `plan/06` §三 的措辞口径处理，**不写"用户已确认"**。

---

## 二、下一棒待办（M6 发布）

M5 已把**交付面**做扎实（契约三处对齐 + 报告双轨 + 批量通路 + 报告层零判定门禁）。
M6 是发布棒，重心在**对外动作与发布留档**（`plan/05` M6 行 + `plan/06` §六 R1–R10）。

1. **脱敏四步**（`plan/06` R1）：姊妹表述处置 / 跟踪文件名扫描 / 全文本内容扫描 /
   二进制样本扫描 / 构建产物扫描；**命令 + 结论逐条留档**。
2. **提交元数据邮箱检查**（R2）：`git log --format="%ae %ce" --all | sort -u`；
   真实个人邮箱 → noreply 改写。
3. **干净环境验证**（R3）：新目录 clone + 全新 venv，**按 README 逐条跑通**，
   逐条 + 退出码语义成表（含 `check` 退出 1 = 检出命中，非故障）。
4. **建仓 + CI 首推**（R4）：按 `plan/06` P1/P2 的推荐默认（**先 private**，绿了再切 public）；
   push↔run 逐条对账（`head_sha` + `conclusion`）；预留"至少一轮诊断"预算。
5. **tag + Release**（R5）：annotated tag（P3 = `v0.1.0`）+ Release 附**源码 zip**
   （P4；**ASCII 附件名**）+ `--verify-tag`。
6. **发布物本体已验**（R6）：真下载附件 → sha256 与台账一致 → 中立目录解压跑冻结态 `selftest`。
7. **元信息终检**（R7）+ **发布后匿名复核**（R8）+ **缓议项清零**（R9，逐条全表）。
8. **README 收尾**（R10）：状态行转正 + CI badge + 「下载即用」+「已知环境问题」节。
9. **CI 诚实口径回填**：M0–M5 的 DoD 里凡写"CI 待首推验证"的项，M6 首推后**据实补记真实 run id**
   （**追加事实，不回填美化**；历史文档保留原措辞）。
10. **M6 收尾**：写 `plan/HANDOFF-M7.md`（若收尾即终局，则写终局留档），
    回写 `plan/00`/`05`/`06` 状态。

> **注意**：M6 若不改规则/用例/输出字段，**不需要**重跑生成器；
> 一旦改了输出字段，须同步三处（`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + 契约表），
> 一旦改了规则/词表，须重跑**两个**生成器（`gen_ruleset.py` + `gen_cases.py`）。

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
| K8 | 版本号由 manifest 派生 | `medreview/__init__.py` + `manifest.json` | 代码内零版本字面量。**哈希输入须含品类/变相发布词表** |
| K9 | 词面只存在于规则包 | `references/ruleset.json` | 零字面量门禁（`selftest.JUDGMENT_MODULES`）+ 阳性对照。**判定模块 docstring 用结构性描述** |
| K10 | 报告层零外链 | `report.py` | `assert_no_external_links` 常驻断言（渲染出口） |
| K11 | 真值库只存输入与期望（**禁 `observed` 字段**） | `fixtures/cases.json` | `cases.truth_field_violations` 守门 |
| K12 | 基准套件在包内（**不得放仓库顶层**） | `src/medreview/bench/` | `test_face5_bench_is_in_package` |
| K13 | 用例摘要单一实现源 | `bench/ledger.case_digest` | 生成器 import 它 |
| K14 | `applies_if` 必须落品类（**不许写 any**） | `ruleset.load_ruleset` 硬门 | 空 categories → 拒绝加载 |
| K15 | 契约三方对齐 | `constants.CONTRACT_FIELDS_*` + `SKILL.md` | `tests/test_skill_contract.py`。**改输出字段必须同时改三处**；`Finding.evidence_kind` **刻意不进契约字段** |
| K16 | 否定辖域抑制 | `phrase.is_negated` | `test_negation_suppression_unit` + 漏报防护 |
| K17 | 主体门控 | `check.rule_applies` + `model.Rule` | `test_subject_gate_skips_non_subject` + 子串排除门 |
| K18 | 共现语义：`match.groups` 各组必须同时成立 | `check.match_rule` | `test_role_word_alone_is_not_endorsement` + 阳性对照 |
| K19 | 排除语境：`match.exclude_contexts` | `phrase.excluded_context` | `test_exclude_context_suppresses_neutral_wordform` |
| K20 | interpretive 词面不得为裸单字（长度 ≥ 2） | `tools/gen_ruleset.py` RULE_DEFS | `test_bare_single_char_terms_are_gone` |
| K21 | 交叉引用行不进项提取 | `gen_ruleset.clause_items` + `CROSS_REF_RE` | `test_clause_items_excludes_cross_reference_line` |
| K22 | manifest 计数与实算一致（当轮实测） | `gen_ruleset.build` | `test_manifest_counts_match_actual_rules` |
| K23 | 品类词表须配反例结构，且反例非装饰性 | `category_rules[*].exclude_contexts` | `test_exclude_contexts_are_not_decorative` |
| K24 | 品类判定复用规则核查的词面原语 | `src/medreview/phrase.py` | `test_category_matching_reuses_shared_primitive` |
| K25 | 变相发布疑似只进 advisory、不改结论；advisory 进观测集合 | `categorize` + `pipeline` + `bench/cases.observed_keys` | `test_variant_suspect_is_advisory_not_conclusion` |
| K26 | 文档计数表纳入漂移门禁 | `data/README.md` §一之二 | `test_data_readme_counts_match_manifest` |
| K27 | 品类/变相发布条目同样逐条挂原文 | `gen_ruleset.build` | 生成器拒绝出件 + `test_category_and_variant_quotes_are_verbatim_in_snapshot` |
| K28 | **Finding 四要素导出前常驻断言** | `pipeline.assert_findings_traceable` + `errors.FindingIncomplete` | 4 条变异门禁 + 接线自证 |
| K29 | **证据性质是结构字段**（不得字符串前缀特判；证据不得 join 成串） | `model.Finding.evidence_kind` + `constants.EVIDENCE_KINDS` | `test_evidence_kind_is_structural_not_string_prefix` |
| K30 | **同段共现**：`match.segment_groups`；句读分隔符与否定辖域共用 | `phrase.cooccur_in_segment` | `test_cooccur_in_segment_requires_same_segment` |
| K31 | **并列义务宾语须拆组** | `AL-16-D2` 的 `require_all_of` | `test_al_16_d2_requires_both_contraindication_and_adverse_reaction` |
| K32 | **逐项/逐款结构门禁**：§7 项 1–7；§16 项 1–4；§18 项 1–5；兜底集合恰三处 | `ruleset.json` 的 `item` + `excluded_clauses` | `test_mam_clause_7_items_one_to_seven_...` + `test_every_catch_all_clause_is_registered` |
| K33（M4） | **每套件配可证伪探活，打到端到端 `run_benchmarks`；探针自证"缺陷真打中目标套件"** | `tests/test_m4_benchmark.py` 四条探活 | 变异 G1/G2（M4 驱动） |
| K34（M4） | **卡阈值边界须成对且两侧都被真值库断言**（判定线 = literal 词形 / 排除语境 / 否定辖域，**无数值比较器**） | `gen_cases.py` 的 `form` + `naive_oracle` 边界守卫 | `test_boundary_forms_present_and_paired` 等 |
| K35（M4） | **覆盖声明双登记**（规则包侧 + 真值库侧）；非穷举须有**数值**坐实 | `manifest.benchmark_coverage` + `fixtures/cases.json#coverage` | `test_coverage_declaration_is_double_registered` + `test_coverage_is_numerically_non_exhaustive` |
| K36（M4） | **kind 双层断言在测试面也锁一份**（结构层 + 运行层），与 selftest S5 同源 | 两条 `test_dispatch_*` | 变异 G8/G9（M4 驱动） |
| K37（M4） | **真值形态分布纳入文档漂移门禁** | `data/README.md` §一之二 新增行 | `test_data_readme_form_counts_match` |
| **K38**（M5 新增） | **报告层零判定三条 AST 门禁**：不 import 引擎模块 / 不做算术（豁免模板 `%` 与字符串拼接）/ 不内联政策数值（条款号引用形态 + 百分比阈值形态）；**各配阳性 + 阴性对照** | `selftest.scan_engine_imports` / `scan_arithmetic_binops` / `scan_policy_numeric_literals` + S8/S9/S10 | `test_report_layer_*`（含阴性对照） + 变异 G1/G2/G3 |
| **K39**（M5 新增） | **报告层契约三处对齐**（契约块 + 人读字段表 + 输出字段序）+ **章节声明 ↔ 渲染器 id/序** | `SKILL.md` + `constants.CONTRACT_FIELDS_*` | `tests/test_skill_contract.py` 6 项 + 变异 G4/G5/G6/G13 |
| **K40**（M5 新增） | **批量通路（`scan`）**：逐件渲染 + **读入阶段失败隔离** + 逐件机读走 `render_json`（与单件同形）；**空输入不产出报告**（exit 2） | `report.render_markdown_batch` + `cli.cmd_scan` | `test_scan_*` 5 项 + 变异 G8/G9 |
| **K41**（M5 新增） | **报告必备 8 章节**；两轨（人读单件/人读批量/机读）共用同一 `report_sections()`，章节正文唯一源 `_section_lines()` | `report.py` | `test_mandatory_sections_are_exactly_eight_in_order` + `test_both_tracks_share_the_single_section_source` + 变异 G7 |
| **K42**（M5 新增） | **报告格式要件**：覆盖表的行与「未启用清单」行之间必须留空行（否则 Markdown 吸行） | `report.py::_section_lines` | `test_markdown_coverage_rows_separated_from_not_enabled_line` + 变异 G11 |
| **K43**（M5 新增） | **对外文档红线声明门**："不做药品推荐"须在 `README.md` + `SKILL.md` 明写 | 两份对外文档 | `test_readme_and_skill_declare_no_drug_recommendation` + 变异 G12 |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；代码内入口仍有 `_ensure_utf8_stdio()`（CI 是 cp1252）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）。
5. **Git Bash 下 `$?` 会被管道吃掉**：判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）。**变异验证前先备份**。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）。
8. **改规则/词表必须重跑两个生成器**——`gen_ruleset.py`（版本号变）+ `gen_cases.py`（期望可能变）。
   **M5 未改规则**，故版本号不变（`ruleset-c7c2a6d1fd`）。
9. **`git checkout <file>` 会冲掉未提交改动**：变异验证还原用备份，别用 git checkout。
10. **变异驱动注入前必须 `assert_baseline_clean()`**——异常退出会把文件留在变异态，
    下一轮"备份"即脏状态，"还原"反而固化变异。
11. **变异驱动重生成后必须断言生成器返回 0**——生成器静默抛错会让"门没红"被误判成假门。
12. **`form` 字段进台账摘要**——改 `form` 必须重跑 `gen_cases.py` 并过 `--check`。
13. **改判定模块 docstring 会撞零字面量门禁**——写说明用结构性描述，不引用规则包词面。
14. **改输出字段要同步三处**——`constants.CONTRACT_FIELDS_*` + `SKILL.md` 契约块 + SKILL.md 契约表。
15. **`rm -rf .tmp/clone` 偶发 "Device or resource busy"**——换个目录名或先 `cd` 出该目录再删。
16. **新增生效规则必须同时补 B4 用例**——B4 分母 = 生效规则数，漏补即 `bench` 不达标。
17. **M5 新增坑：浅克隆只含"已提交"内容**——要对最新工作做 CI 检出形态复现，须**先提交**。
    本项目按"交付提交 + 收尾提交"两段走（M4/M5 同形）。
18. **M5 新增坑：抽 pytest 失败行要用 `>` 标记行**——用"含 `assert` 的第一行"会抓到
    traceback 的**上下文行**，把红色原因误读成别的断言（M5 变异驱动实测踩到）。
19. **M5 新增坑：`\d+\s*%` 会误伤 `sha256 %s`**（"256 %" 被当阈值）——阈值形态正则必须排除 `%s`/`%d`。
20. **M5 新增：`.venv-*/` 已进 `.gitignore`**（`git status` 不再冒出里程碑 venv 目录）。
21. **M5 新增坑：渲染层重构必须逐字节对比**——"看着一样"会漏掉空行这类**格式要件**；
    做法：把上一棒的渲染器 `git show <commit>:path` 存到 `.tmp/`，对同一批输入比对输出。

---

## 五、DoD 逐项 checklist（M5）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 5-1 | SKILL.md 主入口定稿（入参表 + 契约块 + 确定性纪律明写） | `SKILL.md` + 两条门禁 | ✅ |
| 5-2 | 文档契约块 ↔ 代码字段常量 ↔ 实际输出字段序 三方对齐 | `tests/test_skill_contract.py`（6 项；含 M5 新增三处） | ✅ |
| 5-3 | 分级报告双轨共用同一 `report_sections()` | `test_both_tracks_share_the_single_section_source` | ✅ |
| 5-4 | 报告必备 8 章节（缺一即断言失败） | `test_mandatory_sections_are_exactly_eight_in_order` + 章节声明门 | ✅ |
| 5-5 | 报告层零判定（AST 门禁） | `selftest` S8/S9/S10 + 阳性/阴性对照 | ✅ |
| 5-6 | 报告含条款锚点 + 原文引用 + 免责声明 + 待补材料清单 | 四要素门 + 免责两轨门 | ✅ |
| 5-7 | `medreview scan` 出 Markdown + JSON 报告（逐件齐备） | `test_scan_markdown_renders_every_item` + `test_scan_json_covers_every_item` | ✅ |
| 5-8 | 免责与红线（强制免责 / 不做药品推荐 / 不引用真实机构案例） | 免责要件门 + 两项白名单门禁 | ✅ |
| 5-9 | 全基准绿 | `bench` exit 0（B1 13 / B2 22 / B3 8 / B4 23） | ✅ |
| 5-10 | 双解释器全量测试 | 3.8 与 3.12 各 **204 passed** | ✅ |
| 5-11 | 冻结产物位级一致（双解释器） | `gen_ruleset/gen_cases --check` → FROZEN_TRUTH_OK | ✅ |
| 5-12 | 门禁自检绿 | `selftest` **10 项** SELFTEST_OK | ✅ |
| 5-13 | **变异验证（守门非假门）** | M5 **13 组**全部使门变红 | ✅ |
| 5-14 | 干净 venv 安装 + 裸 console script + 非仓库根 CWD | `.venv-m5` 内 `selftest` OK、`bench` exit 0、`check` exit 1/0、`scan` exit 1 | ✅ |
| 5-15 | CI 检出形态本地复现 | 浅克隆内 **204 项**绿 + 快照 sha256 3/3 全对 + 冻结产物位级一致 | ✅ |
| 5-16 | `plan/M5-交付复核.md` 已落盘 | 文件 | ✅ |
| 5-17 | `plan/HANDOFF-M6.md` 已落盘 | 本文件 | ✅ |
| 5-18 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径（M5 同 M0–M4）**：5-15 只能写"本地等价校验"，因为 `on: push`
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
py -3.12 -X utf8 -m pytest tests/test_m5_delivery.py -q      # M5 交付面门禁（29 项）
py -3.12 -X utf8 -m pytest tests/test_skill_contract.py -q   # 契约三处对齐（6 项）
py -3.12 -X utf8 -m pytest tests/test_m4_benchmark.py -q     # M4 真值基准门禁（24 项）

# 门禁自检 / 基准
py -3.12 -X utf8 -m medreview.cli selftest      # 10 项，须 SELFTEST_OK
py -3.12 -X utf8 -m medreview.cli bench         # 四套件，须 exit 0
py -3.12 -X utf8 -m medreview.cli rules
py -3.12 -X utf8 -m medreview.cli rules --format json

# 单条审查（人读 / 机读 / 带材料 / 已发布情形）
py -3.12 -X utf8 -m medreview.cli check --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --format json --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --text "<文案>" --proof yes --proof-file ./审查证明.pdf
py -3.12 -X utf8 -m medreview.cli check --text "<文案>" --scenario published

# 批量通路（两种格式；逐件出全 8 章节）
py -3.12 -X utf8 -m medreview.cli scan --dir ./samples --format markdown --out report.md
py -3.12 -X utf8 -m medreview.cli scan --dir ./samples --format json     --out report.json

# 冻结产物重生成与位级守门
py -3.12 -X utf8 tools/make_snapshots.py            # 重新抓快照（需要网络）
py -3.12 -X utf8 tools/gen_ruleset.py               # 重生成规则包/manifest/台账
py -3.12 -X utf8 tools/gen_ruleset.py --check       # 位级一致守门
py -3.12 -X utf8 tools/gen_cases.py                 # 重生成真值库
py -3.12 -X utf8 tools/gen_cases.py --check         # 位级一致守门

# CI workflow 结构守门
py -3.12 -X utf8 tests/check_workflows.py

# 干净环境验证（照 README 那条安装通路）
py -3.12 -m venv .venv-m6
./.venv-m6/Scripts/python.exe -m pip install -U pip
NO_PROXY="*" no_proxy="*" ./.venv-m6/Scripts/python.exe -m pip install -e ".[dev]"
./.venv-m6/Scripts/medreview.exe selftest

# CI 检出形态复现（浅克隆；**只含已提交内容**，先 commit）
rm -rf .tmp/m6/clone && git clone -q --depth 1 --no-tags "file:///<仓库绝对路径>" .tmp/m6/clone

# 变异验证（M5 驱动，**不入仓库**；必须用备份还原，别用 git checkout）
py -3.12 -X utf8 .tmp/m5/mutate.py
```

---

## 七、下一棒启动提示词

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M6.md" 继续完成任务
```