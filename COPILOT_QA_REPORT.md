# Backend QA Report — Brightloop Subscription Management

> **Historical report — superseded by the repository-root [TESTING_REPORT.md](TESTING_REPORT.md).** Rechecking current source disproved several listed findings: the plan trial/grace fields exist, invoice-line `product_id` is optional, product/plan eligibility is checked in `_check_plan_min_quantity`, the coupon application flow zeros the generic subscription discount rate and recurring invoice creation inherits the coupon, and the 12-step standalone test now passes. Do not treat the defect list below as current without independently verifying it.

**Branch:** `developer-2-operations`  
**Scope:** Read-only backend inspection and safe validation. No application, UI, configuration, or existing documentation files were changed.

## 1. Project structure

- `subscription_management/`: Odoo 17 addon with Python models, portal controllers, access rules, cron/sequence data, demo data, backend views, and invoice report.
- `subscription_management/tests/`: Odoo `TransactionCase` tests for the lifecycle, billing, products, plans, users, discounts, payments, and dashboard.
- `tests/`: standalone mock/simulation suites, live-XML-RPC scripts, and a 12-step mock integration test.
- Root configuration includes `__manifest__.py`, `odoo.conf`, and `docker-compose.yml`.

The addon depends on Odoo `base`, `mail`, `product`, and `account`; plan/billing code also imports `dateutil`. Recurring billing uses PostgreSQL-specific SQL locking.

## 2. Module implementation status

“Implemented in code” below describes inspected source, not a feature verified in a running Odoo server.

| Area | Models and methods found | Implementation and gaps |
|---|---|---|
| Authentication and access | `res.users` / `res.partner` extensions; `register_portal_customer`, `request_password_reset`; controller routes in `controllers/portal_auth.py`; groups, ACLs, record rules | Registration validation, password policy, portal role assignment, reset request, and customer-scoped contract/invoice endpoints are present. Actual login is Odoo-native. Routes, email delivery, ACLs, and record isolation were not runtime-tested. |
| Products and plans | `product.template` / `product.product`; `subscription.plan`; price computes and `calculate_next_billing_date` | Brand surcharge and variant-aware subscription price; daily/weekly/monthly/yearly plans, availability and quantity checks. `subscription_plan_ids` is exposed in the product view but no enforcement was found when adding a product to a subscription. |
| Subscription management | `subscription.subscription`, lines, quotation templates; lifecycle actions including confirm, activate, pause, resume, close, renew | Lifecycle transitions, pricing totals, line minimums, and MRR/ARR calculations are present. Odoo workflow and computed values were not runtime-tested. A priced plan can be confirmed without product lines, which exposes the invoice-generation defect below. |
| Discounts | `subscription.discount`; eligibility, amount calculation, usage tracking, and subscription/invoice extensions | Percentage/fixed rules and eligibility checks are present. Applying a percentage coupon also copies its rate to recurring invoice lines, then invoice-level coupon logic deducts it again; percentage totals can therefore be understated. |
| Invoices | `subscription.invoice` and invoice lines; confirm/cancel, printing, manual and recurring invoice creation | Creates a custom subscription invoice with line totals and a duplicate-period SQL constraint. It does not create/post `account.move` accounting invoices. A plan-only subscription can fail invoice creation because the required invoice-line product is missing. |
| Recurring billing | `cron_recurring_billing`, catch-up processing, manual generation, audit log; daily cron XML | Due-date processing, catch-up, duplicate checks, row locking, and per-subscription logs are implemented in source. Neither cron nor transaction/concurrency behavior was tested against PostgreSQL/Odoo. |
| Payments | `subscription.payment`, payment registration wizard, invoice reconciliation | Staff can record draft/successful/failed payment records, including partial payments. Stripe/PayPal/card values are selectable labels; no gateway transaction integration was found. |
| Dashboard and reports | `subscription.dashboard`, transient dashboard console, read-group metrics, drill-down actions, invoice QWeb report | KPI/reporting code and backend views exist. Date boundaries are applied to payment metrics, but not subscription counts/MRR or invoice/outstanding/overdue aggregations. Dashboard accuracy and report rendering were not runtime-tested. |

