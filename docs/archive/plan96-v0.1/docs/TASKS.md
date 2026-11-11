# 唯一任务台账 v0.1

> 本轮规划草案，待独立审查。任务定义与状态仅在本文件维护；每条任务的JSON是权威记录，其他视图由它生成。M0-001为已交付待评审草案（REVIEW），其余实施任务TODO；没有ACCEPTED或真实开发commit。
>
> priority=HIGH/STANDARD/LOW表示实施顺序优先级，不改原业务P0/P1/P2；allowedPaths是未来最大修改范围，不表示目录已创建。plannedTests为未来测试场景，不是已执行命令。baselineRefs中的别名见PLAN，实际证据只有evidence数组，基线引用不是完成证据。
>
> 任务拆分、状态/验收与证据规则见COLLABORATION；Git尚未建立的事实见HANDOFF。本台账不构成实施授权。

## M0-001 实施计划与协作协议独立审查

```json
{
  "id": "M0-001",
  "stage": "M0",
  "title": "实施计划与协作协议独立审查",
  "goal": "实施计划与协作协议独立审查",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "项目负责人/独立审查者",
  "assignee": "本轮规划编制者（AI）；独立审查者待指定",
  "allowedPaths": [
    "AGENTS.md",
    "docs/PLAN.md",
    "docs/TASKS.md",
    "docs/COLLABORATION.md",
    "docs/DECISIONS.md"
  ],
  "exclusiveResources": [
    "TASK_LEDGER",
    "PLANNING_PROTOCOL"
  ],
  "dependsOn": [],
  "entryConditions": [
    "本轮规划产物已具备可审查内容；只进行独立评审，不执行实施任务"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "规划审查意见与通过/退回记录",
    "任务/阶段/范围和Git事实源协议冻结"
  ],
  "acceptance": [
    {
      "id": "M0-001/AC1",
      "text": "逐项核对M0—M4、MC01—MC12与96项任务范围"
    },
    {
      "id": "M0-001/AC2",
      "text": "独立审查记录可定位；本轮产物不冒称工程验收"
    }
  ],
  "plannedTests": [
    "运行规划结构检查并记录实际结果；独立人工评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "当前无Git仓库，证据是工作区草案，不可ACCEPTED"
  ],
  "baselineRefs": [
    "HLD§4.1—4.4",
    "AI§15"
  ],
  "status": "REVIEW",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": "docs/HANDOFF.md",
  "draftEvidenceRefs": [
    "AGENTS.md",
    "docs/PLAN.md",
    "docs/TASKS.md",
    "docs/COLLABORATION.md",
    "docs/planning/validation-report.json"
  ],
  "history": []
}
```

## M0-002 Git事实源落地与初始白名单入库

