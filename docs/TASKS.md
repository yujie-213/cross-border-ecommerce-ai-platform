# 唯一任务与验收台账 v0.2

发布跟进附记（2026-11-11）：Codex 在 main / `6247e8356d5892f3ed5a1e7007e632e39263b458` 领取既有仓库许可/连接器核查，起点干净且无 remote；写入范围为 HANDOFF、TASKS 附记、THIRD_PARTY_NOTICES、governance 的 PUBLICATION/许可报告/核查 JSON。既有19项业务任务状态不变。目标账号/仓库/Public/写权限已验证，远端为空；当前连接器不支持本地提交 push，未做远端写入。许可材料与图标核查仍 BLOCKED，发布后 SHA/目录/README 检查 NOT_RUN。证据见 [增量核查](governance/LICENSE_REVIEW.md) 和 [核查记录](governance/connector-publication-check.json)；本轮提交由最终 Git 查询记录，不伪造 SHA。


本台账登记18项近期工作及1项本轮获准的独立产品/视觉原型；SETUP是本轮整理/建仓，A/B为S01必要子集，C按需，D只登记下一项S01专项设计。旧96项完整原稿/状态见archive/plan96-v0.1，旧ID映射见TASK_MAPPING.md。未来场景不预建空任务。


文档治理附记（2026-11-11）：本轮只迁移路径和记录公开准备；以下19项任务状态、依赖、验收、提交与评审历史均保持不变。治理范围/实际提交/检查和公开阻碍见HANDOFF.md及governance/PUBLICATION.md，不将文档治理计为S01或公共能力开发验收。

## S01 MVP 分阶段开发 TODO（2026-11-11—12，基于85a146e）

本节与下方JSON共同构成唯一开发台账，不另建TODO文档。负责人已确认单SKU、教学ERP只读＋受控补充、必要质量门禁、必做真实A01及排除真实审批/执行；具体依据见[ADR-S01-PLAN-001](DECISIONS.md)。原专项/MVP/ERP调查/单SKU核对等文档已经交付，独立评审仍为REVIEW；业务数据/规则/安全尚未准入，四项具体缺口单独登记BLOCKED，不能把文档完成当业务通过。

依据：[需求](requirements/REQUIREMENTS.md)、[概要设计](architecture/DEVELOPMENT_DESIGN.md)、[AI详设](agents/AI_DETAILED_DESIGN.md)、[S01专项](agents/S01_补货Agent专项详细设计.md)、[MVP v0.2](agents/S01_MVP实施文档.md)、[ERP调查](agents/S01_ERP接口调查与字段映射.md)、[单SKU准入核对](agents/S01_单SKU开发准入核对.md)；原型与视觉按现有PRODUCT_SPEC/ALIGNMENT/DESIGN。本计划细化实施任务，不重写冻结正文。

**本轮只有规划授权。** 以下“可先开发”均指负责人和星星评审本计划、随后明确授权Codex实施并满足该任务入口后；本轮不得开始。所有新开发任务仍TODO、未指派、无实现commit/测试结果；本计划所列新软件/真实ERP闭环/真实LLM/浏览器验收全部NOT_RUN；历史只读结构探测事实继续保留，不当作新验收。未解除的BLOCKED门禁也可先准备材料，但不能伪写已关闭。

| 阶段 | 复用/新增任务ID（状态只读下方JSON） | 先后与本阶段出口 |
|---|---|---|
| 0 切片契约与准入 | 复用A-01；新增D-S01-DATA-01/RULE-01/ERP-ACCESS-01/AI-ACCESS-01（完整ID以下方JSON为准） | A-01可先做最小契约/版本；身份恢复、规则和ERP安全材料可并行准备；AI用途安全依赖A-01。四门不构成“整个底座才能开始”的前置 |
| 1 最小工程 | 复用A-02→A-03/A-04→A-05；A-06工程复验 | 无ERP/模型密钥也可先做相应离线实现；MySQL与实际身份配置各在相关验收前具备；API/Worker独立，I01持久投递、O01任务与预算/G02最小审计。A-06是最终端到端前置，不挡纯计算/协议开发 |
| 2 当前数据与确定性计算 | 复用B-01/B-02、B-03/B-04；新增D-S01-LIVE-01 | B-01可先离线适配；B-02/B-03必须有规则门，B-04沿B-03；真实单SKU读取还须身份/补充与ERP安全门。B-01是D01/D02任务，B-03才对应模块B01，B-04对应模块B02，勿混淆编号 |
| 3 统一报告和必做AI | 复用B-05、C-01/C-04；新增D-S01-DEV-01 | C-01在A-05后可与B任务开发离线网关，不等待全数据；S01 Handler消费B-05/B-04/C-01并做领域校验，C-04再验该用途真实模型。任务C-01是A01网关，不是禁止的业务C01建议确认模块 |
| 4 沿原前端接入 | 新增D-S01-UI-01 | 依赖真实Handler/API与G01，先对显式工程样例联调；真实单SKU/AI展示分别受LIVE/C-04约束。保留离线原型，只改正式workspace的数据适配与已有详情展示 |
| 5 端到端与评审 | 新增D-S01-ACCEPT-01 | 依赖A-06/LIVE/Handler/UI/C-04；逐项MVP§11 S01-AC，真实ERP/受控事实/模拟工程/真实模型分开；未通过项保留，实际评审后才ACCEPTED |

依赖规则：`dependsOn`是本任务交付所需前置；`enablementGates`和`entryCondition`是特定真实模式的硬条件，不意味着离线开发也等待所有真实数据。派生DAG展示交付依赖，启用条件以本台账字段为准；禁止绕过启用条件。前置任务交付需相应评审，旧设计REVIEW不自动算通过；可由负责人只签认当前消费的契约/规则范围，不强制全部平台文档完美后才做底座。契约/迁移/组合根/依赖锁/TASKS单一集成人协调，领取时记录实际执行者/分支/基点/文件范围，不预先声称并行人已落实。

来源与证据规则：真实网络读取教学ERP、受控事实、模拟情景按环境/方式/性质分别标注。先恢复原SKU-A；恢复失败仅提出替代方案，获负责人批准才采用新映射，不扩大接口扫描。新认证、TLS例外或新接口验证须单独授权，凭据不入Git；本轮零ERP/模型调用。每项`acceptanceRefs`关联MVP§11的原S01-AC断言（不发明新编号），相关任务分别证明适用部分，D-S01-ACCEPT-01最终逐项关闭全部22项，不能拿部分单测签整项。`completionEvidence`补充了完成所需材料，不是已经存在的证据；未来证据文件只在实际使用且授权后创建并加入精确白名单。

本计划不选用C-02/A02、C-03/A03、C-05/Loop，也不新增S02任务、全S03、RAG/Memory/缓存/Redis/MQ/微服务或真实业务C01/C02/C03。PLAN的通用“C按需”仍保留历史/平台含义，当前S01已选择的C-01/C-04必做，以本台账和生效ADR为准；历史设计与调查记录不重写。

以上是当前规划增量；此前附记的任务数量和阶段授权仅保留为历史事实，实际状态仍只以下方JSON为准。

## 唯一状态与验收规则

状态仅TODO、IN_PROGRESS、BLOCKED、REVIEW、ACCEPTED。TODO不代表获准执行；领取前核对依赖、入口、实际负责人/文件范围/branch/HEAD。遇实际障碍才BLOCKED并写原因/责任/解除条件。完成实现进入REVIEW，不自动ACCEPTED；逐项验收必须有适用真实证据、实现commit、命令/环境/样本/退出码、制品/评审引用。FAIL/NOT_RUN不能填PASS，文档/Mock不替代真实ERP/模型/动作/生产验收。重要契约须评审；本轮SETUP交付REVIEW，不伪造独立验收。

TASKS的JSON记录是唯一状态源；PLAN/HANDOFF只链接状态，generated视图只读。实现/证据分提交，记录观察时HEAD而不要求文件填自己的SHA。没有提交或交接不全如实记录WIP，不能ACCEPTED。下列plannedTests都是将来的测试场景，只有evidence中的实际结果才是已执行证据。

S01设计没有A/B/C/S02硬依赖，下一条明确设计指令可直接开始。设计后的代码切片再追加稳定ID并列真实公共依赖，不能从台账TODO自动开始开发。

证据条目至少填写kind、acceptanceIds、command、environment、sample（明确模拟/真实及版本）、exitCode、result（PASS/FAIL/NOT_RUN）、artifactRef；验收签认review填写reviewer、reviewedCommit、evidenceRef及时间。逐项验收不能只写“已测”，引用产物须可定位且属于被测版本。当前未指派的角色在领取任务时落实到实际人/AI与文件范围。

## SETUP-001 精简计划/归档与本地Git交付

```json
{
  "id": "SETUP-001",
  "stage": "SETUP",
  "title": "精简计划/归档与本地Git交付",
  "kind": "management",
  "dependsOn": [],
  "entryCondition": "当前用户已明确授权计划/归档/本地Git；完成后停止",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": "本轮AI执行者",
  "allowedPaths": [
    "AGENTS.md",
    ".gitignore",
    "docs/",
    "授权白名单中的设计材料（只入库不改基线）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "同步PLAN.md/html、精简任务/协作文件、旧96项归档及映射",
    "安全白名单、扫描、真实本地初始提交与仓库回执"
  ],
  "acceptance": [
    {
      "id": "SETUP-001/AC1",
      "text": "五份既有基线不改，HLD/AI为新版计划直接依据，旧96项原状态/指纹/ID追踪保全"
    },
    {
      "id": "SETUP-001/AC2",
      "text": "MD/HTML/流程图/台账DAG及文档一致性校验通过"
    },
    {
      "id": "SETUP-001/AC3",
      "text": "真实本地Git分支/提交存在，文件不超白名单，无远端/push，无业务初始化"
    }
  ],
  "plannedTests": [
    "文档/归档/hash/依赖检查；离线浏览器检查；秘密扫描；Git提交与文件审计"
  ],
  "risks": [
    "当前只能完成用户明确的管理/本地Git范围，不能扩为业务实现"
  ],
  "requiredEvidenceKinds": [
    "DOCUMENT_CHECK",
    "REPOSITORY"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "84e68e22195d92d708afead9549d84ac3a13d3b4"
  ],
  "testedCommit": "84e68e22195d92d708afead9549d84ac3a13d3b4",
  "evidence": [
    {
      "environment": "Windows / 本地Python与Node/Edge；仅文档及本地Git",
      "sample": "五份已认可设计基线、17份归档、18项新台账、96项历史映射；无真实ERP/模型调用",
      "exitCode": 0,
      "result": "PASS",
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "SETUP-001/AC1",
        "SETUP-001/AC2"
      ],
      "command": "python docs/planning/check_plan.py",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "environment": "Windows / 本地Python与Node/Edge；仅文档及本地Git",
      "sample": "五份已认可设计基线、17份归档、18项新台账、96项历史映射；无真实ERP/模型调用",
      "exitCode": 0,
      "result": "PASS",
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "SETUP-001/AC2"
      ],
      "command": "node docs/planning/render_plan.cjs --browser-only",
      "artifactRef": "docs/planning/browser-check.json"
    },
    {
      "environment": "Windows / 本地Python与Node/Edge；仅文档及本地Git",
      "sample": "五份已认可设计基线、17份归档、18项新台账、96项历史映射；无真实ERP/模型调用",
      "exitCode": 0,
      "result": "PASS",
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "SETUP-001/AC3"
      ],
      "command": "python docs/planning/repository_audit.py staged; python docs/planning/repository_audit.py final",
      "artifactRef": "docs/planning/repository-receipt.json"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "84e68e22195d92d708afead9549d84ac3a13d3b4",
  "dirtyPaths": [
    "docs/HANDOFF.md",
    "docs/TASKS.md",
    "docs/generated/DEPENDENCIES.mmd",
    "docs/generated/STATUS.md",
    "docs/planning/FILES.md",
    "docs/planning/browser-check.json",
    "docs/planning/file-manifest.json",
    "docs/planning/initial-workspace-observation.json",
    "docs/planning/repository-receipt.json",
    "docs/planning/validation-report.json"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "真实初始commit已创建，文档/浏览器/秘密扫描/白名单/基线检查通过；不代替独立验收；证据文件由后续本地提交固定",
      "observedHead": "84e68e22195d92d708afead9549d84ac3a13d3b4"
    }
  ]
}
```

## A-01 S01所需最小版本与公共契约冻结

