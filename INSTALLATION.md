# Brightloop Subscription Management System - Installation & Deployment Guide

> **Current setup:** This earlier manual guide contains historical Odoo-version/path assumptions. Use the repository-specific [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md) and [README.md](README.md) for the current Odoo 17 Docker commands and addon mount.

**Target ERP Platform:** Odoo 17.0 / 18.0 (Community & Enterprise)  
**Module Name:** `subscription_management`  
**Team:** AuraMinds  
**Developer 1 (Core Architect):** Dhruti Viradiya  
**Git Branch:** `developer-1-core`  

---

## 1. System Requirements & Prerequisites

- **Python:** 3.10, 3.11, or 3.12 (standard for Odoo 17/18)
- **Database:** PostgreSQL 12+ (standard Odoo requirement)
- **Odoo Base Modules:** `base`, `mail`, `product` (included in all standard Odoo distributions)

---

## 2. Installing the Module in Odoo

### Step 2.1: Add to Odoo Addons Path
Add the hackathon repository directory to your `odoo.conf` configuration file:
```ini
[options]
addons_path = /path/to/odoo/addons,/Users/dhrutiviradiya/Odoo_hacthon/odoo_hackathon
```

### Step 2.2: Install via Command Line
Run the Odoo server with the `-i` (install) flag targeting your database:
```bash
odoo-bin -c /path/to/odoo.conf -d brightloop_db -i subscription_management
```

### Step 2.3: Install via Odoo Web Interface (Apps)
1. Log into your Odoo instance as Administrator.
2. Enable Developer Mode via **Settings → Developer Tools → Activate Developer Mode**.
3. Navigate to **Apps → Update Apps List**.
4. Search for `Brightloop Subscription Management` or `subscription_management`.
5. Click **Activate / Install**.

---

## 3. Upgrading the Module

Whenever new features or schema modifications are pulled from `developer-1-core`:
```bash
odoo-bin -c /path/to/odoo.conf -d brightloop_db -u subscription_management --stop-after-init
```

---

## 4. Running the Test Suites

### Option A: Standalone Verification Runner (Instant Verification)
We provide a standalone test suite that verifies all pricing formulas, state transitions, constraints, recurring billing calculations, catch-up logic, and idempotency without requiring an active PostgreSQL or Odoo daemon:

```bash
cd /Users/dhrutiviradiya/Odoo_hacthon/odoo_hackathon
python3 tests/run_standalone_verification.py -v
```

**Expected Output:**
```
test_01_product_and_odoo_variant_surcharge ... ok
test_02_plan_validation_and_cadence_calculations ... ok
test_03_subscription_lifecycle_and_state_machine ... ok
test_04_automated_billing_engine_and_idempotency ... ok
test_05_catchup_billing_engine ... ok
test_06_paused_and_expired_subscription_safety ... ok
test_07_renewal_and_early_close_policies ... ok
test_08_discounts_and_multi_tax_computations ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.001s

OK
```

### Option B: Odoo Native Test Runner
To run the standard Odoo `TransactionCase` tests within an active Odoo test database:
```bash
odoo-bin -c /path/to/odoo.conf -d test_db -i subscription_management --test-enable --stop-after-init --log-level=test
```

---

## 5. Automated Recurring Billing Scheduled Action (Cron)

The module ships with an automated recurring billing Scheduled Action:
- **XML ID:** `subscription_management.ir_cron_subscription_recurring_billing`
- **Model:** `subscription.subscription`
- **Method:** `cron_recurring_billing()`
- **Default Frequency:** Every 24 hours (configurable to hourly for high-frequency billing)

### Manual Billing Trigger:
Administrators and staff can also trigger recurring billing directly from any active subscription using the **"Generate Next Invoice"** button on the subscription form view.
