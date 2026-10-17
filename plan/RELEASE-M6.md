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

（发布后回填：建仓命令、首推、run 对账表——每行 `run id` × `head_sha` × `conclusion`。）

## 五、tag + Release（R5）

（发布后回填：annotated tag 指向（`git rev-list -n1 v0.1.0` 自指表述）、Release 创建
与 `--verify-tag`、附件 ASCII 名、sha256 记 `plan/DIST-sha256-M6.txt`。）

## 六、发布物本体已验 + 匿名复核（R6/R8）

（发布后回填：真下载 → sha256 对账 → 中立目录解压跑冻结态自检；无凭据 clone/下载/读 tag。）

## 七、元信息终检（R7）

（发布后回填：description / topics 回读 / release assets / `isDraft=false` / 可见性切换。）

## 八、缓议项清零（R9）

（发布后回填：P1–P8 逐条全表——结论 = 结案 / 显式跳过 + 原因 + 出处。）