## 3. Tests and validation executed

| Check | Result |
|---|---|
| Python AST parse over addon and root test Python files | **Passed:** 35 files parsed. |
| XML well-formedness using Python standard-library ElementTree | **Passed:** 16 XML files parsed. This does not validate Odoo fields, XML IDs, or view semantics. |
| `python -m unittest discover -s tests -p '*standalone.py' -v` | **Passed:** 77 mock-based tests. |
| `python tests/run_standalone_verification.py` | **Passed:** 91 mock/simulation tests. These do not import or exercise the Odoo ORM implementation. |
| `python subscription_management/tests/test_billing_engine.py` | **Blocked:** failed at import because `dateutil` is unavailable. Odoo itself is also unavailable. |
| `python tests/test_end_to_end_integration_12_steps.py` | **Failed at import:** requests `MockSecurityContext`, which is not defined in `tests/test_user_management_standalone.py`. No workflow steps ran. |
| Live Odoo/XML-RPC flow, addon test suite, Docker startup, database/install/upgrade, cron, and browser/UI checks | **Not run:** prerequisites are absent; no live service was started. |

No test result above is evidence that the actual Odoo models work.

## 4. Bugs and errors found

1. **Demo data references undefined plan fields — likely install/upgrade blocker when demo is loaded.** `subscription_management/demo/demo_data.xml:64-80` sets `trial_period_days` and `grace_period_days`. Neither field is defined on `subscription.plan` in `subscription_management/models/subscription_plan.py` (model starts at line 8; its plan fields are defined in the first half of the file). The manifest includes demo data and `odoo.conf` has `without_demo = False`. Odoo demo-data loading should reject these unknown fields. **Suggested fix:** remove the unsupported demo fields or implement them in the existing plan model before loading demo data; then test a clean install with demo enabled.
2. **Plan-only recurring invoice has a required-field failure.** `subscription_management/models/subscription.py:429-436` permits confirming a priced plan with no product lines. `subscription_management/models/subscription_invoice.py:560-563` then creates a plan-fee line with `product_id=False` when there are no subscription lines, while `subscription_management/models/subscription_invoice.py:260-264` defines invoice-line `product_id` as required. Billing will fail for this valid subscription shape and be recorded as a failed billing attempt. **Suggested fix:** provide a valid product for the plan fee or model the fee without requiring a product; cover the no-product subscription case.
3. **Percentage coupon can be deducted twice on recurring invoices.** `subscription_management/models/discount.py:289-324` sets `discount_rate` when applying a percentage coupon. Recurring billing copies that rate onto invoice lines at `subscription_management/models/subscription_invoice.py:560-577`; the discount extension also applies the coupon deduction at `subscription_management/models/discount.py:387-418`. **Suggested fix:** choose one discount application path and add a recurring-invoice total regression test for percentage coupons.
4. **12-step test cannot start.** `tests/test_end_to_end_integration_12_steps.py:61-62` imports `MockSecurityContext`, but that symbol is absent from `tests/test_user_management_standalone.py`; execution stops before any integration assertions. **Suggested fix:** align the test with the existing mock API or supply the intended test helper, then rerun it.
5. **Dashboard date filter is only partially applied.** In `subscription_management/models/dashboard.py:111-124`, date bounds are added to the payment domain. The subscription and invoice aggregations (including outstanding/overdue metrics and monthly invoice breakdown) use domains without those bounds (`:70-109`, `:166-214`). **Suggested fix:** apply the selected period consistently or label metrics as all-time/current-state.
6. **Product/plan eligibility is not enforced.** The product-plan relation is defined in `subscription_management/models/product.py:34-40` and shown in the view, but no validation/use of it was found in subscription line creation or confirmation. **Suggested fix:** validate selected products against the plan when creating/updating subscription lines.

