# D-S01-UI-01 前端 MVP 交付

本轮交付正式 Vue 前端，消费已有 S01_BACKEND 只读教学 API。最终状态仅 REVIEW，负责人和星星独立评审前不登记 ACCEPTED、不合 main。开发基线 `6fdf10cd6850794cc1ba2695078e68a58996e974`，分支 `codex/s01-frontend-mvp`。

已实现工作台、授权固定包筛选、真实任务创建 / 有界轮询 / 取消 / 刷新恢复、历史与游标、报告详情、逐日图与等价表、质量与风险、四类 AI 解释、Token / 可选缓存 Token、版本和当前证据。人工审批页明确尚未开放。界面沿用原型，原型源码保留。

## 工程与接口

| 页面 / 模块 | 实际能力与来源 |
|---|---|
| `frontend/src/App.vue` / 共享组件 | 原型三导航、工作台 / 列表 / 详情 / 审批说明、模态键盘与响应式 |
| `frontend/src/api/` | TypeScript DTO、统一 Cookie/CSRF HTTP 客户端；无签名密钥 / ERP 凭据 |
| `useWorkspace.ts` | 原 key 命令恢复，任务身份绑定、迟到读取隔离、2秒 / 60次上限、拒绝停止与清理 |
| options → 创建 | GET `/api/v1/s01/options` → 精确 scope / packageRef → POST analysis-tasks，scope 无 tenantId |
| 状态 / 取消 | GET task；POST cancel 带原 expectedRevision / Idempotency-Key，冲突要求核对 |
| 报告 / 证据 | GET task/report、task/evidence/id；本次 reportRef/任务绑定，当前权限每次复核 |
| 历史 / 重新分析 | GET analysis-tasks 单一精确范围、limit20 / before；重新分析显式 previousReportRef |
| 图表与候选 | baseline.series / candidates[].evaluation.series；SVG只做坐标显示转换，无采购计算 |
| 身份 | POST / DELETE session，安全Cookie；无效401清理Cookie最小修复，鉴权不放宽 |

技术决定与兼容性见 [ADR-S01-UI-001](../../DECISIONS.md)。静态打包与受控本机启动、部署条件见 [运行手册](../../runbooks/s01-frontend.md)。无全局汇总接口，工作台数字明确只统计当前精确范围历史本页；不遍历 catalog 冒充全库。

## 测试与验收映射

固定被测实现 `465892c9342f23fd3e1614df85c564ade0a5ef9a`。前端[验证记录](frontend-verification.json)：客户端 **19 PASS**，类型检查与生产构建PASS，Edge浏览器 **5 PASS**（3 REAL、2 PROTOCOL FIXTURES）；后端[完整回归](backend-regression.json)：**603 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，旧601逐名保全、新增2项Cookie恢复，9条命令全PASS。文档检查18项PASS。开发期失败与修复记录见 [history](history.json)，与最终0失败分开；原C-04历史FAIL不改写。

固定提交的源码/测试/工具/配置与证据收尾提交保持一致；最终Git回执另列。真实隔离库MySQL8.0.27、UTC/READ-COMMITTED、head0005不变，无清库/其他库操作。原[付费核账保全](budget-preservation.json)前后完全一致。

| 验收 | 验证内容 |
|---|---|
| AC1 | 原型保全；1440/1024/390；服务端14行A曲线数据逐值对照；前端无库存/候选/日期重算；审批不可操作 |
| AC2 | 真实 A—E、原key重放/冲突、previousReportRef、刷新、无报告终态；协议错误/空选项不回落样例 |
| AC3 | 真实 off=NOT_ATTEMPTED；协议夹具 AVAILABLE/UNAVAILABLE/Token未知/缓存/费用未知；规则与质量独立 |
| AC4 | 实际Edge Cookie/CSRF/恶意Origin、真实撤权证据404、独立API/Worker/MySQL、取消/revision冲突、上限停止、分页/键盘 |

真实 A—E 使用既有教学 ERP 正式 GET capture，经真实 API / 独立 Worker / MySQL 处理；本轮没有新的 ERP 网络访问。不是五种库存同时在线。A 17件缺口、18件候选且到货前风险；B 无需补货；C 期末覆盖但中途缺货；D 约束无候选；E 质量调查。实际 taskRef/reportRef/snapshotRef 见 [浏览器案例](real-browser-cases.json)。

协议夹具只覆盖 AI 与异常展示，不替代 C-04；普通后端只 off/mock，当前教学任务未启用真实 DeepSeek。费用与Token未知不填0。公开 API 不含 MOQ / 倍数数值，详情明确无法核实，不从私有投影补字段。

## 截图

主要页面：[工作台](screenshots/workbench-1440.png)、[A详情1440](screenshots/detail-A-1440.png)、[1024](screenshots/detail-A-1024.png)、[390](screenshots/detail-A-390.png)、[E质量调查](screenshots/detail-E-1440.png)、[历史](screenshots/history-1440.png)、[撤权反馈](screenshots/revoked-evidence.png)。截图均来自浏览器实际 API 页面；最终固定实现重跑后更新对应截图。

## 保留限制

- 企业数据 / 规则 / ERP安全 / AI用途四门 BLOCKED；教学仿真规则只用于教学。
- C-04五例FAIL、原3次/5642Token/费用UNKNOWN/$0.15预约保留，本轮付费模型0。
- 未提供采购草稿、确认、审批、下单、付款、发货或在线ERP任意SKU搜索；未实现企业SSO或正式上线。
- SKU/店铺/仓库仅可显示公开canonical标识；来源包区分时点，不相加。历史筛选只作用本页，报告详情按需读取。
- 后续仅等待独立评审；C-04修复、真实模型正常接入及下一开发阶段需单独指令。


GitHub已普通同步并独立读回交付提交 `15f8a5b0a25f9cfaedc55d7bc3514d6aeae1cb53`，main保持6fdf10c，详见[同步回执](git-receipt.json)。随后仅收尾回执/台账提交，最终HEAD以实时Git读回及负责人交付消息为准；与固定被测实现 `465892c9342f23fd3e1614df85c564ade0a5ef9a` 的源码/测试/配置一致，不合main。
