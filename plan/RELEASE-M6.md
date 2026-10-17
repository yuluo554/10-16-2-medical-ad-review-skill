# plan/RELEASE-M6.md — 发布留档（M6 脱敏发布）

> 项目：`10-16-2-medical-ad-review-skill`（医疗/医美广告合规预审体检 Skill）
> 版本：v0.1.0 · 发布日：2026-10-17 · 仓库：<https://github.com/yuluo554/10-16-2-medical-ad-review-skill>
> 口径纪律：CI 类结论**只记实测到的**；"首跑失败"与"修复提交"成对留档，不遮掩、不回填美化。
> **自指规避**：本文件被打进附件 zip 且位于 tag 树内——附件自身 sha256、tag 指向 sha
> 均不在本文件写死（写入即自指），权威口径见 `plan/DIST-sha256-M6.txt` 与 Release notes。

---

## 一、干净环境验证（R3）

**结论：通过（下表 19 条命令退出码全部符合明示语义）。** 形态：新目录 clone（`--no-local`）+
全新 venv（Python 3.12；README 安装通路）+ 逐条执行。

| # | 命令（README/开发节原文形态） | 退出码 | 语义判定 |
|---|---|---|---|
| 1 | `python -m pytest tests -q` | 0 | **216 passed** 全量绿 |
| 2 | `medreview selftest` | 0 | SELFTEST_OK（裸 console script 通路） |
| 3 | `medreview check --text "<命中文案>"` | **1** | **检出命中 = 既定语义，非故障**（K2） |
| 4 | `medreview check --text "<中性文案>"` | 0 | OK / NOT_ASSESSED 未命中 |
| 5 | `medreview check --format json --text "…"` | **1** | 机读命中，同上 |
| 6 | `medreview check … --proof yes --proof-file ./审查证明.pdf`（文件不存在） | **2** | 输入/用法错误，契约语义 |
| 7 | `medreview scan --dir ./samples --format markdown --out report.md` | **1** | 批量含命中件，整批 exit 1 |
| 8 | `medreview scan --dir ./samples --format json --out report.json` | **1** | 同上 |
| 9 | `medreview rules` | 0 | 规则包加载 + 展示 |
| 10 | `medreview bench` | 0 | 四套件全达标 |
| 11 | `medreview check`（缺参） | **2** | 用法错误，契约语义 |
| 12 | `medreview check --text "   "`（空文案） | **2** | 用法错误，契约语义 |
| 13 | `python tools/audit_repo.py` | 0 | DESSENSITIZE_AUDIT_OK |
| 14 | `python tools/gen_ruleset.py --check` | 0 | FROZEN_TRUTH_OK |
| 15 | `python tools/gen_cases.py --check` | 0 | FROZEN_TRUTH_OK |
| 16 | `python tests/check_workflows.py` | 0 | WORKFLOW_LINT_OK |
| 17 | `python tools/make_release.py --rev HEAD --out …` | 0 | ZIP_BUILD_OK |
| 18 | `python tools/make_release.py --verify …` | 0 | ZIP_VERIFY_OK |
| 19 | `medreview scan --dir <空目录>` | **2** | 无输入源不产出空报告，契约语义 |

**CI 检出形态本地复现**（`--depth 1 --no-tags` 浅克隆 + 全新 venv）：**216 passed** +
`selftest` OK + 冻结产物位级一致（双 `--check` OK）。浅克隆下 `audit_repo.py` 按设计显式
报 INCOMPLETE（exit 2，"提交元数据检查：浅克隆只见 1 提交"）——**不冒充"历史已验"**；
CI 侧 `fetch-depth: 0` 提供完整历史走全量审计。

**本轮干净环境/检出复现实测抓出并修复的缺陷（4 个，均非推测）**：
1. **审计器自家名按检出目录名推导** → clone 到任意目录名时自家 badge URL 误报
   （实测：cleanclone 下 7 处误报）→ 改**数据驱动**（README 自指 URL）；
