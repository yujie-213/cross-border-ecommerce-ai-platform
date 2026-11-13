# 近期任务视图（自动生成）

唯一源：[TASKS](../TASKS.md)，SHA-256=`56c4ae440f6690656dad59ca2f7ec02612f56acf95c461614d1ac0ebbe7e46ef`。不要手工编辑；候选不是执行授权。

任务 43 项；TODO 5；IN_PROGRESS 0；BLOCKED 4；REVIEW 17；ACCEPTED 17。

| 轨道 | 数量 | TODO | IN_PROGRESS | BLOCKED | REVIEW | ACCEPTED |
|---|---|---|---|---|---|---|
| SETUP | 1 | 0 | 0 | 0 | 1 | 0 |
| A | 6 | 0 | 0 | 0 | 0 | 6 |
| B | 5 | 0 | 0 | 0 | 0 | 5 |
| C | 5 | 3 | 0 | 0 | 1 | 1 |
| D | 26 | 2 | 0 | 4 | 15 | 5 |

## 当前活动记录

- SETUP-001 精简计划/归档与本地Git交付：REVIEW；实际执行者=本轮AI执行者。
- C-04 S01真实模型解释用途评测与安全降级验收（必做）：REVIEW；实际执行者=Codex（本轮C-04真实复验，单人串行）。
- D-S01-01 S01补货专项详细设计（第一阶段）：REVIEW；实际执行者=Codex（本轮唯一文档执行者与台账集成人）。
- UX-S01-01 S01采购补货交互原型与项目视觉规范：REVIEW；实际执行者=Codex（本轮AI执行者，实际同文件唯一写入者）。
- D-S01-MVP-PLAN S01 MVP实施文档与最小底座范围（仅文档）：REVIEW；实际执行者=Codex（本轮单人文档执行者）。
- D-S01-ERP-01 S01 A01必做范围修订、教学ERP调查与MVP方案更新：REVIEW；实际执行者=Codex（单人执行，不使用代理）。
- D-S01-ENTRY-01 单SKU最小开发准入核对与决策建议（仅文档）：REVIEW；实际执行者=Codex（单人文档执行）。
- D-S01-DATA-01 单SKU身份恢复与受控数据准入：BLOCKED；实际执行者=Codex（本轮单人真实教学ERP接入与集成）。
- D-S01-RULE-01 单SKU供需/候选与质量规则签认：BLOCKED；实际执行者=Codex（本轮单人真实教学ERP接入与集成）。
- D-S01-ERP-ACCESS-01 教学ERP真实只读启用与安全条件确认：BLOCKED；实际执行者=Codex（本轮单人真实教学ERP接入与集成）。
- D-S01-AI-ACCESS-01 A01真实Provider/模型用途启用条件确认：BLOCKED；实际执行者=未指派。
- D-S01-LIVE-01 单SKU教学ERP真实读取与受控补充闭环验收：REVIEW；实际执行者=Codex主集成及冻结范围并行Agent。
- D-S01-MVP-TODO S01 MVP分阶段开发任务规划（本轮仅文档）：REVIEW；实际执行者=Codex（本轮唯一文档规划执行者）。
- D-S01-ONLINE-01 ERP在线采集与工作台入口：REVIEW；实际执行者=Codex。
- D-S01-ONLINE-02 在线数据准入与B01/B02：REVIEW；实际执行者=Codex。
- D-S01-ONLINE-03 正常在线任务DeepSeek解释：REVIEW；实际执行者=Codex。
- D-S01-DATASET-DESIGN-01 仿真经营数据与监控范围评估：REVIEW；实际执行者=Codex。
- D-S01-DATASET-PILOT-01 独立数据范围和ERP能力小试：REVIEW；实际执行者=Codex。
- D-S01-FORECAST-SURVEY-01 自有两SKU ERP未来销量接口只读核实：REVIEW；实际执行者=Codex。
- D-S01-P1P2-BUSINESS-REVIEW-01 P1/P2补货数量与供应商采购约束独立业务核查：REVIEW；实际执行者=Codex。
- D-S01-P3-PREP-01 P3采购审核与执行流程开发准备（无业务执行）：REVIEW；实际执行者=Codex。

## 全部近期记录

