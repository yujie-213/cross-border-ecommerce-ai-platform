# S01 教学 ERP 接口调查与字段映射

版本：0.1 · 2026-11-11 · D-S01-ERP-01 · 调查与方案修订，非开发验收。

## 1. 结论与证据口径

教学服务可以通过负责人明确批准的 HTTPS `verify=False` 例外访问；它是**独立教学模拟 ERP，不是领星官方产品，也不是企业生产事实源**。OpenAPI 为3.0.3、文档/服务版本5.1.0，服务schema_version=5。健康响应的demo_mode=false不改变其教学系统属性。

本轮静态核对 **24 个操作**：19个业务查询、1个认证、1个健康、3个仅静态写入相关操作。实际认证2次，业务查询20次，覆盖16个不同业务查询操作；其中15个操作返回200，10个取得非空样本；1个REST销售订单查询返回503。**200或空数组不等于字段语义、历史覆盖或补货闭环已经通过。** 未调用创建、编辑、删除、审批或采购执行，写入操作调用数为0；未调用LLM、未开发业务代码或TODO。

原始依据为本地 `docs/ERP-openapi.yaml`，1,681,341字节，SHA-256：`15f7fd5da950860d1a84cb4dda038b7165fa493914c5eb42dd7b265f18b8e128`，含178个Path/252个Method操作。下文引用Schema名、字段路径与本地行定位，公开证据只保留结构与元数据，不复制原始响应或认证信息。YAML原文保持不变，作为负责人提供的本地调查输入，不自动随文档同步到Public仓库。

机器证据：[脱敏调查记录](evidence/s01-erp-survey-20261111.json)。该记录的operations以R01—R19、AUTH01、H01、W01—W03标识静态操作，businessObservations以R1/R2标识真实读取；参数只存名称，不存真实对象值。报告映射结论以本记录及所列Schema为依据，不以接口名称推断。

## 2. 环境、鉴权与最小调用边界

### 2.1 实际探测

| 证据 | 操作 | 实际结果与边界 |
|---|---|---|
| P01 | HTTPS `/lingxing-erp/healthz`，正常证书校验 | 自签名证书校验失败；未发送认证。不是接口401或业务失败 |
| P02—P05 | 负责人指定HTTP后检查带前缀健康、带/不带尾斜杠入口、根健康 | 4次404，无重定向，未发送认证；不能据此断言业务库为空 |
| P06 | 负责人明确改为HTTPS且verify=False后，GET健康 | 200，结构/服务版本如§1；禁止自动重定向。例外仅适用本次调查，不成为正式D01默认配置 |
| AUTH-RUN1/2 | `POST /api/auth-server/oauth/access-token` | 实际取得Token；仅在进程内存使用Bearer请求头，不把Token放查询串，不保存密码/Token/Cookie。首次业务读取因范围键不完整停止，第二次按明确限制继续 |

正常TLS探测失败与HTTP404均保留为过程事实。正式接入应配置可信CA/受控证书策略；本次关闭证书校验不能作为生产链路安全验收。临时调查工具位于本机临时目录，不是正式代码，不包含凭据，不入Git；凭据通过不回显终端输入，不写命令参数/文件/响应日志。

认证Schema要求JSON/表单中的`appId/appSecret`，含义是该教学系统已有账号与密码，不是官方app_key签名。响应声明`data.access_token/refresh_token/expires_in`，权限与行范围仍由服务端判定。全局声明Bearer或queryAccessToken二选一，**本方案只用Authorization头**，不采用URL Token。兼容接口`app_key/timestamp/sign`不进行官方签名验证，不能作为官方授权证明。（本地认证定义L2721；info/securitySchemes）

### 2.2 样本范围与局限

两轮各只发现1条库存；继续查询围绕同一SKU和仓库，每次limit/length=1。库存发现记录的店铺键未满足有效店铺绑定，故另选1个获准店铺作为需求查询范围，**没有据此认定该仓库存归该店铺所有**。相关采购/入库只读样本按选定仓库或原单引用限制；不宣称这些原单的每个SKU都与所选SKU相同。未保存真实店铺、仓库、SKU、订单、客户、地址、价格等值。