```json
{
  "id": "A-01",
  "stage": "A",
  "title": "S01所需最小版本与公共契约冻结",
  "kind": "design",
  "dependsOn": [
    "D-S01-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。可先评审切片契约/技术兼容方案，不等待完整数据；最终技术兼容需获准测试MySQL/身份环境实测，实际业务规则另由D-S01-RULE-01签认。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/s01/（未来）",
    "docs/DECISIONS.md",
    "docs/evidence/A-01/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "版本/驱动/OS/真实MySQL兼容矩阵和可复现依赖/测试命令冻结；不是采用文档工具环境作为生产锁",
    "最小Task/ScenarioHandler/AnalysisContext、D01-D04/B01-B02端口、Ref/错误/取消/权限/事务/版本契约及消费者矩阵",
    "沿AI详设§9.1的ModelRequest/ProviderRequest、原task预算/usage/attempt边界、S01四类解释Schema和详情AI状态契约；当前HTTP/options/报告/证据DTO及同源前端/身份接入方案"
  ],
  "acceptance": [
    {
      "id": "A-01/AC1",
      "text": "精确版本有实测证据；MySQL目标/驱动/UTC/精度明确，不用latest或SQLite替代"
    },
    {
      "id": "A-01/AC2",
      "text": "O01/D01-D04/B01/B02/A01/G01/G02/I01边界与资产所有者明确；未知/零/无适用值、三轴来源和业务完整性/技术状态/AI状态区分；当前必做AI子集纳入，不扩全AI"
    },
    {
      "id": "A-01/AC3",
      "text": "契约正反例、消费者/兼容/安全与测试影响经负责人/星星或指定契约评审者核对；重要变化先ADR，未定业务数值不硬编码"
    }
  ],
  "plannedTests": [
    "兼容性实验与真实MySQL最小探测（以后明确授权环境内）；契约Schema/引用/未知值/越权负例；S01-AC与旧MC隔离核查"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "精确版本矩阵、契约样例/消费者清单、实测命令及评审引用；测试运行命令在此冻结后供后续任务采用。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-DATA01",
    "S01-AC-MAP01",
    "S01-AC-SEC01",
    "S01-AC-AI03",
    "S01-AC-AI04"
  ]
}
```

## A-02 最小骨架、配置、错误与日志

```json
{
  "id": "A-02",
  "stage": "A",
  "title": "最小骨架、配置、错误与日志",
  "kind": "development",
  "dependsOn": [
    "A-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-01当前子集评审后可先开发，不需要ERP数据或模型密钥。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "pyproject.toml（未来）",
    "依赖锁文件（A-01冻结实际路径）",
    "src/commerce_hub/bootstrap/",
    "src/commerce_hub/entrypoints/",
    "tests/unit/bootstrap/（未来）",
    "docs/evidence/A-02/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "仅按使用创建模块化包、依赖锁、FastAPI工厂、统一配置/错误/trace日志",
    "无秘密的配置示例，ERP/模型未配置时相应模式关闭，live/ready语义与未来独立Worker入口边界"
  ],
  "acceptance": [
    {
      "id": "A-02/AC1",
      "text": "干净环境可复现启动；不预建无消费者目录/缓存/Agent平台"
    },
    {
      "id": "A-02/AC2",
      "text": "错误/日志脱敏；基础配置缺失安全失败；API启动不迁移、不启动Worker或模型，ERP/AI缺配置不伪造可用"
    }
  ],
  "plannedTests": [
    "冻结命令的启动/缺配置/错误信封/秘密脱敏/未用依赖检查"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "依赖锁与实际启动/负例日志；不含ERP/模型调用证据。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-ENG01",
    "S01-AC-SEC01"
  ]
}
```

## A-03 MySQL、SQLAlchemy与Alembic子集

```json
{
  "id": "A-03",
  "stage": "A",
  "title": "MySQL、SQLAlchemy与Alembic子集",
  "kind": "development",
  "dependsOn": [
    "A-02"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-02之后可先准备必要存储实现；真实迁移/事务验收必须有获准MySQL实例/账号/目标版本，缺环境不能算完成。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "migrations/（未来）",
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/adapters/mysql/",
    "tests/integration/mysql/（未来）",
    "docs/evidence/A-03/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "实际资产所有者的必要Repository/短事务/精确类型和显式唯一Alembic迁移链",
    "真实MySQL迁移、回滚、并发/事务边界测试和最小运行说明；网络在锁外、每分支独立Session"
  ],
  "acceptance": [
    {
      "id": "A-03/AC1",
      "text": "干净库迁移/失败回滚、tenant键/Decimal/UTC/唯一键验证通过，SQLite不替代"
    },
    {
      "id": "A-03/AC2",
      "text": "只建当前消费者表；各模块自己写资产，跨模块走公开契约；API/Worker不自动迁移"
    }
  ],
  "plannedTests": [
    "真实MySQL迁移/约束/精度/短事务与并发回滚；网络锁外与Session隔离测试"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "目标MySQL/驱动版本、迁移head/命令/退出码及并发/回滚日志；无实例则真实测试NOT_RUN。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-ENG01",
    "S01-AC-TX01"
  ]
}
```

## A-04 身份认证、权限与租户必要子集

```json
{
  "id": "A-04",
  "stage": "A",
  "title": "身份认证、权限与租户必要子集",
  "kind": "development",
  "dependsOn": [
    "A-02"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-01/A-02契约后可先做受控签名测试身份与越权路径；真实浏览器发行方/会话与租户范围须负责人签认后启用。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/governance/access/",
    "tests/security/（当前身份与浏览器边界）",
    "docs/evidence/A-04/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "G01可信身份/租户/当前scope/字段权限窄实现，API/Worker/数据/证据统一授权",
    "沿已冻结同源方案的浏览器身份传输、会话期限/CSRF等相应控制；无重复用户管理产品"
  ],
  "acceptance": [
    {
      "id": "A-04/AC1",
      "text": "测试身份也验证签名/发行方/期限，无匿名旁路/前端角色授予权限"
    },
    {
      "id": "A-04/AC2",
      "text": "跨租户同名SKU、扩大scope/证据越权、撤权读与发布均被拒；凭据不进JS/URL/日志"
    }
  ],
  "plannedTests": [
    "签名/过期/范围伪造/跨租户/撤权、所选浏览器认证负例"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "获准身份配置引用及API/Worker/证据边界安全负例；测试身份和正式身份配置证据分开。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-SEC01"
  ]
}
```

## A-05 API/独立Worker与MySQL持久任务

```json
{
  "id": "A-05",
  "stage": "A",
  "title": "API/独立Worker与MySQL持久任务",
  "kind": "development",
  "dependsOn": [
    "A-03",
    "A-04"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-03/A-04后开发持久任务骨架；不要求ERP或模型在线，测试装配与生产注册隔离。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/entrypoints/",
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/governance/observability/",
    "tests/integration/orchestration/（未来）",
    "docs/evidence/A-05/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "API/独立Worker两个进程、MySQL I01工作项/lease fencing/重试/恢复与O01最小受理/取消",
    "O01原task期限/额度许可、attempt预留/结算/未知usage占额的公开端口及G02最小审计；由C-01使用，不再另造预算账本"
  ],
  "acceptance": [
    {
      "id": "A-05/AC1",
      "text": "任务/工作项/必需审计短事务一致，命令key同内容重放/异内容409；当前lease/plan/权限发布门禁有效"
    },
    {
      "id": "A-05/AC2",
      "text": "重启不丢投递，取消/超期/重试耗尽有界，恢复不重置deadline/预算；网络在锁外"
    },
    {
      "id": "A-05/AC3",
      "text": "未实现S01 Handler不在生产装配注册；测试适配不冒充业务完成；不引MQ/通用Runtime"
    }
  ],
  "plannedTests": [
    "真实MySQL双PID停启/重复领取/旧lease/事务失败/取消/期限与预算竞争、未知usage占额测试"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "真实两个PID和MySQL故障/预算日志、任务/投递/审计一致性证据；不填S02 MC。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-TX01",
    "S01-AC-REC01",
    "S01-AC-CONC01",
    "S01-AC-CANCEL01",
    "S01-AC-AI05"
  ]
}
```

## A-06 工程底座复现与故障验收

```json
{
  "id": "A-06",
  "stage": "A",
  "title": "工程底座复现与故障验收",
  "kind": "validation",
  "dependsOn": [
    "A-05"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-05之后验收已用底座，不阻止B/C纯模块开发；S01整体验收必须引用本结果。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "tests/integration/实际工程范围（未来）",
    "docs/evidence/A-06/（未来）",
    "docs/runbooks/最小运行说明（未来）",
    "docs/evidence/A-06/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "干净环境启动/迁移/停启/恢复/去重/取消/权限/预算复现说明与工程证据矩阵"
  ],
  "acceptance": [
    {
      "id": "A-06/AC1",
      "text": "真实MySQL+FastAPI+独立Worker可复现，适用故障/隔离无未解决硬失败"
    },
    {
      "id": "A-06/AC2",
      "text": "只验工程底座；不宣称真实ERP/模型/S01业务或S02 MC通过"
    }
  ],
  "plannedTests": [
    "干净库/双进程恢复/过期lease/重复投递/取消/预算/鉴权/日志回归"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "基于真实实现commit的工程复验命令、环境、退出码和原始日志；明确工程与业务证据类别。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-ENG01",
    "S01-AC-TX01",
    "S01-AC-REC01",
    "S01-AC-CONC01",
    "S01-AC-SEC01",
    "S01-AC-CANCEL01"
  ]
}
```

## B-01 D01/D02 S01输入适配与标准化

```json
{
  "id": "B-01",
  "stage": "B",
  "title": "D01/D02 S01输入适配与标准化",
  "kind": "development",
  "dependsOn": [
    "D-S01-01",
    "A-03",
    "A-04"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-03/A-04后，可先按A-01契约开发离线解析、可替换SourceConnector和受控文件校验；实际身份/字段投影受D-S01-DATA-01和D-S01-RULE-01约束，真实ERP调用另过D-S01-ERP-ACCESS-01；闭环真实读取由D-S01-LIVE-01验收。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/sync/",
    "src/commerce_hub/data/projection/",
    "src/commerce_hub/adapters/sources/",
    "tests/unit/data/（未来）",
    "tests/integration/data/（未来）",
    "docs/evidence/B-01/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "D01教学ERP窄只读适配与受控补充入口、批次/覆盖/错误分类/有界分页和重试；fixture仅用于测试/异常/离线",
    "D02按版本身份/单位/状态映射与不可变投影，三轴记录读取环境/获取方式/事实或情景；只支持当前单SKU字段",
    "采用已调查full库存/主数据及获准订单/采购行来源；503/缺日期/缺店绑定/行未收为空显式保留，不按名称或单头数量猜值"
  ],
  "acceptance": [
    {
      "id": "B-01/AC1",
      "text": "模拟情景、受控事实、真实网络读取教学系统明确区分；不能默换fixture或把教学源称生产事实"
    },
    {
      "id": "B-01/AC2",
      "text": "覆盖不足/未映射/空列表/无效单位/未知数量日期不补0或猜值；供给/镜像不重复累加，部分批次不标完整"
    },
    {
      "id": "B-01/AC3",
      "text": "读接口方法/路径由获准白名单限制；兼容POST只开放文档及授权确认的只读查询，不注册草稿/审批/执行"
    }
  ],
  "plannedTests": [
    "离线契约样例去重/映射/空值/乱序/重放/分页中断/503/403/超时测试；真实读取另由D-S01-LIVE-01记录"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "离线测试标simulated、具体映射/批次/来源版本与错误路径证据；真实读取结果不能仅由本任务Mock替代。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [
    "D-S01-DATA-01",
    "D-S01-RULE-01",
    "D-S01-ERP-ACCESS-01"
  ],
  "acceptanceRefs": [
    "S01-AC-DATA01",
    "S01-AC-MAP01",
    "S01-AC-SOURCE01"
  ]
}
```

## B-02 D03/D04 S01质量/快照与证据

```json
{
  "id": "B-02",
  "stage": "B",
  "title": "D03/D04 S01质量/快照与证据",
  "kind": "development",
  "dependsOn": [
    "B-01",
    "D-S01-RULE-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。质量/覆盖/日期等规则矩阵签认后开发；可以用显式测试样例验证缺失/冲突，不要求所有真实质量事实齐备才实现阻断。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/quality/",
    "src/commerce_hub/data/evidence/",
    "tests/integration/data/（当前质量与证据）",
    "docs/evidence/B-02/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "D03单SKU完整性/时效/覆盖/质量与唯一snapshot manifest；D04受当前权限保护的证据定位",
    "质量不足/调查条件的限制随版本固化，manifest固定D02修订，不伪称跨系统原子历史快照"
  ],
  "acceptance": [
    {
      "id": "B-02/AC1",
      "text": "新增输入产生新版本，旧manifest可定位实际修订；无latest空壳或私写跨模块表"
    },
    {
      "id": "B-02/AC2",
      "text": "必需质量缺失/过期/冲突不放行采购；允许的供需事实与整体报告限制分开"
    },
    {
      "id": "B-02/AC3",
      "text": "原记录/指标/候选证据引用可追溯，撤权/删除/断链不泄露或伪造结论"
    }
  ],
  "plannedTests": [
    "缺项/过旧/覆盖不足/身份歧义/质量调查/新输入/断链/撤权及固定manifest重放"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "S01-AC-DATA01/MAP01/QUALITY01相应结果、manifest/策略/证据版本及授权负例，真实数据证据留受控引用。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-DATA01",
    "S01-AC-MAP01",
    "S01-AC-QUALITY01",
    "S01-AC-REPORT01",
    "S01-AC-SEC01"
  ]
}
```

