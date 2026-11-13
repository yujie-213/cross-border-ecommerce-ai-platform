## 当前公开授权（2026-11-13，覆盖旧材料类别停止点）

负责人明确允许普通教学截图、教学数据、非敏感业务/测试报告与开发证据公开，无需逐张人工审核。不可认证的模型授权ID/任务关联属于可发布元数据。真实API Key、Token、Secret、密码、可复用凭据及实际第三方敏感资料仍不得公开；普通教学记录不是笼统的发布阻断依据。

两份此前非自有SKU报告仅含教学ERP数量/约束及AI说明，没有个人/客户/支付资料或独立保密标记；8张教学截图可保留。重新核实完整新增历史无未解决凭据问题，允许直接正常合并原开发分支至main，不要求另建安全快照。P1/P2阶段PASS不授权采购执行，实际合并/验证/推送以TASKS和[本轮发布证据](../evidence/S01-CARTON-FIX/release-20261113.json)为准，下文旧停止记录按历史时点阅读。


# 文档治理与 GitHub 公开准备

## 本轮既有仓库增量同步（2026-11-11，旧停止点保留为历史）

负责人本轮明确要求将ERP调查及MVP修订完成后同步到既有远端。实际origin为 `https://github.com/yujie-213/cross-border-ecommerce-ai-platform.git`；连接器登录与本机Git Credential Manager账号均为yujie-213，目标Public仓库有写权限。只读ls-remote实测远端main为 `895167c7c1b76db2e46209fa4480e4819e65a06f`，是本地接手HEAD的祖先；未创建新仓库、未修改origin、不重写历史。

本次只按普通fast-forward同步已审查的自有文档、文档工具及原图源派生SVG阅读版与脱敏调查证据。相对上述远端祖先没有新增/修改Mermaid运行时、Archify HTML、字体或其他既有第三方包；原冻结基线/原型也未改。原始 `docs/ERP-openapi.yaml`为本地调查输入，保持未跟踪、不上传；认证信息和原始敏感响应未落库。本轮增量安全与来源检查不等于宣布历史第三方许可缺口闭合，不扩展为发布那些未审材料。

推送前重新核对目标、暂存内容/历史增量和祖先关系，禁止force；推送后以远端main与本地提交相等验证。实际命令/结果、最终SHA和停止点见本轮TASKS/HANDOFF及最终Git查询，不以此前“空仓库/无remote/未推送”描述当前状态。连接器只核对身份/元数据，真实本地历史同步使用Git传输，不用逐文件API重建提交。


## 最新核查（2026-11-11，覆盖下文历史停止点）

用户已自行创建仓库，明确禁止再次创建。当前连接器账号 yujie-213，既有 Public 目标为 [cross-border-ecommerce-ai-platform](https://github.com/yujie-213/cross-border-ecommerce-ai-platform)，有写权限；heads 查询返回409空仓库。未推送、未配置 origin、无远端 SHA。当前连接器不支持本地 Git push 或原始提交导入；未以 Git Data 重建提交或逐文件上传代替。许可核查已细化，但仍有主许可/依赖材料及图标条款缺口，未通过发布门槛，详见 [许可核查](LICENSE_REVIEW.md) 和 [原始记录](connector-publication-check.json)。下文“尚未创建仓库”和账号未验证等是此前事实，不能作为当前结论。


本轮仅做文档治理、公开安全检查和 GitHub 发布准备，不开发补货 Agent、不启动正式前端、不调整业务规则或现有任务状态。开始时为 main / `f113229fa6eefc271b811e290858d596174ea52e`，跟踪区干净、无远端，另有85个既有未跟踪文件。用户已明确同意现有 Git 历史提交邮箱公开；不改写历史。

## 发布停止点

**尚未创建 GitHub 仓库、配置 origin 或推送。**

1. 本机未发现 `gh` 命令，也未在常见安装位置发现 GitHub CLI。当前登录账号、仓库创建权限与同名仓库是否存在均为 NOT_RUN。
2. 现有 Mermaid 包及独立 HTML 内嵌运行时的完整第三方再分发许可尚未核验。包内已有许可注释均保留，详见根目录 THIRD_PARTY_NOTICES.md；本轮不添加项目 LICENSE。仅添加 `.gitignore` 不能解决历史中的第三方材料风险。

按照用户“无法确定公开风险就停止”的要求，公开发布保持阻断。安装/登录也不会自动解除许可阻碍。目标仓库名为 `cross-border-ecommerce-ai-platform`，目标账号未验证，不虚构 URL、Public 状态或远端 SHA。

如后续负责人先完成许可核验，再由用户手动安装与登录：

```powershell
winget install --id GitHub.cli --exact --source winget
gh auth login --hostname github.com --git-protocol https --web
gh auth status --hostname github.com
gh api user --jq .login
```

不使用 `--show-token`，不把凭据写进命令、文档或 Git。后续执行者须重新检查安全结果、登录账号、同名仓库和 origin；符合本轮授权条件后才能创建 Public 仓库及普通 push。若同名仓库已存在或 origin 指向其他项目，应停止报告，不覆盖、不改名、不强推。

## 治理与验证范围

当前分类导航见 docs/README.md；逐文件旧路径、新路径和治理前指纹见 migration.json。五份原文快照位于 docs/archive/governance-20261111，当前正文只修链接；旧计划17份原字节保留。历史版本在docs/archive，不建立第二份当前权威正文。历史固定报告和模拟原型证据保留，原型源码、交互测试、fixture 与样式不改。

`audit.py` 扫描当前文件、ZIP 内部成员与全部可达历史及本地不可达 Git 对象的 blob/提交消息；仅输出候选位置，不回显潜在秘密。Git 作者邮箱另行记录用户明确同意。扫描不将 Git tree 二进制对象内的数字误判为手机号。

没有应用配置契约，不虚构 `.env.example`；当前静态预览不需要环境变量。`.gitignore` 覆盖凭据、虚拟环境、缓存、日志、数据库、模型和本地检查产物。`.gitattributes` 保留按字节取证的历史文件，不进行入库换行转换。最大现有资源约3.3MB，无需 Git LFS；未引入模型权重或大数据。

实际测试、文件扫描、路径检查、任务/规则保全结果记录在 audit.json。历史证据中的失败不删除，原有 REVIEW 不改为 ACCEPTED。新仓库未发布，README 的 GitHub 实际展示、默认分支和远端 SHA 均为 NOT_RUN。

额外格式检查 `git -c core.whitespace=cr-at-eol diff --cached --check` 返回2：151处既有空白问题位于独立图示HTML、第三方Mermaid及归档HTML/diff。为保留原文和第三方字节未批量格式化；该项如实记录FAIL，不影响已通过的语法、链接和模拟交互检查。

## S01 MVP 门槛

现有材料足以继续S01专项设计与负责人评审；尚不具备直接开始正式MVP编码的全部条件。UX-S01-01待最终签认，完整D-S01-01、试点范围、库存/供给/需求口径、质量/时效矩阵及必要契约仍待冻结。按PLAN完成设计后再领取最小工程与真实只读链路任务，不把本轮文档治理当作开发授权。
