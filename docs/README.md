# 项目文档索引

本文只提供导航，不维护第二份需求、计划、任务状态或验收结论。MD 是正文，配套 HTML 是阅读材料；历史归档不是当前实施依据。

## 权威入口与职责

| 入口 | 唯一职责 |
|---|---|
| [项目 README](../README.md) | 对外介绍、实际能力、预览方法 |
| [AGENTS](../AGENTS.md) | 协作入口、授权与稳定边界 |
| [PLAN](PLAN.md) / [HTML](PLAN.html) | 当前 A—D 实施顺序；保留原里程碑与 MC 含义 |
| [TASKS](TASKS.md) | 唯一任务状态与验收台账；含基于85a146e的S01 MVP分阶段开发TODO与准入条件，待负责人/星星评审 |
| [DECISIONS](DECISIONS.md) | 当前决策、ADR 与待冻结事项 |
| [COLLABORATION](COLLABORATION.md) / [CI_RULES](CI_RULES.md) | 分工、提交、交接与检查约定 |
| [HANDOFF](HANDOFF.md) | 最近增量、实际检查和停止点 |
| [派生状态](generated/STATUS.md) | 从 TASKS 生成的只读视图 |

## 按内容阅读

| 分类 | 正文与必要材料 |
|---|---|
| 需求 | [需求文档](requirements/REQUIREMENTS.md) / [HTML](requirements/REQUIREMENTS.html)；[业务流程与术语参考](requirements/BUSINESS_GUIDE.html) |
| 架构 | [总体逻辑架构](architecture/ARCHITECTURE.md) / [HTML](architecture/ARCHITECTURE.html)；[概要开发设计](architecture/DEVELOPMENT_DESIGN.md) / [HTML](architecture/DEVELOPMENT_DESIGN.html)；[最小基座清单](architecture/MINIMUM_BASE_CHECKLIST.md) |
| 架构图与修订 | [逻辑图源](architecture/logical/mermaid/)；[工程图源](architecture/engineering/mermaid/)；[交互职责图](architecture/interactive/architecture-ai-runtime-20261111-110000/ai-runtime.html)；[R01—R09](architecture/REVISION_R01_R09.md)；[H01—H07](architecture/REVISION_H01_H07.md) |
| 计划 | [PLAN](PLAN.md)；[旧96项映射](TASK_MAPPING.md)；[文档构建与检查脚本](planning/) |
| Agent 设计 | [S01 补货专项详细设计（第一阶段）](agents/S01_补货Agent专项详细设计.md) / [HTML 阅读版](agents/S01_补货Agent专项详细设计.html)； [AI 模块详设](agents/AI_DETAILED_DESIGN.md) / [HTML](agents/AI_DETAILED_DESIGN.html)；[设计索引](agents/index.md)；[S01—S10 设计](agents/S01—S10_Agent与Workflow设计.md)；[模拟契约示例](agents/examples/s03-voc/) |
| MVP 实施 | [S01 MVP 实施文档 v0.2](agents/S01_MVP实施文档.md)；[教学ERP调查与字段映射](agents/S01_ERP接口调查与字段映射.md)；[脱敏证据](agents/evidence/s01-erp-survey-20261111.json)；[单SKU开发准入核对与建议](agents/S01_单SKU开发准入核对.md)。A01解释必做，ERP缺口/受控补充与原型对接明确；本轮无开发 |
| A-01 / A-02 工程入口 | [契约材料与当前授权增量](contracts/s01/A-01-契约评审稿.md)；[真实MySQL兼容证据](evidence/A-01/mysql-compatibility.json)；[A-02实际进程检查](evidence/A-02/smoke.json)；[启动/测试命令](../README.md)。负责人认可原则，普通字段自主确定；旧逐项评审材料保留历史，本机.env不入Git，四项业务安全门不解除 |
| 第一大阶段运行 | [A-03—A-06启动/迁移/测试/恢复命令](runbooks/phase-a.md)。独立MySQL上的真实迁移/权限/持久任务和API/Worker进程验证；状态/适用证据仍只在TASKS，工程Handler只在tests装配 |
| S01 双线交付 | [共用消费契约](contracts/s01/D-S01-DEV-01-freeze.md)；[离线数据准入报告](evidence/D-S01-DATA-01/admission-report.md)；[业务Handler工程运行说明](runbooks/s01-business.md)；[完整回归证据](evidence/D-S01-DEV-01/verification.json)。工程样例/Mock 与真实业务准入分开，最终状态及验收仍只读 TASKS |
| 真实教学ERP接入 | [API实测报告](evidence/D-S01-LIVE-01/api-report.md)、[八域矩阵](evidence/D-S01-LIVE-01/data-matrix.json)、[规则签认](evidence/D-S01-LIVE-01/owner-rule-review.md)、[运行边界](runbooks/s01-teaching-erp.md)。新试点已确认，真实观测与工程fixture分开；尚未通过真实B01/B02正向业务验收 |
| UI 设计 | [产品功能规格](ui/PRODUCT_SPEC.md)；[视觉规范](../DESIGN.md)；[参考研究](ui/RESEARCH.md)；[一致性与缺口](ui/ALIGNMENT.md)；[评审修复记录](ui/REVIEW_FIX.md)；[独立原型](../prototypes/s01/index.html) |
| 报告 | [可行性分析](reports/FEASIBILITY.md) / [HTML](reports/FEASIBILITY.html)；[示例测算](reports/feasibility/illustrative-financial-model.json)（非真实企业收益） |
| 历史归档 | [归档说明与旧链接定位](archive/README.md)；[旧96项计划](archive/plan96-v0.1/README.md)；[本次路径迁移表](governance/migration.json) |
| 公开准备 | [发布说明与阻碍](governance/PUBLICATION.md)；[可重跑检查](governance/audit.py)；[检查结果](governance/audit.json) |

## 阅读边界

当前教学P3最小闭环支持已获授权自有范围的人工确认→ERP申请创建/submit，仍不代签审批或下单/收货。V2分支增加全部授权只读目录和方案B，完整范围见契约及交付报告，最终状态只读TASKS。企业真实业务准入独立验收，文档、原型或Mock不能替代；业务决策见DECISIONS。

文档治理仅调整文件归类、导航和文档工具路径。五份治理前基线原文、17份旧计划文件和已有 Git 历史保留；当前五份正文除链接与路径外不变，检查由 `docs/governance/audit.py` 执行。历史证据中的旧路径、旧 SHA 与旧机器环境表示当时事实，不作为当前运行配置。

[S01正式前端运行手册](runbooks/s01-frontend.md) · [本轮前端交付](evidence/D-S01-UI-01/report.md)

S01 V2 增量入口：[需求/架构/API契约](contracts/s01/v2-full-replenishment.md) · [完整产品交付与五SKU实测](reports/S01_V2完整补货工作台交付_20261113.md) · [运行/操作/恢复手册](runbooks/s01-v2.md)。当前任务状态仍只读TASKS。