## B-03 B01 S01确定性供需指标

```json
{
  "id": "B-03",
  "stage": "B",
  "title": "B01 S01确定性供需指标",
  "kind": "development",
  "dependsOn": [
    "A-01",
    "D-S01-RULE-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。已签认的MetricDefinition/需求与时间口径后可用固定期望样例开发纯B01，不需要ERP在线或真实SKU已绑定；未签认不得选常见公式代替。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/metrics/",
    "tests/unit/metrics/s01/（未来）",
    "docs/evidence/B-03/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "当前使用的净可售或互斥分桶、逐日余额/首缺/缓冲与净缺口唯一确定性评价器",
    "版本化输入/MetricDefinition/情景/结果Refs和未知/不可算表达，数量精确类型；若存在适用金额硬约束则落实相应评价或阻断"
  ],
  "acceptance": [
    {
      "id": "B-03/AC1",
      "text": "净额不重复扣，预留与新增需求不重复计；有效未收只在获准可售日进入，同一供给不重复加"
    },
    {
      "id": "B-03/AC2",
      "text": "日期/同日顺序/窗口/缓冲/负余额等与签认规则一致；不能从空值/失败推0或日期"
    },
    {
      "id": "B-03/AC3",
      "text": "事实与模拟情景用同一评价器；LLM/前端/B02不复制权威公式，S01-AC不冒充MC"
    }
  ],
  "plannedTests": [
    "签认固定期望与边界：需求AC演示、延期、空/缺值、单位、部分收货/镜像/日期端点；演示专用策略标simulated"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "S01-AC-CALC01/DATE01等固定期望、MetricDefinition版本、输入来源和实际结果；真实SKU事实未就绪时只算工程样例证据。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-CALC01",
    "S01-AC-DATE01",
    "S01-AC-MAP01"
  ]
}
```

## B-04 B02 S01基线/候选与约束

```json
{
  "id": "B-04",
  "stage": "B",
  "title": "B02 S01基线/候选与约束",
  "kind": "development",
  "dependsOn": [
    "B-03"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。B-03与相同已签认需求/候选/质量策略后可做纯候选逻辑；真实日期/MOQ/倍数未知必须拒绝相应候选，不以样例值代替。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/forecasting/",
    "tests/unit/forecasting/s01/（未来）",
    "docs/evidence/B-04/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "B02显式需求情景/已选预测基线、有限候选、MOQ/订购倍数/日期/其他硬约束及比较Refs",
    "每个候选调用B01评价；无解/约束未知/只基线的领域限制，不实现通用求解平台"
  ],
  "acceptance": [
    {
      "id": "B-04/AC1",
      "text": "箱规不自动等于倍数，未收不按单头分摊；无依据日期/硬约束不产可采购候选"
    },
    {
      "id": "B-04/AC2",
      "text": "每个候选引用同版本B01结果，不另算首缺/逐日值；未签认权重不称最优"
    },
    {
      "id": "B-04/AC3",
      "text": "必需质量不足按策略限制候选/采购适用性，不因库存紧张或LLM解释放宽"
    }
  ],
  "plannedTests": [
    "MOQ/倍数/日期/金额硬约束适用性、延期/无解/缺值/质量限制与B01调用唯一性"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "S01-AC-CAND01及已签认比较断言的输入/候选/B01Refs和实际结果；模拟候选不证明实际供应承诺。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-CALC01",
    "S01-AC-DATE01",
    "S01-AC-CAND01",
    "S01-AC-QUALITY01"
  ]
}
```

## B-05 O01 Handler调度/报告与G01/G02边界

```json
{
  "id": "B-05",
  "stage": "B",
  "title": "O01 Handler调度/报告与G01/G02边界",
  "kind": "development",
  "dependsOn": [
    "A-05",
    "B-02",
    "B-03"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-05/B-02/B-03后实现O01公共发布子集，不再实现S01业务Workflow或第二调度；真实业务注册由D-S01-DEV-01负责。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/workspace/",
    "tests/integration/orchestration/（当前发布用例）",
    "docs/evidence/B-05/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "公开ScenarioHandler/DomainResult和O01任务/计划/participant/snapshot/报告关系、最小查询/发布读口",
    "当前权限/lease/plan/取消/期限/证据与版本审校、不可变报告/幂等发布；业务完整性与AI状态独立"
  ],
  "acceptance": [
    {
      "id": "B-05/AC1",
      "text": "O01只发布领域结果，不计算库存/候选/解释语义；D03/D04/B01/B02资产只经公开口使用"
    },
    {
      "id": "B-05/AC2",
      "text": "报告事务/去重/刷新重读和撤权有效；未发布/取消/失lease不出现假reportRef"
    },
    {
      "id": "B-05/AC3",
      "text": "没有业务C01/C02/C03真实确认/审批/执行端点，不把受限报告技术成功写成业务通过"
    }
  ],
  "plannedTests": [
    "领域契约、发布回滚/重复发布/旧plan/旧lease/取消/断链/撤权/并发与历史报告重读"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "S01-AC-REPORT01/RECOVERY01/SECURITY01相关工程证据、版本绑定及失败无报告证明。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-REPORT01",
    "S01-AC-REC01",
    "S01-AC-CONC01",
    "S01-AC-CANCEL01",
    "S01-AC-SEC01",
    "S01-AC-READONLY01"
  ]
}
```

## C-01 A01/ModelProvider与调用控制最小实现

```json
{
  "id": "C-01",
  "stage": "C",
  "title": "A01真实解释必需的网关/Provider与调用控制子集",
  "kind": "development",
  "dependsOn": [
    "A-05",
    "A-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-05/A-01后可先开发离线协议/Schema/超时/预算路径；一个真实Provider/deployment及许可配置须D-S01-AI-ACCESS-01签认后才可调用，受限评测不等于正式用途已开放。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/models/",
    "src/commerce_hub/adapters/models/",
    "当前Prompt/Context/Schema资源（A-01冻结实际路径）",
    "tests/unit/models/（未来）",
    "docs/evidence/C-01/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "既有ModelRequest/ProviderRequest和一个获准ModelProvider适配，结构输出、技术错误/拒答/截断/usage与实际模型版本",
    "当前S01用途Prompt/Context/输出Schema/参数版本最小管理、O01原task allowance预留/结算接口、G02调用与usage日志",
    "不创建第二模型网关/预算、RAG/Tool/Loop或缓存设施；缓存OFF"
  ],
  "acceptance": [
    {
      "id": "C-01/AC1",
      "text": "超时/重试/取消共享原task期限与预算；未发出/已发出未知usage区分并保守占额，无隐藏重试"
    },
    {
      "id": "C-01/AC2",
      "text": "Prompt/Context/Schema/deployment/model/参数/计价/attempt可追，日志无凭据和无差别业务正文"
    },
    {
      "id": "C-01/AC3",
      "text": "A01校验结构与技术事实，不改B01/B02结果、不执行工具；网关单测或Provider连通不等于C-04用途验收"
    }
  ],
  "plannedTests": [
    "ModelRequest/ProviderRequest正反例；结构/拒答/截断/超时/取消/未知usage/额度竞争/日志负例；真实调用另过安全门及C-04"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "网关协议与预算负例、精确版本和实际Provider适配记录；Mock/未发送/真实请求证据分开。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [
    "D-S01-AI-ACCESS-01"
  ],
  "acceptanceRefs": [
    "S01-AC-AI01",
    "S01-AC-AI02",
    "S01-AC-AI04",
    "S01-AC-AI05"
  ]
}
```

## C-02 A02内容理解与结构化产物（按需）

```json
{
  "id": "C-02",
  "stage": "C",
  "title": "A02内容理解与结构化产物（按需）",
  "kind": "conditional-development",
  "dependsOn": [
    "C-01"
  ],
  "entryCondition": "只有真实理解/抽取用例，数据许可/模式/金标准明确",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/understanding/",
    "当前理解用途Schema/评测（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "实际分类/抽取用途、UNKNOWN、引用/人工修订与usage关联"
  ],
  "acceptance": [
    {
      "id": "C-02/AC1",
      "text": "成功/技术失败/语义UNKNOWN分开，ID/位置/Schema校验"
    },
    {
      "id": "C-02/AC2",
      "text": "产物归A02，D04引用；不接管分母/权威身份"
    }
  ],
  "plannedTests": [
    "当前用途的成功/失败/UNKNOWN/注入/位置/版本与人审样例"
  ],
  "risks": [
    "不先开发VOC或全A02来阻塞S01"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": []
}
```

## C-03 A03 RAG/只读Tool/Skill最小契约（按需）

```json
{
  "id": "C-03",
  "stage": "C",
  "title": "A03 RAG/只读Tool/Skill最小契约（按需）",
  "kind": "conditional-development",
  "dependsOn": [
    "C-01",
    "B-02"
  ],
  "entryCondition": "只在业务需要RAG/工具时，所需公开端口和范围已验证",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/retrieval/",
    "当前ToolSpec/Skill资源（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "权限预过滤检索、证据回源、最小ToolSpec/Registry/Executor和Skill元数据"
  ],
  "acceptance": [
    {
      "id": "C-03/AC1",
      "text": "工具提案经后端Schema/权限/预算门禁，无C03/任意SQL/shell/URL"
    },
    {
      "id": "C-03/AC2",
      "text": "Skill/工具版本可追，不默认MCP服务/向量图数据库"
    },
    {
      "id": "C-03/AC3",
      "text": "正式任务许可与即席QueryRun不混；完整即席另过HLD6.4"
    }
  ],
  "plannedTests": [
    "越权/撤权/注入/参数伪造/版本/证据/预算与错误负例"
  ],
  "risks": [
    "无实际检索/工具需求则不创建目录/服务"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "SIMULATED_ENGINEERING"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": []
}
```

## C-04 已选模型用途最小评测与Golden Dataset

```json
{
  "id": "C-04",
  "stage": "C",
  "title": "S01真实模型解释用途评测与安全降级验收（必做）",
  "kind": "validation",
  "dependsOn": [
    "C-01",
    "D-S01-DEV-01",
    "D-S01-AI-ACCESS-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。安全门签认、S01语义门禁实现后，使用获准固定B01/B02结果/证据集做有界真实模型评测；模型评测不要求扩大ERP采集，不向模型发送未经许可的原始数据。",
  "ownerRole": "领取时由负责人指定实际模块执行者；公共契约/迁移/组合根/锁文件/TASKS由指定集成人串行协调",
  "assignee": null,
  "allowedPaths": [
    "tests/evaluation/当前用途（未来）",
    "docs/evidence/C-04/（未来）",
    "docs/evidence/C-04/（未来，仅脱敏证据）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "当前四类解释的许可样本/金标准、规则/人工分层判定与已签认硬失败/语义门禁；版本化评测结果",
    "真实API成功、失败降级/篡改数字日期/错引用/注入/预算等证据与实际usage/费用/耗时；无未经验证收益数字",
    "AI01/AI02的界面断言由D-S01-UI-01和整体验收共同关闭；本任务只证明真实调用/服务端用途与降级，不提前宣称页面验收"
  ],
  "acceptance": [
    {
      "id": "C-04/AC1",
      "text": "真实获准LLM API至少有有效成功及结构/引用/语义通过证据；Mock/固定文字不能替代"
    },
    {
      "id": "C-04/AC2",
      "text": "建议原因/关键依据/主要风险/人工确认四类结构保持权威量/日期/约束/质量/审批不变；越权/无依据结论/错引用硬失败不平均"
    },
    {
      "id": "C-04/AC3",
      "text": "失败明确AI解释不可用，仍保留符合条件规则结果；实际费用/usage/模型Prompt版本可追；启用范围经负责人/指定用途评审者签认"
    }
  ],
  "plannedTests": [
    "S01-AC-AI01—05：真实调用+结构/领域门禁、超时不可用、注入/隐私、迟到取消预算；实际模型与故障注入类别分开"
  ],
  "risks": [
    "实际业务数据/规则/运行条件以相应准入记录和当前授权为准；测试样例不冒充企业事实。"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "changeType": "PLANNING_REFINEMENT",
      "reason": "基于85a146e和ADR-S01-PLAN-001细化当前S01消费者范围，状态仍TODO、未领取或编码",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "completionEvidence": [
    "真实Provider关联、版本/usage/耗时、结构/语义/安全判定与人工评审；阈值待安全门签认，不虚构已达标。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "acceptanceRefs": [
    "S01-AC-AI01",
    "S01-AC-AI02",
    "S01-AC-AI03",
    "S01-AC-AI04",
    "S01-AC-AI05"
  ]
}
```

## C-05 Runtime/Harness/Loop启用评审（按需）