## 5. Backend integration status

The intended path is represented in code: portal customer/partner → product and plan → subscription lifecycle → coupon extension → custom subscription invoice → payment reconciliation → dashboard aggregates. However:

- The only successful end-to-end-style tests are in-memory mocks, not calls through the Odoo registry.
- The new 12-step test fails before execution.
- The demo-data field mismatch may prevent a demo-enabled module install.
- Plan-only invoice creation and percentage-coupon billing have identified defects.
- Payment records reconcile within the custom invoice model; there is no evidence of standard Odoo accounting invoice posting or external gateway processing.

**Integration verdict:** not verified end-to-end in Odoo.

## 6. Odoo environment and run readiness

- Python available: **3.14.2**.
- `odoo`, `dateutil`, `psycopg2`, `lxml`, `pytest`, and the Docker CLI were not available in the checked environment.
- `odoo.conf` and `docker-compose.yml` configure a container-based Odoo/PostgreSQL setup, but Docker is unavailable here.
- Therefore, installation, module registry loading, view validation, ORM behavior, access rules, email, payments, cron, and live database behavior could not be verified.
- Configuration contains development credentials/settings; replace and secure them before any shared or public deployment. Values are intentionally not reproduced here.

**Run-readiness in this environment:** not runnable or runtime-testable.

## 7. Demo preparation checklist (source-based; not runtime-verified)

Do not present these as verified screens or a live working system until the addon is installed and the following actions are exercised in Odoo.

1. **Prepare records:** use one staff/manager account, a customer/partner, one service product, and a monthly plan. Avoid the supplied demo plans until their unsupported fields are addressed.
2. **Product pricing:** create/edit a product with the Odoo brand and compare its displayed base and subscription price. Expected by source: a 560 surcharge over the base before variant extras.
3. **Subscription lifecycle:** create a subscription with a priced plan and a product line meeting minimum quantity; send quotation, confirm, then activate. Verify state and next billing date after each action.
4. **Discount:** use a fixed-amount coupon for any amount demonstration until percentage double deduction is fixed. Confirm eligibility and resulting totals before showing them.
5. **Invoice:** trigger billing only for an active, due subscription that has product lines. Verify generated custom invoice, billing period, total, and billing log.
6. **Payment:** register a partial payment and then the remaining amount using the payment wizard; verify residual and paid state. Describe this as manual payment recording, not Stripe/PayPal processing.
7. **Dashboard/report:** display KPI/report views only after comparing their values with the underlying invoices/payments. Current date filters do not consistently scope all metrics.

**Do not claim as completed:** a live Odoo installation verified by this QA; the 12-step integration; successful demo-data installation; standard accounting invoice posting; online gateway transactions; tested customer email/reset delivery; or fully date-filtered dashboard figures.

## 8. Remaining critical issues

1. Resolve the unsupported demo fields and verify a clean Odoo install with demo enabled.
2. Fix and test plan-only recurring invoice generation.
3. Eliminate percentage-coupon double deduction and test recurring totals.
4. Repair the 12-step test import and make the integration test exercise actual Odoo models if it is intended as an Odoo integration test.
5. Run addon tests and a clean install/upgrade against the target Odoo 17 + PostgreSQL environment.

## 9. Recommended next steps

1. **Before video submission:** have the target Odoo operator verify module installation; first check the demo-field mismatch. Do not rely on this workstation for a live Odoo demo.
2. Demonstrate only flows actually executed in the target environment; if unavailable, label any walkthrough as a mock or source-code demonstration.
3. After installation, execute the lifecycle with a product line, a fixed discount, a manual partial/full payment, and compare dashboard totals against source records.
4. Resolve the billing/discount defects, then run Odoo `TransactionCase` tests and the live XML-RPC flow on a disposable database.
