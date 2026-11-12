# S01 后端闭环交付报告

2026-11-12，分支 `codex/s01-backend-closure`。实现提交 `5f6c50acea6fe4dead2dec22188ed2e5f5b0eb30`，可重复复验工具提交/最终被测 HEAD `c965a334b6bbc3c689fb334c80f8cf0a9ee84dad`。本轮交付 REVIEW，负责人和星星独立评审尚未运行；正式前端对接之前停止。

教学仿真 API 写入、正式 GET 回读、准入、B01/B02、后端进程链路已验证。真实 AI 共3次，A/B成功、C校验拒绝，D/E按首次失败停止规则未发送，因此真实模型五例评测 FAIL。合法规则报告保留，企业正式经营数据和规则仍待验收。

## 按证据来源分别判定

| 类别 | 结果 | 依据与限制 |
|---|---|---|
| 本地 Mock/离线协议与真实隔离库回归 | PASS，601/601 | [全量证据](verification.json)：原399逐名保全、新202，0失败/错误/跳过；ERP/模型为离线 fixture，数据库和适用API/Worker为真实进程 |
| 真实教学 ERP API 写入 | PASS | [批次证据](teaching-data/dataset-evidence.json) 与 A—E记录；固定教学范围，受控创建/更新/自身清理，无付款/发货/采购提交/审批/过账/通知 |
| 真实教学 ERP API 回读 | PASS，仅本批已核范围 | 独立正式 GET、原请求/读侧独立规范摘要、店仓SKU、单行库存、七销售键与精确集合完整性；旧经营记录503/不完整仍保留 |
| ERP 内仿真业务数据 | PASS，仅教学 | [准入](admission/teaching-simulation.md)、[catalog](teaching-data/catalog-review.json)：A—E ADMITTED；`SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP`，非企业经营事实 |
| B01/B02 正向与反例 | PASS，9项 | [独立 Golden](admission/teaching-golden.json)、[逐项实际对照](teaching-data/calculation-comparison.json)；A/B/C、D四变体、E数据/质量分级，不改算法迎合期望 |
| 真实 DeepSeek 调用 | 部分成功，评测 FAIL | [模型报告](model/report.md)：3次/5642 Token，A/B AVAILABLE，C INVALID_OUTPUT，D/E NOT_RUN；费用UNKNOWN、预约$0.15保留 |
| 真实 API/Worker/MySQL 联调 | PASS，5项教学场景 | [进程证据](teaching-data/backend-process.json)：固定真实GET capture输入，独立进程、幂等、历史、前报关联、证据、API重启、当前缩权；本次复放不增加ERP网络请求 |
| 企业正式业务规则/真实经营数据 | BLOCKED / 待验收 | [原调查](erp/README.md)、[剩余事项](remaining.md)；教学通过不代签正式规则或采购安全门 |
| 正式前端与完整MVP页面验收 | NOT_RUN | 已交 [API 对接文档](../../contracts/s01/backend-api.md)，按本轮停止点没有开发前端 |

## 计算结果与数据语义

A 的7日需求8/10/9/11/12/14/13、库存60，余额52/42/33/22/10/-4/-17。缺口17，MOQ12/独立倍数6得候选18；D7可售后期末1，但D6仍缺货，报告保留风险。B库存96，无缺口、无候选。C库存10、D7教学计划供给67，期末0但D2已缺货，不编造桥接采购。D验证MOQ24、独立倍数10、max17及D7时序；E质量调查阻断候选，离线未知库存阻断baseline。

店铺、仓库、商品和 Listing 关系由真实 GET 固定。库存各场景是同一自有行按时点更新后的独立快照，不能同时相加。销量七日回放未来需求属于版本化教学规则；C采购草稿不代表在途，OPEN/计划量/可售日明确为教学派生。A空供给仅证明本批指定集合；D是A事实加教学规则复算；E-DATA是离线负例。箱规未默认为订购倍数。记录清单、异常恢复、保留与清理见 [批次手册](teaching-data/batch-runbook.md)。

## 公共能力兼容与控制

复用已验收 O01、D01—D04、B01/B02、A01、G01/G02、I01。Token统一为输入/输出/总数；缓存按Provider可选，缺失null/UNKNOWN。费用可空，与解释成功独立；未知不当0，不释放可能已发送请求的预约。保留原task次数/Token/期限/预留、幂等、取消、超时和迟到只核账控制。同logicalCall不盲重发。

0005迁移仅原唯一用量表追加可空Token分项、放宽费用/旧总数可空；[历史指纹](usage-migration.json)证明366条usage、759条attempt、1619条budget原维度保全，无历史数值推断。无新增预算表或平台；统一usage Adapter覆盖chat形状与Ollama形状的离线映射，未宣称已真实接入其他云或本地模型。

报告公开投影裁剪原包、内部manifest、源响应与未授权字段。客户端只选择服务端固定packageRef，当前权限在选项/历史/报告/证据读取重验。所有候选 `procurementEligible=false`，AI不能解除调查或批准采购。

## 复验与评审

[运行手册](../../runbooks/s01-backend.md) 和 [批次命令](teaching-data/batch-runbook.md) 提供固定capture计算、独立进程和全量复验。MySQL8.0.27、唯一 `s01_a01_test_20261112`、UTC/READ-COMMITTED、head `0005_optional_usage`，没有清库或改其他数据库。pip check、compileall、默认关闭入口及离线模型suite均退出0。

[回归历史](regression-history.json) 保留此前的取消前claim失败、Windows临时目录权限错误及一次租约恢复失败。发现并核验遗留教学测试Worker后仅停止该进程，62项相关生命周期用例通过，再以所需权限固定HEAD全量601通过；没有删断言或改算法掩盖失败。

独立评审应重点核查：教学事实与派生边界、API写读一致性及幂等恢复、Golden独立性、C拒绝及D/E未运行的用途覆盖限制、可空费用仍占预算、历史核账保全和公开权限。当前不把工程交付或部分模型成功登记为 ACCEPTED；不合main，等待负责人和星星审查。
