# S01教学技术验收合并复验

负责人明确通知星星独立评审完成，批准被审`098fe19bfc2c67476cb18443bbad29d12c5d0ffd`的前端竞态、结构化引用和真实A—E教学技术验证 **ACCEPTED**。UI任务ACCEPTED；C-04技术范围ACCEPTED，含正式用途签认的整体仍REVIEW（沿用混合任务分项验收方式）。企业四门BLOCKED、D-S01-ACCEPT-01仍TODO，S01 MVP整体未验收。[批准登记](review.md)。

fetch确认来源精确098fe19、main6fdf10c为祖先、跟踪区干净；未知OpenAPI保留。仅在被审源码后追加验收文档e08f264，然后实际`git switch main` / `git merge --ff-only codex/s01-ui-c04-fix`，无冲突，不变基/改写/强推。合并后固定测试HEAD `e08f2640171eb34d72a1b2df4b02933b35bed8a3`；最终证据提交与它的src/tests/tools/frontend/migrations/依赖完全一致。最终main提交和远端同步用实际Git回读，不预填未来SHA。

| 本轮合并后重跑 | 结果 |
|---|---|
| 后端全量（真实唯一隔离MySQL、离线模型/ERP） | 639 PASS，0 FAIL/ERROR/SKIP，原639逐名保全 |
| 其余工程命令 | 九条总命令全部exit0；pip/编译/离线套件/默认禁网入口 |
| 前端单测 | 31 PASS / 0 FAIL |
| Vue类型检查 / 生产构建 | PASS / PASS |
| Edge Playwright | 6 PASS，4真实本机API + 2协议夹具；0 flaky/skipped |
| 文档一致性 | 18项检查，实际结果见docs/planning/validation-report.json |
| 安全/范围/历史保全 | 见preservation.json |

[后端逐项](backend-regression.json)、[前端/浏览器逐项](frontend-verification.json)、[浏览器观测](real-browser-cases.json)、[账本前后指纹](budget-preservation.json)、[范围与秘密扫描](preservation.json)。本次未出现产品测试失败，不删断言、不改Golden/算法/必要校验。自有API/Worker/Vite测试进程已停止。

本轮真实DeepSeek/ERP联网复测 **NOT_RUN（负责人明确禁止）**，新增请求/Token/费用记录0。被审五例真实PASS及原C原文v1拒绝/v2离线PASS沿用独立历史证据，不冒充本次联网。原任务5642Token/UNKNOWN/$0.15预约、新任务10047Token/UNKNOWN/$0.25预约，以及各budget/attempt/usage前后指纹完全一致；没有释放未知预约。既有两付费任务预算未改，工程测试仅生成其隔离夹具记录。

未完成的S01 MVP工作：LIVE正式经营数据/规则/ERP安全/AI用途签认，普通前端真实AI流程仍off/mock，完整S01-AC端到端复现及负责人验收尚未开展。下一步建议先冻结后续教学整体验收口径和模型正常流程接入条件，经负责人新授权并满足对应依赖/准入后按D-S01-ACCEPT-01推进；企业正式运行必须四门签认。手机逐日表LOW技术债仍只登记于docs/ui/S01-frontend-entry.md。本轮验收合并推送后停止。

可复现命令（根目录，已有获准本机依赖/隔离库/私有capture；禁止另发付费请求）：

```powershell
$env:PYTHONPATH='src'
.tmp/stage-a-clean/Scripts/python.exe -m tools.verify_s01_frontend --run-backend --evidence-dir <新的docs/evidence子目录> --baseline-evidence docs/evidence/S01-UI-C04-ACCEPTANCE/backend-regression.json
python docs/planning/build_docs.py
python docs/planning/check_plan.py
# frontend/中 npm run test; npm run typecheck; npm run build
# 按docs/runbooks/s01-frontend.md启动受控本机API/Worker/Vite，另设新证据目录后 npm run test:browser
```
