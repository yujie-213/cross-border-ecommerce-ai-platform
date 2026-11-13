# 本地平台日常运行、管理员与恢复

当前日常入口为根目录Start-Platform.cmd/Stop-Platform.cmd；首次Initialize-Platform.cmd，忘记密码Reset-Admin.cmd。完整首次环境安装及登录步骤以[README](../../README.md)为准，历史临时Token工具不作为默认使用流程。

## 进程与配置

启动器使用持久私有runtime.json和Windows文件锁，管理三个独立进程：API8765、Worker、前端资源及同源代理5173。默认打开http://localhost:5173；不需要开发Vite窗口、S01_API_TARGET或Token。服务无自动到期；关闭监督窗口或Stop入口仅结束同一Windows Job下的子进程，异常监督进程退出也由OS清理。不会按名字/端口扫描或终止其他服务。

正常start先检查Python/依赖、.env/ERP配置、DB连接、迁移、admin和端口。前端构建源摘要改变才执行npm run build；依赖缺失请按README显式安装，不自动npm ci或pip。启动不创建业务任务/会话、不发ERP/AI/采购请求；Worker仍按O01处理用户已明确创建、当前授权有效的持久任务，恢复沿原预算/期限。失效会话的任务不能因重启取得新权限。

sessionSeconds默认28800（300—86400）；apiPort/webPort可调整；modelEnabled/requisitionEnabled保留V2受控装配，不额外授予源业务权限或模型预算。配置更改需停止重启；已有会话按签发截止过期，新配置影响后续登录。私有签名密钥不能每次启动再生成，丢失后旧Cookie无效，但数据库报告/密码哈希不消失。不要公开runtime.json、Cookie或.env。

## 首次初始化、迁移与重置

Initialize是显式前向迁移/本地管理员初始化，当前head0011_local_admin，仅新增G01密码哈希/失败锁定表；旧0010以前链保持。仅获准s01_a01_test_20261112，不自动建库、换库、删数据或降级。已初始化不会覆盖密码。

admin密码隐藏输入两次，随机32字节盐、scrypt N131072/r8/p1、64字节派生值；盐和哈希只存DB，实际哈希也不进入公开证据。签名密钥独立随机生成。Reset-Admin显式改哈希、增加principal revision并撤销其会话；保留所有业务历史，不重置其他主体、ERP凭据或模型费用。

## HTTP及会话

GET /api/v1/auth/config给登录模式；本地模式为PASSWORD。POST /api/v1/auth/login只接受严格username/password JSON和匹配Origin，不返回JWT；成功写HttpOnly会话和签名CSRF Cookie，JWT/DB/Cookie同一时长。GET /api/v1/session恢复当前登录，DELETE /session要求CSRF并真正撤销。失效401清Cookie返回登录，权限403和后端503不当作业务成功。

本地模式拒绝旧Bearer换Cookie；普通用户不能通过传角色、供应商或签认字段提权。超级管理员只授予V2现有平台动作，ERP采购仍要求自有授权、业务关系和必要约束、人工认知确认。REFERENCE_ONLY算法未知不是额外禁购门，真实硬冲突仍阻断。

同源前端代理只转固定本机API，不转任意主机；静态资源仅frontend/dist，不暴露私有目录。Cookie Secure例外只限明确loopback HTTP本地应用，不能据此声称企业远程部署安全。登录连续失败短暂锁定，重置仅有本机/数据库控制权的负责人执行；无账号中心、注册、多角色界面。

## 停止、恢复与排错

Stop写入当前instanceId停止请求；仅监督进程处理自己的实例。重复启动先检查文件锁，沿现有URL打开页面；端口冲突或配置错误不会先杀占用者。业务记录保存在MySQL，停止/重启不清库。浏览器关闭后8小时内重新打开，自动复验Cookie并恢复历史；退出或过期需密码。正在执行任务仍按现有I01租约/权限/预算恢复，不重置或自动创建替代任务。

- 数据库错误：检查.env/服务，不输出连接凭据。
- 迁移错误：显式Initialize，未知状态保留；不可手改版本、drop或清库。
- 登录错误：核对输入或等待短暂锁定；必要时本机重置。
- 前端构建错误：查看私有build.log，按锁文件安装依赖；不会回退成旧静态原型。
- 子服务未就绪/退出：监督器关闭本项目其他子进程并给错误；私有api.log/worker.log/frontend.log仅本机排查。
- 请购UNKNOWN：沿原操作/业务号核查，不能因超时或重启另创建一张。

## 验证与实际边界

完整命令见README。tests/integration/http/test_local_login.py使用隔离MySQL和明确合成ERP测试哈希、CSRF、轮换/过期/重置/错误；原生Windows测试验证重复锁、正常/突然退出仅清理自管进程；代理单元验证payload/文件范围/Cookie头。

真实Edge门控用例tests/browser/s01/local-platform.spec.ts，密码仅临时进程环境输入，不存测试源码/日志；浏览器Cookie状态只在Git忽略私有目录。login用例人工只读全量、旧AI与申请1426读取及拒绝未勾选认知确认；restore/expired不产生新任务。实际测试与历史实测明确分开，不能用合成ERP替代真实结果。

已有V2真实AI/创建submit/幂等恢复证据保留；本轮无必要不重复付费模型或采购写入。真实在途/分批收货净扣、ERP算法/刷新语义和企业四门仍按原限制。合main后仅按负责人实际使用反馈再定UI优化，不自动开始整体重构或其他Agent。
