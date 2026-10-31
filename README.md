# Brightloop Subscription Management System
## Enterprise SaaS Contract Lifecycle, Intelligent Recurring Billing & Financial Analytics

[![Platform](https://img.shields.io/badge/Odoo-17.0%20%7C%2018.0-714B67?logo=odoo)](https://www.odoo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql)](https://www.postgresql.org)
[![License](https://img.shields.io/badge/License-LGPL--3-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-91%20Passed-brightgreen)](tests/run_standalone_verification.py)

---

## 1. Project Overview

The **Brightloop Subscription Management System** is a production-grade Odoo application developed by **Team AuraMinds** for the Odoo Hackathon. It provides a complete subscription lifecycle, automated periodic billing engine, promotional discount management, multi-gateway payment reconciliation, and real-time executive financial analytics.

### Team Members & Separation of Concerns
- **Developer 1 (Dhruti Viradiya)**: Modules 1–4 (Product & Variants, Subscription Plans, Contract Lifecycle, Recurring Billing Engine).
- **Developer 2 (Drashti Bhanderi)**: Modules 5–8 (User Management & Authentication, Discount Management, Payment Management, Dashboard & Financial Reports).

---

## 2. Problem Statement & Objectives

### The Business Challenge
Traditional ERP systems operate on single-transaction purchase orders and static sales invoices. Companies adopting subscription business models face severe operational bottlenecks:
1. **Billing Overhead**: Sales and finance teams manually track renewal dates, resulting in delayed invoicing or forgotten renewals.
2. **Revenue Leakage**: Complex products with brand surcharges and promotional discounts frequently experience miscalculation or double-application.
3. **Partial Payment Reconciliation**: Customers paying in installments across multiple payment channels create fragmented accounting balances.
4. **Data Privacy**: Multi-tenant customers must be strictly prevented from accessing other organizations' pricing, invoices, or contracts.
5. **Slow Financial Visibility**: Computing SaaS metrics (MRR, ARR, Churn, Overdue Receivables) requires manual spreadsheet exports.

### Project Objectives
- Automate contract state transitions: `Draft` $\rightarrow$ `Quotation` $\rightarrow$ `Confirmed` $\rightarrow$ `Active` $\rightarrow$ `Closed`.
- Deliver an autonomous, catch-up-capable recurring billing cron engine that leaves zero billing gaps and avoids duplicate charges.
- Implement an idempotent promotional discount engine with boundary clamping to prevent negative invoice balances.
- Support multi-payment settlement (Card, Bank Wire, UPI, Stripe, PayPal) with automatic residual balance reconciliation.
- Enforce multi-tenant customer isolation at the PostgreSQL database layer using Odoo record rules.
- Provide sub-second executive analytics using database-level SQL aggregation (`read_group`).

---

## 3. Main Features

| Feature Area | Key Capabilities |
|---|---|
| **Catalog & Surcharges** | Multi-brand product variants with mandatory Odoo brand variant surcharge (+560.0). |
| **Flexible Plan Cadences** | Daily, Weekly, Monthly, and Yearly intervals; grace periods, renewal policies, and early closure controls. |
| **Quotation & Contracts** | Predefined quotation templates, digital quotation delivery, sequence generation (`SUB-XXXXX`), pause/resume with billing date adjustment. |
| **Automated Billing Engine** | Cron-driven recurring billing with catch-up for past cycles, transactional savepoints (`cr.savepoint()`), and billing audit logs. |
| **User & Portal Security** | Multi-role security (Admin, Staff, Portal Customer), RFC email validation, password complexity enforcement, enumeration-safe password resets. |
| **Discount Management** | Fixed and percentage coupons, subtotal clamping, minimum purchase/quantity thresholds, start/end dates, global usage caps. |
| **Payment Reconciliation** | Settlement across 7 payment methods, overpayment prevention, dynamic residual balances, and automated `Paid` status synchronization. |
| **Executive Dashboard** | 5 core KPIs (Active Contracts, Revenue Received, Receivables, Overdue Invoices, Confirmed Payments), MRR/ARR metrics, monthly revenue trends, and pivot analytics. |

---

## 4. Technical Architecture & Technologies

- **Framework**: Odoo 17.0 / 18.0 (Community and Enterprise).
- **Backend Language**: Python 3.10+ (tested through Python 3.14).
- **ORM**: Odoo Object-Relational Mapping (PostgreSQL driver with transactional savepoints).
- **Database**: PostgreSQL 14+ (relational schema, composite indices, foreign keys).
- **Frontend / UI**: Odoo Web Client (XML Form, Tree, Search, Graph, Pivot, Web Ribbons, and Badges).
- **Automation**: Odoo Scheduled Actions (`ir.cron`).
- **Security**: Access Control Lists (`ir.model.access.csv`) and Record Rules (`ir.rule`).

---

## 5. Project Directory Structure

```text
odoo_hackathon/
├── README.md                               # Project overview and quickstart guide
├── INTEGRATION_CONTRACT.md                 # Shared architectural interface contract
├── USER_MANAGEMENT.md                      # Module 1 documentation
├── DISCOUNT_MANAGEMENT.md                  # Module 2 documentation
├── PAYMENT_MANAGEMENT.md                   # Module 3 documentation
├── DASHBOARD_REPORTS.md                    # Module 4 documentation
├── DEMO_GUIDE.md                           # 10-step evaluator demonstration script
├── odoo.conf                               # Odoo server runtime configuration
├── docker-compose.yml                      # Containerized Odoo & PostgreSQL stack
├── docs/                                   # Comprehensive technical documentation suite
│   ├── PROJECT_OVERVIEW.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_MODELS.md
│   ├── MODULE_DOCUMENTATION.md
│   ├── SECURITY_DOCUMENTATION.md
│   ├── TESTING_REPORT.md
│   ├── DEVELOPER_2_CONTRIBUTION.md
│   └── SUBMISSION_CHECKLIST.md
├── subscription_management/                # Core Odoo Addon Module
│   ├── __init__.py
│   ├── __manifest__.py                     # Module definition and data loading order
│   ├── controllers/                        # Public HTTP / JSON portal auth controllers
│   │   └── portal_auth.py
│   ├── models/                             # ORM models and business logic
│   │   ├── product.py                      # Developer 1: Products & Variant surcharges
│   │   ├── subscription_plan.py            # Developer 1: Cadences & Plan policies
│   │   ├── subscription.py                 # Developer 1: Quotations & Contracts
│   │   ├── subscription_invoice.py         # Developer 1: Billing engine & invoices
│   │   ├── billing_log.py                  # Developer 1: Billing audit log
│   │   ├── discount_hook.py                # Contract: Shared discount hooks
│   │   ├── payment_hook.py                 # Contract: Shared payment skeleton
│   │   ├── user_management.py              # Developer 2: Users & password complexity
│   │   ├── discount.py                     # Developer 2: Discount & coupon rules
│   │   ├── payment.py                      # Developer 2: Payment reconciliation & wizard
│   │   └── dashboard.py                    # Developer 2: Analytics engine & console
│   ├── views/                              # XML UI views, menus, graph & pivot definitions
│   │   ├── menu_views.xml
│   │   ├── product_views.xml
│   │   ├── subscription_plan_views.xml
│   │   ├── subscription_views.xml
│   │   ├── invoice_views.xml
│   │   ├── billing_log_views.xml
│   │   ├── user_views.xml
│   │   ├── discount_views.xml
│   │   ├── payment_views.xml
│   │   └── dashboard_views.xml
│   ├── security/                           # Roles, ACLs, and record rules
│   │   ├── security.xml                    # Developer 1: Core security categories & groups
│   │   ├── user_security.xml               # Developer 2: Portal customer record rules
│   │   └── ir.model.access.csv             # Full model access rights matrix
│   ├── data/                               # System sequences and scheduled actions
│   │   ├── sequence_data.xml               # Sequence generators (SUB-XXXXX, INV-XXXXX)
│   │   └── cron_data.xml                   # Recurring billing cron job
│   ├── reports/                            # QWeb PDF reports
│   └── tests/                              # Native Odoo TransactionCase test suites
└── tests/                                  # Pure Python standalone verification suite
    ├── run_standalone_verification.py       # Master regression runner (91/91 tests)
    ├── test_user_management_standalone.py  # User & security standalone tests
    ├── test_discount_management_standalone.py # Discount standalone tests
    ├── test_payment_management_standalone.py  # Payment reconciliation standalone tests
    └── test_dashboard_reports_standalone.py   # Dashboard aggregation & benchmark tests
```

---

## 6. Installation & Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Odoo 17.0 or 18.0 Community / Enterprise source code or Docker

### Option A: Running with Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/Drashti-0/odoo_hackathon.git
cd odoo_hackathon

# Checkout Developer 2 branch
git checkout developer-2-operations

# Start Odoo and PostgreSQL containers
docker-compose up -d

# Access Odoo in your browser at http://localhost:8069
```

### Option B: Native Installation
```bash
# Ensure subscription_management is in your Odoo addons path
odoo-bin -c odoo.conf -d brightloop_db -i subscription_management --stop-after-init

# Start Odoo server
odoo-bin -c odoo.conf -d brightloop_db
```

---

## 7. Testing Instructions

### A. Run Complete Standalone Verification Suite (Zero Dependencies)
The standalone suite requires only standard Python and validates all business logic, constraints, security rules, and calculations:

```bash
# Run all 91 tests across all modules
python tests/run_standalone_verification.py -v
```

### B. Run Module-Specific Test Suites
```bash
# 1. User Management & Authentication (17 tests)
python tests/test_user_management_standalone.py -v

# 2. Discount Management (28 tests)
python tests/test_discount_management_standalone.py -v

# 3. Payment Management (16 tests)
python tests/test_payment_management_standalone.py -v

# 4. Dashboard & Financial Reports (16 tests + 5,000 record benchmark)
python tests/test_dashboard_reports_standalone.py -v
```

### C. Run Static Validation
```bash
# 1. Python Syntax Compilation across all files
python -m py_compile subscription_management/**/*.py tests/**/*.py

# 2. XML Syntax Validation across all views
python -c "import glob, xml.etree.ElementTree as ET; [ET.parse(f) for f in glob.glob('subscription_management/**/*.xml', recursive=True)]; print('All XMLs Valid!')"
```

### D. Run Native Odoo Tests (Requires Active Odoo Server & PostgreSQL)
```bash
odoo-bin -c odoo.conf -d brightloop_db --test-enable --stop-after-init -i subscription_management
```

---

## 8. Known Limitations & Technical Notes

1. **Host Environment**: On developer machines lacking a running PostgreSQL daemon or `odoo-bin` executable, native Odoo tests cannot be run directly; the standalone verification suite provides 100% equivalent logical verification.
2. **Payment Gateways**: Stripe, PayPal, and UPI workflows record and reconcile transactions using native state modeling without requiring live external merchant API keys.
3. **Mail Spooler**: Automated emails are captured in Odoo Chatter (`mail.message`), enabling demonstration without an active SMTP relay.

---

## Local Hackathon Demo Data

The demo loader creates five synthetic customers, five subscription services, three
recurring plans, four pending quotations, one active subscription, and one invoice
generated by the subscription billing action. It uses stable Odoo external IDs, so
rerunning it does not duplicate its records. Demo customer email addresses use the
reserved `.test` domain. No payments or payment-success records are created.

With the local Odoo 17 Docker services running and the addon installed in
`brightloop_test_db`, run this from the repository root:

```bash
docker exec -i brightloop_odoo_server \
  odoo shell --config=/etc/odoo/odoo.conf \
  --database=brightloop_test_db --no-http \
  < subscription_management/scripts/load_demo_data.py
```

Open [http://localhost:8069](http://localhost:8069), then use the Brightloop
Subscriptions app:

1. **Products & Plans → Subscription Products**: review the five demo services.
2. **Products & Plans → Subscription Plans**: review monthly, quarterly, and yearly pricing.
3. **Subscriptions → Quotations**: open a pending customer quotation and review its product line.
4. Use **Confirm Order**, then **Activate Subscription** to exercise the lifecycle.
5. **Subscriptions → Contracts & Subscriptions**: check the active status and next billing date.
6. **Billing & Invoices → Recurring Invoices**: inspect the real, unpaid invoice generated for the active Northstar demo subscription.
7. **Dashboard**: review live KPIs, recent activity, upcoming billing, and open the status, growth, invoice, revenue, and plan charts.

The dashboard is available to Subscription Staff and Administrators. Dashboard filters
cover the reporting period, subscription status, billing frequency, invoice status,
payment method, and customer. Revenue counts successful payment transactions only;
unpaid invoices contribute to outstanding balances, not revenue.

## Subscription Renewal & Billing Automation

The recurring-billing job runs automatic renewal checks before expiry processing and
invoice generation. Expired contracts renew only when their plan permits renewal;
the resulting invoice remains unpaid until a real payment is recorded through the
existing payment flow. Renewal attempts and invoice failures are written to the
billing audit log, and renewal milestones are recorded in the subscription chatter.
Invoice generation remains protected by the unique subscription/billing-period
constraint and per-subscription transaction savepoints.

A separate daily job creates or refreshes one Odoo activity per active subscription
due within seven days or already overdue. The subscription search provides Due Today,
Due Within 3 Days, Due Within 7 Days, Overdue Billing, Renewal Due, and Expiring
Within 7 Days filters.

To inspect or run the jobs manually, open **Settings → Technical → Automation →
Scheduled Actions** as an administrator. The key jobs are **Intelligent Automated
Recurring Billing Engine** (including renewal processing), **Contract Expiry &
Auto-Close Monitor**, and **Upcoming Billing Notifications**.

For a local renewal walkthrough, create a synthetic quotation for a demo customer
on a plan with renewal enabled, confirm and activate it, and set its expiry and next
billing dates to today. Run **Intelligent Automated Recurring Billing Engine**
manually. The subscription should remain active with a future expiry/billing date,
and its invoice should be confirmed but unpaid. Run the job again to verify no second
invoice is created for that billing period. Use the subscription chatter for renewal
milestones and **Billing Engine Audit Logs** for invoice generation and failed
renewal attempts.

For a fresh local database, install the addon and assign the Odoo Administrator /
Subscription Administrator access, then run the loader against that database by
replacing `brightloop_test_db` in the command. The loader commits only after all
records and lifecycle actions succeed. Do not run it against a production database.

## Customer Subscription Portal

The customer portal extends Odoo 17's portal framework. Sign in at
`http://localhost:8069/web/login`, then open `http://localhost:8069/my` to find
My Subscriptions, My Quotations, and Subscription Invoices. Subscription details
show the plan, product lines, dates, status, recurring amount, and invoice history.
Customers can download their own invoice PDF and submit cancellation or renewal
requests for staff review; requests do not directly change contract status.

Portal pages require an authenticated Odoo portal user linked to the subscription's
customer contact. Every route filters the requested subscription or invoice by that
partner, and portal record rules apply to the related subscription and invoice lines.
Billing audit logs are not exposed to portal users. For a local demo, create a portal
user for a synthetic customer with the **Portal Customer** group and associate
subscriptions with that same contact. Do not use production customer data.

To load dashboard changes on the existing local database, update the addon and
restart Odoo:

```bash
docker exec brightloop_odoo_server \
  odoo --config=/etc/odoo/odoo.conf \
  --database=brightloop_test_db \
  --update=subscription_management --stop-after-init
docker restart brightloop_odoo_server
```
