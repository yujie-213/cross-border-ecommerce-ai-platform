# S01数据质量与分析能力契约 v1

2026-11-14，负责人正式开发任务批准方案E，基线main ece11160，独立分支codex/s01-admission-runtime-fix；不合main、不改Vue/B01/B02，不ERP业务写/付费模型。历史报告及旧采集按原版本读取/恢复。

## 时间与证据

新V2采集标记admissionVersion=s01-runtime-v1。业务日从显式策略时区和原任务开始时间确定，采集完成时间为最后真实响应时间；库存observedAt与源rowUpdatedAt分别保留，超过24小时采集/跨业务日恢复须重新采集，不伪装最新。SMA默认7个完整自然业务日，与库存守恒范围独立。

库存基点复用已登记MonitorBinding的可选stockCheckpoint和scopeVersion；无该字段时保留已登记期初证据，或完整独立ERP流水的最早before值。禁止由当前库存加窗口销量反推基点。基点后全scope流水须有界完整、去重、关系/余额链一致；当前只允许已证实销售出库，采购入库可只在凭证/过账/质量/库存关联全部独立验证时支持；其他事件明确UNSUPPORTED。未解释差额不重置基点。版本变更使用登记服务的显式原版本CAS并保留旧版本，不新增数据库表/HTTP写接口。

销量按订单业务日期和已支付/已履约数量；未付/未发/取消分类排除，退款/部分履约语义未知仅影响相关日。有效正销量需独立履约出库；零日需完整目标店仓未按日期裁剪的有界正式销售集合、当前库存与独立全流水一致、该日位于可信观测起点之后且未断货。仅返回空页/固定ID不等于零。源覆盖不全/早于可信起点/无法确认零时UNKNOWN，保留参考均值但不进确定性B01。已获准教学历史的正销量可保留原业务日期，并明确非历史实物过账。

## 兼容增量响应

现有V2详情新增admissionVersion、dataQuality（identity/demand/inventory/procurement分域状态/原因）、demandWindow（窗口、KNOWN_SALES/KNOWN_ZERO/UNKNOWN/CENSORED日明细、已知/零/缺失数、样本时间/分母）、inventoryBasis（基点版本/事实时间/当前观察/守恒/未解决历史）、capabilities（facts/reference/risk/rules/requisition各enabled/reasons）、recoveryHints（业务说明与恢复动作）。敏感原始行与凭据不公开。旧报告不改写、缺新增字段表明LEGACY_REPORT，消费者不得假造新质量签认。

L1已核实事实可展示；L2有效样本可作明确日期参考；L3a完整需求+可信当前库存可由原B01算风险，缺报价/箱规不能吞掉风险；L3b采购规划参数完整才原B02候选；L4保留独立方案B，即ERP参考来源本身不禁人工请购。新风险字段不作为采购数量；旧quantity仍只有规则候选或ERP参考。

提交前G01/自有写范围、当前库存、有效报价/MOQ/整箱/最低金额、已有正式采购、人工确认/漂移、幂等及写后回读全部保持。未知可售日期不扣在途，待审批不变有效采购；不执行领导审批/下单/收货/入库。

## 实施与验收

D01有界完整集合与恢复、D02基点/守恒/日覆盖、D03不可变质量证据、V2能力及采购比较为消费者；旧normalizer用于历史重放，不静默重算旧报告。新契约随本轮提交REVIEW。必须完成两SKU原始证据/跨日/未知零/合法增量/错误与重复事件/过期报价/历史/恢复/P3及全量回归。真实ERP只读、真实MySQL、隔离仿真与30日模拟分开，不把接口缺失标PASS。

## 字段边界补充

自动来源基点的originAt为原登记/首条ERP过账前值的事实起点，checkpoint.observedAt为本次独立读取时间；显式新基点使用其已登记的observedAt/postedAt水位。二者不可互换，源行rowUpdatedAt也不是采集时间。零日只能在该有据起点之后按完整范围与未缺货条件证明。capabilities.requisition是任务自有部署范围和业务条件的指示，不取代当前会话的G01重新鉴权。riskResult.inTransitQuantity仅统计已确认可售供给；未证实采购分别在formalPurchases和uncertainties显示，不能把0解释为无任何采购。

## 两SKU可用性定向修复增量（2026-11-14）

新增HISTORICAL_REFERENCE状态/来源：仅当原结果无规则/ERP建议，但既有capabilities.reference=true时使用。quantity/sourceQuantity仍null，采购资格仍按原门检查，历史参考不能提交请购。现有API继续返回库存/历史日期与记录日期均值；最小Vue面板消费既有demandWindow/inventoryBasis/recoveryHints，不改WorkBuddy原型。summary仅当有新历史参考结果时增加historicalReference计数并计入可查看分析覆盖；旧报告字段及统计校验保持原样。新采集的stock/ledger请求每页最多25，预算/完整性/去重/原任务恢复不变，不把小页成功解释为永久无超时。11/13零订单已由正负日期查询对照证实，但当日中午建档、无整日可售证据，仍不补为有效零预测样本。
