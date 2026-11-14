# 跨境电商智慧 AI 平台

当前评审版提供简洁平台首页和独立的 **智能补货工作区**：仅分析登记核验的自有商品，逐仓预测需求、判断参考补充量，并与 ERP 建议对比。当前为 10 款商品、11 个店仓对象，保留原两款并新增 8 款受控教学商品。逐个体验请看[产品体验版场景与截图](docs/reports/S01_产品体验版使用与评审_20261114.md)；通用操作见[商品分析使用说明](docs/runbooks/s01-product-demand.md)。

后端为FastAPI、独立Worker、SQLAlchemy/Alembic/MySQL；前端为Vue3/TypeScript生产资源。任务、报告、采集证据、模型用量及请购操作持久保存。当前只提供一个本地超级管理员账号，不建设企业账号中心。

## 日常使用：双击即可启动

已完成本机首次配置后，在仓库根目录：

1. 双击 **[Start-Platform.cmd](Start-Platform.cmd)**。启动器检查配置、数据库/迁移、端口和依赖，启动API、独立Worker及前端服务，自动打开浏览器。
2. 使用账号 **admin** 和本机初始化时设置的密码登录。无需PowerShell多终端、动态端口或手工Bearer Token。
3. 首页进入「智能补货」，点击「检查自有商品」，按业务判断、SKU或店仓筛选；详情显示逐仓预测、参考补充量、采购候选和 ERP 对比。刷新当前店仓分析不调用AI；「生成AI解读」单独按需调用，近期任务中已有三份真实解读可直接体验。
4. 需要请购时核对采购事实、有效报价、MOQ/整箱，确认最终数量与来源限制后提交。平台确认不等于ERP领导审批，不下单/收货/入库。
5. 停止时双击 **[Stop-Platform.cmd](Stop-Platform.cmd)**，或在启动窗口按Ctrl+C/关闭窗口。只关闭本项目管理的进程，不终止占用相同端口的其他服务。

默认地址为 **http://localhost:5173**；API只监听本机8765。请使用启动器打开的localhost地址。启动窗口保持运行，无900秒自动关闭限制。默认登录会话为8小时，浏览器刷新、重新打开和服务重启在会话有效时自动恢复；退出/过期/本机重置后重新输入账号密码。

本轮本机评审实例为 **http://localhost:5175/#/home**、API8768，保持运行；最终状态 REVIEW，不合 main。本轮体验不执行真实请购提交、审批、下单或采购收货。

启动、登录和查看历史不创建分析任务，也不调用ERP、AI或采购写入。人工批量只读、零模型；新任务才采集最新事实。正常停止/重启保留历史和原请购幂等操作，不清库。

## 首次配置

需要Windows、CPython **3.13**、MySQL8/9、Node/npm。当前实测Node24.21.0/npm11.19.0；项目锁定Vite的Node要求为`^20.19.0 || >=22.12.0`。不是Docker部署，不要求Redis/MQ。

