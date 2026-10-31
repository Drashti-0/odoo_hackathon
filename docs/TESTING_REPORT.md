# Testing Report

**Evidence snapshot:** 2026-10-31  
**Project:** Brightloop Subscription Management, Odoo 17

## Results

| Check | Result | Evidence / qualification |
|---|---|---|
| Standalone verification suite | **PASS** | `python3 tests/run_standalone_verification.py -q` completed with 93 tests passed during the final mission. |
| Addon XML well-formedness | **PASS** | All 16 `subscription_management/**/*.xml` files parsed successfully. |
| Odoo module registration | **PASS** | `subscription_management` was reported installed in `brightloop_test_db`. |
| Scheduled action registration | **PASS** | The recurring billing, expiry monitor, and upcoming billing notification actions were present and enabled in the inspected database. Their jobs were not triggered in this documentation verification. |
| Runtime binding and startup | **PASS** | Reconciled the Odoo 17 service with Compose after finding the running container was bound to all interfaces and the configured `--admin-passwd` CLI argument caused a restart loop. Odoo now runs with port 8069 bound to `127.0.0.1`; HTTP `/web` responds with a login redirect. The Odoo and PostgreSQL containers were recreated without deleting volumes. The module remains installed and database counts remain 65 subscriptions, 40 invoices, and 25 payments. |
| Local dashboard and portal-plan requests | **FAIL** | The dashboard compute path raised `NameError: name 'inv_domain' is not defined` in `subscription_management/models/dashboard.py` during monthly invoice aggregation. A subsequent plan-page request also raised PostgreSQL `UndefinedColumn` for `subscription_plan.trial_period_days`, showing the installed database schema is behind the mounted addon source. The browser capture after restart was blank; a valid current dashboard screenshot is unavailable. The dashboard is Developer 2-owned; no owner authorization to edit it was received. No module upgrade was run because it would alter the shared database schema. |
| Admin dashboard/menu presentation | **PASS, LIMITED** | Brightloop navigation for Dashboard, Subscriptions, Billing & Invoices, Reporting, Products & Plans, and Configuration was visible in the earlier authenticated browser session. It was not revalidated after the runtime restart. |
| Portal authentication/page screenshots | **BLOCKED / NOT TESTED** | Anonymous `/my` and `/my/plans/64` requests redirected to login. The already-shared `/my/plans/64` browser tab displayed a 404. No authorized synthetic portal login was available for a customer-specific visual or cross-customer test. |
| Product, plan, quotation, invoice, payment/report page screenshots | **NOT TESTED** | The submission capture did not independently verify each of these pages in the browser. |
| Native Odoo tests | **FAIL / INCONCLUSIVE ON POPULATED DB** | A recorded run reported 132 tests, 14 failures, and 6 errors on the already-populated `brightloop_test_db`. It is not a clean isolated database run. |
| PDF report rendering/download | **NOT TESTED** | QWeb report action and guarded portal route exist in code; actual PDF output was not generated as part of the final documentation task. |
| Email sending | **FAIL for delivery claim** | Reviewed invoice `action_send_email()` only posts chatter text; actual mail dispatch is not implemented by that method. |
| Live payment provider | **NOT TESTED** | The payment transaction model and payment methods exist; a real external provider transaction was not performed. |
| Cron execution | **NOT TESTED** | Jobs exist and were enabled, but no controlled billing/expiry/notification execution was performed for this report. |

## Native test failure details previously observed

The full run against the shared, populated database had **14 failures and 6 errors**. Findings included:

- Dashboard assertions expecting small isolated fixture totals while existing records contributed to global aggregates.
- Existing portal-test records causing duplicate-email/unique-key setup conflicts; the test class includes a database commit.
- Conflicting assertions for subscription expiry state (`expired` versus `closed`).
- Invoice test errors for missing subscription links and duplicate subscription-period invoices.
- A concurrent uncommitted edit to `subscription_management/tests/test_subscription_portal.py` was observed during the previous audit. It was left untouched. The full suite was not rerun after that concurrent edit.

Because the database was not clean and was not reset, the result must not be presented as a clean-baseline product regression result. The defects and test-isolation risks need triage in an isolated test database by the owners of the core test files.

## Commands

Standalone tests were run using:

```bash
python3 tests/run_standalone_verification.py -q
```

XML parsing was performed over all addon XML files. Database state was read from the local Odoo/PostgreSQL containers. No database records were intentionally modified; Odoo and PostgreSQL containers were recreated, and the named database volume remained intact. A module upgrade, full clean-database test installation, PDF render, cron job, or payment gateway call was not run.

The dashboard RPC path emitted the `inv_domain` `NameError`; later browser requests emitted the `UndefinedColumn` error for `subscription_plan.trial_period_days` and a QWeb exception. These indicate live app/database errors, not a clean runtime. A module upgrade was not run because it would alter the shared database schema and no such change was authorized.

## Evidence image

A browser screenshot was captured after the runtime restart, but it showed a blank viewport and is not valid dashboard evidence. The browser's file-export attempt saved only the Odoo form toolbar, not the dashboard. The pre-existing tracked image at `screenshots/admin-dashboard.png` also shows only the toolbar. No valid current dashboard screenshot file is included in this delivery.
