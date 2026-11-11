# 唯一任务与验收台账 v0.2

本台账只有18项近期工作；SETUP是本轮整理/建仓，A/B为S01必要子集，C按需，D只登记下一项S01专项设计。旧96项完整原稿/状态见archive/plan96-v0.1，旧ID映射见TASK_MAPPING.md。未来场景不预建空任务。

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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/实际使用契约（未来）",
    "docs/DECISIONS.md"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "精确技术兼容矩阵、最小Task/ScenarioHandler/Refs/错误/事务/取消/权限与测试契约"
  ],
  "acceptance": [
    {
      "id": "A-01/AC1",
      "text": "Python/FastAPI/ORM/驱动/MySQL版本有验证，不取latest"
    },
    {
      "id": "A-01/AC2",
      "text": "只冻结S01切片所需字段，所有者/版本/消费者明确；不强制AI字段"
    },
    {
      "id": "A-01/AC3",
      "text": "重要变化有评审，S02/全部公共能力非前置"
    }
  ],
  "plannedTests": [
    "兼容性实验、契约正反例与MC/S01验收编号隔离审查"
  ],
  "risks": [
    "版本/DB环境与关键输入未确定则限制相关实现"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "pyproject/锁文件（未来）",
    "src/commerce_hub/bootstrap/",
    "src/commerce_hub/entrypoints/",
    "必要tests/"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "按使用创建模块化骨架、FastAPI工厂、统一配置/错误/日志"
  ],
  "acceptance": [
    {
      "id": "A-02/AC1",
      "text": "依赖可复现；无未使用空模块"
    },
    {
      "id": "A-02/AC2",
      "text": "配置缺失安全失败、日志无秘密、应用启动不迁移/内启Worker/模型"
    }
  ],
  "plannedTests": [
    "启动/缺配置/错误响应/日志脱敏/静态检查"
  ],
  "risks": [
    "不得把全部AI/场景目录提前创建"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "migrations/（未来）",
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/adapters/mysql/"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "真实连接/短事务/必要Repository、显式单迁移链"
  ],
  "acceptance": [
    {
      "id": "A-03/AC1",
      "text": "干净库迁移成功、失败整体回滚、UTC/Decimal/tenant键正确"
    },
    {
      "id": "A-03/AC2",
      "text": "网络锁外执行、并发分支独立Session，SQLite不替代"
    }
  ],
  "plannedTests": [
    "真实MySQL迁移/回滚/精度/唯一键与并发事务验证"
  ],
  "risks": [
    "仅创建当次必要表，DB账号与版本需冻结"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/governance/access/",
    "tests/security/当前边界（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "可信身份、当前scope/租户/字段与工具用途检查"
  ],
  "acceptance": [
    {
      "id": "A-04/AC1",
      "text": "测试身份仍验证签名/发行方/期限，不设匿名旁路"
    },
    {
      "id": "A-04/AC2",
      "text": "API/Worker/数据/证据边界不能被用户参数扩权"
    }
  ],
  "plannedTests": [
    "签名/过期/跨租户/扩大scope/字段越权负例"
  ],
  "risks": [
    "生产身份/数据使用边界未确认不得开放真实数据"
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/entrypoints/",
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/governance/observability/"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "两个进程、MySQL工作项/租约/重试/owner恢复、O01最小受理契约及G02必需审计"
  ],
  "acceptance": [
    {
      "id": "A-05/AC1",
      "text": "任务/工作项/必需审计原子性、命令去重和当前lease门禁可证"
    },
    {
      "id": "A-05/AC2",
      "text": "重启不丢投递，超限/取消有界；I01不推断业务/源结果"
    },
    {
      "id": "A-05/AC3",
      "text": "未实现Handler不生产注册；测试装配不成为第二公共任务平台"
    }
  ],
  "plannedTests": [
    "两PID停启/重复领取/旧Worker/回滚/取消/重试耗尽故障测试"
  ],
  "risks": [
    "技术持久投递不是S01/S02业务验收，租约数值待测"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "tests/integration/实际工程范围（未来）",
    "docs/evidence/A-06/（未来）",
    "docs/runbooks/最小运行说明（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "启动/迁移/停启/恢复命令、实际提交/日志与工程验收矩阵"
  ],
  "acceptance": [
    {
      "id": "A-06/AC1",
      "text": "真实MySQL+FastAPI+独立Worker链可复现，必要故障/隔离无硬失败"
    },
    {
      "id": "A-06/AC2",
      "text": "不标S02 MC06/07、真实ERP/模型或S01业务通过"
    }
  ],
  "plannedTests": [
    "干净库/双进程/恢复/去重/取消/权限/日志与交接复验"
  ],
  "risks": [
    "只证明工程，不做全项目公共能力就绪门槛"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/sync/",
    "src/commerce_hub/data/projection/",
    "实际选定读取适配器（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "一个获准输入模式的批次/来源/覆盖、SKU仓单位/分桶/供给映射与版本投影"
  ],
  "acceptance": [
    {
      "id": "B-01/AC1",
      "text": "simulated与真实来源明确区分；不接全部系统"
    },
    {
      "id": "B-01/AC2",
      "text": "歧义隔离、镜像不重复加、重放/删除/单位状态有证据；只读"
    }
  ],
  "plannedTests": [
    "模拟/已获准读取样本的去重/映射/覆盖/乱序/失败负例"
  ],
  "risks": [
    "真实ERP品牌/字段/权限未知不编造SDK；模拟不证明接口验收"
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
  "history": []
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
    "B-01"
  ],
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/quality/",
    "src/commerce_hub/data/evidence/"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "S01必需质量/时效/覆盖、固定manifest、当前权限下证据定位"
  ],
  "acceptance": [
    {
      "id": "B-02/AC1",
      "text": "snapshot定位固定数据修订，新增输入新版本，不存latest/hash空壳"
    },
    {
      "id": "B-02/AC2",
      "text": "原记录/指标/情景引用可追；D03/D04不复制对方资产"
    }
  ],
  "plannedTests": [
    "过旧/缺项/未映射/新输入/断链/删除/撤权测试"
  ],
  "risks": [
    "必需质量信号缺失阻断相关结论，不推断安全"
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
  "history": []
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
    "D-S01-01",
    "A-01"
  ],
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/metrics/",
    "tests/unit/metrics/s01/（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "可售、逐日余额、首缺、缓冲/缺口的实际使用子集"
  ],
  "acceptance": [
    {
      "id": "B-03/AC1",
      "text": "数量/单位/时间窗/可售日/缺项与设计期望一致"
    },
    {
      "id": "B-03/AC2",
      "text": "唯一公式，事实与情景均用同一评价器；LLM不算数"
    }
  ],
  "plannedTests": [
    "S01自有固定期望/边界/重复供给/单位与日期测试"
  ],
  "risks": [
    "S01期望须专项设计冻结，不能复用S02标签假称MC通过"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/forecasting/",
    "tests/unit/forecasting/s01/（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "显式假设需求基线、MOQ/倍数/日期候选及比较"
  ],
  "acceptance": [
    {
      "id": "B-04/AC1",
      "text": "每个候选调用B01，不另算逐日余额/首缺"
    },
    {
      "id": "B-04/AC2",
      "text": "无解/交期未知明确限制，不自动学习模型/求解平台"
    }
  ],
  "plannedTests": [
    "MOQ/倍数/预计可售日/无解与B01调用唯一性测试"
  ],
  "risks": [
    "学习预测或高级求解有真实收益证据再另立任务"
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
  "history": []
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
  "entryCondition": "本任务获明确实施授权；仅落实当前选定切片",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/workspace/",
    "必要入口/审计（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "公开ScenarioHandler/DomainResult、版本/证据审校、报告/取消/重入与观测子集"
  ],
  "acceptance": [
    {
      "id": "B-05/AC1",
      "text": "O01不重做领域计算；task/plan/participant/snapshot正确关联"
    },
    {
      "id": "B-05/AC2",
      "text": "真实业务Handler待S01实现任务注册，公共契约测试适配不冒充场景"
    },
    {
      "id": "B-05/AC3",
      "text": "报告可重读/去重/当前鉴权，无自动C01/C02/C03"
    }
  ],
  "plannedTests": [
    "契约测试、报告事务/重复发布/旧计划/租约/断链/取消验证"
  ],
  "risks": [
    "公共报告服务通过不等于S01业务闭环已实现"
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
  "history": []
}
```

## C-01 A01/ModelProvider与调用控制最小实现

```json
{
  "id": "C-01",
  "stage": "C",
  "title": "A01/ModelProvider与调用控制最小实现",
  "kind": "conditional-development",
  "dependsOn": [
    "A-05",
    "A-01"
  ],
  "entryCondition": "S01专项设计证明需要LLM，模型用途/数据许可与预算已明确",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/models/",
    "src/commerce_hub/adapters/models/",
    "实际Prompt/Context资源（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "统一请求/内部Provider解析、版本、结构输出、技术错误、期限/费用/usage记录"
  ],
  "acceptance": [
    {
      "id": "C-01/AC1",
      "text": "复用O01预算，attempt预留/结算/未知占额；无隐藏重试"
    },
    {
      "id": "C-01/AC2",
      "text": "Prompt/Context/Schema可追，缓存OFF不创建设施；A01不执工具"
    },
    {
      "id": "C-01/AC3",
      "text": "网关技术验收不自动启模型用途；启用还须C-04和真实许可"
    }
  ],
  "plannedTests": [
    "协议/Schema/拒答/超时/未知usage/预算竞争/版本与敏感日志负例"
  ],
  "risks": [
    "只有切片确需模型且数据/Provider条件获准时排期；非S01设计/规则MVP硬依赖"
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
  "history": []
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
  "title": "已选模型用途最小评测与Golden Dataset",
  "kind": "conditional-validation",
  "dependsOn": [
    "C-01"
  ],
  "entryCondition": "首次启用某真实模型用途前必须完成该用途评测",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "tests/evaluation/当前用途（未来）",
    "docs/evidence/C-04/（未来）"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "许可样本/金标准/规则与人审分层、版本/质量/费用/时延结果"
  ],
  "acceptance": [
    {
      "id": "C-04/AC1",
      "text": "Schema/引用/UNKNOWN/注入/成本等达获准阈值，硬失败不平均"
    },
    {
      "id": "C-04/AC2",
      "text": "实际模型与Mock证据分开，不把模拟费用当报价/收益"
    }
  ],
  "plannedTests": [
    "锁定集/真实获准模型/人工复核及结构/安全/预算回归"
  ],
  "risks": [
    "阈值/数据/计价未冻结则关闭对应模型用途，不阻规则S01"
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
  "history": []
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

## D-S01-01 S01补货专项设计（下一项）

```json
{
  "id": "D-S01-01",
  "stage": "D",
  "title": "S01补货专项设计（下一项）",
  "kind": "design",
  "dependsOn": [],
  "entryCondition": "收到下一条S01专项设计指令；当前计划/基线/本地Git可定位；本轮不执行",
  "ownerRole": "按任务领取时指定模块负责人/集成人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s01-design.md（获指令后才创建）",
    "docs/TASKS.md（按设计追加切片）",
    "docs/DECISIONS.md"
  ],
  "parallelCondition": "依赖满足、契约稳定且实际文件不相交；迁移/组合根/公共Schema/台账串行合入",
  "deliverables": [
    "字段/输入模式/业务流程/约束/质量依赖/公共子集与自有S01-AC",
    "专项设计后才拆实现/测试/复盘任务"
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
    "授权样例的桌面推演、字段/单位/日期/缺项/权限/质量反例审查"
  ],
  "risks": [
    "输入不足可先形成有缺口的设计，不补造企业事实"
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
