# 跨境电商智慧 AI 平台

面向跨境电商运营的智慧中台设计与原型项目。围绕采购、库存、订单与客户反馈，把分散的业务数据、确定性指标、AI 解释和人工决策连接起来，使建议能够追溯到输入、规则和证据。

当前仓库提供需求与架构设计、代码基座及公共能力开发规划，以及采购补货场景 S01 的独立交互原型。**平台业务服务尚未实现，也未接入真实企业系统。** 本地模拟验证不代表真实业务验收、生产可用性或性能结论。

## 要解决的问题

- 库存、需求、未收供给来自不同系统，日期、单位和口径容易混用。
- 补货建议需要同时考虑供给日期、MOQ、订购倍数、缓冲与质量阻断。
- AI 解释必须有依据，不能代替库存、金额等权威计算。
- 人工确认、提交审批、独立批准与外部执行需要分开；输入变化后旧批准不能继续使用。

## 架构与技术边界

设计采用模块化中台和确定性 Workflow。公共能力由场景复用，S01 采购补货是首个实施切片，无需等待 S02 或所有公共能力完成。

| 层次 | 已确定的设计职责 | 实现情况 |
|---|---|---|
| O01 编排 | 统一任务、计划、预算与报告；通过 ScenarioHandler 调用场景 | 设计与计划 |
| D01—D04 数据 | 只读接入、映射投影、唯一快照 manifest、证据定位 | 设计与计划 |
| B01 / B02 业务分析 | B01 负责确定性指标；B02 构造候选并调用 B01 评价 | 设计与计划 |
| A01—A03 AI | 模型统一网关、受控运行时、只读工具；模型不计算权威库存 | 设计与计划 |
| C01—C03 人工控制 | 建议、审批、另行授权执行各自管理状态 | 原型演示；服务未实现 |
| G / I 公共工程 | 权限、审计与工作项等按当前切片补齐 | 设计与计划 |

工程设计确定使用 Python/FastAPI、SQLAlchemy、Alembic 和 MySQL；API 与 Worker 分为独立进程。上述应用工程尚未建立。响应缓存默认 OFF，不预建 Redis、消息队列、向量库或多 Agent 通信。正式前端组件库与应用技术选型尚未冻结。

已实现的独立原型使用原生 HTML、CSS、JavaScript；文档工具使用 Python、Mermaid，浏览器检查使用 Playwright。它们不构成正式前端或平台后端。

## 当前可用内容

S01 原型包含工作台、建议列表、详情和人工审批预览，支持搜索筛选、固定逐日样例、证据反馈、模拟分析/取消/暂停、版本变化与审批失效。默认只读，显式开启后才演示人工流程，外部执行始终禁用。全部数据和身份为模拟，刷新清空状态。

下一阶段待做：S01 完整专项设计与口径确认、必要公共契约冻结、最小工程与只读分析链路、适用真实数据验证。ERP、数据库、模型网关、后台任务、持久审批和真实权限均未实现。任务与验收状态只以 [TASKS](docs/TASKS.md) 为准；本轮不启动这些开发任务。

## 目录与文档入口

```text
.
├── README.md / AGENTS.md / DESIGN.md
├── docs/
│   ├── README.md                     # 分类索引与文档职责
│   ├── PLAN.md / TASKS.md / DECISIONS.md
│   ├── COLLABORATION.md / HANDOFF.md
│   ├── requirements/                 # 需求与业务术语
│   ├── architecture/                 # 逻辑架构、概要设计、图示
│   ├── agents/                       # AI 详设、场景设计、契约示例
│   ├── ui/                           # 产品原型规格与视觉研究
│   ├── reports/                      # 可行性与示例测算
│   ├── planning/ / generated/         # 文档工具、证据与派生状态
│   ├── governance/                   # 迁移映射与公开准备检查
│   └── archive/                      # 旧计划、修订前版本与原文快照
├── prototypes/s01/                   # 原型源码、自动检查、截图
└── tools/                            # 文档生成工具
```

完整导航见 [docs/README.md](docs/README.md)。产品功能与操作流程由 [产品规格](docs/ui/PRODUCT_SPEC.md) 和可操作原型评审；视觉表达由 [DESIGN.md](DESIGN.md) 约束，两者不能互相替代。

## 本地预览与检查

直接用浏览器打开 [prototypes/s01/index.html](prototypes/s01/index.html)，无需安装或构建。也可在项目根目录启动仅监听本机的预览：

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

浏览器访问 `http://127.0.0.1:8765/prototypes/s01/`。这只是静态原型预览，没有平台服务启动命令、数据库迁移或 ERP 配置；当前不需要 `.env`。

文档检查：

```powershell
python -m pip install -r tools/requirements-docs.txt
python docs/planning/build_docs.py
python docs/planning/check_plan.py
python docs/ui/check_design.py
python docs/governance/audit.py
```

原型自动检查见 [原型说明](prototypes/s01/README.md)。需要 Node.js、现有 Playwright 与浏览器；可通过 `PLAYWRIGHT_MODULE`、`BROWSER_EXECUTABLE` 指定本机安装位置。测试仅验证模拟交互，结果与截图保留在原型的 `evidence/`。

## 后续路线与公开状态

按 [PLAN](docs/PLAN.md) 的 A—D 增量计划推进：先完成 S01 专项设计，再建立所需最小工程与公共能力，最后实现只读补货报告。按需增加 AI 解释与人工协作能力；确认、审批和外部执行分别授权。UX-S01-01 仍待负责人最终验收，完整 S01 业务设计及必要口径尚未冻结，不能直接开始 MVP 编码。

GitHub 公开发布尚未完成，阻碍与检查结果见 [公开准备说明](docs/governance/PUBLICATION.md)。项目未声明开源 LICENSE；第三方资源保留其原有声明，不能据此推定已取得全部再分发许可。
