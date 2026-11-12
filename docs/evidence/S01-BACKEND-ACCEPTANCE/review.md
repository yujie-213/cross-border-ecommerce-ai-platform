# S01 后端分项验收与 main 合入

评审日期：2026-11-12。评审人：负责人和星星；结论来自负责人本轮明确通知，Codex负责登记与Git操作，不冒充独立评审人。

交付提交 `1619bc1d1f7018bb8116dafeceaf9713fe52687e`，已验证实现 `c965a334b6bbc3c689fb334c80f8cf0a9ee84dad`。本次原范围验收沿用下列既有实测证据，没有新增真实 ERP 或模型调用。合并后复验另存 `postmerge-verification.json`，不得替换原 `S01-BACKEND/verification.json`。

## 已批准的教学后端工程范围：ACCEPTED

| 范围 | 负责人批准依据 |
|---|---|
| 教学ERP仿真API写入与独立GET、来源/教学规则区分 | [批次](../S01-BACKEND/teaching-data/dataset-evidence.json)、[准入](../S01-BACKEND/admission/teaching-simulation.md) |
| 原B01/B02与9项独立Golden | [独立期望](../S01-BACKEND/admission/teaching-golden.json)、[逐项对照](../S01-BACKEND/teaching-data/calculation-comparison.json) |
| 5项真实API/Worker/MySQL与任务/取消/幂等/历史/报告/证据/权限 | [进程联调](../S01-BACKEND/teaching-data/backend-process.json)、[601项回归](../S01-BACKEND/verification.json) |
| Token统一统计/Provider映射、费用可空和未知预算保留 | 原601项回归及 [实际Token/费用事实](../S01-BACKEND/model/execution.json)；工程核账通过不等于模型用途五例通过 |
| 0005迁移与历史核账保全 | [366条usage/759条attempt/1619条budget原字段指纹](../S01-BACKEND/usage-migration.json) |
| 后端API及运行文档 | [API契约](../../contracts/s01/backend-api.md)、[运行手册](../../runbooks/s01-backend.md) |

任务状态仍只维护在 [TASKS](../../TASKS.md)。D-S01-DEV-01此前工程ACCEPTED保持；LIVE同时涉及企业真实数据/业务验收，本轮在其review/history登记教学工程范围ACCEPTED，整体保持REVIEW。没有删除或改写LIVE历史源FAIL/业务NOT_RUN，也没有放宽文档校验器使混合任务整体通过。

## 未通过和保留事项

C-04整体保持REVIEW，五例真实用途评测FAIL：A AVAILABLE、B AVAILABLE、C INVALID_OUTPUT、D/E NOT_RUN。C缺必需文内引用而被正确拒绝；后两例按首败停止。原3次调用、输入5067/输出575/总5642 Token，费用UNKNOWN、原$0.15预约保留，见 [实际模型报告](../S01-BACKEND/model/report.md)。后续在原C-04下独立安排用途修复/评测和正常S01在线模型接入，不创建第二台账、不利用剩余额度自动重发。本轮新增付费调用0。

企业数据、真实补货规则、正式ERP安全和AI正式用途四门继续BLOCKED。企业审批/采购下单/外部执行均未授权。教学规则、API联网或局部模型成功都不解除这些门。

## 合并和验证方式

合并前本地/远端评审分支均1619bc1，main均b1813e5；main是评审分支祖先。先在评审分支提交验收/交接文档并普通同步，再以 `git merge --ff-only codex/s01-backend-closure` 合入本地main。若发现远端漂移、冲突或关键检查FAIL，停止推送main，不强推或改历史。

合并后执行原全量工具 `python -m tools.verify_s01_backend`，真实隔离库和离线ERP/模型、独立进程测试；新证据只表示合并后的工程复验。其默认输出移存到本目录，原始被审证据逐字保全。再检查601项名称和src/tests/tools/migrations/依赖与被审实现一致、默认入口禁网、四门/C-04状态、未知OpenAPI指纹、公开Git范围和秘密模式。文档生成/18项检查通过后才普通推送main。

测试后只追加文档/证据提交时，报告必须区分已测试的合并HEAD与包含收尾证据的最终main HEAD，并核对二者没有任何源码/测试/配置差异。实际命令、退出码、HEAD和远端读回事实以本目录JSON及最终Git结果为准；不预填成功或尚不存在的SHA。

## 下一阶段

确认下一阶段为D-S01-UI-01，保持TODO、未领取编码。本次仅准备 [前端准入交接](../../ui/S01-frontend-entry.md)。下一条前端开发指令下达后从最新同步main建立工作基线；复用统一中台原型/视觉/架构，消费现有真实API。普通S01后端仍是显式off/mock装配，正式DeepSeek在线流程不是已交付能力。
