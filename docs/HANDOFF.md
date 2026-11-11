# 当前增量交接 v0.3

## S01 MVP 实施文档交付（2026-11-11）

最新用户授权是编写可供AI参考的MVP实施文档；用户进一步明确：本轮不编码/不生成TODO/不调查ERP、不开发完整模拟系统；下一阶段专门调查现有YAML并修订方案，若真实ERP满足核心数据则正式开发优先直接接入，模拟用于自动化测试/异常/离线备用；适配层支持替换，前端直接沿用。该澄清已完整写入[实施文档](agents/S01_MVP实施文档.md)§0/3/4/9/10，不能依据早前“先模拟闭环”的初始默认进入实现。

实际Codex单人接手main / `3a470082052efcd29a61d238d61eb902c6ac85d5`，已跟踪diff/暂存区干净，未知未跟踪 `docs/ERP-openapi.yaml`保留；本轮未读取/哈希/修改/暂存该文件内容。未生成业务代码/应用目录/模拟系统/开发TODO，未调用ERP/模型、未动原型/冻结正文/原专项MD与HTML/原阅读版构建器，没有远端操作。

文档提交 `f3b7551f8096c07c5e3b3bc3ce8d76d9ab19b34e` 固定实施正文、两处导航与精确白名单。正文16章/27表，含最小底座能力矩阵、接口调查后的主来源决策门禁、可替换SourceConnector、标准输入/公开契约、规则冻结、资产/事务/恢复、最小API、既有原型对接差距、阶段输入产出/出口、S01自有未来验收、运行与AI交接提示、完整项目扩展及待确认项；没有新增开发任务清单或可运行业务代码。本轮只增加D-S01-MVP-PLAN这一项design文档记录，不改原19项任务，不把规划或待评审设计标为开发完成。

针对该提交实际执行内存Python检查：正文16章连续/27张表可Markdown解析/13相对链接无断链，无checkbox TODO或业务源码块；源文件与Git对象相同，SHA256 `aeb150234dc4a0deae1a286d2a6c1a58e2d5c879e0318d357e8a823e6194b2ee`。对照基点18个指定原专项/基线/计划/决策/视觉/UI/原型文件字节保全，既有19任务JSON不变，development记录未新增，未创建src/pyproject/migrations等业务入口；定向秘密启发式0发现。`python docs/planning/build_docs.py`、`python docs/planning/check_plan.py`均退出0、18项PASS，CRLF约定下diff --check通过。以上仅文档自检，非接口、软件或业务验收。

D-S01-MVP-PLAN交付REVIEW，负责人独立设计评审NOT_RUN；当前实现规范是待调查后修订的v0.1建议，不伪称企业字段/生产规则已冻结。下一步只有在新授权下开展ERP接口调查并修订本文；不自动编码或开发TODO，不把模拟例子当企业验收。最终证据提交从Git读取，避免填写自身SHA；未跟踪YAML继续保留，完成后停止。


## S01 专项设计 HTML 阅读版追加交付（2026-11-11）

用户追加授权“再做一份方便阅读的HTML版本”，覆盖上一轮“不生成HTML副本”的交付限制；Markdown仍是唯一设计正文，业务结论不改。Codex单人接手main / `c7e3dca74295a737eab40f8e46445e5d93a94f95`，status/diff/暂存起点干净，无代理、无远端写入。

阅读版为 [S01专项设计HTML](agents/S01_补货Agent专项详细设计.html)，直接离线打开。11章、9张内嵌SVG、9份讲稿和6段伪代码完整保留；章节导航/图表速查、图表放大/缩放/适宽/拖动、讲稿展开、Mermaid图源与复制入口、深浅主题记忆、打印可用。图表在构建期用已有本地Mermaid渲染，HTML不加载外部脚本/字体/资源。页首注明新增授权和原文历史范围，不手改原文来迁就阅读版。

