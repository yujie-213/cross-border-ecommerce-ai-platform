# 最小可运行代码基座交付与验收清单

> 版本：0.2 ｜ 状态：设计清单，待独立复核；不是本轮已完成的代码交付。
>
> 本文件直接派生自[概要开发设计文档 v0.2](智慧中台AI应用项目_概要开发设计文档.md)第 4.1—4.4 节；请只在该正文维护规则后同步生成。

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

