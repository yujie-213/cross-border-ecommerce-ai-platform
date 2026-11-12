# 项目协作入口

本项目当前采用 docs/PLAN.md 的 A—D 增量计划，S01 补货是第一个实施场景。旧96项草案已归档，不再是硬性路线。原M0—M4和MC01—MC12保留，实施顺序变更见 docs/DECISIONS.md；不得把S01测试冒充S02 MC验收。

## 接手与授权

1. 先读本文件、docs/HANDOFF.md、docs/TASKS.md当前任务及直接依赖，再读相关契约/决策和设计章节；不靠历史聊天、不默认重读全部文档。
2. 记录实际分支、HEAD、git status和未提交diff；未知改动先保留，不覆盖、reset --hard、clean、强推或擅自stash。
3. 项目代码/契约/计划/状态/证据以Git版本文件为准；ERP等仍为业务事实权威。生成进度视图只读，TASKS是唯一任务状态与验收台账。
4. 工具与模型不绑定。更换AI执行者不改变契约、验收、预算或权限；不要在规范中强制某模型/编码工具。
5. 最新授权（2026-11-12）覆盖第一大阶段剩余A-03/A-04/A-05/A-06：按现有计划/契约完成SQLAlchemy/Alembic、G01、API/独立Worker/任务预算与恢复、真实工程复验并提交/普通同步GitHub。允许契约明确且文件不冲突的并行工作，公共契约/迁移链/组合根/锁/台账由Codex主集成人串行协调。普通字段/版本/测试失败自行修复，不重复审批；仅破坏性数据库操作、关键业务规则缺失、重大架构冲突或无法安全解决时暂停报告。只用本机.env获准账号及s01_a01_test_20261112；不改其他项目库，不泄漏秘密，不换库/绕过。四项业务安全门不解除，不操作ERP/真实模型/采购写入，不开始第二大阶段、S01业务Handler或正式前端。保留origin与历史，不重写/强推；早前只做A-02/文档的停止点保留历史。

## 稳定边界

- O01统一任务/预算/计划/报告，通过ScenarioHandler调场景；Runtime只回RunOutcome，Handler形成DomainResult，YIELD不发布。
- D01只读接入，D02映射投影，D03唯一snapshot manifest，D04证据定位；跨模块只走公开契约，不私写表/共享ORM。
- B01唯一确定性指标；B02构造预测/候选/约束并调用B01评价；LLM不计算权威库存、金额和分母。
- 所有模型经A01；A03工具只读，不注册C03。确认/提交/独立审批/另行执行分开；UNKNOWN用原key核对。当前S01只读切片不开放外部写入。
- 预算/期限/usage/重试共享原task或受控query许可，恢复不重置；ModelRequest/ProviderRequest按AI详设v0.2 §9.1。
- 缓存OFF，不先建缓存设施；不默认Agent平台、全套LLMOps、Memory、Redis、MQ、Milvus、Neo4j或多Agent通信。
- 目录/迁移/依赖只为当前获准切片创建。API和Worker独立进程；MySQL短事务，网络在锁外，异步分支不共享Session。

## 状态、变更、并行与结束

状态和验收规则唯一在 docs/TASKS.md 开头定义。已完成开发不自动ACCEPTED；须真实提交、适用测试、逐项证据和相应评审。未运行写NOT_RUN，失败写FAIL，模拟工程验证不能写真实ERP/模型/生产验收。

领取时填写实际负责人/分支/基点/文件范围；不同AI不可并写同文件。公共契约、迁移链、组合根、依赖锁、TASKS由指定集成人协调；重要契约/架构变化先写ADR及消费者/兼容/安全/测试影响，获评审后才实施。

每次完成或中断都更新TASKS对应记录、HANDOFF的增量事实/未完成项/真实测试/提交，必要时更新DECISIONS，然后从TASKS生成状态。不要手写第二份完成率。无提交或交接不全时保留事实与阻碍，不虚造SHA或验收。

文档命令：`python docs/planning/build_docs.py`、`python docs/planning/check_plan.py`。真实开发测试按专项设计后冻结的命令执行。补充约定见docs/COLLABORATION.md；本轮结束后停止，等待下一条开发指令。

## 文档位置

分类入口为docs/README.md。五份正文位于docs/requirements、architecture、agents、reports；治理前原文字节快照与旧计划在docs/archive，旧路径对照见docs/governance/migration.json。业务状态仍只读docs/TASKS.md，公开准备与阻碍见docs/governance/PUBLICATION.md。
