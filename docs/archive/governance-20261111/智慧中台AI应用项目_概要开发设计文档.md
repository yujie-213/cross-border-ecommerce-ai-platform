# 跨境电商智慧中台 AI 应用项目概要开发设计文档

> 文档编号：AIH-HLD-001 ｜ 版本：0.2 ｜ 日期：2026-11-11 ｜ 状态：第 10 步 H01—H07 定点修订，待独立复核
>
> 设计基线：需求文档草案 v0.2、总体逻辑架构与流程设计 v0.2（含最新两项图示修正）、可行性分析报告 v1.0。本文将已确认的逻辑架构映射为工程方案，保留 S01—S10、17 个公共模块、22 项候选需求及既有建设阶段。
>
> 本次仅形成文档、Mermaid 源图及阅读版，不创建应用工程、不编写业务代码、不连接企业业务系统。接口名称、目录、表名和状态实现方案属于概要设计建议，不表示已经开发或验证。

## 01 设计结论、依据与决策状态

采用 **Python/FastAPI 模块化单体 + 独立异步 Worker + MySQL** 作为工程方向。API 与 Worker 共享模块代码和契约，通过 MySQL 中的持久任务协作；逻辑模块不直接等同于服务或进程。场景负责领域流程，公共能力负责唯一实现，O01 负责单场景与跨领域的任务级协调。

本文用三种标记区分确定程度：**【确定】**来自用户技术方向或已确认基线；**【建议】**为本轮提出、待概要设计审查冻结的工程选择；**【待验证】**必须用真实接口、数据、运维条件或业务口径验证的假设。建议不自动转为已批准实施决策。

| 依据 | 采用的约束 | 本文落点 |
|---|---|---|
| [需求文档草案 v0.2](智慧中台AI应用项目_需求文档草案.md) | 完整场景、唯一归属、公开契约、权限与人工控制、分期 | 第 02、05—09、13、18—20 节 |
| [总体逻辑架构与流程设计 v0.2](智慧中台AI应用项目_总体逻辑架构与流程设计.md) | O01→ScenarioHandler 路径；B02→B01 单向依赖；显式提交审批与执行；五层及横向治理 | 第 03—07、11—14 节及全部工程图 |
| [可行性分析报告 v1.0](智慧中台AI应用项目_可行性分析报告.md) | 接口、容量、质量、安全、人员和预算均有验证门槛；成本示算不是实测 | 第 08、10—12、16—20 节 |

【确定】不调整已通过 R01—R09 的职责边界。原文中历史性的“待复核”页眉不构成本轮重新设计依据；以用户确认的复核结果和最新图示修正为准。三份基线正文及已有图文件保持不变。

【待验证】企业接口尚未被本文接通或测通；真实租户/店铺/仓库规模、数据量、同步频率、任务峰值、模型地域与审批岗位尚不足以冻结容量和上线日期。可研的人月、价格和收益示例不得直接写成 API SLA、线程数或采购配置。

本轮仅以以上三份项目基线、本文 v0.1 和本次 H01—H07 意见为修订依据，不关联其他历史项目。主要增补位置为第 4.1—4.4、6.4、12.3、13.2.1 节；第 5.3 节为工程约束索引。完整修订对照见[H01—H07 修订说明](智慧中台AI应用项目_概要设计审查修订说明_H01-H07.md)。

## 02 产品范围、分期与工程建设边界

### 2.1 完整场景与公共基座复用

| 场景 | 保留的业务规划与阶段 | 主要公共能力复用 | 场景自身负责的内容 |
|---|---|---|---|
| S01 供需与库存分析 | P0 分析；预测、滞销、供应商等按原规划扩展 | D01—D04、B01/B02、A01/A03、C01—C03 | 供需解释、候选方案约束、领域降级与建议判断 |
| S02 履约风险分析 | P0；运输方案扩展按原规划 | D01—D04、B01/B02、A01/A03、C01 | 履约窗口、异常判定、风险归因与处置建议 |
| S03 客户体验分析（VOC） | P0 | D01—D04、A02/A03、B01、C01—C03 | VOC 分群规则、成熟队列口径选择、工单建议 |
| S04 贡献与费用分析 | P0；费用审查扩展按原规划 | D01—D04、B01、A01/A03、C01 | 贡献口径使用、费用归因、证据组织与业务解释 |
| S05 客服辅助 | P1 | A01—A03、D01—D04、C01/C02 | 多语言、售后建议与人工确认；不因此开放客户消息发送 |
| S06 内容与增长辅助 | P1 | A01—A03、D01—D04、B01/B02、C01/C02 | 本地化、素材和广告建议；不因此开放自动投放 |
| S07 单证辅助 | P1 | D01—D04、A02/A03、C01/C02 | 字段比对、规则与人工复核；专业解析器按材料需要评估 |
| S08 经营规划 | P2 | D01—D04、B01/B02、A01/A03、C01/C02 | 市场、定价、多仓方案；不因此开放自动改价或调仓 |
| S09 视觉质检辅助 | P2 | D01—D04、A01/A02、C01/C02 | 图像检查标准、异常解释；视觉模型与算力另行验证 |
| S10 政策核查辅助 | P2 | D01—D04、A02/A03、C01/C02 | 政策版本适用、条款比对与专业复核；不把模型答复当最终合规结论 |

所有场景统一使用 W01、O01、G01/G02、I01。表中的复用是可调用的能力范围，不要求每次任务调用所有能力，更不要求一次部署全部候选存储或模型。

### 2.2 分期保持不变

| 原阶段 | 工程交付重点 | 进入下一阶段的证据 |
|---|---|---|
| M0 数据与授权验证 | 数据清单、身份/映射责任、接口样本、动作幂等与回执可行性 | 可研验证清单及真实系统责任人确认；不以 Mock 替代 |
| M1 公共基座 | 统一契约、权限、数据投影/质量/证据、任务、模型和指标基础 | 公共契约与可靠性测试通过，来源与指标可追溯 |
| M2 四类只读场景 | S01—S04 按公共契约接入；建议由用户按需创建 | 单场景与联合分析均满足原验收标准；建议不自动审批 |
| M3 有限写入 | 只开放验证通过的 ERP 采购草稿、CRM 内部工单动作 | 独立审批、幂等、UNKNOWN 恢复、权限和业务责任均验证 |
| M4 扩展规划 | 按需求推进 P1/P2 场景和确有收益的候选技术 | 每个场景单独通过数据、效果、成本与运营门槛 |

【确定】采购草稿创建不等于采购批准或到货，工单创建不等于问题解决。首期不增加库存调整、退款、支付、自动改价、自动投放或客户消息发送。后续新增写入动作必须经过独立的范围与风险评审。

## 03 五层逻辑架构到工程与部署的映射

### 3.1 逻辑模块、代码包和物理单元

| 逻辑层 | 既有模块 | 建议工程归属 | 物理运行位置 |
|---|---|---|---|
| L1 交互层 | W01 | workspace；HTTP 入口及前端交互契约 | 前端静态资源/现有门户 + FastAPI 进程；前端框架待选 |
| L2 场景与任务层 | S01—S10、O01 | scenarios、orchestration | 短命令在 API；持久分析在 Worker；共用同一代码制品 |
| L3 通用能力层 | B01/B02、A01—A03、C01—C03 | capabilities、collaboration | 作为 Python 模块被调用；重计算和外部执行由 Worker 承担 |
| L4 数据与集成层 | D01—D04 | data + 按归属组织的 adapters | Worker 同步、API/Worker 查询；MySQL 为权威持久化 |
| L5 基础设施层 | I01 | infrastructure + adapters | MySQL、进程运行、配置/凭据、任务领取、备份设施 |
| 横向治理 | G01/G02 | governance | API、Worker、工具和适配器边界均执行；不是单独部署要求 |

【确定】至少区分 API 与 Worker 的进程生命周期；【建议】同一版本制品、不同启动入口和配置，按实际负载配置 Worker 数量。API 重启不丢任务；Worker 重启不丢业务状态。前后端可通过现有入口部署，本文不新增网关或前端服务要求。

MySQL 是需要运行的持久化组件。云模型是外部依赖；本地模型服务仅在算力、许可和数据边界验证后部署。Milvus、Neo4j 均不出现在当前必需部署清单。执行凭据需要更强隔离时，可用同一 Worker 制品的受限执行角色/独立配置运行，不据此提前拆分独立业务服务。

### 3.2 工程模块与依赖图

下图为工程分层和主要依赖视图，不逐一展开第 5 节中的全部允许调用。实线表示主要使用依赖，虚线表示实现、注入或治理约束；不表示每个框都是一个进程。API 与 Worker 是入口，模块内部的数据访问须经所属 Repository 端口。

```mermaid
flowchart TB
  UI[W01 前端工作台] --> HTTP[entrypoints/http / FastAPI]
  HTTP --> APP[Application Services / W01、O01、C01—C03]
  WK[entrypoints/worker] --> APP
  APP -->|仅 O01 经 ScenarioHandler.analyze 调度| SH[scenarios / S01—S10 领域流程]
  APP -->|O01 共享快照与证据| DATA[data / D03、D04 公开契约]
  SH --> AI[capabilities / A01—A03 公共契约]
  SH --> B2[capabilities/forecasting / B02]
  B2 -->|候选情景指标评价，单向依赖| B1[capabilities/metrics / B01]
  SH --> B1
  B1 --> DATA
  SYNC[data / D01、D02 接入与投影] --> DATA
  WK --> I[infrastructure / I01 持久工作项与运行支持]
  APP --> I
  DATA --> PORTS[所属模块的 Domain / Repository 等端口]
  AI --> PORTS
  I --> PORTS
  ADP[adapters / MySQL、模型、读源、动作] -.实现对应端口.-> PORTS
  ADP --> DB[(MySQL)]
  ADP --> EXT[模型及业务源接口 / 读写适配分离]
  BOOT[bootstrap / 组合根] -.注入具体实现.-> APP
  GOV[governance / G01、G02] -.所有入口及调用边界强制治理.-> APP
```

图中 Application Services、Domain/Ports、adapters 是代码层和目录分组，不是新增的万能服务或统一执行器。O01 只直接使用 D03/D04 及联合报告限定的 A01/A03；场景按公开契约使用其他数据/能力。A02 需要模型时调用 A01；A03 即席查询由 W01 进入，指标查询复用 B01。这些细部调用按第 5、7、10 节执行，未在工程分层图重复连线。外部写入适配器只注入 C03，读源适配器只用于 D01；G01/G02 对所有边界生效，不能解读为只保护图中所连节点。

### 3.3 API、Service、Domain、Repository、Adapter

| 工程角色 | 职责与允许依赖 | 禁止内容 |
|---|---|---|
| API / 入口 | HTTP 参数与响应映射、身份建立、调用应用服务；Worker 入口接收已注册任务类型 | 在路由中计算供需、拼 Prompt、直接执行 SQL 或第三方写入 |
| Application Service | 所属模块用例、权限检查、事务边界、状态机与对外能力协调；依赖领域和端口 | 越过其他模块公开服务写其私有表；持有跨网络长事务 |
| Domain | 值对象、确定性规则、状态转换、不变量；依赖标准库及必要纯领域类型 | FastAPI、数据库 Session、模型 SDK、HTTP 请求上下文、环境变量读取 |
| Repository 端口 | 面向真实聚合/查询的数据契约，如 TaskStore、SnapshotReader；由需要它的模块拥有 | 全系统 GenericRepository/任意表 CRUD；跨模块共享 ORM 实体 |
| Adapter | 实现 Repository、ModelProvider、SourceConnector、ActionAdapter 等端口；封装 SDK、SQL、协议和重试事实 | 选择业务降级、暗改指标、在模型适配器中审批或执行工具 |
| bootstrap 组合根 | 装配配置、依赖、公开服务、注册表和客户端生命周期 | 承担场景流程；作为任意模块反向查找依赖的全局服务定位器 |

源码依赖方向是 **入口→应用服务→领域/所属端口；适配器→端口；组合根→具体实现**。运行时通过注入到达适配器，不意味着领域代码反向导入基础设施。跨模块仅导入对方公开契约/服务协议；DTO 与 ORM 不跨越持久化边界。内部 Python 调用不转成 HTTP 自调用。

【建议】HTTP DTO 使用 Pydantic 校验并转换为领域类型；领域金额、数量和状态规则保持可独立测试。使用异步 I/O 处理模型和数据接口，CPU 密集预测/视觉任务放入 Worker 的独立进程执行路径，不阻塞 API 事件循环。同步 SDK 如确有需要，在适配器边界使用有界隔离执行，不能默认为所有调用开无限线程。

## 04 建议代码目录与协作归属

### 4.1 分批创建目录，不提前生成空模块

以下均为未来工程提案，本轮不创建。目录分为“首批闭环实际需要”“后续公共能力有使用方时创建”“P1/P2 未来场景”三类。首批闭环是 M1 内部的工程验收切片，不替代 M0—M4，也不以补货或某个场景收缩完整产品范围。每个目录只有出现实际契约、用例或实现时才创建，不强制复制一套空 application/domain/ports/contracts。

```text
commerce-ai-hub/                         # 首批拟创建；当前仅目录设计
├─ pyproject.toml                        # 版本与依赖锁定后创建
├─ migrations/                          # 只建首批实际使用的表，单一历史
├─ src/commerce_hub/
│  ├─ bootstrap/                        # 配置与依赖装配，只注册已实现能力
│  ├─ entrypoints/
│  │  ├─ http/                          # app.py 工厂、分析/报告/健康入口
│  │  └─ worker/                        # __main__.py、领取与分派入口
│  ├─ contracts/                        # 确实跨模块使用的引用/身份/错误信封
│  ├─ workspace/                        # W01 分析提交、状态与报告视图
│  ├─ orchestration/                    # O01 最小任务、计划、预算及报告用例
│  │  └─ contracts/                    # AnalysisContext/ScenarioHandler/DomainResult
│  ├─ scenarios/
│  │  └─ s02_fulfillment/               # 首个真实调用公共能力的窄切片 Handler
│  ├─ capabilities/
│  │  └─ metrics/                      # B01 首批履约事实评价，不建空预测/AI 目录
│  ├─ data/
│  │  ├─ sync/                         # D01 最小批次/覆盖契约，测试夹具接入
│  │  ├─ projection/                   # D02 样例身份与事件投影
│  │  ├─ quality/                      # D03 真实持久化的质量/快照
│  │  └─ evidence/                     # D04 真实引用登记与解析
│  ├─ governance/
│  │  ├─ access/                      # G01 测试身份与数据范围校验，非认证旁路
│  │  └─ observability/               # G02 必需审计与 Trace
│  ├─ infrastructure/                 # I01 MySQL 工作项与运行配置
│  └─ adapters/
│     └─ mysql/<owner>/               # 仅首批模块的 Repository 与事务适配
├─ tests/
│  ├─ fixtures/                        # 明示 simulated 的 D01 测试连接器与样本
│  ├─ contract/                        # 实际使用的协议
│  ├─ integration/                     # API—MySQL—Worker 闭环
│  └─ faults/                          # 回滚、崩溃、越权、重复处理
└─ docs/                               # 契约、配置、迁移、验收与交接说明
```

