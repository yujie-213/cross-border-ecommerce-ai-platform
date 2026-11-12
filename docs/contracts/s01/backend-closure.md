# S01 后端闭环增量消费契约（2026-11-12）

基线 `e547335323fd19fccd324752dbeb1d08c9e21c2d`，分支 `codex/s01-backend-closure`；fetch 后 main=`b1813e5`、ERP评审分支=`e547335`，无远端漂移。负责人本轮完整任务授权包括有界教学ERP发现、规范化准入、规则计算、最多10次/$1真实DeepSeek、后端联调与对接材料；不含前端、采购写入、其他业务场景或自动合main。原未跟踪OpenAPI保留。

主集成人独占公共契约、组合根、HTTP/O01、迁移/锁、TASKS/HANDOFF/DECISIONS及最终提交。并行边界：

- 数据发现线：仅 `tools/s01_candidate_discovery.py`、`tests/unit/data/test_candidate_discovery.py`、`docs/evidence/S01-BACKEND/erp/`；使用已有Reader，不修改Connector/既有观测Handler。真实原响应只存忽略私有目录，最多20候选、优先3—5核验，先测全局接口。
- 模型线：仅新 `scenarios/s01/natural_explanation.py`、`adapters/models/evaluation.py`、`tools/s01_model_evaluation.py`、专属新测试和 `docs/evidence/S01-BACKEND/model/`；复用A01/O01/G02，未获主集成调度前不发真实请求，不改原严格Mock策略或公共Provider。
- 准入线：仅新 `data/admission/`、`tests/unit/data/test_admission.py`、`docs/evidence/S01-BACKEND/admission/`；新包契约和适配，既有B01/B02不复制。公共模型增量由主集成人集成。

固定服务端计算包包含精确scope、asOf、来源逐字段记录、规则版本和签认记录、规范化库存/逐日需求/逐行供给/独立约束/质量。四种性质明确：ERP_NETWORK、CONTROLLED_FACT、SIMULATED、UNKNOWN。包不可只改标签把工程Fixture变真实；真实模式拒绝任何模拟/未知必需事实或未签规则。受控事实须有来源/负责人/版本/时点，规则签认须显式用途和对应内容摘要；开发者不伪签。缺口可产生阻断报告，既有观测路径永远不可计算。工程样例使用独立SIMULATED_ENGINEERING路径。

核心复用D02 project、D03唯一capture、B01 evaluate、B02 propose；公共模型兼容追加AdmittedInput/AdmittedPolicy，保留旧FixtureInput/Policy字节语义与旧消费者。准入后的业务规则必须明确采用当前引擎的净可用、D1、日内先供给后需求、欠交累计、缓冲和逐日显式需求语义；不支持的规则拒绝。质量CLEAR须有有效签认，不以LLM解除调查。B02候选仅分析，采购适用保持false，等待业务独立审查。

模型Context只取已计算的quantity事实与本次白名单引用，四类Explanation结构保留。自然语言策略将自由说明与权威结构分离：机器可验证的事实引用/数量/日期/限制约束，以及自然语言允许范围；无法证明一致的内容拒绝并降级，不宣称通用语义证明。真实请求需要官方现行价格/模型预检、持久化同一授权总额/次数控制、每次独立O01原预算和G02核账。输入/输出/总Token按Provider Adapter统一映射，缺失null；缓存维度可选。actualCost/currency/pricingVersion可null，解释成功独立于费用核算，UNKNOWN费用保留原预约且不当零。运输不确定保持UNKNOWN及全部预约；同logicalCall不盲发。官方费率只作本次$1发送授权预检旁证，不实现平台价格表、不把估算写成实际费用。调用失败不撤销合法计算。

无新调度/预算/报告平台或依赖。ADR-A01-USAGE-002兼容追加0005迁移，仅放宽原usage空值及追加Token分项，保全历史记录；无新表。新包只接受服务端固定Ref，客户端不能提交来源签认或路径。沿既有创建/状态/取消/报告/证据/关联；最小追加受权选项和历史查询，当前scope重鉴权。实际数据库仅`s01_a01_test_20261112`。离线、真实教学、受控事实、真实模型和故障证据分列，全部实现提交后固定HEAD复验，最终REVIEW，不代签ACCEPTED。


## 生效授权增量：教学API仿真批次

负责人新增允许机构教学ERP独立测试批次的普通API创建/必要更新/受控清理，覆盖本文件先前“采购写入禁止”中仅教学测试数据创建部分；真实付款/发货/采购提交审批/外部通知仍禁止。先读OpenAPI明确CRUD、副作用、店仓/租户、幂等和回读完整性。没有完整旧SKU则可新建批次SKU；只处理本批次记录，销售不可删时明确保留，不全局清理。

新增TEACHING_SIMULATION包与SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP来源；只读正式GET回读经摘要绑定后映射，写回执不代替回读。教学规则teaching-s01-rules-v1及独立Golden只适用于教学，不解除REAL_ANALYSIS正式签认门。数据线独占data/admission新增教学契约，ERP线独占tools/s01_teaching_dataset.py及专属测试/teaching-data证据，公共枚举/组合根/B01B02消费者仍主集成串行。原模型10次/$1总授权不增加；本地模拟、API写、API读、教学仿真计算、真实模型和独立进程证据分列。