分页仅观察到REST的integer型total/limit/offset/page/pages、兼容接口total，以及选定库存scope的offset=0/1均为空；不证明全部分页稳定、删除水位或历史覆盖。无角色切换/故意越权试探，不把本次账号成功推广为其他角色有权。第一轮无回显输入工具在认证前终止，属本地工具失败，不计ERP认证请求。

## 3. 接口目录：声明与实测分开

### 3.1 共享约束

普通REST列表返回`{items,total,limit,offset,page,pages}`，items与total为文档必需，其他字段依契约；通常limit默认50、full最大200、offset默认0。`field/q/match=exact`明确要求有效业务字段完整等值；其他参数是否组合/是否精确，仍须实测。`date_from/date_to`在通用资源中多为无format字符串，不能据名称认定按订单时间、UTC或双闭区间过滤。

库存与销售的`view=report`最大2000，但文档明确“报表精简字段，不用于ODS采集”；full最大200。库存report缺主键映射字段，销售report的item_list仅声明sku，没有需求数量，不用它们做权威D02采集。兼容列表返回code/message/data/total等，可空；HTTP200后还需检查业务code和结构。

普通REST声明400/401/403/404/405/409；403的scope_denied是范围或无法安全映射，并非空成功。报价/评价还声明503。错误Schema存在ObservedLocalErrorEnvelope、BoundedWorkflowEnvelopeError和仅message的变体；D01应保留HTTP/业务码、分类错误而不把所有失败解析为空列表。**现场GET销售订单503未在该操作responses中列出，是实际文档差异。**

### 3.2 REST读取

下表各行均为GET，鉴权继承全局Bearer（报价/评价/退货显式Bearer）；只列S01关键参数，完整名称/类型/响应码见证据operations。

| ID / Path（`/api/v1/`前缀） | 关键请求与响应Schema | 本轮真实结果 |
|---|---|---|
| R01 `products` | field=sku/q/match=exact，limit/offset；Resource_products | R2-V04：200/1条，精确SKU检查通过；unit、moq、procurement_lead_days、default_carton_qty有类型，qc字段为空 |
| R02 `warehouses` | ids或warehouse_code/name/type；Resource_warehouses | R2-V02：200/1条，所选仓ID检查通过；不是仓库库存来源 |
| R03 `store-authorizations` | ids或platform/store_name/site；Resource_store_authorizations | R2-V00S/V03：200/1条，所选店铺ID可读；不证明等于其他接口sid的完整映射 |
| R04 `listings` | sku/store_name/listing_id或field/q/exact；Resource_listings | R2-V07：200/空；未取得所选店铺与SKU的Listing/MSKU桥接 |
| R05 `inventory` | wid/store_id、field=sku/q/exact、view=full、inventory_scope=fba/overseas/local；Resource_inventory | R1-V01/R2-V01：200/1条；按选定店铺+仓+SKU重查R2-V05/06为空，不等于库存0 |
| R06 `sales-orders` | store_name/shipping_warehouse、view=full、时间/状态字符串；Resource_sales_orders | R2-V08：503，未取得REST订单行或历史范围验证；不能填日需求0 |
| R07 `purchase-orders` | field=warehouse_name/q/exact、单号/状态/计划到货；Resource_purchase_orders | R2-V09：200/1条，仓范围检查通过；单头received/pending为int，supplier_id和planned_arrival为空 |
| R08 `supplier-deliveries` | purchase_order_sn/warehouse_name、limit/offset；Resource_supplier_deliveries | R2-V11：200/空；逐SKU送货/收货关系未验证 |
| R09 `inbound-orders` | 仓/采购单号/qc_status、limit/offset；Resource_inbound_orders | R2-V10：200/1条，仓范围检查通过；质检/可用/次品数量有类型，不等于未来可售日期 |
| R10 `suppliers` | ids或supplier_code/name；Resource_suppliers | 未调用：所读采购单supplier_id为空，不凭名称猜主键 |
| R11 `supplier-quotes` | sku/supplier_code/quote_no；history=1须quote_no；limit≤100；SupplierQuotePage | R2-V13：200/空。需costs/suppliers/products读取权限，文档声明店仓受限账号403，不能自动扩大权限 |
| R12 `customer-tickets` | field=store_name/q/exact、order_sn；Resource_customer_tickets | R2-V14：200/1条，店铺检查通过；不含已确认投诉类别/成熟群组分母 |
| R13 `customer-voice` | store_id、kind=reviews/feedback、日期、rating、visibility、history；items为宽松object | R2-V16：200/1条，含rating/business_date/store_id/sku字段；本轮未证明所选SKU成熟群组关联 |
| R14 `sales-returns` | order_id/state/q、limit/offset；SalesReturnRecord | 未调用：REST销售查询失败，未取得该路径获准原订单ID；不猜ID补查 |
| R15 `replenishment` | field=sku/q/exact、store_name、limit/offset；Resource_replenishment | R2-V20：200/空。即使有数据，也只能作为源建议参照，不取代B01/B02 |

