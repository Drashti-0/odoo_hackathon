# Brightloop Subscription Management System

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Odoo%2017%2F18-blue.svg)]()
[![Team](https://img.shields.io/badge/team-AuraMinds-orange.svg)]()
[![License](https://img.shields.io/badge/license-LGPL--3-green.svg)]()

Enterprise Subscription Management System built for Brightloop Software as part of the Odoo Hackathon.

## Team - AuraMinds
- **Dhruti Viradiya** (Developer 1 - Core Architecture, Modules 1–4)
- **Drashti Bhanderi** (Developer 2 - Modules 5–8)

---

## Assigned Modules & Separation of Concerns

### Developer 1 (Branch: `developer-1-core`):
1. **Product & Product Variant Management:**
   - Multi-brand pricing engine with mandatory **Odoo brand variant surcharge (+560.0)**.
2. **Subscription Plan Management:**
   - Daily, Weekly, Monthly, and Yearly cadence configuration.
   - Comprehensive validations, grace periods, pause, renewal, and auto-close policies.
3. **Quotation & Subscription Management:**
   - Predefined quotation templates.
   - Strict lifecycle state transitions: `Draft` → `Quotation` → `Confirmed` → `Active` → `Closed`.
   - Pause & resume with date shift, renewal rollover, early closure permissions, and audit chatter.
4. **Invoice & Intelligent Automated Billing Engine:**
   - Automated recurring billing via Scheduled Action (`ir.cron`).
   - Catch-up billing for past due cycles without leaving gaps.
   - Idempotency defense preventing duplicate invoices for the same subscription period.
   - Row-level database locks (`FOR UPDATE SKIP LOCKED`) and transactional savepoints for safe concurrency and fault isolation.
   - Complete billing audit trail (`subscription.billing.log`).

### Developer 2 (Collaborator):
5. User Management & Authentication (Portal, Roles, Security)
6. Discount Management (Coupons, Promos, Vouchers)
7. Payment Management (Gateways, Settlement, Reconciliation)
8. Dashboard & Financial Reports (MRR, ARR, Churn, KPI Analytics)

*See [`INTEGRATION_CONTRACT.md`](INTEGRATION_CONTRACT.md) for complete data schemas, APIs, and integration hooks.*

---

## Quick Start & Verification

### Running Standalone Verification Tests
Verify all 8 test suites directly (zero external dependencies required):
```bash
python3 tests/run_standalone_verification.py -v
```

### Installation in Odoo
See [`INSTALLATION.md`](INSTALLATION.md) for full deployment instructions, configuration file setup, and Odoo native test execution.