前端工程归属待企业现有门户和团队技术栈确认，概要阶段不凭空选定 React/Vue。前端只消费 W01/API 的契约，不直接访问数据库、模型密钥或 Worker。不存在没有明确职责的 utils、万能 common、通用索引工厂或独立 Memory 服务。

| 创建类别 | 后续目录归属 | 创建触发条件 |
|---|---|---|
| 后续公共能力 | capabilities/forecasting（B02）、models（A01）、understanding（A02）、retrieval（A03） | 对应预测/模型/理解/检索用例已排期且有真实使用方；A03 即席启用须同时实现第 6.4 节控制 |
| 后续协作能力 | collaboration/suggestions（C01）、approvals（C02）、executions（C03） | 建议协作用例进入交付；C01/C02 原子提交按第 12.3 节，写动作另过 M3 门槛 |
| 后续数据/基础设施适配 | adapters/sources、actions、models、retrieval | 某个具体连接器/动作/提供方/索引被验证并纳入实施；不先建厂商空目录 |
| P0 后续场景 | scenarios/s01_supply_inventory、s03_customer_voc、s04_contribution_fees | M2 分步实施，不因首批用 S02 验证工程链而删减 |
| P1/P2 未来场景 | scenarios/s05_customer_assistance、s06_content_growth、s07_documents、s08_planning、s09_visual_quality、s10_policy_check | 依原业务规划逐项排期；当前只保留目录归属说明 |

### 4.2 最小可运行代码基座的交付定义与依赖顺序

【建议】最小交付不是“API 能启动”或“静态返回报告”，而是用真实 MySQL、两个独立进程、已注册的 S02 窄切片 ScenarioHandler，走通 **API→任务与工作项原子落库→Worker 领取→O01 派发场景→公共指标/快照/证据→持久报告→API 读取**。源数据使用模拟夹具；任务、数据库事务、租约、授权、Handler 调用和报告持久化不得模拟。不开启模型调用和外部写动作，不把未实现的模块注册成伪成功能力。

| 开发顺序（未来实施） | 最小模块/产物 | 前置依赖与完成定义 |
|---|---|---|
| 1 版本与边界冻结 | 已选 Python/依赖锁、配置 schema、现有公共契约所需子集 | 先解决 V01/V12；不生成无人使用接口；冻结测试夹具口径 |
| 2 持久化与治理 | I01 连接/短事务/工作项；G01 测试身份/范围；G02 审计/Trace；对应迁移 | MySQL 可用且迁移显式执行；具备事务回滚和租户隔离测试 |
| 3 数据切片 | D01 测试连接器、D02 投影、D03 质量/manifest、D04 引用；B01 一项履约评价 | 使用第 2 步持久化与治理；夹具经所有者公开用例装载，不直接散写业务表 |
| 4 领域与编排 | S02 Handler；O01 SINGLE 任务、计划、持久报告和取消点 | S02 真正调用 B01 与数据公开契约；O01 只经 ScenarioHandler 调度；JOINT 契约保留，未实现能力明确拒绝 |
| 5 两个入口装配 | W01/API、独立 Worker、bootstrap | 由组合根注册第 2—4 步实际实现；API 与 Worker 使用同一迁移版本和同一 MySQL |
| 6 闭环与故障验收 | 第 4.3 节逐项证据、操作说明、最小 CI | 不以单元 Mock 测试代替跨进程和真实 MySQL 验证；通过后再依原 M1/M2 计划扩展公共能力 |

建议运行入口如下，均为未来开发后的操作约定，本轮不执行：

| 入口 | 拟定启动方式/责任 | 启动依赖与边界 |
|---|---|---|
| 数据库迁移 | `alembic upgrade head`，独立运维/开发命令 | 配置与版本已冻结→MySQL 就绪→迁移完成；API/Worker 不自行迁移 |
| API | `uvicorn commerce_hub.entrypoints.http.app:create_app --factory` | MySQL/迁移/必要配置就绪；提供 `/health/live`、`/health/ready` 及分析/报告资源；ready 校验其真实依赖 |
| Worker | `python -m commerce_hub.entrypoints.worker` | 与 API 相同代码/配置版本；MySQL/迁移就绪；只领取已注册 workKind；不由 API 启动 |
| 样例装载 | tests/fixtures 的测试装载过程调用 D01/D02 用例 | 仅显式测试环境，标示 simulated；不是生产公开 API 或后台常驻导入服务 |

启动顺序为“冻结配置与依赖→MySQL→迁移→测试数据装载→API 与 Worker（两者可分别启动）”。可以先停 Worker 证明 API 受理后的任务仍持久存在；前端框架、云模型、Milvus、Neo4j、C01—C03 都不是此闭环运行依赖。

### 4.3 最小代码基座交付与客观验收清单

以下 MC 编号是验收项，不是新增模块。样例采用 S02：固定 asOf 下，夹具订单 A 已超承诺时点仍未完成、B 尚未到承诺时点；具体字段/期望值在测试 fixture 与 B01 评价样例中显式冻结，仅为工程验证，不代表企业正式履约口径。

| 编号 | 交付/操作 | 可客观验收的结果与证据 |
|---|---|---|
| MC01 | 从干净测试库显式迁移；独立启动 API、Worker | 迁移版本可查、ready 通过；两个 PID/入口可独立停止，无额外中间件依赖 |
| MC02 | 通过受控测试过程装载 D01 模拟批次 | 可查 simulated 来源、批次/覆盖、D02 修订、映射版本及预期 A/B 数据；不冒充真实接口 |
| MC03 | 已授权身份提交 `POST /api/v1/analysis-tasks` | 返回 202/taskRef/Location；提交后 MySQL 同时存在同一 tenant 的 task/plan 与工作项及必需审计 |
| MC04 | 在任务/工作项落库中间注入失败 | task、work 和必需审计全回滚，不返回受理成功；重复命令不产生第二个任务 |
| MC05 | 先停 Worker，受理任务后重启 API，再启动 Worker | 原 taskId 仍可查询并被处理；不依赖 API 内存或 BackgroundTasks 续跑 |
| MC06 | 跟踪 Worker→O01→S02.analyze | 同一 trace/task/plan/participant/snapshot 引用链；确认调用 S02/B01，不能静态拼一份 DomainResult 冒充执行 |
| MC07 | 检查固定输入、计算和报告 | D03 manifest 可解析，B01 输出夹具约定的确定性超时指标，S02 据其规则标出 A 风险、B 不被误报；D04 引用能回源；O01 发布报告并持久关联产物 |
| MC08 | 使用 `GET /analysis-tasks/{id}` 与报告 API，重启进程后再读 | 查询得到终态和 reportRef；报告/证据版本保持，未自动产生建议、审批或执行记录 |
| MC09 | 两个 Worker 竞争领取、失租约的旧 Worker 迟到 | 当前 token 才能提交；同 task/plan/snapshot 的重复处理不重复发布逻辑结果/报告版本，恢复不丢任务；过程有审计 |
| MC10 | 注入只读步骤崩溃、已提交报告但工作项未完成、重试超限 | 按第 11 节重入/复用已完成结果；已发布报告不重复创建；超限明确失败/待人工，不无限重试 |
| MC11 | 跨租户读取、扩大 scope、未注册场景或缺必需数据 | 拒绝越权/不支持能力；质量缺口明确阻断相关结论，不把缺失当零/成功 |
| MC12 | 取消排队/运行任务，检查配置、日志及文档 | 安全检查点生效，迟到结果不复活；无明文秘密；交付契约、迁移/运行/配置/测试证据和交接清单 |

MC01—MC12 是未来开发交付的通过条件，本次均只定义验收方法，未执行也不标记通过。后续公共能力启用的附加门槛分别为：C01/C02 的事务故障测试见第 12.3 节，A03 即席控制测试见第 6.4 节，C03 来源校验与 UNKNOWN 测试见第 13.2.1 节；不把这三项扩展的实际代码混入最初运行闭环。

### 4.4 模拟与真实验证的证据分级

模拟连接器仅替代外部源读取，不能替代 MySQL、事务、Worker、权限或报告。测试身份仍须验证签名/范围，测试密钥与发行方仅用于隔离环境，生产不得开启匿名绕过模式。模拟数据报告必须携带数据来源标记及限制，可证工程链路和恢复行为；不能证明真实接口连通、授权、覆盖、新鲜度、映射质量、业务收益或生产容量。

真实只读集成另需企业测试接口/受控导出、来源责任人、实际分页/限流/删除/时区/覆盖与质量记录；真实写入还必须逐动作证明源前置条件、原子条件执行、幂等、回执与人工责任。证据分别标注“模拟工程验证 / 真实只读验证 / 真实动作验证”，前一级通过不自动获得后一级资格，M0/M3 门槛不变。

## 05 模块公共契约与唯一责任

### 5.1 公开接口目录

以下方法为建议的模块级接口语义，不承诺最终函数签名。`Ref` 均包含资源 ID、版本与租户范围；调用还须携带服务端生成的授权上下文、Trace 和必要的预算许可。返回大型结果时返回受控引用及摘要，不在每层复制全文。

| 模块 | 职责与建议公开接口 | 输入 → 输出 | 上下游及扩展方式 |
|---|---|---|---|
| W01 | 工作台查询、分析和人工操作入口；`submit_analysis`、`read_report`、`submit_approval_command` | 用户参数/明确操作 → taskRef、只读视图、命令结果 | 调 O01、A03 即席查询、C01/C02/C03 公开用例；新增页面复用既有命令，不增加前端业务状态权威 |
| O01 | `create_task`、`run_task`、`cancel_task`、`read_report`；内部计划、预算、调度、联合报告职责分工 | AnalysisContext → task/plan、DomainResult 引用、reportRef | 调 ScenarioHandler、D03/D04；A01/A03 仅联合报告解释/检索；新增场景通过注册表，非新分支堆入调度器 |
| D01 | `sync`、`read_batch_status`；只读取数/游标/覆盖范围 | SourceRequest、cursor、授权范围 → SourceBatchRef、coverage、技术错误 | 外部只读接口→D02；新增 SourceConnector，必须声明分页、增量/删除、限流及授权能力 |
| D02 | `normalize_batch`、`resolve_identity`、`read_projection` | batchRef、mapping/ruleVersion → projectionRevisionRef、映射问题 | 消费 D01；供 D03/B01/A02/A03 按公开查询读取；新增标准化规则不改源系统事实 |
| D03 | `check_quality`、`freeze_snapshot`、`read_manifest` | participant 数据需求、scope、asOf、投影版本 → QualityResult、snapshotId/manifest | 读 D01 覆盖元数据与 D02 固定版本；供 O01/场景；新增领域质量规则，快照仍唯一归属 D03 |
| D04 | `register_evidence`、`resolve_evidence`、`read_lineage` | 受控资产/结果引用、位置、版本、权限 → evidenceId、证据视图/血缘 | 引用 D03 快照、B/A 结果及来源；供报告/建议/工具；新证据类型只增解析适配，不复制原文与指标 |
| B01 | `evaluate_metrics`、`read_metric_result` | MetricRequest、事实或显式假设输入引用、metricDefinitionVersion → MetricResultRef、质量/约束 | 读 D02/D03；被场景、B02、A03 受控指标工具调用；新增指标注册口径与测试，唯一计算实现 |
| B02 | `forecast`、`evaluate_candidates` | ForecastRequest、约束、候选假设、模型版本 → Forecast/ScenarioResultRef、B01 评价引用 | 场景→B02→B01；新增预测器/候选策略；不实现第二套逐日平衡/缺口公式 |
| A01 | `invoke_model`、`describe_capabilities` | ModelRequest、上下文片段、输出模式、调用许可 → ModelResponse/TechnicalError、usage | 由场景/A02/A03/O01 报告环节调用；注入 ModelProvider；不执行工具、不判断业务降级 |
| A02 | `understand`、`revise_annotation` | 文本/文档/图像受控引用、taxonomyVersion → 结构化标签、置信度/UNKNOWN、修订引用 | 读 D02/D03，需要时调 A01；供场景/B01 使用其结果；不计算投诉率分母、不自行合并身份 |
| A03 | `retrieve`、`query_semantic`、`invoke_read_tool`；即席入口运行控制见 6.4 | QuerySpec、受信 QueryRunContext 或任务许可、scope、版本 → 证据/指标引用、受控结果及 usage | 读 D02/D03/D04，指标调用 B01；解释需要时调 A01；即席许可不得由调用者自签 |
| C01 | `create_suggestion`、`confirm`、`submit_for_approval`、`supersede`；独立只读版本视图 | 已发布分析/证据引用、用户选择、版本 → SuggestionRef、确认状态/approvalRef | SubmitForApprovalUseCase 为提交事务唯一协调者，经注入的 C02 提交命令协作；只写 C01，详见 12.3 |
| C02 | `submit_approval`、`decide`、`revoke`、`validate_approval` | 冻结建议/动作/指纹、审批人操作 → ApprovalRef、当前有效性及范围 | 提交命令不回调 C01；决策用例经独立只读端口核验建议版本，不依赖 C01 提交服务，详见 12.3 |
| C03 | `request_execution`、`dispatch`、`reconcile_receipt`、`read_execution` | 有效审批引用、明确执行命令、executionKey → ExecutionRef、源记录/回执状态 | 检查 C01/C02/G01，借 I01 排队，调用 ActionAdapter；唯一外部写入模块 |
| G01 | `authenticate`、`authorize`、`derive_scope` | 验证后身份、资源/动作/工具、当前策略 → EffectiveScope/允许或拒绝 | 所有入口及敏感调用；角色、数据范围、字段与动作规则扩展；不让调用方自报可信权限 |
| G02 | `record_audit`、`record_usage`、`record_trace`、`evaluate` | 最小事件、版本/引用、Trace、评测结果 → 审计/观测/评测记录 | 横向采集；不成为报告、审批或业务指标的第二权威；后续可导出外部观测平台 |
| I01 | `enqueue`、`claim`、`heartbeat`、`complete`、`retry_later`；配置/连接/备份支持 | workKind、owner/payloadRef、lease → workRef、领取许可/投递结果 | 仅通用领取、租约和有界重投；C03 发送/核对选择归 C03，详见 11.2—11.4 |

### 5.2 O01 内部职责不拆服务

| 内部职责 | 边界及输入输出 |
|---|---|
| 任务与参与者管理 | 校验 SINGLE/JOINT、登记 participant、建立计划与版本；不实现任何场景领域步骤 |
| 计划/预算协调 | 冻结 budgetPolicyVersion、分配并行槽、重规划判定和调用预算；不替场景决定领域降级 |
| 快照协调与派发 | 按参与者数据声明向 D03 请求一致锚点与 manifest，注入受限视图给 ScenarioHandler |
| 联合审查、报告组合与发布 | 聚合 DomainResult 引用、冲突/缺证据判定、联合层降级、只读报告发布；不重新计算 B01/B02/A02 结果 |

这些是 O01 内部类/用例组织建议，仍共享一个任务领域和版本记录。单场景也经过同一任务流程；没有第二套“单 Agent 专属调度器”。报告审查发现领域结果需重算时，重新派发对应 ScenarioHandler，不能直接调用领域能力修补结果。

### 5.3 统一工程规则与细则维护位置

本表是约束索引；算法、状态和事务细则只在指定章节维护，其他章节使用规则号/章节引用，不各自新增例外。ER 编号是文档规则，不是模块。图中的控制点必须对应这些细则。