### 3.3 兼容只读POST

这些操作的description明确说明本地只读查询，因此允许调用；“POST”不自动意味着写入，反之“模拟系统/不写官方平台”也不意味着写本地单据可以调用。

| ID / Method Path | 关键请求与响应 | 本轮结果与业务限制 |
|---|---|---|
| R16 POST `/erp/sc/routing/data/local_inventory/inventoryDetails` | LingxingRequest9：wid逗号字符串、sku为模糊搜索、offset/length（默认20，上限800）；Response9含product_total/valid/bad/qc/lock、third_inventory | R2-V17：200/空；分桶仍只有声明，不能据此套库存公式或相加三方镜像 |
| R17 POST `/erp/sc/data/mws/orders` | Request6：sid/sid_list、start/end_date左闭右开、date_type=1/2/3/10及其站点/北京时间/UTC语义、order_status/配送、offset/length（默认1000，上限5000） | R2-V19：200/1条，quantity_ordered/local_sku/seller_sku有类型；UTC日期字段实际为空，未验证完整历史窗口或店/仓/SKU归属全链 |
| R18 POST `/erp/sc/routing/data/local_inventory/purchaseOrderList` | Request4：order_sn数组、start/end双闭、search_field_time=create/expect_arrive/update、offset/length≤500；Response4单头与item_list各有数量/状态/日期 | R2-V18：200/1条；行级quantity_receive/expect_arrive_time为空，wid与数字status也为空；有单头总量不等于有每SKU未收供给 |
| R19 POST `/erp/sc/routing/restocking/analysis/getSummaryList` | Request3：sid_list、data_type/asin_list/msku_list、offset/length默认20上限50；Response3含库存/销量/建议 | 未调用：所选Listing/MSKU关系未取得；文档承认mode等有未实现范围，不能猜MSKU或把汇总建议作为权威计算 |

兼容契约的描述同时出现“未实现字段可接收但不生效”和“unsupported字段请求400”，存在保证强弱差异。D01只能启用逐一验证的参数子集，不宣称字段列在Schema中就必然生效。Response3的sales_avg/total_*、quantity_sug_purchase等即使非空，也缺少统一分母/窗口/算法证据，不能直接覆盖B01指标或B02候选。

### 3.4 采购草稿/审批仅静态调查

| ID / 操作 | 声明与无法据此证明的内容 |
|---|---|
| W01 POST `/api/v1/purchase-orders` | Resource_purchase_orders_Write，201；未知/只读字段400。通用CRUD不自动过账；status_text、received_qty、pending_qty为流程维护字段，不能通过CRUD伪造阶段。未证明其等同本平台获批“采购草稿”合同或支持C03 executionKey |
| W02 POST `/api/v1/workflows/replenishment/{id}/create-purchase` | 请求supplier_name/warehouse_name，描述重复提交复用来源单据；这只是教学本地动作的描述，不证明外部幂等期限、当前批准、跨对象原子条件或本平台执行安全 |
| W03 POST `/api/v1/workflows/purchase-orders/{id}/submit` | 可选空对象，提交本地采购审批，200/409/401/403；依然是状态写入，禁止本轮调用 |

