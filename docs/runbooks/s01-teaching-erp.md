> 日常使用增量（2026-11-14）：当前默认入口为[Windows一键启动与管理员登录](local-platform.md)及[README](../../README.md)。下文保留原阶段/开发测试运行方式；临时Token、动态端口和900秒演示不再是日常流程。本地loopback HTTP Cookie例外以新契约为准，旧测试配置保持其原安全语义。

# S01 教学ERP只读接入与准入报告

本阶段只读，状态见[TASKS](../TASKS.md)，事实/缺口见[真实验证报告](../evidence/D-S01-LIVE-01/api-report.md)。已验收DEV工程在main；本阶段新代码另交REVIEW。TEACHING_ERP_ONLY：仅指定教学HTTPS主机在Connector内关闭证书验证，禁重定向/环境代理；生产必须正常证书校验。账号密码或Token只填根目录忽略的.env.erp，不放命令行/日志/Git。API本身的源错误不因TLS例外而转成功。

原始身份、参数和响应仅存data/private/s01-erp-20261112；本阶段负责人已确认identity.json对应的新试点。既有来源文件不可冒充SKU-A恢复。Adapter严格方法/路径白名单；REST用full、页最多50、最多5页/读取、共享请求上限；已知503/超时最多一次退避重试，D01不再叠加重试。候选discover每次最多20条，complete=false只作发现；read遇不完整/漂移/重复/超限失败，不切Mock。源空集合只表示该接口范围下返回空，不能证明业务无记录。

显式真实采集并构造固定包（有界查询，不扫描全量）：

```powershell
.\.tmp\stage-a-clean\Scripts\python.exe -m tools.s01_erp_readonly --capture
```

失败输出FAIL和固定安全码，不能作为当前数据完整成功。新采集每次唯一私有目录保留原响应/指纹，不保存认证响应。只有显式选择已有真实观测回放时才用下列入口；此次固定包保留原观测时点及SOURCE_REVALIDATION_FAILED，不是最新重采集成功：

```powershell
.\.tmp\stage-a-clean\Scripts\python.exe -m tools.s01_erp_readonly --input-capture data/private/s01-erp-20261112/fixed-observation-capture.json
```

构造出的projection.json是安全观测DTO，真实数据未准入时永不作为计算输入。D02投影和D03唯一manifest绑定来源/版本/三轴/源synthetic/当前缺口；原B02在质量门返回阻断，B01不执行。O01拥有任务/预算/报告，当前模型预算0，AI显示NOT_ATTEMPTED。任务SUCCEEDED只表示阻断报告发布成功，不表示库存/候选/采购可用。无迁移/新依赖，默认应用不注册教学场景。

显式教学API与Worker分别启动（使用既有获准本机G01身份与唯一隔离MySQL，不能匿名绕过）：

```powershell
$env:COMMERCE_ENVIRONMENT='test'
$env:COMMERCE_MODEL_PROVIDER='mock'
$env:COMMERCE_MODEL_NETWORK_ENABLED='false'
$env:COMMERCE_TEACHING_PACKAGE_PATH=(Resolve-Path data/private/s01-erp-20261112/projection.json).Path
.\.tmp\stage-a-clean\Scripts\python.exe -m uvicorn commerce_hub.bootstrap.teaching_erp:create_app --factory --host 127.0.0.1 --port 8000
# 另一终端注入相同获准身份/固定包环境配置：
.\.tmp\stage-a-clean\Scripts\python.exe -m commerce_hub.bootstrap.teaching_erp worker
```

原任务API受理SINGLE/TEACHING_S01_ADMISSION，parameters只接受服务端固定packageRef，scope按包中的单SKU/店/仓/quantity及当前G01核验；不允许客户端传URL、秘密或raw数据。原报告和D04证据读取会再次授权；重入不重新抓ERP，历史报告依据持久固定投影验证，不拼latest。示范进程使用生成的本机教学工程身份，非企业身份/生产许可验收。

复验：显式mock/network=false/COMMERCE_RUN_MYSQL_TESTS=1，运行python -m tools.verify_s01_erp、python docs/planning/build_docs.py、python docs/planning/check_plan.py及git -c core.whitespace=cr-at-eol diff --check。回归的HTTP响应是OFFLINE契约fixture；真实网络证据单独在source-index.json，不能混算。实际私有观测包的独立API/Worker/MySQL演示另记real-workflow.json；未准入的真实B01/B02正向业务计算仍NOT_RUN。
