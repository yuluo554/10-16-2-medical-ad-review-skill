# HANDOFF-M1 — 数据先行（下一棒交接）

- **生成时间**：2026-10-15（M0 收尾）
- **上一棒**：M0 计划先行 + 骨架（已完成）
- **下一棒**：M1 数据先行（快照入仓 + 条文块 + 规则包冻结 + manifest + 台账）
- **启动命令**（用户侧，绝对路径）：

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M1.md" 继续完成任务
```

---

## 一、当前进度 + 证据

### 已完成（M0）

| 交付物 | 位置 | 证据 |
|---|---|---|
| 数据底座预检 | `plan/PRECHECK-M0.md` | 三源 HTTP 200 + 字节数 + 汉字数 + 定义位条号数（74/32/23，无重复） |
| 首期条款逐字核验 | `plan/PRECHECK-M0.md` §二 | §16（5 项 + 2 款义务）、§18（6 项 + 1 款义务）、§46、§7/§8、§6（**8 项**）/§7（8 项）全部对上 |
| 实测勘误 | `plan/PRECHECK-M0.md` §三 E-1 → `plan/06` D8 | 题面写 §6 白名单"7 项"，实测**8 项**；规则包按 8 项建 |
| 计划文档 00–06 | `plan/` | 总览/题目/架构/模块详设/数据计划/里程碑/交付对标 |
| 官方快照入仓 | `data/knowledge/raw/*.txt` | 3 份，LF 无 CRLF，sha256 入 `data/ledger.csv` |
| 条文块 + 规则包 + manifest | `src/medreview/references/` | 25 条生效规则 + 3 条兜底条款（显式不建规则） |
| 真值库 | `src/medreview/fixtures/cases.json` | 37 用例（B1×5 / B2×11 / B3×4 / B4×17） |
| 假机构名白名单 | `data/fake_org_whitelist.txt` | 3 个虚构机构名；基准 fail-fast 校验样例机构名（变异验证过） |
| 引擎（13 模块 + bench 包） | `src/medreview/` | 分层：规则/判定/分级/报告/编排 |
| 基准四套件 | `src/medreview/bench/` | **全部达标**（`medreview bench` exit 0） |
| 门禁自检 7 项 | `medreview selftest` | SELFTEST_OK（含阳性对照） |
| 测试套件 | `tests/` | **65 项全绿**（3.8 与 3.12 双解释器） |
| CI workflow（三矩阵） | `.github/workflows/ci.yml` | win 3.8 / win 3.12 / ubuntu 3.12 + workflow-lint job |
| SKILL.md 主入口 | `SKILL.md` | 含机器契约块（三面对账守门已验） |

### 本棒的关键实测发现（写清，避免下一棒重复踩）

1. **题面 §6 项数有误**：题面写"白名单 7 项"，实测官方原文是 **8 项**（含（八）联系电话）。已按实测建规则，勘误登记在 `plan/06` D8——**题面文档不改写**。
2. **"缺材料"不能判 OK**：首版 `grade` 把 `input_required` 当"无命中 → OK"，被生成器的独立 oracle 当场抓出。已改为归入 **WARN** 并在报告独立成节——否则"没查过"会被读成"没问题"。
3. **适用域需要"情形"维度**：《互联网广告管理办法》§7 第 2 款（按审查通过内容发布）原文以"已经审查通过"为前提，只对**已发布**情形生效；发布前自查应判 `skipped` 而非"待补材料"。已引入 `applies_if.scenario`。
4. **摘要实现曾有两份**：`tools/gen_cases.py` 与 `bench/ledger.py` 各算一份用例摘要 → 冻结台账全部报"内容不符"。已收成**包内唯一实现源**，生成器 import 它。
5. **`benchmark/` 放顶层会被漏装**：CLI 的 `bench` 曾 `from benchmark import runner` → `ModuleNotFoundError`。已移入包内 `src/medreview/bench/`，并加守门断言"顶层不得有 benchmark/"。
6. **B4 覆盖曾虚高**：`observed_keys` 含 `rule:skipped:*`，导致"不适用"也算"已覆盖"，删掉覆盖用例也不会红。已排除 skipped（只认"真被判过"）。
7. **零字面量门禁真的抓到东西**：判定模块 docstring 里的领域词（如"养生知识""说明书"）被门禁拦下，已改为不提名（词面只在规则包）。扫描面已明确划分为"判定模块"（严）与"展示/工具模块"（宽）。
8. **报告零外链是常驻断言**：往人读报告里加官方 URL 会被 `assert_no_external_links` 当场拦下——URL 只进机读产物 `rule_sources` 字段。

---

## 二、下一棒待办（M1 数据先行）

M1 的骨架**已经预置完毕**（快照、生成器、规则包、台账都在位）——M1 的工作重心是**深化与验收**，不是从零搭：

1. **复核快照与基准日**：重跑 `tools/make_snapshots.py` 复测三源可获取性；若页面改版则更新基准日并同步 `data/README.md`、`plan/PRECHECK-M0.md`。
2. **扩展规则覆盖面**（当前 25 条 → 目标覆盖首期全部可判定条款）：
   - 《广告法》§16 两款义务的**处方药/非处方药/个人自用器械提示语**目前只建了 1 条（`AL-16-D2`），需按原文补齐 3 条 `mandatory_disclosure`（每组提示语一条）；
   - 《医疗广告管理办法》§6 白名单目前只有 1 条汇总规则（`MAM-6-W`），可考虑按 8 项逐项建 `whitelist_scope`（或明确记录"汇总式覆盖"的决策理由）；
   - 检查 `terms_basis=interpretive` 的 13 条规则，逐条复核词表是否恰当（这些词**不逐字在原文中**，是解释层）。
3. **`data/README.md` 与 manifest 联动**：把 manifest 的 `terms_basis_counts`、`total_rule_count` 等计数与文档对齐（**计数当轮实测，别抄**）。
4. **补 `input_required` 的运行时索取体验**：CLI 可考虑增加 `--proof-file` 之类入参（当前只有 `--proof yes/no`）。
5. **M1 收尾**：写 `plan/HANDOFF-M2.md`，回写 `plan/00`/`05`/`06` 状态。

---

## 三、既定口径清单（K 编号——**动了会打挂测试**）

| 编号 | 口径 | 实现点 | 守门 |
|---|---|---|---|
| K1 | 条款号锚点 + 法条原文 | `references/ruleset.json` | 锚点核不到原文的规则**拒绝加载**（`ruleset.load_ruleset`），进未启用清单 |
| K2 | 退出码 0/1/2/3 | `cli.main` 单一分派 | `tests/test_skeleton.py` 的 6 条端到端断言 |
| K3 | BLOCK/WARN/OK/NOT_ASSESSED 映射 | `grade.grade_results` | `test_grade_priority_block_over_warn` 等 |
| K4 | 判定三态 + `input_required` 第三态 | `check.py` + `constants.RULE_STATES` | 反向样例（`b3_applies_reverse`）+ `test_input_required_never_grades_ok` |
| K5 | 序列化参数（sort_keys + ensure_ascii=False + LF + 尾换行） | `serialize.write_text_atomic` | `test_serialize_lf_and_trailing_newline`、`test_report_json_deterministic` |
| K6 | 基准门槛随 manifest 下发（**代码零默认值**） | `bench/runner.load_thresholds` | 缺门槛 → exit 2；`test_bench_unknown_suite_is_usage_error` 同族 |
| K7 | 对账语义单一实现源 | `bench/cases.compare_case` | 真值库测试与基准共用；`test_truth_case_digest_matches_package_implementation` |
| K8 | 版本号由 manifest 派生 | `medreview/__init__.py` + `manifest.json` | 代码内零版本字面量 |
| K9 | 词面只存在于规则包 | `references/ruleset.json` | 零字面量门禁（`selftest.JUDGMENT_MODULES` 扫描面）+ 阳性对照 |
| K10 | 报告层零判定 + 零外链 | `report.py` | `assert_no_external_links` 常驻断言 + `test_report_markdown_has_no_external_links` |
| K11 | 真值库只存输入与期望（**禁 `observed` 字段**） | `fixtures/cases.json` | `cases.truth_field_violations` 守门 |
| K12 | 基准套件在包内（**不得放仓库顶层**） | `src/medreview/bench/` | `test_face5_bench_is_in_package` |
| K13 | 用例摘要单一实现源 | `bench/ledger.case_digest` | 生成器 import 它（工具内零第二份口径） |
| K14 | `applies_if` 必须落品类 + 可选情形（**不许写 any**） | `ruleset.load_ruleset` 硬门 | 空 categories → 拒绝加载；`test_scenario_gates_clause_7_2` |
| K15 | 契约块 ↔ 代码字段 ↔ 输出字段序 三方对齐 | `constants.CONTRACT_FIELDS_*` + `SKILL.md` | `tests/test_skill_contract.py`（变异验证过） |

---

## 四、本机环境坑（只写实测过的）

1. **两条解释器通道**：`py -0p` → 3.8.8-64 + 3.12-64。**每棒双解释器全量复跑**（3.8 是底线门）。
2. **跑脚本一律 `py -X utf8`**（中文控制台 cp936）；但**代码内入口仍有 `_ensure_utf8_stdio()`**（CI 是 cp1252，本机习惯掩盖缺口）。
3. **`PYTHONDONTWRITEBYTECODE=1` 全程设**（pyc 偶发损坏家族）；跑生成器/测试都加。
4. **`PYTHONPATH=src`** 才能在仓库根跑 `python -m medreview.cli`（未安装态）；装了 `-e .` 则不需要。
5. **Git Bash 下 `$?` 会被管道吃掉**：`cmd | head` 的 `$?` 是 head 的。判退出码要 `cmd > file; echo $?` 或 `${PIPESTATUS[0]}`——本棒实测踩过（`scan` 的 exit 1 被 `head` 掩盖成 0）。
6. **临时产物不放仓库树内**：用 `.tmp/`（已进 `.gitignore`）或系统 tempfile。
7. **pip 装包**：`NO_PROXY="*" no_proxy="*" py -m pip install ...`（系统代理污染）；干净 venv 验证时 `python -m pip install -e ".[dev]"` 秒装（零运行时依赖）。
8. **`.gitattributes` 双半**：源码 `* text=auto eol=lf`；快照 `data/knowledge/raw/** -text`（防 EOL 归一化改字节、sha256 失配）。

---

## 五、DoD 逐项 checklist（M0）

| # | DoD | 证据 | 状态 |
|---|---|---|---|
| 0-1 | 数据底座预检留档 | `plan/PRECHECK-M0.md` §一 | ✅ |
| 0-2 | 首期条款逐字核验 | `plan/PRECHECK-M0.md` §二 | ✅ |
| 0-3 | 骨架猜测被实测勘误并同步（§6 = 8 项） | `plan/PRECHECK-M0.md` E-1 + `plan/06` D8 + `plan/03` §4.2 | ✅ |
| 0-4 | `plan/00–06` 齐全 | `plan/` | ✅ |
| 0-5 | 待定决策表经用户拍板 | `plan/06` §三 P1–P8（按推荐默认执行，**未获逐项答复**，如实留档） | ⬜ 待用户确认 |
| 0-6 | 可运行骨架 | `src/` `tests/` `pyproject.toml` `tools/` | ✅ |
| 0-7 | 双解释器全量测试 | 3.8 与 3.12 各 **65 passed** | ✅ |
| 0-8 | 门禁自检绿（含阳性对照） | `medreview selftest` → SELFTEST_OK（7 项全 PASS） | ✅ |
| 0-9 | 基准四套件达标 | `medreview bench` → exit 0，四套件全"达标" | ✅ |
| 0-10 | 冻结产物位级一致 | `gen_ruleset.py --check` + `gen_cases.py --check` → FROZEN_TRUTH_OK（双解释器） | ✅ |
| 0-11 | 干净 venv 安装 + 裸 console script 冒烟 | `.venv-test` 内 `pip install -e ".[dev]"` → `medreview.exe selftest` OK、65 项测试绿、`bench` exit 0、非仓库根 CWD 跑 `python -m medreview.cli` OK | ✅ |
| 0-12 | CI workflow 结构守门 | `tests/check_workflows.py` → WORKFLOW_LINT_OK | ✅ |
| 0-13 | **本地等价校验（未接远端，CI 待首推验证）** | 上列全部本机通路；**不可本机实跑的 ubuntu 矩阵与 cp1252 环境差异显式标注"待首推验证"** | ✅（等价） |
| 0-13b | **CI 检出形态本地复现**（`git clone --depth 1 --no-tags file:///<abs>`） | 浅克隆内：65 项 pytest 全绿；快照 sha256 与台账逐份一致（`ALL_MATCH`）；`gen_ruleset/gen_cases --check` 均 FROZEN_TRUTH_OK；干净 venv `pip install -e ".[dev]"` + 裸 `medreview bench` exit 0 | ✅ |
| 0-13c | **未建仓的补偿留档** | `plan/06` P1/P2 已如实标注"推荐默认；本对话未执行"（建仓属对外动作，用户要求"不着急直接开始"） | ✅ |
| 0-14 | 变异验证（守门不是假门） | 4 组变异全部使门变红：① 关掉锚点硬门 → `test_rule_with_unresolvable_quote_is_refused` 红；② `input_required` 判 OK → `test_input_required_never_grades_ok` 红；③ 改 SKILL.md 契约块 → 2 项契约测试红；④ 篡改用例 → 冻结台账报红 | ✅ |
| 0-15 | `plan/HANDOFF-M1.md` 已落盘 | 本文件 | ✅ |
| 0-16 | 首提交、工作树干净 | `git log` + `git status` | ✅ |

**CI 诚实口径**：0-13 只能写"本地等价校验"，因为 `on: push` 从未被 GitHub 执行过（**本项目当前无远端**）。M6 首推后据实补记真实 run id。

---

## 六、关键命令速查

```bash
# 环境
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

# 跑测试（双解释器）
py -3.12 -X utf8 -m pytest tests -q
py -3.8  -X utf8 -m pytest tests -q

# 门禁自检 / 基准
py -3.12 -X utf8 -m medreview.cli selftest
py -3.12 -X utf8 -m medreview.cli bench
py -3.12 -X utf8 -m medreview.cli rules

# 单条审查（人读 / 机读）
py -3.12 -X utf8 -m medreview.cli check --text "<文案>"
py -3.12 -X utf8 -m medreview.cli check --format json --text "<文案>"

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
./.venv-test/Scripts/python.exe -m pip install -e ".[dev]"
./.venv-test/Scripts/medreview.exe selftest
```

---

## 七、下一棒启动提示词

```
/goal 读取 "<项目根绝对路径>\plan\HANDOFF-M1.md" 继续完成任务
```
