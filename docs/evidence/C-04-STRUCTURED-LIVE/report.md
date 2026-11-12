# C-04 结构化引用官方模型复验

新授权独立任务真实 **C/D/E/A/B全部PASS**，最终交付 **REVIEW**，等待负责人和星星独立评审；不合main、不自动ACCEPTED、本轮技术验证具备提交评审的条件；企业正式准入和完整S01 MVP验收仍按各自门禁评审。

实现与全部实际测试提交 `412c0161c187b1245ca4e5b7b8a74d58e24df709`；分支codex/s01-ui-c04-fix，基线48ce3e9。用户新授权明确覆盖旧结束任务停止点。记录：[授权](authorization.json)、[实际调用/用量](execution.json)、[639项回归](backend-regression.json)、[前端/浏览器](frontend-verification.json)、[预算保全](budget-preservation.json)、[范围/历史与秘密扫描](preservation.json)、[过程](history.json)。

## 真实结果与用量

| 场景 | 真实解释/结构/引用/事实 | 输入Token | 输出Token | 总Token | 缓存命中/未命中 |
|---|---|---:|---:|---:|---|
| C | AVAILABLE / PASS | 1802 | 181 | 1983 | 0 / 1802 |
| D | AVAILABLE / PASS | 1799 | 182 | 1981 | 512 / 1287 |
| E | AVAILABLE / PASS | 1803 | 181 | 1984 | 512 / 1291 |
| A | AVAILABLE / PASS | 1985 | 191 | 2176 | 512 / 1473 |
| B | AVAILABLE / PASS | 1758 | 165 | 1923 | 512 / 1246 |
| 合计 | 5次 / 5 PASS | 9147 | 900 | 10047 | 2048 / 7099 |

五条场景输出均无文内[ref]，依靠text/supportRefs和保留的逐条事实校验通过。Provider实际返回、G02每维Token、usageRef、绑定/版本摘要、已发布报告只读核对一致。官方HTTPS api.deepseek.com/chat/completions / deepseek-flash，禁代理/重定向/自动重试。新task `b8007816493d4b4ead5d993fef1128a2`；原task不重发，新logicalCall命名空间与旧调用无交集。

C保持期末缺口0但首次缺货和风险，不虚构桥接采购；D约束无候选，候选未知需确认；E候选UNKNOWN且质量BLOCKED，没有把未知补0或解除质量；A候选18件仍有到货前风险，B无需补货、没有0件采购单。全部procurementEligible=false。UNKNOWN候选的受控短语/数字允许集及必需覆盖均校验，不能因supportRefs存在就证明任意文本正确。

actualCost/currency/pricingVersion仍null/UNKNOWN，不伪造价格或当免费，不影响五例AVAILABLE。新O01预算上限10次/240000Token/$1、每次$0.05风险预约、并发1/30秒/600秒/单投递。实际5次，新未知费用$0.25预约保留。原3次/5642Token、五例FAIL与$0.15预约前后指纹相同，费用UNKNOWN保留。没有为了验证数量而重复调用；必要修复复测已获授权，但本轮首轮全部成功，无此需要。

## 工程修改和回归

只增加显式新授权配置，分离源catalog许可与执行许可、固定新主体/key/task/logicalCall，CDEAB顺序。旧配置/默认接口兼容；教学scope属于原准入/批次/规则摘要绑定，不改包、不重签来源，新主体在原精确教学租户内操作独立任务。普通后端仍off/mock。前轮竞态与v2引用代码未改，旧v1 Prompt及全部摘要读取保留，无B01/B02/Schema/依赖/迁移/移动布局改动。

前端31 PASS，Vue类型检查/生产构建PASS，Edge浏览器6 PASS（4真实API/2协议夹具，含迟到竞态/关闭/撤权/退出、CSRF/Origin、刷新、幂等、响应式）。后端 **639 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，原632逐名保全，新7项独立授权/主体/键/顺序/预算/首败停止测试；九条工程命令全部0。错数量、日期、引用、风险遗漏、质量放行、采购越权负例继续通过，不改Golden或删断言。MySQL8.0.27、仅s01_a01_test_20261112、UTC/READ-COMMITTED、head0005未变。

## 可复现核验与证据

已结束评测不盲重发。根目录在获准本机环境运行：

```powershell
$env:PYTHONPATH='src'
.tmp/stage-a-clean/Scripts/python.exe docs/evidence/C-04-STRUCTURED-LIVE/verify_readonly.py --verify
.tmp/stage-a-clean/Scripts/python.exe -m tools.verify_s01_frontend --run-backend --evidence-dir docs/evidence/C-04-STRUCTURED-LIVE --baseline-evidence docs/evidence/S01-UI-C04-FIX/backend-regression.json
```

verify_readonly.py默认NOT_RUN，显式--verify只读MySQL和本机Git忽略capture，核对当前源码与被测实现相同、原始响应摘要、Schema/引用/事实/版本、Provider/G02四维Token、独立任务预算和公开记录完全一致；不发送网络、不写账或覆盖原证据。原C原文v1拒绝/v2离线PASS保留在[前轮离线证据](../S01-UI-C04-FIX/offline-revalidation.json)，本轮没有改校验契约。

实际执行参数为 `--execute --authorization-id s01-c04-structured-20261112-r1 --max-requests 10 --max-cost-usd 1 --request-risk-usd .05 --catalog-path <existing-private-teaching-catalog> --private-output <private-successor-worker.json>`，可信API/Worker装配与配置见[后端手册](../../runbooks/s01-backend.md)。原始响应/令牌/Key不入Git；本机.env保持不变。修改文件精确清单见preservation.json.changedFiles。

[工作台](screenshots/workbench-1440.png)、[桌面详情](screenshots/detail-A-1440.png)、[390回归截图](screenshots/detail-A-390.png)来自本轮普通off模式真实API，不能冒充DeepSeek在线前端；移动端LOW技术债仍只登记于docs/ui/S01-frontend-entry.md。全部自有API/Worker/Vite已停止。四企业门BLOCKED、采购/审批/ERP写入及下一模块不开发。完成普通push后停止，最终HEAD/远端一致性按实时Git回读；源码与被测提交保持一致。
