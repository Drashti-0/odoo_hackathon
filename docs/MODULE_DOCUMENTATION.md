# Module-Wise Technical Documentation
## Brightloop Subscription Management System

> **Evidence note:** This is a technical design/history document. Performance figures and feature descriptions are not a substitute for current runtime proof; in particular, no 5,000-record benchmark was run for this final task. Consult [TESTING_REPORT.md](TESTING_REPORT.md) for measured test evidence and limits.

**Project:** Subscription Management System – Brightloop Software  
**Team:** AuraMinds  
**Target Version:** Odoo 17.0 / 18.0  
**Branch:** `developer-2-operations`  

---

## 1. Module 1: Repository Architecture & Core Integration (Task 1)

### Purpose & Scope
Provides the baseline Odoo application structure, dependency declarations, and integration hooks between team developers as ratified in `INTEGRATION_CONTRACT.md`.

### Features
- Native Odoo 17/18 addon architecture inside `subscription_management`.
- Manifest configuration specifying data loading order: Security $\rightarrow$ Sequences $\rightarrow$ Cron $\rightarrow$ Views $\rightarrow$ Record Rules.
- Abstract extension hooks: `discount_hook.py` and `payment_hook.py`.

### Models & Files
- Manifest: `subscription_management/__manifest__.py`
- Hook Models: `subscription_management/models/discount_hook.py`, `subscription_management/models/payment_hook.py`
- Core Models (Developer 1): `product.py`, `subscription_plan.py`, `subscription.py`, `subscription_invoice.py`, `billing_log.py`

### Test Files
- `tests/run_standalone_verification.py` (Developer 1 core tests 1–14).

---

## 2. Module 2: User Management & Authentication (Task 2)

### Purpose & Scope
Implements role-based access control, secure customer self-service onboarding, enterprise password complexity, and row-level multi-tenant customer isolation.

### Features
- **Public Portal Endpoints**: JSON/HTTP controllers for customer registration, login, and password reset.
- **Strict Email Validation**: RFC 5322 regex validation and case-insensitive duplicate email detection.
- **Password Policy**: Enforces $>8$ characters with mandatory uppercase, lowercase, numerical, and special characters.
- **User Enumeration Defense**: Password reset returns identical success responses regardless of whether the email exists.
- **Row-Level Customer Isolation**: Record rules restrict portal customers to their own contracts, invoices, and payments.

### Models & Important Methods
- `res.users` (Extension in `models/user_management.py`):
  - `register_portal_customer(name, email, password)`
  - `validate_password_complexity(password)`
  - `request_password_reset(email)`
- `subscription.customer.register.wizard`: Staff customer onboarding wizard.
- `portal_auth.py` (`controllers/portal_auth.py`): Web routing endpoints.

### Views & Menus
- User Management Views: `views/user_views.xml` (Wizard form view, action).
- Security Definitions: `security/user_security.xml`.

### Security Rules
- `subscription_portal_rule`: `[('partner_id', '=', user.partner_id.id)]`
- `subscription_invoice_portal_rule`: `[('partner_id', '=', user.partner_id.id)]`

### Relevant Test Files
- Native: `subscription_management/tests/test_user_management.py`
- Standalone: `tests/test_user_management_standalone.py` (17 tests).

---

## 3. Module 3: Discount Management (Task 3)

### Purpose & Scope
Provides an automated promotional discount and coupon engine that seamlessly integrates into subscription pricing and recurring invoice generation without compounding errors.

### Features
- **Discount Types**: Fixed Dollar Amount deductions and Percentage deductions.
- **Eligibility Boundaries**: Minimum purchase threshold, minimum line item quantity, validity date ranges (`start_date`, `end_date`), and global usage limits (`usage_limit`).
- **Clamping Security**: Clamps deduction to prevent negative invoice totals.
- **Scope Options**: Product-specific targeting vs whole-subscription deductions.
- **Automated Billing Integration**: Generated recurring invoices automatically inherit active discounts from their subscription.
- **Idempotency Defense**: `discount_usage_recorded` flag prevents billing cron retries or invoice saves from double-incrementing usage counts.

### Models & Important Methods
- `subscription.discount` (New model in `models/discount.py`):
  - `check_eligibility(check_date, subtotal, total_quantity, product_ids)`
  - `calculate_discount_amount(subtotal, matching_subtotal)`
- `subscription.subscription` (Extension in `models/discount.py`):
  - `_compute_amounts()`, `_compute_discount_amount()`, `action_apply_discount()`
- `subscription.invoice` (Extension in `models/discount.py`):
  - `apply_discount_code(code)`

### Views & Menus
- Discount Views: `views/discount_views.xml` (Tree, Form, Search view with Expired/Archived ribbons).
- Menu Item: **Products & Plans** $\rightarrow$ **Discounts & Coupons**.

### Security Rules
- ACL: Admin has full CRUD; Staff has Read/Create/Write; Customers have zero access.
- Server-side Python checks: Modify or unlink operations by non-admins raise `AccessError`.

