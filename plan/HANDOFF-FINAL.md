# HANDOFF-FINAL：末态基线 / 发布执行记录 / 复跑手册 / 遗留项

> M6 出口门 = 项目收官门。本文件是本项目的**收官快照**——任何人在任何时间拿到这个仓库，
> 读这一份就能知道"现在是什么状态、怎么复跑、还剩什么没做"。
>
> 生成于 2026-10-17（M6 收棒，**项目终局，无下一棒**；末次实测 HEAD `dd1deee`，run `38997095114` 绿）。库内一律相对路径；
> 发布执行细节见 [`plan/RELEASE-M6.md`](./RELEASE-M6.md)。

---

## 一、发布坐标（末态）

| 项 | 值 |
|---|---|
| 公开仓库 | <https://github.com/yuluo554/10-16-2-medical-ad-review-skill> |
| 可见性 | **PUBLIC**（先 private 跑绿 CI → tag/Release → public，P1 顺序；API 回读确认） |
| Release | `v0.1.0` · <https://github.com/yuluo554/10-16-2-medical-ad-review-skill/releases/tag/v0.1.0> |
| 发布基线提交 | **tag `v0.1.0`**——权威值用 `git rev-list -n1 v0.1.0` 现取（**故意不写死 SHA**：本文件每次改动都会移动 HEAD，写死的 SHA 必然过期；M6 当轮已做过一次 tag 迁移重打） |
| 附件（ASCII 名） | `10-16-2-medical-ad-review-skill-0.1.0-src.zip`（77 tracked 文件 / 998,563 字节 / 确定性构建；含发布留档与收官快照） |
| sha256 留档 | `plan/DIST-sha256-M6.txt`（zip sha256 + 字节数 + 文件数；**自指规避**：zip 内不含本值） |
| topics | 8 个（`medical-advertising` / `compliance` / `agent-skill` / `rules-engine` / `china-regulation` / `deterministic` / `cli` / `offline`），已回读确认 |
| description | 已设（中文一句话定位），`gh api` 回读确认 |

**附件 sha256**（真下载 + 匿名 curl 双链路核对一致）：

```
4ffdb217393ef2ada1a90536e6fdd85ba69649c1561d4f6c839bd301c69a8053  10-16-2-medical-ad-review-skill-0.1.0-src.zip
```

---

## 二、末态基线（全部实测，2026-10-17）

| 项 | 值 | 怎么核 |
|---|---|---|
| 全量测试 | **216 passed**（Python 3.8.8 / 3.12 双解释器各一遍） | `py -3.8 -X utf8 -m pytest tests -q` · `py -3.12 -X utf8 -m pytest tests -q` |
| 规则包 | **30 条生效**（未启用兜底 3 条显式列出），版本 `ruleset-c7c2a6d1fd`（内容哈希派生） | `py -X utf8 -m medreview.cli rules` |
| 基准 | 四套件全达标（B1 13 / B2 22 / B3 8 / B4 23；66 用例，期望锚定冻结真值库） | `py -X utf8 -m medreview.cli bench`（exit 0） |
| 门禁自检 | **10 项** SELFTEST_OK（含报告层零判定三条 AST 门禁 S8/S9/S10） | `py -X utf8 -m medreview.cli selftest` |
| 冻结产物 | `gen_ruleset.py --check` + `gen_cases.py --check` → FROZEN_TRUTH_OK（双解释器） | 见复跑手册 |
| CI | **9/9 run 全 success**（首推 `38993895184` 即 4 job 全绿；收官 run `38997095114`；tag `v0.1.0`→`5a04d43`；9 run = 7 main push + 2 tag push，逐条见 RELEASE-M6 §四） | `gh run list --repo yuluo554/10-16-2-medical-ad-review-skill` |
| 脱敏 | 五步 0 硬门命中（姊妹表述/文件名/内容/二进制/产物 + 提交元数据 noreply） | `py -X utf8 tools/audit_repo.py` → DESENSITIZE_AUDIT_OK |
| 发布物 | 真下载 sha256 对账一致 + 中立目录（无 .git）全量绿 + 解压树重建 zip 与下载件**逐字节一致** | 见 `plan/RELEASE-M6.md` §六 |
| 匿名复核 | 裸 https clone 见 v0.1.0 + curl 下载 sha256 一致 + latest API 可达（无凭据） | `plan/RELEASE-M6.md` §六·八 |

---

## 三、复跑手册（从零到"全绿"的完整命令序列）

> **执行通道**：一律 `py -X utf8`（中文控制台 cp936）；全程 `PYTHONDONTWRITEBYTECODE=1`。

### 3.1 首次上手（干净环境）

```bash
git clone https://github.com/yuluo554/10-16-2-medical-ad-review-skill.git
cd 10-16-2-medical-ad-review-skill
py -m venv .venv                 # 3.8 或 3.12 都可以
.venv\Scripts\activate           # POSIX: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"     # 测试面 = 安装面
python -m pytest tests -q             # 期望 216 passed
medreview selftest                    # 期望 SELFTEST_OK
```

