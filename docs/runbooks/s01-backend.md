> 日常使用增量（2026-11-14）：当前默认入口为[Windows一键启动与管理员登录](local-platform.md)及[README](../../README.md)。下文保留原阶段/开发测试运行方式；临时Token、动态端口和900秒演示不再是日常流程。本地loopback HTTP Cookie例外以新契约为准，旧测试配置保持其原安全语义。

# S01 后端固定包运行与复验

本入口只做只读分析；不提供采购批准、下单或库存写入。状态以 TASKS 为准。正式前端未开发。

本机使用 `.env` 注入既有隔离 MySQL 与可信身份设置，不打印或提交秘密。数据库固定 `s01_a01_test_20261112`，先显式迁移：

```powershell
$env:COMMERCE_ENVIRONMENT='test'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
python -m commerce_hub.infrastructure.database
$env:COMMERCE_S01_CATALOG_PATH='<本机固定JSON包目录文件>'
$env:COMMERCE_S01_EXPLANATION_MODE='off'
python -m uvicorn commerce_hub.bootstrap.s01_backend:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

另一个终端设置相同变量并执行 `python -m commerce_hub.bootstrap.s01_backend worker`。API 启动不迁移、不内嵌 Worker、不读取 ERP 或模型。目录文件为最多24项 `{kind,payload}` 数组，包含 `OBSERVATION`、`SIMULATED`、`ADMITTED` 或 `TEACHING_SIMULATION`；原响应及本机配置只放 Git 忽略私有目录。浏览器只能提交已授权 `packageRef`。显式 `mock` 解释模式只用于工程样例；默认 `off`。

`OBSERVATION` 保留真实观测时点、覆盖不足和未知语义，永远不允许直接计算。`ADMITTED` 先严格校验逐字段来源、完整性、规则及有效签认，再消费既有 B01/B02；TEST_ONLY 默认拒绝，开发者不代签。普通启动没有真实付费模式，评测只由独立、默认关闭的工具注入 Provider。

`TEACHING_SIMULATION` 通过 D01 `TeachingAdmissionConnector/read_pages` 接入既有正式 GET capture，再规范化到 D02、形成 D03 manifest 和质量判断。读取本机 capture 不算一次新的 ERP 网络请求。批次、写回执、独立 GET、scope、逐资源与逐字段摘要必须一致；教学规则和源值分别标注，不能把历史销量重放的预测日期说成 ERP 已确认需求。

教学数据工具默认 `NOT_RUN`，只有显式 `python -m tools.s01_teaching_dataset --execute-teaching-data` 才能访问固定教学地址。它不属于通用后端写入 API。保留私有 journal、每次发送前状态、请求摘要和独立回读；发送不确定先查询原记录，不能换批次重建。库存是可加总批次，场景使用同一自有记录按时点顺序更新并独立回读；旧快照保持原时点，不冒称当前库存。销售记录不支持删除，依靠独立批次保留隔离。

API 请求、状态与公开 DTO 见 [对接契约](../contracts/s01/backend-api.md)。任务 `SUCCEEDED`、报告 `completeness`、AI `status` 及 `procurementEligible` 是四个独立维度。费用 null 表示未知，不能在界面显示为0；AI 成功不要求费用已核算。

统一用量契约记录 `inputTokens/outputTokens/totalTokens`，缓存计数按能力可选；缺失为 null。G02 保留唯一调用事实，旧 `tokens` 是总数。0005 只追加 Token 分项并放宽空值，不重写历史。未知费用继续占预约，运输不确定继续 UNKNOWN 且全额占用；不能换 key 重发。后续权威事实在原 attempt 幂等补齐，冲突拒绝。取消/期限/旧计划/Lease 失效后只允许迟到核账，不能发布。

离线与隔离库复验：

```powershell
$env:COMMERCE_RUN_MYSQL_TESTS='1'
python -m pytest -p no:cacheprovider --basetemp=.tmp/s01-backend-check
python -m tools.s01_model_evaluation
python -m tools.s01_model_evaluation --offline-suite
python -m tools.s01_backend_observation_smoke
python docs/planning/build_docs.py
python docs/planning/check_plan.py
```

提交实现后运行 `python -m tools.verify_s01_backend`，生成绑定实际 HEAD 的全量证据，逐名保全原399项。真实 ERP 发现与模型评测另列，不计为离线回归网络成功。真实固定观测联调只有显式 `--run-real-backend` 才执行，它复放既有网络 capture，不再采集 ERP。

教学批次固定 GET capture 的9项 Golden 对照与5项独立进程复验，使用已提交的 `tools.verify_s01_teaching_golden` 和 `tools.verify_s01_teaching_backend`。精确命令、批次记录、UNKNOWN恢复及保留状态见 [批次重复验证手册](../evidence/S01-BACKEND/teaching-data/batch-runbook.md)。回归前应停止已确认属于本项目、无需继续运行的旧测试 Worker，避免它同时轮询隔离库；不停止其他项目进程。

有界模型评测使用同一个固定授权 task、最多5个 A—E 请求、总预算$1、每次保守预留$0.05，无自动重试。仅发送已计算并标明来源的工程或教学 quantity 事实和引用，不发送源 ERP 原响应。官方费率只用于该次授权上限预检，不作为平台计价或实际费用；无法预检则 NOT_RUN。输出四数组经过 Schema、引用、受控自然同义表述、未知与质量/审批门禁校验；不宣称能证明任意自由文本。原始返回只存 `data/private/`。再次运行不得更改授权 id、任务或 key 绕过已发送记录。

模型工具通过独立 `bootstrap.s01_model_evaluation` API 和 Worker 执行，固定授权派生租户、主体与命令 key；O01 的可选 `validate_command` 消费钩子拒绝换 key 创建第二预算任务，原场景不受影响。五例在同一个 task 预算内串行，首次失败停止剩余例，A 的合法规则报告仍可发布，评测 `analysisReport.evaluation.status` 单独显示失败。内部所有成功 case 的 G02 回执在发布和读取时核验；公开结果去掉源包、投影、manifest 和内部案例记录。固定600秒 task deadline、单次投递，不因工具重启恢复预算或期限。


## C-04结构化引用真实复验（2026-11-13收尾）

新明确授权、配置和脱敏结果见docs/evidence/C-04-STRUCTURED-LIVE/report.md。首轮C/D/E/A/B五次均通过。原旧授权/失败与记录仍保留；新任务独立主体/预算/命令/logicalCall，原教学包不改。普通S01_BACKEND仍只off/mock；此次为独立官方模型用途评测，不是浏览器在线模型启用。

默认不会付费：`python -m tools.s01_model_evaluation` 输出NOT_RUN。真实入口仅识别Git固定授权；需显式test/deepseek/network=true、官方base URL/model及本机Key、私有catalog/output、可信本地身份装配。已结束新任务的同command重放只能核对原结果，不能用作新调用。必要新复测须根据负责人当前授权登记新的具体授权/预算及定位理由，保留旧记录，不换key复活旧任务。

只核验既有结果：`python docs/evidence/C-04-STRUCTURED-LIVE/verify_readonly.py --verify`，仅在既有唯一隔离库SELECT并读取私有capture，逐条对照事实/版本/Token/G02及公开摘要；不发送模型/ERP、不写账。需原私有capture和获准本机.env。没有私有资料则NOT_RUN/缺失，不重新付费获取或伪造。
