# 真实模型解释与 Token 核验

2026-11-12，固定实现 `c965a334b6bbc3c689fb334c80f8cf0a9ee84dad`，官方 HTTPS `deepseek-flash`，独立本机 API/Worker 与唯一隔离 MySQL。输入为本批教学仿真 GET capture 经 D01/D02/D03、B01/B02 形成的 quantity 事实和白名单引用，没有发送 ERP 原响应。

**本次用途评测 FAIL：A、B 成功，C 输出拒绝后安全停止，D、E NOT_RUN。** 技术任务 `SUCCEEDED` 且发布了合法 A 规则/解释报告，不能将该任务状态当作五例评测全部通过。真实记录见 [execution.json](execution.json)，原输出离线复核见 [output-validation.json](output-validation.json)。[readiness.md](readiness.md) 保留发送前 NOT_RUN 的历史时点。

| 场景 | 真实调用与解释 | 输入 Token | 输出 Token | 总 Token | 缓存命中/未命中 | 耗时 ms |
|---|---|---:|---:|---:|---|---:|
| A 有缺口 | AVAILABLE；Schema、受控语言、领域事实与引用通过 | 1822 | 211 | 2033 | 0 / 1822 | 1622 |
| B 无需补货 | AVAILABLE；无0件候选，来源与人工确认限制保留 | 1601 | 183 | 1784 | 384 / 1217 | 1587 |
| C 中途缺货 | UNAVAILABLE / INVALID_OUTPUT；保留确定性结果 | 1644 | 181 | 1825 | 384 / 1260 | 1489 |
| D 采购约束 | NOT_RUN，首个失败后未发送 | null | null | null | null | null |
| E 质量调查 | NOT_RUN，首个失败后未发送 | null | null | null | null | null |
| 已发送合计 | 3次 | 5067 | 575 | 5642 | 768 / 4299 | — |

C 的原始 JSON 可以按 Schema 解析，且有结构化 `supportRefs`；但五条文本均缺失必需的句尾 `[ref]`。原策略 `s01-controlled-natural-v1` 返回 `UNCONTROLLED_NATURAL_LANGUAGE`，A01 对外归类 `INVALID_OUTPUT`。离线重验原文再次复现拒绝；没有改原响应、放宽语义门禁或重发。该受控语言策略只验证允许范围内的事实保持，不宣称可证明任意自然语言含义。

## 预算、用量和费用

唯一授权 `s01-backend-20261112-v1`，唯一 task `192fee223c6a429d868bb584b3cf6e15`。原总授权10次/$1，本装配进一步固定为同一持久任务最多5次，600秒期限、单次投递、串行、首次失败停止。实际 `usedCalls=3`、`usedTokens=5642`、无隐式重试或同 logicalCall 重发。成功解释的 G02 usageRef 与持久调用事实匹配；失败的 C 也保留真实 usage。

三次费用、币种、计价版本均为 null / UNKNOWN，未实现 DeepSeek 平台价格表，也没有将发送前估算写成实际费用。每次风险预留 $0.05，剩余 **$0.15 费用预约继续占用**；`actualCost=null` 不表示0，也没有导致 A/B 降级。已知 Token 已结转，未知费用保留至原 attempt 的权威核账事实到达。Token 输入/输出/总数与缓存扩展都直接来自 Provider Adapter 映射，没有编造缺失指标。

当日官方费率页只用于本授权发送上界预检，公开指纹见 execution.json；不是账单或平台运行计价依赖。没有以余下额度建立第二任务、换授权、换 key 或重新发送已发送请求。D/E 的真实模型覆盖留待评审后的明确后续安排；它们的计算/约束/质量行为已有独立 Golden、Mock 和后端进程证据，不能替代真实模型成功。

## 通过与未通过的范围

- 已验证：真实 Provider 响应、A/B 合法解释、C 拒绝降级、Token 记账、费用可空且继续占额、模型不改 B01/B02、公开报告/版本与 G02 回执核验。
- 工程故障和安全负例：601项回归中的超时、取消、迟到、未知、额度、引用/数字/日期篡改、质量/采购越权等。它们是离线注入或真实隔离库测试，不冒称真实 DeepSeek 曾发生所有故障。
- 未通过：五例全部真实解释成功。D/E 未发送，C 原输出未通过受控语言规则；正式企业用途仍未获签认。

本轮进入 REVIEW，等待负责人和星星独立评审。教学模型验证不解除企业数据/规则/安全门，不批准采购，也没有实现前端。
