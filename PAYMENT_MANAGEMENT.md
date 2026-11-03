# Module 3: Payment Management & Multi-Payment Reconciliation
## Project: Subscription Management System – Brightloop Software
### Team: AuraMinds | Developer 2: Drashti Bhanderi
### Target Odoo Version: Odoo 17.0 / 18.0 (Community & Enterprise)
### Branch: `developer-2-operations`

---

## 1. Executive Summary

The **Payment Management Module** is the third operational module implemented by Developer 2 in the Brightloop Subscription Management System. It completes the financial lifecycle of recurring subscriptions by recording, managing, and reconciling payments against subscription invoices.

### Architectural Principles:
1. **Multi-Payment Reconciliation**: Allows multiple partial payments per invoice, accumulating until the invoice residual reaches 0.00.
2. **Deterministic State Synchronization**: Automatically transitions invoice `payment_state` (`not_paid` -> `partial` -> `paid`) and invoice lifecycle `state` (`confirmed` -> `paid`) when fully settled.
3. **Idempotency & Double-Settlement Defense**: Re-confirming an already settled payment is a safe no-op. Re-computing totals does not duplicate amounts or corrupt balances.
4. **Strict Financial Constraints**: Negative and zero payment amounts are blocked at the ORM constraint level. Overpayments exceeding the invoice's outstanding balance are rejected.
5. **Security & Role-Based Isolation**: Record rules enforce strict customer isolation (customers only see payments for invoices matching their `partner_id`). Settlement actions (`action_confirm_payment` and `action_fail_payment`) are restricted to Internal Staff and Administrators; portal customer attempts raise `AccessError`.

---

## 2. Model Architecture & Fields

### A. Extended Model: `subscription.payment` (`models/payment.py`)

Inherits from `subscription.payment` without modifying Developer 1's core files:

| Field Name | Type | Properties | Description |
|---|---|---|---|
| `invoice_id` | `Many2one` | `subscription.invoice`, required, ondelete='cascade' | Target invoice being paid |
| `partner_id` | `Many2one` | `related='invoice_id.partner_id'`, store=True | Billing customer |
| `amount` | `Monetary` | required, currency_field='currency_id' | Payment amount (strictly > 0.0) |
| `payment_date` | `Datetime` | default=now, required | Settlement timestamp |
| `payment_method` | `Selection` | `cash`, `bank_transfer`, `upi`, `card`, `stripe`, `paypal`, `other` | Mode of settlement |
| `payment_note` | `Text` | optional | Audit memo, cheque number, or bank wire ref |
| `state` | `Selection` | `draft`, `success`, `failed` | Lifecycle state |
| `gateway_response` | `Text` | readonly | Failure reason or gateway confirmation |

#### Key Methods:
- `action_confirm_payment()`: Confirms settlement (`state='success'`). Verifies user permissions (`group_subscription_user` or `group_subscription_manager`). Reconciles target invoice totals. Idempotent if already settled.
- `action_fail_payment(reason)`: Marks transaction as `failed`. If previously settled, triggers reconciliation to restore residual balance.

---

### B. Extended Model: `subscription.invoice` (`models/payment.py`)

Augments `subscription.invoice` with payment reconciliation:

| Field Name | Type | Properties | Description |
|---|---|---|---|
| `payment_ids` | `One2many` | comodel='subscription.payment', inverse='invoice_id' | All transactions linked to this invoice |
| `amount_paid` | `Monetary` | compute='_compute_payment_totals', store=True | Total sum of settled payments (`state == 'success'`) |
| `amount_residual` | `Monetary` | compute='_compute_payment_totals', store=True | Remaining balance (`max(0.0, amount_total - amount_paid)`) |
| `is_overdue` | `Boolean` | compute='_compute_overdue', store=True | True if unpaid and `due_date < today` |
| `days_overdue` | `Integer` | compute='_compute_overdue' | Days elapsed since due date |

#### State Machine Transition Logic:
$$\text{amount\_paid} = \sum_{\substack{p \in \text{payment\_ids} \\ p.\text{state} = \text{'success'}}} p.\text{amount}$$

$$\text{amount\_residual} = \max(0.0, \text{round}(\text{amount\_total} - \text{amount\_paid}, 2))$$

- **Full Settlement**: If $\text{amount\_residual} \le 0.001$ and $\text{amount\_total} > 0.0$:
  - `payment_state = 'paid'`
  - `state = 'paid'`
- **Partial Settlement**: If $0.0 < \text{amount\_paid} < \text{amount\_total}$:
  - `payment_state = 'partial'`
  - `state = 'confirmed'`
- **Unpaid / Zero Settlement**: If $\text{amount\_paid} = 0.0$:
  - `payment_state = 'not_paid'`
  - `state = 'confirmed'`

---

### C. Transient Wizard: `subscription.payment.register.wizard`

Interactive modal wizard for staff/managers to record incoming payments directly from the invoice form:
- Displays current invoice total and live outstanding residual balance.
- Pre-fills amount with remaining residual.
- Validates that entered amount is $> 0.0$ and $\le \text{amount\_residual}$.
- On submit, creates payment transaction and triggers settlement in a single atomic transaction.