| 规则 | 允许的工程路径 | 禁止内容 | 细则唯一维护位置 |
|---|---|---|---|
| ER01 任务与场景 | O01→ScenarioHandler→领域能力→DomainResult | O01 直接执行 B01/B02/A02 领域步骤；场景反向调度或隐藏参与者 | 5.2、7.1—7.2 |
| ER02 计算唯一性 | B02 单向调用 B01 评价事实/假设 | B01 依赖 B02；重复逐日指标公式 | 5.1 中 B01/B02 契约 |
| ER03 模型边界 | A01 只返回技术结果；业务调用方决定流程 | A01 决定业务降级、执行工具或审批 | 10.1—10.2 |
| ER04 数据所有权 | 经所有者公开接口/授权只读投影访问 | 跨模块私有表写入、共享 ORM、把投影当源事实 | 8.1—8.4、9.1 |
| ER05 只读工具 | A03 白名单与 G01 后端强制权限 | 模型工具注册 C03 写动作、任意 SQL/Cypher/shell/HTTP | 10.2 |
| ER06 人工控制 | 明确确认、提交、独立审批、另行执行 | 确认即提交、批准即执行 | 13.1 |
| ER07 即席查询 | W01→A03 的受控只读 QueryRun；正式分析→O01 | 无预算/无期限查询或包装成正式联合报告 | 6.4 |
| ER08 本地事务 | 唯一发起协调者、共享一条 MySQL 短事务 | 内层独立 commit、新事务、跨网等待、服务循环 | 12.1、12.3 |
| ER09 投递与外部恢复 | I01 有界重投；C03 根据执行状态决定发送或核对 | 通用工作项推断外部结果、租约失效即盲目重发 | 11.2—11.4、13.2—13.2.1 |
| ER10 有界调用 | 运行作用域内预留/结算，同一次调用关联审计 | 子 Agent/重试重置预算；切入口获得无约束额度 | 正式任务 7.3；即席 6.4 |

### 5.4 抽象的实际需求与克制范围

| 抽象/端口 | 服务的真实需求与至少一个用例 | 当前范围与不预建内容 |
|---|---|---|
| ScenarioHandler | S02 单场景和 S03+S04 联合分析采用同一调度协议 | 固定输入/输出/取消点；不做通用 DAG 平台 |
| MetricEvaluator（B01） | B02 对多个候选供需情景复用逐日评价 | 指标契约；不抽象任意计算引擎 |
| ModelProvider（A01） | 云 API 与本地模型协议不同且可能切换 | invoke/capabilities/technical errors；不统一所有厂商附加功能 |
| SourceConnector（D01） | ERP、物流、CRM 的分页、增量和限流不同 | 只读取数和覆盖声明；不预建所有平台 SDK |
| ActionAdapter（C03） | ERP 草稿和 CRM 工单的幂等、回执各异 | 前置核验、execute/queryReceipt；无证明的动作不注册启用 |
| RetrievalProvider（A03） | 知识/证据检索可由基础关系查询或未来向量/图查询实现 | 受控 QuerySpec→引用；不先建万能 IndexStore |
| 所有者 Repository 端口 | O01 保存计划，D03 固定 manifest，C02 保存批准版本 | 按真实聚合/查询定义；无 GenericRepository 或跨模块万能 CRUD |
| TaskBudgetHandle（O01） | S03、S04 并行调用不能各自消耗完整任务预算 | 仅正式分析任务预留/结算；即席在 A03 应用用例内按 6.4 控制，不反向创建 O01 假任务 |
| 持久 WorkItemStore（I01） | API 重启不丢分析，C03 崩溃后能回执核对 | MySQL 领取/租约/恢复；无消息平台抽象大而全实现 |
| 本地事务范围 | 创建 task+work、提交 suggestion+approval 需原子落库 | 单 MySQL 短事务；无分布式事务框架 |
| C01 ApprovalSubmitPort / C02 SuggestionRevisionReader | 前者供提交协调者调用 C02 命令；后者供 C02 决策核验建议版本 | 两个有真实使用方的窄端口，由组合根分别注入 C02 提交、C01 只读视图；不互相注入完整 Service，详见 12.3 |

新增抽象必须同时交代所有者、现有用例、公开输入输出及测试边界。没有真实使用方的能力只记入待验证清单，不提前生成代码接口或独立组件。

公开契约沿用基线的 `ScenarioHandler.analyze`、`ActionAdapter.execute/queryReceipt`、MetricDefinition、Forecast/OptimizerProvider、UnderstandingProvider、Retrieval/QueryProvider 等语义。未来 Python 方法可按工程规范采用 snake_case，但须在接口说明中一一映射，不能借更名改变责任或协议。第 5.1 节列出的模块应用用例并不取代这些扩展契约。

## 06 核心数据结构、契约版本与 HTTP 边界

### 6.1 AnalysisContext 与参与者视图

保留基线 `schemaVersion="0.2"` 的统一结构。下例为冻结前的 JOINT 任务；时间与业务参数仅为结构示意，不是企业配置。

```json
{
  "schemaVersion": "0.2",
  "taskId": "task_example",
  "analysisMode": "JOINT",
  "participants": [
    {"participantId": "p_voc", "scenarioId": "S03", "scenarioVersion": "0.1", "required": true, "businessParameters": {"cohortPolicyRef": "voc_policy_example"}},
    {"participantId": "p_fees", "scenarioId": "S04", "scenarioVersion": "0.1", "required": true, "businessParameters": {"metricPolicyRef": "fees_policy_example"}}
  ],
  "scope": {"tenantId": "tenant_example", "storeIds": ["store_example"], "warehouseIds": [], "canonicalSkuIds": []},
  "window": {"asOf": "2026-11-11T00:00:00Z"},
  "planVersion": null,
  "snapshotId": null,
  "policyContextRef": "server_policy_example",
  "budgetPolicyVersion": "budget_policy_example",
  "budget": {"maxDomainParallelism": 2, "maxReplans": 1}
}
```

【确定】SINGLE 采用完全相同结构且恰好一个参与者；JOINT 至少两个，参与者数量可以大于并行度，按波次执行。O01 冻结 planVersion，D03 冻结 snapshotId，不能由客户端伪造。scope 与 policyContextRef 由服务端核准；“空仓库/SKU 列表”的全量或不适用含义由 QuerySpec 明示，不能因空值放宽授权。

共同 `asOf` 是一致分析锚点，不要求各领域窗口相同。S03 的成熟订单队列、S04 费用期间、S01 未来供需窗口在各参与者业务参数/口径中声明。子参与者获得同一 task/plan/snapshot 的受限只读视图，不另造一份互不相干的 AnalysisContext。确需新增实际场景时须显式变更 participants/analysisMode 并走重规划，不能暗中跨域。

| 契约 | 主要字段与所有者 | 关键约束 |
|---|---|---|
| CommandContext | G01 产生 principalRef、effectiveScope、policyVersion；入口补 traceId、commandId | 不保存长期可复用用户 Bearer Token；Worker 恢复按当前策略复核 |
| DomainResult | O01 契约：participantId/scenarioId/scenarioVersion、taskId、planVersion、snapshotId、结论摘要、artifact/evidenceRefs、constraints、领域输出状态 | 必须匹配当前计划与参与者；不复制所有指标明细；未知/不完整不得伪装为完整结果 |
| MetricRequest/Result | B01：metricDefinitionVersion、inputRef、事实/假设类型、窗口、单位、resultRef、quality | 候选假设显式标注；使用同一评价器与口径，不把预测值冒充事实 |
| ModelRequest/Response | A01：provider/modelRef、prompt/contextVersionRefs、outputSchemaVersion、callAllowanceRef、deadline；输出内容、toolRequests、usage/技术状态 | 技术失败不带业务降级结论；厂商扩展保留在适配器内，结构校验不可跳过 |
| EvidenceRef | D04：evidenceId、assetRef/assetVersion、locator、snapshot/resultRef、权限标签、lineage | 引用可解析、可鉴权；hash 只辅助完整性，不代替原始证据或权限 |
| Suggestion/ApprovalRef | C01/C02：各自 ID/version、actionType/version、scope、payloadFingerprint、有效期 | 确认、提交、批准各自留痕；改建议内容使原批准不再覆盖新内容 |
| ExecutionRequest/Receipt | C03：executionKey、approvalRef、actionType/version、requestFingerprint；源 recordId/status/observedAt | 相同 key 不得换 payload；技术接收与业务动作结果分离 |
| WorkItem | I01：workId、owner、workKind/version、payloadRef、dedupeKey、runAfter、attempt、leaseToken/expiry | 保存投递元数据而非第二份业务状态；仅执行注册类型，不反序列化任意可执行对象 |
| 版本化事件信封 | 原业务生产者：eventId、schemaVersion、producer、tenantId、aggregateId/Version、occurredAt、traceId、payloadRef | 生产者唯一、消费去重；可在本地事务/既有工作项中传递，不要求新增消息总线 |

### 6.2 版本兼容与结果重放

【建议】HTTP 路径大版本 `/api/v1` 与 AnalysisContext schema 版本、指标版本、计划版本独立。契约可选字段新增需给定安全默认并通过消费者契约测试；删除字段、改变单位/空值语义/权限行为须升级不兼容版本和迁移计划。计划、快照、提示词、模型标识、工具、映射、指标和审批版本分别记录，不以一个“系统版本号”替代。

分析结果至少可追溯 `task/participant/plan/snapshot + scenario/metric/model/prompt/tool/policy versions + evidenceRefs`，完整关联可经引用链取得，不要求在每行重复全部字段。代码发布以提交/制品版本记录。重放优先复用固定输入及已保存产物；模型输出受供应商版本和采样影响，不能承诺仅凭同一 Prompt 必然逐字复现。

### 6.3 HTTP 与前后端边界

| 建议资源接口 | 应用服务归属 | 行为与响应边界 |
|---|---|---|
| `POST /api/v1/analysis-tasks`、`GET .../{id}`、`POST .../{id}/cancel` | W01→O01 | 创建持久任务返回 202/taskRef/Location；查询与取消都验证数据范围 |
| `GET /api/v1/reports/{id}` | W01→O01 | 返回有权限的已发布版本；下载/证据访问重新鉴权 |
| `POST /api/v1/queries` | W01→A03 | 同步、有界、只读；先建立第 6.4 节 QueryRun 控制，不允许任意 SQL 或替代正式分析 |
| `POST /api/v1/suggestions`、`POST .../{id}/confirm`、`POST .../{id}/submit-approval` | W01→C01 | 每个动作来自明确用户操作；提交才产生 C02 PENDING |
| `POST /api/v1/approvals/{id}/decision`、`POST .../{id}/revoke` | W01→C02 | 核验审批人身份、独立性、版本与状态；批准不排执行任务 |
| `POST /api/v1/executions`、`GET .../{id}` | W01→C03 | 明确执行命令 + 当前有效审批；返回受理引用，不把 202 当源写入成功 |

以上为资源级概要，不是本轮完整 OpenAPI。前端可先轮询状态，WebSocket/SSE 暂无必需证据。建议统一错误信封含 `code/message/details/traceId/retryable`，details 脱敏。401 表示未认证、403 表示未授权，资源存在性需掩蔽时使用统一 404；422 为参数错误，409 为版本/状态冲突。已受理异步任务的业务失败由任务/报告查询表达，不以最初 HTTP 成功码隐含业务成功。前端不得自行推断审批有效性或执行终态。

### 6.4 W01→A03 即席查询的独立运行控制

【建议】此入口仅处理短时受控查询，不创建 O01 task/plan/report，也不把用户问题送入无界 Agent Loop。W01 建立身份与命令上下文，调用 A03 的即席应用用例；**A03 是本次 QueryRun 的运行协调者**，G01 提供当前授权与获准策略，A01 仍只负责技术模型调用，G02 唯一记录调用成本事实、审计与 Trace。复杂/长时/需要场景判断的问题返回 `ANALYSIS_TASK_REQUIRED` 并提示用户显式提交 O01，不能暗中启动第二套正式分析。

| 控制点 | 责任与最小设计 | 拒绝/失败行为 |
|---|---|---|
| 授权与上下文 | W01 验证身份；A03 再用 G01 生成 effectiveScope、字段/工具/模型数据边界与 queryPolicyVersion；QueryRunContext 属 A03，含 queryId、principal/tenant、scope、deadline、budgetRef、traceId | 参数不能扩大范围；检索预过滤、证据解析复核同正式链路；授权失败不调用数据/模型 |
| 请求与周期额度 | A03 同时约束单 query 的模型/工具次数、tokens、费用、结果规模，以及同租户/用户的查询周期额度和并发数；预留后调用，结束结算 | 不允许反复新建 queryId 重置周期额度；同命令 key + 同指纹复用结果/处理中状态，不重复发起；异指纹拒绝 |
| 持久化与并发 | 启用即席时才增加 A03 的 adhoc_query_run 与 adhoc_quota_window 运行记录；同 MySQL 短事务锁定额度窗口、登记预留并提交，结束条件结算 | 不是业务事实/报告账本或新预算平台；多 API 实例不能仅靠进程内计数；窗口按服务端时间划分 |
| 超时/取消 | 服务端冻结 queryDeadline；下游 deadline 为本次剩余时间与各适配器超时的较小值；客户端只能缩短，所有重试也消耗原次数和时间 | 到期停止新调用；断连/进程崩溃不代表供应商未计费，未知消耗保持占额，关闭查询重试权限并待核对 |
| 成本与审计 | A01 向 G02 记录带 queryId/callId 的技术 usage；A03 向 G02 记录工具、决策、拒绝/超时与结算关联；callId 去重，避免两次计费统计 | A03 额度余额只是控制状态，G02 为成本/审计事实；无法确认 usage 不能按零结算；必需运行/审计记录不可写时拒绝新查询；调用后 usage 不明保留占额和待核对关联 |
| 响应与终点 | 返回受控结果/证据与 queryId、版本/范围限制，不生成 O01 正式 reportVersion 或 C01/C02/C03 记录 | 错误按 6.3 安全信封返回；不把即席文本包装成跨领域正式结论 |

复用第 7.3 节的预留/结算规则、MySQL 条件更新方式以及已有 G01、A01、G02、A03 检索/工具契约；TaskBudgetHandle 仍归 O01 正式任务。A03 的控制在自身应用用例内实现，不抽出独立 BudgetService、通用额度框架或新增模块，也不调用 O01 为查询伪造任务。两种入口可复用经过验证的纯计算/计费值对象；没有两个真实实现前不额外抽象接口。

未配置获准上限、超时或可信计费版本时，有费用的模型查询默认关闭（modelCalls=0），只开放已配置有界的确定性只读查询；不使用“无限”兜底。具体请求/周期金额、tokens、次数和期限属 V05，实际启用前必须冻结并验证。G01 策略为即席和正式入口明确分配额度，不能各自使用同一笔未扣减的剩余预算；若企业要求跨入口共享实时总额硬上限，在统一并发核算方案验证前不启用涉及该总额的收费入口，不声称两份独立计数已实现全局封顶。

