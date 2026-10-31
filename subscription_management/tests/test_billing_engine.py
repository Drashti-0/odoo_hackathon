# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBillingEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Global Tech Solutions',
            'email': 'finance@globaltech.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Server Monitoring',
            'list_price': 500.0,
        })
        cls.daily_plan = cls.env['subscription.plan'].create({
            'name': 'Daily Plan',
            'price': 10.0,
            'billing_interval_unit': 'daily',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.weekly_plan = cls.env['subscription.plan'].create({
            'name': 'Weekly Plan',
            'price': 50.0,
            'billing_interval_unit': 'weekly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.monthly_plan = cls.env['subscription.plan'].create({
            'name': 'Monthly Plan',
            'price': 200.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.yearly_plan = cls.env['subscription.plan'].create({
            'name': 'Yearly Plan',
            'price': 2000.0,
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })

    def test_01_interval_calculations(self):
        """Test daily, weekly, monthly, yearly date advancing."""
        start = date(2026, 1, 15)
        self.assertEqual(self.daily_plan.calculate_next_billing_date(start), date(2026, 1, 16))
        self.assertEqual(self.weekly_plan.calculate_next_billing_date(start), date(2026, 1, 22))
        self.assertEqual(self.monthly_plan.calculate_next_billing_date(start), date(2026, 2, 15))
        self.assertEqual(self.yearly_plan.calculate_next_billing_date(start), date(2027, 1, 15))

        # Month-end handling
        jan31 = date(2026, 1, 31)
        self.assertEqual(self.monthly_plan.calculate_next_billing_date(jan31), date(2026, 2, 28))

    def test_02_automated_invoice_generation_and_idempotency(self):
        """Test invoice creation, duplicate prevention, and retry safety."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 500.0,
            })]
        })

        # Run recurring billing
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 1, "Exactly one invoice should be generated")
        first_invoice = sub.invoice_ids[0]
        self.assertEqual(first_invoice.state, 'confirmed')
        self.assertEqual(first_invoice.amount_untaxed, 700.0, "Total untaxed should be plan 200 + line 500 = 700")

        # Advance milestone check
        expected_next = self.monthly_plan.calculate_next_billing_date(today)
        self.assertEqual(sub.next_billing_date, expected_next)

        # Retry execution on the same date (Idempotency test)
        sub.next_billing_date = today  # force date back to test duplicate defense
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 1, "Duplicate invoice MUST NOT be created")

        # Check billing log
        logs = self.env['subscription.billing.log'].search([('subscription_id', '=', sub.id)])
        self.assertTrue(len(logs) >= 2, "Both initial generation and skipped retry must be logged")
        self.assertIn('success', logs.mapped('status'))
        self.assertIn('skipped', logs.mapped('status'))
