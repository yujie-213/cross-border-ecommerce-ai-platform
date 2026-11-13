# S01 后端 API 前端对接契约

版本：2026-11-12
适用场景：`S01_BACKEND` 只读分析。本文按当前 HTTP schema、路由和服务实现整理；不开放采购审批、采购执行或 ERP 写入。

## 1. 对接原则

### 2026-11-13 在线模式兼容增量

显式在线装配 `commerce_hub.bootstrap.s01_online` 注册相同 `S01_BACKEND/0.1.0`。options的在线选项返回 `choiceRef`、`inputMode=ONLINE_TEACHING_ERP`、精确scope、`asOf=null`；选项只是服务端授权映射，API不联网查数。SKU选择限定最多20个已配置映射，Worker重新核实来源身份；不支持无界商品搜索。

创建在线任务的 `parameters` 为 `{"inputMode":"ONLINE_TEACHING_ERP"}`，不传packageRef、源事实、路径或规则。原固定包请求不变，只有显式配置固定目录才可用。在线任务永不回退固定包。新命令新采集；同key重放原任务。受理事务不等待ERP网络；Worker在锁外采集，短事务复核身份、租约、plan及期限后，D01提交采集回执、D03保存不可变输入。已完成采集在恢复中复用；未完成尝试保留INTERRUPTED、最多两次采集尝试。旧租约及取消后不可提交/发布。

在线公开报告新增 `dataReport.acquisition`：采集ID、请求范围、开始/完成时间、接口覆盖/错误/条数/摘要、映射版本和多接口非原子限制；`observedDomains`提供有依据的原字段观测，语义未确认不能视为净可售。manifest、规范化内部输入和原始敏感响应不公开；历史读取不访问ERP，固定到原snapshot。报告技术成功与业务BLOCKED/PARTIAL分别展示。`scenarioSupplement.inputMode`区分在线与固定来源，在线报告无需packageRef。

- 前端先调用 options，使用服务端返回的 `packageRef` 和精确 scope 创建任务。浏览器不能提交 ERP 原始响应、文件路径、来源签认或业务规则。
- 任务技术状态、报告完整性、AI 可用性和采购适用性是四个独立维度，不能合并成一个“成功”状态。
- `state=SUCCEEDED` 只表示任务完成且报告已发布。它不表示 `completeness=RULES_ONLY`、AI `AVAILABLE`、真实业务准入通过或可以采购。
- 当前所有候选的 `procurementEligible=false`。前端只能展示和复核，不能出现“下单”“批准采购”或外部执行入口。
- 所有 DTO 都是精确字段集合。前端应忽略未来新增的可选显示字段，但不能自行补算库存、缺口、候选量、日期、费用或质量结论。

## 2. 认证、命令头和通用错误

API 使用受信身份。服务端接受 `Authorization: Bearer <token>`，也支持由 `POST /api/v1/session` 建立的安全 Cookie 会话。Cookie 会话执行 POST/DELETE 时还需匹配 `Origin`、`commerce_csrf` Cookie 和 `X-CSRF-Token`。

创建与取消必须携带：

```http
Idempotency-Key: <1..128 chars>
```

同一主体、同一 key、同一内容返回原结果；同 key 改内容返回 `COMMAND_CONFLICT`。通用错误体：

```json
{
  "code": "POLICY_DENIED",
  "message": "Authentication or current authorization rejected",
  "details": null,
  "traceId": "<trace-id>",
  "retryable": false
}
```

前端至少处理：

