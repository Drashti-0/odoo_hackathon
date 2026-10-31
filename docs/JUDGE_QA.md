# Judge Q&A

Answers reflect the repository and verification evidence as of 2026-10-31. Do not state that an untested external integration or workflow has passed.

## Product and business

### 1. What problem does Brightloop solve?

It connects subscription products/plans, customer quotations, contract lifecycle, recurring invoice periods, and payment status in Odoo, reducing the need to track these records in separate manual workflows.

### 2. Who uses the application?

Subscription Administrators configure plans and access; Officers/Staff manage customer operations; Portal Customers can access customer-scoped subscription, quotation, plan, invoice, and billing-history pages.

### 3. Why build this inside Odoo?

The implementation reuses Odoo's ORM, PostgreSQL persistence, web client, menus/actions, role groups, chatter/activities, product catalog, and portal framework instead of maintaining a separate application and customer database.

### 4. What is the primary workflow?

Create a subscription-eligible product and plan, issue a quotation to a customer, confirm and activate the contract, generate a subscription-linked invoice for the billing period, and reconcile payment records to show paid/residual state.

### 5. What is innovative about the solution?

The value is the integrated lifecycle-to-billing workflow: one contract holds plan and product terms, scheduled billing creates period-linked invoices, and a uniqueness constraint helps stop duplicate invoices for the same subscription period. It does not claim AI or a new payment network.

## Technical

### 6. Which Odoo version is targeted?

The addon manifest version is `17.0.1.0.0` and the local Docker Compose default image is Odoo `17.0`. Some older repository documents mention Odoo 18, but this submission targets Odoo 17.

### 7. What are the main custom models?

`subscription.plan`, `subscription.subscription`, `subscription.line`, `subscription.invoice`, `subscription.invoice.line`, `subscription.payment`, `subscription.discount`, `subscription.billing.log`, and dashboard models. The module also extends standard product, partner/user, and invoice/payment behavior.

### 8. How is recurring billing performed?

An `ir.cron` record invokes the subscription recurring-billing method daily. The source includes billing-date processing, period duplicate protection, row locks and audit logging. The cron records were active in the inspected database; its real side effects were not executed as part of the final verification.

### 9. How are duplicate invoices addressed?

The invoice model declares a SQL uniqueness constraint over subscription, billing-period start, and billing-period end; the recurring engine also contains locking/savepoint patterns. Native test errors on the populated database mean the full behavior still requires a clean isolated Odoo test run.

### 10. What database is used?

PostgreSQL, operated by Odoo's ORM. The local demo environment uses a PostgreSQL Docker service and an Odoo bind mount for the addon.

### 11. How is portal customer data restricted?

Portal routes require an authenticated user and search for subscriptions/invoices using the logged-in partner or commercial-partner scope. Module record rules also restrict subscription and invoice records. A final authenticated two-customer browser test was not available, so describe this as implementation evidence, not a newly verified end-to-end pass.

### 12. Does `sudo()` in portal routes bypass customer ownership?

The invoice PDF route first resolves the invoice through a customer-scoped lookup, then uses elevated access to render the report. The staff-request routes similarly resolve a customer-owned subscription before creating an activity. The inspected uses are tied to these flows; this was a source review, not a formal independent security certification.

### 13. Is payment processing connected to Stripe or PayPal?

The data model has payment methods labelled Stripe and PayPal and tracks transaction state, but no real provider transaction was performed or verified. Do not describe the current demo as a live payment gateway integration.

### 14. How does a discount work?

The discount model supports fixed/percentage rules and eligibility fields; invoice and subscription extensions apply discounts and track usage. The standalone verification passed, but the complete native ORM integration was not isolated and verified in this final run.

### 15. What happens when a subscription expires?

The declared lifecycle includes both `expired` and `closed`, and the plan has auto-close/grace-period policy. Test expectations disagree over which state an expired contract should reach in some scenarios; the team needs to settle this contract before claiming the expiry behavior is fully verified.

### 16. Are emails sent when an invoice is marked sent?

Not by the reviewed `subscription.invoice.action_send_email()` implementation: it posts a chatter message saying the invoice was sent but does not dispatch an email. Actual email delivery is a known gap.

### 17. Can customers buy a plan from the portal?

Available plan list/detail pages exist, but a self-service purchase/checkout path was not verified. Do not promise plan purchase from the portal unless the team demonstrates the complete supported flow.

### 18. What reports are available?

The addon defines a QWeb invoice report and backend dashboard graph/pivot analytics. A separate financial-report QWeb file mentioned in the integration contract was absent. PDF rendering and download were not tested in this final check.

## Reliability, testing, and delivery

### 19. What testing has passed?

The standalone runner passed 92 tests, and all 16 addon XML files parsed. The module was installed in the inspected local Odoo 17 database and cron records were enabled. These facts do not substitute for the native Odoo end-to-end test suite.

### 20. What did the native Odoo tests report?

A run against the already populated local database reported 14 failures and 6 errors out of 132 tests. Dashboard fixtures saw existing records, portal fixtures collided/reused data, invoice fixture errors occurred, and lifecycle expectations conflicted. It was not a clean isolated test database run.

### 21. Does the demo contain real customer information?

The documented loader creates synthetic `.test` customers and uses stable Odoo external IDs. It does not create fake payment-success records. Demo data should only be loaded into a development database.

### 22. Is the project production-ready?

It is a substantial hackathon prototype, not a production-certified payment/billing deployment. Before production, isolate and fix the native suite, verify portal and invoice rendering, implement actual notification dispatch, validate cron behavior, and integrate any payment provider with its security, compliance, and reconciliation requirements.

### 23. What should judges see in the demo?

The strongest supported story is the linked Odoo workflow: dashboard → product/plan → quotation → subscription and next billing date → linked invoice and its actual payment/residual state. Use an existing synthetic quotation and do not manufacture a successful payment.

### 24. What is the biggest current limitation?

End-to-end verification is incomplete: the native test suite did not pass cleanly, and portal login, PDF output, cron execution side effects, actual email sending, and live payment provider behavior were not verified in the final check.

### 25. What is the next high-value engineering step?

Run the native Odoo suite on an isolated disposable test database, fix fixture isolation and resolve the intended expiry-state contract, then validate the portal with two separate synthetic customers and verify a PDF/cron run without touching production data.
