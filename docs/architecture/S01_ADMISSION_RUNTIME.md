# S01运行数据准入增量架构

2026-11-14，ADR-S01-ADMISSION-018与contracts/s01/admission-runtime.md为本轮实现依据。既有FastAPI/独立Worker/MySQL/O01/G01/G02继续唯一所有权，B01/B02函数不改。无新服务、缓存、队列或数据库表。

D01 V2Reader持久原任务的版本、开始时间、分页/预算/私有响应及实际读取时间；sync.runtime按真实店仓有界发现完整销售范围，按SKU/仓有界获取库存全流水，不使用预测窗口裁剪。D02 stock_basis完成独立基点/守恒；projection.runtime把业务日销量/零日证据与采购参数分开，构造既有AdmittedInput交原D03/B01/B02。D03 quality.runtime生成稳定能力/恢复语义，现有catalog_manifest/seal_result/ManifestStore将其一同封存。

基点存既有d02_monitor_scopes.content中的可选StockCheckpoint，通过scopeVersion与原digest CAS显式修订；旧content和历史报告不重写。旧检查点无新版本时走原采集/投影，历史只读不会重新计算为新结果。当前实现每次仍需完整有界SKU流水，真实ERP没有已验证水位过滤时可能降级，不能宣称全量增量事件平台。

新结果仍由原Handler/ItemStore/O01发布，失败按对象隔离，新API字段自然随原详情返回。L3a风险与L3b候选分开；L4原P3/方案B单独检查权限、最新事实、采购约束、人工确认及幂等回读。只有自有部署范围允许显示请购能力，G01提交时再次检查；未实现任何ERP写入新路径。WorkBuddy仅消费兼容增量契约，正式Vue本轮不动。
