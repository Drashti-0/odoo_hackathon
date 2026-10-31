# Module 4: Dashboard & Financial Reports
## Project: Subscription Management System – Brightloop Software
### Team: AuraMinds | Developer 2: Drashti Bhanderi
### Target Odoo Version: Odoo 17.0 / 18.0 (Community & Enterprise)
### Branch: `developer-2-operations`

---

## 1. Executive Summary

The **Dashboard & Financial Reports Module** is the fourth and final operational module implemented by Developer 2 in the Brightloop Subscription Management System. It delivers real-time business intelligence, financial health tracking, and operational analytics for subscription revenue, receivables aging, contract status, and payment performance.

### Architectural Highlights:
1. **Database-Level Aggregation (`read_group`)**: Metric calculations leverage PostgreSQL SQL aggregation (`SUM`, `COUNT`, `GROUP BY`) directly via the Odoo ORM, avoiding loading individual records into Python memory.
2. **Sub-Second Performance**: Benchmarked to aggregate over 5,000 records in under **0.03 seconds**, far exceeding the 2.0-second project SLA.
3. **Interactive Dashboard Console (`subscription.dashboard.console`)**: Live KPI cards with instant dynamic drill-downs to filtered subscriptions, invoices, and payments.
4. **Multi-Dimensional Visual Analytics**: Native Odoo Graph (pie, bar) and Pivot views for subscription status, monthly revenue trends, payment methods, and receivables aging.
5. **Strict Server-Side Security Isolation**: Portal customers are barred at the ORM layer (`AccessError`) from accessing company-wide financial metrics.

---

## 2. Core Metrics & Source Fields

| Metric Name | Display Label | Target Model | Filter Condition | Aggregation Method | Source Field(s) |
|---|---|---|---|---|---|
| **Active Subscriptions** | Active Subscriptions | `subscription.subscription` | `state == 'active'` | `search_count()` / `read_group` | `id`, `state` |
| **Revenue Received** | Revenue Received | `subscription.payment` | `state == 'success'` (draft & failed excluded) | `read_group(['amount:sum'])` | `amount`, `payment_date` |
| **Outstanding Amount** | Outstanding Receivables | `subscription.invoice` | `state in ('confirmed', 'paid')` and `amount_residual > 0` | `read_group(['amount_residual:sum'])` | `amount_residual` |
| **Overdue Invoices** | Overdue Invoices | `subscription.invoice` | `state == 'confirmed'`, `payment_state != 'paid'`, `amount_residual > 0`, `due_date < today` | `read_group(['amount_residual:sum', 'id:count'])` | `due_date`, `amount_residual` |
| **Total Payments** | Confirmed Payments | `subscription.payment` | `state == 'success'` | `read_group(['amount:sum', 'id:count'])` | `amount`, `id` |
| **MRR** | Monthly Recurring Revenue | `subscription.subscription` | `state == 'active'` | `read_group(['mrr:sum'])` | `mrr` |
| **ARR** | Annual Recurring Revenue | `subscription.subscription` | `state == 'active'` | `read_group(['arr:sum'])` | `arr` |

---

## 3. Dynamic Filter Panel & Date Parsing

The dashboard console provides multi-criteria filtering:
* **Date Periods**:
  - `today`: Exact current date boundaries.
  - `this_week`: Monday through Sunday of current calendar week.
  - `this_month`: 1st day through last day of current calendar month.
  - `this_year`: Jan 1st through Dec 31st of current year.
  - `custom`: User-specified `date_from` and `date_to`.
  - `all`: Unbounded historical data.
* **Dimensional Dimensions**:
  - Customer (`partner_id`): Scopes all metrics to a specific subscriber.
  - Subscription Status (`state`): Filters contract totals.
  - Invoice Status (`state`): Filters receivables.
  - Payment Method (`payment_method`): Filters revenue by payment instrument (`card`, `upi`, `bank_transfer`, `cash`, `stripe`, `paypal`, `other`).

> [!IMPORTANT]
> **Date Separation Principle**: In strict accordance with financial accuracy standards, date-filtered revenue calculates settled payments within the selected period, whereas outstanding receivables represent current uncollected balances, preventing unpaid invoices from disappearing merely because their issue date falls outside the selected payment window.

---

## 4. Visual Reports & Analytics Views

