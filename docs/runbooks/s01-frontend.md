# 序衡 S01 前端运行与演示

本轮正式前端位于 `frontend/`，旧 `prototypes/s01/` 保留。只读教学闭环，普通后端模型 off；无采购、审批、ERP 写入或付费模型调用。任务验收状态唯一在 TASKS。

## 本机受控启动

使用已有 `.tmp/stage-a-clean` Python 环境、本机 `.env` 获准 MySQL 账号及唯一 `s01_a01_test_20261112`，迁移应已处于 `0005_optional_usage`。启动工具不执行迁移、清库或 ERP / 模型访问。已有私有教学批次 catalog 必须就绪；不能用不存在的包自动回落到模拟 SKU。

```powershell
$env:PYTHONPATH='src'
.tmp/stage-a-clean/Scripts/python.exe -m tools.s01_frontend_dev --execute-local
```

该命令使用现有 G01 `provision_fixture` 测试身份流程，只赋当前 catalog 精确 scope 的 create/read/cancel/工程 Worker 权限。API 与 Worker 独立进程；默认运行 900 秒，Ctrl+C 关闭本工具拥有的进程。身份不是生产账号管理能力。短期 Bearer 与 API 地址仅写入 Git 忽略的 `data/private/s01-frontend/session.json`，不要复制到日志、聊天、Git 或 URL。私有 control 文件仅供测试工具暂停自有 Worker / 调整自有测试主体读取权限，不注册 HTTP 端点；与其他项目隔离。

另一终端：

```powershell
cd frontend
npm ci
$s01Local = Get-Content ../data/private/s01-frontend/session.json -Raw | ConvertFrom-Json
$env:S01_API_TARGET=$s01Local.apiTarget
npm run dev
```

打开 `http://localhost:5173`。点击“连接身份”，从本机私有回执取得短期 Bearer 连接；它只用于 POST `/api/v1/session` 交换 Cookie，用后清空，不写入浏览器存储。已有 Cookie 可留空核对。不要在此输入 ERP 密码或服务端签名密钥。开发代理只允许 loopback HTTP API，浏览器同源，不扩 CORS、不关闭 CSRF / Origin、不删除 Secure。实际 Edge 已核验 localhost Secure Cookie 行为；非 localhost 正式部署必须使用 HTTPS。

生产静态交付为 `npm run build` 生成的 `frontend/dist/`，由部署方同源托管并把 `/api/` 转发到既有 FastAPI；`COMMERCE_BROWSER_ORIGIN` 必须与真实 HTTPS Origin 精确匹配。Vite 是开发工具，不是生产身份提供方。企业部署/SSO/上线与新账号权限均不在本轮验收范围。

## 演示顺序

1. 工作台 / 补货建议，选择授权店、仓、SKU 与包时点。包标识用于区分同 SKU 的多个快照；不要将库存相加。店仓 SKU 当前仅有服务端公开 canonical 标识，没有商品名称查询 API。
2. “新建补货分析”核对来源与 packageRef，发起真实分析任务。任务每 2 秒查询，最多 60 次；终态、拒绝或网络异常停止，未更改服务端状态。
3. 发布后自动读取本次报告：任务状态 / 完整性 / AI / 采购适用性独立。查看 A 的 60 件库存、17 件缺口、18 件候选，仍有到货前缺货；B 无需补货；C 总量覆盖但中途缺货；D 约束限制、E 质量调查。五包为既有教学 GET capture，不是五种库存同时在线。
4. 查看逐日图和等价表、质量、Token 未知、证据与版本。从报告重新分析会携带 previousReportRef，不继承计算或审批。
5. 历史只按选定精确店仓 SKU 查询，每页 20 条；状态筛选只作用于本页。工作台统计也仅本页，非全库。无汇总接口时不推算其他范围。
6. 刷新后从 sessionStorage 的任务标识重新读取，不缓存报告或凭据；网络不确定命令保留原 key 和请求内容，使用“原命令核对”。不要改 key 盲重发。

会话到期后重新连接；401 响应清除无效 Cookie，仍需有效 Bearer。403 会停止敏感读取，已撤销权限需管理员在受控服务端恢复。真实采购审批尚未提供，人工审批页仅作说明。

## 验证

```powershell
cd frontend
npm run test
npm run build
npm run test:browser
```

浏览器测试使用已安装 Edge、上述 API/Worker 与真实隔离库，3 个 REAL 集成测试和 2 个明确 PROTOCOL FIXTURES 测试。夹具只测 AI/异常/轮询/分页分支，不当真实模型验收。截图和脱敏摘要在 `docs/evidence/D-S01-UI-01/`；原始测试临时输出在 `.tmp/`。

回归前先停止本工具，避免它的 Worker 与后端进程测试竞争。后端按既有验证命令执行，证据另存本轮目录，不覆盖 S01-BACKEND 或 C-04 历史失败证据。
