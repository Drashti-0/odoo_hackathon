# Module 2: Discount Management

**Brightloop Software – Subscription Management System (Odoo 17/18)**  
**Developer 2:** Drashti Bhanderi  
**Branch:** `developer-2-operations`  
**Status:** IMPLEMENTED & VERIFIED (28/28 Discount Tests Passing, 53/53 Unified Tests Passing)

---

## 1. Architectural Overview & Shared Contract Integration

Module 2 extends Developer 1's hook model (`subscription.discount`) and integrates discount rule evaluation directly into the subscription and recurring billing engine:
- Extends `subscription.discount` in `models/discount.py`.
- Connects with `subscription.subscription` via `_hook_compute_discount()`.
- Connects with `subscription.invoice` via automatic inheritance on creation and idempotent amount computation.
- Fully preserves Developer 1's invoice line models, multi-tax calculations, and catch-up billing workflows.

---

## 2. Core Discount Capabilities

### A. Discount Types
1. **Percentage Discount (`percentage`):**
   - Value must satisfy `0.0 < value <= 100.0`.
   - Formula: `Discount = Eligible Amount × (Percentage / 100.0)`.
2. **Fixed Amount Discount (`fixed`):**
   - Value must satisfy `value > 0.0`.
   - Formula: `Discount = min(Fixed Value, Eligible Amount)` (guarantees discount never exceeds subtotal or produces negative invoice totals).

### B. Eligibility & Threshold Enforcement
- **Minimum Purchase Amount (`min_purchase_amount`):** Requires untaxed subtotal to meet or exceed threshold.
- **Minimum Quantity (`min_quantity`):** Requires total item units to meet or exceed threshold.
- **Validity Dates (`start_date`, `end_date`):** Enforces active window (`start_date <= date <= end_date`). Rejects pre-start or expired redemptions.
- **Usage Limits (`usage_limit`):** Enforces maximum global redemptions across all contracts/invoices.
- **Product Applicability (`applicable_product_ids`):** If specified, discount deduction calculates only from eligible product lines; if left empty, applies to all products.
- **Whole Subscription Applicability (`apply_to_whole_subscription`):** Determines whether the rule applies at the subscription contract level or line-matching level.

### C. Admin-Only Security Control
- Only users with `group_subscription_manager` (or Superuser) can create, edit, or delete discount rules.
- Internal Staff (`group_subscription_user`) and Portal Customers (`group_subscription_portal`) attempting create/write/unlink trigger an immediate server-side `AccessError`.

---

## 3. Automated Billing Engine Integration & Idempotency

### A. Automatic Inheritance
When Developer 1's recurring billing cron (`cron_recurring_billing`) or manual generation triggers an invoice for an active subscription with a valid discount:
- The generated invoice automatically inherits `discount_id` and `discount_code`.
- The discount deduction is applied to the invoice subtotal while preserving line taxes.

### B. Idempotency & Duplicate Prevention
- Repeated execution of `_compute_amounts()` computes the discount deduction functionally without stacking or compounding deductions.
- Multiple saves, edits, recalculations, or cron retries on the same period produce the identical financial total.

### C. Concurrency-Safe Usage Tracking
- When an invoice transitions to `'confirmed'` (or is auto-confirmed by the billing engine), usage is incremented safely with row-level locks (`SELECT FOR UPDATE`).
- Boolean flag `discount_usage_recorded` on `subscription.invoice` guarantees that retry operations never count the same invoice twice.
- If an invoice is cancelled (`action_cancel()`), the recorded usage is decremented accordingly.

---

## 4. Test Verification Summary

All 28 required test cases are verified:
- **Discount Calculation:** Fixed, Percentage, Boundary checks, Clamping (Tests 1–5).
- **Eligibility Conditions:** Min purchase, Min quantity, Product-specific, Whole-subscription (Tests 6–11).
- **Date & Usage Limits:** Start dates, Valid ranges, Expiry, Limits, Concurrency, Duplicate prevention (Tests 12–18).
- **Billing Integration:** Auto-application, Totals, Idempotency, Retry safety, Tax preservation, Base engine stability (Tests 19–24).
- **Security:** Admin permissions, Staff restrictions, Customer restrictions, RPC protection (Tests 25–28).

**Commands:**
```bash
python tests/test_discount_management_standalone.py -v
python tests/run_standalone_verification.py -v
```
