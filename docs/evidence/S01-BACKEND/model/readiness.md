# S01 model evaluation readiness

Status: **offline PASS; real request NOT_RUN; C-04 NOT_RUN**.

This line implements a bounded evaluation adapter and controlled-language validator without changing the accepted A01 gateway, the original DeepSeek provider, or the strict Mock strategy. The prepared online path uses one persistent O01 task through independent API and Worker processes. Network access is disabled by default. No real model request was sent while preparing this evidence.

## Official model and pricing snapshot

Checked on 2026-11-12 against official DeepSeek API documentation only:

- The current non-reasoning API identifier is `deepseek-flash`, mapped by the official pricing page to DeepSeek-V4.1 at the observed time.
- Peak prices per one million tokens are USD 0.006 for cache-hit input, USD 0.30 for cache-miss input, and USD 1.20 for output.
- Chat Completions reports token counts, including cache-hit/cache-miss fields where present, but does not report a billed USD amount. The adapter therefore records `actualCost=None`; dated rate arithmetic stays in this evidence document and is never settled as a G02 billing fact.
- JSON Output is requested, followed by local JSON Schema and S01 domain validation. It is not described as provider-native strict JSON Schema enforcement.

Official sources:

- `https://api-docs.deepseek.com/quick_start/pricing`
- `https://api-docs.deepseek.com/api/create-chat-completion`
- `https://api-docs.deepseek.com/guides/json_mode`

The pricing page was fetched successfully through a read-only browser on 2026-11-12. Its rendered table showed `deepseek-flash`, model version `DeepSeek-V4.1-Flash-1017`, 1M context, 384K maximum output, and peak rates of USD 0.006 cache-hit input, USD 0.30 cache-miss input, and USD 1.20 output per one million tokens. The same page states to use `deepseek-flash` as the model name and warns that prices may change. No account login or API/model call was involved.

No provider price or pricing-version constant is added to the platform. A real run must fail closed if configured model/base URL differs. Pricing must be rechecked before a later-date paid run.

For this authorization check only, the conservative maximum-rate calculation treats all 24,000 input tokens as cache misses and adds the full 1,024 output-token allowance:

```text
(24,000 × USD 0.30 / 1,000,000) + (1,024 × USD 1.20 / 1,000,000)
= USD 0.00842880 per request
= USD 0.04214400 for five A-E requests
```

This is below the USD 1 authorization. The explicit risk reservation is USD 0.05 per requested case and totals USD 0.25 for five cases. These figures only establish that the bounded paid evaluation can fit under the authorization observed on 2026-11-12. They do not become a platform price table or `actualCost`.

## Validation boundary

The output keeps the four S01 arrays: recommendation reasons, key evidence, major risks, and human confirmations. Each sentence must select one caller-approved phrase, may add one neutral wrapper, and must end with exactly one authorized fact citation. The validator checks section authorization, mandatory facts, numbers, ISO dates, UNKNOWN wording, quality-gate wording, evidence references, purchase approval/execution claims, risk denial, and extra text or prompt injection.

This is a conservative controlled language with limited natural variation. It does not prove the meaning of arbitrary prose and must not be reported as general semantic verification. B01/B02 values and business gates remain authoritative outside the model.

## Accounting and online limitation

The evaluation tool creates or idempotently reuses one stable O01 task with `max_calls = 5`, five serial A-E cases, at most 24,000 reserved tokens per request, and `max_cost = USD 1`. Each call reserves USD 0.05. The fixed authorization still has the broader ten-request ceiling, but this evaluation task cannot consume more than five. The same authorization-derived tenant, principal, command key and catalog digest are reused on every invocation; a different command key is rejected by the evaluation handler. It has no redirects, environment proxy, implicit retry, or same-logical-call resend.

The CLI does not claim work or invoke the provider. In managed mode it starts a local API process and an independent Worker process, forces one delivery attempt and a 600-second task deadline, creates the fixed task once through HTTP, polls for 660 to 900 seconds, and reads its public report before stopping its owned processes. Its fixed identity session and JWT are valid for 16 minutes, covering the maximum 900-second poll plus startup and final-read margin without refresh or task replacement. Re-running the CLI submits the same idempotency key and body. Provider exchanges and complete per-case results stay below the configured ignored `data/private/` path; stdout contains only task/report references, case IDs, the catalog digest and bounded status fields. A technically `SUCCEEDED` task is not an evaluation pass unless `analysisReport.evaluation.status` is `PASS`.

The public A01/O01/G02 integration now treats token and cost dimensions independently: token-complete, cost-null usage can return a successful validated explanation while the explicit USD risk reservation stays occupied. A different logical call may continue inside the original persistent limits; the same logical call cannot be resent. This model line does not depend on a pricing formula for send admission. The new public migration and combined integration still require verification before a paid request, so paid requests remain NOT_RUN in this readiness record. If the official model identity or maximum rates cannot be reverified immediately before the paid run, the tool must not send.

The official-rate estimate is informational evidence only. It is not an invoice, an O01 settlement amount, a production dependency, or a reason to publish or reject an explanation.

## Prepared commands

Default-safe and offline checks:

```text
python -m tools.s01_model_evaluation
python -m tools.s01_model_evaluation --offline-suite
pytest -q tests/unit/models/test_natural_explanation.py tests/unit/models/test_evaluation_provider.py
```

The paid form requires all explicit arguments and a Worker raw-output path below ignored `data/private/`. It starts and stops the dedicated API and Worker processes itself:

```text
python -m tools.s01_model_evaluation --execute --authorization-id s01-backend-20261112-v1 --max-cost-usd 1 --request-risk-usd 0.05 --max-requests 5 --private-output data/private/<result>.json
```

To use the controlled teaching-ERP catalog, add `--catalog-path data/private/<catalog>.json`. The catalog must bind the same fixed authorization and authorization-derived tenant, contain one to five ordered A-E `TEACHING_SIMULATION` entries, and normalize every entry to the exact same scope. `--external-processes --api-base-url http://127.0.0.1:<port>` is available only when the same dedicated bootstrap has already been started with `COMMERCE_S01_MODEL_EVALUATION_ENABLED=true` and the matching fixed environment.

No paid form was executed for this readiness evidence.

## Offline verification result

Executed on 2026-11-12:

- Dedicated model tests: `43 passed`.
- Offline CLI suite: `PASS`, five A-E controlled scenarios accepted and three unsupported-number/semantic-reversal/purchase-approval injections rejected.
- Default CLI: `NOT_RUN`, network `DISABLED`.
- A-E preflight computed five distinct snapshot/logical-call IDs. Conservative token upper bounds were A 10,647; B 10,193; C 10,313; D 9,944; E 10,329, all below the 24,000 per-request reservation.
- The dedicated suite also verifies that the private catalog cannot escape `data/private/`, binds authorization/tenant/scope/case order, and that the CLI performs one idempotent POST followed only by task polling and report reading.
