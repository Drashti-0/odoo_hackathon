# Final Hackathon Demonstration

**Target duration:** 6 minutes  
**Environment:** Odoo 17 local development database with synthetic demo records already loaded; one authenticated internal Subscription Administrator or Officer account. Do not use production records.

## What we are solving

Software companies sell recurring services, but managing products, plans, contracts, renewals, billing periods, invoices, and customer access across disconnected workflows creates avoidable manual work and makes receivables harder to track. Brightloop brings these subscription operations into Odoo and connects the contract to its generated billing records.

## 6-minute run of show

### 0:00–0:35 — Set the context

Say: “Brightloop is an Odoo 17 subscription-management addon. The central record is a customer contract: it points to a plan and product lines, moves through a controlled lifecycle, and links recurring invoices to billing periods. The dashboard and portal are views over Odoo data, not a separate static demo.”

Start at `http://localhost:8069/web` on the Brightloop Subscriptions dashboard. Identify the data as the current local demo database, not production.

### 0:35–1:20 — Show live operational visibility

Point out the dashboard's database-backed customer/product/plan/subscription/invoice indicators, MRR/ARR fields, receivable/revenue metrics, filters, and chart/report navigation. Avoid reading out a “headline” financial number unless its source records and the current dashboard filter are understood. Existing local test/demo data may affect global totals.

Explain that “revenue received” is based on successful payment records; an unpaid invoice belongs in outstanding/residual figures, not settled revenue.

### 1:20–2:05 — Show the catalog and recurring terms

Open **Products & Plans → Subscription Products** and choose a synthetic demo service. Show its subscription eligibility and configured price/variant fields. Open **Subscription Plans** and compare the monthly, quarterly, and yearly demo records: price, billing interval/count, and policy fields.

Do not claim the portal supports checkout/plan purchase; the observed portal plan page is a catalogue/detail view, and purchase flow was not verified.

### 2:05–3:10 — Follow a quotation into a contract

Open **Subscriptions → Quotations** and select a synthetic customer quotation. Show customer, plan, product lines, validity/terms, and calculated total. Confirm it through the real form action, then activate it if this quotation is intended for the live demonstration.

Use an existing pending quotation if possible. Avoid creating duplicate records during the presentation. If you need a new quotation, prepare it in advance using a synthetic `.test` customer.

### 3:10–4:05 — Verify subscription lifecycle and billing schedule

Open the resulting record under **Contracts & Subscriptions**. Point to state, plan, start/expiry dates, next billing date, recurring amount, and invoice smart link/history. Explain the current state label and avoid presenting the expiry `closed`/`expired` semantics as fully regression-verified.

### 4:05–5:00 — Inspect a real linked invoice

Open **Billing & Invoices → Recurring Invoices**. Verify customer, source subscription, billing period, invoice/document state, payment state, amount paid, and residual. Explain that the synthetic loader's invoice is unpaid and no fake payment-success record is created.

The QWeb invoice report action exists, but PDF download was not exercised in the final verification. If the evaluator expects a PDF, only demonstrate it after confirming the report renders in the current environment.

### 5:00–5:40 — Explain payment and discount controls

Show payment transactions linked to invoices and the available discount rule fields or an existing safe demo discount. Clarify that staff-recorded transaction states and payment-method labels are not proof of a live Stripe/PayPal/UPI gateway. Do not mark a payment successful as a presentation prop. Do not use the invoice “send email” action to claim an email was sent; the reviewed method only posts a chatter message.

### 5:40–6:00 — Close with customer isolation and limitations

Describe the customer portal: authenticated routes filter subscriptions/invoices to the user's partner/commercial-partner records; renewal/cancellation controls submit staff-review requests. The portal was not authenticated and visually tested in this final verification; do not claim a live customer walkthrough. End with the concrete next steps: isolated native test run, portal/PDF validation, real mail-template dispatch, and provider sandbox integration if in scope.

## Why the solution matters

- Subscription terms and recurring billing records stay connected to the Odoo customer and product.
- Billing dates and linked invoices improve staff visibility into upcoming work and receivables.
- Billing-period uniqueness and the engine's lock/savepoint design aim to prevent duplicate work during scheduled runs.
- Role-scoped Odoo access and partner-scoped portal lookups support customer data separation.
- Reusing Odoo's ORM, menus, groups, chatter, activities, and portal framework avoids a parallel standalone application.

These are implementation capabilities and design benefits; this demo does not claim measured time savings or production-scale performance.

## Strongest demonstrated features

1. A live, database-backed dashboard inside the Odoo backend.
2. The connected plan → quotation → subscription → invoice data model.
3. Subscription lifecycle state and next-billing fields.
4. Recurring billing configuration and billing audit model.
5. Real unpaid invoice/residual semantics and explicit separation from payment success.
6. Synthetic, external-ID-based demo data loading for repeatable local setup.

## What makes the project different

The project combines a configurable subscription lifecycle, recurring billing and period-level invoice protection with Odoo-native role-based UI and a customer portal. Its defensible differentiator is the connected workflow and traceability in the ERP—not a claim of AI, automatic gateway settlement, or a separately implemented payment processor.

## Technical architecture in one minute

- Odoo 17 addon: `subscription_management`.
- Python ORM models extend product/customer functionality and define plans, subscriptions, invoice lines, payments, discounts, logs, dashboard records, and onboarding wizards.
- PostgreSQL is the persistence layer.
- XML defines backend views, actions, menus, portal QWeb templates, security records, cron jobs, sequences, and invoice report.
- Python HTTP controllers extend the Odoo portal; portal routes use the authenticated user and customer-scoped record searches.
- Docker Compose runs Odoo and PostgreSQL. The local Compose file bind-mounts the addon directory into `/mnt/extra-addons/subscription_management`.

## Demo data and preparation checklist

- Use `brightloop_test_db` only if that local database is available; otherwise create a development database and install the addon.
- Load demo data with the command in [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md); it creates synthetic `.test` customers, catalog, plans, quotations, an active subscription, and an unpaid invoice through Odoo ORM.
- Check that the dashboard is the expected action and that the local app is responsive.
- Prepare an existing quotation rather than creating duplicate live demo records.
- Prepare distinct internal and portal accounts. Do not disclose passwords on screen or in submission documents.
- If showing customer scope, use two synthetic customers and verify the second user's records are not accessible before the event.
- Do not trigger cron against production data.
- Keep “actual email”, “actual provider payment”, and “PDF verified” claims off the script unless separately verified.

## Likely evaluator follow-up

Use [JUDGE_QA.md](JUDGE_QA.md) for concise technical and business answers. If asked about current test limitations, state plainly that the standalone suite passed 93 tests, while a previously recorded native run on the populated database had 14 failures and 6 errors out of 132 and is not a clean isolated result.

## Known limitations to disclose

- Native test run is not a clean pass; test-data contamination and genuine state/fixture mismatches need owner triage in an isolated database.
- Portal customer login and cross-customer access were not verified in the final browser run.
- QWeb invoice PDF output, cron side effects, actual notification delivery, and provider gateway calls were not exercised in this final verification.
- Invoice action named as email/send does not dispatch mail in the reviewed implementation.
- No separate financial-report QWeb file was found despite its listing in the integration contract.
- Contract documentation and code/tests have a lifecycle expiry naming disagreement (`expired` vs `closed`).
- No standalone original hackathon problem statement was found in the repository; the problem framing here is derived from the project documentation and implementation.
