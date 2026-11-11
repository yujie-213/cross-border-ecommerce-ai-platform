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
| UI 设计 | [产品功能规格](ui/PRODUCT_SPEC.md)；[视觉规范](../DESIGN.md)；[参考研究](ui/RESEARCH.md)；[一致性与缺口](ui/ALIGNMENT.md)；[评审修复记录](ui/REVIEW_FIX.md)；[独立原型](../prototypes/s01/index.html) |
| 报告 | [可行性分析](reports/FEASIBILITY.md) / [HTML](reports/FEASIBILITY.html)；[示例测算](reports/feasibility/illustrative-financial-model.json)（非真实企业收益） |
| 历史归档 | [归档说明与旧链接定位](archive/README.md)；[旧96项计划](archive/plan96-v0.1/README.md)；[本次路径迁移表](governance/migration.json) |
| 公开准备 | [发布说明与阻碍](governance/PUBLICATION.md)；[可重跑检查](governance/audit.py)；[检查结果](governance/audit.json) |

## 阅读边界

首期 S01 只读，不开放外部采购执行。当前完成的是设计、规划与模拟原型，不能把文档或原型测试当作平台公共能力已经实现。业务规则与实现边界见正文及 DECISIONS；任务状态只读 TASKS。

文档治理仅调整文件归类、导航和文档工具路径。五份治理前基线原文、17份旧计划文件和已有 Git 历史保留；当前五份正文除链接与路径外不变，检查由 `docs/governance/audit.py` 执行。历史证据中的旧路径、旧 SHA 与旧机器环境表示当时事实，不作为当前运行配置。
