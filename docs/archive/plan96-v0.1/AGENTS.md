# 项目协作规范（规划草案）

本项目当前只编制分阶段实施计划与协作协议，等待独立审查；不得依据台账中的TODO自行开始业务工程、补货Agent、部署或创建全部代码目录。后续经本项目审查及具体实施授权后，按以下协议开展任务；已有明确授权不重复索取。

## 事实来源与开始流程

Git中版本化的项目文件和实际证据是唯一项目事实来源；聊天、模型记忆、摘要和未提交工作区不能替代它们。当前目录尚非Git仓库，规划文件是待初次入库的工作区草案；本轮不执行git init/commit。Git落地由docs/TASKS.md中的M0-002负责，不宣称已有提交。

每次接手先读本文件→docs/HANDOFF.md的接手入口→docs/generated/STATUS.md（派生）→docs/TASKS.md中目标任务及直接依赖。先检查git status、HEAD、当前分支及未提交diff，再读取HANDOFF所列增量、目标模块契约和指定基线章节；不默认全量重读五份设计，不主动读取其他项目/历史会话。

五份授权基线及版本索引在docs/PLAN.md；历史页眉的“待复核”不推翻用户本次确认。若正文/引用/指纹冲突，记录差异并停止受影响实现，不自行重设计。模型偏好沿用用户要求的GPT-5.6 Sol、medium；不要自动切换模型或把模型名称写成项目运行依赖。

## 不得突破的代码边界

- 保持M0—M4、S01—S10、17公共模块和原业务分期。首批S02最小基座不开模型/外部写动作；A、B只是M1内验收节点，MC01—MC12由B最终验收。
- O01→ScenarioHandler→公共能力→DomainResult→O01；O01不重做领域B01/B02/A02步骤，场景不调度其他场景。B02单向调用B01，LLM不算权威金额/库存/分母。
- D01只读接入，D02投影/身份，D03唯一输入manifest，D04证据定位，O01任务/计划/报告/检查点；仅公开接口/受控投影跨模块，禁止私表写入/共享ORM。
- A01是唯一模型网关，只给技术结果；A03模型工具只读，C03独占外写。确认、提交、独立审批、另行执行是不同命令；UNKNOWN先原key核对。
- 子调用/重试/恢复共用原预算与期限；正式task与A03即席控制不混。Runtime只返回RunOutcome，Handler生成DomainResult；YIELD不得发布。模型契约按AI详设v0.2的§9.1。
- 缓存默认OFF，不先建缓存设施；Loop、多Agent、独立框架、Redis/MQ/Milvus/Neo4j/高级LLMOps/Memory均非首批必需。有真实使用方和已通过门槛才新增。
- 只创建本任务真实需要的目录/迁移。CPU/网络调用不占长数据库事务；并行分支不共享Session；迁移链/组合根/公共契约由指定集成人协调。

## 领取、并行与变更

任务唯一状态在docs/TASKS.md。状态只用TODO、IN_PROGRESS、BLOCKED、REVIEW、ACCEPTED；不得在HANDOFF/PLAN另写一套可修改状态或完成百分比。依赖未满足通常仍TODO；实际领取后被条件阻断才写BLOCKED及具体解除条件。

领取前核验授权、直接依赖ACCEPTED、entryConditions和路径租约，填写assignee/branch/baseCommit/allowedPaths/集成资源。并行必须契约已冻结且文件写范围不重叠；相同模块、迁移链、bootstrap、公开Schema、TASKS、生成器等共享文件只由一名集成人串行修改。分支/工作树安排按实际环境与用户要求决定，不预建。

公共契约/架构变更先在docs/DECISIONS.md记录问题、兼容影响、消费者、数据/权限/阶段影响、测试/迁移/回滚、责任人与评审结果。未获相应评审的Proposed决策不能供并行调用方实施。不得以赶任务或框架便利私改契约。

## 结束、证据与提交

按docs/COLLABORATION.md的两阶段提交/证据流程：先固定实现提交C1，针对C1执行适当测试，记录精确命令、环境/样本、退出码、真实结果和制品hash；再提交证据、TASKS/HANDOFF与生成视图C2。不得伪造SHA、测试通过或用文档渲染冒称业务验收；测试未运行写NOT_RUN，失败写FAIL并保留输出。提交范围只含本任务授权改动，不覆盖用户或其他人的未提交文件。

每个任务结束更新台账、交接记录、必要ADR及派生视图，留下实际commit、未完成项和接手命令。开发者提交REVIEW；ACCEPTED必须每条验收都有适用证据、有效Git提交、相关测试通过、依赖及启用条件满足、合格评审记录。业务/源动作批准须由对应责任人签认，AI不能自造。

中断/脏工作区/失败恢复先保存事实，不执行未授权reset --hard、clean、强推、覆盖或自动stash。按docs/COLLABORATION.md恢复流程对照HEAD、diff、日志和checkpoint，不丢弃未知改动。未提交结果不能标ACCEPTED。

## 最小文档检查

本轮仅运行 `python docs/planning/check_plan.py` 与 `python docs/planning/render_status.py --check` 检查规划文件。未来仓库已落地后CI增加Git证据校验（见docs/CI_RULES.md），不预建任务管理平台或业务CI工程。开发检查命令以目标任务/实际工程锁定为准，不能把规划中的拟定pytest名称当已经存在或已经通过的测试。