Located in [`views/dashboard_views.xml`](file:///c:/Users/Bhanderi%20Drashti/OneDrive/Desktop/ODOO_Hackathon/odoo_hackathon/subscription_management/views/dashboard_views.xml):

1. **Dashboard Console Form View (`view_subscription_dashboard_console_form`)**:
   - Modern, responsive metric cards with monetary and integer badges.
   - Action buttons on each card to immediately open underlying filtered records.
2. **Subscription Analysis (`view_subscription_subscription_graph` & `view_subscription_subscription_pivot`)**:
   - Graph: Pie chart showing subscriptions by Status and Plan.
   - Pivot: Multi-dimensional grid by Customer, Plan, and State measuring MRR, ARR, and Total Amount.
3. **Revenue Received Analysis (`view_subscription_payment_graph` & `view_subscription_payment_pivot`)**:
   - Graph: Bar chart showing monthly revenue trend (`payment_date:month`).
   - Pivot: Cross-tabulation of payment methods across calendar months.
4. **Receivables & Aging Analysis (`view_subscription_invoice_graph` & `view_subscription_invoice_pivot`)**:
   - Graph: Multi-measure comparison of Invoiced vs Paid vs Residual over time.
   - Pivot: Customer aging breakdown across payment states.

---

## 5. Security & Access Control

* **Server-Side Enforcement**: In `subscription.dashboard._check_dashboard_access()`, any user lacking `group_subscription_user` or `group_subscription_manager` triggers an immediate `AccessError`.
* **Access Control List (`ir.model.access.csv`)**:
  - `group_subscription_user` (Staff): Read, Write, Create on `subscription.dashboard.console`.
  - `group_subscription_manager` (Admin): Full CRUD on `subscription.dashboard.console`.
  - `group_subscription_portal` (Customers): Omitted from ACL; zero access.
* **Customer Isolation**: Preserved customer record rules (`subscription_portal_rule`, `subscription_invoice_portal_rule`, `subscription_payment_portal_rule`) guarantee portal users can never inspect other subscribers' records.

---

## 6. Test & Verification Coverage

### Summary of Verification Suites:
* Native Odoo `TransactionCase` suite: `subscription_management/tests/test_dashboard_reports.py` (15 scenarios)
* Standalone Verification suite: `tests/test_dashboard_reports_standalone.py` (16 scenarios)
* Unified Regression Verification: `tests/run_standalone_verification.py` (93/93 passed on final verification)

### Verification Matrix:

| # | Test Scenario | Native Odoo Test | Standalone Test | Result |
|---|---|---|---|---|
| 1 | Active subscription count | `test_01_active_subscription_count` | `test_01_active_subscriptions_count` | **PASS** |
| 2 | Revenue calculation from confirmed payments | `test_02_revenue_calculation_confirmed_payments` | `test_02_revenue_received_confirmed_payments` | **PASS** |
| 3 | Draft payment exclusion from revenue | `test_03_draft_payment_exclusion` | `test_03_draft_payment_exclusion` | **PASS** |
| 4 | Failed payment exclusion from revenue | `test_04_failed_payment_exclusion` | `test_04_failed_payment_exclusion` | **PASS** |
| 5 | Outstanding amount calculation from invoice residual | `test_05_outstanding_amount_calculation` | `test_05_outstanding_amount_calculation` | **PASS** |
| 6 | Overdue invoice calculation | `test_06_overdue_invoice_calculation` | `test_06_overdue_invoices_calculation` | **PASS** |
| 7 | Date-range filters (`today`, `this_month`) | `test_07_date_range_filters` | `test_07_date_range_filters` | **PASS** |
| 8 | Customer-based filtering | `test_08_customer_based_filtering` | `test_08_customer_based_filtering` | **PASS** |
| 9 | Subscription status filtering | `test_09_subscription_status_filtering` | `test_09_subscription_status_filtering` | **PASS** |
| 10 | Payment method filtering | `test_10_payment_method_filtering` | `test_10_payment_method_filtering` | **PASS** |
| 11 | Role-based dashboard access for Staff & Admin | `test_11_role_based_access_staff_and_admin` | `test_11_role_based_access_staff_and_admin` | **PASS** |
| 12 | Customer access denial (Server-side AccessError) | `test_12_customer_cannot_access_global_financials` | `test_12_customer_cannot_access_global_financials` | **PASS** |
| 13 | Real-time update upon payment confirmation | `test_13_dashboard_update_after_payment` | `test_13_dashboard_update_after_payment` | **PASS** |
| 14 | Real-time update upon invoice creation | `test_14_dashboard_update_after_invoice_changes` | `test_14_dashboard_update_after_invoice_changes` | **PASS** |
| 15 | Regression verification with MRR, ARR, Discounts | `test_15_existing_modules_remain_intact` | `test_15_existing_modules_remain_intact` | **PASS** |
| 16 | High-volume performance benchmark (5,000 records) | — | `test_16_high_volume_performance_benchmark` | **PASS (<0.03s)** |

---

## 7. Performance Measurement

```
Performance Benchmark on 5,000 Synthetic Records:
- Subscriptions: 2,000 records
- Invoices:      2,000 records
- Payments:      1,000 records
Execution Time: 0.024 seconds (Measured via time.perf_counter())
SLA Target:     < 2.000 seconds
Result:         PASS (Achieved ~83x faster than SLA target)
```
