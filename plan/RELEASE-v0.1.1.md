# RELEASE-v0.1.1 — 二次迭代发布留档（R1–R10）

> 发布日期 2026-10-20 ｜ 目标仓 `yuluo554/10-16-2-medical-ad-review-skill`
> 发布链路沿用 `plan/06-交付对标.md` §六 R1–R10（与 M6 同形）。
> 本文件**不含**附件自身 sha256 之外的发布坐标自指值；附件 sha256 权威值见
> `plan/DIST-sha256-v0.1.1.txt`（main 分支版）与 Release notes。

---

## 摘要

| 项 | v0.1.0（M6） | v0.1.1（本轮） |
|---|---|---|
| 发布范围 | 首版发布 | D1（真值库随包）+ D1 同族（白名单）+ D2（退出码）+ D4（CI 卫生） |
| 提交 | `5a04d43`（tag 指向） | `490fbb3`（tag 指向） |
| 源码 zip | 77 文件 / 998,563 B | **78 文件 / 1,009,977 B** |
| sha256 | `4ffdb217…8053` | `bc9acb9a…6702` |
| 测试 | 216 passed | **220 passed** |
| 未修项 | — | **D3**（license 弃用，硬期限 2027-02-18，须先抬 floor） |

---

## 一、R1 脱敏审计

```bash
.venv-test/Scripts/python.exe tools/audit_repo.py
[audit] 提交元数据邮箱：2827****om
[audit] 结论：PASS（0 硬门命中）
DESENSITIZE_AUDIT_OK            # exit 0
```

发布物本体（解压树、无 `.git`）同样通过：

```bash
$TEMP/mr-extract: python tools/audit_repo.py
DESENSITIZE_AUDIT_OK            # exit 0（no_git 兜底形态）
```

## 二、R2 提交元数据邮箱

```bash
git log --format="%ae %ce" --all | sort -u
282769740+yuluo554@users.noreply.github.com 282769740+yuluo554@users.noreply.github.com
```

唯一值 = GitHub noreply，无需改写。

## 三、R3 干净环境验证

**A. 源码态**（`.venv-test`，Python 3.12.10）

| 命令 | 输出 | 退出码 |
|---|---|---|
| `pytest -o addopts="" -q` | 220 passed in 40.31s | 0 |
| `medreview bench` | `全部套件达标` | 0 |
| `medreview selftest` | `SELFTEST_OK`（S8/S9/S10 三条 `[PASS]`，含阳性+阴性对照） | 0 |
| `medreview rules` | 未启用清单空 | 0 |
| `gen_ruleset.py --check` | `FROZEN_TRUTH_OK` | 0 |
| `gen_cases.py --check` | `FROZEN_TRUTH_OK` | 0 |
| `tests/check_workflows.py` | `PASS ci.yml` + `WORKFLOW_LINT_OK` | 0 |
| `tools/audit_repo.py` | `DESENSITIZE_AUDIT_OK` | 0 |
| `medreview --version` | `medreview ruleset-c7c2a6d1fd` | 0 |

**B. wheel 安装态**（全新 venv，CWD=`%TEMP%`）

| 命令 | 输出 | 退出码 |
|---|---|---|
| `medreview bench` | `全部套件达标`（b1 13 / b2 22 / b3 8 / b4 23） | **0**（v0.1.0 时为 1） |
| `medreview check --text …` | 8 个 `##` 章节，含「八、免责声明」 | 1（检出命中，符合声明语义） |
| `medreview selftest` | `SELFTEST_OK` | 0 |
| `medreview rules` | 空清单 | 0 |
| `medreview --version` | `medreview ruleset-c7c2a6d1fd` | 0 |

负控：删 `site-packages/medreview/fixtures/cases.json` → `bench` **exit 3**；恢复 → exit 0。

## 四、R4 CI 首推（含新 actions 大版本）

| run | head | 事件 | 结果 |
|---|---|---|---|
| `39306288411` | `666ef0c` | push/main | 4 job 全 success（`test×3` + `workflow-lint`） |
| （tag 提交） | `490fbb3` | push/main + push/tag | 两次 run，共 8 个 check-run 全 success |

