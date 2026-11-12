当前执行增量（2026-11-12）：负责人已授权完整前端开发；正式工程见 `frontend/`，启动见[运行手册](../runbooks/s01-frontend.md)，本轮证据见[交付报告](../evidence/D-S01-UI-01/report.md)。下方“仍TODO/只准备准入”为前次交接历史，不覆盖本轮授权。

# D-S01-UI-01 前端 MVP 准入与交接

负责人于2026-11-12确认下一阶段为S01前端MVP开发与后端API联调。本轮只准备准入，任务仍TODO；收到下一条开发指令前不创建前端代码、页面或依赖。

基线：本轮验收合入并同步后的最新main。原已验证实现c965a33与交付1619bc1仍是历史证据；实际前端开工时重新读取main HEAD和工作区状态，不能拿历史HEAD替代最新基线。验收分项见 [登记](../evidence/S01-BACKEND-ACCEPTANCE/review.md)。

## 复用统一产品与架构

沿用整个中台的 [PRODUCT_SPEC](PRODUCT_SPEC.md)、[DESIGN](../../DESIGN.md)、[原型](../../prototypes/s01/index.html)、[原型边界](ALIGNMENT.md) 和 [开发架构](../architecture/DEVELOPMENT_DESIGN.md)。原型是模拟交互；正式页面应替换数据消费并保留统一布局/视觉，不复制成另一套系统，不把会话内审批演示当后端能力。不在本次交接另选框架或组件库。

页面展示服务端B01/B02产物，不在前端重算库存、候选、日期或费用。任务state、报告completeness、AI status和procurementEligible独立展示。教学源必须显示 `SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP` 对应标识；所有候选当前采购适用false。

## 已实现接口与拟开发消费范围

精确字段、身份、错误码、幂等、当前权限、Cookie/CSRF要求以 [后端API契约](../contracts/s01/backend-api.md) 和实际schema为准。以下是已有API的页面消费准备，不表示页面已实现。

| 前端范围 | 已有后端能力 | 消费边界 |
|---|---|---|
| 店铺/仓库/SKU/包选择 | GET `/api/v1/s01/options` | 只用授权mappedChoices及packageRef；不是全量ERP商品搜索或任意SKU现场采集 |
| 创建单SKU分析 | POST `/api/v1/analysis-tasks`，S01_BACKEND | 精确scope和服务端固定包；Idempotency-Key；浏览器不提交文件路径、规则签认或原始ERP数据 |
| 状态与取消 | GET `/{taskId}`、POST `/{taskId}/cancel`，基路径analysis-tasks | 有界轮询、终态停止、expectedRevision和取消幂等；无报告不显示“查看本次报告” |
| 库存/需求/缺货/候选/七日变化 | GET `/{taskId}/report` | baseline.series和候选evaluation.series含day/demand/arrivals/closingBalance；用服务端实际点数绘图并提供表格，不补未知日或把null当0 |
| AI解释与Token/降级 | report.analysisReport.ai | 四类解释、输入/输出/总Token、可选缓存和UNKNOWN费用；off返回NOT_ATTEMPTED，失败显示不可用并保留规则结果 |
| 质量/风险/人工确认 | report.dataReport.quality及limitations、解释中的确认说明 | 质量阻断独立于AI；只读人工复核说明，不等于确认/审批接口 |
| 证据与历史/前报关联 | GET `/{taskId}/evidence/{evidenceId}`、GET analysis-tasks历史；创建可带previousReportRef | 当前scope重鉴权、404和分页正常展示，不回落固定旧报告冒充新结果 |
| 身份与会话 | 现有Bearer及POST/DELETE `/api/v1/session` | 受信身份来自服务端/授权本机配置；无用户名密码登录或任意角色赋权接口，不能把签名密钥放浏览器 |

analysis-tasks相关路径完整前缀为 `/api/v1/analysis-tasks`。不存在的报告、失败或空选项必须显示实际错误/空态，不用前端Mock冒充接通；工程Mock演示若使用必须明确标注，不能替代真实API浏览器验收。

## 尚未提供的能力与独立剩余项

- 普通S01_BACKEND真实DeepSeek在线解释流程尚未提供。现装配显式test/offline且解释只支持off/mock；独立付费评测装配不等于普通分析已接云模型。
- 原C-04继续承担用途修复与后续评测；A/B成功、C拒绝、D/E未发、整体FAIL保留。正常分析流程的真实模型接入需要单独实现/签认与调用授权，当前不补发或重建授权任务。
- 没有采购草稿提交、审批、采购下单、付款、发货或ERP业务写入的前端API；不能连接原型按钮到虚构端点。
- 企业正式数据、业务规则、ERP安全、AI正式用途四门仍BLOCKED；本阶段可先接已验收教学固定包的真实后端API，不能展示为企业采购结论。
- 正式身份来源、同源部署和本机授权catalog须在前端开工时核实，遵循现有G01与部署架构，不以角色下拉框或浏览器密钥代替授权。

## 下一阶段验证要求

收到开发指令后覆盖：选择→创建→轮询→取消/报告、教学来源、七日数据与表格一致、UNKNOWN和质量阻断、AI未尝试/不可用、证据权限、历史/刷新/前报关系、错误/空态、窄屏及深浅主题。后端实际请求/响应与浏览器证据可追；真实模型、Mock和固定教学回放分开。D-S01-UI-01不能因页面完成而自动关闭C-04或四项企业门；最终完整MVP仍由原D-S01-ACCEPT-01单独验收。


## UX技术债（LOW，仅登记，2026-11-12）

390px小屏幕逐日数据表阅读成本较高，横向滚动提示不足。后续可考虑横向滚动提示、折叠数据表或移动端专用展示。当前S01 MVP主要在桌面使用，无手机端针对性优化需求；本轮不实施、不新增组件/依赖或移动布局重构。归属D-S01-UI-01后续UX评审，非本轮修复验收阻断。