| HTTP | code | 含义与前端处理 |
|---|---|---|
| 401 | `UNAUTHENTICATED` | 未登录、Token 无效或 Bearer/Cookie 冲突；响应清理无效会话/CSRF Cookie，回到可信身份连接，不回显凭据；重新连接仍需有效 Bearer。 |
| 403 | `POLICY_DENIED` | 当前主体无该 scope/action 权限；隐藏资源详情，不把它当作资源不存在的证明。 |
| 403 | 其他授权拒绝码 | 当前授权已撤销或范围不匹配；停止轮询和后续命令。 |
| 404 | `NOT_FOUND` | 资源不存在、跨租户、无读取权限、持久化绑定无效或证据不可解析；统一显示“不可访问或不存在”。 |
| 404 | `REPORT_NOT_PUBLISHED` | 任务尚未成功发布报告；继续查任务状态，不重建假报告。 |
| 409 | `COMMAND_CONFLICT` | 幂等 key 被不同内容复用；生成新 key 前必须确认这是新用户命令。 |
| 409 | `REVISION_CONFLICT` | 取消使用了旧 revision；重新读取任务并让用户确认当前状态。 |
| 409 | `TASK_TERMINAL` | 已成功、失败或终止，不能再取消。 |
| 422 | `INVALID_REQUEST` | HTTP schema 不合法，包括缺字段、额外字段、非法 limit/revision。 |
| 422 | `INVALID_PARAMETERS` | packageRef、scope 或 previousReportRef 与服务端目录不匹配。 |
| 422 | `UNSUPPORTED_SCENARIO` | 当前装配未注册该场景。 |
| 422 | `INVALID_HISTORY_QUERY` | history 的 scenario/limit 不受支持。 |
| 503 | `IDENTITY_NOT_CONFIGURED` | 服务未装配受信身份。 |
| 503 | `AUTH_BACKEND_UNAVAILABLE` | 授权后端不可用；可按产品策略稍后重试。 |

## 3. 获取可分析选项

```http
GET /api/v1/s01/options
GET /api/v1/s01/options?storeId=store-1&warehouseId=wh-1&canonicalSkuId=sku-1
Authorization: Bearer <token>
```

筛选参数可省略；服务端只返回当前主体对 `tasks:create` 有权限的固定包。响应示例：

```json
{
  "scenarioId": "S01_BACKEND",
  "scenarioVersion": "0.1.0",
  "analysisMode": "SINGLE",
  "inputMode": "SERVER_PACKAGE_REF",
  "mappedChoices": [
    {
      "packageRef": "<sha256>",
      "sourceMode": "SIMULATED",
      "scope": {
        "tenantId": "tenant-1",
        "storeIds": ["store-fixture"],
        "warehouseIds": ["warehouse-fixture"],
        "canonicalSkuIds": ["sku-fixture"],
        "fields": ["quantity"]
      },
      "asOf": "2026-11-12T00:00:00Z",
      "sourceNature": "SIMULATED_ENGINEERING"
    }
  ],
  "limitations": [
    "READONLY_ANALYSIS_ONLY",
    "SOURCE_AND_RULE_ADMISSION_PER_PACKAGE",
    "LIVE_AI_EVALUATION_SEPARATE"
  ],
  "maxModelCalls": 1,
  "actions": ["analyze", "read", "cancel"]
}
```

`sourceMode` 可能为 `SIMULATED`、`OBSERVATION`、`ADMITTED` 或 `TEACHING_SIMULATION`。`OBSERVATION` 是只读教学 ERP 观测且保持阻断；`ADMITTED` 只有服务端来源与规则准入包通过时才能计算。`TEACHING_SIMULATION` 是经真实 API 写入并独立回读的仿真数据，来源为 `SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP`，只按明确版本教学规则验证。options 的存在不代表企业正式业务验收通过。

## 4. 创建分析任务

```http
POST /api/v1/analysis-tasks
Authorization: Bearer <token>
Idempotency-Key: 1d7f...
Content-Type: application/json
```

```json
{
  "analysisMode": "SINGLE",
  "scenarioId": "S01_BACKEND",
  "scope": {
    "storeIds": ["store-fixture"],
    "warehouseIds": ["warehouse-fixture"],
    "canonicalSkuIds": ["sku-fixture"],
    "fields": ["quantity"]
  },
  "parameters": {
    "packageRef": "<options.mappedChoices[].packageRef>"
  },
  "previousReportRef": null
}
```

