# 跨境电商智慧 AI 平台

面向跨境电商运营的智慧中台设计与原型项目。围绕采购、库存、订单与客户反馈，把分散的业务数据、确定性指标、AI 解释和人工决策连接起来，使建议能够追溯到输入、规则和证据。

当前已实现阶段 A 工程底座及阶段 B 的 S01 模拟工程链路，并保留需求、架构和独立交互原型。**真实教学 ERP 已有只读观测；真实业务数据与规则准入、正式模型用途启用和采购执行仍未完成。** 工程测试通过不代表真实业务验收、生产可用性或性能结论；A-01～A-06、B-01～B-05 的工程交付已获负责人验收，状态为 ACCEPTED；真实业务启用继续受原有门禁约束。

S01 后端已补充固定服务端包、严格来源/规则准入适配、A—E计算、自然解释消费、历史与新旧报告关联。Token统计为基础、费用可选，未知费用不阻断合法AI解释。真实观测仍保留BLOCKED，新增交付等待负责人和星星独立验收。运行边界与复验见 [S01 业务工程说明](docs/runbooks/s01-business.md)，真实单 SKU 仍缺的资料与签认见 [离线准入报告](docs/evidence/D-S01-DATA-01/admission-report.md)。

本轮教学仿真API写入/独立GET、9项Golden、5项独立进程联调及601项回归通过。负责人和星星已批准教学后端工程范围ACCEPTED及合main，见 [分项验收](docs/evidence/S01-BACKEND-ACCEPTANCE/review.md)。真实模型3次中A/B成功、C拒绝，D/E未发送，五例用途评测FAIL、C-04仍REVIEW，四项企业门仍BLOCKED。下一阶段 [前端准入交接](docs/ui/S01-frontend-entry.md) 已准备，本轮不编码。

## 要解决的问题

- 库存、需求、未收供给来自不同系统，日期、单位和口径容易混用。
- 补货建议需要同时考虑供给日期、MOQ、订购倍数、缓冲与质量阻断。
- AI 解释必须有依据，不能代替库存、金额等权威计算。
- 人工确认、提交审批、独立批准与外部执行需要分开；输入变化后旧批准不能继续使用。

## 架构与技术边界

设计采用模块化中台和确定性 Workflow。公共能力由场景复用，S01 采购补货是首个实施切片，无需等待 S02 或所有公共能力完成。

| 层次 | 已确定的设计职责 | 实现情况 |
|---|---|---|
| O01 编排 | 统一任务、计划、预算与报告；通过 ScenarioHandler 调用场景 | 持久任务/预算/恢复、S01 工程 Handler 和事务一致报告发布已实现 |
| D01—D04 数据 | 只读接入、映射投影、唯一快照 manifest、证据定位 | 工程输入、精确映射、质量/快照和受权证据查询已实现；真实教学 ERP 只读观测与准入适配已实现，真实计算门仍阻断 |
| B01 / B02 业务分析 | B01 负责确定性指标；B02 构造候选并调用 B01 评价 | 显式模拟策略下逐日供需、缺口和受约束候选已实现；真实规则未验收 |
| A01—A03 AI | 模型统一网关、受控运行时、只读工具；模型不计算权威库存 | A01 工程网关已验收；S01 解释与受限真实模型评测独立列证，正式用途待评审，A02/A03未实施 |
| C01—C03 人工控制 | 建议、审批、另行授权执行各自管理状态 | 原型演示；服务未实现 |
| G / I 公共工程 | 权限、审计与工作项等按当前切片补齐 | 可信签名/当前scope、审计usage、MySQL工作项与独立Worker已实现 |

工程采用 Python/FastAPI、SQLAlchemy、Alembic 和 MySQL；API 与 Worker 为独立进程。阶段 A 提供迁移、权限、持久任务、预算与恢复，阶段 B 提供模拟输入→质量检查→供需计算→候选→报告保存及查询。响应缓存默认 OFF，不预建 Redis、消息队列、向量库或多 Agent 通信。正式前端尚未接入，现有原型保持独立。

