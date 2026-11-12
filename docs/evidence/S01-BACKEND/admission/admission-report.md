# S01 来源与规则准入适配证据

日期：2026-11-12
基线：`e547335323fd19fccd324752dbeb1d08c9e21c2d`
范围：仅来源/规则准入包、规范化适配和离线测试；未读取 ERP、未签认业务规则、未执行采购写入。

## 结果

- 工程实现：PASS。`AdmissionPackage` 使用 Pydantic `extra=forbid`，默认生产入口拒绝工程模式、测试证据级别、模拟/未知必需来源和明显测试引用 scheme。
- 逐字段绑定：PASS。scope、asOf、coverage、mapping、库存/需求/供给集合、行关键值和 policy 均须有唯一来源记录；每条记录含 nature、sourceVersion、owner、sourceRef、observedAt 和规范化 JSON `valueDigest`。集合摘要覆盖完整行，另以 recordCount 声明集合完整性。
- 受控补充：PASS。`CONTROLLED_FACT` 缺少 `factBasis` 时 schema 阻断；模块不读取或相信外部引用内容，只验证受信服务端装配记录的结构与绑定。
- 规则记录：PASS。仅接受 `OPERATOR_PROVIDED_CONTROLLED_RECORD`，重算内容摘要，并精确绑定 policy、scope、asOf、有效期、签认时点及现有 B01 固定语义。
- 公共适配：PASS。`normalize` 只输出公共 `AdmittedInput` 字段，不输出 `inputId`；工程模式不回退为 Fixture 成功。
- 真实 ERP 来源与业务规则签认：NOT_RUN / BLOCKED。本线没有网络调用、真实来源包或负责人签认，不能据此宣称真实 SKU 已准入。

## 接口

- `validate_admission(package, allow_test_only=False)`：返回 `AdmissionDecision` 和明确问题，不用 fixture 替代失败。
- `normalize(package, allow_test_only=False)`：仅在准入通过后返回 canonical input 字典，否则抛出带问题列表的 `AdmissionRejected`。
- `package_revision(package)`：对完整规范化包计算稳定 SHA-256。

`allow_test_only=True` 只用于离线合同形状测试。生产默认拒绝 `TEST_ONLY_CONTRACT`。测试构造器位于 `tests/support/admission.py`，不随生产源码发布；其中的 `offline-contract:` 引用没有被读取，也不是 ERP 观察或业务批准证据。

## 固定合同样例

离线样例使用 D0=`2026-11-12`、净可用库存 10、D1/D2 需求各 8、D1 在途 2、MOQ/倍数 5。它只验证适配后继续复用现有 D02/D03/B01/B02：基线缺口 4、首次缺货 D2、候选量 5、候选后期末余额 1，`procurementEligible=false`。这些数字是构造测试，不是教学 ERP 返回值或采购建议。

## 验证

- `python -m pytest -q tests/unit/data/test_admission.py --tb=short -p no:cacheprovider`：38 PASS。
- `python -m pytest -q tests/unit/data --tb=short -p no:cacheprovider`：116 PASS。
- `python -m compileall -q src/commerce_hub/data/admission tests/support/admission.py tests/unit/data/test_admission.py`：PASS。
- `git diff --check -- src/commerce_hub/data/admission tests/support/admission.py tests/unit/data/test_admission.py`：PASS。

测试全部离线，未使用 `.env.erp`、真实 MySQL 或模型额度。
