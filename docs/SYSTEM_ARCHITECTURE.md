# System Architecture Documentation
## Brightloop Subscription Management System

**Project:** Subscription Management System – Brightloop Software  
**Team:** AuraMinds  
**Target Version:** Odoo 17.0 / 18.0  
**Branch:** `developer-2-operations`  

---

## 1. High-Level Architectural Overview

The **Brightloop Subscription Management System** is built natively on Odoo's multi-tier MVC architecture. It integrates with standard Odoo base modules (`base`, `mail`, `product`) and organizes business logic into modular components:

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Web Layer"]
        Browser["Odoo Web Client (Browser)"]
        Portal["Customer Self-Service Portal"]
    end

    subgraph ControllerLayer["Controllers & Security"]
        PortalAuth["portal_auth.py (HTTP/JSON Endpoints)"]
        ACL["ir.model.access.csv (Model Access Lists)"]
        Rules["ir.rule (Multi-Tenant Record Rules)"]
    end

    subgraph ServiceLayer["Business Logic & Workflow Engine"]
        SubLifecycle["Subscription Lifecycle Engine"]
        BillingCron["Automated Billing Cron Engine"]
        DiscountEngine["Discount & Coupon Rules"]
        PaymentReconciliation["Payment Settlement & Reconciliation"]
        DashboardEngine["Dashboard & Financial Analytics Engine"]
    end

    subgraph ModelLayer["Odoo ORM Models"]
        M_Plan["subscription.plan"]
        M_Sub["subscription.subscription"]
        M_Line["subscription.line"]
        M_Inv["subscription.invoice"]
        M_Pay["subscription.payment"]
        M_Disc["subscription.discount"]
        M_Log["subscription.billing.log"]
    end

    subgraph DatabaseLayer["Data Persistence"]
        PostgreSQL[("PostgreSQL Database")]
    end

    Browser --> ACL
    Portal --> PortalAuth
    PortalAuth --> Rules
    ACL --> ServiceLayer
    Rules --> ModelLayer
    ServiceLayer --> ModelLayer
    ModelLayer --> PostgreSQL
