# 本轮交付与文件变化

由repository_audit.py生成。只改管理/计划文档及文档工具；五份基线未改，未建业务工程。旧17份文件字节保全，96项任务/评审状态逐ID可追。实际提交及剩余未跟踪见[仓库回执](repository-receipt.json)。

管理范围数量：{"ADDED": 17, "MODIFIED": 15, "ARCHIVED": 19, "UNCHANGED": 2}。ARCHIVED包括17份原稿、说明与指纹清单。白名单内既有设计/图表/修订史只读入库，不计本轮新增设计。

| 路径 | 变化 |
|---|---|
| [.gitignore](../../.gitignore) | ADDED |
| [AGENTS.md](../../AGENTS.md) | MODIFIED |
| [docs/archive/plan96-v0.1/AGENTS.md](../archive/plan96-v0.1/AGENTS.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/archive-manifest.json](../archive/plan96-v0.1/archive-manifest.json) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/CI_RULES.md](../archive/plan96-v0.1/docs/CI_RULES.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/COLLABORATION.md](../archive/plan96-v0.1/docs/COLLABORATION.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/DECISIONS.md](../archive/plan96-v0.1/docs/DECISIONS.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/generated/DEPENDENCIES.mmd](../archive/plan96-v0.1/docs/generated/DEPENDENCIES.mmd) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/generated/STATUS.md](../archive/plan96-v0.1/docs/generated/STATUS.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/HANDOFF.md](../archive/plan96-v0.1/docs/HANDOFF.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/PLAN.md](../archive/plan96-v0.1/docs/PLAN.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/baseline-manifest.json](../archive/plan96-v0.1/docs/planning/baseline-manifest.json) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/check_plan.py](../archive/plan96-v0.1/docs/planning/check_plan.py) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/file-manifest.json](../archive/plan96-v0.1/docs/planning/file-manifest.json) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/FILES.md](../archive/plan96-v0.1/docs/planning/FILES.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/initial-workspace-observation.json](../archive/plan96-v0.1/docs/planning/initial-workspace-observation.json) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/render_status.py](../archive/plan96-v0.1/docs/planning/render_status.py) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/task_io.py](../archive/plan96-v0.1/docs/planning/task_io.py) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/planning/validation-report.json](../archive/plan96-v0.1/docs/planning/validation-report.json) | ARCHIVED |
| [docs/archive/plan96-v0.1/docs/TASKS.md](../archive/plan96-v0.1/docs/TASKS.md) | ARCHIVED |
| [docs/archive/plan96-v0.1/README.md](../archive/plan96-v0.1/README.md) | ARCHIVED |
| [docs/CI_RULES.md](../CI_RULES.md) | MODIFIED |
| [docs/COLLABORATION.md](../COLLABORATION.md) | MODIFIED |
| [docs/DECISIONS.md](../DECISIONS.md) | MODIFIED |
| [docs/generated/DEPENDENCIES.mmd](../generated/DEPENDENCIES.mmd) | MODIFIED |
| [docs/generated/STATUS.md](../generated/STATUS.md) | MODIFIED |
| [docs/HANDOFF.md](../HANDOFF.md) | MODIFIED |
| [docs/PLAN.html](../PLAN.html) | ADDED |
| [docs/PLAN.md](../PLAN.md) | MODIFIED |
| [docs/planning/authorization-and-scope.json](authorization-and-scope.json) | ADDED |
| [docs/planning/baseline-manifest.json](baseline-manifest.json) | UNCHANGED |
| [docs/planning/browser-check.json](browser-check.json) | ADDED |
| [docs/planning/build_docs.py](build_docs.py) | ADDED |
| [docs/planning/check_plan.py](check_plan.py) | MODIFIED |
| [docs/planning/diagrams/plan-flow.mmd](diagrams/plan-flow.mmd) | ADDED |
| [docs/planning/diagrams/plan-flow.svg](diagrams/plan-flow.svg) | ADDED |
| [docs/planning/diagrams/render-receipt.json](diagrams/render-receipt.json) | ADDED |
| [docs/planning/file-manifest.json](file-manifest.json) | MODIFIED |
| [docs/planning/FILES.md](FILES.md) | MODIFIED |
| [docs/planning/git-whitelist.json](git-whitelist.json) | ADDED |
| [docs/planning/initial-workspace-observation.json](initial-workspace-observation.json) | MODIFIED |
| [docs/planning/plan-build.json](plan-build.json) | ADDED |
| [docs/planning/preflight.json](preflight.json) | ADDED |
| [docs/planning/render_plan.cjs](render_plan.cjs) | ADDED |
| [docs/planning/render_status.py](render_status.py) | MODIFIED |
| [docs/planning/repository-receipt.json](repository-receipt.json) | ADDED |
| [docs/planning/repository_audit.py](repository_audit.py) | ADDED |
| [docs/planning/security-scan.json](security-scan.json) | ADDED |
| [docs/planning/task-mapping.json](task-mapping.json) | ADDED |
| [docs/planning/task_io.py](task_io.py) | UNCHANGED |
| [docs/planning/validation-report.json](validation-report.json) | MODIFIED |
| [docs/TASK_MAPPING.md](../TASK_MAPPING.md) | ADDED |
| [docs/TASKS.md](../TASKS.md) | MODIFIED |

文件hash见file-manifest.json，自引用文件不计算自身hash。旧基线可选链接指向architecture/feasibility/.archify的材料可能未入库；原工作区文件保留。PLAN.html图示自包含。文档脚本不是业务实现。