新克隆环境只需进行一次依赖安装（项目根目录PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
npm --prefix frontend ci
```

当前开发机启动器也兼容已有`.tmp/stage-a-clean`环境；新环境推荐`.venv`。不要提交本机配置或依赖目录。

按[.env.example](.env.example)创建Git忽略的`.env`，填写负责人提供的获准MySQL连接；**当前迁移保护仅允许`s01_a01_test_20261112`，程序不自动建库或换库**。ERP凭据使用既有本机`.env.erp`字段`ERP_USERNAME`/`ERP_PASSWORD`或`ERP_ACCESS_TOKEN`。没有获准账号时应由负责人提供，不能借用其他项目库或绕过来源权限。AI密钥只放本机`.env`的`COMMERCE_MODEL_API_KEY`；配置密钥不增加模型预算。

然后双击 **[Initialize-Platform.cmd](Initialize-Platform.cmd)**：

- 显式核对隔离库并前向升级至`0011_local_admin`，旧表/任务/报告不重置；日常启动不会执行迁移。
- 首次以隐藏输入设置并确认admin密码。密码只以随机盐scrypt哈希保存于数据库，明文不写源码、README、Git或本地配置文件。已有账号不会被初始化命令覆盖。
- 随机签名密钥和本机运行参数保存在Git忽略的`data/private/local-platform/runtime.json`，普通使用不需要复制其中内容或设置身份令牌。

本机忘记密码可双击 **[Reset-Admin.cmd](Reset-Admin.cmd)**，隐藏输入两次新密码。重置会撤销该管理员旧会话，保留任务、报告及采购记录；不操作ERP账号密码。该入口依赖本机文件/数据库控制权，不能用于企业远程账号管理。

本地配置的`sessionSeconds`默认28800，可设置300—86400，影响后续登录；`apiPort`/`webPort`可调整本机端口。更改后停止并重新启动。`modelEnabled`控制单品真实模型开关，`requisitionEnabled`控制已授权自有教学请购装配；关闭时界面明确提示，不回退伪造数据。运行中不要编辑或外传签名密钥。

## 已实现的业务边界

| 能力 | 当前行为 |
|---|---|
| 当前分析范围 | 版本化登记清单限定真实商品/店仓/库存/销售/报价ID；空清单不回退全租户。当前10款/11店仓，新增对象须登记核验；同SKU逐仓独立计算 |
| 手动批量 | 持久进度、取消、失败隔离、显式重试、历史、来源统计和风险分组；批量不调用AI、不创建采购 |
| 独立预测与比较 | 使用全部登记可信历史，不要求最新一天有销售；缺报价/MOQ仍可预测。参考补充量与采购候选分开，ERP没有建议也能分析；库存未知不伪造缺口 |
| 单品AI | 仅主动新建触发；解释绑定事实和未知，失败保留确定性结果；历史展示实际Token/费用状态 |
| 人工请购 | REFERENCE_ONLY本身不禁购；必要范围/报价/MOQ/整箱/待审及正式采购核对/人工确认仍强制；回读中、失败或UNKNOWN关闭提交，同业务对象换分析仍受保护 |
| 本地超管 | 拥有当前平台功能权限；**不扩大ERP业务授权**，共享SKU可读不等于可采购，现有自有教学范围控制继续有效 |

ERP内部算法、生成周期、日均窗口及在途/部分收货抵扣语义仍有UNKNOWN；未知可售日期的采购不作为有效供给抵扣。企业数据/规则/ERP安全/AI正式用途四门保持独立准入，当前不是企业生产安全认证或S01全部企业业务验收。S02—S10、完整RBAC/SSO及前端整体重构均未开展。

[V2业务交付与真实证据](docs/reports/S01_V2完整补货工作台交付_20261113.md)保留当时221SKU/975对象、真实AI及申请1426的历史观察；新批量以本次真实ERP结果为准。最新运行与合并验收见[本地产品化报告](docs/reports/S01_本地产品化与main验收_20261114.md)。唯一状态/验收台账为[TASKS](docs/TASKS.md)。

## 排错与恢复

- **配置或数据库不可连接**：核对`.env`、MySQL服务和获准账户。错误不会显示密码；原始本机工程日志位于`data/private/local-platform/`。
- **迁移未就绪**：显式运行Initialize-Platform；不要手工修改alembic_version、删表、清库或换库。
- **缺Python/前端依赖**：执行首次安装命令。启动器仅在源文件改变时自动重新构建前端，不自动联网安装依赖。
- **端口占用**：确认占用者属于谁，或调整本地端口；启动器不会按端口杀进程。重复启动已有本项目实例只打开现有页面。
- **密码错误/短暂锁定**：核对本机admin密码；连续失败会短暂锁定，必要时使用本机重置入口。数据库故障会明确提示服务错误，不跳转循环。
- **会话过期**：返回账号密码登录页。Cookie为HttpOnly/SameSite Strict，写命令保留CSRF；HTTPS使用Secure，本地loopback HTTP明确限定为非Secure Cookie，不可直接对外部署。
- **请购结果未知**：从原单品历史沿原操作核对，不换键盲发；已提交显示真实单号及原独立回读时点。重启不重置预算、报告或幂等记录。

完整[日常运行/迁移/登录/恢复手册](docs/runbooks/local-platform.md)提供配置和测试说明。

## 工程验证与文档

```powershell
$env:COMMERCE_RUN_MYSQL_TESTS='1'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
python -m pytest tests --basetemp=.tmp/review-fresh
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
python docs/planning/build_docs.py
python docs/planning/check_plan.py
```

真实ERP/付费模型/采购证据与工程夹具分开。旧[s01_frontend_dev](docs/runbooks/s01-frontend.md)、[s01_v2_dev](docs/runbooks/s01-v2.md)的临时Token、动态端口、900秒入口仅用于历史/开发测试，**不是日常启动流程**；默认仍保留，便于复验原证据，不应对外开放。

架构与公开契约见[文档索引](docs/README.md)、[本地启动/鉴权契约](docs/contracts/local-platform.md)、[A—D计划](docs/PLAN.md)及[决策](docs/DECISIONS.md)。旧原型在`prototypes/s01/`，不是当前平台运行入口。仓库未声明开源LICENSE，第三方资源遵守[原声明](THIRD_PARTY_NOTICES.md)。
