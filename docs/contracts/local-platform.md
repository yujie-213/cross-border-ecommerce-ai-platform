# 本地教学产品启动与单管理员鉴权契约 v1

2026-11-14；当前V2分支029e79e/main e3591aa。负责人明确授权本轮产品化和通过验收后的普通合main，不改B01/B02/ERP数据。

- 单一Windows启动器管理三个独立子进程：FastAPI API、Worker、前端生产资源及同源API代理。仅loopback，默认web5173/API8765；端口由私有配置可调整，不动态要求用户复制。Windows Job Object随监督进程结束清理本项目子进程，文件锁防重复启动；停机请求只影响该实例，不按端口/PID通杀其他服务。
- 运行不设900秒关闭时间；启动只做依赖/配置/数据库/迁移版本/端口/构建与就绪检查。显式initialize才执行当前获准隔离库的前向迁移，日常start不得迁移、清库、创建业务任务或调用ERP/模型。
- G01新增一张每本地部署租户仅一个admin的凭据表，固定平台principal，用户名admin；无注册/角色管理/SSO。CLI以getpass输入，数据库仅保存随机盐scrypt哈希；scrypt N=2^17/r8/p1，参考[OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)与[Python3.13](https://docs.python.org/3.13/library/hashlib.html)。签名密钥独立随机生成到Git忽略本地配置，不从密码派生，不每次启动重置。
- 密码POST /api/v1/auth/login要求同源Origin/JSON，错误统一，不回显输入；持久失败计数和短暂锁定。密码重置仅本机显式CLI，撤销旧会话并增加principal revision。SQL锁内仅状态变更，哈希在锁外。
- GET /auth/config暴露登录模式；GET /session验证当前Cookie恢复登录；DELETE /session继续服务端撤销、CSRF与退出。登录随机新jti，JWT exp/数据库expires_at/Cookie Max-Age同一截止，默认28800秒，可配置300—86400秒。HttpOnly/SameSite=Strict；HTTPS使用Secure，明确仅loopback HTTP开发入口允许非Secure，禁止外部HTTP。
- 本地账号模式不启用旧Bearer换Cookie入口；开发测试程序集保留旧入口及旧证据，UI根据服务端模式展示，普通流程只有账号密码。401清除失效Cookie并回登录，503明确错误不无限跳转。刷新/浏览器重开/服务重启复用持久签名配置和有效会话。
- 超管获全部当前V2平台动作权限，保留既有app tenant以读历史；读目录是已授权全教学租户，采购仍由已有自有教学scope策略控制，不因平台超管扩大ERP业务权限。不跳过人工认知确认、价格、单位、MOQ/整箱或提交前复读。
- 迁移0011只追加G01本地管理员凭据表，旧迁移与报告不变；普通启动不自动初始化会话或重签历史身份。无新框架或依赖。
- 验证：全量后端/前端/类型/构建、真实Windows启动停止/重复启动/端口占用与进程所有权、真实浏览器密码登录/错误/退出/过期/重启/旧历史/新只读批量。复用已有真实AI/ERP请购证据，不伪造联网，不为此另建采购单或重置模型预算。通过后正常合main，main实际启动/主要功能复验及文档同步。
