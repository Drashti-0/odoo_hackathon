# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestSubscriptionLifecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Customer
        cls.partner = cls.env['res.partner'].create({
            'name': 'Acme Corporation',
            'email': 'billing@acme.com',
        })

        # Product with Brand Variant (Odoo adds 560)
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Cloud ERP Hosting',
            'list_price': 1000.0,
            'is_subscription': True,
            'brand_name': 'odoo',
        })
        cls.product = cls.product_tmpl.product_variant_id

        # Subscription Plan
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Monthly Professional',
            'price': 150.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 2.0,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
            'auto_close': True,
            'auto_close_days': 5,
        })

    def test_01_product_variant_pricing(self):
        """Test Product and Odoo Brand Variant Price Calculation (+560 surcharge)."""
        self.assertEqual(self.product_tmpl.brand_surcharge, 560.0, "Odoo brand surcharge must be 560.0")
        self.assertEqual(self.product_tmpl.subscription_price, 1560.0, "Subscription price must be base 1000 + 560 = 1560")
        calc_price = self.product.get_subscription_price()
        self.assertEqual(calc_price, 1560.0, "Variant price method must return 1560.0")

    def test_02_plan_validation(self):
        """Test Plan constraints on negative price, minimum quantity, and dates."""
        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Plan',
                'price': -10.0,
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Quantity Plan',
                'price': 50.0,
                'min_quantity': 0.5,
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Dates Plan',
                'price': 50.0,
                'start_date': date(2026, 12, 31),
                'end_date': date(2026, 1, 1),
                'billing_interval_unit': 'monthly',
            })

    def test_03_subscription_lifecycle_flow(self):
        """Test Full Lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 2.0,  # meets min_quantity
                'unit_price': 1560.0,
            })]
        })
        self.assertEqual(sub.state, 'draft')
        self.assertTrue(sub.name.startswith('SQ-') or sub.name == 'New')

        # 1. Draft -> Quotation
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')

        # 2. Quotation -> Confirmed
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith('SUB-'), "Confirmed subscription should have SUB- prefix")

        # 3. Confirmed -> Active
        sub.action_activate()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, sub.start_date)

        # 4. Active -> Paused
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')
        self.assertEqual(sub.pause_date, date.today())

        # 5. Paused -> Resumed
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertFalse(sub.pause_date)

        # 6. Active -> Closed
        sub.action_close(reason="Client completed project")
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_reason, "Client completed project")

    def test_04_duplicate_surcharge_prevention(self):
        """Test that Odoo brand surcharge of 560 is not applied twice."""
        # Product with Odoo brand template
        tmpl = self.env['product.template'].create({
            'name': 'ERP Pro Suite',
            'list_price': 800.0,
            'is_subscription': True,
            'brand_name': 'odoo',
        })
        prod = tmpl.product_variant_id
        # Surcharge must be exactly 560
        self.assertEqual(prod.subscription_price, 1360.0)
        self.assertEqual(prod.get_subscription_price(), 1360.0)

    def test_05_currency_fallback_safety(self):
        """Test currency fallback safety when currency is initially unassigned."""
        sub = self.env['subscription.subscription'].new({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
        })
        sub._compute_currency_id()
        self.assertTrue(sub.currency_id, "Currency should fall back to company currency")
