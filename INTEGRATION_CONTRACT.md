# Technical Integration Contract: Brightloop Subscription Management System

**Project:** Brightloop Software - Subscription Management System (Odoo 17/18)  
**Team:** AuraMinds  
**Developer 1 (Author):** Dhruti Viradiya (Core Engine, Modules 1–4)  
**Developer 2 (Collaborator):** Drashti Bhanderi (Modules 5–8)  
**Branch:** `developer-1-core`  
**Status:** ACTIVE & RATIFIED  

---

## 1. Architectural Overview & Modular Structure

The solution is architected as an enterprise-grade Odoo addon module: `subscription_management`.
All models follow strict Odoo ORM conventions, snake_case table names, dot-notated model IDs, explicit field tracking for chatter/audit trails, and security ACLs.

### Module Breakdown
| Module # | Module Name | Primary Developer | Responsibility Summary |
|---|---|---|---|
| **Module 1** | Product & Product Variant Management | **Developer 1** | Products, variants, variant surcharge engine (e.g. Odoo brand +560) |
| **Module 2** | Subscription Plan Management | **Developer 1** | Daily/Weekly/Monthly/Yearly plans, constraints, auto-close, renewal, pause policies |
| **Module 3** | Quotation & Subscription Management | **Developer 1** | Templates, full state machine (`draft` → `quotation` → `confirmed` → `active` → `closed`), pause, resume, renewal, audit log |
| **Module 4** | Invoice & Automated Billing | **Developer 1** | Recurring cron billing engine, catch-up billing, duplicate prevention, concurrency locks, billing logs |
| **Module 5** | User Management & Authentication | Developer 2 | Security groups (Portal, Officer, Manager), multi-tier access, customer portal |
| **Module 6** | Discount Management | Developer 2 | Coupon codes, fixed/percentage discounts, voucher validation on subscriptions & invoices |
| **Module 7** | Payment Management | Developer 2 | Payment transactions, gateway integrations, automated receipt reconciliation |
| **Module 8** | Dashboard & Financial Reports | Developer 2 | MRR, ARR, Churn, Active Subscriptions KPI cards, cohort retention charts |

---

## 2. File Ownership Matrix

To prevent merge conflicts and maintain clean separation of concerns, file ownership is strictly designated:

### Developer 1 Owned Files
- `odoo_hackathon/subscription_management/__manifest__.py` (Core registration)
- `odoo_hackathon/subscription_management/__init__.py`
- `odoo_hackathon/subscription_management/models/__init__.py`
- `odoo_hackathon/subscription_management/models/product.py`
- `odoo_hackathon/subscription_management/models/subscription_plan.py`
- `odoo_hackathon/subscription_management/models/subscription.py`
- `odoo_hackathon/subscription_management/models/subscription_invoice.py`
- `odoo_hackathon/subscription_management/models/billing_log.py`
- `odoo_hackathon/subscription_management/views/product_views.xml`
- `odoo_hackathon/subscription_management/views/subscription_plan_views.xml`
- `odoo_hackathon/subscription_management/views/subscription_views.xml`
- `odoo_hackathon/subscription_management/views/invoice_views.xml`
- `odoo_hackathon/subscription_management/views/billing_log_views.xml`
- `odoo_hackathon/subscription_management/views/menu_views.xml`
- `odoo_hackathon/subscription_management/data/sequence_data.xml`
- `odoo_hackathon/subscription_management/data/cron_data.xml`
- `odoo_hackathon/subscription_management/reports/invoice_report.xml`
- `odoo_hackathon/subscription_management/security/ir.model.access.csv`
- `odoo_hackathon/subscription_management/security/security.xml`
- `odoo_hackathon/subscription_management/tests/*`