文档构建工具 `node docs/agents/scripts/build_s01_reading.cjs` 从MD生成；`--check`只读验证。HTML带MD与构建器指纹；正文改变或构建器改变时检查拒绝旧HTML。此工具只服务文档，不是S01业务代码；未修改前端原型。必要索引两处与精确白名单已补。阅读版实现提交 `a0c26153e65020d1b061556e84b27b74dce9964e`；最终证据提交由Git读取，不写自身SHA。

针对该提交实际运行 `node docs/agents/scripts/build_s01_reading.cjs --check` 退出0：1440/1920/390×深浅6组布局、9图弹窗/缩放/适宽/Esc与焦点恢复、鼠标拖动/手机弹窗、主题切换与记忆、讲稿/图源展开和全部页内链接均PASS；11章/9图/9稿/6块伪代码匹配，浏览器错误和HTTP请求0。作者查看桌面、原尺寸图表和手机深色截图，临时截图不入库。首轮390px长hash导致12px页面溢出FAIL，修复页尾换行后重建重测通过，未隐藏内容规避检查。

HTML SHA256 `eb48d77111d005a9460ae27c5081eacc08ffc49864de918b23071300df92dd71`，476025字节；MD SHA256 `53684a012e65115c320569cb6acf4737dc51edc0a3523f59a9ff01f6ccf1ed9a`与接手Git对象逐字节相同。秘密启发式针对HTML/构建器/两索引/白名单5文件0发现；最终复核：源MD及五份基线/视觉/UI/原型等14个指定文件相对接手提交字节不变，其余18项任务JSON未改；本轮10份精确文档/工具/派生变更秘密启发式0发现；build_docs.py与check_plan.py均退出0、18项PASS，CRLF约定下diff --check通过。

收尾期间发现新增未跟踪 `docs/ERP-openapi.yaml`，初始接手时不存在。归属未知，原样保留，未读取/修改/暂存；未执行ERP调查。首次保全脚本因要求未跟踪为0而报FAIL，识别为并发新增文件后定向复核本轮范围，未删除文件使检查通过。

TASKS的D-S01-01仍为REVIEW，负责人独立设计评审/真实ERP/模型/业务/MC验收均NOT_RUN。未调查ERP、未登录、未开发业务、未修改冻结需求/架构/原型、不拆MVP或TODO、不推送。完成阅读版后停止，等待负责人评审。


## S01 第一阶段专项详细设计交付停止点（2026-11-11）

最新授权已转为用户明确要求的D-S01-01第一阶段设计；以下治理/发布/原型条目是历史事实。当前唯一专项正文为[S01补货Agent专项详细设计](agents/S01_补货Agent专项详细设计.md)。实际Codex单人编写，无代理；接手main / `895167c7c1b76db2e46209fa4480e4819e65a06f`，工作区/暂存区干净。实测已有origin，保留不改；本轮无push或远端检查，不以旧交接“无remote”覆盖当前事实。

设计提交 `858af84b8527adee98a26a2e87ed8fdf10d81e90` 固定主文档、两处导航及该主文档精确白名单；后续只补本节/台账/派生视图/检查证据、图例文字澄清及两份原有治理文件漏列的白名单路径。图源与伪代码未变。TASKS为唯一状态源，负责人独立DESIGN_REVIEW未运行，不标ACCEPTED，不视为开发完成。

正文包括定位/业务价值、设计思想、逻辑输入输出与规则来源、质量降级矩阵、1张架构图、3张意图图、5张时序图及9份逐字讲稿、6块Python风格伪代码、复用边界和Q01—Q11/X01—X06问题/差异。沿用O01统一任务/预算/计划/报告，S01确定性Workflow，B01唯一计算，B02构造候选并回调B01评价，可选A01解释；无LLM意图分类器/直接采购/新Agent平台。API与Worker各在本进程装配同一O01模块用例，不形成第二调度中心。