| ID | 内容 | 状态 | 直接依赖 |
|---|---|---|---|
| SETUP-001 | 精简计划/归档与本地Git交付 | REVIEW | 无；仍核对入口指令 |
| A-01 | S01所需最小版本与公共契约冻结 | ACCEPTED | D-S01-01 |
| A-02 | 最小骨架、配置、错误与日志 | ACCEPTED | A-01 |
| A-03 | MySQL、SQLAlchemy与Alembic子集 | ACCEPTED | A-02 |
| A-04 | 身份认证、权限与租户必要子集 | ACCEPTED | A-02 |
| A-05 | API/独立Worker与MySQL持久任务 | ACCEPTED | A-03, A-04 |
| A-06 | 工程底座复现与故障验收 | ACCEPTED | A-05 |
| B-01 | D01/D02 S01输入适配与标准化 | ACCEPTED | D-S01-01, A-03, A-04 |
| B-02 | D03/D04 S01质量/快照与证据 | ACCEPTED | B-01, D-S01-RULE-01 |
| B-03 | B01 S01确定性供需指标 | ACCEPTED | A-01, D-S01-RULE-01 |
| B-04 | B02 S01基线/候选与约束 | ACCEPTED | B-03 |
| B-05 | O01 Handler调度/报告与G01/G02边界 | ACCEPTED | A-05, B-02, B-03 |
| C-01 | A01真实解释必需的网关/Provider与调用控制子集 | ACCEPTED | A-05, A-01 |
| C-02 | A02内容理解与结构化产物（按需） | TODO | C-01 |
| C-03 | A03 RAG/只读Tool/Skill最小契约（按需） | TODO | C-01, B-02 |
| C-04 | S01真实模型解释用途评测与安全降级验收（必做） | REVIEW | C-01, D-S01-DEV-01, D-S01-AI-ACCESS-01 |
| C-05 | Runtime/Harness/Loop启用评审（按需） | TODO | 无；仍核对入口指令 |
| D-S01-01 | S01补货专项详细设计（第一阶段） | REVIEW | 无；仍核对入口指令 |
| UX-S01-01 | S01采购补货交互原型与项目视觉规范 | REVIEW | 无；仍核对入口指令 |
| D-S01-MVP-PLAN | S01 MVP实施文档与最小底座范围（仅文档） | REVIEW | 无；仍核对入口指令 |
| D-S01-ERP-01 | S01 A01必做范围修订、教学ERP调查与MVP方案更新 | REVIEW | 无；仍核对入口指令 |
| D-S01-ENTRY-01 | 单SKU最小开发准入核对与决策建议（仅文档） | REVIEW | 无；仍核对入口指令 |
| D-S01-DATA-01 | 单SKU身份恢复与受控数据准入 | BLOCKED | 无；仍核对入口指令 |
| D-S01-RULE-01 | 单SKU供需/候选与质量规则签认 | BLOCKED | 无；仍核对入口指令 |
| D-S01-ERP-ACCESS-01 | 教学ERP真实只读启用与安全条件确认 | BLOCKED | 无；仍核对入口指令 |
| D-S01-AI-ACCESS-01 | A01真实Provider/模型用途启用条件确认 | BLOCKED | A-01 |
| D-S01-LIVE-01 | 单SKU教学ERP真实读取与受控补充闭环验收 | REVIEW | B-01, B-02, D-S01-DATA-01, D-S01-RULE-01, D-S01-ERP-ACCESS-01 |
| D-S01-DEV-01 | S01 Workflow与规则报告/AI解释语义接入 | ACCEPTED | B-05, B-04, C-01 |
| D-S01-UI-01 | 沿用S01原型的真实API/AI详情对接 | ACCEPTED | D-S01-DEV-01, A-04 |
| D-S01-ACCEPT-01 | 单SKU S01 MVP端到端复现与负责人验收 | TODO | A-06, D-S01-LIVE-01, D-S01-DEV-01, D-S01-UI-01, C-04 |
| D-S01-MVP-TODO | S01 MVP分阶段开发任务规划（本轮仅文档） | REVIEW | 无；仍核对入口指令 |
| D-S01-ONLINE-01 | ERP在线采集与工作台入口 | REVIEW | A-06, B-01, D-S01-UI-01 |
| D-S01-ONLINE-02 | 在线数据准入与B01/B02 | REVIEW | D-S01-ONLINE-01, B-03, B-04 |
| D-S01-ONLINE-03 | 正常在线任务DeepSeek解释 | REVIEW | D-S01-ONLINE-02, C-01 |
| D-S01-DATASET-DESIGN-01 | 仿真经营数据与监控范围评估 | REVIEW | 无；仍核对入口指令 |
| D-S01-DATASET-PILOT-01 | 独立数据范围和ERP能力小试 | REVIEW | D-S01-DATASET-DESIGN-01 |
| D-S01-MONITOR-SCOPE-01 | D02版本化自建SKU监控清单 | ACCEPTED | D-S01-DATASET-DESIGN-01, D-S01-DATASET-PILOT-01 |
| D-S01-DATASET-IMPORT-01 | S01八场景最小经营数据集 | TODO | D-S01-DATASET-PILOT-01, D-S01-MONITOR-SCOPE-01 |
| D-S01-FORECAST-SURVEY-01 | 自有两SKU ERP未来销量接口只读核实 | REVIEW | D-S01-MONITOR-SCOPE-01 |
| D-S01-P1P2-BUSINESS-REVIEW-01 | P1/P2补货数量与供应商采购约束独立业务核查 | REVIEW | D-S01-ONLINE-02, D-S01-ONLINE-03, D-S01-MONITOR-SCOPE-01 |
| D-S01-CARTON-FIX-01 | MOQ与ERP整箱采购规则最小修复及两SKU真实复验 | ACCEPTED | D-S01-P1P2-BUSINESS-REVIEW-01, D-S01-ONLINE-02, D-S01-ONLINE-03 |
| D-S01-P1P2-MERGE-01 | P1/P2阶段验收登记、main正常合并与发布 | ACCEPTED | D-S01-CARTON-FIX-01, D-S01-MONITOR-SCOPE-01, D-S01-ONLINE-02, D-S01-ONLINE-03 |
| D-S01-P3-PREP-01 | P3采购审核与执行流程开发准备（无业务执行） | REVIEW | D-S01-P1P2-MERGE-01 |

D-S01-01下一条指令即可进入；不依赖A/B/C/S02。C任务仅实际用途需要时选择。旧96项只读映射见TASK_MAPPING，不汇入当前任务完成率。
