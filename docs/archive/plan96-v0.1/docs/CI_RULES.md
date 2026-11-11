# 最小文档与任务证据检查设计 v0.1

本轮只建立轻量文档读取/生成/检查脚本，未初始化业务CI、连接服务或创建项目管理平台。TASKS.md是唯一任务源；脚本不得自动将任务标ACCEPTED、修改人工签认或生成虚假测试输出。

## 当前可运行的文档检查

```text
python docs/planning/render_status.py
python docs/planning/check_plan.py
python docs/planning/render_status.py --check
```

只用Python标准库，读取本轮TASKS和五份基线指纹；生成STATUS.md/DEPENDENCIES.mmd并检查必需文件、字段/ID、引用、DAG、状态、验收及证据基本形状。本轮Git缺失是已记录的启动事实，非“已验收”；不因Git未初始化而伪造SHA或创建仓库。规划检查成功只表示文档结构/覆盖自洽，不表示任何开发测试或业务能力通过。

## 后续CI最低阻断规则

| 规则 | 阻断条件 | 最小实现 / 人工责任 |
|---|---|---|
| DOC-01 必需文件与唯一源 | 缺AGENTS/PLAN/TASKS/HANDOFF/DECISIONS/COLLABORATION/CI_RULES；另有人工维护任务状态源 | 解析TASKS中每条JSON，ID唯一；状态只用TODO/IN_PROGRESS/BLOCKED/REVIEW/ACCEPTED，生成视图只读 |
| DOC-02 字段/链接/依赖 | 无stage/目标/优先级/owner/范围/依赖/交付/验收/测试/风险/依据；依赖不存在、环、ID重用、台账引用路径失效 | DAG/字段自动检查；入口签认和实际权限必须人工核验，不能以DAG通过代替 |
| DOC-03 生成一致性 | STATUS/DEPENDENCIES与TASKS内容hash不符或手改 | `render_status.py --check`，不在CI自动改文件再吞掉漂移 |
| DOC-04 状态事实 | IN_PROGRESS无assignee/baseCommit/范围；BLOCKED无具体原因/责任/解除条件；ACCEPTED未达完整证据规则 | 当前M0-001为工作区规划REVIEW例外，无Git不允许ACCEPTED；未来正常领取均绑定Git基点 |
| DOC-05 ACCEPTED基本证据 | 无真实implementationCommits/testedCommit/review；任一criterion无PASS证据；缺requiredEvidenceKinds；出现FAIL/NOT_RUN冒充验收 | 证据路径/hash/时间/环境/样本/命令/退出码及具名手工签认；实际数据/模型/动作证据类别不能用Mock替代 |
| DOC-06 Git与制品绑定 | SHA不是实际commit；testedCommit不属于评审实现；evidenceCommit无相关制品或hash不符；C1→C2有未经重新验证的相关代码变更 | 仓库落地后增加只读git cat-file/show/diff检查；提交前的制品hash也检查，禁止自引用当前commit SHA |
| DOC-07 变更影响与回归 | 公共契约/基线/数据归属/权限/动作范围改变但无ADR/消费者/兼容与回归证据；模块写范围越权 | PR差异与task.allowedPaths/ADR核对；路径检查不能代替架构审查 |
| DOC-08 交接完整 | 变更任务结束无交接/真实测试/未完成说明或生成视图未更新；脏工作区被冒称干净已提交 | TASKS latestHandoffRef与记录内容核对；WORKTREE_ONLY不能ACCEPTED |

ACCEPTED检查面向**本次变更为ACCEPTED或修改验收记录的任务**，验证实现commit→证据commit之间的相关变更；历史任务的验收是当时版本事实，不因以后无关功能提交就自动抹掉。后续修改同模块/契约时，新任务应声明消费者和所需回归；若发现旧证据失效，再按协议重开/缺陷任务。不能用“全项目HEAD必须等于每个历史testedCommit”这种不可能条件封死后续开发。

证据文件使用每次运行不可变路径；Git中只放许可允许的日志/最小引用。当前脚本对ACCEPTED会检查真实commit存在、testedCommit是evidenceCommit祖先，并按evidenceCommit读取制品blob核对hash，而非要求当前工作区永远保留同名旧文件。本轮没有ACCEPTED、没有Git，故没有实际运行正向Git验收；不能声称该分支已在真实工程验证。DOC-06/07/08完整变更影响、环境真实性、人工签认身份及交接语义审查留仓库/CI落地任务，不能宣称已实现防伪平台。

## 不通过的处理

生成漂移重建后提交；字段/依赖错误修台账并审查；测试FAIL保留原输出继续修或BLOCKED；证据缺失保持REVIEW/IN_PROGRESS；越权/重复动作/关键金额错误立即阻断相应发布。检查器不能自动删验收项、自动换成“无需测试”或把失败平均成通过。

未来CI的最小顺序为文档/状态→格式/类型→目标任务单元/契约→真实MySQL集成→相关故障/隔离→获准离线AI评测→人工/业务和部署门槛。具体命令、工具锁定和CI载体随工程真实出现冻结，本轮不创建厂商CI配置、数据库或模型调用任务。
