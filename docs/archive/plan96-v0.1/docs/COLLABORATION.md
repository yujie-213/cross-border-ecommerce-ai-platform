# AI协作与交接协议设计 v0.1

状态：待独立审查；仅设计管理机制，未初始化业务工程。本文只使用PLAN列明的五份项目基线及本轮新文件。

## 文件分工与单一事实

| 文件 | 唯一职责 | 不应承担 |
|---|---|---|
| ../AGENTS.md | 工作规范、边界、开始/结束流程；指向具体协议 | 可变任务进度、重复业务公式、历史聊天摘要库 |
| PLAN.md | 原M0—M4、里程碑/硬门槛、任务依赖读法、MC映射和实施顺序 | 独立人工维护任务状态/完成率 |
| TASKS.md | 唯一任务台账：定义、依赖、范围、状态、验收、证据、评审、阻塞和变更历史 | 复制其他台账；将产物清单自动视为完成 |
| HANDOFF.md | 当前会话接手入口、定位最新任务/交接记录、事实性工作总结和恢复方法 | 重复保存可修改任务状态；承诺未执行测试 |
| DECISIONS.md | ADR及待冻结决策、评估/批准/替代记录 | 第二任务台账、替代业务C02审批 |
| generated/STATUS.md、DEPENDENCIES.mmd | 从TASKS生成状态/可开始任务/依赖图，只读 | 直接人工编辑；作为另一个状态来源 |
| planning/validation-report.json、变更清单 | 本轮规划文档检查/文件证据 | 应用测试、真实接口/模型/生产验收 |

当前无Git仓库；本轮文件均是工作区草案。五份既有文档的审查状态来自本次用户确认，开发任务尚无实现/测试commit。M0-002经授权建仓并首批入库后，所有项目修改通过仓库记录。初次入库前允许交付工作区草案供审查，不能生成虚假commit或将开发任务标ACCEPTED。

唯一建仓启动特例：M0-002没有“先取得M0-001 ACCEPTED”的硬依赖，而以可保全的独立审查通过记录及仅建仓/入库授权为entryConditions。先把该签认与管理材料纳入真实Git提交，再补全M0-001/002证据和评审。它不允许无证据ACCEPTED，也不允许业务工程提前启动；M0退出仍硬依赖M0-001。阶段图的实线仅表示dependsOn，外部签认条件必须另外逐条检查，不能从“无硬依赖”推导立即可执行。

“Git唯一事实源”指代码、契约、计划、任务状态、决策与验收证据的项目事实；不改变ERP/OMS/WMS/CRM等原系统的业务数据权威。真实敏感数据按许可保存在受控源，Git只存最小授权引用、版本/指纹和可审计签认，不能为了证据把客户资料/凭据全量提交。

任务正文采用每条一个JSON代码块，便于按ID增量读取；它就是TASKS.md的一部分，不另维护任务JSON源。生成的状态/依赖可以删除后重建。每个任务有稳定ID、stage、priority、dependsOn、entryConditions、ownerRole、allowedPaths、parallelPolicy、deliverables、acceptance、plannedTests、risks、baselineRefs、requiredEvidenceKinds及唯一状态字段；状态历史留在同记录history，任务拆分/范围改变保留旧ID及替代关系，不重用已发布ID。

## 状态与评审

| 转换 | 条件 / 必须写入的事实 |
|---|---|
| TODO→IN_PROGRESS | 明确任务授权；直接依赖ACCEPTED、入口门槛满足；登记实际assignee/branch/baseCommit及互斥资源，承诺的文件范围明确 |
| IN_PROGRESS→BLOCKED | 已遇到实际阻碍；blocker含原因、影响、责任角色、解除证据/动作、可继续部分及最后检查时间；不能只写“等依赖” |
| BLOCKED→IN_PROGRESS | 新事实/解除证据可定位；保留原阻塞历史与恢复记录，不清空失败日志 |
| IN_PROGRESS→REVIEW | 提交可审查产物、证据和未完成事项；不得写“已验收”。开发任务原则上所需测试通过，设计草案可明确列未冻结事项请求评审 |
| REVIEW→IN_PROGRESS或BLOCKED | 评审退回或发现阻碍；保存意见、修复范围，不能暗改验收标准以求通过 |
| REVIEW→ACCEPTED | 每个验收criterionId有适用真实证据；测试/依赖/启用门槛、Git提交和评审全部满足；独立评审者记录姓名/角色/日期/被评实现commit及证据commit |
| ACCEPTED发生后续问题 | 优先新增缺陷/变更任务并保留历史；证据失效确需重开时显式ACCEPTED→REVIEW，写原因与受影响消费者，不能无审计清除验收 |

TODO不等于现在可执行；可开始条件还包括依赖、授权、外部条件和资源。计划草案提交独立审查的M0-001为REVIEW，其他实施任务初始TODO；没有ACCEPTED。未验证的真实数据/接口不得因为模拟基座通过而解除。

## Git提交与验收证据，避免自引用SHA

1. 先形成实现/配置/测试代码提交C1。未提交改动可以记录WIP，不能作为已验收版本。保存精确HEAD和dirty范围；不要声称测试覆盖了以后才提交的代码。
2. 针对干净C1执行所需检查，将命令、工作目录、时间、工具版本/环境、输入样本版本、模拟/真实证据类别、退出码、通过/失败摘要、日志/制品路径与SHA-256写入证据。失败原样记录；手工业务复核用具名签认材料，不编造shell命令。
3. 提交证据、台账REVIEW、HANDOFF和派生视图为C2。台账testedCommit=C1，implementationCommits含C1；证据明确testedCommit而非“当前最新”。C2若修改任何相关实现/测试/fixture/契约/配置/迁移，必须重新测试对应新commit并更新证据，不能仍声称C1覆盖了它。
4. 评审者核验C1→C2仅有允许的证据/管理改动，再将ACCEPTED及review记录提交C3。review包含reviewedImplementationCommit=C1、evidenceCommit=C2；C3无需在自身文件中填自己的SHA，接受记录commit从Git历史推导，避免“commit里写自己的hash”的循环。
5. 生成视图使用TASKS内容hash，不写当前生成提交SHA；验证生成无漂移后提交。提交之后HEAD可由git log定位，HANDOFF不手抄一个永远落后一拍的“当前HEAD”。无提交能力/仓库不可用时，交接写WORKTREE_ONLY与原因，保持REVIEW/IN_PROGRESS/BLOCKED，不ACCEPTED。

