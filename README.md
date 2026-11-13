# 跨境电商智慧 AI 平台

面向跨境电商运营的智慧中台项目，当前交付 S01 补货教学工程工作台。围绕库存与补货，把业务数据、确定性指标、AI 解释和人工决策连接起来，使建议能够追溯到输入、规则和证据。

当前已实现 Python/FastAPI 后端、独立 Worker、MySQL 持久任务和 Vue 3/TypeScript 前端，支持教学固定包的补货分析、报告、历史与受权证据读取。前端证据竞态、结构化引用契约及真实 DeepSeek A—E 五场景的教学技术范围已验收并合入 main，见 [验收合并报告](docs/evidence/S01-UI-C04-ACCEPTANCE/report.md)。最近工程基线为后端 639、前端单测 31、浏览器 6 项通过。

**当前启动的是本机教学演示：使用既有教学 ERP 回读数据包，普通页面 AI 为 off，不自动调用 DeepSeek 或在线刷新 ERP。** 独立模型评测的五例成功记录与历史失败分开保留，见 [真实模型评测](docs/evidence/C-04-STRUCTURED-LIVE/report.md)。企业数据、规则、ERP 安全、AI 正式用途四门继续 BLOCKED；S01 MVP 整体验收和采购执行尚未完成。任务状态只读 [TASKS](docs/TASKS.md)。

## 启动当前 S01 工作台（Windows / PowerShell）

在当前开发机打开两个 PowerShell 终端。已有 Python 环境、前端依赖、本机 `.env` 和私有教学 catalog 可直接复用；MySQL 应可连接，库为 `s01_a01_test_20261112`，迁移已到 `0005_optional_usage`。启动工具不会自动建库或迁移。

**终端 1：启动后端 API 和 Worker**（保持窗口运行）：

```powershell
Set-Location -LiteralPath 'D:\电商项目\跨境电商智慧AI平台'
$env:PYTHONPATH='src'
.\.tmp\stage-a-clean\Scripts\python.exe -m tools.s01_frontend_dev --execute-local
```

看到 `READY: independent API/Worker ...` 后再执行终端 2。后端端口由启动工具分配，写入本机私有回执，不固定为 8000。

**终端 2：启动前端并复制本次短期身份令牌**：

```powershell
Set-Location -LiteralPath 'D:\电商项目\跨境电商智慧AI平台\frontend'
$s01Local = Get-Content ../data/private/s01-frontend/session.json -Raw | ConvertFrom-Json
$env:S01_API_TARGET=$s01Local.apiTarget
Set-Clipboard -Value $s01Local.token
npm run dev
```

打开 **http://localhost:5173**，点击右上角“连接身份”，在“短期身份令牌”中粘贴后点击“连接会话”。连接成功后清空剪贴板；令牌只在本机使用，不粘贴到聊天、Git 或 URL。随后点击“新建补货分析”，选择 A—E 中的授权包并发起任务。

演示 API/Worker 和身份默认 **900 秒（15 分钟）** 后到期。到期或需要重启时，在两个终端各按 `Ctrl+C`，再依次重跑上面两组命令并连接新令牌；后端端口可能变化，需要重新读取 `S01_API_TARGET`。这是现有受控演示入口，常驻部署另行配置。

新克隆的仓库还需要 Python 3.13、Node.js、安装后的依赖、本机获准 `.env` 和私有教学包：`data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json`。私有包不在 Git 中。Python 安装见下方工程环境说明；若使用 `.venv`，将终端 1 的 Python 路径替换为 `.\.venv\Scripts\python.exe`。首次安装前端依赖在 `frontend/` 执行 `npm ci`。完整操作与排错见 [前端运行手册](docs/runbooks/s01-frontend.md)。

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

工程采用 Python/FastAPI、SQLAlchemy、Alembic 和 MySQL；API 与 Worker 为独立进程。阶段 A 提供迁移、权限、持久任务、预算与恢复，S01 提供准入输入→质量检查→供需计算→候选→报告保存及查询。Vue 3/Vite 前端通过同源代理消费现有 API；现有静态原型单独保留。响应缓存默认 OFF。

独立原型使用原生 HTML、CSS、JavaScript；文档工具使用 Python、Mermaid，前端浏览器回归使用 Playwright。当前工作台入口为上方 Vue 前端。

## 当前可用内容

当前 S01 前端提供工作台、建议列表、详情、逐日图表与等价表、证据弹窗和历史读取，任务由实际 API/Worker 处理；刷新按任务标识重新读取服务端结果。采购审批页保留说明，不提供审批或下单接口。旧静态原型的样例与身份为模拟，预览方式见下方。

当前独立 MySQL 8.0.27 上的迁移、权限、事务、租约/预算、API/Worker 重启恢复和 S01 模拟报告链路已有实测证据。四项真实数据/规则/ERP/模型准入仍 BLOCKED；没有采购审批或下单接口。任务与验收状态只以 [TASKS](docs/TASKS.md) 为准。

## 工程环境安装与底座入口

后端运行与用量语义见 [后端运行说明](docs/runbooks/s01-backend.md)，前端接口见 [API 对接契约](docs/contracts/s01/backend-api.md)。以下通用底座命令用于工程检查；启动当前 S01 工作台请使用上方专用启动步骤。

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
├── frontend/                         # Vue 3/TypeScript 工作台与前端测试
├── prototypes/s01/                   # 独立静态原型、自动检查、截图
├── src/commerce_hub/                  # 公共底座与 S01 工程插件
├── migrations/ / tests/ / examples/    # 迁移、自动化测试与合成输入
└── tools/                            # 演示、环境检查及文档工具
```

完整导航见 [docs/README.md](docs/README.md)。产品功能与操作流程由 [产品规格](docs/ui/PRODUCT_SPEC.md) 和可操作原型评审；视觉表达由 [DESIGN.md](DESIGN.md) 约束，两者不能互相替代。

## 旧静态原型预览与文档检查

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

按 [PLAN](docs/PLAN.md) 的 A—D 增量计划推进。前端及 C-04 教学技术验证已合入 main；普通页面真实 AI 接入、正式业务签认与完整 S01 MVP 端到端验收仍按 [TASKS](docs/TASKS.md) 的对应范围推进。企业正式规则、采购批准与执行分别验收和授权。

仓库已按负责人授权普通同步 GitHub；公开准备及历史检查见 [公开准备说明](docs/governance/PUBLICATION.md)。项目未声明开源 LICENSE；第三方资源保留其原有声明，不能据此推定已取得全部再分发许可。

本分支 S01 V2 完整补货工作台：授权全目录批量、ERP参考降级、按需单品AI及人工请购；交付范围与实际测试见[交付报告](docs/reports/S01_V2完整补货工作台交付_20261113.md)，[启动/迁移/操作手册](docs/runbooks/s01-v2.md)。状态只读TASKS；未自动合main。
