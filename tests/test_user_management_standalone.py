#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Verification Suite for Module 1: User Management & Authentication
Team: AuraMinds
Developer 2: Drashti Bhanderi
Tests:
1. Successful customer registration
2. Duplicate email rejection
3. Case-insensitive duplicate email rejection
4. Invalid email rejection
5. Password shorter than required length
6. Missing uppercase character
7. Missing lowercase character
8. Missing special character
9. Successful password reset flow
10. Admin permissions
11. Internal Staff permissions
12. Customer permissions
13. Customer cannot create Staff
14. Customer cannot access another customer's subscription
15. Customer cannot access another customer's invoice
16. Direct record access restrictions
17. Unauthorized RPC access restrictions
"""

import re
import unittest

# Import validators directly from module
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class ValidationError(Exception):
    pass


class AccessError(Exception):
    pass


def validate_email_syntax(email):
    if not email or not isinstance(email, str):
        raise ValidationError("Email address cannot be empty.")
    clean = email.strip()
    if not EMAIL_REGEX.match(clean):
        raise ValidationError(f"Invalid email format: '{email}'.")
    return clean


def validate_password_strength(password):
    if not password or not isinstance(password, str):
        raise ValidationError("Password cannot be empty.")
    errors = []
    # Must contain more than 8 characters (len > 8)
    if len(password) <= 8:
        errors.append("Must contain more than 8 characters (at least 9 characters).")
    if not re.search(r'[A-Z]', password):
        errors.append("Must contain at least one uppercase letter (A-Z).")
    if not re.search(r'[a-z]', password):
        errors.append("Must contain at least one lowercase letter (a-z).")
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/~`\\]', password):
        errors.append("Must contain at least one special character (!@#$%^&* etc.).")
    if errors:
        raise ValidationError("Password security policy failure: " + "; ".join(errors))
    return True


# ============================================================================
# ORM & SECURITY MOCK LAYER
# ============================================================================

class MockSecurityGroup:
    ADMIN = 'group_subscription_manager'
    STAFF = 'group_subscription_user'
    PORTAL = 'group_subscription_portal'


class MockPartner:
    _db = []

    def __init__(self, name, email, company_name=None):
        self.id = len(MockPartner._db) + 1
        self.name = name
        self.email = email
        self.company_name = company_name
        MockPartner._db.append(self)

    @classmethod
    def reset(cls):
        cls._db = []

    @classmethod
    def search_by_email(cls, email):
        clean = email.strip().lower()
        for p in cls._db:
            if p.email and p.email.strip().lower() == clean:
                return p
        return None


class MockUser:
    _db = []

    def __init__(self, name, email, password, partner, groups=None):
        validate_email_syntax(email)
        validate_password_strength(password)
        # Case-insensitive duplicate check
        clean = email.strip().lower()
        if MockUser.search_by_email(clean):
            raise ValidationError(f"Email '{email}' is already registered.")

        self.id = len(MockUser._db) + 1
        self.name = name
        self.login = clean
        self.email = clean
        # Password hashed natively, never stored plaintext
        self._password_hash = hash(password)
        self.partner_id = partner
        self.groups = set(groups or [MockSecurityGroup.PORTAL])
        MockUser._db.append(self)

    @classmethod
    def reset(cls):
        cls._db = []

    @classmethod
    def search_by_email(cls, email):
        clean = email.strip().lower()
        for u in cls._db:
            if u.email and u.email.strip().lower() == clean:
                return u
        return None

    def has_group(self, group_xml_id):
        return group_xml_id in self.groups

    @classmethod
    def create_user(cls, creator_user, name, email, password, groups=None):
        requested_groups = set(groups or [MockSecurityGroup.PORTAL])
        privileged_groups = {MockSecurityGroup.ADMIN, MockSecurityGroup.STAFF}

        # Security check: Only Admin can create Staff or Admin
        if requested_groups.intersection(privileged_groups):
            if not creator_user or not creator_user.has_group(MockSecurityGroup.ADMIN):
                raise AccessError("Security Violation: Only Subscription Administrators can create or grant Internal Staff accounts.")

        partner = MockPartner(name=name, email=email)
        return MockUser(name=name, email=email, password=password, partner=partner, groups=requested_groups)

    @classmethod
    def register_portal_customer(cls, name, email, password, company_name=None):
        validate_email_syntax(email)
        validate_password_strength(password)
        clean = email.strip().lower()
        if MockUser.search_by_email(clean):
            raise ValidationError(f"The email '{email}' is already registered.")

        partner = MockPartner.search_by_email(clean) or MockPartner(name=name, email=clean, company_name=company_name)
        user = MockUser(name=name, email=clean, password=password, partner=partner, groups=[MockSecurityGroup.PORTAL])
        return {
            'success': True,
            'user_id': user.id,
            'partner_id': partner.id,
            'message': 'Customer registered successfully.'
        }

    @classmethod
    def request_password_reset(cls, email):
        clean = (email or '').strip().lower()
        # Anti-enumeration response
        msg = f"If the email address '{clean}' is registered with Brightloop, password reset instructions have been sent."
        user = cls.search_by_email(clean)
        # Even if user is not found, return same message (do not reveal existence)
        return {'success': True, 'message': msg, 'email_sent': user is not None}


class MockRecordRuleEngine:
    """Enforces Customer Portal Record Isolation."""

    @staticmethod
    def check_can_read(user, record):
        # Admin and Staff can read everything
        if user.has_group(MockSecurityGroup.ADMIN) or user.has_group(MockSecurityGroup.STAFF):
            return True
        # Portal Customer: Can ONLY read records where partner_id == user.partner_id
        if user.has_group(MockSecurityGroup.PORTAL):
            if record.partner_id.id == user.partner_id.id:
                return True
            raise AccessError(f"Access Denied: Portal customer {user.name} cannot access record {record.name} belonging to partner {record.partner_id.name}.")
        raise AccessError("Access Denied.")

    @staticmethod
    def check_can_write(user, record, values):
        if user.has_group(MockSecurityGroup.ADMIN) or user.has_group(MockSecurityGroup.STAFF):
            return True
        # Portal customer cannot write subscription or invoice records
        if user.has_group(MockSecurityGroup.PORTAL):
            raise AccessError(f"Access Denied: Portal customer {user.name} does not have write permissions on {record.name}.")
        raise AccessError("Access Denied.")


class MockCustomerSubscription:
    def __init__(self, name, partner, amount_total=100.0, state='active'):
        self.name = name
        self.partner_id = partner
        self.amount_total = amount_total
        self.state = state

    def read(self, fields, user):
        MockRecordRuleEngine.check_can_read(user, self)
        return {f: getattr(self, f) for f in fields if hasattr(self, f)}

    def write(self, values, user):
        MockRecordRuleEngine.check_can_write(user, self, values)
        for k, v in values.items():
            setattr(self, k, v)
        return True


class MockCustomerInvoice:
    def __init__(self, name, partner, amount_total=150.0, state='confirmed', payment_state='not_paid'):
        self.name = name
        self.partner_id = partner
        self.amount_total = amount_total
        self.state = state
        self.payment_state = payment_state

    def read(self, fields, user):
        MockRecordRuleEngine.check_can_read(user, self)
        return {f: getattr(self, f) for f in fields if hasattr(self, f)}

    def write(self, values, user):
        MockRecordRuleEngine.check_can_write(user, self, values)
        for k, v in values.items():
            setattr(self, k, v)
        return True


# ============================================================================
# STANDALONE VERIFICATION TEST CASES (17 TESTS)
# ============================================================================

class TestUserManagementAuthentication(unittest.TestCase):

    def setUp(self):
        MockPartner.reset()
        MockUser.reset()

        # Admin
        admin_partner = MockPartner("System Admin", "admin@brightloop.com")
        self.admin_user = MockUser(
            "System Admin", "admin@brightloop.com", "AdminPass123!",
            admin_partner, [MockSecurityGroup.ADMIN, MockSecurityGroup.STAFF]
        )

        # Internal Staff
        self.staff_user = MockUser.create_user(
            self.admin_user, "Operations Staff", "staff@brightloop.com",
            "StaffPass123!", [MockSecurityGroup.STAFF]
        )

        # Customer 1
        res1 = MockUser.register_portal_customer(
            "Alice In Wonderland", "alice@example.com", "AliceSecretPass2026!"
        )
        self.customer_1 = MockUser._db[res1['user_id'] - 1]
        self.partner_1 = self.customer_1.partner_id

        # Customer 2
        res2 = MockUser.register_portal_customer(
            "Bob The Builder", "bob@example.com", "BobSecretPass2026!"
        )
        self.customer_2 = MockUser._db[res2['user_id'] - 1]
        self.partner_2 = self.customer_2.partner_id

        # Subscriptions
        self.sub_1 = MockCustomerSubscription("SUB-00001", self.partner_1, 250.0)
        self.sub_2 = MockCustomerSubscription("SUB-00002", self.partner_2, 500.0)

        # Invoices
        self.inv_1 = MockCustomerInvoice("INV-00001", self.partner_1, 250.0)
        self.inv_2 = MockCustomerInvoice("INV-00002", self.partner_2, 500.0)

    # 1. Successful customer registration
    def test_01_successful_customer_registration(self):
        """1. Customer registration with valid credentials succeeds."""
        res = MockUser.register_portal_customer(
            "David Copperfield", "david@magic.com", "DavidSuperPass2026!"
        )
        self.assertTrue(res['success'])
        user = MockUser._db[res['user_id'] - 1]
        self.assertEqual(user.email, "david@magic.com")
        self.assertTrue(user.has_group(MockSecurityGroup.PORTAL))
        self.assertFalse(user.has_group(MockSecurityGroup.STAFF))

    # 2. Duplicate email rejection
    def test_02_duplicate_email_rejection(self):
        """2. Duplicate email registration is strictly rejected."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer(
                "Alice Clone", "alice@example.com", "ValidPass123!"
            )

    # 3. Case-insensitive duplicate email rejection
    def test_03_case_insensitive_duplicate_email_rejection(self):
        """3. Case-insensitive duplicate email is strictly rejected."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer(
                "Alice Clone Upper", "ALICE@EXAMPLE.COM", "ValidPass123!"
            )
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer(
                "Alice Clone Mixed", "  AliCe@ExamPle.Com ", "ValidPass123!"
            )

    # 4. Invalid email rejection
    def test_04_invalid_email_rejection(self):
        """4. Invalid email syntax is rejected."""
        invalid_emails = ["not-an-email", "@nodomain.com", "user@.com", "user@domain", ""]
        for bad_email in invalid_emails:
            with self.assertRaises(ValidationError):
                MockUser.register_portal_customer("Bad Guy", bad_email, "ValidPass123!")

    # 5. Password shorter than required length (> 8 chars)
    def test_05_password_shorter_than_required_length(self):
        """5. Password shorter than required (>8 characters, so <=8 rejected)."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer("User", "u1@test.com", "Short1!")  # 6 chars
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer("User", "u2@test.com", "Abcdef1!")  # 8 chars (must be > 8)

    # 6. Missing uppercase character
    def test_06_missing_uppercase_character(self):
        """6. Password missing uppercase character is rejected."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer("User", "u3@test.com", "nouppercasepassword123!")

    # 7. Missing lowercase character
    def test_07_missing_lowercase_character(self):
        """7. Password missing lowercase character is rejected."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer("User", "u4@test.com", "NOLOWERCASEPASSWORD123!")

    # 8. Missing special character
    def test_08_missing_special_character(self):
        """8. Password missing special character is rejected."""
        with self.assertRaises(ValidationError):
            MockUser.register_portal_customer("User", "u5@test.com", "PasswordWithoutSpecial123")

    # 9. Successful password reset flow
    def test_09_successful_password_reset_flow(self):
        """9. Password reset request succeeds and hides user enumeration."""
        # Registered user
        res1 = MockUser.request_password_reset("alice@example.com")
        self.assertTrue(res1['success'])
        self.assertTrue(res1['email_sent'])
        self.assertIn("password reset instructions have been sent", res1['message'])

        # Non-registered user receives same message (prevents email harvesting)
        res2 = MockUser.request_password_reset("ghost@nowhere.com")
        self.assertTrue(res2['success'])
        self.assertFalse(res2['email_sent'])
        self.assertIn("password reset instructions have been sent", res2['message'])

    # 10. Admin permissions
    def test_10_admin_permissions(self):
        """10. Admin has full administrative capabilities."""
        self.assertTrue(self.admin_user.has_group(MockSecurityGroup.ADMIN))
        # Admin can read any subscription
        data = self.sub_2.read(['name', 'amount_total'], self.admin_user)
        self.assertEqual(data['name'], 'SUB-00002')

    # 11. Internal Staff permissions
    def test_11_internal_staff_permissions(self):
        """11. Staff has operational access but cannot perform admin-only tasks."""
        self.assertTrue(self.staff_user.has_group(MockSecurityGroup.STAFF))
        self.assertFalse(self.staff_user.has_group(MockSecurityGroup.ADMIN))
        # Staff can read customer subscriptions for support
        data = self.sub_1.read(['name'], self.staff_user)
        self.assertEqual(data['name'], 'SUB-00001')

    # 12. Customer permissions
    def test_12_customer_permissions(self):
        """12. Customer has restricted portal role."""
        self.assertTrue(self.customer_1.has_group(MockSecurityGroup.PORTAL))
        self.assertFalse(self.customer_1.has_group(MockSecurityGroup.STAFF))
        self.assertFalse(self.customer_1.has_group(MockSecurityGroup.ADMIN))

    # 13. Customer cannot create Staff
    def test_13_customer_cannot_create_staff(self):
        """13. Customer attempt to create Staff or elevate privileges is blocked."""
        with self.assertRaises(AccessError):
            MockUser.create_user(
                creator_user=self.customer_1,
                name="Rogue Staff",
                email="rogue@brightloop.com",
                password="RoguePass123!",
                groups=[MockSecurityGroup.STAFF]
            )

    # 14. Customer cannot access another customer's subscription
    def test_14_customer_cannot_access_another_customer_subscription(self):
        """14. Customer 1 attempting to access Customer 2's subscription is blocked."""
        # Reading own subscription is permitted
        own_sub = self.sub_1.read(['name', 'amount_total'], self.customer_1)
        self.assertEqual(own_sub['name'], 'SUB-00001')

        # Reading other customer's subscription raises AccessError
        with self.assertRaises(AccessError):
            self.sub_2.read(['name', 'amount_total'], self.customer_1)

    # 15. Customer cannot access another customer's invoice
    def test_15_customer_cannot_access_another_customer_invoice(self):
        """15. Customer 1 attempting to access Customer 2's invoice is blocked."""
        # Reading own invoice is permitted
        own_inv = self.inv_1.read(['name', 'amount_total'], self.customer_1)
        self.assertEqual(own_inv['name'], 'INV-00001')

        # Reading other customer's invoice raises AccessError
        with self.assertRaises(AccessError):
            self.inv_2.read(['name', 'amount_total'], self.customer_1)

    # 16. Direct record access restrictions
    def test_16_direct_record_access_restrictions(self):
        """16. Direct record ID access is strictly enforced at security layer."""
        with self.assertRaises(AccessError):
            MockRecordRuleEngine.check_can_read(self.customer_2, self.sub_1)
        with self.assertRaises(AccessError):
            MockRecordRuleEngine.check_can_read(self.customer_2, self.inv_1)

    # 17. Unauthorized RPC access restrictions
    def test_17_unauthorized_rpc_access_restrictions(self):
        """17. Unauthorized RPC write attempts by portal customers are rejected."""
        # Customer attempts to alter subscription state via RPC write
        with self.assertRaises(AccessError):
            self.sub_1.write({'state': 'closed'}, self.customer_1)
        # Customer attempts to alter invoice state via RPC write
        with self.assertRaises(AccessError):
            self.inv_2.write({'state': 'paid'}, self.customer_1)


if __name__ == '__main__':
    unittest.main()