2. 审计器 selftest 自家名变体表未随数据驱动对齐 → clean clone 下 selftest AssertionError → 修；
3. 系列名正则把**版本后缀**（`…-skill-0.1.0`）并进系列 token → DIST 台账文件名误报 →
   尾部边界收紧（下一 token 须非数字起头）；
4. 全量审计门不接受"浅克隆显式 INCOMPLETE"状态 → CI 检出形态复现实测抓出 → 门放宽到
   三态白名单（ok / no_git / shallow），**不是**把浅克隆静默当通过。

## 二、脱敏五步 + 提交元数据邮箱（R1/R2）

**结论：五步 0 硬门命中。** 固化为入仓工具 `tools/audit_repo.py`（判据运行时实算，
自家名数据驱动；输出掩码化；扫描面非空自证；浅克隆显式 INCOMPLETE 不静默空扫）。

| 步 | 内容 | 命令 | 结论 |
|---|---|---|---|
| 1 | 姊妹表述处置 | `py -X utf8 tools/audit_repo.py`（第 1 步：系列名形态 + 工作区姊妹 token 运行时实算） | 0 命中：全仓姊妹均为**方向级描述**（`plan/01`/`plan/06` 品牌隔离划界声明），0 处姊妹项目名（D36） |
| 2 | 跟踪文件名扫描 | 同上（第 2 步：.env/.key/secret/token/password/credential） | 0 命中 |
| 3 | 全文本内容扫描 | 同上（第 3 步：邮箱/密钥形态/手机号/身份证/本机绝对路径；noreply 豁免） | 0 命中（71 个文本文件） |
| 4 | 二进制样本扫描 | 同上（第 4 步：ASCII + UTF-16LE 双编码） | 0 个二进制跟踪文件（预期） |
| 5 | 构建产物扫描 | 同上（第 5 步：缓存/打包元数据/dist/大文件复核 + 忽略面简报） | 0 命中；最大文件 70,723 字节（clauses.json） |
| R2 | 提交元数据邮箱 | `git log --format="%ae %ce" --all \| sort -u` | 唯一值 = GitHub noreply（`282769740+yuluo554@users.noreply.github.com`），**无需改写历史** |

**产物扫描**：发布物 = 纯源码 zip（无 exe/dist），打包面 = git 跟踪面（`tools/make_release.py`
门禁断言"不多不少"）；未跟踪杂项（`.tmp/`、`.venv-*/`）天然排除（.gitignore 覆盖）。

## 三、git 三连核对（R4 前置）

- `git status`：clean（无未提交改动）；
- `git log --oneline`：线性历史至 M6 发布基线，各里程碑一笔；
- `git rev-list --count HEAD`：与工作树一致（无"历史落后于工作树"漂移）。

## 四、建仓 + 首推 + CI（R4）

**建仓**：`gh repo create yuluo554/10-16-2-medical-ad-review-skill --private --description …`
（**先 private**，按 plan/06 P1 推荐默认）→ `git remote add origin git@github.com:…`（**SSH**；
gh token 无 workflow scope，HTTPS 推含 workflow 改动的提交会被拒——ad-copy 同系列实录）→ 首推一次成。

**CI 实录（push↔run 逐条对账，`gh run list` 实测）**：

| run id | head_sha | event/ref | conclusion | 说明 |
|---|---|---|---|---|
| 38993895184 | `e977e8c` | push/main | **success（4 job）** | **首推全绿**：win 3.8 + win 3.12 + ubuntu 3.12 + workflow-lint（首跑即绿，未用诊断轮预算） |
| 38994143153 | `e977e8c` | push/v0.1.0（tag，后删） | success | 实测 tag push 触发独立一轮（`on: push` 无 filters） |
| 38994583216 | `c7c4bc2` | push/main | success | 发布物本体复核轮 1 修复（venv 剪枝 + no-git 兜底） |
| 38994796787 | `c7c4bc2` | push/v0.1.0（tag，迁移前） | success | 同提交 tag 轮 |
| 38995147018 | `2572ccf` | push/main | success | 本体复核轮 2 修复（测试面导出树形态） |
| 38995855247 | `5a04d43` | push/main | success | M6 收官（发布留档回填 + HANDOFF-FINAL）；**tag 迁移至此提交** |

