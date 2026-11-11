# 当前增量交接 v0.2

本轮任务：SETUP-001；状态只读TASKS或generated/STATUS，不在本文件重复维护。范围是精简计划、旧稿归档、当前目录本地Git初始化及提交；不执行S01专项设计或任何A/B/C开发。

## 已完成和停止点

已整理A—D计划、18项近期台账与简洁协作协议；96项旧台账及17个管理文件原样归档并逐ID映射；保留原M0—M4/MC含义，S01自立验收，不再等待S02或所有公共能力。PLAN.html从MD派生、流程图同源离线内嵌。

S01是下一项：收到下一条明确指令即可开展D-S01-01设计。未写业务代码、未建src/pyproject/migrations/部署、未连接ERP、未调用真实模型或执行MC/业务测试。当前验证只涉及文档/图示/归档/台账/入库安全与Git。

## 实际Git/工作区与验证

初始化前的实测：当前目录及父目录都无.git，git rev-parse/status退出128（非仓库）；旧17文件hash与上次交付一致；无敏感命名文件；Git user.name/email已配置。详细预检见planning/preflight.json。

Git已创建，初始提交为 `84e68e22195d92d708afead9549d84ac3a13d3b4`，分支 `main`，211个白名单文件，未设远端。提交后已跟踪工作区曾核验干净；本次证据更新由后续本地文档提交固定。完整实际结果记录于[repository-receipt](planning/repository-receipt.json)；该文件的observedHead是采集时HEAD，不是要求随每次提交改写自身SHA。接手始终运行：

```text
git branch --show-current
git rev-parse HEAD
git status --short --branch --untracked-files=all
git diff --stat
```

本轮实际文档/浏览器/安全/Git校验见[validation-report](planning/validation-report.json)、[security-scan](planning/security-scan.json)、[FILES](planning/FILES.md)。计划中的pytest/启动方式是未来约定，当前没有运行任何业务测试。剩余85个未跟踪文件及忽略文件/归属限制由仓库回执逐项记录，不能自动git add .。

实跑结果：`python docs/planning/check_plan.py` 退出0（17项文档检查PASS）；`node docs/planning/render_plan.cjs --browser-only` 退出0（三宽度×深浅主题通过、无远程请求，完整流程截图已抽查）；`python docs/planning/repository_audit.py staged` 退出0（211个暂存blob无疑似秘密）；初始提交后的 `python docs/planning/repository_audit.py final` 退出0（白名单/基线blob/无远端/已跟踪区干净）。这是文档及仓库验证，ERP/模型/MC/S01业务验收均NOT_RUN。最新提交及工作区在接手时实时读Git，证据引用的被测初始提交保持不变。

## 最短接手与下一步输入

1. AGENTS→本HANDOFF→TASKS的D-S01-01及相关契约；只在需要时读HLD§4—7/8.4/11与AI§3/9.1/14.1/15，不重读全部历史。
2. 检查真实branch/HEAD/dirty及本轮回执差异，保留未知改动；确认下一条任务指令再行动。
3. 先做S01专项设计，确认所需公共能力，再追加纵向切片实现/验收任务。不先开发S02，不把全部C排成必做，不提前创建目录。

建议用户下一条提供（缺项可先标待确认做设计）：试点SKU/仓/单位；库存分桶示例及镜像关系；需求来源/窗口；未收供给/预计可售日；MOQ/倍数/交期/缓冲；质量阻断规则；希望输出；先模拟文件还是已有ERP只读样例/接口说明。不要在聊天或Git提交密钥/客户个人资料。真实数据未具备时可用明确simulated样例，不冒充企业验收。

## 未完成/中断交接模板

按任务记录实际branch、观察时HEAD/基点、未提交路径与归属、真实提交、已做/未做、精确测试命令/环境/样本/退出码、FAIL/NOT_RUN、证据/hash、重要ADR、恢复步骤。未提交或交接不全不ACCEPTED。当前没有业务进程需要持续看护；本轮完成后停止。