三者调用数均0；其他修改/删除/批准/付款/收货/执行动作也未调用。是否将来支持C03需单独专项，不纳入本MVP。

## 4. 字段映射、真实空值与最小补充

“声明”来自Schema；“实测”只指上文样本的字段类型/空值，未保存原值。普通Resource字段几乎均nullable且无required，因此缺值合法，不可默认0。

| S01标准输入 | 来源字段 / Schema依据 | 本轮确认与映射规则 | 缺口处理 |
|---|---|---|---|
| tenant/SKU/单位 | products.id/tenant_id/sku/unit；inventory.product_id/sku；listings.sku/listing_id | 商品与库存主键/sku字段有类型，精确商品查询通过；店铺Listing为空 | D02需审核identity/mapping版本；不能只凭同名SKU或源id等于canonicalId |
| 仓与店关系 | inventory.wid/store_id/store_name；warehouses.id/type；store-authorizations.id/name；兼容sid | 仓与独立店铺可读，但发现库存店铺键不满足有效绑定；选定店铺库存查空 | 受控店—仓—SKU或共享库存使用策略须签认；不把另选店铺强绑库存，不把空结果当0 |
| 当前可售 | inventory.available/quantity；Response9.product_valid_num/product_total/bad/qc/lock | REST可售/总量int；兼容分桶未取到样本 | 可售净值语义、预留/冻结/不可售关系需确认；直接净额获准后不再扣一次，不能把quantity-available解释为已知reserved |
| 历史需求 | REST sales_orders.item_list为宽松object；Response6.item_list[].quantity_ordered/local_sku/seller_sku、purchase_date_local/UTC等 | REST503；兼容数量int/local_sku字符串，但UTC日期为空、站点时区/覆盖未实测 | 使用获准时间/状态口径和数据覆盖补充；未证完整日需求则阻断未来曲线。不能把amount当销量或用源日均值补未知 |
| 未收供给 | REST purchase_orders.received_qty/pending_qty（单头）；Response4.item_list[].quantity_plan/real/entry/receive | 单头int，RESTitem_list.quantity有值；兼容行级quantity_receive为null，supplier_id为空 | 需要每SKU状态/未收量及原单定位补充；禁止按比例分单头pending或重复减已收；采购/送货/入库同一供给不叠加 |
| 预计可售日 | REST planned_arrival；Response4.item_list[].expect_arrive_time；inbound qc_status/available_qty | 采购样本计划到货/行预计到货为空；入库质检有类型，但无未来可售日期 | 受控供给可售日/物流+质检规则与依据；到货≠可售，lead_days不能直接补成承诺日期 |
| MOQ | products.moq；SupplierQuote.minimum_quantity、version/有效期 | 商品moq int；报价查询空，无报价版本实测 | 确认适用供应商/SKU/单位与优先级；null/非正不默认为1 |
| 订购倍数 | products.default_carton_qty；Response4.quantity_per_case | 商品箱规int，采购行箱规空；无明确“订购倍数”字段语义 | 负责人提供独立倍数或签认箱规等同倍数的适用条件；不能自动等同 |
| 交期/额外硬约束 | products.procurement_lead_days；SupplierQuote.lead_days/minimum_amount/unit_price/currency | 商品交期int，报价空；采购日期无法验证 | 交期终点/日历/缓冲待签认；若报价最低金额约束适用，须B01金额评价或明确阻断，不因MVP不算金额而忽略 |
| 质量/投诉 | inbound inspected/available/defective_qty及qc_status；tickets.order_sn/subject；voice.rating/sku；SalesReturnRecord.quality_list（声明） | 入库/工单/评价有样本；质检标准字段为空；退货未调用 | 不将评价数/低星率/次品量当AC-04成熟投诉占比；受控质量信号、成熟分母/调查条件不具备则采购适用性阻断，不强制先做全S03 |
| 版本/时效/覆盖 | id/updated_at/created_at、兼容request_id/response_time、报价version | 字符串时间与分页结构存在，未证明历史asOf/增量/删除/排序稳定；行source_updated_at为空 | D01保存读取批次/逐域水位与限制；D02不可变投影；D03固定实际观测输入，不能伪称跨系统原子历史快照 |

