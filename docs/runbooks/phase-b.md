# 第二阶段 S01 工程演示

本轮只交付显式 `SIMULATED_ENGINEERING` 切片。真实身份、ERP、业务口径和模型许可仍受原门禁约束；工程样例不是恢复原 SKU-A，也不是采购建议或业务验收。任务状态见 [TASKS](../TASKS.md)。安装和本机安全配置沿用 [第一阶段运行说明](phase-a.md)，需要 requirements.lock 中的开发依赖。

## 迁移与启动

以下命令在仓库根目录运行。仅使用本机 `.env` 已授权的 `s01_a01_test_20261112`，不写连接信息到命令行。API/Worker 不自动迁移。

```powershell
.\.venv\Scripts\python.exe -m commerce_hub.infrastructure.database
$env:COMMERCE_ENVIRONMENT='test'
.\.venv\Scripts\python.exe -m uvicorn commerce_hub.bootstrap.engineering:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
# 另一个终端，使用相同 test 环境和本机配置
$env:COMMERCE_ENVIRONMENT='test'
.\.venv\Scripts\python.exe -m commerce_hub.bootstrap.engineering worker
```

唯一迁移链追加 `0004_reports`：新增 O01 所有的不可变报告表，报告、任务成功、审计及投递确认同事务提交。迁移禁止破坏性 downgrade。当前实测 MySQL Server 8.0.27；没有使用 SQLite。默认正式组合根仍不注册 S01；显式工程装配只在 test 环境启用，不接 ERP、模型或采购写入。

## 一条命令演示与测试

```powershell
$env:COMMERCE_ENVIRONMENT='test'
.\.venv\Scripts\python.exe -m tools.demo_s01
$env:COMMERCE_RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=.tmp/phase-b-pytest
.\.venv\Scripts\python.exe -m pip check
```

演示自动生成仅用于独立测试库的工程身份，启动真实 HTTP API 和独立 Worker，提交 [单 SKU 合成输入](../../examples/s01_single_sku.json)，等待持久报告并查询；最后停止自身子进程。密钥和短期令牌只留内存，不打印。手工提交需要 G01 当前有效身份/字段范围，使用既有任务 API 和 `Idempotency-Key`；工程 scenarioId 为 `ENGINEERING_S01`，scope 必须与输入的规范 SKU、店、仓及 quantity 字段一致。输入不能指定网络 URL 或文件路径。

查询：`GET /api/v1/analysis-tasks/{id}`、`GET .../{id}/report`、`GET .../{id}/evidence/{evidenceId}`。每次读取都重新检查当前租户/权限/范围；重复提交返回同一任务和报告。失败、取消、过期、失租约、旧计划和撤权不能发布报告。API 重启后直接查询原任务；Worker 重启继续原 task/快照输入/预算/期限，不重置许可。

预期演示：净可用 55，窗口需求 90，行级有效未收 20，缺口 15；MOQ/独立下单倍数取整得工程候选 20，基线首缺日 2026-11-20，候选末余额 5。所有数值由 B01 统一评价，B02 不复制公式；没有权重或最优推荐。AI 明示 `NOT_ATTEMPTED`，采购资格恒 false。

## 已知边界

D01 提供有限分页/重试只读端口及内联工程适配器；真实 ERP 网络适配与可信 TLS/数据绑定留待准入。D02 显式映射和精确单位换算，D03 唯一质量与 manifest，D04 从已授权报告定位证据。报告固定完整输入投影、规则/映射/指标版本和指纹，不宣称跨系统原子历史快照。

`engineering-demo-v1` 明确采用 UTC D0、次日起逐日需求、同日供给先入、负余额积压、缓冲日纳入目标；净可用不再次扣预留，需求已排除预留，未收必须行级 remaining 和可售日，箱规与下单倍数分开。上述均为获准工程样例策略，真实业务签认尚未完成。缺失/冲突/过期/覆盖不足拒绝计算或限制候选；质量未解决时可保留可信供需事实并禁止候选。

测试使用随机工程租户，保留测试资产，不清其他项目数据。真实 API/Worker 测试包含强杀恢复、同一报告只发布一次、跨租户和撤权拒绝。测试客户端仍有一条既有 Starlette/httpx 弃用提示，不影响结果；未为了消除提示擅自升级依赖。真实 ERP/模型/采购/生产验收均 NOT_RUN；本轮完成后等待复核及下一阶段授权。