```json
{
  "id": "C-05",
  "stage": "C",
  "title": "Runtime/Harness/Loop启用评审（按需）",
  "kind": "conditional-design",
  "dependsOn": [],
  "entryCondition": "只有已选用例证明Workflow不足；重要契约变化经评审",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "当前用途运行约束设计（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "固定Workflow不足的证据、预算/状态/工具/暂停恢复/停止方案"
  ],
  "acceptance": [
    {
      "id": "C-05/AC1",
      "text": "无第二O01/预算/状态权威；RunOutcome由Handler转DomainResult"
    },
    {
      "id": "C-05/AC2",
      "text": "YIELD不发布、重试/恢复共享期限/预算；无收益结论可为不启用"
    },
    {
      "id": "C-05/AC3",
      "text": "此任务只评审，若需要代码另拆获准切片，不建Agent平台"
    }
  ],
  "plannedTests": [
    "与固定Workflow对照、状态/预算/取消/无进展/安全方案审查"
  ],
  "risks": [
    "无实际需求不创建Runtime、持久化平台或多Agent通信"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": null,
  "dirtyPaths": [],
  "latestHandoffRef": null,
  "blocker": null,
  "history": []
}
```

## D-S01-01 S01补货专项详细设计（第一阶段）

```json
{
  "id": "D-S01-01",
  "stage": "D",
  "title": "S01补货专项详细设计（第一阶段）",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "2026-11-11 用户明确授权第一阶段专项设计；只交设计主文档及必要索引/台账，不调查ERP、不拆开发TODO、不编码",
  "ownerRole": "S01专项设计文档集成人；负责人独立评审待签认",
  "assignee": "Codex（本轮唯一文档执行者与台账集成人）",
  "allowedPaths": [
    "docs/agents/S01_补货Agent专项详细设计.md",
    "docs/agents/index.md",
    "docs/README.md",
    "docs/TASKS.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/git-whitelist.json",
    "docs/planning/validation-report.json",
    "docs/agents/S01_补货Agent专项详细设计.html",
    "docs/agents/scripts/build_s01_reading.cjs"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "一份S01专项详细设计主文档：定位、设计思想、架构/意图/时序及逐图讲稿、逻辑伪代码、边界、待确认项",
    "本轮不追加实现切片、MVP计划或开发TODO；评审后另行授权",
    "2026-11-11 追加授权：从Markdown生成离线HTML阅读版；保留正文、图表与讲稿，不改变业务设计"
  ],
  "acceptance": [
    {
      "id": "D-S01-01/AC1",
      "text": "不以S02、旧MC通过或全B/C就绪为设计前置"
    },
    {
      "id": "D-S01-01/AC2",
      "text": "可售分桶/日需求/供给可售日/MOQ/倍数/缓冲/缺质量信号阻断明确"
    },
    {
      "id": "D-S01-01/AC3",
      "text": "真实未知列待确认，模拟不冒充真实ERP/收益；公共契约重要变更有评审"
    }
  ],
  "plannedTests": [
    "本轮文档结构/相对链接/图与讲稿对应/冻结基线及Mermaid离线parse+render；不执行ERP、模型或业务工程测试",
    "负责人独立专项设计评审；业务口径不足保持待确认，不冻结生产字段或阈值",
    "node docs/agents/scripts/build_s01_reading.cjs --check：离线阅读版、同源指纹、图表/讲稿/伪代码、响应布局与阅读交互；不代表S01业务验收"
  ],
  "risks": [
    "输入不足可先形成有缺口的设计，不补造企业事实"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "858af84b8527adee98a26a2e87ed8fdf10d81e90",
    "a0c26153e65020d1b061556e84b27b74dce9964e"
  ],
  "testedCommit": "a0c26153e65020d1b061556e84b27b74dce9964e",
  "evidence": [
    {
      "kind": "DESIGN_SELF_CHECK",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC2",
        "D-S01-01/AC3"
      ],
      "command": "作者逐项对照需求/概要/AI详设/PLAN/DECISIONS/UI/视觉与协作规范；PowerShell here-string | python -（图/讲稿/链接/范围检查）",
      "environment": "Windows / Python；作者自检，不是负责人独立签认",
      "sample": "主文档第一阶段v0.1；9张图与9份紧随讲稿、6块伪代码、14处相对链接；未知公式/阈值/真实ERP字段集中列Q01—Q11，不补造企业事实",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_补货Agent专项详细设计.md"
    },
    {
      "kind": "MERMAID_RENDER",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC3"
      ],
      "command": "PowerShell单引号here-string | node -；Playwright提取本文9个Mermaid块，依次mermaid.parse与mermaid.render，检查SVG/viewBox/错误/网络",
      "environment": "Windows / 已有Playwright / 本地headless Edge / Mermaid 11.4.1；内存页面、阻止HTTP，无展示副本",
      "sample": "设计提交858af84b8527adee98a26a2e87ed8fdf10d81e90图源；9/9成功，pageerror=0、网络=0；图源集合SHA256=53a5e74f127c28eadcb512b9c2194c624655eacd091d2690206ef1ba0290e568",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_补货Agent专项详细设计.md"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC3"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / 本地Python与Git；仅文档与台账检查",
      "sample": "19项既有任务；18项检查PASS；五份冻结基线/原型实现未改。首次tracked-whitelist失败为基点已存在的两份授权治理文件漏列，定向补路径后PASS；普通CRLF空白误报保留换行后重验",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC3"
      ],
      "command": "PowerShell here-string | python -B -（对照Git基点/设计提交，检查图源/伪代码、其余任务JSON、14个保全文件、精确变更范围与秘密模式）；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / 本地Python与Git；只读Git对象对照，不访问ERP/模型",
      "sample": "基点895167c7c1b76db2e46209fa4480e4819e65a06f；图源与伪代码不变、其余18项任务不变、任务数仍19；14指定基线/原型/旧治理文件字节保全；本轮9份精确文档变更、秘密0发现、未跟踪0",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    },
    {
      "kind": "DESIGN_REVIEW",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC2",
        "D-S01-01/AC3"
      ],
      "command": "NOT_RUN：等待负责人独立专项设计评审与口径签认",
      "environment": "无负责人独立评审",
      "sample": "第一阶段专项设计评审稿；Q01—Q11及X04等未签认，不代表开发/业务验收完成",
      "exitCode": null,
      "result": "NOT_RUN",
      "artifactRef": "docs/agents/S01_补货Agent专项详细设计.md"
    },
    {
      "kind": "HTML_READING_VIEW",
      "acceptanceIds": [
        "D-S01-01/AC1",
        "D-S01-01/AC3"
      ],
      "command": "node docs/agents/scripts/build_s01_reading.cjs；node docs/agents/scripts/build_s01_reading.cjs --check",
      "environment": "Windows / 已有Python markdown、Node/Playwright、本地headless Edge、Mermaid 11.4.1；仅文档构建，阻止HTTP",
      "sample": "HTML提交a0c26153e65020d1b061556e84b27b74dce9964e；11章、9张内嵌SVG/9份讲稿/6块伪代码；1440/1920/390三宽×深浅6组布局PASS；9图放大/缩放/适宽/Esc焦点恢复、拖动、手机弹窗、主题记忆、讲稿与图源展开、页内锚点PASS；浏览器错误/远程请求0；作者查看桌面/图表原尺寸/手机深色截图；HTML SHA256=eb48d77111d005a9460ae27c5081eacc08ffc49864de918b23071300df92dd71；MD SHA256=53684a012e65115c320569cb6acf4737dc51edc0a3523f59a9ff01f6ccf1ed9a且原字节未改",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_补货Agent专项详细设计.html"
    },
    {
      "kind": "HTML_DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-01/AC3"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check；定向Python/Git保全与秘密模式核对",
      "environment": "Windows / 本地Python、Git；文档与仓库范围检查",
      "sample": "18项文档检查PASS；源MD与14指定文件保全、其余18项任务未变；本轮10份精确变更秘密0发现。未知未跟踪docs/ERP-openapi.yaml为收尾期间出现，未读取/修改/暂存；无业务验收",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "a0c26153e65020d1b061556e84b27b74dce9964e",
  "dirtyPaths": [
    "docs/ERP-openapi.yaml"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "用户明确授权S01第一阶段专项设计，采用指定agents路径替代旧建议scenarios路径；保留冻结需求与总体架构，不进入后续阶段",
      "observedHead": "895167c7c1b76db2e46209fa4480e4819e65a06f"
    },
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "只交第一阶段专项设计；1架构/3意图/5时序及9份讲稿，逻辑伪代码/降级/人工/待决项齐全。图表离线渲染和文档自检通过，负责人独立评审NOT_RUN；未拆MVP/TODO、未调查ERP、未开发，停止等待评审。",
      "observedHead": "858af84b8527adee98a26a2e87ed8fdf10d81e90"
    },
    {
      "date": "2026-11-11",
      "from": "REVIEW",
      "to": "REVIEW",
      "reason": "用户追加HTML阅读版授权；Codex单人负责HTML/文档构建脚本/导航及台账交接，设计评审状态不变，禁止扩展为业务开发",
      "observedHead": "c7e3dca74295a737eab40f8e46445e5d93a94f95"
    },
    {
      "date": "2026-11-11",
      "from": "REVIEW",
      "to": "REVIEW",
      "reason": "新增授权的HTML阅读版已本地提交并通过离线浏览器检查。首轮390px页尾长hash溢出FAIL已修复，重测6组布局与交互PASS。MD与冻结设计/原型不变；无ERP/模型/业务开发，独立设计评审仍NOT_RUN。 收尾新出现未跟踪docs/ERP-openapi.yaml，归属未知，保留且未读取/修改/暂存。",
      "observedHead": "a0c26153e65020d1b061556e84b27b74dce9964e"
    }
  ]
}
```

## UX-S01-01 S01独立产品原型与视觉规范（本轮授权）

