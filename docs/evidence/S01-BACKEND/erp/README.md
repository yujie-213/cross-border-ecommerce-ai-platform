# S01 教学 ERP 候选发现报告

执行时间：2026-11-12T11:03:05Z。工具先检查全局销量与采购接口，在最多20个候选中优先核验5个；全过程只读，ERP业务写入0、模型调用0。教学源记录均保留其 `synthetic=true` 性质，不能称为生产事实。

## 实际接口结果

| 检查 | 结果 | 覆盖解释 |
|---|---|---|
| 全局销量 REST | REACHABLE | 首页返回，总数1153919；仅取1条且 `complete=false`，不能外推完整需求。随后5个精确店仓查询均返回 `ERP_503`，没有按SKU继续重试坏接口。 |
| 全局采购 REST | REACHABLE | 首页返回，总数1234；仅取1条且 `complete=false`。5个精确仓范围各读取28个采购头，但没有匹配候选SKU的行；结果为UNKNOWN，不解释为未收数量0。 |
| 候选发现 | PASS | 有界发现20个候选，仅核验5个；未遍历全量库存、Listing、商品、销量或采购。 |
| 身份/库存/商品约束 | PARTIAL | 5个候选均取得单SKU、单店、单仓、Listing、2行库存、1行商品及报价；净可用口径、批次聚合和时效阈值未签。 |
| 入库/评价质量窗口 | PARTIAL | 窗口查询为空时保持UNKNOWN；商品质检标准只是信号，不能形成质量CLEAR结论。 |

## 候选比较

| 候选别名 | 角色 | 已观测域/8 | 精确缺口数 | 可计算程度 |
|---|---|---:|---:|---|
| `sku-ac3ab740d7f4b86790c4` | 推荐主样本（并列） | 5 | 11 | BLOCKED |
| `sku-ba0806427a2780d68965` | 并列最近样本 | 5 | 11 | BLOCKED |
| `sku-c009bfeb1faef1f69207` | 并列最近样本 | 5 | 11 | BLOCKED |
| `sku-eb55c28f45c27d9d5241` | 并列最近样本 | 5 | 11 | BLOCKED |
| `sku-1c5fe03ebb578d2bb976` | SKT-OL-XXL 已知负例 | 5 | 11 | BLOCKED |

四个非负例在当前证据下并列：库存源时间同为2026-09-16 23:00:00，商品均具备MOQ、箱规、采购交期和质检标准，但销量精确查询失败、采购行未匹配、可售日缺失，无法基于事实区分更优样本。工具采用稳定别名顺序选 `sku-ac3ab740d7f4b86790c4` 作为后续受控补充的主样本；这不是业务优选或采购建议。

共同缺口为：`ERP_503`、`NO_MATCHING_LINES_NOT_ZERO`、`SELLABLE_DATE_MISSING`、`HISTORY_TO_FUTURE_RULE_UNSIGNED`、`UNRECEIVED_DEDUP_RULE_UNSIGNED`、`NET_AVAILABLE_SEMANTICS_UNSIGNED`、`BATCH_AGGREGATION_UNSIGNED`、`FRESHNESS_THRESHOLD_UNSIGNED`、`MOQ_CONFLICT_REQUIRES_RULE`、`CARTON_QUANTITY_SEMANTICS_UNSIGNED`、`QUALITY_DECISION_UNSIGNED`。

公开逐域状态、缺口和响应指纹见 [candidate-matrix.json](candidate-matrix.json)。真实业务准入保持 `BLOCKED`；空返回始终保持UNKNOWN，不转成零。

## 私有可复核包

本轮最终私有包为 `data/private/s01-backend-erp-discovery/run-20261112T110305Z-edff865b/`，其中 `discovery-private.json` 包含推荐别名对应的完整SKU、店、仓、Listing、库存、商品、报价、采购头及读取事件，可按 `candidateId=sku-ac3ab740d7f4b86790c4` 的SHA-256别名定位。文件SHA-256为 `fa1809d2ba06720e342ca9bf817633678af13a85927119a33da3a5971b08cecc`，大小335066字节；70个原始响应共172317字节。该目录由 `.gitignore` 的 `data/private/` 规则排除，不提交、不公开源ID或参数值。

同目录的 `best-observation.json` 是从上述固定captures离线生成的D02八域观测projection，无新网络请求。revision为 `6241b32722728305f56d3630de70e05058ebb28952a5ed9eaab6d1d2fa0ce614`，文件SHA-256为 `95b6c872772801648fc870400e2c820cae58e62409c8427e3a3ab26569bee784`。scope仅含哈希SKU/店/仓别名和 `fields=[quantity]`；`sourceSynthetic=true`、`ownerConfirmed=false`、`revalidationFailed=true`。D03实际生成12个BLOCK问题，`calculationAllowed=false`、`candidatesAllowed=false`，不包含金额、原始ID或私有参数值。
