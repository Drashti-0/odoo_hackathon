# Database & Model Documentation
## Brightloop Subscription Management System

**Project:** Subscription Management System – Brightloop Software  
**Team:** AuraMinds  
**Target Version:** Odoo 17.0 / 18.0  
**Branch:** `developer-2-operations`  

---

## 1. Master Model Registry

The following comprehensive table indexes every data model in the application, detailing its purpose, key fields, relationships, important methods, and ownership:

| Model Technical Name | Primary Purpose | Key Fields | Relationships | Key Methods | Author / Module |
|---|---|---|---|---|---|
| `product.template` | Base product definitions | `name`, `list_price`, `is_subscription`, `brand_name` | One2many to `product.product` | `_compute_subscription_price()` | Developer 1 (Core) |
| `product.product` | Surcharge pricing engine | `brand_surcharge`, `subscription_price`, `variant_extra` | Many2one to `product.template` | `get_subscription_price()` | Developer 1 (Core) |
| `subscription.plan` | Billing cadence & policies | `name`, `code`, `billing_interval_unit`, `billing_interval_count`, `price`, `auto_close` | One2many to `subscription.subscription` | `get_next_billing_date()`, `_check_dates()` | Developer 1 (Core) |
| `subscription.subscription` | Central contract lifecycle | `name`, `state`, `start_date`, `next_billing_date`, `mrr`, `arr`, `amount_total` | Many2one: `partner_id`, `plan_id`. One2many: `line_ids`, `invoice_ids` | `action_confirm()`, `action_activate()`, `action_pause()`, `action_renew()` | Developer 1 (Core) |
| `subscription.subscription` *(Extension)* | Promotional discount integration | `discount_id`, `discount_code`, `discount_rate`, `amount_discount` | Many2one to `subscription.discount` | `_compute_amounts()`, `_compute_discount_amount()`, `action_apply_discount()` | Developer 2 (Task 3 Extension) |
| `subscription.line` | Subscription line items | `product_id`, `quantity`, `unit_price`, `discount_rate`, `price_subtotal`, `price_total` | Many2one to `subscription.subscription` | `_compute_amounts()` | Developer 1 (Core) |
| `subscription.quotation.template` | Predefined quotation templates | `name`, `plan_id`, `validity_days`, `terms_and_conditions` | One2many to `subscription.quotation.template.line` | `_compute_defaults()` | Developer 1 (Core) |
| `subscription.invoice` | Recurring billing invoice | `name`, `state`, `invoice_date`, `due_date`, `amount_untaxed`, `amount_total` | Many2one: `partner_id`, `subscription_id`. One2many: `line_ids` | `action_confirm()`, `_compute_amounts()` | Developer 1 (Core) |
| `subscription.invoice` *(Extension)* | Discounts & Payment Reconciliation | `discount_id`, `discount_amount`, `amount_paid`, `amount_residual`, `is_overdue`, `payment_ids` | One2many to `subscription.payment`, Many2one to `subscription.discount` | `_compute_payment_totals()`, `_compute_overdue()`, `action_register_payment()` | Developer 2 (Tasks 3 & 4 Extension) |
| `subscription.invoice.line` | Invoice line items | `product_id`, `quantity`, `unit_price`, `discount_rate`, `price_subtotal`, `price_total` | Many2one to `subscription.invoice` | `_compute_line_amounts()` | Developer 1 (Core) |
| `subscription.billing.log` | Billing engine audit log | `subscription_id`, `invoice_id`, `execution_date`, `status`, `message` | Many2one: `subscription_id`, `invoice_id` | `log_execution()` | Developer 1 (Core) |
| `res.users` *(Extension)* | Password complexity & portal customer registration | `password`, `login`, `email`, `groups_id` | Many2one to `res.partner` | `register_portal_customer()`, `validate_password_complexity()`, `request_password_reset()` | Developer 2 (Task 2 Extension) |
| `subscription.discount` | Promotional rules & coupon limits | `name`, `code`, `discount_type`, `value`, `min_purchase_amount`, `min_quantity`, `usage_limit`, `usage_count` | Many2many to `product.product` (`applicable_product_ids`) | `check_eligibility()`, `calculate_discount_amount()`, `action_archive()` | Developer 2 (Task 3 New Model) |
| `subscription.payment` | Multi-method payments | `name`, `amount`, `payment_date`, `payment_method`, `state`, `gateway_response`, `payment_note` | Many2one: `invoice_id`, `partner_id` | `action_confirm_payment()`, `action_fail_payment()`, `_check_payment_amount()` | Developer 2 (Task 4 Extension) |
| `subscription.payment.register.wizard` | Modal payment entry dialog | `invoice_id`, `partner_id`, `amount`, `payment_date`, `payment_method`, `payment_reference` | Many2one to `subscription.invoice` | `action_submit_payment()` | Developer 2 (Task 4 Transient) |
| `subscription.customer.register.wizard` | Staff customer registration | `name`, `email`, `password`, `company_name` | Many2one to `res.partner` | `action_register_customer()` | Developer 2 (Task 2 Transient) |
| `subscription.dashboard` | Financial analytics engine | N/A (Abstract calculation engine) | Relational queries via ORM | `get_dashboard_metrics()`, `_check_dashboard_access()`, `_parse_date_range()` | Developer 2 (Task 5 Abstract) |
| `subscription.dashboard.console` | Interactive UI analytics console | `date_range_type`, `date_from`, `date_to`, `partner_id`, `active_subscriptions`, `revenue_received`, `outstanding_amount`, `overdue_invoices`, `mrr_total`, `arr_total` | Many2one: `partner_id`, `currency_id` | `_compute_dashboard_metrics()`, `action_view_active_subscriptions()`, `action_view_received_payments()` | Developer 2 (Task 5 Transient) |