```json
{
  "id": "UX-S01-01",
  "stage": "D",
  "title": "S01采购补货交互原型与项目视觉规范",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "2026-11-11 用户明确授权参考研究、DESIGN.md、独立浏览器原型与一致性检查；未经确认不得正式前端开发",
  "ownerRole": "本轮原型/文档集成人",
  "assignee": "Codex（本轮AI执行者，实际同文件唯一写入者）",
  "allowedPaths": [
    "DESIGN.md",
    "prototypes/s01/",
    "docs/ui/",
    "docs/TASKS.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/git-whitelist.json",
    "docs/planning/validation-report.json"
  ],
  "parallelCondition": "本轮单一执行者，无并行写入；保留既有未知文件与五份冻结基线",
  "deliverables": [
    "独立离线四页交互原型；与正式业务代码隔离",
    "项目专属DESIGN.md与独立PRODUCT_SPEC.md",
    "三份来源研究、需求对照/占位/未实现清单、800字内设计说明、真实浏览器证据"
  ],
  "acceptance": [
    {
      "id": "UX-S01-01/AC1",
      "text": "SAP/Airtable/Shopify来源可定位；视觉规范独立综合，产品功能规格单独维护"
    },
    {
      "id": "UX-S01-01/AC2",
      "text": "工作台/建议列表/详情/人工审批可预览，筛选/异常/人工终点演示可复查"
    },
    {
      "id": "UX-S01-01/AC3",
      "text": "只读首期、质量阻断、版本/角色/UNKNOWN边界对照；占位与未实现明确，不冒充MC/ERP验收"
    },
    {
      "id": "UX-S01-01/AC4",
      "text": "有真实浏览器/文档校验与制品指纹；设计说明不超过800字；负责人评审后才考虑正式开发"
    }
  ],
  "plannedTests": [
    "node prototypes/s01/check.cjs：离线交互、四宽度、异常/角色/版本；人工截图检查",
    "python docs/planning/build_docs.py；python docs/planning/check_plan.py；源基线/未知文件保全检查"
  ],
  "risks": [
    "原型不冻结企业字段/质量矩阵或真实审批策略",
    "D-S01-01完整专项仍待后续：本任务不是其全部设计或业务实现验收"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_FRONTEND",
    "DESIGN_ALIGNMENT"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "8140d40439517f957044537fdffa11f2c5a6463e",
    "9a7c9a34bd4079fbdb8bef65b80c7dcdea224df4",
    "4df78d585b73fbffb2066c813a9ef087e5e1466c"
  ],
  "testedCommit": "4df78d585b73fbffb2066c813a9ef087e5e1466c",
  "evidence": [
    {
      "kind": "SIMULATED_FRONTEND",
      "acceptanceIds": [
        "UX-S01-01/AC2",
        "UX-S01-01/AC3",
        "UX-S01-01/AC4"
      ],
      "command": "node prototypes/s01/check.cjs",
      "environment": "Windows / existing Playwright / local headless Edge / file URL",
      "sample": "simulated CB-1001 AC-02/03产物、4类阻断和会话审批；4宽度×5页面；无真实ERP/模型",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "prototypes/s01/evidence/browser-check-before-review-fix.json"
    },
    {
      "kind": "DESIGN_ALIGNMENT",
      "acceptanceIds": [
        "UX-S01-01/AC1",
        "UX-S01-01/AC3",
        "UX-S01-01/AC4"
      ],
      "command": "python docs/ui/check_design.py；作者逐项对照 docs/ui/ALIGNMENT.md 并查看原型截图",
      "environment": "Windows / Python；作者自检，不冒充负责人独立评审",
      "sample": "三份来源、五份冻结基线、85个未知文件指纹、462字设计说明、9组颜色对比",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/ui/design-review-before-review-fix.json"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "UX-S01-01/AC4"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py",
      "environment": "Windows / existing Python；仅文档生成与检查",
      "sample": "19项任务/原17项检查规则；生成状态不手写",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "SIMULATED_FRONTEND",
      "acceptanceIds": [
        "UX-S01-01/AC2",
        "UX-S01-01/AC3",
        "UX-S01-01/AC4"
      ],
      "command": "node prototypes/s01/check.cjs",
      "environment": "Windows / existing Playwright / headless Edge / local file URL；被测提交 4df78d585b73fbffb2066c813a9ef087e5e1466c",
      "sample": "20组检查：原15组增强，新4种阶段跨页失效及SKU隔离/逐日文案；4宽度×5页面20布局组合，另失效审批/暂停任务390px；全simulated",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "prototypes/s01/evidence/browser-check.json"
    },
    {
      "kind": "DESIGN_ALIGNMENT",
      "acceptanceIds": [
        "UX-S01-01/AC1",
        "UX-S01-01/AC3",
        "UX-S01-01/AC4"
      ],
      "command": "python docs/ui/check_design.py；作者查看延期详情、失效审批/暂停任务及390px失效审批截图",
      "environment": "Windows / Python；作者自检，负责人最终验收尚未完成",
      "sample": "5份冻结基线/85既有未知文件不变；462字说明与9组颜色；DESIGN.md/styles/index/fixture未改",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/ui/design-review.json"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "4df78d585b73fbffb2066c813a9ef087e5e1466c",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "本轮明确设计授权，只领取独立产品/视觉原型，不扩大到D-S01-01全部后端专项或A/B/C开发",
      "observedHead": "482e83d4f0af2f64b9eaad1bc0279b76938d6b70"
    },
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "独立原型/视觉/产品规格及真实浏览器证据交付；15组交互与20布局组合通过。负责人尚未签认；不是D-S01-01完整专项/业务验收。",
      "observedHead": "9a7c9a34bd4079fbdb8bef65b80c7dcdea224df4"
    },
    {
      "date": "2026-11-11",
      "to": "IN_PROGRESS",
      "reason": "用户授权小范围原型评审修复：情景/版本/审批失效、跨页来源一致性、模拟任务发布区分、逐日文案及自动化交互回归；保留布局配色fixture，不进入正式前端。",
      "observedHead": "0e4aec39d6e5529278d4f047c75382630667c7be",
      "from": "REVIEW"
    },
    {
      "date": "2026-11-11",
      "to": "REVIEW",
      "reason": "局部评审修复已独立提交；20组浏览器交互/20基础布局及新增失效窄屏检查PASS，源文件指纹匹配被测SHA。冻结口径不改、真实服务NOT_RUN；停止等待负责人最终验收。",
      "observedHead": "4df78d585b73fbffb2066c813a9ef087e5e1466c",
      "from": "IN_PROGRESS"
    }
  ]
}
```

## D-S01-MVP-PLAN S01 MVP实施文档（仅文档）

```json
{
  "id": "D-S01-MVP-PLAN",
  "stage": "D",
  "title": "S01 MVP实施文档与最小底座范围（仅文档）",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "2026-11-11 用户明确授权MVP实施文档，并澄清：本轮不编码/不生成TODO/不调查ERP；下一阶段调查现有YAML后修订方案，核心满足则正式开发优先真实ERP只读",
  "ownerRole": "MVP实施文档集成人；实施/契约/业务评审待负责人",
  "assignee": "Codex（本轮单人文档执行者）",
  "allowedPaths": [
    "docs/agents/S01_MVP实施文档.md",
    "docs/agents/index.md",
    "docs/README.md",
    "docs/TASKS.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/git-whitelist.json",
    "docs/planning/validation-report.json"
  ],
  "parallelCondition": "本轮不并行代理、不并写文件；保留未知未跟踪docs/ERP-openapi.yaml，不读取/修改/暂存",
  "deliverables": [
    "一份可供AI阅读的MVP实施规范：最小公共能力、接入调查决策门禁、契约/数据/实现顺序/原型对接/验收与完整项目演进",
    "不新增开发TODO或未来开发任务台账，不创建业务代码或模拟系统，不改原型或冻结设计"
  ],
  "acceptance": [
    {
      "id": "D-S01-MVP-PLAN/AC1",
      "text": "最小底座子集、必须保留与按需延期边界及模块所有者明确，不等全部公共能力/S02"
    },
    {
      "id": "D-S01-MVP-PLAN/AC2",
      "text": "数据适配可替换；下一阶段先调查YAML再修订，满足核心需求时真实ERP只读优先；模拟仅测试/异常/离线备用"
    },
    {
      "id": "D-S01-MVP-PLAN/AC3",
      "text": "实施顺序/输入输出/契约/失败处理/验收及扩展规则可供AI参考，现有前端直接复用，不新设计"
    },
    {
      "id": "D-S01-MVP-PLAN/AC4",
      "text": "本轮只文档，无业务编码/TODO/ERP调查，不篡改冻结规则、既有任务状态或原型，证据与待决项如实"
    }
  ],
  "plannedTests": [
    "本轮：正文结构/引用链接/权威边界/不生成代码与TODO/保全范围检查；build_docs.py与check_plan.py",
    "后续实施与ERP/模型/业务/独立设计评审本轮NOT_RUN"
  ],
  "risks": [
    "YAML本轮不读取，核心字段与接口能力仍待下一阶段调查；企业规则仍待签认，不以示例补造生产口径"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "f3b7551f8096c07c5e3b3bc3ce8d76d9ab19b34e"
  ],
  "testedCommit": "f3b7551f8096c07c5e3b3bc3ce8d76d9ab19b34e",
  "evidence": [
    {
      "kind": "DESIGN_SELF_CHECK",
      "acceptanceIds": [
        "D-S01-MVP-PLAN/AC1",
        "D-S01-MVP-PLAN/AC2",
        "D-S01-MVP-PLAN/AC3",
        "D-S01-MVP-PLAN/AC4"
      ],
      "command": "作者对照本轮用户澄清及PLAN/概要/AI/S01专项/UI既有规范；PowerShell here-string | python -（正文结构/链接/无TODO/Markdown解析检查）",
      "environment": "Windows / Python markdown；仅文档作者自检，不代替负责人独立评审",
      "sample": "16章/27表/13处相对链接无断链；明确下一阶段先调查YAML再修订、满足核心需求则正式开发优先ERP；适配器可替换，模拟仅测试/异常/离线备用；最小底座/阶段出口/原型数据对接/验收与扩展齐全；无开发任务清单或代码块；主文档SHA256=aeb150234dc4a0deae1a286d2a6c1a58e2d5c879e0318d357e8a823e6194b2ee",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_MVP实施文档.md"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-MVP-PLAN/AC4"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / existing Python/Git；文档和台账验证",
      "sample": "新增仅1项design文档工作，既有19项任务保持不变；20项台账、18项既有文档规则PASS；不创建业务代码/完整模拟系统/开发TODO，不读取ERP YAML",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "D-S01-MVP-PLAN/AC4"
      ],
      "command": "PowerShell here-string | python -B -（Git对象对照、既有任务JSON、指定文件保全、边界/秘密启发式检查）",
      "environment": "Windows / 本地Python/Git；不读取docs/ERP-openapi.yaml",
      "sample": "原S01详设/HTML/文档构建器、五份冻结基线、PLAN/DECISIONS、视觉/UI/原型等18文件相对基点字节不变；无应用初始化；未知未跟踪YAML保持原样不暂存。定向秘密模式0发现，检查仅覆盖本轮获准文档",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    },
    {
      "kind": "DESIGN_REVIEW",
      "acceptanceIds": [
        "D-S01-MVP-PLAN/AC1",
        "D-S01-MVP-PLAN/AC2",
        "D-S01-MVP-PLAN/AC3",
        "D-S01-MVP-PLAN/AC4"
      ],
      "command": "NOT_RUN：负责人独立实施文档评审；下一阶段ERP调查与方案修订尚未开始",
      "environment": "无独立评审/ERP调用/业务实现环境",
      "sample": "v0.1实施建议；非生产冻结规格，真实ERP/模型/工程/业务/MC验收全部NOT_RUN",
      "exitCode": null,
      "result": "NOT_RUN",
      "artifactRef": "docs/agents/S01_MVP实施文档.md"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "f3b7551f8096c07c5e3b3bc3ce8d76d9ab19b34e",
  "dirtyPaths": [
    "docs/ERP-openapi.yaml"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "用户授权实施文档，并明确真实ERP优先条件/接口调查顺序/可替换适配层；仅领取文档，不生成开发TODO或执行后续阶段",
      "observedHead": "3a470082052efcd29a61d238d61eb902c6ac85d5"
    },
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "MVP实施文档与必要导航已本地提交；文档结构/链接/保全及18项文档检查PASS。用户澄清的调查后ERP优先、可替换适配层、模拟备用与复用前端均写明；未生成开发TODO/业务代码/模拟系统、未读取或调查ERP。停止等负责人评审与下一阶段指令。",
      "observedHead": "f3b7551f8096c07c5e3b3bc3ce8d76d9ab19b34e"
    }
  ]
}
```

## D-S01-ERP-01 教学ERP调查与MVP方案修订（仅文档/获准只读）