任何即席数据访问前先持久化运行控制及必需审计；收费模型调用还须先持久化费用预留，再调用供应商。若崩溃/超时导致结算未知，A03 通过其 queryId/callId 读取已有 G02/供应商可得记录，由同一应用用例核对；不能自动退款额度再执行同一请求。必要的核对可用既有 I01 工作项，不建立独立恢复平台；供应商无法核对时保守保留占额并交人工。来源事实/模型输出不复制为长期 Memory。

启用验收至少证明：两个 API 实例竞争额度不超发；单次和周期任一额度耗尽都不调用模型；越权请求零数据泄露；多工具/重试共享原 queryDeadline；响应丢失仍保留未知消耗；相同 commandId 不二次执行；queryId/callId 可追到 G02 成本和审计；正式任务与即席不能通过切换入口扩大权限或重复使用已分配额度。此为后续启用测试计划，本轮不执行。

## 07 单场景与跨领域任务执行

### 7.1 统一工程路径

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant W as W01 / HTTP
  participant O as O01 应用服务
  participant J as I01 持久任务
  participant R as Worker
  participant D as D03 快照
  participant S as ScenarioHandler
  participant P as B01/B02/A02/A03/A01
  participant E as D04 证据
  U->>W: 提交单场景或联合分析
  W->>O: 已授权的 AnalysisContext
  O->>J: 同一短事务保存任务与待处理项
  O-->>W: 202 / taskRef
  R->>J: 领取并提交租约
  R->>O: run_task(taskRef, leaseToken)
  O->>D: 按参与者声明冻结共同锚点和输入版本
  D-->>O: snapshotId / manifest / quality
  break 关键数据不达标，既有策略不允许继续相关分析
    O->>O: 发布阻断/有限信息与待补事项，不派发无依据步骤
    O->>J: 记录本次处理完成
  end
  alt SINGLE：如 S02
    O->>S: analyze(单参与者视图, budgetHandle)
    S->>P: 按 S02 领域流程调用公共能力
    P-->>S: 固定版本产物/技术错误
    S-->>O: DomainResult / 领域降级结果
  else JOINT：如 S03 + S04
    loop 按可配置并行度分波调度参与者
      O->>S: analyze(各参与者受限视图, 共享预算)
      S->>P: 领域步骤及确定性计算
      P-->>S: 各能力结果引用
      S-->>O: 各自 DomainResult
    end
  end
  O->>E: 校验证据引用和权限
  E-->>O: 可发布证据视图/缺口
  opt 仅联合报告解释确需 AI 或检索
    O->>P: 仅 A01/A03 报告级调用，计入共享预算
    P-->>O: 解释/引用或技术错误
  end
  O->>O: 审查冲突、应用联合降级；需重算则重派场景
  O->>O: 核验计划/租约，保存并发布报告版本
  O->>J: 记录处理完成
  W->>O: 查询已发布报告
  O-->>W: 报告 / 候选建议 / 完整性状态
  Note over W,R: 首批最小闭环仅启用 S02 窄切片与 simulated 源数据，持久任务/Worker/快照/报告均真实运行
  Note over U,O: 只读流程到报告结束；不自动创建建议、审批或外部动作
```

图中循环是逻辑波次表示，实现可并行运行，但每个并发分支独享数据库 Session。公共能力 P 是为缩短时序图的参与者分组，不允许通过一个万能执行器绕过模块契约。O01 的两处 P 调用中，前者来自场景领域流程，后者严格限联合报告 A01/A03；没有 O01→B01/B02/A02 的隐藏调用。

### 7.2 计划、检查点与业务降级

【确定】领域输入不足、预测不可用、分类置信度不足的业务处理由 ScenarioHandler 决定；跨参与者结果缺失、冲突、联合报告证据不足由 O01 决定。A01 仅返回 timeout、rate_limit、provider_unavailable、invalid_response 等技术事实。A02 的 UNKNOWN 是语义输出，不等同于 C03 的外部执行 UNKNOWN。

【建议】每个场景声明依赖、required/optional 结果及可用降级策略版本。检查点绑定当前 task/plan/participant/snapshot 与输出引用。恢复时只复用版本匹配、证据仍可访问的已完成产物。计划失效/输入变更时重派场景，而不是手工覆盖报告里的指标数字。

联合层可输出 COMPLETE、PARTIAL、RULES_ONLY、BLOCKED 等报告完整性语义，具体适用条件由原业务口径冻结；这些不是 A01 技术错误码，也不是任务投递状态。必需参与者失败不能默认为可跳过；哪些场景允许 PARTIAL 或规则模式须完成业务降级矩阵确认后才能启用。

### 7.3 可配置预算

| 参数 | 默认/确定程度 | 调整依据与约束 |
|---|---|---|
| maxDomainParallelism | **2，沿用基线** | 正整数；基于连接池、源限流、模型配额、峰值及耗时验证；多场景排队不丢弃 |
| maxReplans | **1，沿用基线** | 非负整数；新增参与者、改变依赖/需重算的输入变更才计重规划；普通取证不另算重规划 |
| taskDeadline、模型/工具调用数、tokens/费用上限 | 【建议】必须配置；数值待测 | 用可研压力情景和真实负载校准，未冻结前不开放无上限生产运行 |
| retryLimit、backoff、providerTimeout | 【建议】按只读/模型/动作分别配置；值待测 | 依据错误类型、供应商限流、回执 SLA 和剩余预算；不是一个全局重试装饰器 |
| leaseDuration、heartbeatInterval、pollInterval、claimBatchSize | 【建议】配置；值待负载与恢复演练冻结 | 心跳显著短于租约，数据库时间判定；选择领取索引/批量上限，避免轮询拖累业务 |

任务启动时固定 budgetPolicyVersion 和有效上限，后续策略调整不改写历史任务。O01 TaskBudgetHandle 在并发模型/工具调用前原子预留额度，完成后结算实际 usage；未知消耗保守占额并记录待核对，不因超时自动退还全部预算。场景、联合审查、检索与重试共用总预算，不能每个 Agent 重新获得一份上限。技术超预算返回调用受限事实；是否降级/终止由对应场景或 O01 决策并审计。

## 08 MySQL 数据域、归属与概要模型

### 8.1 核心数据域

MySQL 保存关系型业务投影、任务/审批/执行和审计。下列为**候选逻辑表组**，用于说明所有者、关系与设计原则，不是待一次性执行的 DDL；P1/P2 不在本轮提前建全表。

| 唯一写入所有者 | 概要表组示例 | 核心关系与约束 |
|---|---|---|
| D01 | source_connection、ingestion_batch、sync_cursor | 来源、授权范围、批次、游标和覆盖声明；密码不入业务明文列 |
| D02 | identity_mapping、projection_revision、normalized_*_version | 映射审核版本；投影行关联来源记录/版本及批次；保留修订/删除标记 |
| D03 | quality_check、analysis_snapshot、snapshot_input_ref | snapshot→固定输入 manifest；记录覆盖、新鲜度、缺失及阻断原因 |
| D04 | evidence_ref、evidence_edge | evidence→来源/投影/快照/结果的受控位置引用；边只表达血缘/证据关系 |
| B01 | metric_definition、metric_result | 唯一指标口径版本；结果绑定事实/假设输入和窗口；不由 O01 再存一份指标主表 |
| B02 | forecast_scenario、optimization_result | 假设/预测/约束及模型版本；候选指标只保存 B01 resultRef |
| A02 | understanding_result、annotation_revision | 标签、置信度/UNKNOWN、分类体系及人工修订；不是身份主数据 |
| O01 | analysis_task、task_plan、participant_run、analysis_report、budget_usage | task→plan→participant；report 引用领域结果与证据；拥有正式任务计划/报告/预算账本 |
| A03（即席启用时） | adhoc_query_run、adhoc_quota_window | 仅 queryId、策略/截止时间、去重/预留/结算/并发控制和 G02 引用；不复制源事实或正式报告；详见 6.4 |
| C01 | suggestion_version、risk_alert | 建议内容、去重、确认/提交状态和来源报告版本；建议变更追加版本 |
| C02 | approval_record、approval_decision | 冻结动作、范围、指纹、有效期、审批人；与建议版本关联 |
| C03 | execution、execution_attempt、receipt_observation | 执行聚合、每次尝试/核对、源回执引用；唯一键与请求指纹分别保留 |
| G01 | principal_binding、role_scope_binding、policy_revision | 与企业身份的绑定、范围授权、当前策略；不是默认再建完整企业 IAM |
| G02 | audit_event、trace_summary、evaluation_case/result | 只保存观测/审计/评测所需信息和业务引用；不复制审批/报告正文作为第二账本 |
| I01 | work_item、work_attempt | 工作项领取、租约、重试时间、终止/恢复元数据；payload 指向所有者记录 |

W01 不另设业务事实账本；A01 的提供方配置优先配置文件/环境引用，调用成本与轨迹归 G02。A03 若以后采用索引，索引代际/构建任务等元数据按实际需要增加，由 A03 管理，不能先把向量/图写成当前必建数据域。知识正文归已声明的受控来源/数据资产，D04 只引用，不成为万能文档库。

### 8.2 业务源、投影与跨模块只读

【确定】ERP/OMS/WMS/TMS/CRM/平台和财务系统仍是各自事实权威，中台 D02 是带来源和版本的分析投影。D01 同步、D02 映射、B01 指标或 AI 标签均不得反向覆盖源订单、库存和账务主事实。来源权威冲突按业务责任人确认的优先级处理，不能凭名称相似自动合并 SKU。

跨模块优先调用所有者的公开查询服务，返回版本化只读 DTO/Ref。确有批量分析需求时，可由所有者提供只读投影查询端口/数据库视图，明确字段、范围、版本与性能契约；这不授权调用者导入私有 ORM 或写表。共享 MySQL 实例不代表共享任意表访问权。API 与 Worker 的数据库账户按运行职责最小授权，模块级边界另由代码依赖检查和契约测试保证。

### 8.3 表与字段设计原则

【建议】业务表关联键包含 tenantId，唯一键及跨表关联同时约束租户，防止 ID 正确但跨租户误连。聚合使用内部不透明 ID；来源保留 sourceSystem/sourceRecordId/sourceVersion，不把外部 ID 作为全系统唯一键。状态更新使用 expectedVersion/乐观锁；关键幂等、审批和任务领取增加数据库唯一约束与必要行锁。

金额使用 Decimal/DECIMAL 并记录币种、汇率口径与版本；库存数量按计量单位选择精度，不统一用二进制浮点。时间保存 UTC 的带语义字段（如数据库 DATETIME(6) 约定 UTC），同时保留源时区/业务日规则；asOf、源发生时间、observedAt、coverageThrough 不混用。JSON 仅用于版本化参数/假设和有限扩展，关键状态/租户/索引条件/金额不藏进无约束大 JSON。

索引优先覆盖租户+业务查询键、来源去重键、任务 `status/runAfter/leaseExpiry` 领取条件、幂等键和审批关联。分区、分库、读副本不预设；只有容量测试、保留周期和查询计划证明有必要时再引入。持久化和模型日志不得无限保留，业务/法务确认的删除策略要覆盖派生产物和候选索引。

### 8.4 D03、D04、O01 的边界

| 对象 | 唯一归属 | 可以保存 | 不应保存 |
|---|---|---|---|
| snapshotId / 输入 manifest | D03 | 固定投影/映射/质量版本、数据范围、共同锚点及源覆盖 | 调度计划、完整报告、第二份所有来源数据 |
| evidenceId / 引用与血缘 | D04 | assetVersion、locator、snapshot/resultRef、权限标签、关系边 | 重复输入 manifest、指标明细、另一份报告正文 |
| taskId / planVersion / reportVersion | O01 | 参与者、调度、预算、DomainResult 引用、报告解释/结论、快照/证据引用 | 独立维护第二套数据版本清单、重新计算指标/标签 |

固定输入版本不能仅保存“latest”查询条件。D03 的 manifest 必须能解析到仍保留的不可变投影修订/批次和规则版本；保存 hash 但底层记录已覆盖并不能重现输入。若原始内容删除，证据解析应标示不可用并按保留政策处理，不谎称仍可复核。跨系统共同 asOf 是质量受控的一致锚点，不承诺多个外部系统的原子事务快照。

## 09 同步、标准化、质量、分析快照与数据流

### 9.1 同步与冻结规则

【建议】D01 的读批次以源分页/增量/导出机制形成 batchRef；D02 将映射、单位、状态转换为固定 projectionRevision。源支持变更版本则保留源版本，不支持时记录读取时间、导出批次与内容指纹，明确可重放限制。增量记录和删除标记均需去重，重放同一批次不重复累加库存或费用。

只有投影与该批次处理状态提交成功，才推进可用同步游标；若分阶段暂存，原始读取进度与“投影可分析进度”分别记录。隔离/失败记录会影响 coverage/quality，不得因最新游标很新就宣称数据齐备。没有可靠增量接口时可用受控文件导入作为过渡，但要记录人工提交人、文件版本、覆盖范围和延迟，不视为接口已连接。

D03 按场景声明的必需数据、scope 和 asOf 检查覆盖、成熟队列、延迟、映射和缺失，固定到已提交投影版本。不使用长时间持有的数据库事务/MVCC 读视图充当永久分析快照。质量未通过时提供阻断/缺口结果，由场景和 O01 按既有边界决定业务终点。

### 9.2 数据同步到分析快照图

```mermaid
flowchart TB
  EXT[外部 ERP / OMS / WMS / TMS / CRM / 平台 / 财务]
  EXT -->|只读 API 或受控导入，实际能力待验证| D1[D01 批次 / 游标 / 覆盖声明]
  D1 --> D2[D02 身份映射 / 单位状态标准化]
  D2 --> PV[(MySQL 不可变投影修订及来源引用)]
  D2 --> ERR[映射歧义 / 缺失 / 隔离记录]
  PV --> D3[D03 质量检查 / 固定输入 manifest]
  D1 -->|可分析覆盖与新鲜度| D3
  ERR -->|缺口影响质量| D3
  O[O01 参与者声明 / scope / asOf] --> D3
  D3 --> SN[(D03 analysis_snapshot / snapshot_input_ref)]
  SN --> SC[O01 调 ScenarioHandler]
  PV -->|按快照固定版本只读| SC
  SC --> CALC[B01 指标 / B02 情景 / A02 理解 / A03 检索 / A01 模型]
  CALC --> RES[(各能力所有者的固定版本结果)]
  SN -->|快照引用| EV[D04 证据引用与血缘]
  RES -->|结果和资产位置引用| EV
  RES -->|DomainResult 引用| RPT[O01 审查 / 报告发布]
  EV -->|授权证据视图| RPT
  RPT --> VIEW[W01 报告 / 候选建议]
  VIEW -->|用户明确选择与确认| C1[C01 建议版本]
  C1 -->|用户明确提交审批| C2[C02 独立人工审批]
  C2 -->|另一次明确执行命令且复核通过| C3[C03 受控执行]
  C3 --> PRE[C03 经 ActionAdapter 读取来源前置状态]
  PRE -->|窄只读查询| EXT
  EXT -->|当前状态 / 版本 / 时点 / 覆盖| PRE
  PRE --> SAFE{条件 PASS 且源原子保证成立}
  SAFE -->|C03 锁外 execute / 原 key 与条件 token| EXT
  SAFE -->|不满足或无法证明| STOP[不发送 / 有界只读重查或人工处理]
  EXT -->|回执或核对结果，不当作完整源投影| C3
  C3 -->|后续只读同步观察业务事实| D1
  PV -.仅候选，按需异步构建.-> IDX[Milvus / Neo4j 派生索引]
  EV -.授权元数据与引用.-> IDX
  IDX -.仅向 A03 提供候选引用，回源复核.-> CALC
