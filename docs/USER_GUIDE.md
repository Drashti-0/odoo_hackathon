# User Guide

## Sign in

Use the Odoo URL and user account configured by the local administrator. Internal users work in `/web`; portal customers sign in and open `/my`. A portal customer must be linked to the correct Odoo contact and must not be assigned internal subscription staff/administrator groups.

## Administrator

Subscription Administrators can manage plans, catalog configuration, access to the subscription app, and scheduled actions.

1. Open **Brightloop Subscriptions** in the Odoo app switcher.
2. Use **Products & Plans** to maintain subscription products, variants, plans, and quotation templates.
3. Use **Configuration** for administrator-only settings shown by the installed module.
4. Review the dashboard and reports through **Dashboard** and **Reporting**.
5. To inspect scheduled jobs, open Odoo **Settings → Technical → Automation → Scheduled Actions** with an administrator account. The addon defines:
   - Subscription: Intelligent Automated Recurring Billing Engine
   - Subscription: Contract Expiry & Auto-Close Monitor
   - Subscription: Upcoming Billing Notifications
6. Do not trigger a billing job against real customer data as a demo action. Use a development database and synthetic customer records.

## Officer / Staff

### Product and plan setup

- Create a subscription product using the product form and mark it as a subscription product.
- Define the plan's price, billing unit and interval count (for example, three months), availability dates, and renewal/pause/closure policies.
- Check currency and product-plan compatibility before offering the plan.

### Quotation to subscription

1. Navigate to **Subscriptions → Quotations**.
2. Create a quotation for a customer, choose the plan, and add product lines.
3. Review quote validity, terms, quantities, taxes, and totals.
4. Use the supported confirmation action to progress the quotation; use activation when the business workflow calls for it.
5. Open **Subscriptions → Contracts & Subscriptions** to inspect state, next billing date, recurring amount, and invoice links.

The model state vocabulary includes draft, quotation, confirmed, active, paused, closed, and expired. Some lifecycle expectations are currently inconsistent between native tests and implementation; see the testing report before presenting expiry behavior as fully validated.

### Billing and payments

- Use **Billing & Invoices → Recurring Invoices** to inspect generated invoices, billing periods, customer, document state, payment state, totals, paid amount, and residual.
- The invoice report is the supported PDF report. PDF rendering was not verified in the final submission check.
- Payment records are linked to an invoice. The module records transaction status and payment method; no live payment-provider transaction was demonstrated.
- The invoice action labelled as email/send currently posts a chatter message and is not evidence that an email was sent. Do not use it to claim email delivery.

### Dashboard and reports

The dashboard console includes database-backed filters and KPIs for subscriptions, invoices, payment collection, receivables, and recurring-revenue metrics. It is an internal view and is protected from portal access. Amounts depend on the selected company/database and are not static demo figures.

## Portal Customer

After signing in, use `/my` to view portal home and navigate to:

- **My Subscriptions**: subscription records belonging to the logged-in contact or its commercial partner.
- **My Quotations**: draft/quotation records in the same customer scope.
- **Available Plans**: plans considered available by the portal controller.
- **My Invoices** and **Billing History**: customer-scoped invoice/payment information.
- Subscription and invoice detail pages: records are looked up with a customer ownership condition; unauthorized/missing records return not found.
- Invoice PDF: the portal controller has a guarded report route, but actual authenticated PDF delivery has not been verified in this submission.

Portal cancellation and renewal controls submit requests for staff review; they do not directly cancel or renew a contract. Customers must not be given internal financial dashboard access.

## Local demo walkthrough

Use only a development database with synthetic demo data:

1. Open **Products & Plans → Subscription Products**.
2. Open **Products & Plans → Subscription Plans**.
3. Open an existing quotation and inspect the customer, plan, and lines.
4. Confirm and activate through the actual form actions.
5. Verify the resulting subscription and next billing date.
6. Inspect the linked invoice under **Billing & Invoices → Recurring Invoices**.
7. If a valid synthetic portal user exists, separately verify its `/my` pages and confirm it cannot access another customer's record.

The demo loader does not create successful payment records. It uses synthetic `.test` identities. See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for loading instructions.
