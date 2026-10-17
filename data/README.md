# data/README.md — 依据查证与数据纪律

基准日：**2026-10-15**（所有三态判定与可获取性记录均以此日为准）。
**M1 复测**：2026-10-16 以 `tools/make_snapshots.py` 的同一抓取路径重测三源，
**三份快照逐字节一致**（字节数 32858 / 16130 / 7413 与入仓件完全相同），
故基准日维持 2026-10-15 不变（见 §二.4 复测记录）。

## 一、一手法条源查证记录（三态）

| 法条 | 涉及条款 | 状态 | 一手 URL（实测 samr.gov.cn 可直连可解析） |
|---|---|---|---|
| 《中华人民共和国广告法》 | §16（医疗/药品/器械广告禁止内容 + 药品与器械的**显著标明义务**）、§18（保健食品广告禁止内容 + 显著标明义务）、§46（医疗广告审查要求：发布前须取得审查证明） | ✅ | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_5474cf75173c45d6a0379730fb4e8d97.html |
| 《互联网广告管理办法》 | §7（须审查品类的发布要求；第 2 款"按审查通过内容发布"）、§8（禁止以健康养生知识等形式变相发布医疗广告）；全文 32 条 | ✅ | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_d93a579afd45413e8576e4623fab348f.html |
| 《医疗广告管理办法》 | §6（可发布内容白名单：医疗机构第一名称/地址/所有制形式/类别/诊疗科目/床位数/接诊时间/联系电话 **8 项**）、§7（**8 类**禁止情形，第（八）项为兜底） | ✅ | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ggjgs/art/2023/art_6584dc1c94c2408db7c73f0b5e3d225a.html |
| 《医疗美容广告执法指南》 | 全文 | ⬜ 未定位到一手直连源，需 M1 用浏览器检索市场监管总局官网落地；落地前不落库、不进入首期 | — |

> **§6 项数勘误**：题面写"白名单 7 项"，实测官方原文为 **8 项**（含（八）联系电话）。
> 规则包按 8 项建、8 项作为结构化数据登记（`ruleset.json` 的 `whitelist_items`），
> 题面文档不改写，勘误登记在 `plan/06` D8。M1 已把该 8 项落成**可校验资产**：
> `tests/test_m1_semantics.py::test_whitelist_items_are_eight_and_verbatim` 断言
> "项数 == 8 且每项逐字在 §6 快照中"。

三态口径：✅ = 已实测一手直连源可访问且可解析；⬜ = 未定位/待落地；❌ = 已证不可得（本题暂无）。

**纪律**：M1 冻结法条规则包时，每条规则须挂上述一手原文（条款号 + 原文文本 + URL + 基准日），**未挂原文核对不得落库/生效**。法条更新须重新核对并更新基准日。

## 一之二、冻结规则包计数（M4 当轮实测，非抄上一棒）

| 计数项 | 实测值 | 出处（单一实现源） |
|---|---|---|
| 规则包版本 | `ruleset-c7c2a6d1fd` | `references/manifest.json` `ruleset_version`（由内容哈希派生，K8；**M2 起指纹含品类/变相发布词表**） |
| 生效规则数 | **30** | `manifest.enabled_rule_count` == `medreview rules` 实算 |
| 未启用兜底条款数 | **3** | `manifest.excluded_clause_count`（§16（五）/§18（六）/§7（八）） |
| 总条目数 | **33** | 生效 30 + 兜底 3 |
| 白名单登记项数 | **8** | `manifest.whitelist_item_count` == `ruleset.whitelist_items` 长度 |
| 词表溯源分级 | literal **16** / interpretive **14** | `manifest.terms_basis_counts` == 逐条实算 |
| 品类条目数 | **5** | `manifest.category_rule_count` == `ruleset.category_rules` 长度 |
| 品类信号词数 | medical 18 / drug 13 / device 11 / health_food 6 / fsmp 3 | `manifest.category_signal_counts` == 逐条实算 |
| 品类反例结构数 | medical 5 / drug 4 / device 6 / health_food 2 / fsmp 1 | `manifest.category_exclude_counts` == 逐条实算 |
| 变相发布信号条数 | **2**（§8 两款各一条） | `manifest.variant_rule_count` == `ruleset.variant_rules` 长度 |
| 真值用例数 | **66**（B1×13 / B2×22 / B3×8 / B4×23） | `fixtures/cases.json` 内置台账 `ledger.count` |
| 真值形态分布 | positive **50** / reverse **8** / threshold_exact **3** / near_miss **5** | `fixtures/cases.json` `coverage.by_form` == 逐条实算 |