```

---

## 2. Model Relationships (Entity-Relationship Diagram)

The following ER diagram maps the actual data models and foreign-key relationships implemented across Developer 1's core models and Developer 2's extensions:

```mermaid
erDiagram
    RES_PARTNER ||--o{ SUBSCRIPTION_SUBSCRIPTION : "places"
    RES_PARTNER ||--o{ SUBSCRIPTION_INVOICE : "billed"
    RES_PARTNER ||--o{ SUBSCRIPTION_PAYMENT : "pays"

    SUBSCRIPTION_PLAN ||--o{ SUBSCRIPTION_SUBSCRIPTION : "governs"
    PRODUCT_PRODUCT ||--o{ SUBSCRIPTION_LINE : "referenced"

    SUBSCRIPTION_SUBSCRIPTION ||--|{ SUBSCRIPTION_LINE : "contains"
    SUBSCRIPTION_SUBSCRIPTION ||--o{ SUBSCRIPTION_INVOICE : "generates"
    SUBSCRIPTION_SUBSCRIPTION }o--o| SUBSCRIPTION_DISCOUNT : "applies"

    SUBSCRIPTION_INVOICE ||--|{ SUBSCRIPTION_INVOICE_LINE : "contains"
    SUBSCRIPTION_INVOICE ||--o{ SUBSCRIPTION_PAYMENT : "reconciles"
    SUBSCRIPTION_INVOICE }o--o| SUBSCRIPTION_DISCOUNT : "inherits"

    SUBSCRIPTION_SUBSCRIPTION ||--o{ SUBSCRIPTION_BILLING_LOG : "audited"
```

---

## 3. Subscription & Invoicing Workflow Sequence

The lifecycle of an enterprise contract from initial quotation to full payment settlement:

```mermaid
sequenceDiagram
    autonumber
    actor Staff as Subscription Staff
    participant Sub as subscription.subscription
    participant Engine as Recurring Billing Engine
    participant Inv as subscription.invoice
    participant Pay as subscription.payment
    participant Dash as subscription.dashboard

    Staff->>Sub: Create Quotation (Plan + Lines)
    Staff->>Sub: action_confirm() (assigns SUB-XXXXX)
    Staff->>Sub: action_activate() (State=active, sets next_billing_date)
    
    Note over Sub,Engine: Period passes or manual trigger
    Engine->>Sub: _process_recurring_billing_catchup()
    Sub->>Inv: Create Confirmed Invoice with Discount
    
    Staff->>Pay: Register Partial Payment ($150)
    Pay->>Inv: action_confirm_payment()
    Inv->>Inv: payment_state='partial', residual=$250
    
    Staff->>Pay: Register Final Settlement ($250)
    Pay->>Inv: action_confirm_payment()
    Inv->>Inv: payment_state='paid', state='paid', residual=$0
    
    Staff->>Dash: Open Dashboard Console
    Dash->>Dash: Database read_group() SQL Aggregation
    Dash-->>Staff: Live Revenue Received, Active Count & Overdue Receivables
```

---

## 4. Developer 2 Model Extensions & Hooks

Developer 2 extended Developer 1's core architecture exclusively through clean Odoo class inheritance (`_inherit`), strictly avoiding modifications to core source files:

1. **`subscription.subscription` Extension** (in [`models/discount.py`](../subscription_management/models/discount.py)):
   - Hooks into `_compute_amounts()` to calculate promotional discounts.
   - Adds fields: `discount_id`, `discount_code`, `discount_rate`, `amount_discount`.
2. **`subscription.invoice` Extension** (in [`models/discount.py`](../subscription_management/models/discount.py) & [`models/payment.py`](../subscription_management/models/payment.py)):
   - Adds fields: `discount_id`, `discount_amount`, `discount_usage_recorded`.
   - Adds payment reconciliation fields: `payment_ids`, `amount_paid`, `amount_residual`, `is_overdue`, `days_overdue`.
   - Extends methods: `_compute_payment_totals()`, `_compute_overdue()`, `action_register_payment()`.
3. **`subscription.payment` Extension** (in [`models/payment.py`](../subscription_management/models/payment.py)):
   - Inherits `subscription.payment` skeleton from Developer 1's `payment_hook.py`.
   - Adds 7 payment methods, memo notes, and boundary constrains.
   - Implements idempotent settlement: `action_confirm_payment()`, `action_fail_payment()`.
4. **`subscription.dashboard` Engine** (in [`models/dashboard.py`](../subscription_management/models/dashboard.py)):
   - Abstract analytics engine querying PostgreSQL directly via `read_group()`.
   - Transient model `subscription.dashboard.console` for interactive UI cards, dynamic date/customer filtering, and drill-downs.

---

## 5. Security & Multi-Tenant Data Flow

```mermaid
flowchart LR
    subgraph RequestSource["Incoming Request"]
        Cust["Portal Customer Request"]
        Internal["Internal Staff / Admin Request"]
    end

    subgraph SecurityGate["Security & Access Enforcement"]
        ACL["Access Control Matrix (ir.model.access.csv)"]
        ServerCheck["Python Server-Side Method Checks (raise AccessError)"]
        RecordRule["Row-Level Record Rules (ir.rule)"]
    end

    subgraph QueryExecution["Database Execution"]
        SQL["SQL Query with injected WHERE partner_id = ?"]
    end

    Cust --> ACL
    Cust --> ServerCheck
    Cust --> RecordRule
    Internal --> ACL
    Internal --> RecordRule

    RecordRule --> SQL
```

- **Authentication**: Native Odoo user session management with password complexity checks on creation.
- **Record Rules**: Record rules inject `partner_id = user.partner_id.id` into all customer searches, making cross-tenant data leaks physically impossible at the SQL query level.
- **Server Checks**: Critical methods (`action_confirm_payment`, `get_dashboard_metrics`, discount modifications) verify staff or admin roles in Python, rejecting unauthorized RPC requests with an immediate `AccessError`.
