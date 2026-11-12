# 教学ERP真实只读接入：当前消费契约（2026-11-12）

负责人已批准96ba88f工程成果普通合入main及D-S01-DEV-01工程ACCEPTED。当前基线b1813e5，单人Codex集成，分支codex/s01-erp-readonly。本轮明确授权指定教学ERP真实认证/有界只读查询，包括经本地OpenAPI确认无副作用的三个兼容POST；禁止任何业务写入与真实模型。指定HTTPS基址保持不变，仅本Connector按负责人授权使用TEACHING_ERP_ONLY局部关闭证书验证，不沿用生产配置、不跟随重定向。凭据在忽略的.env.erp运行时注入，无凭据/Token/原始敏感响应入Git。

原SKU-A缺已保存标识，不能证明恢复。负责人已确认新试点SKT-OL-XXL（MIMI Apparel US、美国FBA平台仓）；它是通过真实网络读取的教学系统synthetic=true数据，不是生产事实，也不是本地Fixture。真实标识、原响应及参数值仅留data/private/s01-erp-20261112；Git保存最小脱敏资料/引用/指纹。三轴为TEACHING_ERP/NETWORK_READ/OBSERVED_FACT，另保留sourceSynthetic，不把ERP源内模拟标记擦除。

已观察到库存多批次、旧时点/时区与净额口径未签、销售503/兼容超时、未收集合/可售日/独立倍数/质量缺口。因此当前仅实现真实读取→D02观测投影→D03唯一准入manifest/质量→B02在质量门前返回阻断→O01受权报告。B01在不满足输入时必须不执行；这不是核心确定性补货计算验收成功。不得用工程Policy或Fixture冒充真实规则，也不人为补需求/零供给。未来数据与签认规则满足时再使用已批准的规范化输入消费原B01/B02；本次不改其算法和权威结果。

兼容增量：DomainResult仅新增TEACHING_ERP_OBSERVED来源；D02新增观测投影、D03新增始终阻断计算的观测快照公开用例，D04新增观测证据定位。旧工程DTO/快照/ScenarioHandler和默认空注册表不变；新Handler仅显式教学准入装配，参数只接受服务端固定packageRef，G01校验当前精确tenant/店/仓/SKU/quantity，O01唯一拥有任务、预算与报告，G02沿原审计。网络采集在任务创建前固定版本、在事务外执行；任务/重入只消费固定投影，不重新扫描ERP。公开报告只含合法数量观测/缺口与证据，原始参数/记录/秘密不公开。

该来源扩展不授权真实业务模式或采购建议。规则/数据未通过继续BLOCKED，AI安全门原样，AI显示DETERMINISTIC_ADMISSION_ONLY/NOT_ATTEMPTED。消费方为新教学Handler、D02/D03/D04/O01；旧消费者与数据按原路径保留。无新表/迁移/依赖；回滚关闭显式教学装配，既有工程链路保留。验证包括真实教学读取、部分页/503/超时/越权路径/重定向/局部TLS/无秘密输出负例、真实MySQL及独立API/Worker与完整回归。独立业务验收仍由负责人和星星完成，本记录只冻结本轮有界技术消费，不代签业务规则。
