# medreview — 医疗广告合规预审体检

[![CI](https://github.com/yuluo554/10-16-2-medical-ad-review-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/yuluo554/10-16-2-medical-ad-review-skill/actions/workflows/ci.yml)

**状态**：🚧 v0.1.0 开发中（M0 骨架 + M1 数据先行 + M2 品类判定器 + M3 禁止情形核查已完成；M4 真值基准待办）

---

## 这是什么

医疗、医美、药品、医疗器械、保健食品属法定"发布前须经审查"的广告品类。违规发布的代价是罚款、停业整顿乃至吊销执照——对医疗机构、医美机构、代运营公司与 MCN 法务而言，**发布前自查是刚需**。

`medreview` 是一个**发布前辅助自查工具**（不是法律意见）：判断一段推广内容是否构成医疗/药品/器械/保健食品广告，对照禁止性规定逐条做**确定性清单核验**，输出 `BLOCK / WARN / OK` 分级报告，每条结论附条款号锚点与法条原文引用。

**所有判定规则来自冻结的一手法条文本**（禁止情形清单、可发布内容白名单、须审查品类判定）；引擎零 LLM 调用、零第三方依赖、零网络访问。

## 核心特性

| 特性 | 说明 |
|---|---|
| 确定性规则引擎 | 分级结论 100% 由规则产出，可复现、可离线跑 |
| 条款级溯源 | 每条命中含条款号锚点 + 法条原文逐字引用 + 文案命中片段 |
| 四态结论 | `BLOCK` / `WARN` / `OK` / **`NOT_ASSESSED`**（"没检查过"≠"合规"） |
| 待补材料清单 | 判定需外部材料时显式列出缺什么，**绝不静默判合规** |
| 锚点硬门 | 引文核不到原文的规则**拒绝加载**，进"未启用清单"显式报出 |
| **导出前溯源断言** | 每条命中四要素（条款锚点／法条原文／文案证据／规则 id）**导出前常驻校验**：引文必须逐字在快照、证据必须逐字在文案，不满足即**拒绝出件**（不留"半溯源"报告） |
| 纯本地 | 引擎源码零网络导入（AST 静态门禁可核验），文案不外发 |

## 安装

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    POSIX: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

> 注意：Windows 上请用 `python -m pip`（`py -m pip` 会绕过 venv 装进系统 Python）。

## 快速开始

```bash
# 审查单条文案（人读 Markdown 报告）
medreview check --text "XX医疗美容门诊部（虚构）双眼皮手术，保证治愈，无效退款。"

# 机读 JSON 报告（含规则来源 URL，供核证）
medreview check --format json --text "本品保健食品可有效降血糖、降血压。"

# 补材料后重跑（报告"待补材料清单"节索要的材料，用它回传；只记摘要不落路径）
medreview check --text "XX医疗美容门诊部（虚构）双眼皮手术。" --proof yes --proof-file ./审查证明.pdf

# 批量审查一个目录下的全部 .txt 文案（失败件单列，不中断整批）
medreview scan --dir ./samples

# 列出规则包全部条目与锚点（含未启用清单）
medreview rules

# 跑内置基准套件（四套件；退出码 0 达标 / 1 未达标 / 2 用法错误）
medreview bench

# 内建自检（门禁阳性对照 + 装配完整性）
medreview selftest
```

**退出码语义**（已锁进测试，是契约不是巧合）：

| 码 | 含义 |
|---|---|
| `0` | 完成且未命中（`OK` / `NOT_ASSESSED`） |
| `1` | **检出命中**（`BLOCK` / `WARN`）——"查出了问题"的既定语义，**不是故障** |
| `2` | 输入/用法错误 |
| `3` | 规则包不可用 |

## 分级口径

| 结论 | 含义 |
|---|---|
| `BLOCK` | 命中确定性禁止情形（《医疗广告管理办法》§7 任一项、《广告法》§16/§18 任一款、《互联网广告管理办法》§8 变相发布等） |
| `WARN` | 命中白名单外但非明确禁止的表述、语境存疑待人工复核项、**或存在待补材料项** |
| `OK` | 有适用规则且全部通过 |
| `NOT_ASSESSED` | **未评估**：一条适用规则都没有（非涉医内容）。**绝不与 `OK` 合并** |

## 隐私与红线

- **纯本地**：引擎源码零网络导入（静态门禁可核验），不上传用户文案到任何外部服务；
- **不做法律意见**：输出仅为辅助自查参考，不替代广告审查机关的官方审查；
- **不做药品推荐**：不评价任何具体药品/器械/疗法的有效性，不生成推广内容；
- **合成数据**：基准样例一律使用虚构机构名（白名单见 `data/README.md`），不引用真实机构违规案例。

> **免责声明**：本工具输出为发布前辅助自查参考，**不构成法律意见，不替代官方审查**。判定依赖内置冻结规则包（基准日 2026-10-15），法规更新后须重新核对。发布前请以官方审查结论为准。

## 数据来源

首期规则来自以下一手官方全文（基准日 2026-10-15，实测可直连可解析）：

| 法规 | 涉及条款 |
|---|---|
| 《中华人民共和国广告法》 | §16、§18、§46 |
| 《互联网广告管理办法》 | §7、§8 |
| 《医疗广告管理办法》 | §6（白名单 **8 项**，实测勘误见下）、§7 |

> **实测勘误**：《医疗广告管理办法》§6 白名单官方原文为 **8 项**（题面写 7 项，含（八）联系电话）。
> 规则包按实测 8 项建，并作为可校验资产登记（`ruleset.json` 的 `whitelist_items` + 门禁断言"8 项且逐字在原文中"）。

来源 URL、抓取记录与 sha256 台账见 [`data/README.md`](data/README.md) 与 [`data/ledger.csv`](data/ledger.csv)。

合成样例一律使用虚构机构名，白名单见 [`data/fake_org_whitelist.txt`](data/fake_org_whitelist.txt)（基准断言校验样例机构名必须在名单内）。

## 项目结构

```
src/medreview/        引擎（规则加载/判定/分级/报告）
src/medreview/bench/  内置基准套件
src/medreview/references/  冻结规则包（生成物，禁手改）
tools/                生成器与开发期工具（不随包发给用户）
tests/                回归 + 门禁 + 变异验证
plan/                 计划文档与里程碑交接
data/knowledge/raw/   官方全文快照（-text 字节冻结）
```

## 开发

```bash
python -m pytest tests -q              # 全量测试
python tools/gen_ruleset.py --check    # 冻结规则包位级一致守门
python tools/gen_cases.py --check      # 冻结真值库位级一致守门
python tests/check_workflows.py        # CI workflow 结构守门
```

## 已知环境问题

- **底线 Python 3.8**：全部源码按 3.8 语法写（`typing.List` 而非 `list[str]`）；
- **Windows 用 `python -m pip`**：`py` 启动器会绕过 venv 装进系统 Python；
- **规则包是生成物**：请勿手改 `src/medreview/references/*.json`，改需求走 `tools/gen_ruleset.py` 整目录重生成。

## 许可

软件部分 MIT（见 [`LICENSE`](LICENSE)）。`data/knowledge/raw/` 下为法律法规官方公布文本，
仅作规则溯源与逐字核验之用（说明见 LICENSE 的 Data Notice 节）。

## 计划与里程碑

见 [`plan/00-README总览.md`](plan/00-README总览.md)（文档索引、决策记录、承诺-证据台账、里程碑状态）。
