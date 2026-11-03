# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError, UserError


@tagged('post_install', '-at_install')
class TestPaymentManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_manager = cls.env.ref('subscription_management.group_subscription_manager')
        cls.group_user = cls.env.ref('subscription_management.group_subscription_user')
        cls.group_portal = cls.env.ref('subscription_management.group_subscription_portal')

        # Admin User
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Payment Admin',
            'login': 'payment_admin@brightloop.com',
            'email': 'payment_admin@brightloop.com',
            'password': 'AdminSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_manager.id])],
        })

        # Staff User
        cls.staff_user = cls.env['res.users'].with_user(cls.admin_user).create({
            'name': 'Payment Staff',
            'login': 'payment_staff@brightloop.com',
            'email': 'payment_staff@brightloop.com',
            'password': 'StaffSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_user.id])],
        })

        # Customer 1
        res1 = cls.env['res.users'].register_portal_customer(
            name="Alice Subscriber",
            email="alice_payment@brightloop.com",
            password="AliceSecurePass123!"
        )
        cls.customer_user_1 = cls.env['res.users'].browse(res1['user_id'])
        cls.customer_partner_1 = cls.env['res.partner'].browse(res1['partner_id'])

        # Customer 2
        res2 = cls.env['res.users'].register_portal_customer(
            name="Bob Subscriber",
            email="bob_payment@brightloop.com",
            password="BobSecurePass123!"
        )
        cls.customer_user_2 = cls.env['res.users'].browse(res2['user_id'])
        cls.customer_partner_2 = cls.env['res.partner'].browse(res2['partner_id'])

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Dedicated Cloud Server',
            'list_price': 500.0,
            'is_subscription': True,
        })

        # Invoices for Customer 1
        cls.inv_1 = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'due_date': date.today() + relativedelta(days=15),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 1.0,
                'unit_price': 500.0,
            })]
        })

        # Invoices for Customer 2
        cls.inv_2 = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_2.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'due_date': date.today() + relativedelta(days=15),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 2.0,
                'unit_price': 500.0,
            })]
        })

    def test_01_create_valid_payment(self):
        """1. Creating a valid payment record."""
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_1.id,
            'amount': 200.0,
            'payment_method': 'bank_transfer',
            'name': 'WIRE-TEST-001',
            'payment_note': 'Wire transfer received from client bank',
            'state': 'draft',
        })
        self.assertEqual(pay.amount, 200.0)
        self.assertEqual(pay.payment_method, 'bank_transfer')
        self.assertEqual(pay.partner_id, self.customer_partner_1)
        self.assertEqual(pay.state, 'draft')

    def test_02_rejecting_zero_and_negative_amounts(self):
        """2. Rejecting zero and negative payment amounts."""
        with self.assertRaises(ValidationError):
            self.env['subscription.payment'].with_user(self.staff_user).create({
                'invoice_id': self.inv_1.id,
                'amount': 0.0,
                'payment_method': 'card',
            })
        with self.assertRaises(ValidationError):
            self.env['subscription.payment'].with_user(self.staff_user).create({
                'invoice_id': self.inv_1.id,
                'amount': -50.0,
                'payment_method': 'card',
            })

    def test_03_full_payment(self):
        """3. Full payment settles invoice completely (payment_state='paid', state='paid')."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 2, 1),
            'billing_period_end': date(2026, 2, 28),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 300.0,
            })]
        })
        self.assertEqual(inv.amount_total, 300.0)
        self.assertEqual(inv.amount_residual, 300.0)

        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 300.0,
            'payment_method': 'card',
            'state': 'draft',
        })
        pay.action_confirm_payment()

        self.assertEqual(pay.state, 'success')
        self.assertEqual(inv.amount_paid, 300.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')

    def test_04_partial_payment(self):
        """4. Partial payment updates balance and marks invoice partial."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 3, 1),
            'billing_period_end': date(2026, 3, 31),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 500.0,
            })]
        })
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 200.0,
            'payment_method': 'upi',
            'state': 'draft',
        })
        pay.action_confirm_payment()

        self.assertEqual(inv.amount_paid, 200.0)
        self.assertEqual(inv.amount_residual, 300.0)
        self.assertEqual(inv.payment_state, 'partial')
        self.assertEqual(inv.state, 'confirmed')

    def test_05_multiple_partial_payments(self):
        """5. Multiple partial payments accumulate correctly until full settlement."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 4, 1),
            'billing_period_end': date(2026, 4, 30),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 600.0,
            })]
        })
        # Payment 1: $200
        p1 = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 200.0,
            'payment_method': 'cash',
        })
        p1.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 200.0)
        self.assertEqual(inv.amount_residual, 400.0)
        self.assertEqual(inv.payment_state, 'partial')

        # Payment 2: $300
        p2 = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 300.0,
            'payment_method': 'bank_transfer',
        })
        p2.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 500.0)
        self.assertEqual(inv.amount_residual, 100.0)
        self.assertEqual(inv.payment_state, 'partial')

        # Payment 3: $100 (Final settlement)
        p3 = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 100.0,
            'payment_method': 'upi',
        })
        p3.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 600.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')

    def test_06_correct_outstanding_balance_calculation(self):
        """6. Residual balance is always amount_total - amount_paid."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 5, 1),
            'billing_period_end': date(2026, 5, 31),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 1000.0,
            })]
        })
        self.assertEqual(inv.amount_residual, 1000.0)
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 450.0,
            'payment_method': 'card',
        })
        pay.action_confirm_payment()
        self.assertEqual(inv.amount_residual, 550.0)

    def test_07_failed_payment_not_affecting_balance(self):
        """7. Failed payment does not reduce invoice balance."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 6, 1),
            'billing_period_end': date(2026, 6, 30),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 400.0,
            })]
        })
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 400.0,
            'payment_method': 'stripe',
            'state': 'draft',
        })
        pay.action_fail_payment(reason="Card declined by issuer")
        self.assertEqual(pay.state, 'failed')
        self.assertEqual(inv.amount_paid, 0.0)
        self.assertEqual(inv.amount_residual, 400.0)
        self.assertEqual(inv.payment_state, 'not_paid')

    def test_08_draft_payment_not_affecting_balance(self):
        """8. Draft payment does not reduce invoice balance."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 7, 1),
            'billing_period_end': date(2026, 7, 31),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 250.0,
            })]
        })
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 250.0,
            'payment_method': 'paypal',
            'state': 'draft',
        })
        self.assertEqual(inv.amount_paid, 0.0)
        self.assertEqual(inv.amount_residual, 250.0)
        self.assertEqual(inv.payment_state, 'not_paid')

    def test_09_duplicate_confirmation_prevention(self):
        """9. Re-confirming an already settled payment is idempotent and safe."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 8, 1),
            'billing_period_end': date(2026, 8, 31),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 500.0,
            })]
        })
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 250.0,
            'payment_method': 'card',
        })
        pay.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 250.0)

        # Confirm again
        pay.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 250.0, "Duplicate confirm must not add amount again")

    def test_10_payment_linked_to_correct_invoice_and_customer(self):
        """10. Payment correctly associates with invoice and customer partner."""
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_1.id,
            'amount': 100.0,
            'payment_method': 'card',
        })
        self.assertEqual(pay.invoice_id, self.inv_1)
        self.assertEqual(pay.partner_id, self.customer_partner_1)
        self.assertIn(pay, self.inv_1.payment_ids)

    def test_11_customer_can_view_only_own_payments(self):
        """11. Customer can view their own payment transactions."""
        pay1 = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_1.id,
            'amount': 50.0,
            'payment_method': 'upi',
        })
        # Customer 1 reads own payment
        visible_pays = self.env['subscription.payment'].with_user(self.customer_user_1).search([])
        self.assertIn(pay1, visible_pays)

    def test_12_customer_cannot_access_another_customer_payment(self):
        """12. Customer 1 cannot access Customer 2's payments."""
        pay2 = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_2.id,
            'amount': 150.0,
            'payment_method': 'card',
        })
        # Customer 1 searching payments must NOT see Customer 2's payment
        visible_pays = self.env['subscription.payment'].with_user(self.customer_user_1).search([])
        self.assertNotIn(pay2, visible_pays)

        # Direct read raises AccessError
        with self.assertRaises(AccessError):
            pay2.with_user(self.customer_user_1).read(['amount', 'state'])

    def test_13_staff_and_admin_permissions(self):
        """13. Staff and Admin can settle payments; customer attempt raises AccessError."""
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_1.id,
            'amount': 50.0,
            'payment_method': 'card',
            'state': 'draft',
        })
        # Customer attempting to confirm payment must be blocked
        with self.assertRaises(AccessError):
            pay.with_user(self.customer_user_1).action_confirm_payment()

        # Staff can confirm
        pay.with_user(self.staff_user).action_confirm_payment()
        self.assertEqual(pay.state, 'success')

    def test_14_existing_discount_and_invoice_calculations_remain_correct(self):
        """14. Existing discount and invoice calculations remain intact with payments."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Twenty Off',
            'code': 'OFF20',
            'discount_type': 'fixed',
            'value': 20.0,
        })
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_1.id,
            'billing_period_start': date(2026, 9, 1),
            'billing_period_end': date(2026, 9, 30),
            'state': 'confirmed',
            'discount_id': disc.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })]
        })
        inv._compute_amounts()
        # 100 gross - 20 discount = 80 total
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 80.0)
        self.assertEqual(inv.amount_residual, 80.0)

        # Pay 80
        pay = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': inv.id,
            'amount': 80.0,
            'payment_method': 'card',
        })
        pay.action_confirm_payment()
        self.assertEqual(inv.amount_paid, 80.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')
