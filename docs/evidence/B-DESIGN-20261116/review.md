# B V1设计自检与交付说明

2026-11-16，基点2547d1e23ef8cbc991a6e238df9961c35a551696；Codex单人、设计自检，不代替负责人或星星独立评审。

- 交付：复用差距、三链详细设计、产品操作、分阶段实施与覆盖四份正文；TASKS新增一项设计REVIEW及六项实施TODO，原任务JSON语义和需求正文保持。
- `python docs/planning/build_docs.py`：PASS，重新生成PLAN和台账派生视图。
- `python docs/planning/check_plan.py`：最终18项PASS。
- `python docs/evidence/B-DESIGN-20261116/check_design.py`：最终11组PASS，包含冻结需求字节不变、逐需求映射、18个AC、链接及真实代码路径、任务shape/DAG、设计与开发状态。
- `node docs/planning/render_plan.cjs --browser-only`：本地PLAN三宽度×深浅主题检查PASS，见现有browser-check.json；未进行B正式页面开发或业务浏览器验收。
- `git diff --check`：PASS；逐文件检查仅文档及文档检查工具，未知docs/ERP-openapi.yaml未读未改未入提交。

初次检查曾失败：复用引用遗漏frontend/src前缀，以及静态检查标记使用英文teacher与正文中文不符，均已修正。文档生成器在Windows写出CRLF导致无关行差异，已按Git原文件逐行保留未改字节、仅新行LF，消除整文件噪声。首次全局文档检查因PLAN更新后旧浏览器指纹失效而FAIL；无头Edge首次沙箱spawn EPERM，获常规工具执行许可后仅重做本地文档布局检查，最终18项通过。未修改检查器放宽既有检查。

人工语义自检：三链全部覆盖；ERP及独立教学分源；30×24小时、20订单-SKU/20件、10个百分点且3件、UNKNOWN均保持；政策原文和发布责任不代签；风险suspected不算有效、确认默认30天、单店显式仓及当前授权重验；单品与批量同端口，失败未核实、历史与当前分列；不把风险传入库存指标、候选或采购资格。AI数值只引用程序结果，客户和政策文本不能增加权限。

检查限制：静态覆盖证明有设计位置，不证明业务正确实现。B Mermaid保留图源及围栏检查，未宣称本轮全部渲染；无B业务代码、迁移、ERP联网/写入、模型调用、全量后端回归或三AC实测；以上均NOT_RUN。费用与既有预算无变动。未来ERP原生完整群组、政策内容、映射绑定和B模型启用须实证或明确授权；本轮无新增必须改变冻结合同的待决事项。

公开审查范围仅本轮新增／修改文档和检查脚本；未读取.env等凭据、未引入客户原始记录。提交普通推送当前分支，不合main。提交SHA及远端一致性由Git实际回读，避免本文自引用。
