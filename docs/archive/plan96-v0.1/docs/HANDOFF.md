# 项目接手入口 v0.1

日期：2026-11-11。本轮范围是开发计划和AI协作协议设计，下一步等待独立审查。本文件说明事实和接手方法；任务可变状态只在[TASKS](TASKS.md)，当前任务/候选/计数从[生成视图](generated/STATUS.md)读取。

## 当前任务与工作区

- 本轮交接任务：**M0-001**（规划及协议草案审查）；执行 `python docs/planning/render_status.py --task M0-001` 读取权威记录，不从聊天推断状态。
- 工作目录：`D:\电商项目\跨境电商智慧AI平台`。实际只读检查 `git rev-parse --show-toplevel` 与 `git status --short --branch` 均退出1，提示不是Git仓库；未执行git init、commit、建分支/工作树或上传远端。无HEAD/branch/baseCommit可填写。
- 观察证据：[initial-workspace-observation.json](planning/initial-workspace-observation.json)。当前管理产物是待初次入库的工作区草案，没有开发commit，没有ACCEPTED开发任务。
- 五份用户授权基线以用户确认的审查状态为准，正文未改，指纹见[baseline-manifest](planning/baseline-manifest.json)。不把旧页眉的“待复核”解释为重设计授权。

## 已形成的材料

已编制M0—M4初版96任务的定义/依赖/范围/验收/测试/风险，A/B两个M1验收节点及MC映射，B后S01专项设计/MVP路径，S01—S10/22候选覆盖，AGENTS及PLAN/TASKS/HANDOFF/DECISIONS职责和模板、状态/证据/提交/并行/恢复/CI协议。

本轮只创建AGENTS与docs内实际管理/文档工具/生成视图，不创建业务src、pyproject、migrations、应用测试树、部署文件或补货Agent。文件清单和实际文档检查分别见[FILES](planning/FILES.md)、[validation-report](planning/validation-report.json)。这些不是应用运行/MC/模型效果/企业接口验收。

## 未完成及不可推断的事实

规划尚待独立审查；Git根/白名单/权限、具体版本/驱动、节点A测试驱动、S02夹具、真实源样本/口径/岗位、权限/数据许可、质量/预算/时延、前端落点、两动作源保证、部署/RPO/RTO和实际评审人员仍待按DECISIONS与M0冻结。没有连企业系统、没有真实模型调用/压测/部署、没有业务开发测试结果。

“已完成编制材料”不等于其审查通过或相应工程任务已完成。TASKS里的plannedTests不是实际命令；真实执行只能写入证据记录。本轮实际检查命令为文档工具，输出以当前验证报告为准：

```text
python docs/planning/render_status.py
python docs/planning/check_plan.py
python docs/planning/render_status.py --check
```

## 下一位AI的最短接手路径

1. 读根AGENTS、本文件及STATUS；提取目标任务和直接依赖，确认本次用户是否已通过规划审查/授权具体任务。
2. 当前尚无Git，重查仓库状态，不凭此文档假定仍不存在。若仍不存在，只进行获准的规划审查/修订；M0-002仅在可保全独立审查签认和建仓授权下启动。它没有“先ACCEPTED M0-001”的硬依赖，避免建仓前提交证据死锁；建仓后把签认入库，再按真实SHA验收。
3. 仓库已存在时，记录当前HEAD/branch/dirty路径，对照最新交接的baseCommit和相关文件diff。未知未提交改动先保留，不reset/clean/自动stash。
4. 按任务baselineRefs只读相关基线章节/契约/ADR。工程初始化优先HLD§4.1—4.4/6/11/12，S01专项优先PRD§7.1、AI§14.1；A01/VOC优先AI§9.1/附录A/C；不全量重读无关内容。
5. 填实际assignee/范围/分支/基点并获得共享文件所有权后再实施。完成或中断时按COLLABORATION更新台账/交接/必要ADR，生成视图并留真实提交和测试证据。

## 后续每个任务的交接模板（按需创建，不预建目录）

```text
taskId: <稳定ID，状态请查TASKS，不在此重复存储>
author/role: <实际执行者>
baseCommit: <实际起点SHA；无仓库则null并解释>
implementationCommits: <真实提交或WORKTREE_ONLY及原因>
branch: <实际分支>
changedPaths: <仅本任务修改及他人改动的已知归属>
dirtyPathsAndHashes: <中断时未提交内容，不能假装被commit覆盖>
completedWork: <做成了什么/产物引用；不以此自动验收>
remainingWork: <未完成和风险，不写“无”除非核查过>
tests: <精确命令/环境/样本/退出码/PASS、FAIL、NOT_RUN/原始日志>
contractOrDecisionChanges: <ADR/兼容评审引用或明确无>
nextSteps: <接手后最初几条具体操作和所需资料>
blockers: <实际阻碍、责任方、解除证据，与TASKS本条关联>
evidenceRefs: <版本化路径/hash/testedCommit>
```

无Git/无提交/测试失败/交接缺失的恢复规则统一见[COLLABORATION](COLLABORATION.md)，不要在每次交接另写例外。当前没有业务运行需要持续看护；本轮结束后不自动启动实施。