服务端从身份写入 tenant，前端不得在请求 scope 中传 `tenantId`。响应为 `202 Accepted`，并带 `Location: /api/v1/analysis-tasks/{taskId}`：

```json
{
  "taskRef": {"tenantId": "tenant-1", "taskId": "<task-id>"},
  "state": "QUEUED",
  "revision": 1,
  "planVersion": "1",
  "reportRef": null,
  "scenarioId": "S01_BACKEND",
  "deadline": "2026-11-12T02:00:00.000000Z",
  "errorCode": null,
  "sourceNature": "NOT_YET_EVALUATED"
}
```

`previousReportRef` 用于“基于旧报告发起新分析”，不复制旧结论：

```json
"previousReportRef": {"tenantId": "tenant-1", "reportId": "<old-report-id>"}
```

旧报告必须属于同租户、同场景版本、同精确 scope，任务已成功、报告已发布且当前主体仍有读取权。无权、跨 scope、篡改或失效引用统一返回 `NOT_FOUND`。新任务有自己的快照、报告和 AI 调用；旧报告保持不变，旧候选或人工结论不能继承。

## 5. 查询任务状态

```http
GET /api/v1/analysis-tasks/{taskId}
Authorization: Bearer <token>
```

任务状态可为 `QUEUED`、`RUNNING`、`SUCCEEDED`、`FAILED` 或 `CANCELLED`。前端轮询建议：

- `QUEUED`/`RUNNING`：展示 deadline，继续有界轮询；`reportRef` 仍为 null。
- `SUCCEEDED`：仅当 `reportRef` 非 null 时请求 report。
- `FAILED`：展示 `errorCode`，不得假设报告存在。
- `CANCELLED`：停止轮询；迟到模型 usage 仍可能在后台核账，但不会发布报告。

## 6. 取消任务

```http
POST /api/v1/analysis-tasks/{taskId}/cancel
Authorization: Bearer <token>
Idempotency-Key: cancel-...
Content-Type: application/json

{"expectedRevision": 1}
```

成功返回任务 view，`state=CANCELLED`、revision 增加一次、`errorCode=CANCELLED`、`reportRef=null`。相同 key 和相同 expectedRevision 可重放；旧 revision 返回 `REVISION_CONFLICT`。取消不代表远端模型绝对未产生 usage，费用与 Token 状态由 G02 独立核账。

## 7. 读取报告

```http
GET /api/v1/analysis-tasks/{taskId}/report
Authorization: Bearer <token>
```

公开报告不返回内部 source package、projection、manifest 或 ERP 原始响应。主要结构：

```json
{
  "contractVersion": "0.1.0",
  "sourceNature": "SIMULATED_ENGINEERING",
  "completeness": "RULES_ONLY",
  "scope": {"tenantId": "tenant-1", "storeIds": ["..."], "warehouseIds": ["..."], "canonicalSkuIds": ["..."], "fields": ["quantity"]},
  "snapshotRef": "snapshot-...",
  "taskRef": {"tenantId": "tenant-1", "taskId": "..."},
  "reportRef": {"tenantId": "tenant-1", "reportId": "..."},
  "planVersion": "1",
  "scenarioId": "S01_BACKEND",
  "scenarioVersion": "0.1.0",
  "participants": [{"scenarioId": "S01_BACKEND", "snapshotRef": "snapshot-..."}],
  "dataReport": {
    "quality": [],
    "supplyDemand": {"baseline": {}, "candidates": [], "limitations": [], "selection": null},
    "reliableFacts": {"inventory": []},
    "scenarioSupplement": {
      "engineeringFixture": true,
      "procurementEligible": false,
      "realAdmission": "BLOCKED",
      "sourceMode": "SIMULATED",
      "packageRef": "...",
      "calculationStatus": "PASS",
      "previousReportRef": null
    },
    "evidence": []
  },
  "analysisReport": {"ai": {}}
}
```

