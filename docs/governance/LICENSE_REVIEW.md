# 第三方许可增量核查（2026-11-11）

结论：**BLOCKED，尚未满足公开发布门槛**。已实际核对主许可及本地声明，不能把本轮风险识别视为全部依赖许可清单已完成。原始包、交互图、历史提交均未删除或改写，未增加项目级 LICENSE。

负责人 Codex；分支 main，起点 `6247e8356d5892f3ed5a1e7007e632e39263b458`，起点工作区干净、无 remote。范围仅本报告、第三方声明、公开准备、任务附记、交接及核查证据。机器可读事实与历史对象指纹见 [核查记录](connector-publication-check.json)。

## 已核实与缺口

- Mermaid 11.4.1、11.15.0 的上游版本标签主许可均为 MIT，版权人为 Knut Sveidqvist。本地两个 min.js 包未发现该版权声明；现有 bundled license 注释不能代替主许可全文。须补齐主许可和完整内嵌依赖的版权/许可清单。11.15.0 文件 SHA256 与已有 mermaid-source.json 一致；11.4.1 上游包字节对应关系尚未验证。
- 本地 11.4.1 声明 DOMPurify 3.2.1、js-yaml 4.1.0、Lodash、Cytoscape 及若干来源代码；11.15.0 声明 DOMPurify 3.4.0、js-yaml 4.1.1 等。声明不是完整依赖证明。已读取 DOMPurify 3.2.1 上游许可，允许选择 Apache-2.0 或 MPL-2.0；其余版本/依赖全文及再分发材料仍未逐项闭合。
- 两份交互 HTML 均含相同的 19,521 字符 `archify-software-notices`，包含 NOTICE、Apache-2.0、历史 MIT 和第三方公告；不再笼统视为完全无运行时许可。字体 CSS 内含 JetBrains Mono 的版权及 OFL-1.1 全文，上游 OFL 已核对。固定字体子集字节来源尚未独立验证。
- 交互图公告列出 Simple Icons 集合许可与图标独立条件，包括 Jenkins/Rust 的 SA、Vue 的 NC-SA，以及品牌/商标条款。必须核对实际内嵌矢量、署名和变更说明；公告提及不等于实际内嵌，也不能据未显示就推定没有打包。尚未完成该核查，不能用 Archify Apache-2.0 一概覆盖图标。
- 对全部可达 Git 历史中匹配的 Mermaid 包和交互 HTML 收集 blob/SHA256 指纹；这是定向核查，不能替代全量第三方 SBOM 或历史授权证明。后续补充声明不能使缺声明的历史快照自动取得授权。

## 已读取的上游原始材料

- [Mermaid 11.4.1 LICENSE](https://raw.githubusercontent.com/mermaid-js/mermaid/mermaid@11.4.1/LICENSE)
- [Mermaid 11.15.0 LICENSE](https://raw.githubusercontent.com/mermaid-js/mermaid/mermaid@11.15.0/LICENSE)
- [DOMPurify 3.2.1 LICENSE](https://raw.githubusercontent.com/cure53/DOMPurify/3.2.1/LICENSE)
- [JetBrains Mono OFL](https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/OFL.txt)

首次尝试 Mermaid 的 `v11.x` 标签返回404，已改用真实 `mermaid@11.x` 标签读取成功。Vue 固定版本 LICENSE 页面读取503，未视为已核实。

## GitHub 通道核查

连接账号 `yujie-213`；既有目标仓库 `yujie-213/cross-border-ecommerce-ai-platform`（ID 1453919821）为 Public，连接器返回 push 权限，默认分支名 main。查询 heads 返回409 `Git Repository is empty.`，远端 SHA 不存在，文件结构和 README 的发布后检查为 NOT_RUN。

当前工具目录没有本地 Git push/send-pack/pack 导入能力。Git Data 的 create_commit 只接受 message/tree/parents，不能导入原始 commit、作者/提交者时间和签名，无法原样保留本地历史 SHA。没有调用任何远端写接口，也没有逐文件上传、创建仓库、配置 origin 或改写历史。

恢复条件：先闭合上述许可缺口，再使用具备本地 Git 传输能力的已认证通道；普通 push 前重新检查目标和远端 refs。如已有提交，先验证祖先关系，不覆盖、强推或重写本地历史。成功后核对远端 SHA、目录和 README。当前连接器能力限制独立于仓库写权限，不能通过重试 create_commit 解决。