（后续收尾回填提交各产生 1 个 main run——快照非终值；可复跑规则：
`gh api repos/yuluo554/10-16-2-medical-ad-review-skill/actions/runs --jq '.total_count'`
等于该仓收到的 push 事件数。）

## 五、tag + Release（R5）

- **annotated tag `v0.1.0`**：指向 = `git rev-list -n1 v0.1.0`（自指表述，不写死 sha）；
  tag 注释记发布基线提交、CI run id、内容清单与免责口径。
- **迁移重打**（零消费者窗口内，ad-copy 同系列同形态）：tag 初指 `e977e8c` → 本体复核实测
  抓出 2 个发布物级缺陷 → 修复（`c7c4bc2`）→ 删旧 tag → 在含修复的提交重打（本轮再修
  测试面 2 处于 `2572ccf`，见 §六）。迁移后核验：`git cat-file -e v0.1.0:tools/audit_repo.py` 成功。
- **Release**：`gh release create v0.1.0 <zip> --verify-tag --notes-file`；
  附件 `10-16-2-medical-ad-review-skill-0.1.0-src.zip`（**ASCII 名**；终版 77 文件，含发布留档与收官快照——tag 指向 M6 收官提交 `5a04d43`，发布留档/台账/收官快照均在 tag 树内）；
  `gh release edit v0.1.0 --draft=false` 转正后 `isDraft=false`（API 回读实测）。
- **sha256 台账**：`plan/DIST-sha256-M6.txt`（**自指规避**：zip 内不含本值，台账随发布后
  回填提交落 main；zip 内只写复算规则）。

## 六、发布物本体已验（R6）

**真下载链路（两轮，含一轮真缺陷，如实留痕）**：

1. `gh release download v0.1.0` 真下载 → sha256 复算**与构建值一致** → `testzip()` 无损坏 →
   解压**中立目录**（树外、无 `.git`）→ venv 安装 → `selftest` OK / `bench` exit 0 /
   `check` exit 1（命中，既定语义）。
2. **第一轮抓出 2 个真实缺陷**（本机与 CI 都有 `.git`，永远测不出；只有"下载→解压→
   无 git 中立目录"才暴露——mcp 同系列同形态实录）：
   - 审计器 filesystem 兜底不剪**里程碑命名 venv**（`.venv-n` ≠ `.venv`）→ 1126 处误报；
   - 打包测试面 4 处假设 `.git` 存在 → 导出树必红。
   修复：前缀剪枝 + `--verify` 导出树显式 exit 2 + `HEAD` 无 git 自动降级 + 测试双形态断言。
3. **第二轮**：删旧 tag/附件 → 修复提交（`c7c4bc2`）CI 绿 → 迁移重打 tag → 重建附件（终版 tag 再迁移至收官提交 `5a04d43`，使发布留档/台账/HANDOFF-FINAL 均在 tag 树内）
   （`--clobber`）→ 真下载复算 sha256 一致 → 干净解压树全量绿（`audit` OK、`pytest` 剩余
   2 处测试面假设已修，修复提交 `2572ccf` CI 绿）。
4. **同源证明**：从下载件解压树重建 zip（`tools/make_release.py --out`，无 git 兜底）→
   sha256 **与下载件逐字节一致**（`8d991723…`）——打包面 = 下载树同源的正面证明。

**纪律补记（本轮实测）**：验证产物（`rebuilt.zip` 等）**必须落遍历树外**——落树内会被
下一轮文件系统遍历扫进包，"重建不一致"是验证方法缺陷而非打包器缺陷。

## 七、元信息终检（R7）

- `gh repo view` 回读：description（中文一句话定位）、visibility；
- topics：`gh repo edit --add-topic` 后 `gh api` 回读确认；
- release assets：`10-16-2-medical-ad-review-skill-0.1.0-src.zip` 在列；
- `isDraft=false`、`isPrerelease=false`（API 回读实测）；
- **可见性**：CI 三矩阵全绿 + 发布三件套齐后 `gh repo edit --visibility public`（P1 顺序纪律），
  API 回读 `visibility=PUBLIC`。