### 3.2 全套守门（每次收尾必跑）

```bash
py -3.12 -X utf8 -m pytest tests -q             # 216 passed
py -3.8  -X utf8 -m pytest tests -q             # 双解释器底线门
py -3.12 -X utf8 -m medreview.cli selftest      # 10 项 SELFTEST_OK
py -3.12 -X utf8 -m medreview.cli bench         # 四套件 exit 0
py -3.12 -X utf8 tools/gen_ruleset.py --check   # FROZEN_TRUTH_OK
py -3.12 -X utf8 tools/gen_cases.py    --check  # FROZEN_TRUTH_OK
py -3.12 -X utf8 tests/check_workflows.py       # WORKFLOW_LINT_OK
py -3.12 -X utf8 tools/audit_repo.py            # DESENSITIZE_AUDIT_OK（浅克隆下显式 INCOMPLETE）
```

### 3.3 发布物复算（不信任台账时）

```bash
# 重建比对（同 tag 树 → 同 zip 字节；解压树/无 .git 也能跑，走文件系统兜底）
py -3.12 -X utf8 tools/make_release.py --verify <下载的.zip> --rev v0.1.0   # ZIP_VERIFY_OK
py -3.12 -X utf8 tools/make_release.py --rev v0.1.0 --out rebuilt.zip       # sha256 应等于台账值
```

### 3.4 免责与红线（复跑时同样适用）

输出为发布前**辅助自查**参考，**不构成法律意见，不替代官方审查**；`check` 退出码
**1 = 检出命中（既定语义，非故障）**；`NOT_ASSESSED` ≠ 合规；待补材料 ≠ 没问题。

---

## 四、本里程碑（M6）关键实测发现（写清，避免复跑者重踩）

1. **审计器自家名必须数据驱动**（README 自指 URL），不能按检出目录名推导——clone 到
   `cleanclone` 时按目录名推导会让自家 badge URL 误报（实测 7 处）；
2. **filesystem 兜底剪枝须含 venv 前缀形态**（`.venv-n`/`.venv-m5` 等里程碑命名 ≠ `.venv`），
   不剪会把整个 site-packages 扫进去（实测 1126 处误报）；
3. **系列名正则的尾部边界**：`…-skill-0.1.0` 的版本后缀会被"系列 token"吞并——下一 token
   须非数字起头；DIST 台账文件名因此误报过；
4. **本机与 CI（都有 `.git`）永远测不出"无 git 形态"缺陷**——发布物本体复核（下载→解压
   中立目录）是唯一暴露面，本轮抓出 4 个（前述 3 个 + 打包测试面假设 git 存在）；
5. **验证产物必须落遍历树外**：`rebuilt.zip` 落树内会被下一轮 filesystem 遍历扫进包，
   "重建不一致"是验证方法缺陷而非打包器缺陷；
6. **tag 迁移重打**（零消费者窗口）：tag 初指的提交缺发布留档/缺陷修复——修完 CI 绿后
   删旧 tag 重打；附件 `--clobber` 重传并**重新真下载复算**；
7. **`gh repo edit --visibility public` 需要 `--accept-visibility-change-consequences`**
   （gh 2.93 新要求）；
8. **tag push 会触发独立一轮 CI**（`on: push` 无 filters）——对账时按 event+ref 区分同 sha 双 run；
9. **tag 删除重建会把 Release 打回 draft**——迁移 tag 后必须 `gh release edit --draft=false`；
   匿名下载随即 404 还叠加**边缘缓存分钟级收敛延迟**（API `state: uploaded` 正常但浏览器
   URL 404）——复验等一分钟或走 `api.github.com` asset 端点（`Accept: application/octet-stream`）。

---

## 五、遗留项（全表清零后的显式跳过，出处见 `plan/RELEASE-M6.md` §九）

| 项 | 状态 | 原因 |
|---|---|---|
| 《医疗美容广告执法指南》扩展包 | 显式跳过 | 一手直连源未定位（D1）；未挂原文核对不得落库/生效 |
| wheel/PyPI 发布形态 | 显式跳过 | P4 定版"仅源码 zip"；README「已知环境问题」已声明 |
| 开源空白检索式发布日复跑 | 显式跳过 | 搜索结论非发布门；原结论带基准日留档（`data/README.md` §三） |
| 交付形态 GUI/exe | 从未承诺 | D5：纯 CLI，源码即交付 |

**无未决事项。** 项目收官；后续如需迭代（新法规入包、扩展品类），从 §3.2 全套守门起步，
改规则/词表须重跑两个生成器（`gen_ruleset.py` + `gen_cases.py`），改输出字段须同步契约三处
（K15），细节见 [`plan/HANDOFF-M6.md`](./HANDOFF-M6.md) §三 K 清单（仍全部有效）。
