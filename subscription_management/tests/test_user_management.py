# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError


@tagged('post_install', '-at_install')
class TestUserManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_manager = cls.env.ref('subscription_management.group_subscription_manager')
        cls.group_user = cls.env.ref('subscription_management.group_subscription_user')
        cls.group_portal = cls.env.ref('subscription_management.group_subscription_portal')

        # Admin user
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Brightloop Admin',
            'login': 'admin_test@brightloop.com',
            'email': 'admin_test@brightloop.com',
            'password': 'AdminSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_manager.id])],
        })

        # Internal Staff user created by Admin
        cls.staff_user = cls.env['res.users'].with_user(cls.admin_user).create({
            'name': 'Brightloop Staff',
            'login': 'staff_test@brightloop.com',
            'email': 'staff_test@brightloop.com',
            'password': 'StaffSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_user.id])],
        })

        # Customer 1
        res1 = cls.env['res.users'].register_portal_customer(
            name="Alice Customer",
            email="alice@customer.com",
            password="AlicePassword2026!",
            company_name="Alice Corp"
        )
        cls.customer_user_1 = cls.env['res.users'].browse(res1['user_id'])
        cls.customer_partner_1 = cls.env['res.partner'].browse(res1['partner_id'])

        # Customer 2
        res2 = cls.env['res.users'].register_portal_customer(
            name="Bob Customer",
            email="bob@customer.com",
            password="BobPassword2026!",
            company_name="Bob Enterprises"
        )
        cls.customer_user_2 = cls.env['res.users'].browse(res2['user_id'])
        cls.customer_partner_2 = cls.env['res.partner'].browse(res2['partner_id'])

        # Plan
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Standard Plan',
            'price': 100.0,
            'billing_interval_unit': 'monthly',
        })

        # Subscriptions and Invoices for Customer 1
        cls.sub_1 = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'plan_id': cls.plan.id,
            'state': 'active',
        })
        cls.inv_1 = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'subscription_id': cls.sub_1.id,
            'partner_id': cls.customer_partner_1.id,
            'billing_period_start': '2026-01-01',
            'billing_period_end': '2026-01-31',
            'state': 'confirmed',
        })

        # Subscriptions and Invoices for Customer 2
        cls.sub_2 = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_2.id,
            'plan_id': cls.plan.id,
            'state': 'active',
        })
        cls.inv_2 = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'subscription_id': cls.sub_2.id,
            'partner_id': cls.customer_partner_2.id,
            'billing_period_start': '2026-01-01',
            'billing_period_end': '2026-01-31',
            'state': 'confirmed',
        })

    def test_01_successful_customer_registration(self):
        """1. Successful customer registration with valid credentials."""
        res = self.env['res.users'].register_portal_customer(
            name="Carol Danvers",
            email="carol@danvers.com",
            password="CarolSecurePassword2026!",
        )
        self.assertTrue(res['success'])
        user = self.env['res.users'].browse(res['user_id'])
        self.assertEqual(user.email, "carol@danvers.com")
        self.assertTrue(user.has_group('subscription_management.group_subscription_portal'))
        self.assertFalse(user.has_group('subscription_management.group_subscription_user'))

    def test_02_duplicate_email_rejection(self):
        """2. Duplicate email rejection."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="Alice Duplicate",
                email="alice@customer.com",
                password="ValidPassword2026!",
            )

    def test_03_case_insensitive_duplicate_email_rejection(self):
        """3. Case-insensitive duplicate email rejection."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="Alice Upper",
                email="ALICE@CUSTOMER.COM",
                password="ValidPassword2026!",
            )

    def test_04_invalid_email_rejection(self):
        """4. Invalid email syntax rejection."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="Invalid Email Guy",
                email="not-an-email",
                password="ValidPassword2026!",
            )

    def test_05_password_shorter_than_required_length(self):
        """5. Password shorter than required length (>8 chars)."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="Short Pass",
                email="short@test.com",
                password="Sh1!",  # 4 chars <= 8
            )
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="Eight Pass",
                email="eight@test.com",
                password="Abcdef1!",  # Exactly 8 chars, policy mandates > 8
            )

    def test_06_missing_uppercase_character(self):
        """6. Password missing uppercase character."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="No Upper",
                email="noupper@test.com",
                password="lowercasepassword123!",
            )

    def test_07_missing_lowercase_character(self):
        """7. Password missing lowercase character."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="No Lower",
                email="nolower@test.com",
                password="UPPERCASEPASSWORD123!",
            )

    def test_08_missing_special_character(self):
        """8. Password missing special character."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].register_portal_customer(
                name="No Special",
                email="nospecial@test.com",
                password="PasswordWithNoSpecial123",
            )

    def test_09_successful_password_reset_flow(self):
        """9. Successful password reset flow and anti-enumeration defense."""
        res_existing = self.env['res.users'].request_password_reset("alice@customer.com")
        self.assertTrue(res_existing['success'])
        self.assertIn("password reset instructions have been sent", res_existing['message'])

        # Non-existent email should return same generic success to prevent email enumeration
        res_nonexistent = self.env['res.users'].request_password_reset("unknown@nowhere.com")
        self.assertTrue(res_nonexistent['success'])
        self.assertIn("password reset instructions have been sent", res_nonexistent['message'])

    def test_10_admin_permissions(self):
        """10. Admin has full administrative permissions."""
        self.assertTrue(self.admin_user.has_group('subscription_management.group_subscription_manager'))
        # Admin can create subscription plans
        new_plan = self.env['subscription.plan'].with_user(self.admin_user).create({
            'name': 'Admin Created Plan',
            'price': 250.0,
            'billing_interval_unit': 'monthly',
        })
        self.assertTrue(new_plan.id)

    def test_11_internal_staff_permissions(self):
        """11. Internal Staff has daily operational access."""
        self.assertTrue(self.staff_user.has_group('subscription_management.group_subscription_user'))
        self.assertFalse(self.staff_user.has_group('subscription_management.group_subscription_manager'))
        # Staff can create subscriptions
        sub = self.env['subscription.subscription'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'plan_id': self.plan.id,
            'state': 'draft',
        })
        self.assertTrue(sub.id)

    def test_12_customer_permissions(self):
        """12. Customer has restricted portal access."""
        self.assertTrue(self.customer_user_1.has_group('subscription_management.group_subscription_portal'))
        self.assertFalse(self.customer_user_1.has_group('subscription_management.group_subscription_user'))
        self.assertFalse(self.customer_user_1.has_group('subscription_management.group_subscription_manager'))

    def test_13_customer_cannot_create_staff(self):
        """13. Customer cannot create Staff or assign privileged roles."""
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(self.customer_user_1).create({
                'name': 'Hacker Staff',
                'login': 'hacker@brightloop.com',
                'email': 'hacker@brightloop.com',
                'password': 'ValidPassword2026!',
                'groups_id': [(6, 0, [self.group_user.id])],
            })

    def test_14_customer_cannot_access_another_customer_subscription(self):
        """14. Customer cannot access another customer's subscription."""
        # Customer 1 searches subscriptions: should see only sub_1, never sub_2
        visible_subs = self.env['subscription.subscription'].with_user(self.customer_user_1).search([])
        self.assertIn(self.sub_1, visible_subs)
        self.assertNotIn(self.sub_2, visible_subs)

    def test_15_customer_cannot_access_another_customer_invoice(self):
        """15. Customer cannot access another customer's invoice."""
        visible_invs = self.env['subscription.invoice'].with_user(self.customer_user_1).search([])
        self.assertIn(self.inv_1, visible_invs)
        self.assertNotIn(self.inv_2, visible_invs)

    def test_16_direct_record_access_restrictions(self):
        """16. Direct record ID access restriction: accessing unauthorized record raises AccessError."""
        # Customer 1 attempts direct read on Customer 2's subscription
        with self.assertRaises(AccessError):
            self.sub_2.with_user(self.customer_user_1).read(['name', 'amount_total'])

        # Customer 1 attempts direct read on Customer 2's invoice
        with self.assertRaises(AccessError):
            self.inv_2.with_user(self.customer_user_1).read(['name', 'amount_total'])

    def test_17_unauthorized_rpc_access_restrictions(self):
        """17. Unauthorized RPC access: customer attempting to modify status or plan via RPC is blocked."""
        # Customer 1 tries to write/confirm Customer 2's subscription
        with self.assertRaises(AccessError):
            self.sub_2.with_user(self.customer_user_1).write({'state': 'closed'})

        # Customer 1 tries to grant self internal staff role via write
        with self.assertRaises(AccessError):
            self.customer_user_1.with_user(self.customer_user_1).write({
                'groups_id': [(4, self.group_user.id)]
            })