**D4 目标达成实测**：`gh api …/check-runs/$job/annotations` 回读后，
`Node.js 20 is deprecated … actions/checkout@v4, actions/setup-python@v5` 这条**已不存在**。
仍有一条 `The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026`——
那是 **runner 镜像公告**（`actions/runner-images#14748`），与 action 版本无关，升级无法消除。

## 五、R5 tag + Release

- **annotated tag `v0.1.1`**：指向 = `git rev-list -n1 v0.1.1`（自指表述，不写死 sha）；
  当前指向 `490fbb3`（含 `plan/DIST-sha256-v0.1.1.txt` 的规则版，使 zip 内链接不悬空）。
  > 流程留档：tag 先在 `0dcaed2` 打，发现 README 引用的台账文件不在树内 → 建台账提交
  > `490fbb3` → 删旧 tag → 重打（**零消费者窗口**：当时 Release 尚未创建）。
- **Release `v0.1.1`**：<https://github.com/yuluo554/10-16-2-medical-ad-review-skill/releases/tag/v0.1.1>
  附件 `10-16-2-medical-ad-review-skill-0.1.1-src.zip`（ASCII 名，78 文件）。
- **sha256 台账**：`plan/DIST-sha256-v0.1.1.txt`——tag 树内是**规则版**（不写自身 sha，避免自指），
  main 分支版由本轮回填提交补终值。两版内容不同是**有意为之**。

## 六、R6 发布物本体已验

| 步骤 | 结果 |
|---|---|
| 构建确定性 | 同 rev 两次 `--out` → 同一 sha256 `bc9acb9a…6702`；`--verify` → `ZIP_VERIFY_OK` exit 0 |
| 真下载 | `gh release download v0.1.1` → 1,009,977 B |
| 本地复算 | `sha256 bc9acb9aaa1586e5a16e7dc9fbceb7c5098097a8f03c9c0f330a72ceab3b6702` |
| GitHub digest | `sha256:bc9acb9aaa1586e5a16e7dc9fbceb7c5098097a8f03c9c0f330a72ceab3b6702` |
| **三方一致** | ✅ 构建输出 = 下载件 = Registry digest |
| 解压树跑通 | `pytest tests -q` → **220 passed**；`bench` 达标；`selftest` `SELFTEST_OK`；`audit` `DESENSITIZE_AUDIT_OK`；两个 `--check` 均 `FROZEN_TRUTH_OK`（均无 `.git` 形态） |

## 七、R7 元信息终检

| 项 | 值 |
|---|---|
| description | 未改（本迭代不涉及定位调整） |
| topics | 未改（8 个） |
| Release 附件 | 1 个，`10-16-2-medical-ad-review-skill-0.1.1-src.zip` |
| `isDraft` | `false`（`gh release create` 默认非 draft，回读确认） |
| `isLatest` | 应为 true（v0.1.1 > v0.1.0） |

## 八、R8 发布后匿名复核

无凭据路径（裸 https + 无 `credential.helper`）实测，2026-10-20：

```bash
# ① 匿名 clone（--depth 1，禁用凭据助手）
git -c credential.helper= clone --depth 1 https://github.com/yuluo554/10-16-2-medical-ad-review-skill.git
→ 成功；HEAD = 8fc8ac9

# ② 匿名读 tag
git ls-remote --tags https://… v0.1.1
→ 8914499bbb8e542fe12ea991f9523e5ff0fb23f9  refs/tags/v0.1.1

# ③ 匿名下载附件并复算
curl -sL -o anon.zip https://github.com/…/releases/download/v0.1.1/10-16-2-medical-ad-review-skill-0.1.1-src.zip
→ 1,009,977 B；sha256 bc9acb9aaa1586e5a16e7dc9fbceb7c5098097a8f03c9c0f330a72ceab3b6702（与台账/Release 一致）

# ④ 匿名 clone 树跑通（全新 venv + `pip install -e ".[dev]"`）
medreview bench    → exit 0，全部套件达标
medreview selftest → exit 0，SELFTEST_OK
medreview --version→ medreview ruleset-c7c2a6d1fd
```

