# S01 后端闭环评审证据

当前分支 `codex/s01-backend-closure`，工作基点 `e547335323fd19fccd324752dbeb1d08c9e21c2d`。状态与实现提交只以 [TASKS](../../TASKS.md) 为准；本轮交付停止在正式前端对接之前。

证据按来源和运行方式分别登记：

| 材料 | 用途与边界 |
|---|---|
| [ERP 候选调查](erp/README.md) | 原教学记录的真实有界查询与缺口；503、不完整分页和未知语义保留。 |
| [教学写入与回读](teaching-data/dataset-evidence.json) | 独立批次的真实 API 写入及独立 GET；来源始终是教学仿真。 |
| [教学准入](admission/teaching-simulation.md) | 写读 artifact、逐字段来源、D01/D02/D03 与教学规则隔离。 |
| [独立 Golden](admission/teaching-golden.json) | 手算日账和 MOQ、独立倍数、最大量、可售日、质量反例；不调用 B01/B02 生成期望。 |
| [计算验证](calculation.md) | 既有 B01/B02 工程场景、准入消费与限制。 |
| [模型评测准备及范围](model/readiness.md) | 有界真实评测方式、受控自然语言语义校验及 Token/费用分离。实际发送另列结果。 |
| [历史用量迁移](usage-migration.json) | 0005 最小兼容迁移前后历史事实指纹保全。 |
| [待评审及剩余事项](remaining.md) | 企业正式业务门、正式用途与前端后续工作。 |
| [前端 API 契约](../../contracts/s01/backend-api.md) | 受权任务、报告、证据与历史对接准备；本轮没有开发前端。 |
| [运行手册](../../runbooks/s01-backend.md) | 显式固定包装配、独立 API/Worker、复验和默认关闭模式。 |

`SUCCEEDED` 是任务技术状态。教学仿真验证、实际教学 API 读写、真实模型解释、企业正式业务验收分别判定。教学规则通过不批准真实企业采购；所有候选 `procurementEligible=false`。

输入、输出、总 Token 是统一基础事实，Provider 无法提供的值为 null；缓存计数按能力选填。费用 null 表示未知，保留预留额度，不能解释为零。解释成功由模型响应、Schema、领域事实和安全门禁判定，不要求费用已核算。