---

## 3. Security & Access Control

1. **Access Control List (`ir.model.access.csv`)**:
   - `access_subscription_payment_register_wizard_user`: Read, Write, Create for `group_subscription_user` (Staff).
   - `access_subscription_payment_register_wizard_manager`: Full access for `group_subscription_manager` (Admin).
2. **Record Rule (`subscription_payment_portal_rule`)**:
   - Customer Portal domain: `[('partner_id', '=', user.partner_id.id)]`.
   - Customers can only view their own payment transactions.
   - Customers cannot access, view, or settle other customers' payments.
3. **RPC Defense**:
   - Portal customers attempting to invoke `action_confirm_payment()` or `action_fail_payment()` are blocked by `AccessError`.

---

## 4. Test & Verification Coverage

### Summary of Test Suites:
- Native Odoo `TransactionCase` suite: `subscription_management/tests/test_payment_management.py` (14 scenarios)
- Standalone Verification suite: `tests/test_payment_management_standalone.py` (16 scenarios)
- Full Project Verification suite: `tests/run_standalone_verification.py` (69/69 passed)

### Test Verification Matrix:

| # | Test Scenario | Native Odoo Test | Standalone Test | Result |
|---|---|---|---|---|
| 1 | Creating a valid payment | `test_01_create_valid_payment` | `test_01_create_valid_payment` | PASS |
| 2 | Rejecting zero and negative payment amounts | `test_02_rejecting_zero_and_negative_amounts` | `test_02_rejecting_zero_and_negative_amounts` | PASS |
| 3 | Full payment settles invoice (`state='paid'`, `payment_state='paid'`) | `test_03_full_payment` | `test_03_full_payment_settles_invoice` | PASS |
| 4 | Partial payment updates balance & state (`partial`) | `test_04_partial_payment` | `test_04_partial_payment` | PASS |
| 5 | Multiple partial payments accumulate to full settlement | `test_05_multiple_partial_payments` | `test_05_multiple_partial_payments` | PASS |
| 6 | Correct outstanding balance calculation | `test_06_correct_outstanding_balance_calculation` | `test_06_correct_outstanding_balance_calculation` | PASS |
| 7 | Failed payment not affecting invoice balance | `test_07_failed_payment_not_affecting_balance` | `test_07_failed_payment_not_affecting_balance` | PASS |
| 8 | Draft payment not affecting invoice balance | `test_08_draft_payment_not_affecting_balance` | `test_08_draft_payment_not_affecting_balance` | PASS |
| 9 | Duplicate confirmation prevention (idempotent no-op) | `test_09_duplicate_confirmation_prevention` | `test_09_duplicate_confirmation_prevention` | PASS |
| 10 | Payment linked to correct invoice and customer | `test_10_payment_linked_to_correct_invoice_and_customer` | `test_10_payment_linked_to_correct_invoice_and_customer` | PASS |
| 11 | Customer can view only their own payments | `test_11_customer_can_view_only_own_payments` | `test_11_customer_can_view_only_own_payments` | PASS |
| 12 | Customer cannot access another customer's payment | `test_12_customer_cannot_access_another_customer_payment` | `test_12_customer_cannot_access_another_customer_payment` | PASS |
| 13 | Staff/Admin permissions (customers cannot confirm) | `test_13_staff_and_admin_permissions` | `test_13_staff_and_admin_permissions` | PASS |
| 14 | Existing discount and invoice calculations remain intact | `test_14_existing_discount_and_invoice_calculations_remain_correct` | `test_14_existing_discount_and_invoice_calculations` | PASS |
| 15 | Overpayment rejection against residual | — | `test_15_overpayment_validation` | PASS |
| 16 | Interactive Payment Registration Wizard simulation | — | `test_16_payment_registration_wizard` | PASS |

---

## 5. UI Views & User Experience

1. **Payment Form View (`view_subscription_payment_form`)**:
   - Status bar with draft/success/failed states.
   - Settled and Failed web ribbons.
   - Settle and Fail action buttons with conditional visibility.
   - Detailed billing and transaction memo fields.
2. **Payment Tree View (`view_subscription_payment_tree`)**:
   - Color-coded badges for status (`decoration-success`, `decoration-info`, `decoration-danger`).
   - Payment method badges and monetary formatted columns.
3. **Payment Search View (`view_subscription_payment_search`)**:
   - Quick filters for Settled, Draft, and Declined payments.
   - Group by Customer, Invoice, Payment Method, Status, and Month.
4. **Invoice Inheritance (`view_subscription_invoice_form_inherit_payments`)**:
   - Financial totals group augmented with `amount_paid` and `amount_residual`.
   - Overdue ribbon (`bg-danger`) displayed when `is_overdue == True`.
   - Dedicated "Payment Transactions" notebook page displaying payment history.
   - Action button "Register Payment" on invoice header.
