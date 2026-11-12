# S01 业务 Handler 的工程装配与复验

本轮只交付 D-S01-DEV-01 工程范围，状态只读 [TASKS](../TASKS.md)。真实业务四门仍 BLOCKED；本轮不访问 ERP/真实 DeepSeek、不写采购、不接前端。资料准入结论见 [单 SKU 离线报告](../evidence/D-S01-DATA-01/admission-report.md)。

`S01SupplyInventoryHandler` 复用现有 D01/D02/D03/质量/B01/B02 链路，经 A01 调 Mock，最后形成 DomainResult。B01/B02 原权威结果保持不变。四类解释的 `s01-exact-facts-v1` 策略只接受本次最小事实的完整受控文本与引用集合，错量/日期/约束/质量/审批或引用会丢弃解释；这是工程允许集，不证明真实模型自然语言泛化，也不替代 C-04。

仅显式入口 `commerce_hub.bootstrap.s01_business` 注册 `ENGINEERING_S01_BUSINESS`；要求 environment=test、provider=mock、network=false，任一不满足拒绝装配。原默认应用仍不注册业务 Handler。服务端每任务最多一次模型调用、24000 token 预留、0.01 TEST 费用上界；沿原 O01/G02 预算与 usage，不新增账本或自动重试。固定 logicalCall/attempt 在重入时复用；已结算但结果未保存的解释降级 RESULT_UNAVAILABLE，SENT/UNKNOWN 继续保守占额。

仅用本机获准 `.env` 与唯一隔离库 `s01_a01_test_20261112`，不改本地文件或回显秘密。API 与 Worker 是独立进程，沿既有受权 JWT/会话和 quantity scope；身份配置缺失不绕过。手工工程演示使用原 `examples/s01_single_sku.json`，与原 SKU-A 无关。

```powershell
$env:COMMERCE_ENVIRONMENT='test'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
# 获准测试身份配置沿既有 G01，由本地配置注入；不要在终端回显。
.\.tmp\stage-a-clean\Scripts\python.exe -m uvicorn commerce_hub.bootstrap.s01_business:create_app --factory --host 127.0.0.1 --port 8000
# 在另一终端使用相同获准本地配置：
.\.tmp\stage-a-clean\Scripts\python.exe -m commerce_hub.bootstrap.s01_business worker
```

创建/查询/取消/报告/证据继续走原 `/api/v1/analysis-tasks` API。创建参数直接沿工程 FixtureInput，SINGLE 单 SKU；显式新分析可带顶层 `previousReportRef={tenantId,reportId}`，须同租户/场景/版本/精确 scope 且旧报告已发布、当前有读取权。关联参与幂等指纹，作为服务端保留元数据存入任务参数，传给 D01 前剥离；客户端直接注入 `_previousReportRef` 拒绝。新任务/报告引用独立，旧输入、预算、期限与报告不改写。读报告和建立关联都复核持久指纹和 SQL 归属；读取时仍按当前 G01 重鉴权。

`GET /api/v1/s01/options?storeId=...&warehouseId=...&canonicalSkuId=...` 只返回当前获准工程 scope 与能力；D02 目前没有服务端映射目录，`mappedChoices=[]`、`NO_SERVER_SIDE_MAPPED_CATALOG` 明示该限制，不能当真实映射可用。公开报告只含 quantity DTO、计算引用/公开 D04 证据、工程限制和经过校验的 AI 状态/解释；不返回内部 projection/manifest/源映射或 Provider 原文。

固定实现提交后执行：

```powershell
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
$env:COMMERCE_RUN_MYSQL_TESTS='1'
.\.tmp\stage-a-clean\Scripts\python.exe -m tools.verify_s01_dev
python docs/planning/build_docs.py
python docs/planning/check_plan.py
git -c core.whitespace=cr-at-eol diff --check
```

完整逐测试名、版本、命令/退出码和脱敏原始输出见 [固定提交全量证据](../evidence/D-S01-DEV-01/verification.json)。验证器不允许未提交的应用/测试/验证器改动；保全原 C-01 的全部 281 项名称，新增 Handler/API/独立 Worker、语义、降级、质量、重入、迟到、权限、关联/存储完整性和快照标识边界。pip check、compileall 和默认关闭的连通入口只证明工程状态；该入口本轮绝不带 `--execute`。证据先记录真实结果，最终 REVIEW 等待负责人和星星独立验收，互审不代签。