### Developer 2 Owned Files
- `odoo_hackathon/subscription_management/models/discount.py` (Discount & Coupon models)
- `odoo_hackathon/subscription_management/models/payment.py` (Payment transaction models)
- `odoo_hackathon/subscription_management/models/dashboard.py` (Dashboard queries & reporting models)
- `odoo_hackathon/subscription_management/views/discount_views.xml`
- `odoo_hackathon/subscription_management/views/payment_views.xml`
- `odoo_hackathon/subscription_management/views/dashboard_views.xml`
- `odoo_hackathon/subscription_management/reports/financial_report.xml`

---

## 3. Data Models Specification & Schema Contracts

### 3.1 Product & Variants (`models/product.py`)
- **Inherited / Extended Model:** `product.template` and `product.product` (or standalone subscription product if base product is overridden)
- **Key Fields:**
  - `is_subscription` (Boolean): Flag to designate subscription-eligible products.
  - `subscription_plan_ids` (Many2many → `subscription.plan`): Compatible plans.
  - `brand_name` (Char / Selection): Product brand (e.g. 'Odoo', 'Generic', etc.).
  - `brand_surcharge` (Float): Auto-computed or configurable; for 'Odoo' brand, adds **560.0** currency units.
  - `subscription_price` (Float, Computed): Base `list_price` + variant surcharges (`brand_surcharge` + attribute extra prices).
- **Public APIs for Dev 2 & Core:**
  - `get_calculated_price(partner=None, plan=None)`: Returns unit price inclusive of variant extra price.

---

### 3.2 Subscription Plan (`models/subscription_plan.py`)
- **Model Name:** `subscription.plan`
- **Key Fields:**
  - `name` (Char, Required): Plan display name (e.g. "Professional Monthly", "Enterprise Annual").
  - `code` (Char, Unique): Short identifier.
  - `price` (Float, Required): Base recurring price.
  - `billing_interval_unit` (Selection: `daily`, `weekly`, `monthly`, `yearly`): Billing frequency.
  - `billing_interval_count` (Integer, Default 1): Interval step multiplier.
  - `min_quantity` (Float, Default 1.0): Minimum product quantity enforcement.
  - `start_date` (Date): Plan availability start date.
  - `end_date` (Date): Plan availability end date.
  - `auto_close` (Boolean): Automatically close subscriptions upon expiry.
  - `auto_close_days` (Integer): Grace period in days before automatic closure.
  - `allow_early_close` (Boolean): Allows subscriber/agent early termination.
  - `allow_pause` (Boolean): Allows pausing active subscriptions.
  - `allow_renewal` (Boolean): Allows manual or automatic renewal.
  - `active` (Boolean, Default True): Archiving support.
- **Constraints:**
  - `@api.constrains('start_date', 'end_date')`: Ensures `end_date >= start_date`.
  - `@api.constrains('price')`: Ensures `price >= 0.0`.
  - `@api.constrains('min_quantity')`: Ensures `min_quantity >= 1.0`.

---

### 3.3 Quotation & Subscription (`models/subscription.py`)
- **Model Name:** `subscription.subscription`
- **Key Fields:**
  - `name` (Char, Unique): Sequence code (`SQ-00001` in Draft/Quotation, `SUB-00001` once Confirmed).
  - `partner_id` (Many2one → `res.partner`, Required): Customer reference.
  - `plan_id` (Many2one → `subscription.plan`, Required): Linked subscription plan.
  - `state` (Selection): `draft` → `quotation` → `confirmed` → `active` → `paused` → `closed` → `expired`.
  - `start_date` (Date, Required): Subscription activation date.
  - `expiry_date` (Date): Expected termination date (optional or computed from plan).
  - `next_billing_date` (Date, Index=True): Next date for scheduled recurring invoice generation.
  - `last_billing_date` (Date): Most recent invoice generation date.
  - `pause_date` (Date): Timestamp when subscription was paused.
  - `close_date` (Date): Date subscription was closed.
  - `close_reason` (Text): Audit justification for early or normal closure.
  - `line_ids` (One2many → `subscription.line`): Subscription product lines.
  - `invoice_ids` (One2many → `subscription.invoice`): Generated recurring invoices.
  - `invoice_count` (Integer, Computed): Number of linked invoices for smart button.
  - `amount_untaxed` (Monetary, Computed): Total untaxed subtotal of lines.
  - `amount_tax` (Monetary, Computed): Tax calculated across lines.
  - `amount_discount` (Monetary, Computed / Stored): **Developer 2 Hook** - Discount deduction.
  - `amount_total` (Monetary, Computed): `amount_untaxed + amount_tax - amount_discount`.
  - `currency_id` (Many2one → `res.currency`).
  - `company_id` (Many2one → `res.company`).
  - `user_id` (Many2one → `res.users`): Responsible account manager / sales rep.
  - `template_id` (Many2one → `subscription.quotation.template`): Preset configuration template.