已实现的独立原型使用原生 HTML、CSS、JavaScript；文档工具使用 Python、Mermaid，浏览器检查使用 Playwright。它们不构成正式前端或平台后端。

## 当前可用内容

S01 原型包含工作台、建议列表、详情和人工审批预览，支持搜索筛选、固定逐日样例、证据反馈、模拟分析/取消/暂停、版本变化与审批失效。默认只读，显式开启后才演示人工流程，外部执行始终禁用。全部数据和身份为模拟，刷新清空状态。

当前独立 MySQL 8.0.27 上的迁移、权限、事务、租约/预算、API/Worker 重启恢复和 S01 模拟报告链路已有实测证据。四项真实数据/规则/ERP/模型准入仍 BLOCKED；没有采购审批或下单接口。任务与验收状态只以 [TASKS](docs/TASKS.md) 为准。

## 运行工程底座与模拟链路

本轮后端运行与用量语义见 [后端运行说明](docs/runbooks/s01-backend.md)，前端准备见 [API 对接契约](docs/contracts/s01/backend-api.md)，最终证据入口见 [本轮交付](docs/evidence/S01-BACKEND/README.md)。

安装、身份配置和公共 API/Worker 命令见[阶段 A 运行说明](docs/runbooks/phase-a.md)；S01 显式工程装配和一条命令演示见[阶段 B 运行说明](docs/runbooks/phase-b.md)。显式迁移后再分别启动 API/Worker。

已验证环境：Windows 10 build 19045 / CPython 3.13.5；其他 OS/Python 组合未验证。根目录 `.env` 使用 [.env.example](.env.example) 的字段，在本机填写获准连接，禁止提交密码。当前提供健康、受控任务、会话及工程报告/证据接口；真实企业身份接入和 S01 正式业务模式尚未启用。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
.\.venv\Scripts\python.exe -m commerce_hub.infrastructure.database
.\.venv\Scripts\python.exe -m uvicorn commerce_hub.entrypoints.http.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

`GET /health/live` 返回200。`GET /health/ready` 验证数据库、迁移和可信身份配置，缺项返回503；满足时200仅表示工程底座就绪，不表示真实 S01 业务可用。默认业务注册表为空，S01 模拟链路须显式 test 装配；启动不迁移、不内嵌 Worker，不调用 ERP/模型。

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe tools/smoke_foundation.py --output docs/evidence/A-02/smoke.json
$env:COMMERCE_RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=.tmp/ab-review-pytest
# 自动启动并停止自身 API/Worker，仅使用获准独立测试库和合成身份
$env:COMMERCE_ENVIRONMENT='test'
.\.venv\Scripts\python.exe -m tools.demo_s01
```

独立数据库兼容验证命令为 `tools/check_mysql_compat.py`，会在固定 `s01_a01_test_20261112` 库建本次专用fixture表、验证后只清理自己的表；使用前须有该库变更授权，不能作为任意数据库探针。阶段证据与真实/模拟范围见[唯一台账](docs/TASKS.md)，A-01/A-02历史证据仍绑定当时提交。实际进程套件会自动用测试装配启动/停止自己的API/Worker进程，不注册生产探针。

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
├── src/commerce_hub/                  # 公共底座与 S01 工程插件
├── migrations/ / tests/ / examples/    # 迁移、自动化测试与合成输入
└── tools/                            # 演示、环境检查及文档工具
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

按 [PLAN](docs/PLAN.md) 的 A—D 增量计划推进。当前后端闭环在既有底座上完成独立教学切片，具体状态、证据和剩余门禁只读 [TASKS](docs/TASKS.md)。本轮停止在正式前端对接之前，等待负责人和星星独立评审；企业正式规则、采购批准与执行仍分别验收和授权。

GitHub 公开发布尚未完成，阻碍与检查结果见 [公开准备说明](docs/governance/PUBLICATION.md)。项目未声明开源 LICENSE；第三方资源保留其原有声明，不能据此推定已取得全部再分发许可。
