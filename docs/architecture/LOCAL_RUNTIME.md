# 本地教学运行与认证增量

2026-11-14，消费[本地契约](../contracts/local-platform.md)，不改被冻结的总体设计正文。Windows监督器→OS Job→API/独立Worker/前端生产资源代理；浏览器同源Cookie/CSRF→HTTP路由→G01当前授权→O01任务/既有V2业务。静态代理不拥有ERP或业务写能力；真实数据仍D01/D02/D03，所有AI经A01，采购仍复用P3。

本地持久配置含随机签名密钥；数据库G01仅加本地单管理员哈希/失败锁定表。会话沿既有principals/sessions/grants，默认8小时；重置增加revision并撤销会话，任务/报告/幂等存储不变。启动不签发临时fixture，不清库/自动迁移，不新建业务任务或调用模型/ERP。生产远程TLS、企业身份/行隔离和四项正式业务门不由本地模式代签。

前端保留既有App/V2Workbench，增加最外层账号登录与会话恢复门；开发装配继续原Token界面，普通本地装配只显示账号密码。无新RBAC中心、SSO、Docker、服务治理或前端整体重构。