`completeness`：

| 值 | 前端含义 |
|---|---|
| `BLOCKED` | 必需输入不足，确定性 baseline 不可计算。可展示 `reliableFacts` 和质量问题。 |
| `PARTIAL` | baseline 可计算，但质量或候选规则阻断候选。 |
| `RULES_ONLY` | 当前固定规则链已计算；不代表真实规则验收、AI 可用或采购适用。 |

`analysisReport.ai.status`：

- `AVAILABLE`：解释通过结构、引用和事实一致性检查，可以展示解释；它仍不能改变 B01/B02 数量、质量、`completeness` 或 `procurementEligible`。
- `UNAVAILABLE`：解释失败、超时、语义拒绝、发送状态不确定或已知用量超出额度；保留合法的规则报告。单独缺少费用或 Token 字段不构成解释失败。
- `NOT_ATTEMPTED`：该包或装配未启用模型。

AI usage 字段：

```json
{
  "usageStatus": "UNKNOWN",
  "tokenUsageStatus": "KNOWN",
  "costStatus": "UNKNOWN",
  "usageRef": "<g02-reference-or-null>",
  "usage": {
    "inputTokens": 1000,
    "outputTokens": 200,
    "totalTokens": 1200,
    "cachedInputTokens": null,
    "uncachedInputTokens": null,
    "actualCost": null,
    "currency": null,
    "pricingVersion": null
  }
}
```

- Token 字段为 `null` 表示 provider 未提供或该维度尚未核实，绝不表示 0。
- `tokenUsageStatus=KNOWN` 表示 input/output/total 都已知且一致；`PARTIAL` 表示至少一个 Token 维度已知；`UNKNOWN` 表示 Token 全未知；`NOT_SENT` 表示没有发送模型请求。
- `actualCost=null`、`costStatus=UNKNOWN` 表示费用尚未知，绝不表示免费。O01 会继续保留相应费用额度，后续真实账单可补充一次。
- `usageStatus=KNOWN` 仅在 Token 与费用都完整；正常响应可以出现 Token 已知、费用未知，此时 usage 已记录但 `usageStatus=UNKNOWN`。
- `usageRef` 是持久 G02 使用事实引用。它可以在部分 usage 已记录时存在；null 表示没有可持久引用，不能据此推断费用为 0。

## 8. 读取证据

报告的每项 evidence 包含 `evidenceId` 与受控 `fieldPath`。解析：

```http
GET /api/v1/analysis-tasks/{taskId}/evidence/{evidenceId}
Authorization: Bearer <token>
```

响应是该公开报告内可解析的最小字段值，例如 baseline 或候选评价。它不是源系统下载能力。无权、报告未发布、ID 不存在或历史绑定无效返回 404；前端显示“证据不可访问或不存在”，不能暴露内部路径或尝试猜测 ID。

## 9. 历史查询

```http
GET /api/v1/analysis-tasks?storeId=store-fixture&warehouseId=warehouse-fixture&canonicalSkuId=sku-fixture&scenarioId=S01_BACKEND&limit=20&before=<task-id>
Authorization: Bearer <token>
```

响应：

```json
{
  "items": [
    {
      "taskRef": {"tenantId": "tenant-1", "taskId": "..."},
      "state": "SUCCEEDED",
      "revision": 2,
      "planVersion": "1",
      "reportRef": {"tenantId": "tenant-1", "reportId": "..."},
      "scenarioId": "S01_BACKEND",
      "deadline": "...Z",
      "errorCode": null,
      "sourceNature": "NOT_YET_EVALUATED"
    }
  ],
  "nextCursor": null
}
```

history 只返回当前精确 scope 和场景的任务索引，不返回 parameters 或内部资产。`limit` 为 1—50；传 `nextCursor` 到 `before` 获取下一页。历史 view 的 `sourceNature` 不是最终报告来源判定，详情页必须读取 report。

