# S01后端API与WorkBuddy前端交接说明

2026-11-14；正式Vue未改。待负责人/星星评审并另行合main后，WorkBuddy基于最新main实施，不直接依赖未合分支当生产。本轮契约为contracts/s01/admission-runtime.md，质量结构版本s01-runtime-v1。只扩展既有响应，不建平行API。

## 现有端点

| 调用 | 用途/边界 |
|---|---|
| POST /api/v1/s01/v2/batches | 人工创建批量，Cookie/CSRF/Idempotency-Key，零模型/零业务写 |
| GET /api/v1/s01/v2/batches | 批量历史，旧结果仍可查看 |
| GET /api/v1/s01/v2/batches/{id} | 任务/来源完整度/覆盖率；处理完成不等于分析全部有效 |
| GET /api/v1/s01/v2/batches/{id}/items | 服务端分页筛选；新增质量字段随条目返回，PENDING尚无质量结果 |
| GET /api/v1/s01/v2/batches/{id}/items/{key} | 详情直接返回item，含完整新增结构；不公开ruleResult.input |
| POST /api/v1/s01/v2/singles | 单品新采集，既有AI开关受服务端授权，本轮不调用付费模型 |
| GET /api/v1/s01/v2/singles/{id} | 单品报告dataReport.item中相同字段，顶层snapshot是原不可变报告 |
| POST/GET /api/v1/s01/v2/singles/{id}/requisition | 原人工确认/幂等/ERP回读；新能力字段不取代服务端G01与复核 |

请求体、分页、现有状态/来源/排序未改；主数量quantity仍来自规则候选或唯一ERP参考。riskResult、referenceAverage、observedHistory都不能代替quantity传请购。

## 字段与状态

| 字段 | 含义/使用方式 |
|---|---|
| admissionVersion | s01-runtime-v1为新语义；旧报告无字段，展示历史版本，不能给它补新PASS |
| dataQuality.identity/demand/inventory/procurement | 分域status/reasons；VERIFIED、REFERENCE、UNKNOWN、BLOCKED、READY_FOR_REVALIDATION含义不能相互抵消 |
| demandWindow | windowStart/windowEnd为实际完整业务日区间，timezone/observationDays明确；validDays含真零，zeroDays、missingDays分别展示 |
| dailySales[] | KNOWN_SALES/KNOWN_ZERO/UNKNOWN/CENSORED；未知quantity=null，不画成0；不把“有效”解释为“有订单” |
| history/observedHistory | 前者已独立关联出库，后者只是ERP已支付已发货状态确认；后者可作参考，不算库存核验通过 |
| averageDailyDemand | 只有完整7日才有值；referenceAverage分母是观察到销量的日期数，并非7日SMA；referenceDenominator必须保留 |
| sampleStart/sampleEnd/sampleAgeDays/referenceGrade | 样本区间/陈旧程度；STALE_HISTORICAL显著标历史参考 |
| inventoryBasis | physical/available、observedAt实际读取、rowUpdatedAt源变更；checkpoint版本/水位/来源及originAt事实起点（区别于observedAt实际读取）；status/residual/historyStatus说明当前和历史不同边界 |
| capabilities | facts/reference/risk/rules/requisition，各enabled/reasons独立。不是阶梯升级；ERP参考可有独立人工请购路径 |
| riskResult | 原B01基线结果；缺报价时仍可存在，不能当采购候选。D1_AFTER_D0及当天余量未计限制保持 |
| recoveryHints[] | code/message/action；业务文案先展示，异常码/快照ID折叠到证据 |

requisition.enabled还结合自有部署范围；permissionCheck=G01_RECHECK_REQUIRED_AT_SUBMISSION表明当前会话/写权限/CSRF/最新报价/正式采购等仍须服务端复查。按钮不能只依据源数量或capabilities自行绕过后端；READ目录不代表获准采购。procurementEligibility保留原兼容语义（业务条件），不等于授予账号权限。

## 展示建议

列表主标签继续区分规则建议、ERP参考、无需补货、待核实；新的风险/趋势可作为副信息，不创造采购数量。详情先展示“最近7日，6个有效日，1日缺证据”，再说明“库存81件已核验，11/13是否零销量待确认”。若报价过期且销量完整，显示风险和趋势，采购区域提示报价需更新。

错误不能只显示STOCK_*。优先recoveryHints.message/action；例如“库存流水未完整获取，暂不能完成守恒核验”，保留查看历史/重新分析。新失败与旧成功并排按各自日期展示，禁止将旧数量自动填为最新结果。新FAILED返回统一UNKNOWN能力、demandWindow/inventoryBasis为null；旧FAILED缺版本正常按旧结构处理。

原型例子见docs/evidence/S01-ADMISSION/api-examples.json（纯隔离字段示例，不是ERP当下建议）。真实API/Worker/数据库验证见专项验证报告。新前端上线前覆盖旧报告、新参考、风险但不可采购、未知零、真实零、库存异常/源超时、ERP参考/重复建议、无0件候选及刷新恢复；本轮未做新Vue浏览器验收，也未重新付费AI或采购。

供给展示须把riskResult.inTransitQuantity标为“已确认可售在途”，不能称为“全部采购”。未证实可售日期/逐行剩余的采购仍在formalPurchases显示UNKNOWN，不能当0件采购；不计它们的风险是明确条件情景。
