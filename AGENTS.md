# 项目协作入口

本项目当前采用 docs/PLAN.md 的 A—D 增量计划，S01 补货是第一个实施场景。旧96项草案已归档，不再是硬性路线。原M0—M4和MC01—MC12保留，实施顺序变更见 docs/DECISIONS.md；不得把S01测试冒充S02 MC验收。

## 接手与授权

1. 先读本文件、docs/HANDOFF.md、docs/TASKS.md当前任务及直接依赖，再读相关契约/决策和设计章节；不靠历史聊天、不默认重读全部文档。
2. 记录实际分支、HEAD、git status和未提交diff；未知改动先保留，不覆盖、reset --hard、clean、强推或擅自stash。
3. 项目代码/契约/计划/状态/证据以Git版本文件为准；ERP等仍为业务事实权威。生成进度视图只读，TASKS是唯一任务状态与验收台账。
4. 工具与模型不绑定。更换AI执行者不改变契约、验收、预算或权限；不要在规范中强制某模型/编码工具。
5. 最新授权（2026-11-12）为：读取本机.env获准连接，在s01_a01_test_20261112独立库验证MySQL/驱动兼容，必要检查后直接开发A-02最小骨架并测试/提交/普通同步GitHub。A-01原则与模块职责已获认可，普通字段/DTO/错误码由执行者依现有设计自主确定，不再逐项重复审批；真实数据安全、破坏性操作、关键业务规则及重大架构变化仍需负责人确认。四项业务安全门保持，不调用ERP/真实模型/采购写入，不自动开始A-03或业务Handler/正式前端。仅使用获准账号与目标测试库，权限不足即报告，不换库/绕过；秘密不输出/提交。保留既有origin与历史，不重写、不强推；早前仅文档/本地Git限制保留为历史事实。

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