实际检查：PowerShell临时脚本经stdin运行Node，已有Mermaid 11.4.1 + Playwright + 本地无头Edge逐图parse/render，9/9 PASS、有效viewBox/非空文本、pageerror和HTTP请求均0；脚本和图像不入库。首发Edge因沙箱spawn EPERM失败，获工具离线渲染审批后重跑通过。设计提交主文档字节与被测内容一致；图源集合SHA256 `53a5e74f127c28eadcb512b9c2194c624655eacd091d2690206ef1ba0290e568`。Python内存结构检查：9图9稿按序紧随，6块伪代码、14正文相对链接无断链，无业务目录；作者逐项边界自检PASS，不代替独立评审。

`python docs/planning/build_docs.py`退出0；`python docs/planning/check_plan.py`最终退出0、18项PASS。首轮17/18：tracked-whitelist发现基点已跟踪的LICENSE_REVIEW.md和connector-publication-check.json漏列，经原提交/授权核对仅补精确路径，未修改其内容。普通diff --check因既有CRLF新行报FAIL，保留原换行后以 `git -c core.whitespace=cr-at-eol diff --check` 重验。最终内存Python检查PASS：图源/伪代码与设计提交相同；其余18项任务记录完全未变、未增任务ID；五份冻结正文、视觉/UI/原型及两份旧治理材料共14个指定文件字节不变；相对基点只变更9个获准文档/派生/白名单文件，定向秘密启发式0发现、未跟踪文件0。最新交接提交从Git读取，不伪造自身SHA。旧检查/证据不改写为业务PASS。

未做：真实ERP/API调查或登录、模型用途验证、B01/B02工程或业务计算测试、S01业务/MC验收、真实审批/采购执行；均NOT_RUN。未动五份冻结基线、DESIGN、UI规格与原型；无MVP文档、开发TODO、应用代码或独立HTML/PDF/SVG展示副本。本轮不处理公开发布许可及原发布阻碍。

评审需负责人签认试点身份/单位与分桶镜像、需求/预留/逐日及缓冲口径、未收供给/交期终点/MOQ倍数、质量依赖及降级矩阵、实际数据可得性、最小报告/API与是否启用解释；详细影响在正文§10。原型D1日历/同日顺序与R的D0后7天存在真实待决语义，未擅改。第一阶段设计完成后停止，等待负责人评审；不自动进入ERP调查、MVP/TODO拆解或任何开发。


## 既有 GitHub 仓库发布核查停止点（2026-11-11）

用户明确仓库已创建、不得重建，只准真实 Git 推送并保留历史，禁止逐文件上传替代。Codex 接手 main / `6247e8356d5892f3ed5a1e7007e632e39263b458`，工作区干净、无 remote。只更新许可核查、公开准备、TASKS附记及本交接，未动业务实现/原始第三方资源。

连接器账号 yujie-213；目标仓库存在且 Public/有写权限，heads 查询409空仓库。无 push/pack 导入接口；create_commit 无法保留本地 commit 的原始元数据和 SHA。未调用远端写入，未配置 origin、未强推或改写历史。远端提交/目录/README 发布后核验 NOT_RUN。

许可已定向核对：Mermaid 两版本主许可 MIT；交互 HTML 已带 Archify/字体完整公告，但完整依赖许可及实际内嵌品牌图标条件尚未闭合，不能解除公开阻碍。事实、来源、指纹与恢复条件见 [许可核查](governance/LICENSE_REVIEW.md) 和 [连接器记录](governance/connector-publication-check.json)。本轮 build_docs.py 退出0（仅生成本地阅读版，不代表GitHub发布）；check_plan.py 退出0，18项PASS；核查JSON结构/4个历史blob记录检查PASS；普通diff --check曾因CRLF报告FAIL，恢复原文件换行后按cr-at-eol重验；最终真实提交由 Git 查询。许可通过且有已认证 Git 传输通道后才能普通 push，并重新检查远端祖先关系及发布结果。


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
