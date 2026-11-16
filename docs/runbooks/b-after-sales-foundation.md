# B V1.0 最小公共后端接续

本轮仅实现 G01 B 资源授权和 O01 受信任务适配，不注册尚未实现的业务 Handler，不连接 ERP／模型。原型入口为 [index.html](../../prototypes/b-after-sales/index.html)，打开方法见 [原型说明](../../prototypes/b-after-sales/README.md)。状态唯一读 [TASKS](../TASKS.md)。

## 显式增量授权

先按原有流程初始化 admin。已有 admin 不重新 initialize／reset；普通启动和登录均不自动补权。新命令使用实际 `g01_local_admin.principal_id`，只写 `g01_b_resource_grants` 与 G02 审计，绝不修改密码、principal revision、session、原 `g01_grants` 或采购授权。

迁移仍用原 `.venv/Scripts/python.exe -m commerce_hub.infrastructure.database`，只允许本机 `.env` 已获准的 `s01_a01_test_20261112`，新增 `0012_b_resource_grants`；没有破坏性 downgrade。本轮测试已经在该隔离库执行正向迁移，未执行本机真实 admin 补权。S01 readiness 接受原 `0011_local_admin` 和新增 `0012`，不因缺 B 表全局拒绝服务；B readiness 单列。

本机私有 JSON 配置须由实际获准范围准备，不能从网页接收。下面仅为格式示例，不是实际授权清单：

```json
{
  "schemaVersion": "1.0.0",
  "configurationVersion": "example-v1",
  "tenantId": "EXACT_LOCAL_TENANT",
  "workspaceId": "EXACT_B_WORKSPACE",
  "grants": {
    "b:case:write": {
      "schemaVersion": "1.0.0",
      "tenantId": "EXACT_LOCAL_TENANT",
      "workspaceId": "EXACT_B_WORKSPACE",
      "resources": [{
        "resourceKind": "CASE",
        "sourceNature": "TEACHING_ERP_OBSERVED",
        "sourceTenant": "EXACT_SOURCE_TENANT",
        "resourceIds": [],
        "allowCreate": true,
        "datasetVersions": {}
      }]
    }
  }
}
```

命令默认 dry-run：

```powershell
.venv/Scripts/python.exe -m commerce_hub.entrypoints.grant_after_sales --config data/private/b-grants.json
.venv/Scripts/python.exe -m commerce_hub.entrypoints.grant_after_sales --config data/private/b-grants.json --apply
```

apply 必须复用核对后的同一配置。命令键绑定 installation、实际 tenant/principal、配置版本及 hash。同配置重跑零新增；已撤销、收紧、revision 改变或配置不同均冲突，不覆盖。所需 B grant 与审计在同一短事务内提交，失败整体回滚，成功后独立连接回读。此命令不负责以后显式修订已有 B 授权。

资源范围 v1 包含精确 tenant/workspace、CASE/POLICY/DATASET、来源及资源 ID 或创建父权限；DATASET 子资源还需精确版本。禁通配、教师资料与客户端 actor/mode 自授。父权限仅允许创建，不授权任意已存在对象。未来领域 API 必须从持久资产解析归属后调用 G01；案件关联 ERP 时还须按已冻结设计叠加 sourceRead 对象／字段约束，不能借 B grant 扩大原 S01 读取。

## 任务与启用

`COMMERCE_B_ENABLED` 默认 `false`。当前没有正式 Vue 或 B 业务场景注册，开启 flag 不会凭空得到案件／分析能力，也不会启用模型网络。已注册的受信 `HandlerSpec.task_authorization` 由服务端选择 `BTaskAuthorization`，不能由请求传入。

未来 CASE/DATASET 在消费时分别注册对应 Handler；传入服务器已解析资源范围。B 任务创建、读取、列表、报告、取消、Worker start/checkpoint/commit、预算预约／发送及发布都复核 B task 动作及相应领域动作。scope 版本未知、策略缺失或场景版本不匹配均拒绝，不回退旧 SKU 权限。旧 Handler 未配置 adapter 时保持原任务路径。

通用读取／取消沿用 `/api/v1/analysis-tasks/{taskId}` 及 `/report`、`/cancel`。新增：

- GET `/api/v1/task-history`：逐行按持久场景和 scope 授权的混合索引，默认 20、最多 50，每页最多扫描 200 行，空页仍可能有 nextCursor。游标绑定当前用户／会话／工作区，只携带签名位置及 ID 摘要，不返回受限任务 ID、参数和计数。
- GET `/api/b/v1/tasks?workspaceId=…`：同一索引按精确工作区过滤，模块关闭返回 503。
- GET `/api/b/v1/status`：独立 B readiness，关闭时 DISABLED，授权表就绪时 FOUNDATION_READY，不表示业务链已实现。

原创建 DTO 仍拒绝 BResourceScope，防止客户端自行声明资产归属。后续领域 job API 在 CASE/DATASET 阶段解析对象并调用现有 TaskService；本轮没有开放通用 B 创建入口。模型预算继续存原 task，UNKNOWN 不释放、不重置、不盲重发。关闭 B 时 Worker 不领取 B 工作，原 S01 可继续运行。

定向测试在 `tests/security/test_b_resources.py`，真实 MySQL/G01/API/Worker 与合成业务 fixture 分别标注；进程用例复用已有 OwnedProcess，实际重启 API、终止并重启独立 Worker，核对同 task/deadline/budget。浏览器用例在 `tests/browser/s01/b-after-sales-prototype.spec.ts`，只访问本地 HTML，不能作为真实售后业务验收。

下一步：负责人确认原型方向后，依下一次连续授权接续 FOUNDATION.F3、CASE 和 DATASET；三链、风险及单品／批量补货联动仍全量必做。政策正文及发布责任、完整教学包／真实映射与绑定、B 独立模型用途和预算须在相应消费者启用时落实，不挪用 S01 授权。