> **环境注记**：本机裸 443 直连不通（`curl 28 / Failed to connect … 443`），上述命令经
> `HTTPS_PROXY=http://127.0.0.1:7897` 走通。这是**本机网络**的限制，与发布物无关；
> 但如实记录——"匿名复核通过"的前提是本机有可用出口。

## 九、复核记录（本机实测，2026-10-20）

执行顺序与结果：

1. 源码态全量门禁 → 全绿（220 passed）
2. wheel 构建 + 干净 venv 安装 → `bench` exit 0（D1 修复生效）
3. 删真值库 → `bench` exit 3（D2 修复生效）；删规则包 → `rules` exit 3（对照未回归）
4. push main → CI `666ef0c` 4 job 全绿；注解回读确认 Node20 弃用已消失
5. 建台账提交 `490fbb3` → 重打 tag → 确定性打包（78 文件）
6. 解压树复核（无 `.git`）→ 220 passed + 四门禁全绿
7. `gh release create` → 真下载 → 三方 sha256 一致

## 十、R9 缓议项 / 未验证项全表

| # | 项 | 结论 | 原因 / 出处 |
|---|---|---|---|
| 1 | **D3 license 弃用** | **显式跳过**（硬期限 2027-02-18） | PEP 639 需 setuptools ≥77（要求 Py ≥3.9）；本仓 floor `>=3.8`，3.8 上最高 75.3.4，实测 PEP 639 写法在该版本**构建失败**。修它须先抬 floor（独立批次）。证据见 `update/03-执行记录.md` §五 |
| 2 | 元数据仍有 `SetuptoolsDeprecationWarning` | 已知未修 | 即第 1 项的表征，**不是回归** |
| 3 | 3.8 通道本地完整跑 | **未验证** | 本机无 3.8 venv；仅 CI `test (windows-latest, 3.8)` 绿（CI 侧证据） |
| 4 | `ubuntu-latest` 迁移 Ubuntu 26 后是否仍可跑 | **未验证** | 迁移未落地；注解仍在 |
| 5 | 匿名（无凭据）clone/下载复核 | **已验** | §八：匿名 clone + `ls-remote` 读 tag + `curl` 下载复算 sha256 一致 + clone 树 `bench`/`selftest`/`--version` 全通（经本机代理出口） |
| 6 | 两个生成器共用 `FROZEN_TRUTH_OK` | **显式不处理** | 有意共用（同族"冻结产物位级一致"结论），文档各处已如实写 |

## 十一、R10 README 收尾

| 项 | 状态 |
|---|---|
| 状态行转正 | ✅ `v0.1.1 已发布`（链接指向新 Release） |
| CI badge | ✅ 原有 badge 指向 workflow，无需改 |
| 「下载即用」 | ✅ 指向 v0.1.1 + 新台账 `plan/DIST-sha256-v0.1.1.txt` |
| 「已知环境问题」 | ✅ 已改为「规则包与基准真值库均随包」+ 三条通路实测可用 |

## 十二、改动面（相对 v0.1.0）

```
 .github/workflows/ci.yml         | 17 +++++++---     actions v5/v6 + permissions/concurrency
 README.md                        | 13 +++---         退出码表 / 已知环境问题 / 状态行 / 台账引用
 SKILL.md                         |  2 +-             退出码表
 pyproject.toml                   |  4 ++-            package-data 加 fixtures
 src/medreview/bench/ledger.py    | 24 +++++++++--    白名单取内嵌字段
 src/medreview/bench/runner.py    |  8 +++--          缺真值库 → exit 3
 tests/test_readme_gate.py        | 76 +++++++++++    wheel package-data 双侧守门
 tests/test_skeleton.py           | 43 ++++++++++     白名单漂移/权威性 + exit 3 端到端
 tools/make_release.py            |  2 +-             FIXED_DATE_TIME → 2026-10-20
 plan/DIST-sha256-v0.1.1.txt      | 新文件            发布物台账
```

**零改动**：`check.py` / `grade.py` / `categorize.py` / `normalize.py` / `phrase.py` / `report.py`；
`src/medreview/references/*.json`、`src/medreview/fixtures/cases.json`（两个 `--check` 均 `FROZEN_TRUTH_OK`）；
`selftest` 的 S8/S9/S10 三条 AST 门禁（仍 `[PASS]`，含阳性+阴性对照）。
