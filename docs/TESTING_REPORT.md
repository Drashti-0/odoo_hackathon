# Testing Report

**Evidence snapshot:** 2026-10-31  
**Project:** Brightloop Subscription Management, Odoo 17

## Results

| Check | Result | Evidence / qualification |
|---|---|---|
| Standalone verification suite | **PASS** | `python3 tests/run_standalone_verification.py -v` completed with 92 tests passed (observed during the audit). |
| Addon XML well-formedness | **PASS** | All 16 `subscription_management/**/*.xml` files parsed successfully. |
| Odoo module registration | **PASS** | `subscription_management` was reported installed in `brightloop_test_db`. |
| Scheduled action registration | **PASS** | The recurring billing, expiry monitor, and upcoming billing notification actions were present and enabled in the inspected database. Their jobs were not triggered in this documentation verification. |
| Runtime binding | **PASS** | Docker Compose maps the repository addon directory to `/mnt/extra-addons/subscription_management`. |
| Local browser dashboard | **PASS, LIMITED** | Reopened the authenticated Odoo dashboard at `http://127.0.0.1:8069/web#action=304&menu_id=197&cids=1`. The page showed KPI/filter/chart content with values read from the live database; a screenshot was rendered in the browser tool. A reload produced no browser console errors or page errors. This verifies dashboard rendering only, not the correctness of every aggregate. |
| Admin dashboard/menu presentation | **PASS, LIMITED** | The visible admin page showed Brightloop navigation for Dashboard, Subscriptions, Billing & Invoices, Reporting, Products & Plans, and Configuration. Other menu actions were not individually opened in this final check. |
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
python3 tests/run_standalone_verification.py -v
```

XML parsing was performed over all addon XML files. Database state was read from the local Odoo/PostgreSQL containers. No records were intentionally modified for this documentation report. A module upgrade, full clean-database test installation, PDF render, cron job, or payment gateway call was not run.

During the final browser check, `pageerror` and browser console-error listeners were attached, the existing authenticated dashboard page was reloaded, and no errors were observed during that reload. Odoo container logs filtered for `ERROR`, `CRITICAL`, and `Traceback` over the preceding 15 minutes returned no matches. This is a bounded check, not a guarantee of error-free operation.

## Evidence image

A screenshot of the live admin dashboard was displayed by the integrated browser tool during inspection and is attached in the task conversation. The browser's file-export attempt saved only the Odoo form toolbar, not the dashboard. The repository also contains a pre-existing tracked image at `screenshots/admin-dashboard.png`, which likewise shows only the toolbar and is not valid dashboard evidence. No valid dashboard screenshot file is included in this delivery; the tool-rendered image is the only actual screenshot evidence.