```

此图是工程数据流，不改变既有逻辑数据流。源数据进入 D01 的路径和 C03 写入路径分开；执行回执不能直接篡改分析投影。写入后是否产生新的分析任务/快照由业务明确触发，不默认原报告随源更新自动变更。

### 9.3 Milvus、Neo4j 与 MySQL

【候选/待验证】Milvus 只用于 A03 确有收益的语义召回；Neo4j 只用于关系路径查询确实超出关系查询的成本/表达能力。基础阶段可用 MySQL 的结构化查询、受控关键词查询和 D04 evidence_edge；这些不能被宣称为已达到语义检索或复杂 GraphRAG 效果。

若引入候选索引，以 MySQL/受控源资产为事实与元数据权威，索引是可重建的派生副本。由 A03 维护 indexGeneration、asset/version/chunk、embeddingModel/version、构建覆盖/状态；通过 I01 已有持久任务异步更新，不建立双主写入或跨库分布式事务。写入 MySQL 与索引成功可有时间差，查询必须暴露覆盖与新鲜度，不能把“任务已排队”当索引已更新。

检索请求在后端生成租户、授权范围、资产与版本过滤条件；未能证明后端满足必要预过滤约束的适配器不得承载该数据查询，不能仅靠召回后删几条越权结果。候选命中还需通过 D04/所有者回源核验当前权限、有效版本和快照适配性，才进入模型上下文。Milvus 支持元数据过滤的机制可作为候选验证基础，具体版本和索引方案仍须实测。[Milvus 官方过滤检索说明](https://milvus.io/docs/filtered-search.md)

图查询采用白名单参数化模板/受控 QuerySpec，限制跳数、返回规模和超时；路径中每个节点/边都须符合租户与权限，不只检查起点。Neo4j 具体版本/许可、备份与运维成本待确认；查询参数化的技术依据参见 [Neo4j Python 官方查询文档](https://neo4j.com/docs/python-manual/current/query-simple/)。两种候选均需完成效果提升、真实规模、隔离、删除、重建及运维验证，才列入某阶段部署清单。

## 10 Agent 与 AI 公共基座概要

### 10.1 模型网关与运行位置

【确定】所有业务 Agent、A02/A03 及 O01 联合报告解释都通过 A01；云端和本地模型接入 ModelProvider，模型名称不散布在路由与场景代码中。【建议】统一 ModelRequest 的输出 schema、超时、预算许可与 Trace；适配器映射模型特性、响应格式、工具请求、usage 和技术错误。不同提供方不一定支持同样的结构化输出、多模态或工具协议，能力声明不满足场景要求时返回不支持，不能静默换成语义不同的输出。

Agent/Workflow 作为场景内部的应用流程运行，正式持久任务在 Worker 内执行；同步即席查询运行控制以第 6.4 节为准。同一场景可包含多个角色，但不产生新的业务模块号、独立任务权威或专属模型/检索网关。O01 管参与者和任务级流程，不接管每个 Agent 的内部领域步骤。初期可用可测试的显式 Python Workflow，是否采用专门 Agent 框架留待第 11 步效果与复杂度评估。

### 10.2 Function Calling、工具和权限

【建议】A03 承担受控只读工具目录/执行门面，ToolSpec 包含 name/version、输入输出 schema、所需范围、资源限制和只读属性。首批真实用例包括 B01 指标查询、A03 资料检索、D04 证据解析。工具注册由可信代码/配置完成，不接受用户或模型动态安装 Python 函数、任意 Skill 或外部地址。

模型返回的 tool request 只是提案。所属场景的 Workflow（或 O01 的联合报告解释步骤）校验工具白名单、参数结构、当前 G01 权限、任务预算与截止时间，再调用 A03；服务端绑定 tenant/snapshot/scope，不采用模型自报的权限。工具返回最小必要结果和证据引用，不能把未经清洗的源文本直接提升为系统指令。A01 不执行工具，A03 不注册 C03 写动作，模型不能通过 Function Calling 跳过用户确认、独立审批或执行命令。

若后续通过 MCP 接入工具，它只是同一 ToolSpec/权限契约的传输适配形式，不产生第二套工具业务逻辑、授权系统或必需部署的 MCP 服务。

### 10.3 Prompt、Context、Skills、Memory 的归属

| 资产 | 归属及基本版本管理 | 本阶段范围 |
|---|---|---|
| Prompt | 场景业务模板归场景；A02/A03 通用模板归其模块；联合报告模板归 O01；A01 只做提供方格式适配 | 建议以 Git 管理模板和元数据，记录 templateId/version/hash 与输出 schema，不建专门 Prompt 平台 |
| Context | O01 管 task/scope/plan/snapshot/预算锚点；场景按用途组织受限片段，D04 管证据引用 | 统一引用与权限规则；切片、压缩、上下文窗口策略详细设计留第 11 步 |
| Skills | 属于实际使用的场景或 A02/A03 能力，必须有名称/版本、输入输出、允许工具和评测例 | 是可信能力清单/流程资源，不构成任意代码执行插件市场 |
| Memory | 按基线仅允许经确认、可撤销的偏好；事实查询仍来自 D02/D03/D04，任务状态/检查点归 O01，不能冒充长期 Memory | 当前不引入独立 Memory 服务或表；偏好持久化有明确需求后再定义归属、授权和保留期，不扩展为未经确认的经验事实库 |
| 检索资产 | 正文归既有受控资产，引用归 D04，检索协议和候选索引归 A03 | RAG 统一走 A03；知识更新和删除须能传播到派生索引 |

资产和复用边界按本表及 ER03—ER05 执行；实现时不能通过 Prompt/Memory 改变这些职责。具体权限细则维护于第 14 节，不在模板中另设一套例外。

### 10.4 AI 公共调用路径图

```mermaid
sequenceDiagram
  autonumber
  participant S as 场景 / O01报告 / A03即席用例
  participant B as 对应运行控制 / O01任务或A03查询
  participant G as G01 当前授权
  participant A as A01 模型网关
  participant M as ModelProvider
  participant T as A03 只读工具 / 检索
  participant D as B01 / D04 / 受控数据查询
  participant L as G02 观测评测
  S->>G: 校验当前身份、用途、范围及模型数据边界，取得获准策略
  alt 正式分析任务
    S->>B: 使用 O01 taskId / TaskBudgetHandle
  else W01 发起即席查询
    S->>B: A03 建立 queryId / QueryRunContext，校验请求及周期额度
  end
  S->>B: 申请调用额度及 deadline
  B-->>S: allowanceRef 或预算受限
  break 未获预算许可或当前授权拒绝
    S->>S: 由对应编排层决定终止或获准降级，不调用模型
  end
  opt 当前操作确需模型，已获模型额度许可
    S->>A: ModelRequest / prompt与context版本引用
    A->>M: 适配调用，限制技术超时
    M-->>A: 内容、usage、toolRequests 或技术错误
    A-->>S: 标准化响应 / 技术状态
    A->>L: 脱敏技术轨迹与 usage
    S->>B: 结算或保守保留未知消耗
  end
  alt 当前操作是只读检索或存在获准工具提案
    S->>G: 核验工具白名单、参数与当前范围
    S->>B: 预留工具额度
    break 工具权限或额度核验不通过
      S->>S: 拒绝工具调用，按领域/联合策略处理
    end
    S->>T: 受控 ToolInvocation，服务端绑定scope与snapshot
    T->>G: 再次校验资源权限及过滤条件
    T->>D: 白名单查询 / 指标结果 / 证据解析
    D-->>T: 固定版本引用与最小结果
    T-->>S: ToolResult / evidenceRefs
    S->>B: 结算工具消耗
    Note over S,M: 如需后续模型调用，仍走同一路径并计入同一预算
  else 技术失败或预算不足
    S->>S: 按调用来源处理：场景/联合业务策略，或即席有界错误
  end
  S->>L: 业务决策、版本链及评测关联引用
  Note over A,T: A01 不执行函数；A03 工具不含 C03 写动作
```

图中的“对应运行控制”是两个既有模块内部职责的并列标注，不是新服务：正式任务按 7.3，即席查询按 6.4；即席不得使用另一份 TaskBudgetHandle。纯检索无需模型时仍经过授权、工具/期限/额度与 G02 审计路径，跳过 A01/ModelProvider，不能跳过控制。图仅定义公共路径和一次工具往返，不冻结第 11 步的完整 Agent/LLMOps 设计。

## 11 异步 Worker、任务持久化与恢复

### 11.1 职责与三种状态机

【建议】Worker 领取 I01 工作项，按 workKind 调用所属模块应用服务：分析由 O01 驱动场景，数据同步由 D01 驱动标准化链，执行/回执核对由 C03 驱动。Worker 不自行计算业务结论或改审批状态。注册 workKind/version 和 payloadRef，不用任意 Python 导入路径、pickle 或脚本串调度。

| 状态体系 | 所有者与建议状态 | 含义 |
|---|---|---|
| 分析任务技术进度 | O01：QUEUED、RUNNING、SUCCEEDED、FAILED、CANCELLED | 任务是否完成处理；最终报告完整性另行表达 |
| 持久工作项投递 | I01：PENDING、LEASED、RETRY_WAIT、DONE、DEAD、CANCELLED | 仅通用领取/有界重投；不设所有任务必经的专用恢复态 |
| 建议/审批/外部执行 | C01/C02/C03 使用已确认状态，见第 13 节 | 不能因工作项 DEAD 推断源动作失败；UNKNOWN 必须保留 |

分析流程正确发布 BLOCKED 报告可视为技术处理成功，但不表示业务分析完整；执行模块处理出明确 FAILED 时，对应投递可 DONE；回执核对耗尽自动预算可将工作项置 DEAD/人工处理，但执行仍 UNKNOWN。三者互不覆盖。

### 11.2 MySQL 领取与租约

【建议】使用 MySQL InnoDB 任务表：短事务选择到期工作项并通过 `FOR UPDATE SKIP LOCKED` 避免多个 Worker 同时领取，更新 owner/leaseToken/leaseExpiry/attempt 后立即提交；外部接口调用在锁外执行。该机制适合队列式竞争，不应用于需要完整一致数据集的业务分析查询。[MySQL 官方锁定读取说明](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

心跳、完成、重排和检查点使用 leaseToken/版本条件更新；以数据库 UTC 时间判定租约过期。旧 Worker 失去租约后不能覆盖新状态或发布旧计划报告。并发任务各自创建 Session，不能把同一个 AsyncSession 放进并发 gather；这是 SQLAlchemy 的明确使用边界。[SQLAlchemy 官方异步并发说明](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncsession-with-concurrent-tasks)

租约只约束本地状态写入，不足以撤回旧 Worker 已发出的外部请求；系统是**至少一次工作项处理 + 业务幂等/核对**，不宣称外部 exactly-once。租约过期按投递次数/期限重排或 DEAD，Worker 仍只分派同一所有者用例。是否复用结果、重跑只读步骤或核对外部回执，由所有者读取自己的业务状态决定，不由 I01 判断“源是否创建”。

### 11.3 生命周期图

```mermaid
stateDiagram-v2
  [*] --> PENDING: 本地事务创建工作项
  PENDING --> LEASED: 到期领取 / 更新租约并提交
  RETRY_WAIT --> LEASED: 到期且预算允许
  LEASED --> LEASED: 合法 token 心跳
  LEASED --> DONE: 所有者处理结束 / 条件提交
  LEASED --> RETRY_WAIT: 可重进入口的失败或租约过期，尚有投递预算
  LEASED --> DEAD: 不可重试或预算耗尽
  PENDING --> CANCELLED: 尚未执行且授权取消
  RETRY_WAIT --> CANCELLED: 尚未重试且授权取消
  LEASED --> CANCELLED: 所有者确认无未决外部副作用且协作停止
  DONE --> [*]
  DEAD --> [*]
  CANCELLED --> [*]
