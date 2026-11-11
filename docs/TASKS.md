# 唯一任务与验收台账 v0.2

发布跟进附记（2026-11-11）：Codex 在 main / `6247e8356d5892f3ed5a1e7007e632e39263b458` 领取既有仓库许可/连接器核查，起点干净且无 remote；写入范围为 HANDOFF、TASKS 附记、THIRD_PARTY_NOTICES、governance 的 PUBLICATION/许可报告/核查 JSON。既有19项业务任务状态不变。目标账号/仓库/Public/写权限已验证，远端为空；当前连接器不支持本地提交 push，未做远端写入。许可材料与图标核查仍 BLOCKED，发布后 SHA/目录/README 检查 NOT_RUN。证据见 [增量核查](governance/LICENSE_REVIEW.md) 和 [核查记录](governance/connector-publication-check.json)；本轮提交由最终 Git 查询记录，不伪造 SHA。


本台账登记18项近期工作及1项本轮获准的独立产品/视觉原型；SETUP是本轮整理/建仓，A/B为S01必要子集，C按需，D只登记下一项S01专项设计。旧96项完整原稿/状态见archive/plan96-v0.1，旧ID映射见TASK_MAPPING.md。未来场景不预建空任务。


文档治理附记（2026-11-11）：本轮只迁移路径和记录公开准备；以下19项任务状态、依赖、验收、提交与评审历史均保持不变。治理范围/实际提交/检查和公开阻碍见HANDOFF.md及governance/PUBLICATION.md，不将文档治理计为S01或公共能力开发验收。

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
