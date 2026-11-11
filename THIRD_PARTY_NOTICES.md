# 第三方材料与公开边界

项目尚未添加项目级 LICENSE。本文是来源与待核查事项清单，不授予任何第三方资产的权利。

| 材料 | 已观察的来源或声明 | 当前判断 |
|---|---|---|
| `docs/agents/assets/mermaid-11.4.1.min.js` | 包内包含 DOMPurify、js-yaml、Lodash、Cytoscape 等许可注释 | Mermaid 主许可与全部内嵌依赖的版本、完整许可文本和再分发要求尚未核验 |
| `docs/architecture/logical/assets/mermaid-11.15.0.min.js` | 来源与 SHA 在同目录 mermaid-source.json；含多项 bundled license information | 尚未完成完整上游来源与再分发核验 |
| `docs/architecture/interactive/` 的独立 HTML | 本地架构图工具产物，内嵌运行时代码 | 生成图的业务内容与内嵌运行时授权应分别核查，不能由项目发布授权替代工具资源许可 |
| UI 参考研究 | docs/ui/RESEARCH.md 列明 SAP、Airtable、Shopify 分析来源 | 未下载或复制品牌字体、Logo、截图及整篇原文；原型自行实现，来源不代表品牌背书 |
| 文档与原型截图、模拟数据 | 仓库内文档阅读页与本地模拟原型；数据用途及限制在产品规格列明 | 扫描及人工截图检查不能替代全部内容权属确认；不声称是真实企业案例 |

保留现有包内声明与历史文件。未经核验，不将这些资源重新声明为本项目自有或按某个项目开源协议统一授权。完整再分发声明仍不确定，因此当前停止 Public 发布；不能仅靠忽略当前文件隐藏已进入 Git 历史的材料。
