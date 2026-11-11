# 当前增量交接 v0.3

最新范围为文档治理与GitHub公开发布准备，业务任务状态只读TASKS。用户已授权检查通过后创建新Public仓库；本轮未授权Agent/正式前端/业务服务开发。下面的UX和SETUP授权记录是历史事实，不覆盖本轮新授权。

## 文档治理与公开发布停止点（2026-11-11）

起点main / `f113229fa6eefc271b811e290858d596174ea52e`，跟踪区为空、无remote，85份未跟踪材料已全量扫描并按内容归类；实际执行者Codex，范围为文档迁移/导航、README、文档工具、安全/路径检查和本地提交。源码/fixture/既有19项任务状态与业务决策不改。五份原文及17份旧计划保留原字节；当前正文仅改路径，迁移指纹见governance/migration.json。

Public发布停止：gh未安装/不在PATH，目标账号/权限/重名均未验证；Mermaid及交互图内嵌运行时完整再分发许可尚未核验。用户已明确同意历史提交邮箱公开；不改写历史、不删第三方历史材料、不添加项目LICENSE。未建远端或push。许可核验与手动登录步骤见governance/PUBLICATION.md。当前安全及测试结果统一见governance/audit.json；最终独立提交SHA从Git读取。

治理检查：活动文档本地链接0断链；86处归档历史缺失引用按原字节保留并单列，archive/README.md提供当前替代入口。计划/状态18项检查、AI修订11项和制品18项检查、原型20组交互、文档18个浏览器组合、计划/AI各6个主题宽度组合及设计保全检查均已执行，结果见统一审计。过程中的旧脚本/暂存白名单失败记录保留，不当作业务验收；最终结果以审计记录为准。没有新增业务任务、没有将REVIEW改成ACCEPTED；源码、模拟数据和冻结业务语义不变。结束后等待下一阶段指令。

治理实现提交 `3dbbed25afeb9d4c0624687d94924388da35d213`，后续只补交接/最终检查证据及4张被本轮复跑更新的截图原件（archive/governance-20261111），不改原型实现。151处第三方/历史空白格式问题记录FAIL并保留原字节。当前分支main；没有origin、没有GitHub仓库URL或远端SHA。最终证据提交通过Git查询，审计observedHead表示检查时的治理实现提交，避免自引用SHA。

## 小范围评审修复接手记录（2026-11-11）

用户追加授权UX-S01-01局部修复、自动化交互测试及独立本地提交；未授权正式前端或真实服务。起点main / `0e4aec39d6e5529278d4f047c75382630667c7be`，跟踪diff为空，85个既有未知文件保留。实际唯一写入者Codex；范围为prototypes/s01/app.js、check.cjs、证据，docs/ui产品/一致性/修复回执，以及TASKS/本交接/生成视图/白名单。

已补情景修订与建议/审批/源报告绑定；切换令建议SUPERSEDED，历史审批仍记录原决定但失效；回切不复活，来源入口不改情景。历史report-v1与新任务状态/模拟产物ID区分。逐日表和可售日明确原供给/候选；90/15仅历史指标。布局/配色/fixture/五份基线均不改。详细范围及待确认口径见docs/ui/REVIEW_FIX.md。修复/被测提交 `4df78d585b73fbffb2066c813a9ef087e5e1466c`。最终浏览器20组/20基础布局组合及新增窄屏检查PASS，页面错误/HTTP请求0；5份基线/85未知文件/9组颜色/462字说明保全PASS，17项文档规则PASS。browser-check.json源指纹与提交核对一致；过程FAIL与旧结果保留。作者已查看延期/失效/暂停/窄屏截图。证据随独立后续本地提交固定；该提交不改原型实现。

TASKS已回REVIEW，未伪造review签认。完整版本查询、新任务产物详情、延期重规划/重算、真实服务均未实现，S01/MC/真实审批验收NOT_RUN。真实日粒度/缓冲/迟到供给口径只列建议，未擅自冻结。已完成本轮授权范围并停止，等待负责人最终验收；不得自动开始正式前端。

## 本轮原型增量与停止点

根目录DESIGN.md定义视觉；docs/ui/PRODUCT_SPEC.md定义页面功能和人工流程，两者分离。独立原型在prototypes/s01/index.html，直接离线打开；工作台、建议列表、详情与人工审批均有会话演示。全部simulated，默认只读，显式开启后才演示C01/C02；执行始终禁用。证据与来源见docs/ui/RESEARCH.md、ALIGNMENT.md及DELIVERY.md。完整D-S01-01专项尚未完成，不将本次UX交付冒充其全部验收。

开始时实测main / HEAD `482e83d4f0af2f64b9eaad1bc0279b76938d6b70`，已跟踪diff为空；85个既有未知文件保留，路径/指纹见docs/ui/workspace-observation.json。新增/改动范围仅TASKS指定原型与文档。实际原型实现提交 `8140d40439517f957044537fdffa11f2c5a6463e`；截图复核延期基线混用问题后，修正提交 `9a7c9a34bd4079fbdb8bef65b80c7dcdea224df4`。针对后者重跑浏览器：15组交互/20布局组合PASS，无页面错误/网络请求；9组颜色、462字说明、85个未知文件和五份基线保全检查PASS。文档17项检查PASS。完整证据随本地交接提交固定，见TASKS和docs/ui/DELIVERY.md。

正式ERP/模型/B01/B02/审批/MC/生产验收均NOT_RUN。负责人需确认试点口径、质量/时效矩阵、审批角色/金额/期限与只读范围；确认并另行授权前不进入正式前端开发。本轮交付后停止。

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