关键本地定位：products L4552/Schema L38918；inventory L5438/Schema L42794；purchase-orders L6215/Schema L42929；sales-orders L7061；SupplierQuote L29430；Response9 L34677、Response4 L32302、Request6 L33215/Response6 L33307。定位对应上面的文件指纹，后续文件变化需重新核对，不能依赖永久行号。

## 5. 对 MVP 实施方案的影响

1. **选用真实读取教学ERP的窄适配层**，仍复用SourceConnector→D01批次→D02投影→D03质量/manifest→S01→B01/B02→D04→O01。产品/仓/店主数据与full库存可作为候选读取路径；需求可评估已实测兼容订单路径，REST销售503必须明确记录，不静默切fixture。
2. **当前不是“ERP核心数据已经齐全”**。店仓SKU映射、完整需求窗口、逐SKU未收量、预计可售日、倍数/约束、required质量等需要负责人提供获准受控补充；每项保留来源、版本、单位、责任人、有效期和证据。缺必要补充时只输出有依据的局部/规则/阻断说明，不能宣布完整可采购候选。
3. 教学ERP与受控补充可混合，但报告按数据域标来源，不能标“全部真实生产ERP”。fixture仍只供自动化测试/异常/离线备用，没有完整模拟系统实施要求。
4. **A01真实LLM解释成为MVP必须交付和真实验收的能力**，但模型失败不阻止已有可靠规则结果发布；失败显示“AI 解释不可用”。模型不得修正数据缺口、采购量/日期、质量门禁或审批。具体范围在原[实施文档](S01_MVP实施文档.md)和新ADR中落实，不另造网关。

## 6. 待决与实质差异

| 优先级 | 问题 / 差异 | 最小建议与影响 |
|---|---|---|
| 高 | 旧MVP写“可选A01”，与负责人本轮必做要求冲突 | ADR-S01-AI-001明确覆盖当前MVP范围；保持AI公共契约/其他场景默认选择与原专项正文不重写 |
| 高 | 教学源并非官方ERP；demo_mode=false不能证明企业真实 | 区分来源环境、读取方式与验证等级，验收不冒称官方/生产ERP |
| 高 | 库存店绑定、Listing关系未证；该店仓SKU查空 | 先签认共享仓使用/identity映射，不硬绑、不扩大scope凑数据 |
| 高 | 逐SKU未收量、日期、倍数/质量等不足 | 使用有责任和证据的窄补充或阻断；不新增一整套模拟数据产品 |
| 高 | REST销售503，兼容UTC为空；文档缺503/参数支持描述矛盾 | D01显式分类/限额重试、日期/参数逐项验证；无完整覆盖不产权威日需求 |
| 中 | 本次最小样本没有证明历史水位、全分页、状态全集、价格约束和角色矩阵 | 不关闭这些验收缺口；后续获准开发/验证时记录实际证据，不在本轮增加TODO |
| 中 | 自签名TLS与临时verify=False | 调查例外已获负责人明确指示，正式环境证书策略仍待确认，禁默认为verify=False |

## 7. 自检与停止点

静态24操作的Method/Path、参数、鉴权、响应Ref/字段、分页与错误已核对；实测16不同业务查询操作、15返回200、10非空样本、1个REST销售503。2次认证、20次业务查询、6次入口/健康探测、0业务写入。未得到样本的字段/接口和未验证的时间/状态/全量覆盖均如实列出，没有通过模拟或默认0填充。

报告与JSON只含公开契约、字段类型/空值、计数和错误元数据，不含密码、Token、Cookie或敏感业务值。MVP真实LLM/工程/完整业务/MC验收均NOT_RUN；本轮没有实现这些能力。文档检查、Git提交和远端同步结果由TASKS/HANDOFF记录。交付后停止，等待负责人评审。
