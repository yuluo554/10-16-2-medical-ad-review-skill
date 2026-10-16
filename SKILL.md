---
name: medical-ad-review
description: 医疗/医美/药品/医疗器械/保健食品广告的发布前合规预审体检。判断一段推广内容是否构成医疗类广告、对照禁止性规定逐条做确定性清单核验、输出 BLOCK/WARN/OK 分级报告（每条结论附条款号锚点与法条原文引用）。当用户要"审一段医疗/医美广告文案""自查保健品宣传是否违规""检查药品/器械推广能不能发""发布前合规体检"时使用。纯本地运行，不上传文案。
---

# 医疗广告合规预审（medical-ad-review）

## 定位

**预审式体检工具，不是法律意见。** 判断内容是否构成医疗/医美/药品/器械/保健食品广告、命中哪条禁止性规定、给出 `BLOCK/WARN/OK` 分级报告。

所有判定规则来自**冻结的一手法条文本**（禁止情形清单、可发布内容白名单、须审查品类判定）。**结论只能由确定性规则产出**——本 Skill 不自行发明规则、不拍脑袋下结论。

## 何时使用

- 医疗机构/医美机构/代运营公司/MCN 法务在内容发布前做自查；
- 需要判断某段推广内容是否落入"发布前须经审查"的品类；
- 需要逐条核对《医疗广告管理办法》§7 禁止情形、《广告法》§16/§18、《互联网广告管理办法》§7/§8。

**不适用**：不评价任何具体药品/器械/疗法的有效性（不做药品推荐）；不代办广告审查证明；不出具法律意见。

## 怎么用

引擎是纯本地 CLI（零第三方依赖、零网络访问）。所有结论由 `medreview` 命令产出。

```bash
# 1) 审查单条文案（人读 Markdown 报告，打印到 stdout）
medreview check --text "<待审查文案>"

# 2) 机读 JSON（含条款锚点、法条原文、规则来源 URL）
medreview check --format json --text "<待审查文案>"

# 3) 带元信息与语境提示
medreview check --text "<文案>" \
  --channel "小红书" --subject medical_aesthetic \
  --proof no --scenario prepublication \
  --hint "<宿主 agent 的语境判断>"

# 3b) 补材料后重跑（报告"待补材料清单"节要求的那份材料，用它回传）
medreview check --text "<文案>" --proof yes --proof-file ./审查证明.pdf

# 4) 批量审查一个目录下的全部 .txt
medreview scan --dir ./samples --format json --out report.json

# 5) 查看规则包条目与锚点（含未启用清单）
medreview rules
```

## 退出码（契约，不是巧合）

| 码 | 含义 |
|---|---|
| `0` | 完成且未命中（`OK` / `NOT_ASSESSED`） |
| `1` | **检出命中**（`BLOCK` / `WARN`）——"查出了问题"，**不是执行失败** |
| `2` | 输入/用法错误（缺文案、坏格式、未知子命令） |
| `3` | 规则包不可用（缺锚点、锚点核不到原文、manifest 缺失） |

## 输入契约

| 入参 | 必填 | 说明 |
|---|---|---|
| `--text` / `--text-file` | 二选一 | 待审查文案 |
| `--channel` | 否 | 发布渠道（元信息，不参与判定） |
| `--subject` | 否 | 主体类型（元信息） |
| `--scenario` | 否 | `prepublication`（默认，发布前自查）/ `published`（已发布） |
| `--proof` | 否 | 审查证明：`yes` / `no` / 未提供。**`no` → 无条件义务缺失 → BLOCK** |
| `--proof-file` | 否 | 审查证明/许可材料文件。只把**文件名 + sha256 + 字节数**记进报告（不落路径）；实质核验仍以原件为准 |
| `--hint` | 否 | 语境提示（**只进报告 advisory 分节，永不改结论**） |

## 结论语义（四态，务必按此解读）

| 结论 | 含义 | 该怎么做 |
|---|---|---|
| `BLOCK` | 命中确定性禁止情形 | 必须修改后才能发布 |
| `WARN` | 白名单外表述 / 语境存疑 / **存在待补材料项** | 人工复核；补齐材料后重跑 |
| `OK` | 有适用规则且全部通过 | 注意报告头部的"本次适用规则数/总条目数"覆盖面 |
| `NOT_ASSESSED` | **一条适用规则都没有**（非涉医内容） | **"没检查过"≠"合规"**，不要当成通过 |

**报告"待补材料清单"节必须逐条处理**：那表示"这条判不了"，不是"这条没问题"。

## LLM 的角色（重要）

本 Skill 的引擎**零 LLM 调用**。宿主 agent（你）的职责是：

1. 读用户给的文案与背景，判断它属于哪类内容、有没有"以健康养生知识形式变相发布"这类隐性话术；
2. 把你的语境判断通过 `--hint` 传入——它**只进报告 advisory 分节，不参与任何分级计算**；
3. 把 CLI 的输出解读给用户，并**如实转述** `NOT_ASSESSED` 与"待补材料"的含义。

**绝对不要**：不要自己给 `BLOCK/WARN/OK` 结论（那是规则引擎的唯一职责）；不要绕过 CLI 直接"凭感觉"判断；不要把 `NOT_ASSESSED` 说成"没问题"。

## 输出契约（机器可解析）

<!-- contract-fields: id text channel subject hint proof scenario proof_file categories grade findings applied_rule_count total_rule_count not_enabled advisories input_required ruleset_version rule_sources rule_id clause_anchor quote evidence severity kind notes -->

`medreview check --format json` 的顶层字段（顺序即输出顺序）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `item.id` | string | 内容 ID（原文 sha256 前 12 位，确定性） |
| `item.text` | string | 原文（逐字保留） |
| `item.channel` / `item.subject` / `item.hint` / `item.proof` / `item.scenario` | string\|null | 入参回显 |
| `item.proof_file` | object\|null | 证明材料摘要：`name` / `sha256` / `bytes`（**只记摘要不落路径**） |
| `grade` | enum | `BLOCK` / `WARN` / `OK` / `NOT_ASSESSED` |
| `categories` | string[] | 命中的品类（可能多个，不二选一） |
| `findings` | object[] | 逐条命中：`rule_id` / `clause_anchor` / `quote` / `evidence` / `severity` / `kind` |
| `input_required` | object[] | **待补材料清单**：`rule_id` / `reason` |
| `not_enabled` | object[] | 未启用规则清单（不参与判定）：`rule_id` / `reason` / `code` |
| `advisories` | object[] | 语境提示（不参与分级） |
| `applied_rule_count` / `total_rule_count` | int | 覆盖面 |
| `ruleset_version` | string | 规则包版本（由 manifest 派生） |
| `rule_sources` | object[] | 每条规则的法规名/条款锚点/官方 URL/基准日 |

`findings` 的每条**四要素齐备**：`clause_anchor`（条款号锚点）、`quote`（法条原文逐字）、`evidence`（文案命中片段逐字）、`rule_id`。

## 隐私红线

- 引擎源码**零网络导入**（AST 静态门禁可核验），文案**纯本地处理、不外发**；
- 人读报告零外链（断网可开）；官方来源 URL 只出现在机读产物的 `rule_sources` 字段。

## 免责

输出为发布前**辅助自查**参考，**不构成法律意见，不替代广告审查机关的官方审查**。判定依赖内置冻结规则包（基准日见 `medreview check` 报告头部），法规更新后须重新核对。发布前请以官方审查结论为准。
