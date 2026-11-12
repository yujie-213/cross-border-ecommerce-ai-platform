# S01 前端竞态与C-04引用契约修复

交付状态 **REVIEW**，实现与固定被测提交 `a3da2ba1948009c93501bed1a6ccfcc7749d51cc`，分支 `codex/s01-ui-c04-fix`，基线为远端最新前端0525fa7。待负责人和星星独立评审，不合main。

## 修改与保护

证据弹窗状态与读取归useWorkspace管理，捕获taskId、reportRef、任务读取上下文、请求代次和局部signal；任务/报告切换、关闭、身份交换、退出、失权立即取消并清空数据/错误/加载。成功、错误、finally均检查仍绑定当前状态，不缓存旧证据。单测让传输忽略Abort后返回；浏览器让真实GET完成后延迟交付，验证二次保护。Cookie/CSRF/Origin/权限API未改。

旧文内[ref]只有重复语法作用；真正句子绑定来自每条一个supportRef、当前报告事实/章节白名单及对应受控短语精确匹配。新版Prompt controlled-2 / s01-controlled-natural-v2不再强制文内标记，仍可兼容匹配的旧标记。text/supportRefs和四类数组Schema未改，前端现有“依据”继续从结构化字段显示，无AI布局重构。

保留严格Schema、白名单及task/snapshot/version重建、按ref的受控短语、数量/日期允许集、每项一个事实、必需事实覆盖、未知/质量/风险/采购保护。引用存在不证明任意文本正确；不是任意自然语言推理器。原v1 Prompt/策略/摘要及历史读取保留。B01/B02、数据库迁移、依赖锁、预算/幂等及业务权限均未改。

## 实测结果

| 验证 | 结果 |
|---|---|
| 前端单测 | 31 PASS / 0 FAIL，原19 + 12生命周期测试 |
| Vue类型检查与生产构建 | PASS |
| Edge浏览器 | 6 PASS / 0 FAIL：4真实API（含受控延迟）、2协议夹具；原五项保留 |
| 全量后端 | 632 PASS / 0 FAIL / 0 ERROR / 0 SKIP，原603逐名保全、新23单元+6集成 |
| 九条工程检查命令 | 全部退出0，见backend-regression.json |
| 原A/B原文 | v1、v2均PASS；原六项版本摘要重建一致 |
| 原C原文 | v1仍UNCONTROLLED_NATURAL_LANGUAGE；v2离线PASS，原文摘要不变 |
| 原持久报告 | SELECT只读，v1发布/公开读取兼容PASS，历史五例FAIL不变 |
| 新真实DeepSeek C/D/E | 均NOT_RUN：原授权绑定结束唯一task/首败停止，无新增授权 |

新23单元测试覆盖结构化纯引用正例、伪造/跨任务/错章节引用、引用合法但数量错误、错日期、无风险逆转/风险遗漏、质量放行、未知补0、采购执行、多判断和多引用、无候选编造候选/0件单、v1兼容及策略伪改；6集成覆盖合法A/C/E与数量/引用/质量审批篡改，拒绝后保留规则报告和原记账。没有删改旧测试或Golden断言。

当前MySQL8.0.27、仅s01_a01_test_20261112、UTC/READ-COMMITTED、head0005_optional_usage。新付费调用0，新增input/output/total/cache Token均0；没有新费用记录，历史费用仍UNKNOWN、$0.15预约保留。原预算/attempt/usage前后指纹一致，3次/5642Token不变。当前API仅off/mock，本轮ERP网络0，全部真实数据来源是既有教学GET capture，不能当新增ERP实测。

前端[详细结果](frontend-verification.json)、[后端632项与九命令](backend-regression.json)、[原文离线复验](offline-revalidation.json)、[真实浏览器case引用](real-browser-cases.json)、[预算保全](budget-preservation.json)、[范围/历史/秘密检查与精确修改清单](preservation.json)、[开发失败记录](history.json)。

## 文件与复现

| 文件 | 作用 |
|---|---|
| frontend/src/useWorkspace.ts、App.vue | 证据代次/任务报告绑定及统一弹窗生命周期 |
| src/commerce_hub/scenarios/s01/natural_explanation.py | v2 Prompt/受控校验，保留v1重建 |
| src/commerce_hub/scenarios/s01_backend/__init__.py | 发布/读取识别两版策略 |
| frontend/tests/unit/evidence-race.test.ts | 12项忽略Abort的交错生命周期 |
| tests/unit/models/test_structured_references.py | 23项引用与事实正反例 |
| tests/integration/s01/test_structured_references.py | 6项真实隔离MySQL/A01/O01/G02集成 |
| tests/browser/s01/workspace.spec.ts | 保留原5项，增加真实API延迟竞态及结构化引用展示断言 |
| tools/revalidate_s01_c04.py | 显式--offline复验原私有原文，默认NOT_RUN |
| tools/verify_s01_frontend.py | 参数化新证据目录及603基线，不覆盖历史 |
| docs/DECISIONS.md、contracts/s01/backend-api.md | ADR-S01-UI-C04-002与接口/引用兼容说明 |
| docs/TASKS.md、HANDOFF.md、generated/、planning/ | 唯一台账/交接/派生视图及精确白名单 |
| docs/ui/S01-frontend-entry.md、runbooks/s01-frontend.md | LOW移动技术债仅登记、复验命令与身份生命周期说明 |

完整实际路径在preservation.json.changedFiles；最后收尾SHA与GitHub同步由Git实时读回。源码/测试/工具/配置与被测提交不再变化。运行和验证命令见[手册](../../runbooks/s01-frontend.md)。本机API/Worker/Vite已停止，重复浏览器测试须重建短期fixture；不要将私有Bearer复制到日志/Git/URL。

截图均为本轮固定实现： [桌面工作台](screenshots/workbench-1440.png)、[A报告](screenshots/detail-A-1440.png)、[1024](screenshots/detail-A-1024.png)、[390](screenshots/detail-A-390.png)、[E质量](screenshots/detail-E-1440.png)、[历史](screenshots/history-1440.png)、[撤权](screenshots/revoked-evidence.png)。手机截图仅回归捕获；CSS/图表/移动布局没有改动。

## 保留与后续

手机逐日表可读性/滚动提示LOW技术债登记于docs/ui/S01-frontend-entry.md，本轮不实施。C-04整体仍REVIEW且历史五例FAIL；新版C离线PASS不能替代新真实C/D/E用途评测，也不能批准完整S01 MVP。真实复验要明确后续授权及累计10次/$1预算核对，不复用结束task/logicalCall/key，不释放历史预约；任一失败继续保留安全降级。四项企业正式准入均BLOCKED，采购执行/审批、ERP写入、下一模块均未开发。完成普通推送后停止，仅等待负责人和星星评审。