```json
{
  "id": "D-S01-ERP-01",
  "stage": "D",
  "title": "S01 A01必做范围修订、教学ERP调查与MVP方案更新",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "2026-11-11 用户明确授权静态ERP调查、环境允许下最小安全只读验证、原实施文档修订、本地独立提交及普通远端同步；不编码、不生成TODO、不启动下一阶段",
  "ownerRole": "本轮文档/接口调查集成人；业务与设计评审由负责人待签认",
  "assignee": "Codex（单人执行，不使用代理）",
  "allowedPaths": [
    "docs/agents/S01_MVP实施文档.md",
    "docs/agents/S01_ERP接口调查与字段映射.md",
    "docs/agents/evidence/s01-erp-survey-20261111.json",
    "docs/DECISIONS.md",
    "docs/README.md",
    "docs/agents/index.md",
    "docs/TASKS.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/git-whitelist.json",
    "docs/planning/validation-report.json",
    "docs/governance/PUBLICATION.md"
  ],
  "parallelCondition": "本轮单一执行者；原型/冻结基线/S01专项正文只读；本地YAML原字节保留，凭据不入文件或日志",
  "deliverables": [
    "可追溯的ERP接口/字段/缺口调查报告及无敏感响应证据；区分静态声明与本轮真实观察",
    "更新同一路径MVP实施文档：A01真实解释必做、失败仍可发布受限规则报告、结构输出/预算/日志/版本/验收/详情对接",
    "必要ADR/索引/台账与交接、本地提交和经增量安全/身份/祖先检查后的普通远端同步"
  ],
  "acceptance": [
    {
      "id": "D-S01-ERP-01/AC1",
      "text": "A01真实实现/真实LLM调用及展示为MVP验收必做；沿用既有网关，不将模型成功设为规则报告发布必要条件"
    },
    {
      "id": "D-S01-ERP-01/AC2",
      "text": "相关ERP方法/路径/参数/字段/鉴权/分页/错误/业务含义及缺口可追溯，真实调用事实与文档声明区分，零值不补未知"
    },
    {
      "id": "D-S01-ERP-01/AC3",
      "text": "主数据路径/受控补充/D01-D03/B01-B02/原型对接/待决项落实，教学模拟ERP不冒充官方或生产验证"
    },
    {
      "id": "D-S01-ERP-01/AC4",
      "text": "只读/无业务代码或TODO/无凭据敏感响应入库/原型基线保全、检查/提交/远端结果真实记录"
    }
  ],
  "plannedTests": [
    "本轮：OpenAPI静态结构/Refs/操作和字段映射一致性、最小HTTPS只读探测、文档/保全/秘密启发式、build_docs/check_plan、Git普通push前后核验",
    "已按负责人明确HTTPS verify=False调查例外完成有界只读鉴权/字段观察；正式证书策略及完整覆盖仍待确认。所有业务写接口禁止调用；真实LLM与业务实现验收本轮NOT_RUN"
  ],
  "risks": [
    "自签名TLS：正常校验失败及HTTP四次404保留，负责人后续明确授权本轮verify=False例外；正式接入证书策略仍待确认，不能默认关闭校验",
    "店仓SKU映射、完整需求窗口、逐SKU未收/可售日、订购倍数和成熟质量口径仍有缺口；REST销售订单真实503未掩盖，未知不补0",
    "本地OpenAPI为独立教学模拟系统而非官方/生产ERP；本轮只同步已检查自有文档增量，不宣布旧第三方许可缺口闭合"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "3db663c084d749600c526abffa5b8e322f582b2b"
  ],
  "testedCommit": "3db663c084d749600c526abffa5b8e322f582b2b",
  "evidence": [
    {
      "kind": "DESIGN_SELF_CHECK",
      "acceptanceIds": [
        "D-S01-ERP-01/AC1",
        "D-S01-ERP-01/AC2",
        "D-S01-ERP-01/AC3",
        "D-S01-ERP-01/AC4"
      ],
      "command": "作者对照本轮要求/既有概要与AI契约；PowerShell here-string | python -（OpenAPI一致性/字段观察计数/链接/表格/边界校验）",
      "environment": "Windows / Python yaml、markdown；仅文档与调查作者自检",
      "sample": "24静态操作与原始YAML一致；135本地链接无断链；A01必做、四类结构、真实调用及展示验收、错误降级写入v0.2；不重建模型网关，不以模型成功为规则报告发布条件",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_MVP实施文档.md"
    },
    {
      "kind": "ERP_BOUNDED_READ_OBSERVATION",
      "acceptanceIds": [
        "D-S01-ERP-01/AC2"
      ],
      "command": "临时无凭据探测工具：health/auth + GET查询及3类文档确认只读的兼容POST查询；返回仅保留类型/空值/计数",
      "environment": "真实网络读取教学模拟ERP v5.1.0；用户明确本轮HTTPS verify=False例外；每次业务limit/length=1",
      "sample": "6入口/健康探测，2次认证，20次业务查询；16不同查询操作尝试，15返回200，10非空。0业务写入、0敏感原值保存；同一店仓SKU关系/完整覆盖未证，不等于ERP业务验收通过",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/evidence/s01-erp-survey-20261111.json"
    },
    {
      "kind": "ERP_SALES_REST_OBSERVATION",
      "acceptanceIds": [
        "D-S01-ERP-01/AC2"
      ],
      "command": "GET /api/v1/sales-orders，限定选定店/仓且limit=1",
      "environment": "教学ERP / R2-V08",
      "sample": "实际HTTP503，未伪造成功、未静默切换模拟；兼容订单另行读取的日期/覆盖仍不完整",
      "exitCode": null,
      "result": "FAIL",
      "artifactRef": "docs/agents/evidence/s01-erp-survey-20261111.json"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-ERP-01/AC4"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / 项目既有文档工具",
      "sample": "21项台账、18项文档规则PASS；既有20项任务JSON保持不变，仅新增本轮design记录；独立评审未运行",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "D-S01-ERP-01/AC4"
      ],
      "command": "PowerShell here-string | python -（Git对象/任务JSON/应用入口/秘密启发式/原文哈希检查）",
      "environment": "main / 基点8f79f4b56689d04fb4b0de7560b05f60b86278c5",
      "sample": "17份原专项/HTML/构建器/冻结基线/PLAN/AGENTS/视觉/UI/原型字节不变；无正式业务代码/应用初始化/开发TODO。YAML哈希不变，保留未跟踪；定向秘密模式0发现",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    },
    {
      "kind": "REMOTE_SYNC",
      "acceptanceIds": [
        "D-S01-ERP-01/AC4"
      ],
      "command": "git ls-remote origin refs/heads/main；git merge-base --is-ancestor；增量历史扫描；git push origin HEAD:refs/heads/main；再次ls-remote",
      "environment": "Git Credential Manager和连接器同一yujie-213账号；既有Public origin，无force/新仓库/API重建",
      "sample": "推送前远端895167c7c1b76db2e46209fa4480e4819e65a06f为祖先；7个待同步提交/38个变更提交blob定向秘密扫描0发现、无新增第三方runtime。普通push退出0，远端已实测为3db663c084d749600c526abffa5b8e322f582b2b；本证据/交接收尾提交随后普通同步并最终查询，不填写自身SHA",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/governance/PUBLICATION.md"
    },
    {
      "kind": "DESIGN_REVIEW",
      "acceptanceIds": [
        "D-S01-ERP-01/AC1",
        "D-S01-ERP-01/AC2",
        "D-S01-ERP-01/AC3",
        "D-S01-ERP-01/AC4"
      ],
      "command": "NOT_RUN：负责人独立设计评审、完整ERP业务覆盖及真实LLM/工程/S01/MC验收",
      "environment": "仅调查与文档；无正式软件实现",
      "sample": "REVIEW而非ACCEPTED；店仓映射、时间/逐SKU供给/可售日/倍数/质量补充、TLS正式策略、模型Provider与数据许可/预算等待确认；停止等待负责人评审",
      "exitCode": null,
      "result": "NOT_RUN",
      "artifactRef": "docs/agents/S01_ERP接口调查与字段映射.md"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "3db663c084d749600c526abffa5b8e322f582b2b",
  "dirtyPaths": [
    "docs/ERP-openapi.yaml"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "按最新任务领取调查与文档范围；A01成为MVP必做；ERP认证与TLS信任按安全条件使用，未知YAML原文只读、不默认发布",
      "observedHead": "8f79f4b56689d04fb4b0de7560b05f60b86278c5"
    },
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "静态调查/获准有界真实只读和v0.2方案修订已提交、自检通过并普通同步；REST销售503、核心数据覆盖缺口及未运行的真实LLM/业务验收如实保留。仅文档工作交付待评审，不自动编码。",
      "observedHead": "3db663c084d749600c526abffa5b8e322f582b2b"
    }
  ]
}
```

## D-S01-ENTRY-01 单SKU最小开发准入核对（仅文档）

```json
{
  "id": "D-S01-ENTRY-01",
  "stage": "D",
  "title": "单SKU最小开发准入核对与决策建议（仅文档）",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "负责人本轮明确要求基于42a9417及既有S01设计/实施/ERP证据核对单SKU准入；直接复用D-S01-ERP-01证据，不要求其已独立验收，不新增接口验证/开发TODO/业务代码",
  "ownerRole": "本轮文档核对执行者；身份、数据、规则与质量决定由负责人评审",
  "assignee": "Codex（单人文档执行）",
  "allowedPaths": [
    "docs/agents/S01_单SKU开发准入核对.md",
    "docs/README.md",
    "docs/agents/index.md",
    "docs/planning/git-whitelist.json",
    "docs/TASKS.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/validation-report.json"
  ],
  "parallelCondition": "单人串行；原MVP/调查报告/JSON/专项与原型均只读；未跟踪ERP YAML原样保留，不读取凭据",
  "deliverables": [
    "一份简洁单SKU八域准入表：来源/旧实测/缺口/推荐处理/结果限制",
    "三项最少负责人决定与建议；不假定身份/企业规则，不把既有字段类型当成现存输入数据集",
    "必要导航/白名单/状态与交接、真实文档检查及Git提交；完成停止等评审"
  ],
  "acceptance": [
    {
      "id": "D-S01-ENTRY-01/AC1",
      "text": "八域逐项可追溯，明确原样本别名与未绑定身份，不补未知为0、不推断完整覆盖"
    },
    {
      "id": "D-S01-ENTRY-01/AC2",
      "text": "决定收敛并列推荐方案及MVP结果影响，区分供需/采购适用性/真实AI和完整验收"
    },
    {
      "id": "D-S01-ENTRY-01/AC3",
      "text": "不新调用ERP/认证/模型、不扩大探测、不改原型或业务代码/原设计，无开发TODO；必要检查/提交/交接真实"
    }
  ],
  "plannedTests": [
    "PowerShell here-string | python -：八域/三项决定、证据id与字段类型对照、Markdown表格/相对链接、基点保全/台账保全/秘密启发式",
    "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
    "本轮ERP/认证/模型调用和业务测试NOT_RUN，独立准入评审NOT_RUN；现有实测仅引用，不重放"
  ],
  "risks": [
    "原始身份/数量未保存，SKU-A只是既有样本别名；不能用旧证据直接计算或冒称八域已就绪",
    "负责人尚未签认试点映射、补充数据/计算策略和质量策略；本文推荐不是冻结规则或开发授权"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "6759de4f58a19dafa98af8b4a1f6abc87970572b"
  ],
  "testedCommit": "6759de4f58a19dafa98af8b4a1f6abc87970572b",
  "evidence": [
    {
      "kind": "DESIGN_SELF_CHECK",
      "acceptanceIds": [
        "D-S01-ENTRY-01/AC1",
        "D-S01-ENTRY-01/AC2",
        "D-S01-ENTRY-01/AC3"
      ],
      "command": "PowerShell here-string | python -（Markdown HTMLParser、旧证据id/字段类型、原任务JSON、链接与边界核对）",
      "environment": "Windows / 既有Python markdown/Git；基于42a9417的文档核对，非真实软件或业务验收",
      "sample": "核对表8项数据/3项决定/4层结果表均正确解析；17个旧实测id存在且关键类型/空值/503相符；123本轮所涉及MD本地链接无断链。主文档SHA256=62c6561e733d4994da3a48ee31721d88d2fdcf4d8023fba1693bd15ef9f0ff1d；负责人未签认，准入缺口不宣告关闭",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/agents/S01_单SKU开发准入核对.md"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-ENTRY-01/AC1",
        "D-S01-ENTRY-01/AC2",
        "D-S01-ENTRY-01/AC3"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / 既有Python markdown/Git；基于42a9417的文档核对，非真实软件或业务验收",
      "sample": "22项台账、18项文档规则PASS；仅新增design核对记录，原21项任务JSON保持不变，无正式开发TODO",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "D-S01-ENTRY-01/AC1",
        "D-S01-ENTRY-01/AC2",
        "D-S01-ENTRY-01/AC3"
      ],
      "command": "git diff 42a9417 --name-only；Git对象逐字节/未知文件哈希/秘密启发式检查",
      "environment": "Windows / 既有Python markdown/Git；基于42a9417的文档核对，非真实软件或业务验收",
      "sample": "四份文档/索引/白名单固定于真实提交；其他业务/原型/冻结文件与原MVP/专项/ERP报告/JSON未改。原始YAML未跟踪且哈希仍匹配历史证据，未暂存；定向秘密启发式0发现，无业务入口初始化。新ERP/认证/模型请求均0，不重放旧授权",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    },
    {
      "kind": "DESIGN_REVIEW",
      "acceptanceIds": [
        "D-S01-ENTRY-01/AC1",
        "D-S01-ENTRY-01/AC2",
        "D-S01-ENTRY-01/AC3"
      ],
      "command": "NOT_RUN：负责人单SKU准入/身份/补充数据与规则/质量策略评审；真实ERP/LLM/软件验收",
      "environment": "Windows / 既有Python markdown/Git；基于42a9417的文档核对，非真实软件或业务验收",
      "sample": "SKU-A仅旧样本别名，原始值未保存；当前尚不具备可采购候选业务准入。三项建议均待决定，不能以本文替代授权、数据或规则冻结",
      "exitCode": null,
      "result": "NOT_RUN",
      "artifactRef": "docs/agents/S01_单SKU开发准入核对.md"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "6759de4f58a19dafa98af8b4a1f6abc87970572b",
  "dirtyPaths": [
    "docs/ERP-openapi.yaml"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "领取单SKU文档核对；只复用旧证据，无新ERP调用或开发授权",
      "observedHead": "42a941790b4611c391ee1b8f659d3d969ef8b856"
    },
    {
      "date": "2026-11-11",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "单SKU准入表已独立提交，8域/3决定及引用保全自检与18项文档规则通过；不新调用ERP/模型、不编码、不生成开发TODO，停止等负责人评审。",
      "observedHead": "6759de4f58a19dafa98af8b4a1f6abc87970572b"
    }
  ]
}
```

## D-S01-DATA-01 单SKU身份恢复与受控数据准入

```json
{
  "id": "D-S01-DATA-01",
  "stage": "D",
  "title": "单SKU身份恢复与受控数据准入",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。可先整理受控登记，不新联网；新增只读验证须ERP安全门及单独明确授权。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "docs/evidence/D-S01-DATA-01/（未来脱敏索引）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "原SKU-A受控身份恢复记录；失败则提出且由负责人批准的唯一替代样本方案及新映射版本",
    "该单SKU八域输入/来源/覆盖/有效期/责任/证据登记，明确可算、缺失或情景；敏感值仅留受控位置"
  ],
  "acceptance": [
    {
      "id": "D-S01-DATA-01/AC1",
      "text": "先核对获准本地受控记录，不从原JSON类型猜实际值；换样本须负责人确认且不得称恢复原绑定"
    },
    {
      "id": "D-S01-DATA-01/AC2",
      "text": "基线所需身份/库存/历史/逐行供给与日期等有范围匹配证据，缺项明确阻断；无供给/无销量需完整性证明，质量不足保留采购限制"
    },
    {
      "id": "D-S01-DATA-01/AC3",
      "text": "真实读取、受控事实、模拟情景按三轴分开，文件获授权且有版本/负责人/时点；不把历史16接口观察当完整数据集"
    }
  ],
  "plannedTests": [
    "受控身份/单位/店仓关系/覆盖/逐行未收/日期/MOQ/倍数/质量证据逐项人工核对，当前NOT_RUN"
  ],
  "completionEvidence": [
    "受控包定位/版本/指纹、逐域准入/缺口矩阵与负责人签认；不得保存敏感行值或伪造完整性。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "BUSINESS_REVIEW"
  ],
  "status": "BLOCKED",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": {
    "reason": "原身份与数值未留存；当前八域未完整绑定/补证",
    "responsibleRole": "负责人指定的数据/采购/仓库/质量核对人",
    "releaseCondition": "恢复或批准唯一替代身份，明确本轮实际可用输入及缺失的结果边界，并签认受控包"
  },
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "BLOCKED",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-MAP01",
    "S01-AC-DATA01",
    "S01-AC-REAL01"
  ]
}
```

