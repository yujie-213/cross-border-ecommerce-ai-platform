# 教学测试批次与重复验证

批次 `S01-AI-TEST-20261112`，来源 `SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP`，规则 `teaching-s01-rules-v1`。本轮优先检查了已有商品，5 个候选均未同时满足完整需求、供给及正式规则准入，故建立独立教学批次。原有经营记录的 503、分页不完整和未知未收保持原结论，见 [调查结果](../erp/execution-summary.json)。

## 记录清单和保留状态

实际记录 alias、操作引用、原请求/回执/独立 GET 的摘要见 [批次证据](dataset-evidence.json) 及 [A](case-A-review.json)、[B](case-B-review.json)、[C](case-C-review.json)、[D](case-D-review.json)、[E](case-E-review.json)。原始 ID、请求、响应和发送 journal 仅在 Git 忽略的 `data/private/s01-teaching-dataset/S01-AI-TEST-20261112/`。

| 记录 | 本轮处理与检查 | 结束状态 |
|---|---|---|
| 自有商品和 Listing | 创建/必要更新，独立 GET 验证 SKU 唯一键及固定店仓关联 | 保留并以批次隔离 |
| 自有库存一行 | A=60、B=96、C=10 按时点更新同一行；各次独立 GET 与完整精确集合验证 | 保留；各场景使用相应时点 capture |
| 七个销售记录 | 数量 8/10/9/11/12/14/13；七个精确业务键回读，无镜像或重复 | API 不支持删除，批次隔离保留 |
| 自有采购草稿及明细 | 正式 GET 确认关联；未提交、审批或下单 | 草稿保留；教学计划供给独立派生 |
| 自有质量记录 | PUT 后 GET 确认 INVESTIGATE，检查数20/可用19/缺陷1 | 调查状态保留；不执行入库过账 |
| 多建的第二库存行 | 仅删除本批自有记录；GET 404 和完整精确列表0确认 | 已受控清理 |
| 一次商品更新超时 | 保持 UNKNOWN 后用原 ID GET 确认 APPLIED | 已确认；没有重新发送 |

批次基础证据含14项资源/集合证明，不代表14次总 HTTP 请求。C 的草稿事实另见 C 记录。库存字段的 `sourceUpdatedAt` 来自写回执与详情 GET 一致值；写规范摘要独立从已核验请求构造后与读值比较。

A 的空采购集合只证明教学规则指定的完整本批集合，不证明真实 SKU 所有未收为零。C 的草稿 ID/明细是 ERP 事实，OPEN、67件计划量和 D7 可售是教学规则派生。需求由七日销量按明确规则重放，非企业预测签认。D 四变体是 A 回读事实加教学规则复算；E-DATA 是离线缺数量反例，E-QUALITY 才有实际质量 PUT/GET。商品箱规没有被默认当订购倍数。

## 不新增外部请求的重复验证

在既有 Python 环境、原隔离数据库及本机私有 catalog 就绪后执行：

```powershell
$env:PYTHONPATH='src'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
.tmp/stage-a-clean/Scripts/python.exe -m tools.verify_s01_teaching_golden data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json
.tmp/stage-a-clean/Scripts/python.exe -m tools.verify_s01_teaching_backend data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json
.tmp/stage-a-clean/Scripts/python.exe -m tools.verify_s01_backend
```

第一条比较9项独立 Golden，第二条使用固定真实 GET capture 跑独立 API/Worker/MySQL、幂等、历史、前报关联、证据、重启及当前缩权验证；两者均不新增 ERP 或模型请求。第二条会在唯一隔离库创建新的工程任务，不清库。全量回归的 ERP/模型输入是离线 fixture，单独记录。

## 外部创建或恢复

`python -m tools.s01_teaching_dataset` 默认 `NOT_RUN`。已授权教学创建入口需要显式 `--execute-teaching-data`，分阶段参数见该工具 `--help`。现批次已完成，重复计算应使用上方固定 capture 命令；不要为复验重新执行创建或依次改写库存。

发送 journal 是恢复依据。已验证项先查询原批次/原记录；UNKNOWN 只查证，不换 key 或换批次重建。不得删 journal 来重置状态；销售不可删时继续保留隔离。清理仅限清单中能证明归属的自有记录，不进行全局清理。真实模型评测使用其原固定授权/task，重复运行也不得建立第二预算或绕过已发送状态，见 [模型准备记录](../model/readiness.md)。
