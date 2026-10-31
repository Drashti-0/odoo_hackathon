# Module 1: User Management & Authentication

**Brightloop Software – Subscription Management System (Odoo 17/18)**  
**Developer 2:** Drashti Bhanderi  
**Branch:** `developer-2-operations`  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Overview

Module 1 delivers enterprise-grade user management, authentication, role-based access control (RBAC), and customer data isolation natively within Odoo 17/18.

### Key Components
1. **Password Policy Engine (`models/user_management.py`):**
   - Enforces length > 8 characters (at least 9 characters).
   - Enforces presence of at least 1 uppercase letter (`A-Z`).
   - Enforces presence of at least 1 lowercase letter (`a-z`).
   - Enforces presence of at least 1 special character (`!@#$%^&*()_+-=[]{}|;:'",.<>?/~`\\`).
   - Natively integrates with Odoo's PBKDF2/crypt password hashing (no plaintext password storage).

2. **Case-Insensitive Email Uniqueness (`models/user_management.py`):**
   - Extends `res.users` and `res.partner` via `@api.constrains('email')`.
   - Normalizes email (`lower().strip()`) and validates standard RFC format.
   - Prevents duplicate registrations across user and contact accounts regardless of casing.

3. **Three-Tier Role Hierarchy & Privilege Escalation Defense:**
   - **Administrator (`group_subscription_manager`):** Full control over plans, pricing, cron, and user roles.
   - **Internal Staff (`group_subscription_user`):** Operational management of subscriptions and invoices.
   - **Customer (`group_subscription_portal`):** Restricted access strictly isolated to own records.
   - **Privilege Escalation Protection:** Python constraint in `res.users` ensures that **only Administrators** can create or assign Internal Staff or Admin roles. Customer attempts to elevate privileges via signup, forms, or direct RPC calls raise an immediate `AccessError`.

4. **Customer Data Isolation (Record Rules in `security/user_security.xml`):**
   - Portal customers are constrained by server-level record rules:
     - `subscription.subscription`: `[('partner_id', '=', user.partner_id.id)]`
     - `subscription.line`: `[('subscription_id.partner_id', '=', user.partner_id.id)]`
     - `subscription.invoice`: `[('partner_id', '=', user.partner_id.id)]`
     - `subscription.invoice.line`: `[('invoice_id.partner_id', '=', user.partner_id.id)]`
     - `subscription.payment`: `[('partner_id', '=', user.partner_id.id)]`
   - Internal billing engine audit logs (`subscription.billing.log`) have zero portal access.
   - Direct record reading by ID, URL manipulation, or search operations for another customer's record raises an `AccessError`.

5. **Secure Customer Registration & Anti-Enumeration Password Reset:**
   - Customer self-registration API `register_portal_customer(name, email, password, company_name)`.
   - Registration Wizard (`subscription.customer.register.wizard`) under Configuration for staff.
   - Password Reset API `request_password_reset(email)`:
     - Triggers native Odoo password reset link.
     - Anti-enumeration defense: returns identical response regardless of whether an email exists, preventing email harvesting attacks.

6. **Web / JSON API Controller (`controllers/portal_auth.py`):**
   - `/subscription/api/register`: Secure public registration endpoint.
   - `/subscription/api/reset-password`: Anti-enumeration password reset endpoint.
   - `/subscription/my/contracts`: Authenticated portal contracts listing.
   - `/subscription/my/invoices`: Authenticated portal invoices listing.

---

## 2. Test Verification Matrix

All 17 requirements are verified via automated test suites:

| # | Test Name | Target Behavior | Result |
|---|---|---|---|
| 1 | `test_01_successful_customer_registration` | Valid registration creates partner + portal user | PASSED |
| 2 | `test_02_duplicate_email_rejection` | Duplicate email rejected with ValidationError | PASSED |
| 3 | `test_03_case_insensitive_duplicate_email_rejection` | Mixed/upper case duplicate rejected | PASSED |
| 4 | `test_04_invalid_email_rejection` | Malformed email rejected | PASSED |
| 5 | `test_05_password_shorter_than_required_length` | Passwords <= 8 chars rejected | PASSED |
| 6 | `test_06_missing_uppercase_character` | Missing [A-Z] rejected | PASSED |
| 7 | `test_07_missing_lowercase_character` | Missing [a-z] rejected | PASSED |
| 8 | `test_08_missing_special_character` | Missing special char rejected | PASSED |
| 9 | `test_09_successful_password_reset_flow` | Dispatches reset & defends against enumeration | PASSED |
| 10 | `test_10_admin_permissions` | Admin has full plan & user management | PASSED |
| 11 | `test_11_internal_staff_permissions` | Staff has operational access | PASSED |
| 12 | `test_12_customer_permissions` | Customer limited to portal role | PASSED |
| 13 | `test_13_customer_cannot_create_staff` | Privilege escalation attempt raises AccessError | PASSED |
| 14 | `test_14_customer_cannot_access_another_customer_subscription` | Search returns only own subscriptions | PASSED |
| 15 | `test_15_customer_cannot_access_another_customer_invoice` | Search returns only own invoices | PASSED |
| 16 | `test_16_direct_record_access_restrictions` | Direct read on other customer's ID raises AccessError | PASSED |
| 17 | `test_17_unauthorized_rpc_access_restrictions` | Direct RPC write on other records blocked | PASSED |

### Execution Commands:
- **Standalone Verification Runner:**
  ```bash
  python tests/run_standalone_verification.py -v
  ```
- **Dedicated User Management Standalone Suite:**
  ```bash
  python tests/test_user_management_standalone.py -v
  ```
- **Odoo Native Test Runner:**
  ```bash
  odoo-bin -c /path/to/odoo.conf -d test_db -i subscription_management --test-enable --test-tags=subscription_management -stop-after-init
  ```
