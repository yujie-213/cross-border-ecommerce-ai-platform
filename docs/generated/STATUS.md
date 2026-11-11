# 近期任务视图（自动生成）

唯一源：[TASKS](../TASKS.md)，SHA-256=`aa3f0ab0abfdb4deb9008457cd0e4a5645625f18b9fe06af8429dc2bc0636a8d`。不要手工编辑；候选不是执行授权。

任务 18 项；TODO 17；IN_PROGRESS 0；BLOCKED 0；REVIEW 1；ACCEPTED 0。

| 轨道 | 数量 | TODO | IN_PROGRESS | BLOCKED | REVIEW | ACCEPTED |
|---|---|---|---|---|---|---|
| SETUP | 1 | 0 | 0 | 0 | 1 | 0 |
| A | 6 | 6 | 0 | 0 | 0 | 0 |
| B | 5 | 5 | 0 | 0 | 0 | 0 |
| C | 5 | 5 | 0 | 0 | 0 | 0 |
| D | 1 | 1 | 0 | 0 | 0 | 0 |

## 当前活动记录

- SETUP-001 精简计划/归档与本地Git交付：REVIEW；实际执行者=本轮AI执行者。

## 全部近期记录

| ID | 内容 | 状态 | 直接依赖 |
|---|---|---|---|
| SETUP-001 | 精简计划/归档与本地Git交付 | REVIEW | 无；仍核对入口指令 |
| A-01 | S01所需最小版本与公共契约冻结 | TODO | D-S01-01 |
| A-02 | 最小骨架、配置、错误与日志 | TODO | A-01 |
| A-03 | MySQL、SQLAlchemy与Alembic子集 | TODO | A-02 |
| A-04 | 身份认证、权限与租户必要子集 | TODO | A-02 |
| A-05 | API/独立Worker与MySQL持久任务 | TODO | A-03, A-04 |
| A-06 | 工程底座复现与故障验收 | TODO | A-05 |
| B-01 | D01/D02 S01输入适配与标准化 | TODO | D-S01-01, A-03, A-04 |
| B-02 | D03/D04 S01质量/快照与证据 | TODO | B-01 |
| B-03 | B01 S01确定性供需指标 | TODO | D-S01-01, A-01 |
| B-04 | B02 S01基线/候选与约束 | TODO | B-03 |
| B-05 | O01 Handler调度/报告与G01/G02边界 | TODO | A-05, B-02, B-03 |
| C-01 | A01/ModelProvider与调用控制最小实现 | TODO | A-05, A-01 |
| C-02 | A02内容理解与结构化产物（按需） | TODO | C-01 |
| C-03 | A03 RAG/只读Tool/Skill最小契约（按需） | TODO | C-01, B-02 |
| C-04 | 已选模型用途最小评测与Golden Dataset | TODO | C-01 |
| C-05 | Runtime/Harness/Loop启用评审（按需） | TODO | 无；仍核对入口指令 |
| D-S01-01 | S01补货专项设计（下一项） | TODO | 无；仍核对入口指令 |

D-S01-01下一条指令即可进入；不依赖A/B/C/S02。C任务仅实际用途需要时选择。旧96项只读映射见TASK_MAPPING，不汇入当前任务完成率。
