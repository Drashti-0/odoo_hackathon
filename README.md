# Brightloop Subscription Management

<<<<<<< HEAD
[![Platform](https://img.shields.io/badge/Odoo-17.0-714B67?logo=odoo)](https://www.odoo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql)](https://www.postgresql.org)
[![License](https://img.shields.io/badge/License-LGPL--3-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Standalone%20mock%20tests-93%20passed-brightgreen)](tests/run_standalone_verification.py)
=======
Brightloop is an Odoo 17 addon for managing software subscription products, recurring plans, quotations, subscription contracts, subscription invoices, payments, discounts, and internal operational dashboards.
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

The addon is named `subscription_management` and is in `subscription_management/`. Its Odoo manifest depends on `base`, `mail`, `product`, `account`, and `portal`. The local Docker setup mounts the addon's directory into the Odoo container.

## What is implemented

<<<<<<< HEAD
The **Brightloop Subscription Management System** is an Odoo 17 addon and standalone browser demo developed by **Team AuraMinds** for the Odoo Hackathon. The addon contains subscription lifecycle, recurring billing, discounts, manual payment recording, and reporting code. The browser demo uses local sample data and simulated authentication; it is not connected to Odoo. Live Odoo installation and behavior have not been verified in this environment.
=======
- Subscription products and product variants with brand and variant pricing fields.
- Daily, weekly, monthly, and yearly billing plans with availability and lifecycle policy.
- Quotations and contract lifecycle states: draft, quotation, confirmed, active, paused, closed, and expired.
- Recurring invoices, billing-period duplicate protection, scheduled billing jobs, and billing audit logs.
- Discount rules and invoice/subscription discount hooks.
- Payment transaction records and invoice payment/residual tracking. Payment-method labels include card, bank transfer, Stripe, PayPal, and cash/cheque; a live payment-provider integration was not verified.
- Staff, administrator, and portal roles; customer-scoped portal pages for subscriptions, quotations, plans, invoices, and billing history.
- Odoo backend list, form, search, graph, and pivot views; an invoice QWeb report.
- A database-backed internal dashboard and synthetic, repeatable demo data loader.
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

See [docs/PROJECT_ARCHITECTURE.md](docs/PROJECT_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for implementation details.

## Run locally

The repository includes Docker Compose for Odoo 17 and PostgreSQL. Before exposing this setup beyond a local development machine, replace development-only configuration with private local settings and rotate any default administration secrets. Do not commit `.env` files or credentials.

1. Install Docker Desktop with Docker Compose.
2. From the repository root, create `.env` from `.env.example` only if you do not already have a private local `.env`, then replace development values with local-only values:

<<<<<<< HEAD
### Project Objectives
- Automate contract state transitions: `Draft` $\rightarrow$ `Quotation` $\rightarrow$ `Confirmed` $\rightarrow$ `Active` $\rightarrow$ `Closed`.
- Deliver an autonomous, catch-up-capable recurring billing cron engine that leaves zero billing gaps and avoids duplicate charges.
- Implement an idempotent promotional discount engine with boundary clamping to prevent negative invoice balances.
- Reconcile manually recorded payments and prevent overpayments. Payment-method labels do not connect to payment gateways.
- Configure customer record rules through Odoo access controls; the standalone demo's role filtering is only a UI simulation.
- Provide sub-second executive analytics using database-level SQL aggregation (`read_group`).
=======
   ```bash
   test -f .env || cp .env.example .env
   ```
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

3. Start the services:

   ```bash
   docker compose up -d
   docker compose ps
   ```

<<<<<<< HEAD
| Feature Area | Key Capabilities |
|---|---|
| **Catalog & Surcharges** | Multi-brand product variants with mandatory Odoo brand variant surcharge (+560.0). |
| **Flexible Plan Cadences** | Daily, Weekly, Monthly, and Yearly intervals; grace periods, renewal policies, and early closure controls. |
| **Quotation & Contracts** | Predefined quotation templates, digital quotation delivery, sequence generation (`SUB-XXXXX`), pause/resume with billing date adjustment. |
| **Automated Billing Engine** | Cron-driven recurring billing with catch-up for past cycles, transactional savepoints (`cr.savepoint()`), and billing audit logs. |
| **User & Portal Security** | Multi-role security (Admin, Staff, Portal Customer), RFC email validation, password complexity enforcement, enumeration-safe password resets. |
| **Discount Management** | Fixed and percentage coupons, subtotal clamping, minimum purchase/quantity thresholds, start/end dates, global usage caps. |
| **Payment Recording** | Manual transaction records, overpayment validation, residual balances, and payment-state synchronization. No Stripe, PayPal, bank, or card gateway is connected. |
| **Executive Dashboard** | 5 core KPIs (Active Contracts, Revenue Received, Receivables, Overdue Invoices, Confirmed Payments), MRR/ARR metrics, monthly revenue trends, and pivot analytics. |
=======
4. Open [http://localhost:8069](http://localhost:8069). Create/select a development database as needed, sign in with the locally configured administrator, and install **Brightloop Subscription Management** from Apps. The addon is mounted at `/mnt/extra-addons/subscription_management`.
5. Assign the appropriate Subscription Administrator or Officer / Staff group to internal users.
6. To load synthetic demo records in a development database only, see [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md).
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

Detailed installation, upgrade, demo data, and stop commands are in [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md).

## Verification snapshot

<<<<<<< HEAD
- **Framework**: Odoo 17.0 addon; live installation is pending.
- **Backend Language**: Python 3.10+ (tested through Python 3.14).
- **ORM**: Odoo Object-Relational Mapping (PostgreSQL driver with transactional savepoints).
- **Database**: PostgreSQL 14+ (relational schema, composite indices, foreign keys).
- **Frontend / UI**: Odoo Web Client (XML Form, Tree, Search, Graph, Pivot, Web Ribbons, and Badges).
- **Automation**: Odoo Scheduled Actions (`ir.cron`).
- **Security**: Access Control Lists (`ir.model.access.csv`) and Record Rules (`ir.rule`).
=======
At the 2026-10-31 final verification snapshot, the standalone regression runner passed **93 tests** and all **16 addon XML files** parsed. A previously recorded native Odoo suite run against the already-populated local database reported **14 failures and 6 errors out of 132 tests**; see [docs/TESTING_REPORT.md](docs/TESTING_REPORT.md). Do not interpret that database run as a clean isolated test pass.
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

Actual demo evidence and known verification gaps are recorded in [docs/FINAL_PROJECT_REPORT.md](docs/FINAL_PROJECT_REPORT.md). Screenshot capture/export limitations are documented in [docs/screenshots/README.md](docs/screenshots/README.md).

## Project and submission documents

<<<<<<< HEAD
```text
odoo_hackathon/
├── README.md                               # Project overview and quickstart guide
├── TESTING_REPORT.md                       # Current test evidence and limitations
├── INTEGRATION_CONTRACT.md                 # Shared architectural interface contract
├── USER_MANAGEMENT.md                      # Module 1 documentation
├── DISCOUNT_MANAGEMENT.md                  # Module 2 documentation
├── PAYMENT_MANAGEMENT.md                   # Module 3 documentation
├── DASHBOARD_REPORTS.md                    # Module 4 documentation
├── DEMO_GUIDE.md                           # 10-step evaluator demonstration script
├── odoo.conf                               # Odoo server runtime configuration
├── docker-compose.yml                      # Containerized Odoo & PostgreSQL stack
├── demo_portal/                             # Standalone local-data browser simulation
│   ├── index.html
│   ├── assets/app.js
│   └── DEMO_VIDEO_SCRIPT.md
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
    ├── run_standalone_verification.py       # Standalone mock regression runner
    ├── test_user_management_standalone.py  # User & security standalone tests
    ├── test_discount_management_standalone.py # Discount standalone tests
    ├── test_payment_management_standalone.py  # Payment reconciliation standalone tests
    └── test_dashboard_reports_standalone.py   # Dashboard aggregation & benchmark tests
```
=======
- [Project architecture](docs/PROJECT_ARCHITECTURE.md)
- [Database design](docs/DATABASE_DESIGN.md)
- [User guide](docs/USER_GUIDE.md)
- [Installation guide](docs/INSTALLATION_GUIDE.md)
- [Testing report](docs/TESTING_REPORT.md)
- [Final project report](docs/FINAL_PROJECT_REPORT.md)
- [Hackathon presentation content](docs/PRESENTATION_CONTENT.md)
- [Final hackathon demonstration script](docs/FINAL_HACKATHON_DEMO.md)
- [Judge Q&A](docs/JUDGE_QA.md)
- [Integration contract](INTEGRATION_CONTRACT.md)
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c

## License and team

<<<<<<< HEAD
## 6. Installation & Setup Instructions

### Prerequisites
- Docker Desktop with Docker Compose v2 (for Odoo deployment)
- A private `.env` file with unique values for both required passwords
- No Odoo server or database is bundled into the standalone browser demo

### Option A: Running with Docker (Recommended)
```powershell
Copy-Item .env.example .env
notepad .env
# Set non-empty, unique POSTGRES_PASSWORD and ODOO_ADMIN_PASSWORD values.
docker compose up -d
docker compose ps
```

The Compose file binds Odoo to `127.0.0.1` and does not publish PostgreSQL. Do not share `.env` or terminal output containing resolved configuration.

Open `http://localhost:8069/web/database/manager`, create a database, and use the `ODOO_ADMIN_PASSWORD` value from your private `.env` as the master password. Then sign in as the database administrator, update the Apps list, find **Brightloop Subscription Management**, and install it. These deployment steps still require Docker and live Odoo verification; neither was available during the latest audit.

To run the standalone demo instead, open `demo_portal\index.html` in a browser. Demo accounts are shown on its sign-in screen; this demo does not use Odoo.

---

## 7. Testing Instructions

### A. Run Standalone Mock Verification
This dependency-light suite exercises standalone test doubles; it does not import or execute the Odoo addon and is not proof of Odoo ORM, access-rule, or database behavior.

```bash
# Run all standalone mock tests
python tests/run_standalone_verification.py -v
```

### B. Run Module-Specific Test Suites
```bash
# 1. User Management & Authentication (18 tests)
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

### D. Run Native Odoo Tests (Requires Odoo 17 and PostgreSQL)
```bash
odoo-bin -c odoo.conf -d brightloop_db --test-enable --stop-after-init -i subscription_management
```

---

## 8. Known Limitations & Technical Notes

1. **Live Odoo**: The addon and its TransactionCase tests have not been run against an Odoo 17 server/database in the audited environment.
2. **Accounting and Payments**: `subscription.invoice` is a custom addon model, not an `account.move`. Payment records are manual state entries; payment-method choices are labels only and do not process real payments.
3. **Standalone Demo**: Authentication, subscriptions, invoices, discounts, payments, and reporting in `demo_portal/` are local browser simulations. UI role filters are not a security boundary.
4. **External Assets**: The standalone page loads styling, icons, and charts from CDNs; internet access is required for those assets. Tailwind's CDN build reports a production-use warning.

---

## Local Hackathon Demo Data

The Odoo demo loader is code for creating five synthetic customers, five subscription services, three
recurring plans, four pending quotations, one active subscription, and one invoice
generated by the subscription billing action. The loader has not been run in a live database. It uses stable Odoo external IDs, so
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
6. **Billing & Invoices → Recurring Invoices**: inspect the custom-model invoice generated for the active Northstar demo subscription; it is not an `account.move`.
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
=======
The module manifest declares LGPL-3. The project is by Team AuraMinds. See the integration contract for ownership/interface details.
>>>>>>> c5bd8016b9cc17e6a137062a322f0abffacef69c