---

## 2. Field-Level Technical Specifications

### A. Extended Model: `subscription.payment`
- **`payment_method`**: Selection (`cash`, `bank_transfer`, `upi`, `card`, `stripe`, `paypal`, `other`), Default: `'card'`, Required: True.
- **`payment_note`**: Text (Internal memo, cheque number, bank wire confirmation).
- **`amount`**: Monetary, Required: True.
  - *Validation*: Enforces `amount > 0.0`.
  - *Validation*: Enforces `amount <= invoice_id.amount_residual`.
- **`state`**: Selection (`draft`, `success`, `failed`), Default: `'draft'`.

### B. Extended Model: `subscription.invoice`
- **`amount_paid`**: Monetary, Computed, Stored, Tracking=True.
  - *Logic*: $\sum p.\text{amount}$ for all $p \in \text{payment\_ids}$ where $p.\text{state} = \text{'success'}$.
- **`amount_residual`**: Monetary, Computed, Stored, Tracking=True.
  - *Logic*: $\max(0.0, \text{amount\_total} - \text{amount\_paid})$.
- **`is_overdue`**: Boolean, Computed, Stored.
  - *Logic*: True if `state == 'confirmed' and payment_state != 'paid' and due_date < today`.
- **`days_overdue`**: Integer, Computed.
  - *Logic*: $(\text{today} - \text{due\_date}).\text{days}$ if overdue, else 0.

### C. Extended Model: `subscription.subscription`
- **`mrr`**: Monetary, Computed, Stored. Normalized monthly recurring revenue:
  - Daily: $\text{amount\_untaxed} \times 30.0$
  - Weekly: $(\text{amount\_untaxed} / 7.0) \times 30.0$
  - Monthly: $\text{amount\_untaxed} \times 1.0$
  - Yearly: $\text{amount\_untaxed} / 12.0$
- **`arr`**: Monetary, Computed, Stored: $\text{mrr} \times 12.0$.
- **`amount_discount`**: Monetary, Computed, Stored, Tracking=True. Promotional deduction applied via Developer 2 hook.
- **`amount_total`**: Monetary, Computed, Stored: $\text{amount\_untaxed} + \text{amount\_tax} - \text{amount\_discount}$.

### D. New Model: `subscription.discount`
- **`discount_type`**: Selection (`fixed`, `percentage`), Required: True.
- **`value`**: Float, Required: True.
  - *Validation*: If percentage, $0.0 < \text{value} \le 100.0$. If fixed, $\text{value} > 0.0$.
- **`min_purchase_amount`**: Monetary, Default: 0.0.
- **`min_quantity`**: Float, Default: 0.0.
- **`usage_limit`**: Integer, Default: 0 (0 = unlimited).
- **`usage_count`**: Integer, Default: 0.
- **`apply_to_whole_subscription`**: Boolean, Default: True.
- **`applicable_product_ids`**: Many2many to `product.product`.
