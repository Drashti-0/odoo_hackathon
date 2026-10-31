# Security & Access Control Documentation
## Brightloop Subscription Management System

**Project:** Subscription Management System – Brightloop Software  
**Team:** AuraMinds  
**Target Version:** Odoo 17.0 / 18.0  
**Branch:** `developer-2-operations`  

---

## 1. Security Architecture & Principles

The **Brightloop Subscription Management System** enforces defense-in-depth security across three distinct layers:
1. **Model-Level Permissions (Access Control Lists - ACLs)**: Governs which security groups can Create, Read, Write, or Unlink records in each table.
2. **Row-Level Security (Record Rules)**: Injects dynamic SQL filtering (`WHERE partner_id = ?`) to isolate customers so they can only see their own records.
3. **Server-Side Method Protection**: Python methods inspect `self.env.user.has_group()` and raise `AccessError` before executing sensitive business logic (e.g. confirming payments, viewing global financial dashboards, modifying discount rules).

---

## 2. Security Roles & Group Definitions

All security groups are defined in `subscription_management/security/security.xml`:

| Group Technical XML ID | Display Name | Inherits | Description & Intended Role |
|---|---|---|---|
| `group_subscription_portal` | Subscription Portal Customer | `base.group_portal` | External enterprise customers. Limited strictly to viewing their own quotations, subscriptions, invoices, and payments. |
| `group_subscription_user` | Subscription Officer / Internal Staff | `base.group_user` | Internal operational staff. Can manage contracts, quotations, invoices, and payments, but cannot modify plans, discounts, or cron configurations. |
| `group_subscription_manager` | Subscription Administrator | `group_subscription_user` | Full operational and system configuration authority over pricing plans, discount rules, automated crons, staff users, and financial reports. |

---

## 3. Access Control Lists Matrix (`ir.model.access.csv`)

The model access matrix located in `subscription_management/security/ir.model.access.csv` defines CRUD permissions:

| Model ID | Model Name | Group XML ID | Read | Write | Create | Unlink |
|---|---|---|:---:|:---:|:---:|:---:|
| `model_subscription_plan` | Subscription Plan | `group_subscription_user` | 1 | 0 | 0 | 0 |
| `model_subscription_plan` | Subscription Plan | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_subscription` | Subscription Contract | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_subscription` | Subscription Contract | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_subscription` | Subscription Contract | `group_subscription_portal` | 1 | 0 | 0 | 0 |
| `model_subscription_line` | Subscription Line | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_line` | Subscription Line | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_line` | Subscription Line | `group_subscription_portal` | 1 | 0 | 0 | 0 |
| `model_subscription_invoice` | Recurring Invoice | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_invoice` | Recurring Invoice | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_invoice` | Recurring Invoice | `group_subscription_portal` | 1 | 0 | 0 | 0 |
| `model_subscription_invoice_line` | Invoice Line | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_invoice_line` | Invoice Line | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_invoice_line` | Invoice Line | `group_subscription_portal` | 1 | 0 | 0 | 0 |
| `model_subscription_billing_log` | Billing Engine Audit Log | `group_subscription_user` | 1 | 0 | 0 | 0 |
| `model_subscription_billing_log` | Billing Engine Audit Log | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_discount` | Promotional Discount Rule | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_discount` | Promotional Discount Rule | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_payment` | Payment Transaction | `group_subscription_user` | 1 | 1 | 1 | 0 |
| `model_subscription_payment` | Payment Transaction | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_customer_register_wizard` | Customer Register Wizard | `group_subscription_user` | 1 | 1 | 1 | 1 |
| `model_subscription_customer_register_wizard` | Customer Register Wizard | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_payment_register_wizard` | Payment Register Wizard | `group_subscription_user` | 1 | 1 | 1 | 1 |
| `model_subscription_payment_register_wizard` | Payment Register Wizard | `group_subscription_manager` | 1 | 1 | 1 | 1 |
| `model_subscription_dashboard_console` | Dashboard Console | `group_subscription_user` | 1 | 1 | 1 | 1 |
| `model_subscription_dashboard_console` | Dashboard Console | `group_subscription_manager` | 1 | 1 | 1 | 1 |

> [!NOTE]
> `group_subscription_portal` is explicitly omitted from `model_subscription_payment`, `model_subscription_discount`, `model_subscription_billing_log`, and `model_subscription_dashboard_console`, completely barring portal customers from accessing these models.

---

## 4. Multi-Tenant Record Isolation Rules (`user_security.xml`)

Located in `subscription_management/security/user_security.xml`:

### 1. Subscription Contract Customer Rule
```xml
<record id="subscription_portal_rule" model="ir.rule">
    <field name="name">Portal Customer: Own Subscriptions Only</field>
    <field name="model_id" ref="model_subscription_subscription"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_subscription_portal'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

### 2. Invoice Customer Rule
```xml
<record id="subscription_invoice_portal_rule" model="ir.rule">
    <field name="name">Portal Customer: Own Invoices Only</field>
    <field name="model_id" ref="model_subscription_invoice"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_subscription_portal'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

### 3. Payment Customer Rule
```xml
<record id="subscription_payment_portal_rule" model="ir.rule">
    <field name="name">Portal Customer: Own Payments Only</field>
    <field name="model_id" ref="model_subscription_payment"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_subscription_portal'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

---

## 5. Password Security & Cryptography

1. **Complexity Validation (`validate_password_complexity`)**:
   - Minimum length: $> 8$ characters (enforces 9 or more).
   - Uppercase requirement: At least 1 character in `A-Z`.
   - Lowercase requirement: At least 1 character in `a-z`.
   - Numeric requirement: At least 1 digit in `0-9`.
   - Special symbol requirement: At least 1 character in `!@#$%^&*(),.?":{}|<>_-`.
2. **Native Cryptographic Storage**:
   - Plaintext passwords are never persisted.
   - Odoo's native `_set_password()` hashes passwords using salted PBKDF2-SHA512 or bcrypt algorithms before writing to the PostgreSQL `res_users` table.
3. **Anti-Enumeration Password Reset Flow**:
   - In `request_password_reset()`, the method returns a generic success message regardless of whether the email exists in the database.
   - Prevents attackers from harvesting valid customer or employee email addresses.

---

## 6. Server-Side Method Access Enforcement

To prevent malicious RPC tampering via XML-RPC or JSON-RPC, sensitive actions enforce security checks in Python:

```python
# Payment Settlement Protection
def action_confirm_payment(self):
    is_staff_or_admin = (
        self.env.user.has_group('subscription_management.group_subscription_user')
        or self.env.user.has_group('subscription_management.group_subscription_manager')
        or self.env.is_superuser()
    )
    if not is_staff_or_admin:
        raise AccessError(_("Security Violation: Portal customers cannot confirm or alter payment settlements."))
    ...

# Dashboard Analytics Protection
def _check_dashboard_access(self):
    user = self.env.user
    is_staff_or_admin = (
        user.has_group('subscription_management.group_subscription_user')
        or user.has_group('subscription_management.group_subscription_manager')
        or self.env.is_superuser()
    )
    if not is_staff_or_admin:
        raise AccessError(_("Security Violation: Portal customers are not permitted to view global financial metrics."))
```