- **Lifecycle Methods:**
  - `action_send_quotation()`: Transitions `draft` → `quotation`.
  - `action_confirm()`: Transitions `quotation` → `confirmed`, assigns `SUB-XXXXX` sequence number.
  - `action_activate()`: Transitions `confirmed` → `active`, initializes `next_billing_date`.
  - `action_pause()`: Transitions `active` → `paused`, validates `plan_id.allow_pause`.
  - `action_resume()`: Transitions `paused` → `active`, adjusts `next_billing_date`.
  - `action_renew()`: Validates `plan_id.allow_renewal`, extends duration or rolls over.
  - `action_close()`: Transitions to `closed`, validates `plan_id.allow_early_close` if closing before `expiry_date`.

---

### 3.4 Subscription Lines (`models/subscription.py`)
- **Model Name:** `subscription.line`
- **Key Fields:**
  - `subscription_id` (Many2one → `subscription.subscription`, Ondelete='cascade')
  - `product_id` (Many2one → `product.product`, Required)
  - `name` (Text, Required): Description
  - `quantity` (Float, Default 1.0): Validated against `plan_id.min_quantity`
  - `unit_price` (Float, Required): Base price + variant surcharges
  - `discount_rate` (Float): **Developer 2 Hook** (percentage discount)
  - `tax_ids` (Many2many → `account.tax` or custom tax)
  - `price_subtotal` (Monetary, Computed): `quantity * unit_price * (1 - discount_rate/100)`
  - `price_tax` (Monetary, Computed): Taxes applied
  - `price_total` (Monetary, Computed): `price_subtotal + price_tax`

---

### 3.5 Invoice & Automated Billing (`models/subscription_invoice.py`)
- **Model Name:** `subscription.invoice`
- **Key Fields:**
  - `name` (Char, Unique, Required): Sequence `INV-00001`.
  - `subscription_id` (Many2one → `subscription.subscription`, Ondelete='restrict', Index=True).
  - `partner_id` (Many2one → `res.partner`, Required): Invoiced customer.
  - `invoice_date` (Date, Required, Default Today): Date issued.
  - `due_date` (Date): Payment deadline.
  - `billing_period_start` (Date, Required): Start date of current recurring cycle.
  - `billing_period_end` (Date, Required): End date of current recurring cycle.
  - `state` (Selection): `draft` → `confirmed` → `paid` (also `cancel`).
  - `line_ids` (One2many → `subscription.invoice.line`).
  - `amount_untaxed` (Monetary, Computed).
  - `amount_tax` (Monetary, Computed).
  - `amount_discount` (Monetary, Computed / Dev 2 Hook).
  - `amount_total` (Monetary, Computed).
  - `currency_id` (Many2one → `res.currency`).
  - `company_id` (Many2one → `res.company`).
  - `payment_state` (Selection): `not_paid` | `partial` | `paid` (**Dev 2 Interface**).
  - `payment_ids` (One2many → `subscription.payment` / Dev 2 Hook).
- **Constraints & Idempotency:**
  - Unique SQL constraint: `_sql_constraints = [('uniq_sub_period', 'unique(subscription_id, billing_period_start, billing_period_end)', 'An invoice already exists for this subscription and billing period!')]`
  - ORM check prevents duplicate invoices if cron or user triggers generation multiple times.

---

