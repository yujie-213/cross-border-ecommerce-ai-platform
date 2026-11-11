# 关键实施决策与ADR模板 v0.1

状态：待独立审查。已审查架构按PLAN五份基线继承，不在此重新批准Python/FastAPI、模块化单体+独立Worker、MySQL、模块职责和场景默认Workflow。以下是**实施待冻结事项**，PROPOSED不是任务状态；任务状态只有TASKS中的五种。

| ADR ID | 事项与建议 | 关联任务/基线 | 状态 / 冻结门槛 |
|---|---|---|---|
| IMP-001 | Git根建议复用当前项目目录；初始白名单为五份基线+本轮AGENTS/docs，不git add .，不自动上传远端 | M0-001/002；HLD§16 | PROPOSED：确认仓库归属/访问/秘密排除/签认入库；本轮不init |
| IMP-002 | Python/框架/ORM/驱动/MySQL/OS及锁文件兼容矩阵 | M0-003、M1-002/003；HLD V01/V12 | PROPOSED：实际兼容/精度/事务/锁与许可结果，不用latest |
| IMP-003 | A采用测试专用HTTP装配调用既有I01持久工作项；不生产注册伪S02/报告/新任务平台 | M0-004、M1-008—010；HLD§4 | PROPOSED：契约/测试驱动冻结；B完成正式分析与全部MC |
| IMP-004 | S02夹具与P0数据权威、指标/单位/窗口/质量和领域降级矩阵 | M0-004/005/006/008；HLD V02—04 | PROPOSED：业务/数据责任签认与真实来源证据，Mock不替代 |
| IMP-005 | 企业/测试身份、字段/工具策略、云模型用途许可、地域/留存/删除 | M0-007、M1-004/032；HLD V08/V09 | PROPOSED：安全/数据责任人与适用条款证据；无匿名旁路 |
| IMP-006 | 任务/即席请求及周期额度、计价、期限/并发/重试/租约与质量/时延目标 | M0-008、M1-031、M2-013、M4-006；HLD V05/V13 | PROPOSED：真实规模/配额/未知用量/并发预留验证；初始领域并行2/重规划1保持 |
| IMP-007 | W01复用门户/前端目录与交互方案 | M2-008；HLD V12 | PROPOSED：真实门户/团队约束后决定；不作为A/B先决或默认React/Vue |
| IMP-008 | 两动作schema/岗位/有效期/源readPreconditions/原子条件/幂等/权威回执与撤销竞态 | M0-009、M3-001—012；HLD V06/V07 | PROPOSED：逐动作真实证明，不支持的动作关闭；不得以审批锁或模型解释补足 |
| IMP-009 | 部署位置/环境/凭据、容量、备份/恢复/RPO/RTO、回滚/值守 | M0-008、M2-014、M3发布；HLD V15 | PROPOSED：实际资源/恢复演练和发布窗口授权，不默认Kubernetes |
| IMP-010 | 模块owner/集成人/独立评审者/业务签认者与实际有效投入 | M0-001/010；FSR§8/10 | PROPOSED：人员指派、共享文件串行规则和评审责任签认；角色名不是已分配人员 |
| IMP-011 | TASKS唯一账本、C1/C2/C3证据策略、Git启动例外、CI最小检查 | M0-001/002；本轮COLLABORATION/CI_RULES | PROPOSED：独立审查后冻结；不建项目管理平台 |
| IMP-012 | Loop/多角色/缓存/框架/Memory/向量/图/队列/LLMOps按真实使用方评估 | M4-021；AI§8/9/11/15 | PROPOSED：收益/质量/隔离/成本证明后另建实施任务；当前暂缓且缓存OFF不建设施 |

## ADR最小模板

```text
id / title: <稳定IMP编号与具体问题>
owner / reviewers: <实际责任人，不写泛泛“团队批准”>
status: PROPOSED | APPROVED | SUPERSEDED
context / baselineRefs: <触发、事实和只读基线章节>
relatedTaskIds / consumers: <谁实现、谁被影响，状态仍查TASKS>
options: <备选、保持原方案的代价/收益及证据>
decision: <精确方案/范围/版本，不能只写“采用最新”>
compatibilityImpact: <公共契约、Schema、数据归属、权限、阶段影响>
validation: <真实实验/评测/许可/成本证据及未验证项>
migrationAndRollback: <迁移/兼容窗口/恢复，不能假设无损回滚>
approvalRecord: <审查者/实际时间/签认文件/被审实现或文档commit>
effectiveFor: <后续任务/环境/范围，不能静默改历史任务>
supersedes / supersededBy: <保留历史链，不重写旧决定>
```

架构/公共契约/阶段或动作范围变化必须先评估消费者、数据/权限/预算和验收影响，再由相应责任人审查，最后更新台账依赖/范围及版本。分支/不同AI不得各自发布不兼容“临时统一契约”。同一决策批准不代表关联工程任务ACCEPTED；代码、真实测试及阶段门槛仍需独立证据。
