# UX-S01-01 原型交付与验证回执

交付日期：2026-11-11（Asia/Shanghai）。唯一任务状态见 TASKS.md 的 UX-S01-01；本回执不宣告业务验收，也不关闭 D-S01-01 完整专项。

## 打开与评审

直接打开项目内 `prototypes/s01/index.html`，可在浏览器离线操作。没有外部字体/脚本/图片/CDN，没有 ERP/模型请求；不需要启动正式工程。原型预览已请求在当前 Codex 浏览器面板打开（工具返回 queued）。

主要文档：根目录 DESIGN.md；PRODUCT_SPEC.md；RESEARCH.md；ALIGNMENT.md；DESIGN_NOTE.md。功能/流程以产品规格与可操作原型评审，视觉以 DESIGN.md 评审。完整来源链接在 RESEARCH.md，可追到三份原始 DESIGN.md。

## Git 范围

开始分支 main，HEAD `482e83d4f0af2f64b9eaad1bc0279b76938d6b70`，已跟踪 diff 为空。85 个既有未知文件保持不动，观察与指纹见 workspace-observation.json。五份设计基线不改；未创建 src、依赖锁、数据库、正式前端、远端或部署。

实现提交 `8140d40439517f957044537fdffa11f2c5a6463e`；延期曲线/失效提示修正提交 `9a7c9a34bd4079fbdb8bef65b80c7dcdea224df4`。后者为最终浏览器被测版本；C2仅补证据、台账、README预览说明及文档校验脚本，不改原型实现/fixture。交接提交SHA从Git实时读取，避免回执自引用。

## 验证与限制

前端验证命令 `node prototypes/s01/check.cjs`：15组交互检查，覆盖四页、搜索/组合筛选/排序/导出、正常和阻断、D8延期、角色分离、拒绝理由、安全显示输入、确认/提交分离、批准不执行、原键核对、数量变更与未评价阻断、撤销/过期、模拟任务取消/降级/YIELD、重置、四种宽度和键盘弹窗。

宽度为1920/1440/1024/390；每个宽度检查工作台、列表、正常详情、阻断详情与审批入口，共20个布局组合。实跑结果：15组全部PASS，20个布局组合通过；页面错误与HTTP网络请求均为0。原型浏览器测试不能验证真正的并发、幂等、权限、预算或业务计算。

原始失败保留：browser-check-initial-launch-fail.json 记录沙箱启动 Edge 的 EPERM；browser-check-test-harness-fail.json 记录测试脚本参数引用错误；browser-check-mobile-fail.json 记录390px页面曾撑宽至462px。随后修正测试脚本、网格最小宽度与窄屏导航。另保留browser-check-before-visual-correction.json：该次自动检查曾PASS，人工截图发现延期基线误含候选供给，已在最终被测提交修正并补充逐日反例断言。最终结果只认匹配当前源文件指纹的browser-check.json。

截图在 prototypes/s01/evidence/，包含工作台、列表、正常详情、延期、质量阻断、待审批、已批准和窄屏。已人工查看桌面工作台/列表/详情/审批及窄屏工作台/详情，检查信息层级、截断、滚动与操作位置；最终修正后重新生成全部截图并复核延期图，未发现页面溢出或错误的基线混用。

设计自检命令：`python docs/ui/check_design.py`，PASS；9组主要颜色对比满足所列阈值，设计说明462字，五份基线与85个未知文件指纹不变。design-review-palette-check-fail.json保留校验脚本曾不识别三位十六进制简写的失败，已修正脚本后重跑。此为作者自检，不代替独立评审或完整无障碍验收。

文档命令：`python docs/planning/build_docs.py`、`python docs/planning/check_plan.py`。前者从TASKS生成状态；后者检查17项文档规则，不能当成业务测试。

ERP/OMS/WMS/CRM、B01/B02、真实模型、服务端认证/权限、真实审批/审计/有效期、外写/恢复、MC/S02/S01业务验收与生产验收全部 **NOT_RUN**。负责人尚未独立签认；正式前端开发仍未获准。