```

此状态机仅属于 I01，v0.1 的通用 RECOVERY_REQUIRED 已移除；C03 的 UNKNOWN 及回执恢复完整保留。图中“重进入口”不等于重发外部 HTTP。人工补处理创建有审计的新工作项并关联原 workId，不任意复活终态记录。

| 工作项真实用例 | 租约过期/重复投递后由所有者执行 | 不强加的恢复逻辑 |
|---|---|---|
| O01 只读分析 | 读取 task/plan/snapshot 与检查点；复用已完成产物，未完成安全步骤才重跑；报告已发布则返回原 reportRef 并完成投递 | 不查外部动作回执、不要求 UNKNOWN 或专门通用恢复策略类 |
| D01 同步/本地步骤 | 读取批次/可分析游标，按既有去重与事务提交标记续做 | 不套用“已创建外部单据”的判断 |
| C03 执行 | 读取 execution：终态直接复用；READY 才进入首次发送前核验；SENDING/UNKNOWN 先经原键核对，只有已持久化的合法同键重发许可才可按 13.2.1 复核重发 | I01 不直接调 ActionAdapter，不因重投把 SENDING 当 READY |
| C03 回执核对 | 根据原 key 查询；未决则持久交接下一次核对，或保留 UNKNOWN 转人工 | 不把工作项 DONE/DEAD 当作动作成功/失败 |

C03 可在一个本地短事务中保存 UNKNOWN/核对计划、创建后续核对工作项并结束当前投递；若交接前崩溃，原工作项重入 C03 时仍据 SENDING/UNKNOWN 转核对。若通用投递预算已耗尽而原执行仍 SENDING/UNKNOWN，C03 的未决执行查询必须列出它及关联 DEAD 工作项，交由有权限人员核对，不能静默丢弃或由 I01 改成业务 FAILED。无需新增恢复服务、消息平台或所有任务都实现的 RecoveryStrategy 接口。

对 O01/D01 等无外部写副作用的工作项，投递耗尽由 Worker 分派对应所有者的失败收尾用例：O01 已有报告则复用，否则记录本方 FAILED；D01 标记批次失败且不推进可分析游标。所有者按第 12.1 节将本方终结、必需审计与 I01 DEAD 同一短事务提交，I01 只写自己的记录；异常回滚后继续按原记录处理，不允许形成无限 RUNNING。该收尾只为已注册用例提供明确失败通知，不引入通用恢复框架。

### 11.4 重试、取消与最小事件机制

只读数据查询、确定失败的模型请求可按错误分类、指数退避/抖动建议及剩余预算重试；实际次数和时间待验证。模型重试也可能重复计费，必须记账。数据库死锁仅重试已回滚的短事务，并保留同一业务命令去重键。ActionAdapter 不套用通用 HTTP 写重试。

取消采用协作式检查点：排队项可取消；运行中的领域步骤在安全边界检查取消/权限变化，不再派发新步骤。迟到的结果因任务/计划/租约条件不匹配而不能发布。C03 已进入 SENDING 或结果不明时，不能用“取消任务”断言动作未执行，也不能新增一个未经基线确认的 CANCELLED 执行状态；保留状态并核对回执。尚未发送的执行若被撤销/阻断，记录明确未发送原因与失败结果。

必需事件限状态变化通知、审计、工作项触发。与业务强一致的审计或触发记录和业务状态同一短事务提交；可延迟的观测导出使用已有 I01 任务重试。当前不部署事件总线、独立 MQ 或通用 Saga/事件溯源系统；未来出现明确跨进程消费和吞吐证据时才评估 outbox/MQ，不能以可能扩展为由现在落地。

FastAPI BackgroundTasks 可用于无需可靠恢复的小型请求附带工作，但不能承担分析、审批或外部执行的唯一持久机制；官方也将较重后台计算与进程内附带任务区分。[FastAPI 官方后台任务说明](https://fastapi.tiangolo.com/tutorial/background-tasks/)

## 12 事务边界与一致性

### 12.1 本地事务清单

| 用例 | 同一短事务内完成 | 事务外完成与失败处理 |
|---|---|---|
| O01 创建分析任务 | task/初始 plan + I01 work_item + 必需审计 | Worker 后续取数/模型；事务失败则整体不受理 |
| D01/D02 批次可用提交 | 对应投影修订、批次处理标记、可分析游标推进 | 读源在事务外；大批分段后以提交标记暴露可用版本 |
| D03 冻结快照 | 快照及固定 manifest、质量结论引用 | 输入必须已提交；不长期锁定源/投影；失败不发布半个 manifest |
| C01 用户提交审批 | C01 SubmitForApprovalUseCase 唯一协调；C02 写 PENDING；C01 写 SUBMITTED；G02 必需审计 | 共享同一 MySQL 事务，唯一提交/回滚责任及无环装配见 12.3 |
| C02 决策 | 决策、批准范围/指纹/有效期、审计 | 不在此事务中调用外部系统或自动创建执行任务 |
| C03 请求执行 | 验证批准和状态后保存执行意图、稳定 key、I01 work_item、审计 | 返回 202，Worker 在发送前再复核；不长持审批锁等 HTTP |
| C03 发送/回执 | 发送前记录 SENDING/attempt；回执后按 key/version 更新聚合和引用 | 实际 HTTP 在两段短事务之间；崩溃/超时走 UNKNOWN 核对 |
| O01 报告发布 | 计划/租约条件核验、报告版本与输出引用、任务终态 | 证据查询/模型解释先在锁外完成；不覆盖旧报告版本 |

【建议】由发起用例持有一段本地事务范围；跨模块调用仍走公开服务，各模块仅通过自己的 Repository 写表，不能让每层 Service 各自 commit。组合根注入同一事务上下文，**仅用于顺序的同一命令**；并发分支各用独立 Session/事务。提交失败可整体回滚，不能用“大家共用数据库”作为直接跨表写入的理由。

C01/C02 的具体协调、端口装配及故障语义统一在第 12.3 节定义；其他跨模块事务遵守 ER08，不复制另一套提交规则。

### 12.2 一致性等级与不确定窗口

任务/审批/执行聚合及其必需投递记录以 MySQL 本地事务和唯一约束保证局部一致；源系统→分析投影、投影→候选索引属于带覆盖/延迟标记的最终一致。跨系统 `asOf`、数据库提交与外部写入没有统一原子事务。必须显式记录已知、过期、缺失和 UNKNOWN，而非以技术重试掩盖。

发送前授权复核与外部真正接受之间仍有竞态窗口；来源并发变化的条件读取/原子执行门槛统一见第 13.2.1 节，批准撤销与在途请求的业务边界仍属 V07。数据库租约、指纹和审批锁不构成跨系统原子性证明。

### 12.3 C01/C02 提交审批的单一事务协调

【建议】**C01 的 SubmitForApprovalUseCase 是唯一事务协调者**，位于 collaboration/suggestions/application。W01 明确提交命令后只调用该用例；API 路由、bootstrap、C02 提交服务都不另行提交。I01/MySQL 适配负责提供同一连接/AsyncSession 的本地事务范围，协调者控制其开始、commit 和异常 rollback；不把 ORM Session 暴露给领域对象。

| 参与者 | 同一事务内的责任 | 不得承担的责任 |
|---|---|---|
| C01 SubmitForApprovalUseCase | 开事务；通过自己的 Repository 锁定/校验建议版本及 CONFIRMED 状态、当前权限与命令去重；调用 C02 窄命令；保存本方 SUBMITTED 与 approvalRef；最终唯一 commit | 不写 C02 表；不调用外部接口、不并行分派、不提前返回成功 |
| C02 ApprovalSubmission 应用命令 | 接收受信任的冻结建议/动作/范围/指纹/有效期及当前 txScope；仅经自己的 Repository 插入 PENDING 并返回未提交的 approvalRef | 不回调 C01 Submit 服务；不新开事务、不 commit、不返回对外已受理结论 |
| G02 必需审计写入 | 使用同一 txScope、自己的 Repository 追加提交事件 | 不单独提交，不把完整建议复制成审计账本 |
| MySQL 事务适配 | 所有参与 Repository 绑定同一 Session/连接；执行协调者触发的一次提交/回滚 | 不能因 Repository/Service 嵌套自动 commit，不能开启 REQUIRES_NEW 或以多连接“各自成功”冒充原子性 |

顺序为：锁定建议及命令键→校验获准版本/权限/状态→形成冻结提交信封→C02 插入 PENDING→C01 写 SUBMITTED/关联→G02 追加必需审计→协调者 commit→W01 返回已提交结果。C02/G02 只可 flush 供本事务校验/取 ID，不能 commit。任一步异常、唯一键冲突处理失败、审计不可写或 commit 明确失败均由协调者回滚全部写入；C01 保持原状态、无孤立 PENDING，不返回成功。若提交已完成而响应丢失，重试同 commandId/指纹在 C01 命令去重记录中返回原 approvalRef；提交结果不明先查询同命令结果，不创建第二份批准申请。

无环装配分成四个可独立构造的用例/视图，而不是 C01Service↔C02Service 互相注入：

| 使用者 | 自有窄端口与注入对象 | 依赖终点 |
|---|---|---|
| C01 SubmitForApprovalUseCase | C01 所需的 ApprovalSubmitPort，由组合根绑定 C02 ApprovalSubmission 命令 | C02 提交命令只依赖本方 Repository/策略，不回调 C01；可信建议校验已由持锁协调者完成 |
| C02 ApprovalDecisionUseCase | C02 所需的 SuggestionRevisionReader，由组合根绑定 C01 独立只读版本视图 | 只读视图仅依赖 C01 查询 Repository，不依赖 C01 提交用例或 C02；决策仍属于 C02 |

端口由消费方按实际需求定义，使用结构化只读信封/公共 Ref，组合根按结构契约注入，不要求 C01/C02 领域或应用代码交叉导入具体服务实现。C02 提交命令为内部受信调用，W01 不直接暴露绕过 C01 协调的创建接口。C02 审批决策在其自身短事务内核验当前建议版本与批准范围；需要锁定建议时经该窄只读端口取得同一事务的受控读/锁，锁顺序统一为建议→审批，不写 C01。两个用例对象的依赖均为单向无环，不新增模块或通用事务编排框架。

后续验收必须覆盖：在 C02 写入后、C01 状态写入后、审计写入时和 commit 前分别故障注入，均无部分提交；提交成功响应丢失后同命令重试返回原申请；两个并发提交只得到同一个有效申请；任意内层独立 commit/额外 Session 的实现均视为契约失败。具体数据库测试待开发时执行。

## 13 建议、审批、受控执行与失败恢复

### 13.1 人工终点及状态保持基线

| 阶段 | 已确认状态 | 流程终点及下一步触发者 |
|---|---|---|
| 只读分析 | 报告完整性与任务状态分离 | 报告/候选输出即结束；用户可另外选择创建建议 |
| C01 建议 | DRAFT、CONFIRMED、SUBMITTED、SUPERSEDED、CANCELLED | 确认只得到 CONFIRMED；发起人明确点击提交审批才进入 SUBMITTED |
| C02 审批 | PENDING、APPROVED、REJECTED、EXPIRED、REVOKED | 独立授权审批人作出决定；APPROVED 仍只是可执行资格 |
| C03 执行 | READY、SENDING、SUCCEEDED、FAILED、UNKNOWN | 另一次明确授权执行；SUCCEEDED 仅证明被批准动作的源结果 |

### 13.2 幂等键、指纹和回执契约

| 标识 | 目的与归属 | 不能替代的内容 |
|---|---|---|
| commandId / HTTP Idempotency-Key | 所属应用用例去重用户重复提交；相同 key + 不同请求内容拒绝 | 不证明源系统只执行一次 |
| work dedupeKey / leaseToken | I01 避免重复排队、约束当前领取者本地写入 | 不证明旧 Worker 没发外部请求 |
| executionKey | C03 为被批准的某个动作生成稳定不透明 key；唯一约束含租户、审批版本、approvedActionRef | 不因重启/重试另生成 key；不能换 payload |
| requestFingerprint | C02/C03 对冻结 actionType/schema/payload/scope 的规范化摘要 | 不替代审批原内容；同 key 指纹不同视为冲突 |
| sourceRecordId / receiptRef | ActionAdapter 核对源动作与请求的真实关系 | “请求已接收”不等于草稿/工单已创建，更不等于业务最终完成 |

ActionAdapter 至少声明 actionType/version、权限要求、readPreconditions、execute(executionKey, approvedPayload, conditionToken)、queryReceipt(executionKey)，以及源幂等范围/期限、查询时延、NOT_FOUND 的权威性；conditionToken 仅在来源证明支持时使用，具体门槛见 13.2.1。默认不假设任何企业 API 已有这些能力。仅源接收号或网关 200 而无可验证结果时，不得据此进入业务 SUCCEEDED。

【确定】超时、断网、进程崩溃、租约失效而无法证明未发送时转 UNKNOWN；先用**原 executionKey** 查询源回执。只有权威查询确认未创建、适配器证明同 key 重发安全、批准/当前权限/业务前置条件仍有效、预算允许，才可同键重试。NOT_FOUND 若只是索引延迟、查错范围或暂不可见，不构成重发依据。核对仍不明则继续 UNKNOWN 并转人工，不自动换 key 创建第二单。

回执核对可由最小权限的系统恢复身份继续进行，以确定已发生事实；任何新的写入重试仍须当前合法授权及有效审批，不能凭历史用户 Token 继续写。撤销、超时、内容变更使新写入不再合法时禁止重发，但已发请求仍须核对，不得伪造失败或回滚。

### 13.2.1 C03 发送前的来源状态读取与原子条件

【建议】报告/建议中的 D03 快照用于解释获批依据，不能证明发送时来源状态仍满足动作条件。C03 dispatch 必须先读本方执行状态：终态复用；SENDING/UNKNOWN 先按 13.2 核对原 key；仅 READY 或经核对明确允许重发的原执行进入下述来源检查。此读取是 C03 动作适配器对具体动作的窄前置查询，不替代 D01 同步或建立第二套分析投影。

| 步骤/结果 | 责任与契约 | C03 处理与证据 |
|---|---|---|
| 当前授权及批准核验 | C03 经 G01、C01/C02 公开接口验证动作/指纹/有效期、建议版本和范围 | 失败且明确未发送则 FAILED/原因；不调用 execute |
| readPreconditions | ActionAdapter 用受控只读接口读取本动作必需来源事实，返回 sourceObjectRefs、currentState、sourceVersion/conditionToken、observedAt、coverage/缺失和技术错误 | C03 按已批准动作规则判断，不让 LLM 决策；每次尝试留 observationRef/规则版本，敏感值最小保存 |
| PASS（判断结果，不是新执行状态） | 事实齐备/可信/足够新，且在批准范围内；源能原子保证相关条件 | 才可记录 SENDING 并 execute；只读核验与写请求均在数据库锁外 |
| BLOCKED | 来源对象关闭/失效、状态不符、批准锁定版本不匹配、业务条件不成立 | 明确未发送时 FAILED，并提示重新分析/建议/审批；禁止自动修改获批 payload 以“适配”新状态 |
| UNVERIFIABLE / 技术读取失败 | 无法读取必要状态、覆盖不足、版本不可核验或无安全原子机制 | 明确未调用 execute 时不标 UNKNOWN；可在原期限/预算内保持 READY 重试只读核验，超限/不支持则 FAILED/未发送原因，保留人工流程 |
| execute 的条件冲突 | 源在真正创建草稿/工单时原子比较版本/条件 | 若源明确保证未应用，记录 FAILED/CONDITION_CONFLICT，不盲目改 token 重发；若不能证明是否应用，转 UNKNOWN 并核对 |

采购草稿的具体前置事实可能包括获批供应商/SKU/采购对象的有效状态、获批版本及允许数量等；CRM 内部工单可能包括目标订单/客户关联、工单对象和归属权限。字段与阈值由每个动作合同确认（V06），此处不新增采购策略或 CRM 功能，也不把这些例子当企业接口已提供的字段。

**先读后写本身不能消除并发变化。**有 ETag/版本号/原子条件创建能力时，ActionAdapter 在 execute 中携带原 observation 的 conditionToken，由源在写入点原子判定；多个相关对象须证明关键不变量均受条件覆盖，单个对象的 ETag 不自动保护整个动作。没有版本条件写入时，仅当源另有经过验证的等效原子校验/不变量保证才允许启用；只有“刚刚读过”“数据足够新”或本地租约/锁均不构成安全执行证明，无法证明则禁用该自动动作并保留只读建议/人工操作。

读取后、发送前再检查本地有效批准与 leaseToken，并记录 SENDING/attempt；数据库事务立即提交，再执行 HTTP。sourceVersion/observation 是本次尝试的前置条件证据，不替换 executionKey 或修改冻结 requestFingerprint；若批准本身锁定某源版本，新版本必须符合批准要求，不能通过换 conditionToken 绕过。任何重发都重新读取和判断条件，但先执行 13.2 的原键回执核对，不以“当前来源不满足”倒推出过去一定未写。

后续验收至少覆盖：快照旧而当前来源已变化、读取失败/过期、两个执行并发改变源状态、读取后状态变化导致原子条件拒绝、多个对象条件覆盖不足、源无安全机制拒绝启用，以及条件冲突时响应丢失转 UNKNOWN。真实来源不支持这些证明时，M3 对应动作保持关闭，不能仅凭 Mock 条件写测试宣称安全。

### 13.3 技术调用链

```mermaid
sequenceDiagram
  autonumber
  actor U as 发起人 / 执行人
  actor H as 独立审批人
  participant W as W01 / HTTP
  participant C1 as C01 建议服务
  participant C2 as C02 审批服务
  participant C3 as C03 执行服务
  participant G2 as G02 必需审计
  participant J as I01 / MySQL
  participant R as Worker
  participant X as ActionAdapter / 外部系统
  U->>W: 选择建议并确认
  W->>C1: confirm(建议版本, 用户命令)
  C1-->>W: CONFIRMED，未提交审批
  U->>W: 明确点击“提交审批”
  W->>C1: submit_for_approval(建议版本, commandId)
  C1->>J: 协调者开始唯一 txScope，锁定本方建议/命令键
  C1->>C1: 校验当前权限、CONFIRMED版本与命令去重
  break 无权或状态/版本冲突
    C1->>J: rollback，未调用 C02
    C1-->>W: 拒绝提交
  end
  break 同一命令已成功提交
    C1->>J: 结束只读检查，不新增写入
    C1-->>W: 返回原 approvalRef
  end
  C1->>C2: 经 ApprovalSubmitPort 提交冻结信封与同一 txScope
  C2->>J: 仅 C02 Repository 写 PENDING，不 commit
  C2-->>C1: 未提交 approvalRef，不回调 C01
  C1->>J: 仅 C01 Repository 写 SUBMITTED / approvalRef
  C1->>G2: 同 txScope 追加必需审计
  G2->>J: 仅 G02 Repository 写审计，不 commit
  alt 所有本地步骤及提交成功
    C1->>J: 协调者唯一 commit
    C1-->>W: 已提交审批 / 原 approvalRef
  else 任一步明确失败，包括提交失败
    C1->>J: 协调者 rollback 全部写入
    break 本次提交结束
      C1-->>W: 返回安全错误，无孤立申请
    end
  else 提交结果不确定
    break 先查询同 commandId，不新建申请
      C1-->>W: 返回待核对结果，重试查询原命令
    end
  end
  H->>W: 查看冻结内容并批准
  W->>C2: decide(APPROVED)，经独立只读端口核验建议版本
  C2->>J: 保存批准版本、有效期和审计
  C2-->>W: APPROVED，不自动执行
  U->>W: 明确点击“执行已批准动作”
  W->>C3: request_execution(approvalRef, commandId)
  C3->>C2: validate_approval(指纹、范围、当前有效性)
  C2-->>C3: 验证结果
  break 当前授权或批准核验不通过
    C3-->>W: 拒绝受理，不创建可发送工作项
  end
  C3->>J: 同一短事务保存 READY、executionKey 与 work_item
  C3-->>W: 202 / executionRef
  R->>J: 领取执行项并提交租约
  R->>C3: dispatch(executionRef, leaseToken)
  C3->>C3: 读取执行状态及同键重发许可
  break 已是 SUCCEEDED / FAILED
    C3-->>R: 返回既有结果，不重新发送
  end
  break SENDING/UNKNOWN 且无有效原键核对重发许可
    C3->>X: queryReceipt(原 executionKey)，按13.2核对
    X-->>C3: 源事实或仍未知
    C3->>J: 保存核对结果/后续核对工作项，本次不直接发送
  end
  C3->>C3: 仅 READY 或已核对获准的原键重发，核验权限、批准与指纹
  break 本地复核不通过且明确未发送
    C3->>J: FAILED / 未发送原因，禁止读取或写入越权来源
  end
  C3->>X: readPreconditions(获批动作/来源对象)
  X-->>C3: currentState / sourceVersion或conditionToken / observedAt / coverage
  C3->>C3: 按获批规则判断 PASS / BLOCKED / UNVERIFIABLE
  break 非 PASS 或无安全原子执行保证，明确尚未发送
    C3->>J: 有界只读重查或 FAILED/未发送原因，禁止 execute
  end
  C3->>J: 再验批准及lease，短事务记 SENDING / observationRef 后提交
  C3->>X: 锁外 execute(原 key / fingerprint / conditionToken)，源原子校验
  alt 获得可验证源结果
    X-->>C3: 源 recordId / receipt
    C3->>J: 条件记录 SUCCEEDED 或明确 FAILED
  else 来源条件冲突且权威证明未应用
    X-->>C3: CONDITION_CONFLICT / not applied
    C3->>J: FAILED，保留原 key/指纹，不自动修改请求
  else 结果不确定 / 响应丢失
    C3->>J: UNKNOWN 或恢复标记，持久化核对任务
    R->>C3: reconcile_receipt(原 executionKey)
    C3->>X: 查询原 key 回执
    X-->>C3: 已创建 / 权威未创建 / 仍未知
    alt 已创建
      C3->>J: 核验内容后保存 SUCCEEDED / 源引用
    else 权威未创建且全部重发条件满足
      C3->>C2: 重发前再次验证批准与当前合法性
      C3->>J: 保存同键重试计划与工作项
      Note over C3,X: 重发仍经原 dispatch 的 readPreconditions/原子条件路径，禁止更换 key 或 payload
    else 仍未知或不允许重发
      C3->>J: 未知保留 UNKNOWN 转人工；已证实未创建且禁止重发则 FAILED
    end
  end
  W->>C3: 查询执行与回执
  C3-->>W: 当前状态及源记录引用
  Note over W,X: 不持数据库事务等待 HTTP；草稿/工单成功不等于后续业务完成