### 3.6 Automated Billing Engine & Audit Log (`models/billing_log.py`)
- **Model Name:** `subscription.billing.log`
- **Key Fields:**
  - `execution_date` (Datetime, Default Now)
  - `subscription_id` (Many2one → `subscription.subscription`)
  - `invoice_id` (Many2one → `subscription.invoice`)
  - `status` (Selection: `success`, `skipped`, `failed`)
  - `message` (Text)
  - `billing_period_start` (Date)
  - `billing_period_end` (Date)
  - `amount` (Monetary)
  - `error_traceback` (Text)

---

## 4. Developer 2 Integration Contracts & Interfaces

### 4.1 Discount Management Hook (Module 6 Interface)
Developer 2 can hook into `subscription.subscription` and `subscription.invoice`:
1. **Fields reserved for Developer 2:**
   - `discount_id` (Many2one → `subscription.discount`): Linked coupon or discount rule.
   - `discount_code` (Char): Voucher code entered by user/portal.
   - `discount_type` (Selection: `fixed`, `percent`).
   - `discount_value` (Float).
2. **Hook Method in `subscription.subscription`:**
   ```python
   def _compute_discount_amount(self):
       """Extensible method for Developer 2 to calculate discount.
       Default fallback returns 0.0 or manual discount."""
       for sub in self:
           # Dev 2 overrides or extends this method in models/discount.py
           sub.amount_discount = sub._get_external_discount()
   ```
3. **Hook Method in `subscription.invoice`:**
   ```python
   def apply_discount_code(self, code):
       """Public API for Developer 2 coupon redemption."""
       pass
   ```

### 4.2 Payment Management Hook (Module 7 Interface)
Developer 2 manages payments and payment gateways:
1. **Invoice State Transitions:**
   - Dev 2's payment processing calls `invoice.action_register_payment(amount, payment_method, ref)`
   - Once payment is verified, update `invoice.payment_state = 'paid'` and transition `invoice.state = 'paid'`.
2. **Subscription Auto-Reactivation Hook:**
   - If a subscription was suspended/paused for non-payment, Dev 2 payment handler can call `subscription.action_resume()` upon successful settlement.

### 4.3 Dashboard & Financial Reporting Interface (Module 8 Interface)
Developer 2 builds KPI cards and analytics. Developer 1 exposes the following high-performance stored/computed metrics:
1. **Monthly Recurring Revenue (MRR):**
   - Field: `subscription.mrr` (Float, Stored)
   - Calculated according to frequency:
     - Daily: `amount_untaxed * 30.0`
     - Weekly: `(amount_untaxed / 7.0) * 30.0`
     - Monthly: `amount_untaxed * 1.0`
     - Yearly: `amount_untaxed / 12.0`
2. **Annual Recurring Revenue (ARR):**
   - Field: `subscription.arr` (Float, Stored): `mrr * 12.0`
3. **Churn & Cohort Analysis Data Points:**
   - `start_date`, `pause_date`, `close_date`, `close_reason`, `state` are indexed for fast aggregate SQL queries.

---

## 5. Security & Access Control Model

| Group XML ID | Name | Inherits | Permissions |
|---|---|---|---|
| `group_subscription_portal` | Subscription Portal Customer | `base.group_portal` | Read own subscriptions & invoices |
| `group_subscription_user` | Subscription Officer / Staff | `base.group_user` | CRUD Subscriptions, Quotations, Invoices |
| `group_subscription_manager` | Subscription Administrator | `group_subscription_user` | Configuration, Plans, Cron, Discard, Close |

---

## 6. Development & Verification Principles

1. **Zero Conflict Rule:** Developer 1 strictly maintains files listed in Section 2. Developer 2 implements extensions via Odoo class inheritance (`_inherit = 'subscription.subscription'`).
2. **Safe Cron Execution:** Cron runs with transactional savepoints (`cr.savepoint()`) per subscription record so that single-record failures never break the batch.
3. **Auditability:** Every lifecycle change is posted to Chatter (`mail.thread`) and captured in `subscription.billing.log`.
