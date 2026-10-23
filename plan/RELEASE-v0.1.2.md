# RELEASE-v0.1.2 — 补丁发布：脱敏审计「仓库主人名被误判成姊妹目录名」

> 上一版：`v0.1.1`（2026-10-20）。
> 本版只有**一条**实质改动 + 三组防回退测试；规则集、判定逻辑、基准、报告格式**零改动**。
> 触发来源：轨 I（发布物一致性）的 I-2 —— 复核 SI-024「发布物自带测试失败」时，
> 在**仓库态**跑出 `1 failed / 219 passed`，但同一份 `v0.1.1` 附件解压到中立目录跑出
> `220 passed`。两者矛盾，于是按「哪一侧才是真缺陷」逐层定位。

---

## 一、缺陷与根因

### 症状

| 跑法 | 结果 |
|---|---|
| 仓库态（`D:\ProgramData\zcode\10-16-2-medical-ad-review-skill`） | **1 failed / 219 passed**（`test_audit_full_run_zero_hard_hits`） |
| 同一份 `v0.1.1` 附件解压到中立目录 | **220 passed** |
| 干净 clone（父目录无姊妹仓） | **220 passed** |
| CI | 全绿 |

失败断言原文：

```
AssertionError: 脱敏审计命中 10 处：[('step1_content','LICENSE:3','姊妹目录名 y*******'), ...]
```

10 处命中分布在 `LICENSE:3` / `README.md:3` / `plan/*.md` / `pyproject.toml:14` /
`tests/test_m6_release.py` / `tools/audit_repo.py` —— 全都是**同一个被掩码的 token**。

### 根因（两层，必须一起看）

1. `_sibling_tokens()` 扫**父目录**里的姊妹目录名，收「原名 + 去系列前缀名」两种形态。
2. 工作区里的 profile 仓库目录叫 `10-18-<owner>`（`<owner>` = GitHub 登录名）。
   去前缀后得到的就是 **owner 登录名**，于是它进姊妹 token 集。

而 owner 登录名是**发布坐标本身**：它出现在 README 每一行 badge URL、
`LICENSE` 的版权行、`pyproject.toml` 的 `authors` —— 本该允许。

`_own_names()` 只解析了 `github.com/<owner>/<repo>` 里的 **repo 段**，owner 段被丢弃。

**为什么 CI 一直绿**：CI 检出目录的父目录里没有姊妹仓 ⇒ token 集为空 ⇒ 扫描面为空 ⇒
永远是 PASS。这条缺陷**只在开发机工作区成立**，是「本机红 / 别人绿」而不是「所有人都红」。

---

## 二、改动

`tools/audit_repo.py`：

| 函数 | 改动 |
|---|---|
| `_own_owner()` | **新增**：从 README 自指 URL 推导 owner 登录名（无 URL 时返回空串，不做任何豁免） |
| `_sibling_tokens_from(entries)` | **新增**（从 `_sibling_tokens()` 抽出的纯函数，便于正负对照单测）：`allowed` 集并入 owner |
| `_sibling_tokens()` | 改为薄包装：读父目录条目 → 交给纯函数 |

**为什么不违反「不为让门变绿而放宽门禁」**：改动落在「什么算自家发布坐标」这一侧，
不是「命中几处算过」。可证伪证据是**阳性对照仍在**——见下节第三条测试。

`tests/test_m6_release.py`：新增 3 条守门

| 测试 | 作用 |
|---|---|
| `test_audit_owner_login_is_not_a_sibling_token` | owner 不得进姊妹 token 集；badge URL 形态不得命中 |
| `test_audit_foreign_sibling_still_caught` | **阳性对照**：真姊妹名（运行期拼接，不写字面量）必须仍进 token 集并命中 |
| `test_audit_sibling_tokens_can_be_empty_on_a_neutral_parent` | 父目录无姊妹 ⇒ 空集（CI / 干净 clone 形态） |

---

## 三、防回退实测（两组负控）

| 负控 | 施加方式 | 结果 |
|---|---|---|
| ① 去掉 owner 豁免 | `if owner: allowed.add(owner)` → `pass` | **3 failed**（含 `test_audit_full_run_zero_hard_hits` + 两条新守门） |
| ② 把姊妹检测改瞎 | `_sibling_tokens_from()` 恒 `return []` | **1 failed**（正是阳性对照 `test_audit_foreign_sibling_still_caught`） |
| 恢复 | — | **223 passed**；`tools/audit_repo.py` 直跑 `DESENSITIZE_AUDIT_OK` rc=0 |

②是关键：它证明「把门改瞎」会被抓到，而不是「只要不报错就算过」。

---

## 四、验证

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `py -3.12 -m pytest tests -q` | **223 passed**（v0.1.1 是 220，+3 条新守门） |
| 脱敏审计（仓库态） | `py -3.12 tools/audit_repo.py` | `DESENSITIZE_AUDIT_OK`，rc=0，**0 硬门命中**（修前 10 处） |
| 脱敏审计（解压树） | 解压到中立目录再跑 | 同样 rc=0（行为不变） |

> **测试数 220 → 223** 是本轮唯一会漂的数字。仓内**没有**自指计数守门
> （`grep -rn '220'` 在 CI 与 `tests/` 下 0 命中），故无第二层要同步。

---

## 五、发布物与三方对撞

见 `plan/DIST-sha256-v0.1.2.txt`（tag 树内为**规则版**，不写自身 sha；main 版由发布后回填终值）
与 Release notes。

- 附件：`10-16-2-medical-ad-review-skill-0.1.2-src.zip`
- 打包面 = `git ls-tree` 跟踪面；与 `v0.1.1` 相比**只多/改 3 个文件**
  （`tools/audit_repo.py`、`tests/test_m6_release.py`、`README.md`）+ 新增本文件与 sha 台账

## 六、对历史结论的影响

**本仓的历史审计报告、基准结论、`BLOCK/WARN/OK` 判定结果全部不受影响** ——
改动只在 `tools/`（开发期审计器）与 `tests/`，**不在 `src/`**，运行时判定路径零改动。
故**无需重跑任何历史报告**。