```

图中 C01 的提交协调、回滚及无环装配以 12.3 为准；ActionAdapter 的 readPreconditions/execute/queryReceipt 是同一已批准动作的技术调用，不是新模块。明确的发送状态门禁维护于 13.2.1：SENDING/UNKNOWN 不进入新发送链，只走回执核对；I01 重投不改变该门禁。图中的 C03 自检包含 G01、C01/C02 公开核验。审批人与发起人独立性具体规则仍属 V07。

## 14 安全与权限概要

### 14.1 身份、JWT 与数据范围

【建议】若企业已有身份提供方，优先 OIDC/OAuth2 接入；API 校验 JWT 的签名、公钥来源、固定算法允许列表、issuer、audience、exp/nbf 等。JWT 是身份载体，租户、角色和数据权限仍由 G01 当前策略判定，不能只相信长期 Token 内的历史角色。若无企业 IAM，认证来源及账号生命周期另行冻结，不默认为已具备 SSO。[FastAPI 官方 JWT 安全示例](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

前端通过 TLS 访问 API；浏览器 Token 保存方式、Cookie/CSRF 策略须结合实际门户冻结，不将官方教程中的登录方式直接视为企业已选认证流程。Worker 使用受控运行身份并保留发起人/批准人引用，恢复时复核权限，不保存用户长期明文 Token。需要撤销/禁用时利用 MySQL 当前身份/策略版本校验，无依据不引入 Redis 黑名单服务。

G01 按租户、店铺、仓库、字段、工具、动作及用途实施权限；后台查询/检索、证据解析、导出和执行每个敏感边界重新检查。快照固定数据版本，不固定永久授权。MySQL 不被假定有应用可直接依赖的行级安全，范围过滤由公开查询和数据适配器强制实现并用跨租户测试证明。即使 ID 不可猜，也不构成授权措施。

### 14.2 参数与敏感数据

API 校验长度、枚举、时间窗、数量、分页、参与者和输出规模，拒绝额外的危险字段；SQL 参数化，文件导入校验类型/大小与来源，外部调用目标由可信配置固定。模型不得控制连接字符串、数据库标识、任意 URL 或秘密参数。

密钥通过环境或企业既有密钥设施引用，日志/Trace/任务 payload 不记录明文；生产与测试权限隔离、模型调用前最小化/脱敏，字段级敏感度规则由 G01 与数据所有者管理。审计保留身份引用、动作、资源、决策、版本、时间和 Trace，不默认保留完整个人信息及全部 Prompt。

数据保存地域、跨境传输、供应商数据使用条款、保留/删除期限均沿用可研待确认项；本文不假定已签署合同或已获合规许可。备份、派生索引、缓存式上下文及评测集都必须纳入同一删除/保留策略。没有当前使用需求时不为这些事项额外创建合规平台或复杂脱敏组件。

## 15 测试、观测、评测与故障验证

### 15.1 测试分层与关键验收

| 类型 | 重点验证内容 | 不能混淆的证据 |
|---|---|---|
| 单元测试 | B01 逐日平衡/窗口/单位和贡献口径；B02 候选均调用 B01；状态转换、预算与场景降级 | 不以 Mock 模型“答得对”证明真实效果 |
| 契约测试 | ScenarioHandler/DTO 版本、ModelProvider 技术错误映射、SourceConnector、ActionAdapter 回执/幂等声明、ToolSpec | 测试桩通过不等于企业接口连通或允许写入 |
| MySQL 集成测试 | 租户关联、唯一键、事务回滚、并发领取、租约/CAS、游标与投影原子可用性、迁移 | SQLite 不能替代 MySQL 锁、精度、隔离和驱动验证 |
| 关键故障测试 | READY/SENDING 崩溃、源已建但响应丢失、查询延迟/伪 NOT_FOUND、旧 Worker 迟到、审批撤销竞态、超时/取消/死锁 | 测到一次成功不能证明 exactly-once；必须证明不确定时不盲目重发 |
| 安全测试 | 直接访问他租户报告、工具参数伪造、旧权限快照、索引跨域召回、图路径越权、Prompt 注入/敏感字段 | 不仅测 HTTP 层，也测 Worker、查询适配器和证据解析 |
| AI/业务评测 | 固定样本/金标准、VOC 分类与 UNKNOWN、检索证据命中、幻觉/口径/人工采纳、延迟和单位任务成本 | 分语言/场景/模型版本，不能仅看总体平均分或模型自评分 |

额外必须覆盖：SINGLE 与 JOINT 同一契约；三个以上参与者在默认并行度 2 下分波不丢任务；maxReplans=1 时超限行为；O01 不直接调用领域步骤；A01 技术失败由场景/O01 决策；建议确认不创建 PENDING，审批批准不创建外部写入；同 executionKey 不同 payload 被拒绝；UNKNOWN 恢复不会换 key。

本轮增补的专项验收以对应章节为准：首批基座 MC01—MC12（4.3）、即席控制（6.4）、普通任务与 C03 重入分流（11.3）、跨模块原子提交（12.3）、来源条件/竞态（13.2.1）。测试计划引用这些规则，不另维护含义不同的第二份用例要求。

### 15.2 观测与评测基础

【建议】结构化日志包含 UTC 时间、level、moduleId、traceId、task/participant/plan/snapshotRef、work/executionRef、attempt 和安全错误码；按事件类型最小化字段。Trace 从 HTTP 延续到持久任务和外部适配器，不把用户输入直接作为日志格式字符串。G02 保存审计与评测记录/必要摘要，普通运行日志可先接企业现有输出与采集设施，不强制部署完整观测集群。

技术指标包括任务排队/执行耗时、领取与恢复次数、模型错误/usage、工具耗时、数据覆盖/滞后、UNKNOWN 规模和核对时长；业务指标遵守 B01 唯一口径，G02 不重算贡献或投诉率。评测集包含数据/标签/许可版本、评测规则和模型/prompt/tool 版本，模型升级需与基线对比后放量。在线真实模型评测按预算和隐私单独授权环境配置，不能把 CI 默认为可调用生产密钥。

本阶段定义测试计划与必要门槛；实际业务自动化测试、性能报告和模型效果结果留待开发验证，不在文档中声称已经通过。

## 16 配置、迁移、版本与基本 CI

【建议】配置分环境，明确配置 schema、必需项和安全默认。数据库连接、身份发行方、模型能力、允许工具/动作、预算、租约、重试、同步覆盖阈值分别归属模块；非秘密策略有版本，秘密只有 secretRef。配置启动校验失败即阻止相关能力启动，不能自动降为无认证或无限预算。

建议使用 Pydantic Settings 类配置方案、SQLAlchemy 的稳定受支持版本系列和 Alembic 迁移；具体 Python 小版本、SQLAlchemy 2.0/2.1 维护线及 MySQL 异步驱动待兼容矩阵测试后锁定。统一依赖锁、Python 版本与制品标识，不把当前文档可运行环境当生产版本。[Alembic 官方迁移教程](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

迁移保持一条受控历史，按模块标注所有者、数据回填、锁影响和兼容窗口；由唯一集成负责人检查 revision 冲突。生产迁移不由每个 API 进程启动时执行，不使用 create_all 替代迁移。采用先扩展字段/兼容读取、回填验证、再收缩旧字段的演进方式；数据破坏性变更不能承诺靠一次 downgrade 无损回退，需备份/恢复演练与明确变更计划。

FastAPI 应用通过组合根创建并管理连接/客户端生命周期；启动不自动生成业务表、不暗中启动 Worker 或同步任务。部署前检查配置、迁移状态、数据库与所需依赖；ready 与进程活着分开表达，非必需候选索引不可用不应导致所有无关只读能力同时下线。

CI 建议最小顺序：锁依赖可复现检查→格式/静态检查（Ruff）与一种类型检查器→单元/契约测试→真实 MySQL 集成/迁移→关键故障与隔离测试→小规模离线评测及文档/契约一致性检查。暂不选定 CI 厂商，不要求 Kubernetes。pytest、httpx、Uvicorn 等为建议配套，依赖版本、许可证和平台支持在冻结时核对。

## 17 技术选型决策表

| 技术/方案 | 状态与解决的实际问题 | 为什么采用/建议 | 替代方案 | 引入或暂缓条件 | 维护成本与主要风险 |
|---|---|---|---|---|---|
| Python | 【确定方向】领域计算、AI 与集成主语言 | 同一基座承载指标、模型适配和业务流程 | 企业现有其他语言栈，仅在明确约束时重新评估 | 小版本与科学计算/驱动支持待验证 | 依赖治理、CPU 重计算与异步阻塞 |
| FastAPI + 建议 Uvicorn | FastAPI【确定】；服务器实现【建议】；HTTP 契约 | 类型化校验、OpenAPI、异步 I/O，适合模块化单体入口 | Django/Flask；其他兼容 ASGI 服务器 | 配套版本/运行参数在工程冻结时确认 | 路由膨胀、生命周期、错误处理不一致 |
| 模块化单体 + 独立 Worker | 【确定方向】API 响应与持久任务分离 | 复用代码和本地事务，匹配当前团队/复杂度 | 未来有独立扩缩/团队边界证据再拆服务 | 不因模块数量预拆微服务 | 需守住依赖边界；Worker CPU/凭据隔离 |
| MySQL / InnoDB | 【确定】业务投影、状态、审计、持久队列 | 一个关系型权威存储支撑本地事务/唯一约束 | 若企业标准改变可另评估 PostgreSQL；本轮不切换 | 【建议】8.4 LTS 作兼容验证候选，最终受企业支持矩阵约束 | 锁/索引/备份/容量；轮询任务竞争业务连接 |
| SQLAlchemy + Alembic | 【建议】Repository 实现和版本化迁移 | 限制 ORM 在适配器内，管理 schema 演进 | 直接 SQL+迁移脚本；其他 ORM | 选择维护线和异步驱动，验证事务/精度/迁移 | ORM 隐式 I/O、Session 并发误用、迁移冲突 |
| Pydantic / Settings | 【建议】DTO 与配置边界校验 | 与 FastAPI 协作，显式 schema 和环境配置 | dataclass+显式校验/其他配置库 | 不向纯领域传播 Web 校验依赖；版本锁定 | 严格/宽松转换差异、配置泄密 |
| MySQL 持久工作项 | 【建议实现】异步领取、恢复与短事务触发 | 先满足真实可靠性，不引入额外消息平台 | 后续成熟任务框架/MQ，需迁移收益证据 | 实测轮询/锁竞争满足规模；超出时重新评估 | 自建有限领取机制需故障演练，不包揽调度平台功能 |
| 统一 ModelProvider | 【确定方向】云 API/本地模型适配 | 场景不重复接 SDK、技术错误、usage 处理 | 厂商直连各场景不满足复用约束；可用轻量 SDK 封装 | 每个提供方先验证能力、数据地域、配额与输出 | 模型变更、费用/超时、协议特性差异 |
| 本地模型/GPU | 【候选】特殊隐私、时延或成本需求 | 仅有可证明优势时引入 | 云端合规 API；缩小可用模型场景 | 数据边界、效果、并发、显存、许可与运维评估通过 | GPU 投入、模型服务/升级和容量；不默认为更低成本 |
| Milvus | 【候选】大规模语义召回 | 统一 A03 端口可增加向量能力 | 先受控 MySQL/关键词检索；其他满足契约的向量后端需另评估 | 实测效果、规模、过滤/删除/备份和团队能力证明价值 | 索引重建、embedding 版本、资源与部署依赖；非当前必需 |
| Neo4j | 【候选】复杂多跳关系与解释路径 | 图查询有明确场景收益才增加 | MySQL 关系查询及 D04 evidence_edge | 关系结构/查询复杂度、隔离、许可与运维验证 | 同步一致性、路径权限、备份与版本；非当前必需 |
| httpx/供应商 SDK | 【建议】外部异步 I/O 适配 | 统一超时/连接与受控目标，SDK 特性封装 | 兼容 HTTP 客户端/同步 SDK 有界隔离 | 实际接口验证后选择，动作重试单独约束 | 连接泄漏、默认重试、SDK 日志泄露 |
| JWT / OIDC 接入 | 身份认证需求【确定】，具体方案【建议/待验证】 | 复用企业身份，不另建 IAM 平台 | 既有认证网关/会话方案，需一致安全契约 | 明确 issuer/audience/密钥轮换/撤销和浏览器方案 | Token 泄漏、授权过期、SSO 并非已接通 |
| pytest / Ruff / 类型检查 | 【建议】可测性与多人协作 | 统一契约与依赖质量门槛 | 企业已有等效工具；mypy/pyright 只选一套规则 | 冻结工具/锁文件与 CI 环境 | 维护有意义的故障测试，避免镜像实现式测试 |
| Redis | 【暂缓】尚无证据需要独立缓存/分布式限流 | 任务和权限先用 MySQL 可满足的路径 | 进程内受限非权威缓存；现有 DB 策略 | 真实瓶颈/多实例强限流需要再评估 | 失效、双存储一致性、运维；不得成为默认依赖 |
| MQ / Celery 等任务平台 | 【暂缓】尚无高吞吐多消费者证据 | 当前持久任务足够表达需求，不为框架增加 broker | MySQL 工作项；未来按需求选平台 | 规模/延迟/路由/消费边界证明自建方案不合适 | 额外 broker、投递语义、监控和迁移，不能解决源幂等 |
| 微服务 / Kubernetes | 【暂缓】无独立部署边界证据 | 当前本地事务、团队协作和运维更可控 | 模块化单体 + Worker；企业已有托管运行环境 | 多团队/扩缩/安全或发布隔离收益明确时评估 | 网络契约、分布式一致性、平台成本 |
| Agent 框架/LLMOps 平台/长期 Memory | 【暂缓到第 11 步及需求验证】复杂运行/治理需求 | 先保留公共契约和版本引用，不重复造底座 | 显式 Workflow + A01/A03/G02 基础能力 | 真实 Agent Loop、效果评测和运营需求证实后选择 | 框架耦合、重复状态、隐私与不可控循环 |

官方资料核对日期为 2026-11-11，链接用于说明机制，不冻结自动更新的文档页对应的最新发行版。选型需记录最终锁定版本、兼容矩阵、许可证和变更依据，不能以“官方最新”代替本项目版本控制。

## 18 扩展与多 AI 编码 Agent 交接规范

### 18.1 四类主要扩展

| 扩展 | 新增内容 | 必须复用/不能修改的内容 | 必要验证 |
|---|---|---|---|
| 新业务场景，如 S07 单证 | 场景 Handler、业务参数 schema、质量/输出声明、模板/评测、注册信息 | O01 协议和预算、D01—D04、A01/A03、权限/审批机制；不在 O01 写领域分支 | 单场景/联合兼容、证据可解析、领域降级；真实单证材料效果 |
| 新模型提供方 | A01 适配器、能力声明与技术错误映射、配置 | 统一 ModelRequest、工具执行边界、业务降级归属 | schema/工具请求/usage/超时、脱敏和预算；不支持能力显式报错 |
| 新数据源 | D01 Connector、D02 映射规则、来源/覆盖和质量声明 | 数据归属、快照/证据契约；无第二套取数脚本链 | 身份映射、增量/删除、重放、权限/限流与新鲜度 |
| 新动作类型 | 经范围批准后新增 C03 ActionAdapter、schema/风险与批准范围 | C01/C02/C03 状态与幂等/UNKNOWN 机制；不变成模型工具 | 源幂等/回执/条件写入、权限、取消/撤销竞态、故障恢复 |

### 18.2 交接材料与并行修改规则

【建议】后续每个开发任务必须指定：需求/验收编号、模块所有者、允许修改目录、公开接口及 schemaVersion、依赖接口版本、数据写入归属、错误/幂等/权限语义、测试样例与未验证假设。AI 编码 Agent 使用同一冻结契约和目录归属，不凭聊天摘要创建第二套公共能力。

公共契约变更先给出兼容影响和消费者清单，通过审查后再并行开发调用方。迁移链、组合根、共享引用结构和公开 API 由指定集成人协调；不同任务不能同时各改一份统一接口或自行创建“暂用公共库”。提交交接包括变更文件、运行/测试命令、真实结果、配置项/密钥引用、迁移顺序和遗留项，不提交真实凭据或未经许可的企业样本。

接口文档采用可版本控制的 schema/样例，HTTP OpenAPI 由未来代码生成并与文档校验；本轮只定义其归属与语义。依赖检查和交接验收统一引用第 5.3 节 ER01—ER10，以及第 4.1 节目录创建时点；禁止各开发任务另抄一份约束再自行添加例外。

## 19 尚未冻结的决策与验证清单

下列编号为概要设计审查/验证事项，不是新增模块、阶段或产品功能。未解决项不阻止本轮文档交付，但会限制后续代码冻结、真实集成或动作启用。

| 编号 | 待确认/待验证事项 | 建议责任方与所需证据 | 冻结/启用门槛 |
|---|---|---|---|
| V01 | Python、FastAPI/Pydantic、SQLAlchemy 维护线、MySQL/驱动及部署 OS 的兼容版本 | 技术负责人：异步事务、精度、锁与客户端兼容测试 | 公共工程初始化前冻结；不能自动取 latest |
| V02 | ERP/OMS/WMS/TMS/CRM/财务真实接口、授权与样本 | 系统责任人+数据负责人：接口合同、测试环境、分页/增量/删除/限流及覆盖 | M0；Mock 通过不得替代真实连通 |
| V03 | 统一 SKU/单位/状态、权威来源、指标口径与领域窗口 | 业务+数据负责人：映射审核、成熟队列/贡献等口径样例 | 相关场景开发与验收前冻结 |
| V04 | required/optional 参与者及领域/联合降级矩阵 | 各场景负责人：COMPLETE/PARTIAL/RULES_ONLY/BLOCKED 判定实例 | 禁止未冻结策略隐式跳过必要领域 |
| V05 | 正式任务和即席请求/周期额度、入口分配/共享总额要求、期限/并发/重试、租约与容量 | 技术+运维+财务：多 API 额度竞争、未知用量、连接池/配额、故障恢复测量 | 并行 2、重规划 1 保留；即席付费前冻结 6.4 配置；跨入口总额未验证则不启用相关收费入口 |
| V06 | 两类动作的 readPreconditions 字段/覆盖、源原子条件及多对象不变量、幂等 key 期限和权威回执 | ERP/CRM 责任人：13.2.1 的来源竞态、条件拒绝、响应丢失/迟到与 NOT_FOUND 演练 | M3 逐动作启用；仅先读后写/Mock 成功不够，无安全保证则保留人工流程 |
| V07 | 批准有效期、独立审批人/代理规则、撤销与发送竞态 | 业务+安全：岗位矩阵、允许的线性化边界和失败处置流程 | C02/C03 实际启用前冻结；不承诺撤回在途请求 |
| V08 | 身份发行方、JWT/浏览器方案、禁用/撤销时效、字段权限 | 安全+前端：认证协议与威胁评审、范围测试 | 上线认证与执行前冻结；不假设已有 SSO |
| V09 | 数据地域、供应商条款、个人信息/快照/审计/备份的保留删除 | 业务数据责任人+法务+安全：适用性与合同、删除验证 | 相应数据用于云模型/生产前确认 |
| V10 | Milvus 引入收益与版本/部署依赖 | 检索负责人+运维：分语言召回、隔离、过滤、删除、容量与成本对比 | A03 基础方案不能满足且收益成立才部署 |
| V11 | Neo4j 引入价值与版本/许可 | 数据/业务+运维：真实多跳查询、MySQL 对照、权限和成本 | 确有关系查询收益才部署；无收益不建组件 |
| V12 | 首批 S02 工程夹具/期望、运行/迁移入口、目录时点、依赖锁与 CI；前端门户另按需选择 | 工程负责人：4.1—4.4 的交付定义、模拟/真实证据分级与可复现构建 | 工程初始化前冻结必要项；MC 通过仅代表工程闭环，不替代 M0/M2/M3 |
| V13 | 模型提供方/本地算力、输出能力、质量/成本阈值 | AI+安全+运维：评测集、供应商配额/地域、GPU 实测 | 每个提供方/业务用途独立验证后开放 |
| V14 | 完整 Agent Harness、Context、Loop、Skills/Memory 策略与 LLMOps | 第 11 步设计负责人：真实工作流、失败样本和运营需求 | 本轮只冻结公共边界；不在此提前落地完整平台 |
| V15 | 备份恢复、审计完整性、任务长期积压与人工恢复责任 | 运维+模块负责人：恢复演练、保留周期、值守/核对流程 | 生产前冻结 RPO/RTO 与故障处置，不引用示例代替实测 |

【建议】独立审查优先核对：模块归属/禁止调用、三类状态与事务边界、工具只读/审批执行隔离、快照可解析、候选技术暂缓条件。接口能力不足时保留有条件可行结论，不通过扩大假设来“补全设计”。

## 20 基线对应关系、完整性与本轮交付

### 20.1 文档级追踪

| 基线位置 | 保持的内容 | 概要设计对应 |
|---|---|---|
| 需求第 04/06/08 节；架构第 02/07/09 节 | 五层、17 公共模块、依赖和部署边界 | 第 03—06 节，工程依赖图 |
| 需求 6.1/6.2、8.1/8.3；架构 2.2、7.1 | O01 分工、B01/B02 边界、上下文、预算 | 第 05—07、10—11 节，任务与 AI 路径图 |
| 需求第 09 节；架构第 06 节、7.2；可研第 06/07 节 | 源事实/投影、质量、快照、证据、数据责任 | 第 08—09、12、14 节，数据同步图 |
| 需求第 10/13 节；架构第 03—05 节及最新图示修正 | 只读、建议、人工审批、受控执行与 UNKNOWN | 第 07、11—14 节，任务/状态/审批执行图 |
| 需求第 12—15 节；架构第 10—12 节 | 可复用扩展、验收、完整范围分期 | 第 02、15—20 节 |
| 可研第 05、08—10、13—15 节 | 技术/组织可行性、验证和上线条件 | 第 10—19 节，技术选型与验证清单 |
| 可研第 11—12 节 | 成本/收益为假设，需要真实数据校准 | 第 01、07、17、19 节；不把演算直接变为容量或采购决策 |
| 本次 H01—H07 审查意见 | 最小交付、事务、即席、来源核验、任务精简、统一规则、分批目录 | H01/H07→4.1—4.4；H02→12.3/图06；H03→6.4/图04；H04→13.2.1/图03/图06；H05→11.3/图05；H06→5.3 与细则引用 |

### 20.2 22 项需求的工程归属核对

| 原候选项 | 归属不变 | 对应工程设计与分期 |
|---|---|---|
| 1 供需与库存 | S01 | 第 02/05/07 节；M2，复用 B01/B02 |
| 2 履约风险 | S02 | 第 02/05/07 节；M2 单场景示例 |
| 3 VOC | S03 | 第 02/07/10 节；M2，复用 A02+B01 |
| 4 贡献与费用 | S04 | 第 02/05/08 节；M2，唯一 B01 口径 |
| 5 主数据/质量 | D02/D03 | 第 08—09 节；M0/M1 |
| 6 预测、7 滞销、8 供应商 | S01 | 第 02/05/18 节；沿原规划扩展，无专属公共基座 |
| 9 运输方案 | S02 | 第 02/05/18 节；沿原规划扩展 |
| 10 多语言、11 售后 | S05 | 第 02/10/18 节；P1，不增加客户消息写入 |
| 12 本地化、13 广告 | S06 | 第 02/10/18 节；P1，不增加自动投放 |
| 14 费用审查 | S04 | 第 02/05/08 节；沿原规划扩展 |
| 15 单证 | S07 | 第 02/10/18 节；P1 |
| 16 自然语言查询/知识 | W01+A03 | 第 05/06/09/10 节；按基础与扩展需求分步实现 |
| 17 建议/审批/执行协作 | C01—C03 | 第 05/12/13 节；建议按需，写入 M3 验证后开放 |
| 18 市场、19 定价、20 多仓 | S08 | 第 02/05/18 节；P2，不提前建全量表 |
| 21 视觉 | S09 | 第 02/10/17 节；P2，模型/算力候选 |
| 22 政策 | S10 | 第 02/09/10 节；P2，证据/专业复核 |

### 20.3 本轮文件与图示规范

Markdown 是唯一正文维护源；HTML 由其派生，内嵌预渲染 SVG，无远程运行依赖。Mermaid 代码块分别导出到 `design/mermaid/`，保留 `.mmd` 和 `.svg` 成对文件：

| 图号 | 文件基名 | 内容 |
|---|---|---|
| 01 | 01-engineering-dependencies | 工程模块与依赖关系 |
| 02 | 02-single-joint-analysis | 单场景/联合任务 |
| 03 | 03-data-to-snapshot | 数据同步到快照、来源条件核验及受控写入边界 |
| 04 | 04-ai-tools-common-path | 正式任务/即席查询的有界模型与只读工具路径 |
| 05 | 05-work-item-lifecycle | 精简后的通用工作项投递状态；业务恢复归所有者 |
| 06 | 06-approval-execution-recovery | 单一审批事务、来源状态/原子条件、原键 UNKNOWN 核对 |

本轮修订对照与剩余问题见[H01—H07 修订说明](智慧中台AI应用项目_概要设计审查修订说明_H01-H07.md)；[最小代码基座交付与验收清单](智慧中台AI应用项目_最小代码基座交付与验收清单.md)由本文 4.1—4.4 派生，唯一维护来源仍为本文。清单不表示本轮创建或验收过代码。

本轮校验限文档内容、基线指纹、Mermaid 渲染、SVG/XML、离线 HTML 与阅读布局，不等于代码测试、接口联调、容量验证或 AI 效果验证。`design/validation-report.json` 记录当前 v0.2 实际校验结果；`design/file-manifest.json` 记录本次新增/修改文件，v0.1 正文快照及差异证据保存在 `design/review-h01-h07/`。三份设计基线及其既有 architecture/feasibility 图示、原有构建工具均不修改；本轮只同步概要设计及其派生文件。完成后等待独立复核，不自动推进代码开发或第 11 步详细设计。