```json
{
  "id": "M0-002",
  "stage": "M0",
  "title": "Git事实源落地与初始白名单入库",
  "goal": "Git事实源落地与初始白名单入库",
  "priority": "HIGH",
  "kind": "governance",
  "track": "main",
  "ownerRole": "工程集成人",
  "assignee": null,
  "allowedPaths": [
    ".git（未来授权建仓）",
    ".gitignore",
    "AGENTS.md",
    "docs/",
    "五份授权基线（只入库不改正文）"
  ],
  "exclusiveResources": [
    "GIT_BOOTSTRAP",
    "TASK_LEDGER"
  ],
  "dependsOn": [],
  "entryConditions": [
    "M0-001规划内容已获得可保全的独立审查通过记录，并取得仅建仓/初始入库授权；这是建仓特例，不要求尚无Git时先标M0-001 ACCEPTED",
    "将审查签认和本轮管理文件纳入真实Git提交；此后按常规证据规则验收，不授权业务开发"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "经确认的Git根目录/分支/提交规范",
    "仅白名单文件的初始提交与恢复说明"
  ],
  "acceptance": [
    {
      "id": "M0-002/AC1",
      "text": "真实repo/初始commit可查，未伪造SHA或自动上传远端"
    },
    {
      "id": "M0-002/AC2",
      "text": "五份基线指纹不变，秘密/未经授权文件不默认入库"
    },
    {
      "id": "M0-002/AC3",
      "text": "TASKS仍唯一状态源，生成视图可重建"
    },
    {
      "id": "M0-002/AC4",
      "text": "建仓前审查签认已保全并入库；M0-001在真实提交/复核证据齐备后才可ACCEPTED，未伪造自引用SHA"
    }
  ],
  "plannedTests": [
    "git rev-parse/status/log；白名单与secret扫描；重新生成视图"
  ],
  "requiredEvidenceKinds": [
    "REPOSITORY"
  ],
  "risks": [
    "仓库位置、远端/访问权限、保留策略待冻结；本轮不执行"
  ],
  "baselineRefs": [
    "HLD§16",
    "PRD§12"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-003 工程版本与运行兼容矩阵冻结

```json
{
  "id": "M0-003",
  "stage": "M0",
  "title": "工程版本与运行兼容矩阵冻结",
  "goal": "工程版本与运行兼容矩阵冻结",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "技术负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/decisions/（有需要才创建）",
    "docs/DECISIONS.md",
    "docs/contracts/runtime-compatibility.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-002"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "可与M0-004—009的资料/口径工作并行；DECISIONS由集成人串行合入",
  "deliverables": [
    "Python/FastAPI/Pydantic/ORM/驱动/MySQL/OS版本矩阵",
    "依赖锁和迁移工具决策"
  ],
  "acceptance": [
    {
      "id": "M0-003/AC1",
      "text": "固定受支持版本及许可证/兼容性证据，不用latest"
    },
    {
      "id": "M0-003/AC2",
      "text": "验证异步事务、Decimal、锁领取与目标运行入口的关键兼容项"
    }
  ],
  "plannedTests": [
    "小范围兼容性实验；保存命令/版本/输出，不初始化完整业务目录"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V01/V12；无环境不能以文档推断兼容通过"
  ],
  "baselineRefs": [
    "HLD§4.2",
    "HLD§16/19"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-004 首批S02夹具与最小契约冻结

```json
{
  "id": "M0-004",
  "stage": "M0",
  "title": "首批S02夹具与最小契约冻结",
  "goal": "首批S02夹具与最小契约冻结",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "O01/S02/B01/数据负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/minimal-s02.md（未来）",
    "docs/fixtures/s02-expectations.md（未来）"
  ],
  "exclusiveResources": [
    "PUBLIC_CONTRACTS"
  ],
  "dependsOn": [
    "M0-002"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "可与M0-003/005—009并行编制；契约冻结/合入串行",
  "deliverables": [
    "S02 A/B订单模拟输入、asOf与预期指标",
    "AnalysisContext/Handler/DomainResult/WorkItem最小使用子集",
    "节点A测试装配与B正式分析验收范围"
  ],
  "acceptance": [
    {
      "id": "M0-004/AC1",
      "text": "固定A超承诺、B未超承诺及缺映射/取消等反例"
    },
    {
      "id": "M0-004/AC2",
      "text": "不把I01测试探针注册成S02伪Handler，不扩大首批模型/动作范围"
    },
    {
      "id": "M0-004/AC3",
      "text": "A/B拆分不修改MC原定义"
    }
  ],
  "plannedTests": [
    "契约样例审查、预期值手工核对、MC逐项覆盖评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V03/V12；模拟工程口径不是企业履约口径"
  ],
  "baselineRefs": [
    "HLD§4.2—4.4",
    "HLD§6/7"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-005 真实来源授权与字段样本清单

```json
{
  "id": "M0-005",
  "stage": "M0",
  "title": "真实来源授权与字段样本清单",
  "goal": "真实来源授权与字段样本清单",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "集成/企业系统责任人",
  "assignee": null,
  "allowedPaths": [
    "docs/integration/source-register.md（未来）",
    "docs/evidence/M0-005/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-002"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "ERP/OMS/WMS/CRM/财务/渠道来源、责任人、授权/字段/覆盖清单",
    "试点读取样本及可用性/缺口证据"
  ],
  "acceptance": [
    {
      "id": "M0-005/AC1",
      "text": "接口/导出机制有实际授权和版本来源，不假定已连通"
    },
    {
      "id": "M0-005/AC2",
      "text": "分页/增量/删除/限流/覆盖与缺失有记录，原始敏感数据不直接入Git"
    }
  ],
  "plannedTests": [
    "授权材料复核；受控读取/导出样本核对，未运行项如实列明"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V02、F-01；未获来源时记录缺口，不能用Mock解除M0条件"
  ],
  "baselineRefs": [
    "FSR§6/9/14",
    "HLD§19"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-006 业务范围、权威域与指标口径签认

```json
{
  "id": "M0-006",
  "stage": "M0",
  "title": "业务范围、权威域与指标口径签认",
  "goal": "业务范围、权威域与指标口径签认",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "采购/仓库/客服/财务/数据负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/business-semantics.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-004",
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "店铺/仓/SKU试点边界、身份/单位/状态与权威域",
    "供需、履约、成熟群组投诉、贡献口径与AC期望"
  ],
  "acceptance": [
    {
      "id": "M0-006/AC1",
      "text": "B01/B02边界和来源去重规则有业务签认"
    },
    {
      "id": "M0-006/AC2",
      "text": "质量阈值/费用缺项/窗口/预计可售终点不靠模型猜测"
    }
  ],
  "plannedTests": [
    "AC-01—08口径桌面走查与真实样本映射核对"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V03；口径未定会污染全部场景"
  ],
  "baselineRefs": [
    "PRD§6.2/7/9/14",
    "ARCH§7.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-007 身份、字段权限与数据使用条件冻结

```json
{
  "id": "M0-007",
  "stage": "M0",
  "title": "身份、字段权限与数据使用条件冻结",
  "goal": "身份、字段权限与数据使用条件冻结",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "安全/数据/业务责任人",
  "assignee": null,
  "allowedPaths": [
    "docs/security/access-data-policy.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "身份发行方/测试身份边界",
    "tenant/store/warehouse/field/tool/action矩阵",
    "数据地域、模型用途、日志/备份/删除许可"
  ],
  "acceptance": [
    {
      "id": "M0-007/AC1",
      "text": "测试环境仍校验身份与范围，生产无匿名绕过"
    },
    {
      "id": "M0-007/AC2",
      "text": "云端/本地数据边界及敏感最小化条件未满足则关闭相应用途"
    }
  ],
  "plannedTests": [
    "权限正反例和威胁/数据链路评审；记录合同/许可Ref"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "SECURITY"
  ],
  "risks": [
    "V08/V09；不能从脱敏推定可公开共享"
  ],
  "baselineRefs": [
    "HLD§14/19",
    "AI§4/5/9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-008 质量、降级、预算和验收目标冻结

```json
{
  "id": "M0-008",
  "stage": "M0",
  "title": "质量、降级、预算和验收目标冻结",
  "goal": "质量、降级、预算和验收目标冻结",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "产品/业务/AI/运维/财务负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/quality-budget-acceptance.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-006",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "required/optional依赖及领域/联合降级矩阵",
    "任务/即席额度与期限、容量/时延/质量目标",
    "Golden Dataset责任、观察窗与RPO/RTO初始目标"
  ],
  "acceptance": [
    {
      "id": "M0-008/AC1",
      "text": "并行默认2/整体重规划默认1保持；其余上限有获准来源"
    },
    {
      "id": "M0-008/AC2",
      "text": "缺质量信号不当安全；质量硬失败/成本/业务收益分别验收"
    },
    {
      "id": "M0-008/AC3",
      "text": "未具备真实规模/样本的数值标待验证，不能声称已达标"
    }
  ],
  "plannedTests": [
    "边界/失败实例评审；预算竞争测试方案；金标准覆盖核对"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V04/V05/V13/V15；未冻结相关上限不启收费入口"
  ],
  "baselineRefs": [
    "PRD§8.3/13",
    "FSR§9/12",
    "AI§6/13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-009 两类外部动作可行性与岗位条件调查

```json
{
  "id": "M0-009",
  "stage": "M0",
  "title": "两类外部动作可行性与岗位条件调查",
  "goal": "两类外部动作可行性与岗位条件调查",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "ERP/CRM/业务/安全负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/integration/action-capabilities.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-005",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "ERP采购草稿/CRM内部工单的前置条件/幂等/回执/原子条件证据与缺口",
    "发起/独立审批/执行岗位及有效期草案"
  ],
  "acceptance": [
    {
      "id": "M0-009/AC1",
      "text": "只调查两类动作，无实际开放执行"
    },
    {
      "id": "M0-009/AC2",
      "text": "NOT_FOUND权威性、多对象原子不变量、撤销/在途窗口明确为已证实或未具备"
    }
  ],
  "plannedTests": [
    "源合同/沙箱能力核查；真实写入验证留M3，不用Mock证明可上线"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V06/V07；来源无可靠保证则动作维持关闭"
  ],
  "baselineRefs": [
    "HLD§13.2—13.2.1/19",
    "FSR§6.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M0-010 M0退出与受限工程实施授权

```json
{
  "id": "M0-010",
  "stage": "M0",
  "title": "M0退出与受限工程实施授权",
  "goal": "M0退出与受限工程实施授权",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "项目/业务/技术负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M0-010/（未来）",
    "docs/DECISIONS.md"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M0-001",
    "M0-003",
    "M0-004",
    "M0-005",
    "M0-006",
    "M0-007",
    "M0-008",
    "M0-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "M0门槛逐项签认及M1首批范围",
    "未具备数据/动作的限制和责任表"
  ],
  "acceptance": [
    {
      "id": "M0-010/AC1",
      "text": "满足原M0授权、样本、权威域/责任人与基本价值条件后才进入M1"
    },
    {
      "id": "M0-010/AC2",
      "text": "节点A/B只含无模型无外写基座，不把未知企业条件改成已通过"
    }
  ],
  "plannedTests": [
    "M0证据链/缺口/授权评审；无证据不得通过"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "M0关键条件不足时先补证，不能默许跳过"
  ],
  "baselineRefs": [
    "PRD§15",
    "FSR§14",
    "HLD§2.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-001 最小工程契约与所有者集成约定

```json
{
  "id": "M1-001",
  "stage": "M1",
  "title": "最小工程契约与所有者集成约定",
  "goal": "最小工程契约与所有者集成约定",
  "priority": "HIGH",
  "kind": "design",
  "track": "A",
  "ownerRole": "架构/工程集成人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/minimal-runtime.md（未来）"
  ],
  "exclusiveResources": [
    "PUBLIC_CONTRACTS"
  ],
  "dependsOn": [
    "M0-010"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "首批公开DTO/错误/引用/事务/取消/投递契约",
    "单迁移链/组合根/接口修改所有权"
  ],
  "acceptance": [
    {
      "id": "M1-001/AC1",
      "text": "只冻结A/B实际使用子集，AI字段对无模型闭环非必填"
    },
    {
      "id": "M1-001/AC2",
      "text": "场景注册、owner失败收尾与MC验收边界无歧义"
    }
  ],
  "plannedTests": [
    "消费者契约评审；不兼容字段负例"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V01/V12；过早抽象会扩基座"
  ],
  "baselineRefs": [
    "HLD§4/5/6"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-002 最小工程骨架与配置锁定

```json
{
  "id": "M1-002",
  "stage": "M1",
  "title": "最小工程骨架与配置锁定",
  "goal": "最小工程骨架与配置锁定",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "工程集成人",
  "assignee": null,
  "allowedPaths": [
    "pyproject.toml",
    "依赖锁文件（未来选定）",
    "src/commerce_hub/bootstrap/",
    "src/commerce_hub/entrypoints/",
    "tests/"
  ],
  "exclusiveResources": [
    "BOOTSTRAP",
    "DEPENDENCY_LOCK"
  ],
  "dependsOn": [
    "M1-001",
    "M0-003"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "最小包/启动工厂/配置schema/锁定依赖",
    "只创建正在使用的目录"
  ],
  "acceptance": [
    {
      "id": "M1-002/AC1",
      "text": "API与Worker独立入口，同一制品/迁移版本"
    },
    {
      "id": "M1-002/AC2",
      "text": "配置缺失失败，不自动迁移/启动Worker/模型/源同步"
    }
  ],
  "plannedTests": [
    "干净环境安装/启动/配置负例；静态检查"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "环境兼容实际结果与V01矩阵须一致"
  ],
  "baselineRefs": [
    "HLD§4.1/4.2/16"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-003 MySQL短事务与模块自有持久化适配

```json
{
  "id": "M1-003",
  "stage": "M1",
  "title": "MySQL短事务与模块自有持久化适配",
  "goal": "MySQL短事务与模块自有持久化适配",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "I01/存储集成人",
  "assignee": null,
  "allowedPaths": [
    "migrations/",
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/adapters/mysql/",
    "tests/integration/mysql/"
  ],
  "exclusiveResources": [
    "MIGRATION_CHAIN"
  ],
  "dependsOn": [
    "M1-002"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "首批必要迁移/连接/事务范围与Repository适配",
    "UTC/Decimal/tenant复合键约定"
  ],
  "acceptance": [
    {
      "id": "M1-003/AC1",
      "text": "从干净MySQL显式迁移成功且事务故障整体回滚"
    },
    {
      "id": "M1-003/AC2",
      "text": "每并发分支独立Session，应用启动不create_all/自动迁移"
    }
  ],
  "plannedTests": [
    "真实MySQL迁移/回滚/精度/唯一键集成测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "MySQL环境/账号未具备不可用SQLite替代证据"
  ],
  "baselineRefs": [
    "HLD§8/11/12/16"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-004 G01测试身份与数据范围强制检查

```json
{
  "id": "M1-004",
  "stage": "M1",
  "title": "G01测试身份与数据范围强制检查",
  "goal": "G01测试身份与数据范围强制检查",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "G01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/governance/access/",
    "tests/security/access/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-002",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "可信测试身份校验/有效scope与公开授权端口"
  ],
  "acceptance": [
    {
      "id": "M1-004/AC1",
      "text": "tenant/store/warehouse/field参数不能扩大授权"
    },
    {
      "id": "M1-004/AC2",
      "text": "测试身份非认证旁路，过期/错误签名/越权均拒绝"
    }
  ],
  "plannedTests": [
    "签名/issuer/audience/到期/跨租户/扩大范围负例"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "企业SSO尚未知，测试身份不能标生产认证完成"
  ],
  "baselineRefs": [
    "HLD§14",
    "PRD NFR-01"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-005 G02必需审计与Trace最小链

```json
{
  "id": "M1-005",
  "stage": "M1",
  "title": "G02必需审计与Trace最小链",
  "goal": "G02必需审计与Trace最小链",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "G02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/governance/observability/",
    "src/commerce_hub/adapters/mysql/observability/",
    "tests/integration/audit/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-003"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "同事务必需审计、结构化日志/Trace关联"
  ],
  "acceptance": [
    {
      "id": "M1-005/AC1",
      "text": "业务状态与必需审计同事务，不保存秘密"
    },
    {
      "id": "M1-005/AC2",
      "text": "HTTP/持久工作项/Worker保留关联且审计失败不伪成功"
    }
  ],
  "plannedTests": [
    "审计不可写故障；日志脱敏与trace重入验证"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "观测日志不成为第二份业务主账"
  ],
  "baselineRefs": [
    "HLD§12/15.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-006 I01工作项领取、租约与有界重投

```json
{
  "id": "M1-006",
  "stage": "M1",
  "title": "I01工作项领取、租约与有界重投",
  "goal": "I01工作项领取、租约与有界重投",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "I01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/infrastructure/",
    "src/commerce_hub/adapters/mysql/work_items/",
    "tests/faults/work_items/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-003",
    "M1-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "work_item/attempt公开用例、领取/心跳/完成/重排",
    "owner失败通知与投递去重"
  ],
  "acceptance": [
    {
      "id": "M1-006/AC1",
      "text": "真实MySQL竞争领取与leaseToken条件提交成立"
    },
    {
      "id": "M1-006/AC2",
      "text": "旧Worker迟到不覆盖，重投/到期耗尽有owner收尾，不解释外部结果"
    }
  ],
  "plannedTests": [
    "双Worker竞争/失租约/崩溃/DEAD故障测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V05租约参数待测，不承诺exactly-once"
  ],
  "baselineRefs": [
    "HLD§11"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-007 O01持久任务受理与版本/命令去重

```json
{
  "id": "M1-007",
  "stage": "M1",
  "title": "O01持久任务受理与版本/命令去重",
  "goal": "O01持久任务受理与版本/命令去重",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "O01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/adapters/mysql/orchestration/",
    "tests/integration/tasks/"
  ],
  "exclusiveResources": [
    "PUBLIC_CONTRACTS"
  ],
  "dependsOn": [
    "M1-004",
    "M1-005",
    "M1-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "task/plan/work/审计原子受理用例与查询/取消语义"
  ],
  "acceptance": [
    {
      "id": "M1-007/AC1",
      "text": "同命令同指纹复用、异指纹拒绝；失败不残留半任务"
    },
    {
      "id": "M1-007/AC2",
      "text": "尚无正式Handler时拒绝生产分析执行，不注册伪成功能力"
    }
  ],
  "plannedTests": [
    "原子受理/去重/回滚/取消契约测试；最终正向分析由B验证"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "A阶段单元/契约验证不能冒称MC03正式场景通过"
  ],
  "baselineRefs": [
    "HLD§6/7/12"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-008 FastAPI与独立Worker最小装配

```json
{
  "id": "M1-008",
  "stage": "M1",
  "title": "FastAPI与独立Worker最小装配",
  "goal": "FastAPI与独立Worker最小装配",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "入口/工程集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/entrypoints/",
    "src/commerce_hub/bootstrap/",
    "src/commerce_hub/workspace/",
    "tests/integration/runtime/"
  ],
  "exclusiveResources": [
    "BOOTSTRAP"
  ],
  "dependsOn": [
    "M1-006",
    "M1-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "health live/ready、受控入口与Worker注册分派",
    "测试专用持久工作项HTTP装配"
  ],
  "acceptance": [
    {
      "id": "M1-008/AC1",
      "text": "API/Worker两个进程独立启动/停止，ready反映真实依赖"
    },
    {
      "id": "M1-008/AC2",
      "text": "工程探针仅测试装配且复用I01，不作为生产分析API/ScenarioHandler"
    }
  ],
  "plannedTests": [
    "跨进程持久任务探针、API重启/Worker停启、未注册类型拒绝"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "A测试装配须M0-004冻结，不增加第二任务表/生产探针API"
  ],
  "baselineRefs": [
    "HLD§4.2/11"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-009 节点A可靠性与最小工程检查

```json
{
  "id": "M1-009",
  "stage": "M1",
  "title": "节点A可靠性与最小工程检查",
  "goal": "节点A可靠性与最小工程检查",
  "priority": "HIGH",
  "kind": "development",
  "track": "A",
  "ownerRole": "测试/工程负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/integration/runtime/",
    "tests/faults/work_items/",
    "docs/runbooks/minimal-runtime.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "真实MySQL双进程工程证据、运行/停止/迁移说明",
    "最小格式/类型/契约/集成检查配置（实施时才创建）"
  ],
  "acceptance": [
    {
      "id": "M1-009/AC1",
      "text": "API进程丢失不丢I01持久工作项，Worker恢复有界"
    },
    {
      "id": "M1-009/AC2",
      "text": "回滚/重复领取/旧lease/无密钥日志等工程负例有实际结果"
    }
  ],
  "plannedTests": [
    "干净库迁移、两个进程、故障注入及受控测试任务验证"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "仅预验证MC01/04/05/09/10/12相关工程行为，不代替B最终MC"
  ],
  "baselineRefs": [
    "HLD MC01/04/05/09/10/12"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-010 验收节点A：工程基础闭环

```json
{
  "id": "M1-010",
  "stage": "M1",
  "title": "验收节点A：工程基础闭环",
  "goal": "验收节点A：工程基础闭环",
  "priority": "HIGH",
  "kind": "gate",
  "track": "A",
  "ownerRole": "工程/测试/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M1-010/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "A节点实际提交/测试/限制和独立评审记录"
  ],
  "acceptance": [
    {
      "id": "M1-010/AC1",
      "text": "FastAPI+真实MySQL+独立Worker+I01持久工作项工程链成立"
    },
    {
      "id": "M1-010/AC2",
      "text": "未声称有S02领域计算/报告、全部MC通过、企业接口或模型/写入能力"
    }
  ],
  "plannedTests": [
    "复现A脚本与工程故障；人工核对限制"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "A通过只是中间工程检查点，B仍必须完成"
  ],
  "baselineRefs": [
    "HLD§4.2—4.4",
    "AI§15.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-011 D01模拟批次与覆盖契约

```json
{
  "id": "M1-011",
  "stage": "M1",
  "title": "D01模拟批次与覆盖契约",
  "goal": "D01模拟批次与覆盖契约",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "D01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/sync/",
    "tests/fixtures/sources/",
    "tests/contract/source_batch/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-010"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "明确simulated的测试连接器、批次/覆盖/可分析游标"
  ],
  "acceptance": [
    {
      "id": "M1-011/AC1",
      "text": "通过D01公开用例装载，不散写业务表"
    },
    {
      "id": "M1-011/AC2",
      "text": "重复输入不重复累计，覆盖缺口明确"
    }
  ],
  "plannedTests": [
    "模拟分页/重放/失败/游标未推进验证"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "此连接器不证明真实ERP等连通"
  ],
  "baselineRefs": [
    "HLD MC02/§9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-012 D02 S02身份映射与不可变投影

```json
{
  "id": "M1-012",
  "stage": "M1",
  "title": "D02 S02身份映射与不可变投影",
  "goal": "D02 S02身份映射与不可变投影",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "D02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/projection/",
    "src/commerce_hub/adapters/mysql/projection/",
    "tests/integration/projection/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-011"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "订单/包裹/承诺事件最小映射与版本化投影"
  ],
  "acceptance": [
    {
      "id": "M1-012/AC1",
      "text": "tenant复合身份不误并，歧义/未映射隔离"
    },
    {
      "id": "M1-012/AC2",
      "text": "迟到事件不覆盖较新状态，来源/修订可追"
    }
  ],
  "plannedTests": [
    "同名跨租户/乱序/重放/删除版本反例"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "不重建订单/库存主账"
  ],
  "baselineRefs": [
    "HLD§8/9",
    "PRD AC-01/05"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-013 D03质量门槛与固定snapshot manifest

```json
{
  "id": "M1-013",
  "stage": "M1",
  "title": "D03质量门槛与固定snapshot manifest",
  "goal": "D03质量门槛与固定snapshot manifest",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "D03负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/quality/",
    "src/commerce_hub/adapters/mysql/quality/",
    "tests/integration/snapshots/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-012"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "S02必需数据质量与不可变输入版本清单"
  ],
  "acceptance": [
    {
      "id": "M1-013/AC1",
      "text": "snapshot可定位已提交投影/映射/覆盖，非latest条件/hash空壳"
    },
    {
      "id": "M1-013/AC2",
      "text": "过旧/缺失/映射不明阻断相关结论，新输入新snapshot"
    }
  ],
  "plannedTests": [
    "冻结/源更新/缺口/回滚/版本读取验证"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "D03不保存O01计划/报告，不承诺跨外部系统原子快照"
  ],
  "baselineRefs": [
    "HLD§8.4/9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-014 D04最小证据登记与当前权限解析

```json
{
  "id": "M1-014",
  "stage": "M1",
  "title": "D04最小证据登记与当前权限解析",
  "goal": "D04最小证据登记与当前权限解析",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "D04负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/evidence/",
    "src/commerce_hub/adapters/mysql/evidence/",
    "tests/security/evidence/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-013",
    "M1-004"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "原记录/指标资产定位、版本/父证据和解析端口"
  ],
  "acceptance": [
    {
      "id": "M1-014/AC1",
      "text": "引用可回源、当前撤权/删除时安全失败"
    },
    {
      "id": "M1-014/AC2",
      "text": "不复制manifest/指标明细/报告正文"
    }
  ],
  "plannedTests": [
    "断链/删除/越权/跨版本定位测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "底层资产留存不足不能宣称可重放"
  ],
  "baselineRefs": [
    "HLD§8.4/9",
    "PRD NFR-02"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-015 B01首项履约确定性指标

```json
{
  "id": "M1-015",
  "stage": "M1",
  "title": "B01首项履约确定性指标",
  "goal": "B01首项履约确定性指标",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "B01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/metrics/",
    "tests/unit/metrics/fulfillment/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-013",
    "M0-004"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "固定asOf超承诺评价与结果Ref/单位/窗口"
  ],
  "acceptance": [
    {
      "id": "M1-015/AC1",
      "text": "夹具A超时、B不误报，缺承诺时显式未知"
    },
    {
      "id": "M1-015/AC2",
      "text": "指标唯一实现且带snapshot/metric版本"
    }
  ],
  "plannedTests": [
    "固定期望、边界等号/时区/缺项/多包裹粒度测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "模拟口径不替代企业正式履约口径"
  ],
  "baselineRefs": [
    "HLD MC07",
    "PRD S02-01—03"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-016 S02最小ScenarioHandler

```json
{
  "id": "M1-016",
  "stage": "M1",
  "title": "S02最小ScenarioHandler",
  "goal": "S02最小ScenarioHandler",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "S02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s02_fulfillment/",
    "tests/contract/scenarios/s02/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-014",
    "M1-015"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "真实调用D/B能力的S02 analyze与DomainResult"
  ],
  "acceptance": [
    {
      "id": "M1-016/AC1",
      "text": "结果匹配task/plan/participant/snapshot，包含限制/证据"
    },
    {
      "id": "M1-016/AC2",
      "text": "无LLM/场景私表旁路/静态DomainResult伪装执行"
    }
  ],
  "plannedTests": [
    "Handler调用链、缺数据领域阻断、取消安全点"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "只实现窄切片，不提前扩运输预测"
  ],
  "baselineRefs": [
    "HLD§4.2/7",
    "AI§14.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-017 O01正式SINGLE调度与报告发布/恢复

```json
{
  "id": "M1-017",
  "stage": "M1",
  "title": "O01正式SINGLE调度与报告发布/恢复",
  "goal": "O01正式SINGLE调度与报告发布/恢复",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "O01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "src/commerce_hub/adapters/mysql/orchestration/",
    "src/commerce_hub/bootstrap/",
    "tests/faults/analysis/"
  ],
  "exclusiveResources": [
    "BOOTSTRAP"
  ],
  "dependsOn": [
    "M1-016",
    "M1-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "注册真实S02、计划/快照派发、报告持久化和owner恢复"
  ],
  "acceptance": [
    {
      "id": "M1-017/AC1",
      "text": "唯一O01→Handler路径，报告/任务终态与完整性分开"
    },
    {
      "id": "M1-017/AC2",
      "text": "租约/计划条件发布；已发布重入不新增报告/自动建议"
    }
  ],
  "plannedTests": [
    "报告提交后工作项未完成崩溃、旧计划/租约、重复投递测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "JOINT仅保留兼容契约，未实现时拒绝"
  ],
  "baselineRefs": [
    "HLD§7/11/12"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-018 W01分析任务与报告/证据API

```json
{
  "id": "M1-018",
  "stage": "M1",
  "title": "W01分析任务与报告/证据API",
  "goal": "W01分析任务与报告/证据API",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "W01/入口负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/workspace/",
    "src/commerce_hub/entrypoints/http/",
    "tests/integration/http/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-017"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "POST任务/GET任务与报告/取消/证据访问的正式API"
  ],
  "acceptance": [
    {
      "id": "M1-018/AC1",
      "text": "202只表受理；重启后任务/报告可查询且当前鉴权"
    },
    {
      "id": "M1-018/AC2",
      "text": "只读报告终点无C01/C02/C03记录，无前端框架先决依赖"
    }
  ],
  "plannedTests": [
    "正式分析HTTP→DB→Worker→Handler→报告往返与越权测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "不能把A测试探针作为正式API验收"
  ],
  "baselineRefs": [
    "HLD§6.3/4.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-019 MC01—MC12完整闭环与故障复验

```json
{
  "id": "M1-019",
  "stage": "M1",
  "title": "MC01—MC12完整闭环与故障复验",
  "goal": "MC01—MC12完整闭环与故障复验",
  "priority": "HIGH",
  "kind": "development",
  "track": "B",
  "ownerRole": "测试/所有者集成人",
  "assignee": null,
  "allowedPaths": [
    "tests/integration/",
    "tests/faults/",
    "tests/security/",
    "docs/evidence/MC/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-018"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "12项逐项命令/输入/预期/真实结果/commit与日志"
  ],
  "acceptance": [
    {
      "id": "M1-019/AC1",
      "text": "MC01—MC12全在真实MySQL/API/Worker/Handler上复现"
    },
    {
      "id": "M1-019/AC2",
      "text": "无模拟任务/授权/事务/快照/报告，模拟仅源数据"
    }
  ],
  "plannedTests": [
    "按MC逐项迁移、受理回滚、重启、双Worker、崩溃、越权、取消验收"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "不能以单测Mock或一次happy path抵消故障失败"
  ],
  "baselineRefs": [
    "HLD§4.3/4.4",
    "AI§15.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-020 验收节点B：业务计算最小闭环

```json
{
  "id": "M1-020",
  "stage": "M1",
  "title": "验收节点B：业务计算最小闭环",
  "goal": "验收节点B：业务计算最小闭环",
  "priority": "HIGH",
  "kind": "gate",
  "track": "B",
  "ownerRole": "工程/业务口径/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M1-020/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-019"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "仅直接依赖已ACCEPTED且入口条件满足时；与无依赖关系、实际文件范围不相交的任务并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "B完整MC矩阵及最小代码基座交接",
    "后续S01专项设计的可用契约/数据/报告基点"
  ],
  "acceptance": [
    {
      "id": "M1-020/AC1",
      "text": "MC01—MC12逐项有实际证据和独立评审，A/B合成原最小基座"
    },
    {
      "id": "M1-020/AC2",
      "text": "明确只证明simulated工程验证，不授予真实集成/模型/外写资格"
    }
  ],
  "plannedTests": [
    "干净环境复现正式S02任务至持久报告"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "未过B不可声称最小基座完成或直接启动补货Agent"
  ],
  "baselineRefs": [
    "HLD§4.2—4.4",
    "AI§15"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-021 ERP首期只读连接器

```json
{
  "id": "M1-021",
  "stage": "M1",
  "title": "ERP首期只读连接器",
  "goal": "ERP首期只读连接器",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/ERP集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/erp/",
    "tests/integration/sources/erp/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "试点必要商品/供应/未收采购读取与覆盖记录"
  ],
  "acceptance": [
    {
      "id": "M1-021/AC1",
      "text": "真实授权样本证明分页/增量/删除/部分收货语义与限流"
    },
    {
      "id": "M1-021/AC2",
      "text": "同步失败不推进可分析游标，不写ERP"
    }
  ],
  "plannedTests": [
    "真实只读契约/重放/游标/删除/限流/覆盖验证"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ"
  ],
  "risks": [
    "V02；厂商/字段未知不得假连接"
  ],
  "baselineRefs": [
    "HLD§9",
    "FSR§6"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-022 OMS首期只读连接器

```json
{
  "id": "M1-022",
  "stage": "M1",
  "title": "OMS首期只读连接器",
  "goal": "OMS首期只读连接器",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/OMS集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/oms/",
    "tests/integration/sources/oms/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "订单/退款/承诺/签收授权读取"
  ],
  "acceptance": [
    {
      "id": "M1-022/AC1",
      "text": "订单/退款/事件唯一性与历史覆盖可核验"
    },
    {
      "id": "M1-022/AC2",
      "text": "重放/乱序/取消/更正不重复汇总"
    }
  ],
  "plannedTests": [
    "真实读取/分页/覆盖/去重与时区测试"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ"
  ],
  "risks": [
    "V02；模拟不能证明实际OMS覆盖"
  ],
  "baselineRefs": [
    "FSR§6.1",
    "HLD§9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-023 WMS首期只读连接器

```json
{
  "id": "M1-023",
  "stage": "M1",
  "title": "WMS首期只读连接器",
  "goal": "WMS首期只读连接器",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/WMS集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/wms/",
    "tests/integration/sources/wms/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "库存分桶、收货/质检、包裹/出库必要读取"
  ],
  "acceptance": [
    {
      "id": "M1-023/AC1",
      "text": "分桶/来源/可售终点与权威仓范围可证明"
    },
    {
      "id": "M1-023/AC2",
      "text": "迟到/缺覆盖有标记，不把ERP库存镜像重复相加"
    }
  ],
  "plannedTests": [
    "实际分桶/事件/分页/覆盖测试"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ"
  ],
  "risks": [
    "V02/V03；互斥性和日期需确认"
  ],
  "baselineRefs": [
    "PRD§9",
    "FSR§6.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-024 CRM首期反馈只读连接器

```json
{
  "id": "M1-024",
  "stage": "M1",
  "title": "CRM首期反馈只读连接器",
  "goal": "CRM首期反馈只读连接器",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/CRM集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/crm/",
    "tests/integration/sources/crm/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "反馈/工单/订单关联、语言与最小敏感字段读取"
  ],
  "acceptance": [
    {
      "id": "M1-024/AC1",
      "text": "保留重复工单和订单关系，不把工单数当投诉订单数"
    },
    {
      "id": "M1-024/AC2",
      "text": "脱敏样本有许可与版本，缺关联不猜测"
    }
  ],
  "plannedTests": [
    "真实读取/关联/去重/删除/脱敏测试"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "SECURITY"
  ],
  "risks": [
    "客户资料/语言许可不足限制S03"
  ],
  "baselineRefs": [
    "FSR§6.1/7",
    "AI§14.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-025 财务费用与成本首期只读接入

```json
{
  "id": "M1-025",
  "stage": "M1",
  "title": "财务费用与成本首期只读接入",
  "goal": "财务费用与成本首期只读接入",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/财务集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/finance/",
    "tests/integration/sources/finance/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005",
    "M0-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "实收/费用/成本/转回/币种来源与账单版本"
  ],
  "acceptance": [
    {
      "id": "M1-025/AC1",
      "text": "累计/增量账单与成本转回语义真实签认"
    },
    {
      "id": "M1-025/AC2",
      "text": "缺项与估算不填0，不修改账目"
    }
  ],
  "plannedTests": [
    "真实账单版本/币种/累计快照与退款核对"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ"
  ],
  "risks": [
    "V02/V03费用覆盖/汇率未知则部分或阻断"
  ],
  "baselineRefs": [
    "PRD AC-07/08",
    "FSR§6.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-026 渠道首期必要只读子集

```json
{
  "id": "M1-026",
  "stage": "M1",
  "title": "渠道首期必要只读子集",
  "goal": "渠道首期必要只读子集",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "D01/渠道集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/sources/channel/",
    "tests/integration/sources/channel/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "必要Listing/订单/费用及授权台账"
  ],
  "acceptance": [
    {
      "id": "M1-026/AC1",
      "text": "只接首期使用子集，不全渠道全量或提前广告平台"
    },
    {
      "id": "M1-026/AC2",
      "text": "来源权威/费用归因覆盖明确，缺字段不伪造"
    }
  ],
  "plannedTests": [
    "真实授权/分页/限流/映射/覆盖验证"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ"
  ],
  "risks": [
    "广告/市场等P1/P2资料另于M4验证"
  ],
  "baselineRefs": [
    "PRD§3/5.2",
    "FSR§6.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-027 D02四类P0域标准投影扩展

```json
{
  "id": "M1-027",
  "stage": "M1",
  "title": "D02四类P0域标准投影扩展",
  "goal": "D02四类P0域标准投影扩展",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "D02/数据负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/projection/",
    "src/commerce_hub/adapters/mysql/projection/",
    "tests/integration/projection/p0/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-021",
    "M1-022",
    "M1-023",
    "M1-024",
    "M1-025",
    "M1-026"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "SKU/Listing/仓/订单/包裹及费用/反馈版本投影"
  ],
  "acceptance": [
    {
      "id": "M1-027/AC1",
      "text": "映射签认、单位/状态/权威域唯一，冲突隔离"
    },
    {
      "id": "M1-027/AC2",
      "text": "增量/累计/删除/时区语义一致且不改源主账"
    }
  ],
  "plannedTests": [
    "跨源同对象/重复库存/账单修订/未映射反例"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V03；身份错误污染全部场景"
  ],
  "baselineRefs": [
    "HLD§8/9",
    "PRD AC-01/08"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-028 D03/D04真实质量与证据扩展

```json
{
  "id": "M1-028",
  "stage": "M1",
  "title": "D03/D04真实质量与证据扩展",
  "goal": "D03/D04真实质量与证据扩展",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "D03/D04负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/data/quality/",
    "src/commerce_hub/data/evidence/",
    "tests/integration/data/p0/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-027",
    "M0-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "分域质量/时效/成熟窗快照与证据解析"
  ],
  "acceptance": [
    {
      "id": "M1-028/AC1",
      "text": "真实覆盖及固定输入可解析，过旧/缺映射阻断"
    },
    {
      "id": "M1-028/AC2",
      "text": "撤权/删除/来源更新可复核，不复制权威资产"
    }
  ],
  "plannedTests": [
    "过旧/缺覆盖/固定版本/断链与撤权测试"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "SECURITY"
  ],
  "risks": [
    "V09留存不足不能只靠hash宣称复核"
  ],
  "baselineRefs": [
    "HLD§8.4/9",
    "AI§5"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-029 B01 P0指标目录与确定性计算

```json
{
  "id": "M1-029",
  "stage": "M1",
  "title": "B01 P0指标目录与确定性计算",
  "goal": "B01 P0指标目录与确定性计算",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "B01/业务口径负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/metrics/",
    "tests/unit/metrics/p0/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "供需逐日/缺口、履约、投诉分母、贡献指标"
  ],
  "acceptance": [
    {
      "id": "M1-029/AC1",
      "text": "AC-02—08期望含单位/币种/分母/缺项全部符合"
    },
    {
      "id": "M1-029/AC2",
      "text": "同指标事实/情景唯一实现，LLM/场景不复制公式"
    }
  ],
  "plannedTests": [
    "固定样例、窗口/重复/缺项/Decimal边界测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "口径变更先ADR，不以解释掩盖差异"
  ],
  "baselineRefs": [
    "PRD§6.2/9/14",
    "HLD§5.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-030 B02基线情景与候选评价

```json
{
  "id": "M1-030",
  "stage": "M1",
  "title": "B02基线情景与候选评价",
  "goal": "B02基线情景与候选评价",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "B02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/forecasting/",
    "tests/unit/forecasting/baseline/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-029",
    "M0-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "明确假设的需求基线/候选/MOQ倍数日期约束"
  ],
  "acceptance": [
    {
      "id": "M1-030/AC1",
      "text": "各候选调用B01评价，不另算余额/首次缺货"
    },
    {
      "id": "M1-030/AC2",
      "text": "假设不冒充事实，不编造交期；学习型预测暂缓"
    }
  ],
  "plannedTests": [
    "AC-02/03、MOQ/倍数/日期变化/无解测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V03；学习方法后续滚动回测"
  ],
  "baselineRefs": [
    "HLD ER02",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-031 O01 AI共享预算最小实现

```json
{
  "id": "M1-031",
  "stage": "M1",
  "title": "O01 AI共享预算最小实现",
  "goal": "O01 AI共享预算最小实现",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "O01/G02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "tests/faults/budget/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M0-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "TaskBudgetHandle预留/结算/未决核对"
  ],
  "acceptance": [
    {
      "id": "M1-031/AC1",
      "text": "并发/子调用/重试不超发，usage未知占额"
    },
    {
      "id": "M1-031/AC2",
      "text": "期限/取消/旧lease阻新调用，无Runtime或Redis前置"
    }
  ],
  "plannedTests": [
    "真实MySQL并发/重复结算/崩溃/未知用量测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V05未获准上限不启收费模型"
  ],
  "baselineRefs": [
    "AI§3/6",
    "HLD§7.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-032 A01网关首个获准Provider

```json
{
  "id": "M1-032",
  "stage": "M1",
  "title": "A01网关首个获准Provider",
  "goal": "A01网关首个获准Provider",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "A01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/models/",
    "src/commerce_hub/adapters/models/",
    "tests/contract/models/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-031",
    "M0-007",
    "M0-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "统一ModelRequest/ProviderRequest、Schema/错误/usage",
    "首个用途的真实Provider契约验证"
  ],
  "acceptance": [
    {
      "id": "M1-032/AC1",
      "text": "统一字段和task/plan分离；A01不执行工具"
    },
    {
      "id": "M1-032/AC2",
      "text": "缓存OFF无设施，无隐藏重试/越地域降级"
    },
    {
      "id": "M1-032/AC3",
      "text": "技术错误不决定业务RULES_ONLY"
    }
  ],
  "plannedTests": [
    "协议负例及获准真实输出/usage/超时验证"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SECURITY"
  ],
  "risks": [
    "V09/V13未验证就不启真实调用"
  ],
  "baselineRefs": [
    "AI§9/附录A/C"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-033 A02首个VOC分类能力切片

```json
{
  "id": "M1-033",
  "stage": "M1",
  "title": "A02首个VOC分类能力切片",
  "goal": "A02首个VOC分类能力切片",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "A02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/understanding/",
    "tests/contract/understanding/voc/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-032",
    "M1-024",
    "M0-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "输入/Prompt/Context/Schema/understandingRef/D04与G02关联"
  ],
  "acceptance": [
    {
      "id": "M1-033/AC1",
      "text": "成功、TIMEOUT、语义UNKNOWN区分，不当无投诉"
    },
    {
      "id": "M1-033/AC2",
      "text": "ID/span/Schema/权限与原attempt计费校验"
    },
    {
      "id": "M1-033/AC3",
      "text": "显式Workflow，无Loop/缓存依赖"
    }
  ],
  "plannedTests": [
    "VOC-01—10协议/故障及真实授权样本评估"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "taxonomy/阈值待确认，模拟JSON不证明效果"
  ],
  "baselineRefs": [
    "AI附录C/§14.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-034 A03必要检索与只读工具

```json
{
  "id": "M1-034",
  "stage": "M1",
  "title": "A03必要检索与只读工具",
  "goal": "A03必要检索与只读工具",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "A03负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/retrieval/",
    "src/commerce_hub/adapters/retrieval/",
    "tests/security/retrieval/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-020",
    "M1-029",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "基础授权检索/证据/指标工具与QuerySpec"
  ],
  "acceptance": [
    {
      "id": "M1-034/AC1",
      "text": "权限预过滤及当前回源复核，工具/结果最小化"
    },
    {
      "id": "M1-034/AC2",
      "text": "无C03/任意SQL/URL/shell，不默认向量/图数据库"
    },
    {
      "id": "M1-034/AC3",
      "text": "即席完整额度未具备前只开放获准子集"
    }
  ],
  "plannedTests": [
    "越权/注入/伪参/引用/只读计划负例"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V10/V11候选收益未证不部署"
  ],
  "baselineRefs": [
    "AI§5/10",
    "HLD§6.4/10.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-035 G02 AI版本/评测与反馈基础

```json
{
  "id": "M1-035",
  "stage": "M1",
  "title": "G02 AI版本/评测与反馈基础",
  "goal": "G02 AI版本/评测与反馈基础",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "G02/AI/业务负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/governance/observability/",
    "docs/evaluation/（未来）",
    "tests/evaluation/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-032",
    "M1-033",
    "M1-034"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "版本链/Golden Dataset/离线评测/反馈Ref"
  ],
  "acceptance": [
    {
      "id": "M1-035/AC1",
      "text": "规则/人工/Judge、模型/收益分开，硬失败不平均"
    },
    {
      "id": "M1-035/AC2",
      "text": "usage/attempt费用去重，敏感正文不默认留存"
    }
  ],
  "plannedTests": [
    "固定回归、未知/注入/引用、人审/费用核对"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SECURITY"
  ],
  "risks": [
    "V09/V13；不强制LLMOps平台"
  ],
  "baselineRefs": [
    "AI§12/13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M1-036 M1公共基座真实只读就绪验收

```json
{
  "id": "M1-036",
  "stage": "M1",
  "title": "M1公共基座真实只读就绪验收",
  "goal": "M1公共基座真实只读就绪验收",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "技术/业务/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M1-036/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-028",
    "M1-030",
    "M1-031",
    "M1-033",
    "M1-034",
    "M1-035"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "直接依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "M1公共/真实只读/模型用途就绪矩阵"
  ],
  "acceptance": [
    {
      "id": "M1-036/AC1",
      "text": "B工程、真实只读、真实模型证据分别列明"
    },
    {
      "id": "M1-036/AC2",
      "text": "所需数据/权限/指标/证据/质量/预算满足进入M2门槛"
    }
  ],
  "plannedTests": [
    "公共契约/隔离/故障/模型质量与依赖集成复验"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "MODEL_EVAL",
    "SECURITY"
  ],
  "risks": [
    "用途不满足仍关闭；S01设计可准备不等于M2就绪"
  ],
  "baselineRefs": [
    "PRD§15",
    "FSR§14",
    "AI§15"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-001 S01补货专项设计与MVP范围

```json
{
  "id": "M2-001",
  "stage": "M2",
  "title": "S01补货专项设计与MVP范围",
  "goal": "S01补货专项设计与MVP范围",
  "priority": "HIGH",
  "kind": "design",
  "track": "S01_PREPARATION",
  "ownerRole": "S01/采购/数据/B01/B02负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s01-design.md（未来）",
    "docs/DECISIONS.md"
  ],
  "exclusiveResources": [
    "PUBLIC_CONTRACTS"
  ],
  "dependsOn": [
    "M1-020",
    "M0-006",
    "M0-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "B后可与M1-021—036并行设计准备；MVP代码须M1-036通过",
  "deliverables": [
    "S01字段/约束/时效/质量依赖/输出/测试与MVP范围"
  ],
  "acceptance": [
    {
      "id": "M2-001/AC1",
      "text": "首个MVP为只读Workflow，不开发自主补货Agent"
    },
    {
      "id": "M2-001/AC2",
      "text": "明确可售分桶、供给可售日、MOQ/倍数和质量缺失阻断"
    },
    {
      "id": "M2-001/AC3",
      "text": "公共契约变更先评审，候选与采购动作分离"
    }
  ],
  "plannedTests": [
    "AC-02/03/04桌面走查与真实数据缺口审查"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V03/V04；B后可提前设计，代码仍需M1退出"
  ],
  "baselineRefs": [
    "PRD§7.1",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-002 S01只读补货Workflow MVP

```json
{
  "id": "M2-002",
  "stage": "M2",
  "title": "S01只读补货Workflow MVP",
  "goal": "S01只读补货Workflow MVP",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "S01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s01_supply_inventory/",
    "tests/scenarios/s01/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-001",
    "M1-036"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "B01基线→B02候选→限制→O01报告的Handler"
  ],
  "acceptance": [
    {
      "id": "M2-002/AC1",
      "text": "数量/日期/假设/证据齐全，复用唯一指标评价"
    },
    {
      "id": "M2-002/AC2",
      "text": "缺必需质量信号阻断可执行采购结论，不自动C01/审批/外写"
    }
  ],
  "plannedTests": [
    "AC-02/03/04及过旧/未映射/重复供给/取消/失败负例"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "规则结果可用不代表质量安全；模型解释可选"
  ],
  "baselineRefs": [
    "AI§14.1",
    "HLD ER01—06"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-003 S01真实只读试点人工核对

```json
{
  "id": "M2-003",
  "stage": "M2",
  "title": "S01真实只读试点人工核对",
  "goal": "S01真实只读试点人工核对",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "S01/采购/质量负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/uat/s01/",
    "docs/evidence/M2-003/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-002",
    "M2-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "真实供需/质量依赖/候选人工复核"
  ],
  "acceptance": [
    {
      "id": "M2-003/AC1",
      "text": "数量/日期可追真实snapshot和B01/B02"
    },
    {
      "id": "M2-003/AC2",
      "text": "S03有效/未知引发的限制正确，模拟不冒充企业验收"
    }
  ],
  "plannedTests": [
    "代表任务与过期/质量冲突/缺项核对"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "真实规模/阈值以M0签认值为准"
  ],
  "baselineRefs": [
    "FSR§9",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-004 S02完整P0风险分流

```json
{
  "id": "M2-004",
  "stage": "M2",
  "title": "S02完整P0风险分流",
  "goal": "S02完整P0风险分流",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "S02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s02_fulfillment/",
    "tests/scenarios/s02/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-036"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "未出库/物流停滞/多包裹/催单证据流程"
  ],
  "acceptance": [
    {
      "id": "M2-004/AC1",
      "text": "AC-05中6/4分流、粒度和迟到事件正确"
    },
    {
      "id": "M2-004/AC2",
      "text": "责任线索与事实分开，不取消订单/改地址/补发"
    }
  ],
  "plannedTests": [
    "真实队列/多包裹/乱序/缺承诺/解释降级测试"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "到货预测P1留M4，不扩P0"
  ],
  "baselineRefs": [
    "PRD§7.2",
    "AI§14.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-005 S03 VOC与成熟群组分析

```json
{
  "id": "M2-005",
  "stage": "M2",
  "title": "S03 VOC与成熟群组分析",
  "goal": "S03 VOC与成熟群组分析",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "S03/客服负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s03_customer_voc/",
    "tests/scenarios/s03/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-036"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "A02标签→B01去重投诉/成熟分母→调查信号"
  ],
  "acceptance": [
    {
      "id": "M2-005/AC1",
      "text": "工单数/订单数/分母/窗口分开，投诉占比非缺陷率"
    },
    {
      "id": "M2-005/AC2",
      "text": "技术失败/语义UNKNOWN区分，缺分母阻断占比"
    },
    {
      "id": "M2-005/AC3",
      "text": "结果经O01发布，不私调其他场景"
    }
  ],
  "plannedTests": [
    "AC-04/06、分语言/主题、UNKNOWN/人工修订回归"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "成熟窗/阈值/标签须业务签认"
  ],
  "baselineRefs": [
    "AI§14.3/附录C",
    "PRD§7.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-006 S04贡献与费用P0分析

```json
{
  "id": "M2-006",
  "stage": "M2",
  "title": "S04贡献与费用P0分析",
  "goal": "S04贡献与费用P0分析",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "S04/财务负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s04_contribution_fees/",
    "tests/scenarios/s04/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M1-036"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "贡献/差异、覆盖/缺项/证据的只读报告"
  ],
  "acceptance": [
    {
      "id": "M2-006/AC1",
      "text": "AC-07按事实得19.23/-0.67/4.33 USD，AC-08累计不相加"
    },
    {
      "id": "M2-006/AC2",
      "text": "缺费用不填0，贡献非净利润/到账，不虚构广告归因"
    }
  ],
  "plannedTests": [
    "真实退款/转回/币种/账单/缺项与解释不改数验证"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "财务口径/转回确认/实际估算必须签认"
  ],
  "baselineRefs": [
    "PRD§7.4",
    "AI§14.4"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-007 O01联合分析与跨领域降级

```json
{
  "id": "M2-007",
  "stage": "M2",
  "title": "O01联合分析与跨领域降级",
  "goal": "O01联合分析与跨领域降级",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "O01/场景集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/orchestration/",
    "tests/scenarios/joint/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-002",
    "M2-004",
    "M2-005",
    "M2-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "S01+S03、S03+S04及3参与者统一计划/报告"
  ],
  "acceptance": [
    {
      "id": "M2-007/AC1",
      "text": "同上下文，默认并行2/重规划1，不丢参与者"
    },
    {
      "id": "M2-007/AC2",
      "text": "O01/D03协调新输入，拒绝不兼容快照混用"
    },
    {
      "id": "M2-007/AC3",
      "text": "O01不调用领域计算修结果，必需缺失不隐式跳过"
    }
  ],
  "plannedTests": [
    "多参与者/重规划超限/旧快照/模型失败与领域矩阵"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "V04/V05未冻结不能默许模型判安全"
  ],
  "baselineRefs": [
    "HLD§7",
    "AI§2/6/7"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-008 W01统一报告、证据与角色视图

```json
{
  "id": "M2-008",
  "stage": "M2",
  "title": "W01统一报告、证据与角色视图",
  "goal": "W01统一报告、证据与角色视图",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "W01/前端负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/workspace/",
    "实际选定W01前端目录（未来）",
    "tests/uat/workspace/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-004",
    "M2-005",
    "M2-006",
    "M2-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "四场景/联合报告、证据侧栏、范围/限制/错误呈现"
  ],
  "acceptance": [
    {
      "id": "M2-008/AC1",
      "text": "页面不重算指标/推断批准和执行状态，当前鉴权"
    },
    {
      "id": "M2-008/AC2",
      "text": "沿冻结门户方案落地，不默认React/Vue或新服务"
    }
  ],
  "plannedTests": [
    "角色/越权/断链/部分报告/取消可理解性验收"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "BUSINESS_UAT"
  ],
  "risks": [
    "V12前端落点待定，A/B无需前端工程"
  ],
  "baselineRefs": [
    "HLD§6.3/14",
    "PRD W01"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-009 C01建议确认与规则预警

```json
{
  "id": "M2-009",
  "stage": "M2",
  "title": "C01建议确认与规则预警",
  "goal": "C01建议确认与规则预警",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "C01负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/collaboration/suggestions/",
    "tests/integration/suggestions/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-007",
    "M2-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "建议版本、风险去重/责任交接和明确生成/确认命令"
  ],
  "acceptance": [
    {
      "id": "M2-009/AC1",
      "text": "报告不自动建建议，确认不自动PENDING/执行"
    },
    {
      "id": "M2-009/AC2",
      "text": "参数/证据变化使旧版本失效，预警来源明确"
    }
  ],
  "plannedTests": [
    "风险去重/显式操作/过期/变更/无自动C记录"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "提交审批/批准留M3，不顺连执行"
  ],
  "baselineRefs": [
    "HLD§12.3/13.1",
    "AI ER06"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-010 四场景及联合只读业务UAT

```json
{
  "id": "M2-010",
  "stage": "M2",
  "title": "四场景及联合只读业务UAT",
  "goal": "四场景及联合只读业务UAT",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "业务/测试负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/uat/p0/",
    "docs/evidence/M2-010/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-003",
    "M2-004",
    "M2-005",
    "M2-006",
    "M2-007",
    "M2-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "AC-01—09/12及限制逐项试点签认"
  ],
  "acceptance": [
    {
      "id": "M2-010/AC1",
      "text": "口径/引用/UNKNOWN/关键质量阻断无硬失败"
    },
    {
      "id": "M2-010/AC2",
      "text": "不声称AC-10/11执行验收；模型效果与收益分别记"
    }
  ],
  "plannedTests": [
    "真实代表任务和反例、业务人工签认"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "小样本不能声称全语言/全主题准确率"
  ],
  "baselineRefs": [
    "PRD§14",
    "FSR§9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-011 P0安全与提示注入验收

```json
{
  "id": "M2-011",
  "stage": "M2",
  "title": "P0安全与提示注入验收",
  "goal": "P0安全与提示注入验收",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "安全负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/security/p0/",
    "docs/evidence/M2-011/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-007",
    "M2-008",
    "M2-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "各入口/Worker/工具/检索/导出/日志隔离报告"
  ],
  "acceptance": [
    {
      "id": "M2-011/AC1",
      "text": "无跨tenant/user/字段泄露、模型写工具或敏感日志"
    },
    {
      "id": "M2-011/AC2",
      "text": "撤权/恶意反馈/知识内容不改变权限/预算/执行"
    }
  ],
  "plannedTests": [
    "越权、旧策略、工具伪参、注入对抗测试"
  ],
  "requiredEvidenceKinds": [
    "SECURITY"
  ],
  "risks": [
    "只测HTTP不足；任何阻断性安全失败不放行"
  ],
  "baselineRefs": [
    "PRD NFR-01—03",
    "AI§13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-012 P0模型/Prompt/RAG质量回归

```json
{
  "id": "M2-012",
  "stage": "M2",
  "title": "P0模型/Prompt/RAG质量回归",
  "goal": "P0模型/Prompt/RAG质量回归",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "AI/G02/业务负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/evaluation/p0/",
    "docs/evidence/M2-012/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-005",
    "M2-006",
    "M2-007",
    "M1-035"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "锁定集/分层质量、人审及模型升级对照"
  ],
  "acceptance": [
    {
      "id": "M2-012/AC1",
      "text": "Schema/工具/引用/UNKNOWN/重点主题达冻结阈值"
    },
    {
      "id": "M2-012/AC2",
      "text": "Judge不代替人工，缓存bypass，重放与重新推理分开"
    }
  ],
  "plannedTests": [
    "固定集/真实获准模型/人审和版本回归"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "V13未冻结不放量，不编造效果"
  ],
  "baselineRefs": [
    "AI§12/13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-013 只读容量、预算与恢复压力验证

```json
{
  "id": "M2-013",
  "stage": "M2",
  "title": "只读容量、预算与恢复压力验证",
  "goal": "只读容量、预算与恢复压力验证",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "运维/性能/O01负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/performance/readonly/",
    "docs/evidence/M2-013/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-007",
    "M2-011"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "冻结规模的队列/并发/token/费用/时延证据"
  ],
  "acceptance": [
    {
      "id": "M2-013/AC1",
      "text": "达到获准目标且不超发/无限循环，超时/取消正确"
    },
    {
      "id": "M2-013/AC2",
      "text": "重试/联合解释不重置预算，不为未定位瓶颈先加中间件"
    }
  ],
  "plannedTests": [
    "多实例/额度耗尽/提供方故障/积压与恢复压测"
  ],
  "requiredEvidenceKinds": [
    "OPERATIONS",
    "MODEL_EVAL"
  ],
  "risks": [
    "V05目标不能取可研示算当SLA"
  ],
  "baselineRefs": [
    "HLD§7.3/15",
    "AI§6/9/13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-014 只读部署、备份、回滚与手册

```json
{
  "id": "M2-014",
  "stage": "M2",
  "title": "只读部署、备份、回滚与手册",
  "goal": "只读部署、备份、回滚与手册",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "运维/工程集成人",
  "assignee": null,
  "allowedPaths": [
    "实际选定部署配置（未来）",
    "docs/runbooks/readonly.md（未来）",
    "tests/operations/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-011",
    "M2-013",
    "M0-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "分环境最小部署、迁移/备份恢复/回滚/值守"
  ],
  "acceptance": [
    {
      "id": "M2-014/AC1",
      "text": "API/Worker配置凭据隔离，依赖关闭默认安全"
    },
    {
      "id": "M2-014/AC2",
      "text": "冻结RPO/RTO及回滚实际演练，恢复后数据/报告可核对"
    }
  ],
  "plannedTests": [
    "预发布部署、备份还原/迁移/告警/回滚演练"
  ],
  "requiredEvidenceKinds": [
    "OPERATIONS",
    "SECURITY"
  ],
  "risks": [
    "本轮不部署；环境/窗口/账号待授权"
  ],
  "baselineRefs": [
    "HLD§14—16",
    "FSR§14"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-015 只读受限试点发布与观察

```json
{
  "id": "M2-015",
  "stage": "M2",
  "title": "只读受限试点发布与观察",
  "goal": "只读受限试点发布与观察",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "项目/业务/运维负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/releases/readonly-pilot.md（未来）",
    "docs/evidence/M2-015/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-010",
    "M2-012",
    "M2-014"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "范围/版本/责任明确的试点发布记录及效率/反馈/成本基线"
  ],
  "acceptance": [
    {
      "id": "M2-015/AC1",
      "text": "只发布已通过用途，无自动审批/外写"
    },
    {
      "id": "M2-015/AC2",
      "text": "可比窗口记录效果，不把同期增长/工单创建当AI收益"
    }
  ],
  "plannedTests": [
    "受控发布与线上抽样/反馈/回滚门槛复核"
  ],
  "requiredEvidenceKinds": [
    "OPERATIONS",
    "BUSINESS_UAT"
  ],
  "risks": [
    "试点非全量，观察窗按业务频率冻结"
  ],
  "baselineRefs": [
    "FSR§8/9/12/14",
    "AI§12/13"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M2-016 M2阶段验收与M3准入评审

```json
{
  "id": "M2-016",
  "stage": "M2",
  "title": "M2阶段验收与M3准入评审",
  "goal": "M2阶段验收与M3准入评审",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "项目/业务/技术/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M2-016/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M2-015"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "只读/联合/建议验收与有限写入准入限制"
  ],
  "acceptance": [
    {
      "id": "M2-016/AC1",
      "text": "质量/安全/时延/费用达冻结标准且有证据"
    },
    {
      "id": "M2-016/AC2",
      "text": "未证收益/未开放动作保留，M2通过不自动开写"
    }
  ],
  "plannedTests": [
    "阶段证据链/值守/回滚/业务签认复核"
  ],
  "requiredEvidenceKinds": [
    "BUSINESS_UAT",
    "DESIGN_REVIEW"
  ],
  "risks": [
    "M3逐动作真实验证不能省略"
  ],
  "baselineRefs": [
    "PRD§15",
    "FSR§14"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-001 有限动作/审批岗位与源前置条件冻结

```json
{
  "id": "M3-001",
  "stage": "M3",
  "title": "有限动作/审批岗位与源前置条件冻结",
  "goal": "有限动作/审批岗位与源前置条件冻结",
  "priority": "HIGH",
  "kind": "design",
  "track": "main",
  "ownerRole": "业务/安全/ERP/CRM负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/contracts/actions-approval.md（未来）"
  ],
  "exclusiveResources": [
    "ACTION_CONTRACTS"
  ],
  "dependsOn": [
    "M2-016",
    "M0-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "两类动作schema/指纹/范围/独立审批/有效期与源条件合同"
  ],
  "acceptance": [
    {
      "id": "M3-001/AC1",
      "text": "仅ERP采购草稿/CRM内部工单，确认/提交/批准/执行分别授权"
    },
    {
      "id": "M3-001/AC2",
      "text": "源原子条件、多对象不变量、key期限及NOT_FOUND权威性有证据或明确禁用"
    }
  ],
  "plannedTests": [
    "岗位/动作/竞态合同评审及沙箱验证计划"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "V06/V07；源保障缺失不得靠模型/本地锁弥补"
  ],
  "baselineRefs": [
    "HLD§12.3/13.2.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-002 C02独立审批及有效性校验

```json
{
  "id": "M3-002",
  "stage": "M3",
  "title": "C02独立审批及有效性校验",
  "goal": "C02独立审批及有效性校验",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "C02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/collaboration/approvals/",
    "tests/integration/approvals/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-001",
    "M2-009"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "审批决策/拒绝/撤销/过期及只读建议版本端口"
  ],
  "acceptance": [
    {
      "id": "M3-002/AC1",
      "text": "另一授权人员批准冻结版本/指纹/范围，参数变更失效"
    },
    {
      "id": "M3-002/AC2",
      "text": "APPROVED不创建执行/源动作；C02不写C01状态"
    }
  ],
  "plannedTests": [
    "独立岗位/代理/过期/撤销/版本变更与AC-10测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "岗位/有效期未签认不启用审批用途"
  ],
  "baselineRefs": [
    "HLD§12.3/13.1",
    "PRD AC-10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-003 C01/C02原子提交审批

```json
{
  "id": "M3-003",
  "stage": "M3",
  "title": "C01/C02原子提交审批",
  "goal": "C01/C02原子提交审批",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "C01/C02集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/collaboration/suggestions/",
    "src/commerce_hub/collaboration/approvals/",
    "tests/faults/approval_submission/"
  ],
  "exclusiveResources": [
    "APPROVAL_SUBMIT_CONTRACT"
  ],
  "dependsOn": [
    "M3-002"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "C01唯一SubmitForApproval协调、窄端口/无环装配"
  ],
  "acceptance": [
    {
      "id": "M3-003/AC1",
      "text": "同一MySQL事务写C01 SUBMITTED+C02 PENDING+审计，内层不commit"
    },
    {
      "id": "M3-003/AC2",
      "text": "响应丢失同command返回原approval，确认不自动提交"
    }
  ],
  "plannedTests": [
    "写C02后/写C01后/审计时/commit前故障与并发提交测试"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "不能共享多个Session冒充原子；无网络等锁"
  ],
  "baselineRefs": [
    "HLD§12.3",
    "HLD ER08"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-004 C03执行意图与受控分派

```json
{
  "id": "M3-004",
  "stage": "M3",
  "title": "C03执行意图与受控分派",
  "goal": "C03执行意图与受控分派",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "C03负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/collaboration/executions/",
    "tests/integration/executions/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-003",
    "M1-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "稳定executionKey/批准指纹/READY意图与I01工作项"
  ],
  "acceptance": [
    {
      "id": "M3-004/AC1",
      "text": "仅显式执行命令且当前批准/范围有效才受理"
    },
    {
      "id": "M3-004/AC2",
      "text": "发送前状态门禁严格，SENDING/UNKNOWN先核对，不注册模型工具"
    }
  ],
  "plannedTests": [
    "同key异payload拒绝、重复命令/批准失效/无权/状态分流"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "技术受理202不等于源创建成功"
  ],
  "baselineRefs": [
    "HLD§13",
    "AI ER05/06/09"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-005 ERP采购草稿ActionAdapter

```json
{
  "id": "M3-005",
  "stage": "M3",
  "title": "ERP采购草稿ActionAdapter",
  "goal": "ERP采购草稿ActionAdapter",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "ERP/C03集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/actions/erp_draft/",
    "tests/integration/actions/erp/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-004",
    "M3-001"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "readPreconditions/原子条件execute/queryReceipt的ERP适配"
  ],
  "acceptance": [
    {
      "id": "M3-005/AC1",
      "text": "源真实幂等/回执/多对象条件覆盖成立，单号可核对"
    },
    {
      "id": "M3-005/AC2",
      "text": "只创建草稿，不采购批准/付款/库存调整；无保证则关闭"
    }
  ],
  "plannedTests": [
    "沙箱真实创建/条件冲突/并发变化/响应丢失/原key查询"
  ],
  "requiredEvidenceKinds": [
    "REAL_ACTION"
  ],
  "risks": [
    "来源不支持安全保证时BLOCKED，Mock不能替代"
  ],
  "baselineRefs": [
    "HLD§13.2.1",
    "FSR§6.3"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-006 CRM内部工单ActionAdapter

```json
{
  "id": "M3-006",
  "stage": "M3",
  "title": "CRM内部工单ActionAdapter",
  "goal": "CRM内部工单ActionAdapter",
  "priority": "HIGH",
  "kind": "integration",
  "track": "main",
  "ownerRole": "CRM/C03集成人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/adapters/actions/crm_ticket/",
    "tests/integration/actions/crm/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-004",
    "M3-001"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "内部工单前置读取/原子执行/回执适配"
  ],
  "acceptance": [
    {
      "id": "M3-006/AC1",
      "text": "真实目标对象/归属/权限与源原子条件可验证"
    },
    {
      "id": "M3-006/AC2",
      "text": "只创建内部工单，不发客户消息/退款；创建非解决"
    }
  ],
  "plannedTests": [
    "真实创建/重复/对象变化/迟到回执/原key核对"
  ],
  "requiredEvidenceKinds": [
    "REAL_ACTION"
  ],
  "risks": [
    "授权/幂等/回执不足则禁用此动作"
  ],
  "baselineRefs": [
    "HLD§13.2.1",
    "PRD§3/10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-007 C03 UNKNOWN原键恢复与业务结果关联

```json
{
  "id": "M3-007",
  "stage": "M3",
  "title": "C03 UNKNOWN原键恢复与业务结果关联",
  "goal": "实现并验证C03共用原键核对/UNKNOWN恢复机制；以受控适配fixture验证公共机制，真实源证据分别由M3-010/011收口，不互相挂靠",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "C03/测试负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/collaboration/executions/",
    "tests/faults/execution_recovery/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-004",
    "M3-001"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "SENDING/UNKNOWN恢复、原key查询与有条件原key重试",
    "源业务后续状态独立关联"
  ],
  "acceptance": [
    {
      "id": "M3-007/AC1",
      "text": "未证未创建不重发/不换key；旧lease不能推断源未执行"
    },
    {
      "id": "M3-007/AC2",
      "text": "SUCCEEDED只表示草稿/工单已建，业务状态不覆盖执行事实"
    }
  ],
  "plannedTests": [
    "ActionAdapter契约fixture下的响应丢失/伪NOT_FOUND/重入/旧lease/核对耗尽/撤销测试；真实AC-11按ERP和CRM分别在启用门槛复验"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "公共机制fixture通过不证明任何真实源幂等/回执；未通过逐动作REAL_ACTION门槛仍不得启用"
  ],
  "baselineRefs": [
    "HLD§11/13",
    "PRD AC-11"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-008 W01人工协作与执行状态视图

```json
{
  "id": "M3-008",
  "stage": "M3",
  "title": "W01人工协作与执行状态视图",
  "goal": "W01人工协作与执行状态视图",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "W01/C负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/workspace/",
    "已选W01前端目录（未来）",
    "tests/uat/actions/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-003",
    "M3-004",
    "M3-007"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "确认/明确提交/独立决策/另行执行入口、源回执/业务状态视图"
  ],
  "acceptance": [
    {
      "id": "M3-008/AC1",
      "text": "每个终点独立且有真实用户命令；AI审校非批准"
    },
    {
      "id": "M3-008/AC2",
      "text": "UNKNOWN/部分/过期/失败可解释，前端不自判执行成功"
    }
  ],
  "plannedTests": [
    "岗位分离/按钮命令/重复点击/回执/状态与审计UAT"
  ],
  "requiredEvidenceKinds": [
    "BUSINESS_UAT",
    "SECURITY"
  ],
  "risks": [
    "不得串联“批准即执行”"
  ],
  "baselineRefs": [
    "HLD§6.3/13",
    "PRD§10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-009 写入安全/事务/源竞态综合验收

```json
{
  "id": "M3-009",
  "stage": "M3",
  "title": "写入公共机制安全与事务故障验收",
  "goal": "验证审批/执行公共机制与安全门禁，真实源条件/竞态/回执逐动作在M3-010/011验收，不使ERP启用依赖CRM或相反",
  "priority": "HIGH",
  "kind": "development",
  "track": "main",
  "ownerRole": "安全/测试/系统负责人",
  "assignee": null,
  "allowedPaths": [
    "tests/faults/actions/",
    "tests/security/actions/",
    "docs/evidence/M3-009/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-007",
    "M3-008"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "审批事务、权限/状态门禁、原键恢复与条件拒绝的公共机制故障报告（受控fixture）"
  ],
  "acceptance": [
    {
      "id": "M3-009/AC1",
      "text": "C01/C02同事务回滚、当前权限/批准/旧lease门禁、UNKNOWN不换key的公共机制通过"
    },
    {
      "id": "M3-009/AC2",
      "text": "模型无写工具；源条件冲突/回执未知的fixture验证不冒称真实源保障，真实AC-10/11仍逐动作验收"
    }
  ],
  "plannedTests": [
    "真实MySQL审批/执行事务故障、权限撤销/状态/旧Worker及受控ActionAdapter的条件冲突/响应丢失负例"
  ],
  "requiredEvidenceKinds": [
    "SIMULATED_ENGINEERING",
    "SECURITY"
  ],
  "risks": [
    "公共机制通过不授权真实写入；ERP与CRM各自需真实来源证据，不互作替代"
  ],
  "baselineRefs": [
    "HLD§12.3/13.2.1",
    "FSR§9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-010 ERP动作逐项启用门槛与受控发布

```json
{
  "id": "M3-010",
  "stage": "M3",
  "title": "ERP动作逐项启用门槛与受控发布",
  "goal": "ERP动作逐项启用门槛与受控发布",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "ERP/采购/安全/运维负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/releases/erp-draft-enable.md（未来）",
    "ERP动作启用配置（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-009",
    "M3-005"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "ERP草稿限定对象/岗位/版本/期限的启用批准和发布证据"
  ],
  "acceptance": [
    {
      "id": "M3-010/AC1",
      "text": "所有真实源条件/幂等/回执/岗位/恢复证据已签认"
    },
    {
      "id": "M3-010/AC2",
      "text": "只开批准范围，禁用/回滚不谎称撤回在途动作"
    },
    {
      "id": "M3-010/AC3",
      "text": "在真实ERP沙箱重跑AC-10/11、源并发/原子条件、伪NOT_FOUND/响应丢失/原key核对；不依赖CRM适配已通过"
    }
  ],
  "plannedTests": [
    "逐动作上线前复验/灰度/停止和UNKNOWN值守演练"
  ],
  "requiredEvidenceKinds": [
    "REAL_ACTION",
    "OPERATIONS",
    "BUSINESS_UAT"
  ],
  "risks": [
    "来源能力不达标保持关闭，任务不虚标ACCEPTED"
  ],
  "baselineRefs": [
    "HLD§13/19",
    "FSR§14"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-011 CRM动作逐项启用门槛与受控发布

```json
{
  "id": "M3-011",
  "stage": "M3",
  "title": "CRM动作逐项启用门槛与受控发布",
  "goal": "CRM动作逐项启用门槛与受控发布",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "CRM/客服/安全/运维负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/releases/crm-ticket-enable.md（未来）",
    "CRM动作启用配置（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-009",
    "M3-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "CRM内部工单限定范围启用和回执/后续跟踪"
  ],
  "acceptance": [
    {
      "id": "M3-011/AC1",
      "text": "当前权限/批准/源条件/幂等/回执全部具证据"
    },
    {
      "id": "M3-011/AC2",
      "text": "无客户发送/退款；工单创建与解决分开计量"
    },
    {
      "id": "M3-011/AC3",
      "text": "在真实CRM沙箱重跑AC-10/11、源条件/回执延迟/响应丢失/同key恢复；不依赖ERP适配已通过"
    }
  ],
  "plannedTests": [
    "逐动作真实复验/灰度/回滚/未知责任交接"
  ],
  "requiredEvidenceKinds": [
    "REAL_ACTION",
    "OPERATIONS",
    "BUSINESS_UAT"
  ],
  "risks": [
    "CRM不能满足合同即维持关闭，不借ERP门槛通过代替"
  ],
  "baselineRefs": [
    "HLD§13/19",
    "FSR§14"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M3-012 M3有限动作阶段验收

```json
{
  "id": "M3-012",
  "stage": "M3",
  "title": "M3有限动作阶段验收",
  "goal": "M3有限动作阶段验收",
  "priority": "HIGH",
  "kind": "gate",
  "track": "main",
  "ownerRole": "项目/业务/技术/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/evidence/M3-012/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-010",
    "M3-011"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "两类限定动作及审批/执行/跟踪阶段验收与运营交接"
  ],
  "acceptance": [
    {
      "id": "M3-012/AC1",
      "text": "两个动作分别具真实证据，未获资格的动作不能开放"
    },
    {
      "id": "M3-012/AC2",
      "text": "执行/业务结果/收益不混；备份/恢复/值守责任落实"
    }
  ],
  "plannedTests": [
    "源结果抽查、阶段安全/恢复/岗位/运营复核"
  ],
  "requiredEvidenceKinds": [
    "REAL_ACTION",
    "OPERATIONS",
    "DESIGN_REVIEW"
  ],
  "risks": [
    "任一动作受阻则M3完整交付未完成；调整阶段退出需另行评审"
  ],
  "baselineRefs": [
    "PRD§15",
    "FSR§14"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-001 S01学习型需求/交期预测验证与接入

```json
{
  "id": "M4-001",
  "stage": "M4",
  "title": "S01学习型需求/交期预测验证与接入",
  "goal": "S01学习型需求/交期预测验证与接入",
  "priority": "STANDARD",
  "kind": "validation",
  "track": "main",
  "ownerRole": "S01/B02/算法负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/forecasting/",
    "tests/evaluation/forecasting/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M1-030",
    "M2-003"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "按销量形态/促销/缺货分层的滚动回测和获准提供方"
  ],
  "acceptance": [
    {
      "id": "M4-001/AC1",
      "text": "截止/测试窗口无未来信息泄漏，比较简单与现有基线"
    },
    {
      "id": "M4-001/AC2",
      "text": "没有可验证收益则保留基线，不能声称学习模型已生产有效"
    }
  ],
  "plannedTests": [
    "滚动切分/冷启动/间歇需求/约束与业务影响对照"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "历史长度/质量/算力许可不足先验证不部署"
  ],
  "baselineRefs": [
    "PRD候选6",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-002 S01滞销库存治理

```json
{
  "id": "M4-002",
  "stage": "M4",
  "title": "S01滞销库存治理",
  "goal": "S01滞销库存治理",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S01/库存负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s01_supply_inventory/",
    "tests/scenarios/s01/slow_moving/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-003",
    "M2-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "库龄/剩余需求/贡献的滞销分群与候选建议"
  ],
  "acceptance": [
    {
      "id": "M4-002/AC1",
      "text": "复用库存/需求/贡献指标，无第二台账"
    },
    {
      "id": "M4-002/AC2",
      "text": "假设/范围/证据清楚，不自动清仓改价/调库存"
    }
  ],
  "plannedTests": [
    "真实库龄/低销量/费用缺项与候选人工核对"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "处置收益/数据口径未证实不得承诺释放利润"
  ],
  "baselineRefs": [
    "PRD候选7",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-003 S01供应商风险分析

```json
{
  "id": "M4-003",
  "stage": "M4",
  "title": "S01供应商风险分析",
  "goal": "S01供应商风险分析",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S01/采购负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s01_supply_inventory/",
    "tests/scenarios/s01/supplier/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-003"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "交付/短收/质检指标与供应风险解释"
  ],
  "acceptance": [
    {
      "id": "M4-003/AC1",
      "text": "复用B01/B02与ERP档案，不重建供应商主数据"
    },
    {
      "id": "M4-003/AC2",
      "text": "缺覆盖/关联不明显式待核，不编造履约承诺"
    }
  ],
  "plannedTests": [
    "真实供应/交期/质量样本与时点/来源核对"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "供应数据合法取得和业务阈值是前提"
  ],
  "baselineRefs": [
    "PRD候选8",
    "AI§14.1"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-004 S02运输到货风险扩展

```json
{
  "id": "M4-004",
  "stage": "M4",
  "title": "S02运输到货风险扩展",
  "goal": "S02运输到货风险扩展",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S02/B02/物流负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s02_fulfillment/",
    "src/commerce_hub/adapters/sources/获准物流源/",
    "tests/scenarios/s02/eta/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-004",
    "M1-030"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "授权物流事件/到仓至可售终点预测与风险"
  ],
  "acceptance": [
    {
      "id": "M4-004/AC1",
      "text": "新增物流源按D01/D02接入，非独立取数链"
    },
    {
      "id": "M4-004/AC2",
      "text": "预测区间/截止/覆盖与B01指标相容，不把到港当可售"
    }
  ],
  "plannedTests": [
    "滚动回测/迟到事件/缺跟踪/日期终点对照"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "外部物流接口/预测能力另验证"
  ],
  "baselineRefs": [
    "PRD候选9",
    "AI§14.2"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-005 S04费用账单核查深化

```json
{
  "id": "M4-005",
  "stage": "M4",
  "title": "S04费用账单核查深化",
  "goal": "S04费用账单核查深化",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S04/财务负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s04_contribution_fees/",
    "tests/scenarios/s04/bill_audit/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "账单匹配/分类/差异及核查候选"
  ],
  "acceptance": [
    {
      "id": "M4-005/AC1",
      "text": "复用同费用/币种/版本口径，不自创财务公式"
    },
    {
      "id": "M4-005/AC2",
      "text": "实际追回/避免成本与贡献变动去重，不自动改账"
    }
  ],
  "plannedTests": [
    "累计/增量/退款/币种/部分费用与真实核查样本"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "真实账单字段/匹配标准/财务责任未定先冻结"
  ],
  "baselineRefs": [
    "PRD候选14",
    "AI§14.4"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-006 A03完整即席QueryRun与知识助手

```json
{
  "id": "M4-006",
  "stage": "M4",
  "title": "A03完整即席QueryRun与知识助手",
  "goal": "A03完整即席QueryRun与知识助手",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "A03负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/capabilities/retrieval/",
    "tests/faults/adhoc_query/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M1-034",
    "M1-032"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "请求/周期/并发配额、去重、期限、未知核对与受控回答"
  ],
  "acceptance": [
    {
      "id": "M4-006/AC1",
      "text": "多API竞争不超发，新queryId/切入口不能重复领额"
    },
    {
      "id": "M4-006/AC2",
      "text": "长/复杂分析返回ANALYSIS_TASK_REQUIRED，不伪造正式O01报告"
    },
    {
      "id": "M4-006/AC3",
      "text": "未配置金额/超时/可信计价时收费入口关闭"
    }
  ],
  "plannedTests": [
    "HLD6.4单次/周期/双实例/断连/未知usage/命令重复测试"
  ],
  "requiredEvidenceKinds": [
    "SECURITY",
    "MODEL_EVAL",
    "SIMULATED_ENGINEERING"
  ],
  "risks": [
    "跨入口总额未验证不启相关付费用途"
  ],
  "baselineRefs": [
    "HLD§6.4",
    "AI§3/6/10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-007 S05客服/售后辅助专项验证与设计

```json
{
  "id": "M4-007",
  "stage": "M4",
  "title": "S05客服/售后辅助专项验证与设计",
  "goal": "S05客服/售后辅助专项验证与设计",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S05/客服负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s05-design.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-005",
    "M1-034"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "多语言/政策/订单权限/复核标准及MVP范围"
  ],
  "acceptance": [
    {
      "id": "M4-007/AC1",
      "text": "默认意图澄清+固定RAG+草稿Workflow，多Agent不必需"
    },
    {
      "id": "M4-007/AC2",
      "text": "复用S03已发布主题；发送/退款不在动作范围"
    }
  ],
  "plannedTests": [
    "授权样本/语言/政策适用/无依据承诺金标准评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "REAL_READ"
  ],
  "risks": [
    "政策来源/语言样本/客服权限待验证"
  ],
  "baselineRefs": [
    "PRD候选10/11",
    "AI§14.5"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-008 S05客服/售后辅助MVP

```json
{
  "id": "M4-008",
  "stage": "M4",
  "title": "S05客服/售后辅助MVP",
  "goal": "S05客服/售后辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S05负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s05_customer_assistance/",
    "tests/scenarios/s05/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-007",
    "M1-032",
    "M1-033"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "内部回复草稿、事实引用/澄清与人工接手"
  ],
  "acceptance": [
    {
      "id": "M4-008/AC1",
      "text": "不发送客户消息/承诺赔付，客户上下文隔离"
    },
    {
      "id": "M4-008/AC2",
      "text": "缺政策/订单证据/意图不清正确澄清，默认无Loop"
    }
  ],
  "plannedTests": [
    "语言/政策时效/注入/客户资料隔离/人工草稿验收"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "SECURITY",
    "BUSINESS_UAT"
  ],
  "risks": [
    "ReAct仅另证固定Workflow不足后评估"
  ],
  "baselineRefs": [
    "AI§14.5"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-009 S06内容与增长专项设计

```json
{
  "id": "M4-009",
  "stage": "M4",
  "title": "S06内容与增长专项设计",
  "goal": "S06内容与增长专项设计",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S06/商品/增长负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s06-design.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "本地化/术语/素材许可/期间广告数据与审核标准"
  ],
  "acceptance": [
    {
      "id": "M4-009/AC1",
      "text": "默认生成+确定性事实校验+人工，Reviewer非审批"
    },
    {
      "id": "M4-009/AC2",
      "text": "广告无订单归因证据不伪造；发布/投放仍不开放"
    }
  ],
  "plannedTests": [
    "真实商品/素材/渠道授权、禁用声明与归因评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "REAL_READ"
  ],
  "risks": [
    "品牌/市场标准及新增广告字段需验证"
  ],
  "baselineRefs": [
    "PRD候选12/13",
    "AI§14.6"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-010 S06本地化与增长辅助MVP

```json
{
  "id": "M4-010",
  "stage": "M4",
  "title": "S06本地化与增长辅助MVP",
  "goal": "S06本地化与增长辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S06负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s06_content_growth/",
    "tests/scenarios/s06/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-009",
    "M1-032",
    "M1-034"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "有限候选文案/素材建议/广告诊断假设"
  ],
  "acceptance": [
    {
      "id": "M4-010/AC1",
      "text": "事实/术语/授权与人工审核成立，无自动发布/投放"
    },
    {
      "id": "M4-010/AC2",
      "text": "增长收益另经可比实验，不用文案评分替代收益"
    }
  ],
  "plannedTests": [
    "事实/语言/禁用声明/素材许可/归因限制与成本评测"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT",
    "SECURITY"
  ],
  "risks": [
    "优化循环/多模型Reviewer默认暂缓"
  ],
  "baselineRefs": [
    "AI§14.6"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-011 S07单证抽取与校验专项验证

```json
{
  "id": "M4-011",
  "stage": "M4",
  "title": "S07单证抽取与校验专项验证",
  "goal": "S07单证抽取与校验专项验证",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S07/A02/单证负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s07-design.md（未来）",
    "src/commerce_hub/capabilities/understanding/获准文档提供方/",
    "tests/evaluation/documents/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M1-033",
    "M1-014"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "版式/语种/字段定位/核对规则与专业解析器验证"
  ],
  "acceptance": [
    {
      "id": "M4-011/AC1",
      "text": "关键字段低置信/UNKNOWN进入人工，OCR不确认主数据"
    },
    {
      "id": "M4-011/AC2",
      "text": "默认抽取+确定性跨单核对，文件类型/大小/页数有界"
    }
  ],
  "plannedTests": [
    "授权真实版式/关键字段/页覆盖/恶意文件对照"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "MODEL_EVAL",
    "SECURITY"
  ],
  "risks": [
    "解析器能力/许可/材料不足不能声称准确率"
  ],
  "baselineRefs": [
    "PRD候选15",
    "AI§14.7"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-012 S07单证辅助MVP

```json
{
  "id": "M4-012",
  "stage": "M4",
  "title": "S07单证辅助MVP",
  "goal": "S07单证辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S07负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s07_documents/",
    "tests/scenarios/s07/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-011"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "字段/差异/原文位置/UNKNOWN/复核清单"
  ],
  "acceptance": [
    {
      "id": "M4-012/AC1",
      "text": "A02/D04产物复用，跨单规则属于S07"
    },
    {
      "id": "M4-012/AC2",
      "text": "未覆盖页不当无差异，不写ERP/办理报关"
    }
  ],
  "plannedTests": [
    "关键字段/数量单位/映射/差异召回/人工修订UAT"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "未知字段/单位不能模型猜补"
  ],
  "baselineRefs": [
    "AI§14.7"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-013 S08经营规划专项数据与约束验证

```json
{
  "id": "M4-013",
  "stage": "M4",
  "title": "S08经营规划专项数据与约束验证",
  "goal": "S08经营规划专项数据与约束验证",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S08/经营/B02负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s08-design.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M2-003",
    "M2-005",
    "M2-006"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "选品/定价促销/多仓子问题、授权市场/仓网/目标函数与约束"
  ],
  "acceptance": [
    {
      "id": "M4-013/AC1",
      "text": "默认B02求解+B01评价+解释，无必须自主Agent证据"
    },
    {
      "id": "M4-013/AC2",
      "text": "复用S01已发布预测与S03/S04结果，不假设价格弹性/仓容"
    }
  ],
  "plannedTests": [
    "真实资料授权/目标约束/缺项/可解释性评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "REAL_READ"
  ],
  "risks": [
    "P2市场/预测/成本/仓网数据可能不足"
  ],
  "baselineRefs": [
    "PRD候选18—20",
    "AI§14.8"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-014 S08市场与选品辅助MVP

```json
{
  "id": "M4-014",
  "stage": "M4",
  "title": "S08市场与选品辅助MVP",
  "goal": "S08市场与选品辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S08负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s08_planning/market/",
    "tests/scenarios/s08/market/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-013",
    "M1-034"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "有来源的市场/选品比较与假设"
  ],
  "acceptance": [
    {
      "id": "M4-014/AC1",
      "text": "只用授权资料，区分事实/推断/缺口"
    },
    {
      "id": "M4-014/AC2",
      "text": "无来源不足时返回验证方案，不编造销量/收益"
    }
  ],
  "plannedTests": [
    "来源/版本/权限/对照/未知与人工经营评审"
  ],
  "requiredEvidenceKinds": [
    "REAL_READ",
    "BUSINESS_UAT"
  ],
  "risks": [
    "缺授权资料不能以全网抓取替代"
  ],
  "baselineRefs": [
    "AI§14.8",
    "FSR§4"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-015 S08定价促销模拟MVP

```json
{
  "id": "M4-015",
  "stage": "M4",
  "title": "S08定价促销模拟MVP",
  "goal": "S08定价促销模拟MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S08/B02负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s08_planning/pricing/",
    "tests/scenarios/s08/pricing/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-013",
    "M1-030"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "明确假设的价格/促销候选与B01评价"
  ],
  "acceptance": [
    {
      "id": "M4-015/AC1",
      "text": "约束可核验，预测/模拟非因果收益或已批准价格"
    },
    {
      "id": "M4-015/AC2",
      "text": "不自动改价/投放，LLM不替代求解器"
    }
  ],
  "plannedTests": [
    "约束/无解/币种/敏感性/历史对照与业务复核"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "需求响应参数未证实须假设标注或阻断"
  ],
  "baselineRefs": [
    "AI§14.8",
    "PRD候选19"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-016 S08多仓布局优化MVP

```json
{
  "id": "M4-016",
  "stage": "M4",
  "title": "S08多仓布局优化MVP",
  "goal": "S08多仓布局优化MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S08/B02/仓配负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s08_planning/warehouses/",
    "tests/scenarios/s08/warehouses/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-013",
    "M1-030",
    "M2-003"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "复用S01有效预测的仓网候选/服务成本与约束比较"
  ],
  "acceptance": [
    {
      "id": "M4-016/AC1",
      "text": "B02候选调用B01，不重复预测或建库存账"
    },
    {
      "id": "M4-016/AC2",
      "text": "容量/时效/成本版本明确，无可行解不靠LLM松约束；不调仓"
    }
  ],
  "plannedTests": [
    "真实仓网/覆盖/假设/无解/方案指标与人工验收"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT"
  ],
  "risks": [
    "仓网/需求与成本不齐则专项延期"
  ],
  "baselineRefs": [
    "AI§14.8",
    "PRD候选20"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-017 S09缺陷标准与视觉提供方专项验证

```json
{
  "id": "M4-017",
  "stage": "M4",
  "title": "S09缺陷标准与视觉提供方专项验证",
  "goal": "S09缺陷标准与视觉提供方专项验证",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S09/A02/质检负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s09-design.md（未来）",
    "tests/evaluation/visual/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M1-033"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "缺陷/拍摄标准、正负样本、模型许可/算力和人工责任"
  ],
  "acceptance": [
    {
      "id": "M4-017/AC1",
      "text": "默认视觉能力Workflow，不把多图片当多Agent"
    },
    {
      "id": "M4-017/AC2",
      "text": "按类别/商品/拍摄条件评漏检/未知，不凭正常图平均数放行"
    }
  ],
  "plannedTests": [
    "真实授权图像/跨商品泛化/模糊遮挡/未见类别验证"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "MODEL_EVAL"
  ],
  "risks": [
    "视觉精度、坐标定位和GPU需求均未证实"
  ],
  "baselineRefs": [
    "PRD候选21",
    "AI§14.9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-018 S09视觉质检辅助MVP

```json
{
  "id": "M4-018",
  "stage": "M4",
  "title": "S09视觉质检辅助MVP",
  "goal": "S09视觉质检辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S09负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s09_visual_quality/",
    "tests/scenarios/s09/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-017"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "可疑缺陷/区域引用/UNKNOWN和人工复核"
  ],
  "acceptance": [
    {
      "id": "M4-018/AC1",
      "text": "A02视觉结果可追溯，技术失败不等于无缺陷"
    },
    {
      "id": "M4-018/AC2",
      "text": "不自动放行/报废/库存调整；能力不支持定位时明确限制"
    }
  ],
  "plannedTests": [
    "重点缺陷漏检/误报/图像质量/区域及人工UAT"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT",
    "SECURITY"
  ],
  "risks": [
    "实际模型/硬件仅验证后部署，不默认更便宜"
  ],
  "baselineRefs": [
    "AI§14.9"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-019 S10政策来源与专业复核标准

```json
{
  "id": "M4-019",
  "stage": "M4",
  "title": "S10政策来源与专业复核标准",
  "goal": "S10政策来源与专业复核标准",
  "priority": "STANDARD",
  "kind": "design",
  "track": "main",
  "ownerRole": "S10/专业/数据负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/scenarios/s10-design.md（未来）",
    "docs/policy-corpus-register.md（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M3-012",
    "M1-034"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "授权官方资料版本/时间地区/商品属性/更新责任与金标准"
  ],
  "acceptance": [
    {
      "id": "M4-019/AC1",
      "text": "默认版本化RAG+条款比对+专业复核，无最终合规批准"
    },
    {
      "id": "M4-019/AC2",
      "text": "有效/废止/例外/冲突来源可追，不默认联网Agent"
    }
  ],
  "plannedTests": [
    "资料适用时间/地区/条款反证/专业裁决评审"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW",
    "REAL_READ"
  ],
  "risks": [
    "专业岗位/来源更新/属性标准不足则不启用"
  ],
  "baselineRefs": [
    "PRD候选22",
    "AI§14.10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-020 S10政策核查辅助MVP

```json
{
  "id": "M4-020",
  "stage": "M4",
  "title": "S10政策核查辅助MVP",
  "goal": "S10政策核查辅助MVP",
  "priority": "STANDARD",
  "kind": "development",
  "track": "main",
  "ownerRole": "S10负责人",
  "assignee": null,
  "allowedPaths": [
    "src/commerce_hub/scenarios/s10_policy_check/",
    "tests/scenarios/s10/"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-019",
    "M1-032"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "有引用的条款匹配/适用问题/冲突与待复核清单"
  ],
  "acceptance": [
    {
      "id": "M4-020/AC1",
      "text": "过期/缺属性/地区不明不作确定合规结论"
    },
    {
      "id": "M4-020/AC2",
      "text": "例外/否定不被摘要丢失，专业复核非模型自评；不监管提交"
    }
  ],
  "plannedTests": [
    "有效版本/反证/缺项/未知/专业人工与安全评测"
  ],
  "requiredEvidenceKinds": [
    "MODEL_EVAL",
    "BUSINESS_UAT",
    "SECURITY"
  ],
  "risks": [
    "语义补证Loop须另证收益，不自动引入"
  ],
  "baselineRefs": [
    "AI§14.10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-021 高级AI/检索/运行技术按需评估

```json
{
  "id": "M4-021",
  "stage": "M4",
  "title": "高级AI/检索/运行技术按需评估",
  "goal": "高级AI/检索/运行技术按需评估",
  "priority": "LOW",
  "kind": "design",
  "track": "main",
  "ownerRole": "架构/AI/运维负责人",
  "assignee": null,
  "allowedPaths": [
    "docs/DECISIONS.md",
    "docs/evidence/M4-021/（未来）"
  ],
  "exclusiveResources": [
    "ARCHITECTURE_DECISIONS"
  ],
  "dependsOn": [
    "M3-012",
    "M2-012",
    "M2-013"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "基于真实使用方的Loop/多角色/框架/缓存/Memory/索引/队列评估"
  ],
  "acceptance": [
    {
      "id": "M4-021/AC1",
      "text": "对照现有Workflow质量/费用/复杂度，允许结论为不引入"
    },
    {
      "id": "M4-021/AC2",
      "text": "任何后续实现另建获准任务/契约/证据，不把评估通过当能力已建"
    },
    {
      "id": "M4-021/AC3",
      "text": "缓存实际输出分类/暂停恢复协议等启用门槛不省略"
    }
  ],
  "plannedTests": [
    "需求/收益/隔离/许可/运维和替代方案审查"
  ],
  "requiredEvidenceKinds": [
    "DESIGN_REVIEW"
  ],
  "risks": [
    "只评估、不要求同时建设Redis/MQ/Milvus/Neo4j等"
  ],
  "baselineRefs": [
    "AI§8/9/11/15",
    "ARCH§10"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

## M4-022 完整规划分批发布、回归与运营验收

```json
{
  "id": "M4-022",
  "stage": "M4",
  "title": "完整规划分批发布、回归与运营验收",
  "goal": "完整规划分批发布、回归与运营验收",
  "priority": "STANDARD",
  "kind": "gate",
  "track": "main",
  "ownerRole": "项目/业务/技术/运维/独立评审者",
  "assignee": null,
  "allowedPaths": [
    "docs/releases/expansion/（未来）",
    "docs/evidence/M4-022/（未来）"
  ],
  "exclusiveResources": [],
  "dependsOn": [
    "M4-001",
    "M4-002",
    "M4-003",
    "M4-004",
    "M4-005",
    "M4-006",
    "M4-008",
    "M4-010",
    "M4-012",
    "M4-014",
    "M4-015",
    "M4-016",
    "M4-018",
    "M4-020",
    "M4-021"
  ],
  "entryConditions": [
    "本规划独立审查通过，且本任务已获实施授权"
  ],
  "parallelPolicy": "依赖已ACCEPTED、入口满足且实际文件范围不相交才可并行；公共契约/迁移/组合根/台账由集成人串行合入",
  "deliverables": [
    "各P1/P2用途分批发布/回归/备份/回滚/容量/运营责任及收益观察"
  ],
  "acceptance": [
    {
      "id": "M4-022/AC1",
      "text": "每个用途各过数据/质量/安全/费用/运维门槛，不等同十场景同时上线"
    },
    {
      "id": "M4-022/AC2",
      "text": "收益与产能/现金分开核算，S01—S10/22候选覆盖可追"
    },
    {
      "id": "M4-022/AC3",
      "text": "阶段未具备场景保持TODO/BLOCKED，不编造总产品完成率"
    }
  ],
  "plannedTests": [
    "P0全回归、扩展UAT/隔离/容量、恢复/发布/业务观察复核"
  ],
  "requiredEvidenceKinds": [
    "OPERATIONS",
    "BUSINESS_UAT",
    "SECURITY"
  ],
  "risks": [
    "完整产品预算和工期需逐项数据/人员/报价验证，不取可研占位值"
  ],
  "baselineRefs": [
    "PRD§5.2/15",
    "FSR§11/12/14",
    "AI§15"
  ],
  "status": "TODO",
  "implementationCommits": [],
  "testedCommit": null,
  "evidence": [],
  "review": null,
  "blocker": null,
  "branch": null,
  "baseCommit": null,
  "latestHandoffRef": null,
  "draftEvidenceRefs": [],
  "history": []
}
```

