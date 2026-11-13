> 日常使用增量（2026-11-14）：当前默认入口为[Windows一键启动与管理员登录](local-platform.md)及[README](../../README.md)。下文保留原阶段/开发测试运行方式；临时Token、动态端口和900秒演示不再是日常流程。本地loopback HTTP Cookie例外以新契约为准，旧测试配置保持其原安全语义。

# 第一大阶段工程底座运行说明

当前验收只涵盖工程底座。任务状态与逐项证据唯一见[TASKS](../TASKS.md)；真实ERP/模型/S01业务和S02 MC均未验收，四项业务门禁不解除。

## 安装与显式迁移

已验证Windows10 build19045 / CPython3.13.5 / MySQL8.0.27。其他OS/版本组合未验证。全部运行/测试依赖精确固定在requirements.lock，包括迁移工具；API/Worker启动不会自动迁移。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
.\.venv\Scripts\python.exe -m commerce_hub.infrastructure.database
```

也可显式运行 `.\.venv\Scripts\python.exe -m alembic upgrade head`。唯一迁移链为`0001_foundation → 0002_actor_refs → 0003_delivery_version`；迁移命令只允许`.env`配置的`s01_a01_test_20261112`，用数据库命名锁串行化。初次只创建当前10张模块所有者表及Alembic版本表；0002追加身份修订和会话引用，不存JWT/密码；0003仅追加工作项owner_version以持久绑定投递引用和计划版本。已有数据默认值使无有效身份的旧样本不能执行。没有DROP/TRUNCATE/删库或降级；downgrade会明确拒绝。MySQL DDL不保证事务回滚，本次验证的是失败命令/DML整体回滚，不宣称已做破坏性迁移回退。

`.env`已被Git忽略。数据库字段沿用[示例](../../.env.example)。启用任务入口还需要本机可信`COMMERCE_AUTH_ISSUER/AUDIENCE/SIGNING_KEY`，密钥至少32字节。身份、会话和当前范围须存在于G01受控绑定中；只配密钥不会自动创建账号或授予权限。当前仅实现固定HS256窄接入，不声称企业OIDC/账号生命周期已经接通。真实身份发行方/租户/字段范围仍由负责人确认；未配置拒绝任务访问。

## API与独立Worker

分别在两个终端启动，使用相同配置/代码与迁移版本：

```powershell
.\.venv\Scripts\python.exe -m uvicorn commerce_hub.entrypoints.http.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe -m commerce_hub.entrypoints.worker
```

`/health/live`表示存活；`/health/ready`检查真实连接、迁移结构和可信身份配置。满足时返回200并标`ENGINEERING_FOUNDATION_ONLY`；不表示S01业务就绪，也不要求API在内部启动Worker。缺配置/迁移时返回503；Worker安全退出，不自动迁移或匿名运行。API和Worker生产组合根均为空业务注册表，因此不能受理S01或工程假Handler；工作项只认已注册kind/version，不解释任意导入路径。

现有任务API：`POST /api/v1/analysis-tasks`（Idempotency-Key）、`GET /api/v1/analysis-tasks/{id}`、`POST .../{id}/cancel`（独立Idempotency-Key、expectedRevision）。创建体仅允许SINGLE/scenarioId、显式店仓SKU/字段scope、由注册Handler校验的有限parameters；tenant/主体/计划由服务端绑定，预算和投递上限来自可信配置，不接收客户端预算。未实现S01返回UNSUPPORTED_SCENARIO，不返回假成功报告。当前工程任务终态也始终reportRef=null，真正报告发布归B-05。

Bearer令牌只能通过Authorization头传递；同源浏览器可用`POST /api/v1/session`将已校验Bearer换为Secure/HttpOnly/SameSite=Strict会话Cookie和签名CSRF Cookie。Cookie写命令必须带与会话绑定的X-CSRF-Token及匹配固定COMMERCE_BROWSER_ORIGIN的Origin；冲突Bearer/Cookie拒绝。`DELETE /api/v1/session`撤销当前会话。浏览器Cookie必须HTTPS，不能为了本地HTTP演示关闭Secure。没有密码登录/自动签发令牌或前端角色提权接口。

## 自动化验证与恢复

```powershell
# 无真实MySQL时仅跑纯测试；MySQL类会明确SKIP，不计为PASS。
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider

# 本轮完整工程验证：仅使用现有获准测试库。
$env:COMMERCE_RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

测试使用唯一工程租户/workKind；不清理整个表/库，不接其他项目数据库。存储测试只删除自己新建的随机fixture表。测试产物留在独立测试库并明确SIMULATED_ENGINEERING，不当作真实SKU/业务证据。只有`tests/support/foundation.py`显式注册工程Handler；实际进程测试自动在内存生成随机测试签名密钥、受控身份/范围和令牌，使用同一正式API/Worker公共实现，无生产探针接口或第二调度器。

`tests/integration/processes`会启动真实API和Worker子进程，自动验证API重启、Worker强制终止/租约到期后原task恢复、两个Worker竞争、取消/撤权/重试耗尽，并仅停止自己启动的进程。子进程日志仅留内存检查数据库密码/测试密钥/令牌泄漏，不保存原始日志。用于恢复的数据库身份引用不保存长期Bearer令牌，执行前及条件提交时按当前G01策略复核。

恢复继续使用原task/plan/deadline/预算和attempt记录：工作项至少一次投递，条件提交检查当前token/owner/kind/attempt/计划；旧Worker不能完成新租约。未知usage保持占额，同一logicalCall未知时不能换attempt重新发送；恢复核账与新收费发送分开，G02唯一保存实际usage事实。没有真实模型调用，预算测试中的费用都是显式工程值。API/Worker崩溃后只需按原命令重启，不重建任务、不清库或重置预算。

下一阶段仍为原计划B轨必要公共能力与S01相关准入；本轮不自动开始。真实ERP/模型许可、业务公式/质量规则、企业身份配置和生产部署均不由工程测试放行。