## D-S01-RULE-01 单SKU供需/候选与质量规则签认

```json
{
  "id": "D-S01-RULE-01",
  "stage": "D",
  "title": "单SKU供需/候选与质量规则签认",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。可与身份恢复及A-01契约准备并行，不要求先完成数据采集。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "docs/contracts/s01/（未来）",
    "docs/evidence/D-S01-RULE-01/（未来）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "当前MetricDefinition/需求情景、库存/供给/日期/MOQ/倍数/比较策略及固定期望的最小规则版本",
    "required质量/有效期/成熟群组/调查条件与局部/规则/阻断矩阵；不要求全S03"
  ],
  "acceptance": [
    {
      "id": "D-S01-RULE-01/AC1",
      "text": "不预设需求窗口/预测/阈值/同日顺序/缓冲端点或单位，逐项有业务依据与责任签认"
    },
    {
      "id": "D-S01-RULE-01/AC2",
      "text": "净额或互斥分桶、预留需求关系、未收状态/去重/过期日期、候选硬约束适用范围明确；不能复制UI演示成企业规则"
    },
    {
      "id": "D-S01-RULE-01/AC3",
      "text": "质量不足仍阻断采购适用性；质量12%示例不是通用阈值，模拟规则独立标记；固定期望可复核"
    }
  ],
  "plannedTests": [
    "负责人/业务核对人审规则与来源；净额/日期边界/约束/缺质量/调查/无解的纸面例子复核，当前NOT_RUN"
  ],
  "completionEvidence": [
    "规则/期望样例版本、范围/生效条件、来源与实际签认；未确定值不交开发者猜。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "BUSINESS_REVIEW",
    "DESIGN_REVIEW"
  ],
  "status": "BLOCKED",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": {
    "reason": "原则已确认，但计算/日期/约束/质量具体口径尚未签认",
    "responsibleRole": "负责人指定采购/运营/质量与B01/B02契约评审者",
    "releaseCondition": "当前最小规则和固定期望、质量/降级矩阵获得相应岗位签认"
  },
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "BLOCKED",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-CALC01",
    "S01-AC-DATE01",
    "S01-AC-QUALITY01",
    "S01-AC-CAND01"
  ]
}
```

## D-S01-ERP-ACCESS-01 教学ERP真实只读启用与安全条件确认

```json
{
  "id": "D-S01-ERP-ACCESS-01",
  "stage": "D",
  "title": "教学ERP真实只读启用与安全条件确认",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。历史只读证据直接复用，不为计划重放认证。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "docs/evidence/D-S01-ERP-ACCESS-01/（未来脱敏索引）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "指定HTTPS端点/可信CA或经确认受控证书策略、只读账户及本地安全配置引用",
    "限定一个店/仓/SKU、接口/参数/分页/时间窗/调用上限和出站目标的明确只读授权；与受控补充来源许可分开"
  ],
  "acceptance": [
    {
      "id": "D-S01-ERP-ACCESS-01/AC1",
      "text": "认证信息不硬编码/提交Git；URL不带Token，无自动重定向至非授权地址；不将历史verify=False当正式默认"
    },
    {
      "id": "D-S01-ERP-ACCESS-01/AC2",
      "text": "需要新认证/关闭TLS校验或接口验证时单独获授权；只允许已确认无业务副作用的查询，草稿/写入/审批/执行均关闭"
    },
    {
      "id": "D-S01-ERP-ACCESS-01/AC3",
      "text": "失败/认证错误/503/覆盖不足显式报错，不静默切fixture；范围不齐不扩大扫描找成功样本"
    }
  ],
  "plannedTests": [
    "安全配置/白名单/最小读取方案评审；本任务本轮不新登录或探测，未来实测在D-S01-LIVE-01记录"
  ],
  "completionEvidence": [
    "签认的传输/凭据注入/范围/调用许可与脱敏配置检查，秘密保留本地受控位置。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "DESIGN_REVIEW"
  ],
  "status": "BLOCKED",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": {
    "reason": "正式证书策略/安全凭据配置和下一阶段新读取授权未提供",
    "responsibleRole": "负责人及其指定ERP/安全管理员",
    "releaseCondition": "正式受控传输、凭据引用及单SKU只读调用范围获得明确授权"
  },
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "BLOCKED",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-SEC01",
    "S01-AC-READONLY01",
    "S01-AC-REAL01"
  ]
}
```

## D-S01-AI-ACCESS-01 A01真实Provider/模型用途启用条件确认

```json
{
  "id": "D-S01-AI-ACCESS-01",
  "stage": "D",
  "title": "A01真实Provider/模型用途启用条件确认",
  "kind": "design",
  "dependsOn": [
    "A-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。A-01用途契约后确认，不以全AI平台/A02/A03为前置。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "docs/contracts/s01/（未来）",
    "docs/evidence/D-S01-AI-ACCESS-01/（未来脱敏索引）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "一个获准Provider/deployment与实际模型/版本获取方式、本地密钥配置引用、数据许可/地域/保留策略",
    "S01 Prompt/Context/Schema/参数/计价版本、输入字段白名单、任务期限/额度/重试和用途评测判定规则"
  ],
  "acceptance": [
    {
      "id": "D-S01-AI-ACCESS-01/AC1",
      "text": "A01必做已确定，不重问是否要AI；不签无限额度，不虚构费用或模型能力"
    },
    {
      "id": "D-S01-AI-ACCESS-01/AC2",
      "text": "评测/业务发送范围与许可明确，受控事实和模拟样例分类；注入/敏感/错数错引用等硬失败和金标准有签认"
    },
    {
      "id": "D-S01-AI-ACCESS-01/AC3",
      "text": "原task allowance/unknown usage及超时限制具备；正式用途启用须C-04合格，受限评测可以先在获准范围运行"
    }
  ],
  "plannedTests": [
    "配置/数据许可/预算/Prompt与Schema/金标准人工评审；本轮模型调用NOT_RUN"
  ],
  "completionEvidence": [
    "Provider/用途/输入许可、预算/计价/版本/判定标准及评审引用；密钥不入文档。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "DESIGN_REVIEW"
  ],
  "status": "BLOCKED",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": {
    "reason": "实际Provider/密钥配置、模型数据许可/额度/用途评测规则尚未签认",
    "responsibleRole": "负责人指定模型用途/数据安全/预算负责人",
    "releaseCondition": "签认当前Provider和有界真实评测/业务调用许可及配置，保持正式启用与评测区分"
  },
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "BLOCKED",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-AI01",
    "S01-AC-AI04",
    "S01-AC-AI05"
  ]
}
```

## D-S01-LIVE-01 单SKU教学ERP真实读取与受控补充闭环验收

```json
{
  "id": "D-S01-LIVE-01",
  "stage": "D",
  "title": "单SKU教学ERP真实读取与受控补充闭环验收",
  "kind": "validation",
  "dependsOn": [
    "B-01",
    "B-02",
    "D-S01-DATA-01",
    "D-S01-RULE-01",
    "D-S01-ERP-ACCESS-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。依赖和安全/数据门满足且本次只读验证另获授权后运行，不扩大原范围。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/D-S01-LIVE-01/（未来）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "真实单SKU窄读取→受控补充→D01批次→D02投影→D03质量/manifest→D04引用的实际证据",
    "OpenAPI声明/原调查观察/本次返回与字段语义、类型、过滤/分页/覆盖/时点/实际限制对照；旧503和缺口不抹除"
  ],
  "acceptance": [
    {
      "id": "D-S01-LIVE-01/AC1",
      "text": "新调用严格按本任务单独获准范围；只读且敏感响应不入Git，未知不补0、字段类型不当业务语义"
    },
    {
      "id": "D-S01-LIVE-01/AC2",
      "text": "正常/部分/失败批次、来源三轴、映射/去重与固定manifest可核对；真实读取不能由受控文件或Mock替代证明"
    },
    {
      "id": "D-S01-LIVE-01/AC3",
      "text": "当前缺项及质量限制进入报告输入；未补齐不能冒称真实业务核心数据覆盖通过"
    }
  ],
  "plannedTests": [
    "有界真实读取与受控文件/投影检查；失败/覆盖不足可用测试装配验证并分类，不能人为业务写入造场景"
  ],
  "completionEvidence": [
    "实际端点/参数名称/数量/字段类型/限制、授权范围引用、批次/映射/manifest与脱敏证据；无认证/敏感值。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "REAL_ERP_READ",
    "BUSINESS_REVIEW",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "TODO",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-REAL01",
    "S01-AC-DATA01",
    "S01-AC-MAP01",
    "S01-AC-SOURCE01"
  ]
}
```

## D-S01-DEV-01 S01 Workflow与规则报告/AI解释语义接入

```json
{
  "id": "D-S01-DEV-01",
  "stage": "D",
  "title": "S01 Workflow与规则报告/AI解释语义接入",
  "kind": "development",
  "dependsOn": [
    "B-05",
    "B-04",
    "C-01"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。公共实现依赖满足后可用显式工程样例集成；真实数据运行须D-S01-LIVE-01，真实模型评测须AI安全门/正式启用须C-04。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s01_supply_inventory/",
    "src/commerce_hub/workspace/",
    "tests/integration/s01/（未来）",
    "docs/evidence/D-S01-DEV-01/（未来）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "scenarios/s01_supply_inventory真正Handler：固定输入/质量门禁→B01基线→B02候选/B01评价→经A01解释或降级→DomainResult",
    "建议原因/关键依据/主要风险/人工确认事项四类Context/结构解释与supportRefs领域校验；B01/B02权威量/日期/质量不变",
    "沿O01受理/查询/取消/报告/options/D04证据读口形成当前最小API；固定Workflow顺序/重入/版本绑定与新分析关联旧报告"
  ],
  "acceptance": [
    {
      "id": "D-S01-DEV-01/AC1",
      "text": "实际注册S01 Handler且不复制调度/预算/计算；未具备输入/规则只给相应阻断，无假report或成功占位"
    },
    {
      "id": "D-S01-DEV-01/AC2",
      "text": "A01只读已计算产物与合法证据；结构通过仍需S01引用/事实保持门禁，错数/错日期/错约束/质量/审批丢弃解释"
    },
    {
      "id": "D-S01-DEV-01/AC3",
      "text": "模型失败明确AI解释不可用，合法规则仍可发布；required质量不足/调查不被AI解除，迟到取消/失lease/旧plan不发布"
    },
    {
      "id": "D-S01-DEV-01/AC4",
      "text": "不开放业务C01/C02/C03真实确认/审批/执行；单SKU SINGLE、有界参数/候选和任务预算，跨模块只用公开契约"
    }
  ],
  "plannedTests": [
    "S01-AC-DATA/MAP/CALC/CONSTRAINT/QUALITY/REPORT/AI相关集成与故障回归；场景用Mock与真实调用分开，真实模型验收归C-04"
  ],
  "completionEvidence": [
    "当前实现commit、Handler/API契约与跨模块Refs/版本、阻断/降级/重入/迟到负例；D-S01-LIVE-01与C-04分别提供真实源/模型事实。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [
    "D-S01-LIVE-01",
    "D-S01-AI-ACCESS-01",
    "C-04"
  ],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "TODO",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-CALC01",
    "S01-AC-DATE01",
    "S01-AC-CAND01",
    "S01-AC-QUALITY01",
    "S01-AC-REPORT01",
    "S01-AC-READONLY01",
    "S01-AC-AI01",
    "S01-AC-AI02",
    "S01-AC-AI03",
    "S01-AC-AI04",
    "S01-AC-AI05"
  ]
}
```

## D-S01-UI-01 沿用S01原型的真实API/AI详情对接

