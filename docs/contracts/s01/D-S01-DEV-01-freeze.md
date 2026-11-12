# S01 双工作线共用契约冻结（2026-11-12）

基线：GitHub main `d6f9d70052e9d153daa68cef700913a21c8a633c`，主集成人 Codex。依据本轮负责人明确授权，冻结现有公开契约的消费范围，不改变业务规则、公共 Schema、依赖或迁移。独立验收仍由负责人和星星完成，本文不是业务签认。

- A 线只写 `docs/evidence/D-S01-DATA-01/` 的离线核对报告及证据；B 线只写 `src/commerce_hub/scenarios/s01_supply_inventory/`、`tests/integration/s01/`、专属单元/支持测试及 `docs/evidence/D-S01-DEV-01/`。各自独立工作区/分支/提交。TASKS、HANDOFF、DECISIONS、组合根及公共 API 由主集成人单一写入。
- 数据输入沿 `data.contracts` 的工程 FixtureInput、Mapping、Policy；固定 D01 FixtureConnector → D02 project → D03 capture，D03 是唯一 manifest。原 SKU-A 阅读别名无法还原真实标识，禁止映射成工程 fixture。A 线不修改数据契约或代填业务值，B 线只接显式 SIMULATED_ENGINEERING、SINGLE、单 SKU、quantity 范围。
- B01 是唯一确定性指标实现；B02 propose 构造候选并调用 B01，沿现有版本/质量/日期/MOQ/独立倍数边界。Handler 不重算或改写其返回结果，不把工程候选变成真实采购适用。
- 新 Handler 使用现有 ScenarioHandler.validate/run、DomainResult 0.1.0，以及既有 report_view/validate_result 扩展点。O01 唯一拥有任务、预算、计划、发布、重入与报告；复用原 create/read/cancel/report/evidence API，新增 options 仅返回获准的工程参数能力，不暴露输入明细。新分析沿现有新任务和独立报告引用，不覆盖旧报告。
- 模型仅经 A01 ModelGateway 和现有 S01Bundle/Explanation 四数组/ModelRequest 0.2；仅 MockProvider，网络关闭。Context 只包含已计算产物的最小事实、合法证据及缺失/限制，绑定 tenant/task/plan/participant/snapshot 与精确版本。supportRefs 须存在于本次白名单；结构通过仍须领域事实保持校验。无法证明正确的自由文本应降级，禁止使用关键词黑名单宣称通用语义证明。
- 语义校验须拒绝错数、错日期、错约束、质量放行、采购批准及伪造引用；可采用受控事实文本/模板的严格允许集，明确工程适用范围与局限。A01 失败/拒答/结构失败/语义失败均显示 AI 解释不可用，合法规则报告仍保留。取消、过期、失 lease、旧 plan 在 A01 前后及 O01 发布边界检查；迟到只核账不发布。重入不换 logicalCall/attempt 绕过原预算，不自动重试。
- 公开报告沿 quantity DTO 和当前 G01 重鉴权，内部 projection/manifest 不泄漏；D04 只解析公开证据。AI 的说明与技术/版本/来源状态可公开，原始请求、Provider 内容、私有标识及秘密不公开。
- 四项真实准入继续 BLOCKED；LIVE/C-04、真实 DeepSeek、ERP认证/网络读取、采购写入、UI及其他业务模块均不在本轮范围。A 线只用已获准文档/本地材料，零新 ERP 请求。真实 MySQL/API/独立 Worker 工程验证只用原隔离库 `s01_a01_test_20261112` 和本机获准配置。

验证出口：两线各提交实现和离线/工程证据；主集成固定实现提交后运行原 A/B/C-01 全部测试与新增 Handler/API/Worker/权限/异常回归、pip check、compileall、默认关闭连通入口、文档 build/check 和 diff 检查；互审是工程交叉审查，不能冒充负责人/星星独立验收。D-S01-DEV-01 最终 REVIEW，数据/规则/ERP/AI 门禁保持原状态。
