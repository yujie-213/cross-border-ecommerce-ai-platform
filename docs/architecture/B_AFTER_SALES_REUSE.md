# B V1.0 系统复用与差距分析

2026-11-16；调查基点 `2547d1e23ef8cbc991a6e238df9961c35a551696`，分支 `codex/b-after-sales-v1`。仅静态代码调查，无ERP、数据库、模型实测；“已实现”不等于本轮复验通过。未知 `docs/ERP-openapi.yaml` 未读取、未改动。权威范围：[冻结需求](../requirements/B_AFTER_SALES_V1.md)。先读本表，再读[详细设计](../agents/B_AFTER_SALES_DESIGN.md)。

## 1. 逐项判定

| 能力／判断 | 实际依据（仓库相对路径） | 可用程度及B处理 |
|---|---|---|
| 登录／复用 | `src/commerce_hub/governance/access/local.py`、`entrypoints/http/local_auth.py`、`frontend/src/PlatformApp.vue` | 已有本地admin、Cookie会话及CSRF；沿用真实actor，不虚构岗位账号 |
| 授权／扩展 | `governance/access/service.py` 的ALLOWED_ACTIONS、SCOPE_DIMENSIONS；`governance/access/tables.py` | 当前动作只有任务、工程及S01请购，维度为店仓／canonicalSku／fields；须新增B动作及来源版本授权，不能仅沿用tasks:read |
| 异步任务／复用并扩展装配 | `orchestration/service.py` 的HandlerSpec、TaskService；`worker.py`；`infrastructure/work.py` | 已有命令指纹、领取租约、心跳、恢复、原任务预算和取消；新增B场景注册及版本化参数，不另建队列 |
| 领域结果／扩展 | `orchestration/contracts.py` 的DomainResult | sourceNature只有工程模拟、教学ERP观测、ERP内仿真；不支持中台独立教学来源。新增兼容版本，旧0.1.0仍可读；不得冒标ERP内仿真 |
| 模型控制／复用 | `capabilities/models/contracts.py`、`gateway.py`、`adapters/models/deepseek.py`、`orchestration/budget.py` | 已有结构化结果、预算预检、usage/UNKNOWN；网关拒绝queryRef，工具列表为空，输出上限1024 Token、两条system/user消息。B走任务，拆分有界分类批次，不默认开放工具或无限长上下文 |
| 模型用途及配置／扩展 | `bootstrap/s01_v2.py`、`adapters/models/online.py` | 当前在线授权／装配针对S01。B独立purpose、Prompt/Schema/资料bundle及授权；不继承S01日常模型许可 |
| 审计／复用 | `governance/observability/service.py` 的Audit.record/record_usage/verify_model_receipt | 可追加人工动作、拒用和版本摘要；正文留受控业务资产，不写进details |
| ERP传输／扩展 | `adapters/erp.py` 的TeachingERPReader、ReadBatch、READ_GET/READ_POST | 已有指定教学服务、白名单、禁重定向、限流和complete标记；列表含customer-tickets/customer-voice等不等于明细事件全量可用。只增已验证有界读取；退货阶段、履约完成／全批次覆盖仍需准入验证 |
| 数据投影／按域扩展 | `data/projection/`、`data/quality/`、`data/sync/` 的runtime/online/v2及`data/contracts.py` | 当前以库存需求供应、S01质量规则为主。不能直接当作售后事件模型；复用版本、来源、质量门方法，增加B投影及准入 |
| 快照／扩展 | `data/sync/v2_store.py` AcquisitionCheckpoint；`migrations/versions/0010_s01_v2_manifests.py` | S01专用检查点与manifest已有；新B清单由D03归属，不能私写S01清单或建立第二个输入版本权威 |
| 证据／扩展 | `data/evidence/__init__.py`；S01 handler/explanation与`frontend/src/components/BusinessEvidence.vue` | 目录与S01特定证据／引用校验已有，不能声称通用D04解析器已实现。新增最小授权EvidenceRef解析和资产适配，不复制来源正文 |
| 指标／新增定义、保持原逻辑 | `capabilities/metrics/`、`scenarios/s01_v2/plan_preview.py` | 既有确定性库存指标不含售后成熟群组率；B指标在B01所属metrics下新增独立定义，B02与原供需公式不改 |
| 案件、教学包、政策、调查及风险／新建 | `scenarios/`当前无B实现；迁移0001—0011无B表 | 全部是待实现业务，不以S01报告／请购冒充案件或风险审批 |
| 政策检索／最小新建 | `capabilities/`无可直接使用的政策生命周期与权限检索实现 | A03所属最小SQL过滤与段落检索；不是先建通用RAG平台。A02只新增B实际使用的理解接口及实现 |
| 前端壳／复用并扩展 | `frontend/src/App.vue`、`V2Shell.vue`、`frontend/src/pages/HomePage.vue`、`router.ts` | Vue3、hash路由、首页和S01壳已实现；App入口分发有S01假设，新增显式模块路由；沿用Panel/Notice/Modal/StatusBadge和样式，不重写全站 |
| 前端请求／复用 | `frontend/src/api/client.ts` | 沿用会话、CSRF、错误；B独立状态容器，不能复用useWorkspace的S01业务状态 |
| 数据库／复用 | `infrastructure/database.py`、`migrations/env.py`、`migrations/versions/0011_local_admin.py` | SQLAlchemy/MySQL/Alembic既有单链，后续增量revision；本轮不建表、不迁移 |
| 启停／扩展配置 | `tools/local_platform.py`、`bootstrap/local_platform.py`、`bootstrap/s01_v2.py`、`Start-Platform.cmd` | 现有启动绑定S01装配；后续组合注册B且默认关闭、同一API/Worker进程模型。B缺配置只禁用B，不让S01装配失败 |
| 通用审批／暂不需要 | 总体架构C01/C02/C03为职责规划；当前有S01专用采购服务 | B人工审核由领域状态机＋G01/G02落实；不搭企业审批中心，不接外部执行服务 |
| 新中间件／暂不需要 | 当前MySQL租约队列已承载任务 | 不引入Redis、MQ、Milvus、Neo4j、多Agent框架、Memory、独立RAG、向量索引或新部署服务；版本化政策规模可用SQL检索 |

路径中省略的后端前缀统一为 `src/commerce_hub/`。基础设计依据：`docs/architecture/ARCHITECTURE.md` §7（数据所有权）、`docs/agents/AI_DETAILED_DESIGN.md` §4—6／9.1（网关与上下文）、`DESIGN.md` 与 `docs/ui/PRODUCT_SPEC.md`（视觉与操作）。这些总体文档中的未来目录／端口不能作为已编码证明。

## 2. 可启用性与边界

无需产品重新决定三链范围或统计默认值。后续开发必须验证ERP订单明细身份、发货全集与结束标记、退货收货事件、分页和时区；缺少任一要素时，ERP原生率保持UNKNOWN，同时完整中台教学金样仍是必做交付。工单115397的关联能力沿用需求中的历史证据，USB尺码仅作负例，本轮未重新取证。

政策四类正文、发布责任人及教学商品精确映射是验收资料输入，不能由设计人员代签。接口不足不删功能：采用已冻结D1双源方案，ERP只展示已证实事实，教学包承载完整统计闭环。后续若仍无可核实的商品映射，AC-03正例必须标BLOCKED，不能用SKU文本绕过。