## 10. 前端页面映射

依据当前 PRODUCT_SPEC，正式前端可按以下方式消费：

- 新建分析：options → 选择固定店铺/仓/SKU/package → create。
- 当前任务卡：status 轮询；运行中开放 cancel，终态停止。
- 建议详情：report 的 baseline、candidates、quality、limitations、reliableFacts、AI explanation。
- 数据/质量阻断：使用 `completeness`、quality 和 limitations；不得把未知显示为 0。
- 证据与版本：evidence、snapshotRef、reportRef、planVersion、scenarioVersion。
- 历史报告：history；“重新分析”将旧 `reportRef` 作为 `previousReportRef`，不继承旧批准或结论。

当前后端没有采购建议草稿、人工审批或外部执行 API。原型中的这些交互仍是会话演示，正式前端不得连接到不存在的写接口。

## 11. 本地独立 API / Worker 启动参考

`commerce_hub.bootstrap.s01_backend` 要求显式 test/offline 配置、固定服务端 catalog、mock/off 模型模式；启动时不访问 ERP 或模型网络。先设置本机授权数据库和身份环境，以及：

```powershell
$env:COMMERCE_ENVIRONMENT='test'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
$env:COMMERCE_S01_CATALOG_PATH='D:\path\to\server-catalog.json'
$env:COMMERCE_S01_EXPLANATION_MODE='mock' # 或 off
$env:PYTHONPATH='src'
```

独立 API：

```powershell
.venv\Scripts\python.exe -m uvicorn commerce_hub.bootstrap.s01_backend:create_app --factory --host 127.0.0.1 --port 8000
```

独立 Worker：

```powershell
.venv\Scripts\python.exe -m commerce_hub.bootstrap.s01_backend worker
```

catalog 是受信服务端配置，不能由浏览器路径或请求体指定。真实 DeepSeek 评测使用独立受控评测装配，不通过当前 mock-only backend 启动入口偷偷开启网络。


## 结构化解释与证据生命周期增量（本轮UI/C04修复）

HTTP路由、Cookie/CSRF、权限、text/supportRefs Schema均不变。自然用途新Prompt controlled-2 / s01-controlled-natural-v2：单条解释一个当前事实的唯一supportRef，text匹配该事实受控短语，可不含重复[ref]；事实章节、必需覆盖、数字日期、未知、质量及采购边界继续校验。不是任意自然语言事实证明。旧controlled-1及摘要按原策略重建，历史报告不升级/回写。前端已有“依据”展示来自supportRefs，与模型是否写文内标记无关。

证据读取绑定当前taskId、reportRef、任务读取代次、证据请求代次及会话上下文；切换/关闭/失权立即清空、取消，迟到成功、错误、finally不能覆盖当前状态。不缓存报告/证据。未增加证据API或采购能力。详细决策见ADR-S01-UI-C04-002。

## 在线业务准入增量（阶段2）

在线规范化区分TECHNICAL、SOURCE_DATA和BUSINESS_RULE缺口。当前授权映射不等于已确认净可售、未来曲线、供给可售日、MOQ独立倍数或质量清晰。普通观测只能调用B02的既有质量前置阻断，不调用B01编造数字。已确认身份域的原库存字段单独展示，不能冒充已签净可售。

只有当前联网事实和明确教学规则都满足的teaching-s01-rules-v1路径，才规范化为现有AdmittedInput并调用D02→D03→B02/B01；七条指定历史销量重放为教学假设，独立倍数6、D7可用日及最大120是教学规则，绝不从箱规/交期自动推断。当前真实教学批次店铺0失配、草稿状态不可识别，不能启用此正向路径。其余SKU缺少已签规则，保持UNKNOWN/BLOCKED。快照v2记录规范化摘要、实际接口错误、源数据过期/时点和质量版本；v1历史仍按原版本读取。
