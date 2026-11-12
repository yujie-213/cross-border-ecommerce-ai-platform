# S01 后端计算证据与验收等级

日期：2026-11-12
范围：当前固定 A—E 样例、准入适配合同样例与既有真实教学 ERP 观测。本文不新增网络调用、不修改前端、不执行采购写入，也不代签真实业务规则。

## 结论

现有后端复用同一 D01/D02/D03/B01/B02 链，分别验证工程样例、准入合同样例及教学 ERP 仿真批次。下文的工程 A—E 是原固定样例，其编号含义与新增教学 A—E 不完全相同。新增教学场景以 [独立 Golden](admission/teaching-golden.json) 和教学写读、计算记录为准。教学验证不批准企业正式规则或真实采购。

| 层级 | 状态 | 可声称的结果 | 不可声称的结果 |
|---|---|---|---|
| 模拟工程 A—E | PASS | 固定输入下的 B01/B02 数量、日期、质量门和阻断行为符合当前引擎语义 | 真实 SKU 可采购、正式业务规则获签、真实 ERP 完整 |
| 准入适配合同样例 | TEST_ONLY / PASS | 严格来源/规则包能规范化为 `AdmittedInput` 并复用原计算链 | 样例中的 `offline-contract:` 引用已被读取或是业务签认 |
| 真实 API 内构造的教学仿真 | PASS | 独立 GET capture 经准入链进入原 B01/B02，9项独立 Golden 一致，5项独立进程联调一致 | 企业经营事实、已下单在途、正式规则或采购适用 |
| 真实教学 ERP 观测 | BLOCKED | 已有只读观测和可靠字段可展示，缺口不被 fixture 替换 | 真实 B01/B02 正向候选、采购适用或完整 MVP 验收 |

所有当前候选都保持 `procurementEligible=false`。AI 解释无论 AVAILABLE、UNAVAILABLE 或 NOT_ATTEMPTED，都不能改变该值、质量结论或计算完整性。

## 固定引擎语义

现有 B01 固定语义为：

`NET_AVAILABLE;INCREMENTAL_EXCLUDES_RESERVED;D1_AFTER_D0;SUPPLY_BEFORE_DEMAND;BACKLOG;BUFFER_INCLUDED`

即：输入库存已经是净可用；逐日需求不重复扣预留；D1 是 asOf UTC 日期的下一日；同日供给先计入再扣需求；负余额跨日累计；需求窗口包含 buffer。正式规则若与任一项不一致，准入应拒绝，不能在前端或 Handler 内改算法适配。

## 模拟工程五场景

样例由 `tests/support/backend.py` 从工程 Fixture 明确构造，`sourceNature=SIMULATED_ENGINEERING`、`engineeringFixture=true`、`realAdmission=BLOCKED`。固定断言位于 `tests/unit/s01/test_backend.py`。

### A：需要补货

- 当前可用：55。
- 目标数量：90。
- 已有供给计入后总缺口：15。
- 未补货首次短缺日：2026-11-20。
- 按 MOQ 与订购倍数构造候选：20，预计可用日 2026-11-18。
- 候选经 B01 重新评价后 `stockoutRisk=false`。
- 完整性为 `RULES_ONLY`，但限制仍含工程规则未验证，`procurementEligible=false`。

这证明当前固定引擎能构造并评价正向候选，不证明真实采购建议通过。

### B：不需要补货

- 模拟库存提升至 100。
- baseline `gapQuantity=0`。
- candidates 为空，不生成“0 件采购候选”。
- limitation 为 `NO_REPLENISHMENT_NEEDED`。

### C：中途缺货

- 模拟当前库存 5，较大在途供给延后至 2026-11-21。
- 总量口径 `gapQuantity=0`，但首次短缺日为 2026-11-13，`stockoutRisk=true`。
- candidates 为空。
- limitation 为 `INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED`。

这证明总量足够不会掩盖中途缺货，也不会编造加急、调拨或桥接采购策略。

### D：数据不足

- 删除一个必需逐日需求点。
- `completeness=BLOCKED`。
- baseline 为 null，candidates 为空。
- 已验证库存事实仍可作为 `reliableFacts` 展示，当前样例值为 55。

这证明缺失不会按 0 处理，也不会因仍有部分可靠事实而生成确定性候选。

