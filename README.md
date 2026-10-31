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

## 9. Documentation Index

- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [System Architecture & Mermaid Diagrams](docs/SYSTEM_ARCHITECTURE.md)
- [Database Models & Reference Table](docs/DATABASE_MODELS.md)
- [Module-Wise Technical Documentation](docs/MODULE_DOCUMENTATION.md)
- [Security & Access Control Guide](docs/SECURITY_DOCUMENTATION.md)
- [Test Execution & Verification Report](docs/TESTING_REPORT.md)
- [Developer 2 Contribution Report](docs/DEVELOPER_2_CONTRIBUTION.md)
- [Final Submission Checklist](docs/SUBMISSION_CHECKLIST.md)
- [10-Step Live Demo Script](DEMO_GUIDE.md)
