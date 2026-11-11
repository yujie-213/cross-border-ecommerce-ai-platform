# 最小文档检查与未来CI约定

当前只运行文档生成与校验，不创建应用CI工程或项目管理平台：

```text
python docs/planning/build_docs.py
python docs/planning/check_plan.py
```

普通正文变更执行build_docs即可；流程图变更按顺序运行 `python docs/planning/build_docs.py --prepare` → `node docs/planning/render_plan.cjs` → `python docs/planning/build_docs.py` → `node docs/planning/render_plan.cjs --browser-only` → check_plan。运行依赖为文档工具Python markdown、Node/Playwright与本地Chromium系浏览器，非业务工程依赖；renderer允许PLAYWRIGHT_MODULE、BROWSER_EXECUTABLE、MERMAID_RENDER_JS环境变量覆盖本机默认路径。不用联网脚本，不安装业务依赖。本文档证据仅针对记录的HTML/hash；修改正文后须重跑浏览器检查。

白名单由 `python docs/planning/repository_audit.py prepare` 生成后须人工核对；`scan`检查工作区白名单内容，`staged`检查暂存blob，`final`只读核对实际仓库/HEAD/剩余未跟踪。不得用工具自动把未知新增文件当已授权；秘密启发式扫描不代替归属/内容判断。file-manifest由prepare生成，最后一次修改/扫描/检查后再prepare刷新。

阻断：必需文件缺失；任务ID重复/无效依赖/依赖环；非法状态；ACCEPTED缺真实提交/适用测试/逐条验收与评审；MD→HTML或进度视图漂移；旧96项映射缺失/改写原历史状态；基线指纹改变；S02或全部B/C能力重新变成S01设计前置；缓存/复杂平台被默认引入；入库内容超出显式白名单或含疑似秘密。

TASKS是唯一状态源；生成视图不人工编辑。已完成不自动ACCEPTED；规则在TASKS，不在此另定义。重要契约/架构变化还需人工核验ADR及消费者/安全/兼容影响；自动检查不能证明真实环境/身份签认或模型效果。

未来CI按实际任务增补：格式/类型→目标单元/契约→真实MySQL集成→恢复/隔离→获准AI评测→专项验收。S01用S01-AC编号；MC01—MC12保持原义，S02相关项待真正实现S02后验证。当前没有运行任何这些业务测试。