### E：质量异常

- policy 的质量状态设为 `INVESTIGATE`。
- baseline 仍可计算，固定缺口为 15。
- `completeness=PARTIAL`，candidates 为空。
- quality 含 `QUALITY_REQUIRES_RESOLUTION`。

AI 解释不能解除调查状态；前端应显示已有供需指标和质量阻断，不显示采购适用。

## 准入适配 TEST_ONLY 固定样例

`tests/support/admission.py` 的样例显式标为 `TEST_ONLY_CONTRACT`，引用使用 `offline-contract:`，默认生产入口拒绝；测试只有显式 `allow_test_only=True` 才能验证合同形状。

固定构造：

- D0/asOf：2026-11-12T00:00:00Z。
- 净可用库存：10。
- D1、D2 需求：8、8。
- D1 已有供给：2。
- MOQ 与 orderMultiple：5、5。

适配进入现有链后的固定期望：

- baseline gap：4。
- 首次短缺：2026-11-14。
- 候选数量：5。
- 候选评价期末余额：1。
- `procurementEligible=false`。

该样例验证了：逐字段和集合 `valueDigest` 绑定、来源性质、规则内容摘要、精确 scope/asOf/有效期、固定引擎语义，以及 `normalize → project → capture → propose` 的兼容性。它没有访问 ERP，没有核实外部 sourceRef，也没有业务批准记录。

## 真实教学 ERP 状态

既有真实只读阶段曾取得 `TEACHING_ERP_OBSERVED` 教学源观测，但包含以下已记录缺口：库存时点、完整逐日需求、逐行未收/可售日、独立约束、质量结论和正式规则签认并未共同满足。当前 observation 路径保持 `completeness=BLOCKED`，B01 不执行、B02 无候选、AI 不尝试或仅显示不可用状态。

因此原有经营记录的状态是：

- 教学 ERP 只读访问：已有独立历史证据。
- 真实来源与规则准入包：尚无本文件可引用的正式通过包。
- 真实 B01/B02 正向计算：NOT_RUN / BLOCKED。
- 真实采购建议与采购适用性：BLOCKED。
- 模拟测试通过不得升级为真实验收。

前端若展示 observation 报告，应突出来源/缺失与 `BLOCKED`，不能用模拟 A 的候选填充真实 SKU 空缺。新建教学批次另用 `SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP`，即使实际 API 写入和回读通过，也不升级为真实企业经营事实。

## AI 与计算结果的分离

AI 只解释已计算的白名单事实：

- `AVAILABLE` 表示解释通过 schema、版本、引用和事实一致性校验。
- `UNAVAILABLE` 表示解释失败或拒绝，合法 baseline/candidates 继续保留。
- `NOT_ATTEMPTED` 表示未启用模型。

usage 中 input/output/total Token 或 actualCost 为 null 都表示未知，不表示 0。Token 已知但费用未知时，G02 可以已有 `usageRef`，O01 仍保留费用额度；这不影响既有规则计算的真实性，也不能被前端显示为“免费调用”。

## 验证依据与限制

新增教学 [9项逐日对照](teaching-data/calculation-comparison.json) 保留每项 expected/actual、baseline/candidate 日账、首次缺货及阻断码。A 的候选18仍在 D6 缺货，未把“有候选”当成风险消除；B 不生成0件候选；C 期末0仍识别D2缺货；D 验证独立倍数、MOQ、最大量和可售日；E 分离离线数据缺失与实际质量调查。既有 B01/B02 算法没有为这些期望修改。

本资料依据当前源码和已有测试：

- `tests/unit/s01/test_backend.py`：A—E 五场景固定断言与发布防篡改。
- `tests/unit/data/test_admission.py`：TEST_ONLY 来源/规则准入及适配计算。
- `tests/integration/s01/test_backend_workflow.py`：真实隔离 MySQL 下模型故障保留计算、生命周期变化不发布、来源包绑定。
- `tests/integration/orchestration/test_optional_usage.py`：可选 Token/费用 usage 的持久化、补充、迟到核账和回滚。

本资料解释各类计算证据的范围；实际命令、退出码和被测提交以独立运行记录及最终 verification.json 为准。本轮停止在正式前端对接之前，不执行真实企业采购。