### Relevant Test Files
- Native: `subscription_management/tests/test_discount_management.py`
- Standalone: `tests/test_discount_management_standalone.py` (28 tests).

---

## 4. Module 4: Payment Management (Task 4)

### Purpose & Scope
Records, manages, and reconciles payments against recurring subscription invoices, tracking partial settlements and automatic transitions to Paid status.

### Features
- **7 Payment Methods**: Cash/Cheque, Bank Wire Transfer, UPI, Credit/Debit Card, Stripe Gateway, PayPal Gateway, Other.
- **Multi-Payment Reconciliation**: Partial payments accumulate across multiple dates; updates `amount_residual` and `amount_paid`.
- **Automatic State Machine**:
  - `amount_residual == 0.0`: Transitions `payment_state = 'paid'` and invoice `state = 'paid'`.
  - `0.0 < amount_paid < amount_total`: Transitions `payment_state = 'partial'` and retains `state = 'confirmed'`.
  - `amount_paid == 0.0`: `payment_state = 'not_paid'`.
- **Idempotency & Anti-Overpayment**: Re-confirming settled payments is a safe no-op. Overpayments exceeding the invoice residual are rejected.
- **Overdue Invoicing**: Automatically identifies unpaid invoices past `due_date`.
- **Payment Registration Wizard**: Interactive modal wizard on invoice header.

### Models & Important Methods
- `subscription.payment` (Extension in `models/payment.py`):
  - `action_confirm_payment()`, `action_fail_payment(reason)`
  - `@api.constrains('amount')`, `@api.constrains('amount', 'invoice_id', 'state')`
- `subscription.invoice` (Extension in `models/payment.py`):
  - `_compute_payment_totals()`, `_compute_overdue()`, `action_register_payment()`
- `subscription.payment.register.wizard`: Interactive transient payment dialog.

### Views & Menus
- Views: `views/payment_views.xml` (Payment tree, form, search; wizard form; inherited invoice form adding Payments tab, overdue ribbon, and residual labels).
- Menu Item: **Billing & Invoices** $\rightarrow$ **Payments & Receipts**.

### Security Rules
- `subscription_payment_portal_rule`: `[('partner_id', '=', user.partner_id.id)]` (Customers only view own payments).
- Action protection: Only Staff and Admin can execute `action_confirm_payment` or `action_fail_payment`.

### Relevant Test Files
- Native: `subscription_management/tests/test_payment_management.py`
- Standalone: `tests/test_payment_management_standalone.py` (16 tests).

---

## 5. Module 5: Dashboard & Financial Reports (Task 5)

### Purpose & Scope
Provides real-time executive business intelligence, collection aging, and visual analytics via database-level SQL aggregation.

### Features
- **5 Core Mandatory KPIs**:
  1. Active Subscriptions count (`state == 'active'`).
  2. Revenue Received (exact sum of `state == 'success'` payments).
  3. Outstanding Amount (sum of `amount_residual` on confirmed invoices).
  4. Overdue Invoices (count and amount where `due_date < today` and `amount_residual > 0`).
  5. Total Confirmed Payments (count and monetary volume).
- **Run-Rate Metrics**: Live aggregation of MRR and ARR across active contracts.
- **Interactive Console (`subscription.dashboard.console`)**: Form view with KPI cards, action drill-downs, and dynamic filter controls.
- **Dynamic Filters**: Period (`today`, `this_week`, `this_month`, `this_year`, `custom`, `all`), Customer, Subscription Status, Payment Method.
- **Visual Analytics**: Native Odoo Graph (pie, bar) and Pivot views for subscription distribution, monthly revenue trends, receivables aging, and payment methods.
- **Performance**: Uses Odoo ORM `read_group()` for database-level aggregation. An older document quoted a 5,000-record runtime benchmark; that benchmark was not reproduced during final verification and must not be presented as a verified performance result.

### Models & Important Methods
- `subscription.dashboard` (AbstractModel in `models/dashboard.py`):
  - `get_dashboard_metrics()`, `_check_dashboard_access()`, `_parse_date_range()`
- `subscription.dashboard.console` (TransientModel in `models/dashboard.py`):
  - `_compute_dashboard_metrics()`
  - Drill-downs: `action_view_active_subscriptions()`, `action_view_received_payments()`, `action_view_outstanding_invoices()`, `action_view_overdue_invoices()`

### Views & Menus
- Views: `views/dashboard_views.xml` (Console form, graph views, pivot views, window actions).
- Primary Menu: **Dashboard** (Sequence 1 under `menu_subscription_root`).
- Submenu: **Reporting** $\rightarrow$ Dashboard Console, Revenue & Payments, Invoices & Receivables, Subscription MRR/ARR.

### Security Rules
- Server-side access check in `_check_dashboard_access()` raises `AccessError` if called by portal users.
- ACL: Staff and Admin have access; Portal Customers omitted (zero access).

### Relevant Test Files
- Native: `subscription_management/tests/test_dashboard_reports.py`
- Standalone: `tests/test_dashboard_reports_standalone.py` (16 tests including 5,000-record benchmark).