```json
{
  "id": "D-S01-UI-01",
  "stage": "D",
  "title": "沿用S01原型的真实API/AI详情对接",
  "kind": "development",
  "dependsOn": [
    "D-S01-DEV-01",
    "A-04"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。可以先用已实现API和显式工程测试数据接入；实际单SKU数据展示须D-S01-LIVE-01，真实AI成功展示须C-04获准结果。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/workspace/",
    "tests/browser/s01/（未来）",
    "docs/evidence/D-S01-UI-01/（未来）"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "正式workspace中复用工作台/列表/详情/证据/空态和DESIGN视觉；最少API适配/真实任务轮询/取消与刷新重读",
    "本次报告Ref/基线候选/逐日图表/来源/限制/版本、四类AI解释/依据/独立状态展示；原离线原型保留参照"
  ],
  "acceptance": [
    {
      "id": "D-S01-UI-01/AC1",
      "text": "不另画页面、不改离线原型；前端只格式化/绘图不重算数量/日期，不以角色下拉框授予权限"
    },
    {
      "id": "D-S01-UI-01/AC2",
      "text": "实际API失败/不存在显示错误或空态，不能回落第一个模拟SKU或历史固定报告；新分析/版本关联正确"
    },
    {
      "id": "D-S01-UI-01/AC3",
      "text": "非成功AI明确AI解释不可用，质量阻断独立；真实确认/审批/执行入口禁用，不接假成功"
    },
    {
      "id": "D-S01-UI-01/AC4",
      "text": "同源身份/权限和真实API证据可复查；Mock界面/原型交互不替代真实前后端验收"
    }
  ],
  "plannedTests": [
    "S01-AC-UI01及AI01/02、SEC01：实际API浏览器操作/刷新/失败/阻断/证据撤权；既有适用窄屏/深浅布局回归"
  ],
  "completionEvidence": [
    "实际API网络/报告Ref、浏览器日志/截图及布局/权限/AI状态结果；真实AI展示的Provider证据引用C-04，不用静态文案。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [
    "D-S01-LIVE-01",
    "C-04"
  ],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "BROWSER_API",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "TODO",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-UI01",
    "S01-AC-REPORT01",
    "S01-AC-SEC01",
    "S01-AC-AI01",
    "S01-AC-AI02"
  ]
}
```

## D-S01-ACCEPT-01 单SKU S01 MVP端到端复现与负责人验收

```json
{
  "id": "D-S01-ACCEPT-01",
  "stage": "D",
  "title": "单SKU S01 MVP端到端复现与负责人验收",
  "kind": "validation",
  "dependsOn": [
    "A-06",
    "D-S01-LIVE-01",
    "D-S01-DEV-01",
    "D-S01-UI-01",
    "C-04"
  ],
  "entryCondition": "本轮仅规划，以下开发/调用均未授权执行；待负责人和星星评审计划并另发开发指令后，按依赖/相应启用条件领取。所有依赖及对应范围准入完成后执行；业务缺口仍存在则按实际结果保留受限状态或未通过项，不自动降低验收要求。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/D-S01-ACCEPT-01/（未来）",
    "docs/TASKS.md",
    "docs/HANDOFF.md"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "干净环境/真实MySQL/API+Worker/单SKU真实教学读取+获准补充/B01-B02/A01/既有页面的端到端复现包",
    "MVP§11全部适用S01-AC逐项映射、真实/受控/模拟分类、缺口/限制与失败清单；负责人和星星开发任务评审之后的实际交付评审引用"
  ],
  "acceptance": [
    {
      "id": "D-S01-ACCEPT-01/AC1",
      "text": "真实LLM有效调用及现有详情展示、错误降级均有证据；源数据限制/质量不足不被模型或界面掩盖"
    },
    {
      "id": "D-S01-ACCEPT-01/AC2",
      "text": "库存/需求/供给/日期/约束按当前签认规则评价；当前质量不够只能展示可信供需并阻断采购适用性；不能以一份阻断报告代替未完成核心业务/候选正向或真实模型验收"
    },
    {
      "id": "D-S01-ACCEPT-01/AC3",
      "text": "取消/重启/重复投递/旧版本/撤权/预算/错误与三轴来源可复现；模拟候选正向不标该真实SKU可采购；无法验证项如实NOT_RUN/FAIL及限定验收范围"
    },
    {
      "id": "D-S01-ACCEPT-01/AC4",
      "text": "完成需实现提交/适用测试/逐项证据和负责人指定实际评审签认，未签认维持REVIEW；不宣称旧S02 MC/生产ERP/真实采购通过"
    }
  ],
  "plannedTests": [
    "执行A-01冻结的S01自有集成/真实读取/真实模型/浏览器/故障命令；按MVP§11逐项复现，当前全部NOT_RUN"
  ],
  "completionEvidence": [
    "实际制品/迁移/配置引用/输入与规则版本/命令环境/原始脱敏结果、S01-AC覆盖矩阵及实际验收签认；不能用规划文档验收软件。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "REAL_ERP_READ",
    "MODEL_EVAL",
    "BROWSER_API",
    "BUSINESS_REVIEW",
    "SECURITY"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "branch": null,
  "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3",
  "dirtyPaths": [],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "TODO",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    }
  ],
  "acceptanceRefs": [
    "S01-AC-DATA01",
    "S01-AC-MAP01",
    "S01-AC-CALC01",
    "S01-AC-DATE01",
    "S01-AC-QUALITY01",
    "S01-AC-CAND01",
    "S01-AC-SOURCE01",
    "S01-AC-REAL01",
    "S01-AC-ENG01",
    "S01-AC-TX01",
    "S01-AC-REC01",
    "S01-AC-CONC01",
    "S01-AC-SEC01",
    "S01-AC-CANCEL01",
    "S01-AC-REPORT01",
    "S01-AC-UI01",
    "S01-AC-READONLY01",
    "S01-AC-AI01",
    "S01-AC-AI02",
    "S01-AC-AI03",
    "S01-AC-AI04",
    "S01-AC-AI05"
  ]
}
```

## D-S01-MVP-TODO S01 MVP分阶段开发任务规划（本轮仅文档）

```json
{
  "id": "D-S01-MVP-TODO",
  "stage": "D",
  "title": "S01 MVP分阶段开发任务规划（本轮仅文档）",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "负责人本轮已明确授权制定S01 MVP分阶段开发计划、文档检查、提交和同步；只规划不编码，完成后交负责人和星星评审，再另行授权Codex正式开发。",
  "ownerRole": "由负责人指定实际责任人；负责人/星星评审当前计划，具体业务/安全/契约签认按岗位授权",
  "assignee": "Codex（本轮唯一文档规划执行者）",
  "allowedPaths": [
    "docs/TASKS.md",
    "docs/DECISIONS.md",
    "docs/README.md",
    "docs/HANDOFF.md",
    "docs/generated/",
    "docs/planning/validation-report.json"
  ],
  "parallelCondition": "只有获得实施授权、契约稳定且实际文件不相交时可并行；公共契约/迁移/组合根/锁文件/台账单一集成人协调",
  "deliverables": [
    "细化既有A/B/C当前任务，补齐最小S01实施/验收和准入任务；唯一台账不复制",
    "负责人原则确认ADR、阶段/依赖/启用条件/证据/评审边界与交接、文档检查/本地提交/普通GitHub同步"
  ],
  "acceptance": [
    {
      "id": "D-S01-MVP-TODO/AC1",
      "text": "最小底座/数据/B01-B02/A01/原前端/验收的真实依赖可追溯，无全平台或S02前置"
    },
    {
      "id": "D-S01-MVP-TODO/AC2",
      "text": "每项当前任务列实际交付/AC/预期证据；先开发范围和待数据/规则/安全条件明确，文档已交付与业务未准入不混写"
    },
    {
      "id": "D-S01-MVP-TODO/AC3",
      "text": "只规划不编码/新接口/模型调用；保留原型/原设计/旧证据，检查与提交同步真实，停止待负责人和星星评审"
    }
  ],
  "plannedTests": [
    "本轮文档/DAG/任务覆盖/来源/保全/链接/秘密启发式检查、build_docs.py/check_plan.py/diff --check；软件/接口/模型验收NOT_RUN"
  ],
  "completionEvidence": [
    "本轮计划提交、结构/依赖/链接/保全和18项文档检查结果；独立开发任务评审NOT_RUN。",
    "完成时填写真实实现commit、testedCommit、命令/版本/环境/输入版本/退出码与原始结果；按本任务AC逐项关联证据，未运行NOT_RUN、失败FAIL；负责人/指定评审者签认后才ACCEPTED。秘密/原始敏感响应不入Git，受控证据只登记合法引用/指纹。"
  ],
  "enablementGates": [],
  "risks": [
    "原则确认不代表数据/规则/安全条件就绪；未签认不伪造通过，未授权不开始代码或网络调用。"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "status": "REVIEW",
  "implementationCommits": [
    "26af91242f4ea5f0bb5a1d85ed21f24520662d23"
  ],
  "testedCommit": "26af91242f4ea5f0bb5a1d85ed21f24520662d23",
  "evidence": [
    {
      "kind": "PLANNING_SELF_CHECK",
      "acceptanceIds": [
        "D-S01-MVP-TODO/AC1",
        "D-S01-MVP-TODO/AC2",
        "D-S01-MVP-TODO/AC3"
      ],
      "command": "PowerShell here-string | python -（任务JSON/依赖DAG/启用门禁/原验收编号与来源/状态/保全/Markdown/链接检查）",
      "environment": "Windows / Python markdown/Git；仅计划文档作者自检，非独立任务评审",
      "sample": "31项台账：细化13个既有A/B/C任务，保全9个其余既有记录，新增9项（4准入门/4场景与验收/本轮规划）。交付依赖无环、无C-02/C-03/C-05或S02前置；21项当前实施/准入任务均有交付/AC/预期证据，完整引用原MVP 22个S01-AC。67个所涉及文档本地链接无断链，7表可解析；所有未来实现/真实验收无伪造证据",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/TASKS.md"
    },
    {
      "kind": "DOCUMENT_CHECK",
      "acceptanceIds": [
        "D-S01-MVP-TODO/AC1",
        "D-S01-MVP-TODO/AC2",
        "D-S01-MVP-TODO/AC3"
      ],
      "command": "python docs/planning/build_docs.py；python docs/planning/check_plan.py；git -c core.whitespace=cr-at-eol diff --check",
      "environment": "Windows / 项目既有文档工具；仅文档检查",
      "sample": "build_docs/check_plan均退出0，31项台账/18项文档规则PASS；生成状态/DAG来自TASKS，不另写进度或第二份TODO",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/planning/validation-report.json"
    },
    {
      "kind": "REPOSITORY",
      "acceptanceIds": [
        "D-S01-MVP-TODO/AC1",
        "D-S01-MVP-TODO/AC2",
        "D-S01-MVP-TODO/AC3"
      ],
      "command": "Git对象对照、差异文件白名单、未知YAML哈希/秘密启发式与应用入口检查",
      "environment": "main / 接手85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3；跟踪起点/暂存为空",
      "sample": "仅计划/原则ADR/必要索引/交接/派生文件；原需求/概要/AI详设/MVP/专项/ERP报告与JSON/单SKU表/原型等全部未改，无src/pyproject/migrations初始化。YAML指纹匹配旧证据且未跟踪、不暂存；定向秘密启发式0发现。新ERP/认证/模型请求0",
      "exitCode": 0,
      "result": "PASS",
      "artifactRef": "docs/HANDOFF.md"
    },
    {
      "kind": "DEVELOPMENT_PLAN_REVIEW",
      "acceptanceIds": [
        "D-S01-MVP-TODO/AC1",
        "D-S01-MVP-TODO/AC2",
        "D-S01-MVP-TODO/AC3"
      ],
      "command": "NOT_RUN：负责人和星星评审本轮开发任务计划，再决定具体开发授权",
      "environment": "本轮只有规划授权，无软件/数据/安全签认的替代",
      "sample": "负责人五项原则确认记ADR，不等于真实身份/八域数据/规则/TLS或模型用途许可已签认；四门BLOCKED，实施任务仍TODO且未指派。当前文档交付REVIEW，所有新软件/ERP闭环/真实LLM/业务/MC验收NOT_RUN",
      "exitCode": null,
      "result": "NOT_RUN",
      "artifactRef": "docs/TASKS.md"
    }
  ],
  "review": null,
  "branch": "main",
  "observedHead": "26af91242f4ea5f0bb5a1d85ed21f24520662d23",
  "dirtyPaths": [
    "docs/ERP-openapi.yaml"
  ],
  "latestHandoffRef": "docs/HANDOFF.md",
  "blocker": null,
  "history": [
    {
      "date": "2026-11-11",
      "from": "TODO",
      "to": "IN_PROGRESS",
      "reason": "本轮仅规划登记；未领取开发，已知实际准入缺口单列BLOCKED，不把原则同意当完成",
      "observedHead": "85a146e7abf1c9f1e4aa6a2e05a31f1d5693bfb3"
    },
    {
      "date": "2026-11-12",
      "from": "IN_PROGRESS",
      "to": "REVIEW",
      "reason": "分阶段开发TODO已提交并经依赖/覆盖/保全及18项文档规则检查；只完成规划文档，开发未开始、准入缺口未关闭，交负责人和星星评审后另行授权",
      "observedHead": "26af91242f4ea5f0bb5a1d85ed21f24520662d23"
    }
  ]
}
```
