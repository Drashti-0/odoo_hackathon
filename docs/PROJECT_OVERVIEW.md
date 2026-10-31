# Project Overview
## Brightloop Subscription Management System

> **Evidence note:** This is the original product vision/overview, not a verification report. Performance, end-to-end, gateway, and security guarantees below are not independently certified by the final run. See [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md), [TESTING_REPORT.md](TESTING_REPORT.md), and [SECURITY_DOCUMENTATION.md](SECURITY_DOCUMENTATION.md) for current evidence and limitations.

**Project:** Subscription Management System – Brightloop Software  
**Team:** AuraMinds  
**Target Version:** Odoo 17.0 / 18.0  
**Branch:** `developer-2-operations`  

---

## 1. Executive Summary

The **Brightloop Subscription Management System** is a purpose-built enterprise Odoo application designed to automate the recurring revenue lifecycle for subscription-based businesses. Developed collaboratively by Team AuraMinds, it unifies product catalog configuration, quotation generation, automated recurring billing, discount coupon redemption, multi-method payment reconciliation, and executive business analytics into a cohesive, secure platform.

---

## 2. Industry Context & Problem Statement

Subscription and SaaS business models require fundamentally different operations than traditional one-off product sales:
- **Recurring Invoicing**: Customers expect predictable, timely invoices generated at set cadences (Daily, Weekly, Monthly, Yearly).
- **Grace Periods & Surcharges**: Certain products or brands carry mandatory pricing adjustments (e.g. Odoo brand +$560 surcharge) that must be enforced consistently.
- **Contract Lifecycle**: Subscriptions must be confirmed, activated, paused, resumed, renewed, or terminated with accurate billing date shifts and audit trails.
- **Multi-Method Settlements**: Invoices are frequently paid in installments or across diverse channels (Credit Card, Wire Transfer, UPI, Stripe, PayPal).
- **Data Isolation**: Multi-tenant customer portals must isolate each customer's data so that competitors or outside parties never view unauthorized contracts or invoices.
- **Real-Time Financial Intelligence**: SaaS executives need immediate metrics like Monthly Recurring Revenue (MRR), Annual Recurring Revenue (ARR), and overdue receivables without slow spreadsheet consolidation.

---

## 3. Project Goals & Objectives

1. **Autonomous Billing**: Eliminate manual billing tasks through a background cron engine that automatically generates recurring invoices and catches up on missed cycles.
2. **Defensive Financial Integrity**: Prevent revenue loss through ORM-level constraints blocking zero/negative payments, overpayments, expired coupons, and negative invoice totals.
3. **Multi-Role Security**: Enforce least-privilege security between Subscription Administrators, Internal Staff, and Portal Customers on the server side.
4. **Sub-Second Analytics**: Deliver real-time executive dashboard KPIs using PostgreSQL SQL aggregation (`read_group`), responding in under 0.05 seconds.
5. **Zero-Conflict Engineering**: Maintain strict separation of concerns between Developer 1 and Developer 2 using Odoo inheritance and ratified integration contracts.

---

## 4. Main User Roles & Personas

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Security Hierarchy                     │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
┌───────────────────────────────┐       ┌───────────────────────────────┐
│  Subscription Administrator   │       │         Internal Staff        │
│ (`group_subscription_manager`)│       │  (`group_subscription_user`)  │
├───────────────────────────────┤       ├───────────────────────────────┤
│ • Plan & Pricing Setup        │       │ • Quotation Creation          │
│ • Discount Rule Management    │       │ • Contract Activation & Pause │
│ • Staff User Management       │       │ • Invoice Generation          │
│ • Cron Automation Config      │       │ • Payment Recording & Settle  │
│ • Full Financial Reports      │       │ • Operational Dashboard       │
└───────────────────────────────┘       └───────────────────────────────┘
                                                        ▲
                                                        │ (Isolates from)
                                        ┌───────────────┴───────────────┐
                                        │        Portal Customer        │
                                        │ (`group_subscription_portal`) │
                                        ├───────────────────────────────┤
                                        │ • Self-Service Registration   │
                                        │ • View Own Quotations         │
                                        │ • View Own Invoices & Receipts│
                                        │ • Strictly Blocked from Admin │
                                        └───────────────────────────────┘
```

1. **Subscription Administrator (`group_subscription_manager`)**:
   - Holds full administrative authority over the system.
   - Creates and edits plans, quotation templates, automated cron schedules, and discount rules.
   - Manages internal staff accounts and reviews global financial reports.
2. **Subscription Officer / Internal Staff (`group_subscription_user`)**:
   - Manages day-to-day subscription operations.
   - Creates quotations, confirms and activates contracts, registers incoming payments, and views operational dashboards.
   - Cannot modify administrative configurations or discount rules.
3. **Subscription Customer (`group_subscription_portal`)**:
   - External B2B or B2C subscriber.
   - Can view only contracts, invoices, and payments linked to their specific partner record.
   - Blocked from company-wide metrics, internal audit logs, and administrative controls.

---

## 5. Technology Stack & Environment

- **Core Application Platform**: Odoo 17.0 / 18.0 (Community & Enterprise).
- **Backend Language**: Python 3.10+ (tested through 3.14).
- **Database Engine**: PostgreSQL 14+.
- **Object-Relational Mapping**: Odoo ORM (Active Record pattern, computed fields, constrains, triggers).
- **Frontend / Client**: Odoo Web Framework (XML Form, Tree, Search, Graph, Pivot, Web Ribbons).
- **Asynchronous Execution**: Odoo Scheduled Actions (`ir.cron`) with transactional savepoints (`cr.savepoint()`).
- **Security Subsystem**: Odoo Access Control Lists (`ir.model.access.csv`) and Row-Level Record Rules (`ir.rule`).