推荐证据对象模板（只是协议，未填真实证据）：

```json
{
  "id": "EV-<task>-<n>",
  "criterionIds": ["<task>/AC1"],
  "kind": "SIMULATED_ENGINEERING",
  "testedCommit": "<实际40位Git SHA>",
  "command": "<实际执行命令；人工复核则为null>",
  "cwd": "<仓库相对路径>",
  "environmentRef": "<工具/配置/数据库/模型版本摘要文件>",
  "sampleRef": "<实际输入及版本，明示simulated或真实许可>",
  "result": "PASS",
  "exitCode": 0,
  "artifactPath": "<仓库内证据路径>",
  "sha256": "<实际制品指纹>",
  "observedAt": "<带时区实际时间>",
  "reviewerRef": null
}
```

证据类别为DESIGN_REVIEW、REPOSITORY、SIMULATED_ENGINEERING、REAL_READ、REAL_ACTION、MODEL_EVAL、SECURITY、OPERATIONS、BUSINESS_UAT。模拟输入下真实MySQL/事务/Worker可证明工程行为；Mock API/模型不能证明企业接口/模型效果；写入需REAL_ACTION且对应动作范围。NOT_RUN/FAIL/不适用不能冒充PASS；无需某测试须有明确理由和评审，不能删掉验收项。

## 增量接手与结束流程

接手先按AGENTS的入口顺序读；如果仓库存在，执行 `git status --short --branch`、`git rev-parse HEAD`、`git diff --stat`，再读取目标任务及直接依赖的acceptance/evidence。比较HANDOFF.baseCommit（或最新交接记录基点）到当前HEAD的文件变化，重点读允许目录、相关契约/ADR和失败测试；只有基线变更/范围新增/证据失效才扩大阅读。

可用 `python docs/planning/render_status.py --task M1-001` 直接提取单任务，不需全读台账。主任务未分配时看生成视图的候选列表，不能自动领取未经授权的任务。进度询问只重建视图，聊天中的“做完了”不能改台账。

任务结束必须更新TASKS本条及history、HANDOFF或新的任务交接记录、必要ADR与生成视图。HANDOFF只记录本次做了什么、剩什么、哪些测试真实执行、下一步怎样接，任务状态以TASKS链接/生成区为准。新任务交接文件按真实需要才创建：`docs/handoffs/<taskId>/<timestamp>.md`；本轮不创建96个空文件夹。

## 并行所有权与冲突恢复

| 对象 | 规则 |
|---|---|
| 模块实现 | task.allowedPaths为最大写入范围，实际领取再缩小到文件；一文件一写入者；只读契约消费者可并行，不代表可同时改契约 |
| 共享契约/Schema | 先由契约负责人评审冻结；调用方锁定版本；变化写ADR并更新受影响任务，不能各造临时公共包 |
| migrations、bootstrap、依赖锁、TASKS | 集成人串行写；其他任务提交建议/独立变更包，由集成人合并；禁止两个Agent各改迁移头或台账同段 |
| 任务分支/工作树 | 实际仓库存在且确有任务后再安排；从批准基点建立；合并前复核base变化、接口兼容和集成测试；本轮不预建 |
| 脏工作区/未知修改 | 先归属识别和diff/指纹；保留他人文件，不reset/clean/自动stash；不能隔离时将冲突任务BLOCKED，列需合并/确认范围 |
| 合并冲突/测试失败 | 记录两个提交及冲突文件，按所有者裁决，修复后跑受影响契约与集成测试；不得直接用ours/theirs覆盖未知实现 |

## 中断与恢复矩阵

| 情况 | 先做什么 | 继续与结束条件 |
|---|---|---|
| 会话被打断，有commit | 读取TASKS和最新交接，核对HEAD/branch及相对基点diff | 重跑失败/未完成检查；不凭聊天摘要推断完成；继续原任务并保留记录 |
| 只有未提交改动 | 记录baseCommit、dirty文件/指纹、已做/未做和真实测试；能按授权提交WIP则提交，不能则WORKTREE_ONLY交接 | 新Agent先检查diff而非覆盖；未提交结果不ACCEPTED，不把台账中的旧testedCommit当覆盖新改动 |
| 测试失败/环境不可用 | 保存精确命令/退出码/错误摘要，区分FAIL和NOT_RUN；评估是否实际阻断 | 可修复则IN_PROGRESS；需外部条件则BLOCKED；不能用跳测改为PASS |
| 交接不完整/台账状态冲突 | 以Git实际文件/提交和证据重建最小事实，标不确定项，检查当前运行/未提交资产 | 证据不全不能ACCEPTED；先补交接/阻塞说明，无依据不删除结果或重做可能有副作用动作 |
| 已ACCEPTED但实现/证据变了 | 识别相关差异与消费者，开缺陷/重开评审，保留原接受记录 | 针对新版本补测试和评审；旧PASS不自动覆盖新代码 |

当前仅设计协议。CI最小规则见[CI_RULES.md](CI_RULES.md)，不部署项目管理平台、消息总线或独立协作服务。