## 八、发布后匿名复核（R8）

**无凭据路径全部实测通过**（裸 https + curl，零凭据）：

| 检查 | 结果 |
|---|---|
| `git clone https://github.com/…`（无凭据） | 成功；`git rev-list -n1 v0.1.0` = `5a04d43`（收官提交） |
| tag 树内容 | `plan/RELEASE-M6.md` / `plan/DIST-sha256-M6.txt` / `plan/HANDOFF-FINAL.md` 均在 tag 树内（API `?ref=v0.1.0` 回读） |
| 匿名下载（release download URL + API asset 端点双路） | 均 998,563 字节，sha256 `4ffdb217…` **与台账一致** |
| `releases/latest` API | `"tag_name": "v0.1.0"`、`"draft": false`、release 页 HTTP 200 |

**实测坑（记下）**：tag 删除重建后 Release 自动回到 **draft** 态 → 匿名下载 404
（`browser_download_url` 404，`state: uploaded`、`draft:false` API 均正常）——两件事：
① 必须 `gh release edit v0.1.0 --draft=false` 重新转正；② 边缘缓存收敛有分钟级延迟，
复验时若 API 正常而浏览器 URL 404，等一分钟或走 `api.github.com` asset 端点
（`Accept: application/octet-stream`）再验。

## 九、缓议项清零（R9）

| 项 | 原状态 | 结案 | 依据 |
|---|---|---|---|
| P1 仓库可见性 | 推荐默认；未执行 | ✅ 按"先 private 跑绿 CI，再切 public"执行 | 本文件 §七（`gh repo edit --visibility public` + API 回读） |
| P2 建仓时机 | M0 即建 / 推迟 M6 | ✅ 实际推迟到 M6（用户"不着急"）；补偿措施（每棒 CI 检出形态本地复现）全程执行且本轮兑现 | `plan/00` §二 + 本文件 §一；首推即绿证明补偿有效 |
| P3 版本号 | v0.1.0 | ✅ 结案 | 本文件 §五 |
| P4 发布物形态 | 仅源码 zip | ✅ 结案（76 文件确定性 zip + sha256 台账） | 本文件 §五/§六 |
| P5 医美执法指南扩展项 | 扩展项 | ✅ 显式跳过（一手直连源未定位，未挂原文不落库） | `plan/06` D1 + `data/README.md` §二.3 |
| P6 真值样例规模 | 每规则 ≥2 例 + 边界类 | ✅ 结案（66 用例：positive 50 / reverse 8 / threshold_exact 3 / near_miss 5） | `data/README.md` §一之二（计数门禁锁定） |
| P7 报告法条原文口径 | 仅引用命中项原文 | ✅ 结案（`quote` 逐字在快照 + 四要素导出前断言） | K28 + `plan/03` §四.3 |
| P8 词表规模 | 最小可判定集 | ✅ 结案（literal 16 / interpretive 14，宁缺勿造） | `data/README.md` §一之二 |
| CI 诚实口径（M0–M5"本地等价校验"） | 未接远端 | ✅ 已据实补记真实 run id（本文件 §四）；历史文档保留原措辞，补记为追加事实 | `plan/05` 诚实口径节 |
| 开源空白软论据 | ⬜（2026-10-15） | ✅ 发布日未复跑检索式（跳过原因：搜索结论非发布门，且 D36 已锁定方向级表述）；维持原结论 + 基准日标注 | `data/README.md` §三 |

## 十、CI 诚实口径回填（M0–M5）

历史 DoD 写"本地等价校验（未接远端，CI 待首推验证）"的项，据实补记：**首推 run
`38993895184`（`e977e8c`）三矩阵 + workflow-lint 四 job 全绿**；截至 `2572ccf` 全部
5 轮 push run 均 success（逐条见 §四对账表）。历史文档（`plan/05` 各 DoD 节脚注）
保留原措辞——补记是**追加事实**，非回填美化。
