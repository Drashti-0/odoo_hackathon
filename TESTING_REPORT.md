# Brightloop Subscription Management — Current Verification

**Audit date:** 2026-10-31  
**Branch:** `developer-2-operations`  
**Environment:** Windows; Python 3.14; Node.js available; Docker and Odoo unavailable.

## Status summary

- **COMPLETED AND VERIFIED:** Standalone Python test doubles, static syntax/structure checks, and browser behavior described below.
- **COMPLETED BUT NOT LIVE-TESTED:** Odoo addon source, routes, record rules, models, scheduled-action definitions, and Docker configuration were inspected.
- **PENDING USER ACTION:** Start Docker, create a database, install the addon, and run Odoo-native tests.
- **NOT IMPLEMENTED:** Real payment gateway processing and connection between `demo_portal/` and Odoo.

## Tests actually run

| Check | Result |
|---|---|
| `python tests/run_standalone_verification.py` | **PASS** — 93 tests, 0 failures/errors (0.053 s). These exercise standalone test doubles, not the Odoo ORM. |
| `python -m unittest discover -s tests -p 'test_*_standalone.py' -v` | **PASS** — 78 tests, 0 failures/errors (0.053 s). Mock/standalone tests only. |
| `python tests/test_end_to_end_integration_12_steps.py` | **PASS** — 1 standalone in-memory workflow test; its printed 12 steps are not live Odoo integration. |
| Python AST parse | **PASS** — all 42 repository `.py` files parsed. This does not import or execute the addon. |
| XML parse | **PASS** — all 18 repository XML files are well-formed. |
| Manifest paths/assets | **PASS** — all 19 manifest data/demo references and 4 declared assets exist. |
| Static model/action/ACL checks | **PASS** — declared action models and menu action references resolved; ACL CSV has 31 non-empty data rows with consistent columns. This is not equivalent to Odoo view validation. |
| Frontend JavaScript | **PASS** — `node --check demo_portal\assets\app.js`; both inline scripts parsed. |
| Frontend references | **PASS** — no duplicate HTML IDs and the local JavaScript reference exists. |
| `git diff --check` | **PASS** after final edits. |

## Browser checks actually performed

The existing `demo_portal/index.html` was opened in the integrated browser. The following flows passed:

- Sign-in appeared first; empty login validation, admin login, logout, and refresh returning to sign-in.
- Signup rejected a password mismatch, accepted a valid demo registration, and allowed same-page sign-in.
- Admin navigation opened all 13 sidebar screens. Customer navigation opened the customer dashboard, portal, subscription list, and invoice list; customer-visible records were scoped to Alice's demo customer ID.
- Dashboard charts rendered. No browser JavaScript/page errors were observed; Tailwind CDN emitted its production-use warning.
- A new demo subscription using `LAUNCH20` calculated `$150 - 20% = $120`; an invalid coupon created no subscription.
- Pause/resume worked; invoice generation used the discounted amount; a second invoice for the same period was blocked.
- An overpayment did not change invoice/payment data; a valid $120 simulated payment reconciled to the demo invoice.
- At a narrow mobile viewport, the first check found 6 px of horizontal overflow from `100vw` sizing with a vertical scrollbar. The mobile CSS was corrected; repeat checks on login and customer portal showed no page-level horizontal overflow.
- Browser test mutations were restored from the saved local demo state after each flow.

These are browser-local simulation results, not Odoo integration results. Not every control on every screen was exhaustively tested.

An early signup test expected a dedicated success element, but the existing UI correctly returns to sign-in and shows a toast; the test was adjusted to assert that behavior. The duplicate-invoice flow keeps the subscriptions screen open when it rejects a duplicate, so the test navigated to invoices before checking payment.

## Odoo and deployment checks

- **Odoo TransactionCase tests:** Not run. The current Python environment cannot import `odoo`; no Odoo server/runtime was available.
- **Docker Compose validation/startup:** Not run. The `docker` command is unavailable. No container was started and no database was created.
- **Live portal, access rules, cron, accounting, and installation:** Not verified against Odoo 17/PostgreSQL.
- `.env` is ignored by Git and `.env.example` contains blank required passwords. Compose maps Odoo to loopback, publishes no PostgreSQL port, uses persistent volumes, and waits for the database health check. These properties were inspected statically only.
- An older `COPILOT_QA_REPORT.md` listed defects that current source inspection disproved: the plan trial/grace fields are defined, invoice-line products are optional, product/plan eligibility is checked, percentage coupons zero the generic subscription rate and are inherited by recurring invoices, and the 12-step standalone test passes. That report is marked historical; the Odoo-specific assertions remain unverified without a live database.

## Known limitations and next steps

1. `demo_portal/` uses local browser storage and simulated authentication; it is not connected to Odoo. Its role-based filtering is not a security boundary.
2. The addon defines custom `subscription.invoice` records. Do not describe them as posted `account.move` accounting invoices without verifying/implementing that integration.
3. Payment methods are labels for manually recorded payments. Stripe, PayPal, card, bank, and UPI services are not connected.
4. Install Docker Desktop, copy `.env.example` to `.env`, set unique local passwords, then run `docker compose up -d`.
5. Create a test database at `http://localhost:8069/web/database/manager`, update the Apps list, and install **Brightloop Subscription Management**.
6. Run the addon TransactionCase suite against a disposable Odoo 17 test database before claiming live backend readiness.
7. Open `demo_portal/index.html` for the standalone demo. Internet access is needed for its CDN-hosted styles/icons/charts.