> **M4 新增计数行**：真值用例数随边界类用例补齐由 58 → **66**（B2 由 14 → 22，
> 新增 3 组"卡阈值边界"成对用例）；真值形态分布是 M4 引入的**形态轴**登记
> （plan/03 §6.2 的 `threshold_exact` / `near_miss` 边界类落地）。
> 两行均纳入漂移门禁：`test_m2_semantics.py::test_data_readme_counts_match_manifest`
> 守用例数，`test_m4_benchmark.py::test_data_readme_form_counts_match` 守形态分布。

> 计数**当轮实测**（`medreview rules --format json` + 逐条实算），并已锁门：
> `tests/test_m1_semantics.py::test_manifest_counts_match_actual_rules` 断言规则类计数、
> `tests/test_m2_semantics.py::test_manifest_category_counts_match_actual` 断言品类类计数，
> 均与规则包实算数一致（改了数据不更新 manifest 即红）。
> **M2 新增**：`test_ruleset_version_fingerprints_category_tables` 断言版本号**指纹到**
> 品类/变相发布词表——只改词表不改规则时版本号不动 = 版本化冻结假门。

## 二、数据源可获取性记录（⚠️坑）

1. **nmpa.gov.cn 返回 412 WAF**：国家药监局站点有 WAF 拦截，脚本化抓取不可用；涉及药品/器械说明的核对不要依赖该站直连。
2. **flk.npc.gov.cn 正文 JS 渲染**：国家法律法规数据库页面正文为 JS 渲染，纯 HTTP 拉取拿不到正文；本题法条源以 samr.gov.cn 直连页为准。
3. **《执法指南》(一)(二)不涉及医疗广告认定**：市场监管总局《执法指南》系列第一、二篇与医疗广告认定无关，**勿误标**为医疗广告依据；《医疗美容广告执法指南》需单独定位。
4. **M1 三源可获取性复测（2026-10-16 实测）**：以 `tools/make_snapshots.py` 同一抓取路径重测三源，**HTTP 200 且三份快照逐字节一致**——
   - `advertising_law`：live 32858 字节 == 入仓 32858 字节；
   - `internet_ad_measures`：live 16130 字节 == 入仓 16130 字节；
   - `medical_ad_measures`：live 7413 字节 == 入仓 7413 字节。
   结论：**页面未改版，基准日维持 2026-10-15**，无需更新 `data/README.md` 与 `plan/PRECHECK-M0.md` 的基准日。

## 三、开源空白记录（soft evidence，⬜）

- 基准日：2026-10-15；工具：gh api（GitHub Search）。
- 检索式：`医疗器械广告` → 仅 Neochorne/china-medical-ad-compliance-skill（3★）、yuhudie598-dev/ad-compliance（1★）；`医疗广告 skill` → 0 结果；`医美 广告` → 全部 0★ 素材导航类仓库。
- 通用广告法类 skill 不做医疗事前审查专项（品类判定 + 禁止情形 + 审查要求）。
- **判定**：医疗广告事前审查 Skill 近乎空白。此为软论据（⬜），仓库文档引用时须带检索式与基准日。

## 四、合成数据纪律

1. **假机构名白名单**：所有合成广告样例中的机构一律使用虚构名称，格式如"XX医疗美容门诊部（虚构）""XX市第X医院（虚构）"；维护 `data/fake_org_whitelist` 白名单文件，基准断言脚本校验样例中的机构名必须在白名单内。
2. **不引用真实机构违规案例**：样例文案不影射、不复述任何真实机构的广告或处罚案例。
3. **真值标签挂法条**：每个样例的 BLOCK/WARN/OK 真值须逐条注明支撑条款（如"《医疗广告管理办法》§7 第 X 项"），未挂原文核对不得落库/生效。

## 五、数值口径纪律（一处定义，全文引用）

- 本项目所有"基准日"均指 **2026-10-15**；
- 三态符号统一为 ✅ / ⬜ / ❌（口径见第一节）；
- 条款引用格式统一为"《法规名》§条数"，多项禁止情形写作"§7 第 X 项"，款写作"§16 第 X 款"；
- 不在其他文档重复定义数值口径，需引用时指向本节。
