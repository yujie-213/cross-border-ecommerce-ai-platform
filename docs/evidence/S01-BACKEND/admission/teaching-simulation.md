# S01 教学 ERP 模拟数据准入设计与验证

日期：2026-11-12
模式：`TEACHING_SIMULATION`
来源标记：`SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP`
规则版本：`teaching-s01-rules-v1`

## 边界

本模式只用于用户授权的教学演示数据。它与 `REAL_ANALYSIS` 使用不同的 package、校验和规范化入口，不代表企业经营事实，也不解除真实业务来源、规则签认、质量和采购执行安全门。教学规则不要求正式业务签认，但必须明确标记为 `CONTROLLED_TEACHING_RULE`，不得伪装成 ERP 回读值。

## 写入与回读证据

`TeachingAdmissionPackage` 绑定教学 batch、写操作及回执 artifact、独立 GET 回读 manifest、逐资源 GET artifact、scope digest、record IDs 和规范化内容 digest。POST 返回体不能代替 GET 回读；本地 fixture、mock 或离线文件引用不能建立网络回读事实。

实际 ERP 证据采用“聚合 manifest + 每资源独立 artifact”结构。逐字段 `ERP_NETWORK` provenance 必须引用 manifest 内对应资源 artifact，观察时点与该 artifact 一致。每个资源 artifact 的 `contentDigest` 绑定其 record IDs 及所支持字段的 `fieldPath/valueDigest`；聚合 `readBackContentDigest` 另绑定规范化后的 scope、asOf、coverage、mapping、inventory、demand 和 supply。原始 HTTP response fingerprint 与规范化内容 digest 分开记录。该结构是受信服务端编包和一致性校验，不宣称能以密码学方式证明远端系统真实性。

未来需求曲线及 draft 到教学计划供给的转换必须另有 `TeachingDerivationRule`。规则绑定精确 canonical 路径、方法、原 GET artifact 引用及内容摘要、教学规则记录和自身内容摘要。派生 provenance 使用 `CONTROLLED_TEACHING_RULE` / `VALUE_DERIVED` 并保留 `derivedFromRefs`。允许派生的范围仅为 demand 集合及 day/quantity/semantics、supply 集合及 remainingQty/availableDate/status；库存数量和更新时间、映射、scope、asOf 不能由教学规则替代。采购 draft 的 ID 可作为直接 ERP 事实，但 OPEN 状态、计划量和可售日仍是教学派生，不代表真实下单或在途。

当前 ERP 线确认的接口标识为 OpenAPI `5.1.0`、release `20260917-teaching-final-v2`，并记录具体 operationId。原始敏感响应只允许进入 Git 忽略的私有目录；公开证据只留脱敏 alias 和摘要。销售记录不可删除，依靠独立 batch 隔离；采购只允许草稿，不调用提交、下单或支付；入库不 confirm/post。

## 两种阻断结果

- 准入阻断：缺少独立 GET、write/read batch 或 scope 不一致、record IDs 不一致、artifact/字段摘要不一致、逐字段来源引用不一致时，`validate_teaching_admission` 返回 `BLOCKED`，不得规范化。
- 下游质量阻断：证据链完整时，库存/需求/供给数量可为未知，quality 可为 `VERIFIED_CLEAR`、`INVESTIGATE` 或 `UNKNOWN`。这些 package 可规范化，随后由 D03 对计算或候选形成明确阻断，保留可观察问题路径。

## 独立 Golden A—E

测试中的 Golden 期望使用简单逐日日账：同日供给先入、需求后扣、负余额保留为 backlog。它不导入或调用 B01/B02，目的是独立给出教学期望，而不是重复验证生产计算实现。

| Case | 手算输入与期望 |
|---|---|
| A 缺口 | ERP 库存 60；教学 replay 需求 8/10/9/11/12/14/13；无计划供给。余额 52/42/33/22/10/-4/-17，缺口 17、D6 首次缺货。MOQ 12、倍数 6 得候选 18；商品 lead 7 映射为 D7 可售，候选后仍在 D6 中途缺货。 |
| B 无需补货 | ERP 库存 96；使用同一 replay 需求且无计划供给。余额 88/78/69/58/46/32/19，总量和时序均不缺货。 |
| C 总量覆盖但中途缺货 | ERP 库存 10，教学计划供给 67 在 D7 可售；余额 2/-8/-17/-28/-40/-54/0，总量覆盖但 D2 起已缺货。draft ID/明细为 ERP 事实，计划量、OPEN 与 D7 可售为受控教学派生。 |
| D 采购约束 | 复用 A 的 ERP 回读，四个 controlled-policy 反例分别验证 MOQ 24/倍数 6、MOQ 12/独立倍数 10、maxOrderQty 17 阻断候选 18、D7 可售仍保留 D6 中途缺货。 |
| E 数据或质量异常 | E-DATA 将 opening 保持未知并由 D03 阻断；E-QUALITY 复用 A 的事实但设置 `INVESTIGATE`，可观察缺口但候选必须阻断。 |

教学需求规则固定为 `TEACHING_LAST_7_DAILY_REPLAY_V1`：按日期排序恰好七个教学 ERP 销量日，将各日目标 SKU 数量依序重放到 D1—D7；缺日或同日重复即数据不足，不做趋势、季节性或模型推断。它属于独立 `CONTROLLED_TEACHING_RULE`，不能把预测结果或方法标成 ERP 原始事实。完整输入和期望见 `teaching-golden.json`。

## 离线验证

- `tests/unit/data/test_admission.py` 覆盖独立教学入口、REAL 路径隔离、本地 fixture 拒绝、POST/GET 不可复用、batch/scope/record/value digest 一致性、逐资源 artifact provenance、未知数据下游阻断、quality 三态及 Golden A—E。
- 测试使用脱敏、构造的受信 artifact 形状，不声称已经执行真实 ERP 写入或回读。真实 batch 证据应由 ERP 线完成后另行提供。
