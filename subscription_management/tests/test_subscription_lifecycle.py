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

        # Sales Rep User
        cls.sales_user = cls.env['res.users'].create({
            'name': 'Subscription Sales Rep',
            'login': 'sub_sales_rep@example.com',
            'email': 'sales@example.com',
            'groups_id': [(6, 0, [cls.env.ref('subscription_management.group_subscription_user').id])],
        })

        # Manager User
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Subscription Manager Admin',
            'login': 'sub_manager@example.com',
            'email': 'manager@example.com',
            'groups_id': [(6, 0, [cls.env.ref('subscription_management.group_subscription_manager').id])],
        })

        # Taxes: 10% exclusive and 10% inclusive
        cls.tax_exclusive = cls.env['account.tax'].create({
            'name': 'Sales Tax 10% Exclusive',
            'amount': 10.0,
            'amount_type': 'percent',
            'price_include': False,
            'type_tax_use': 'sale',
        })

        cls.tax_inclusive = cls.env['account.tax'].create({
            'name': 'Sales Tax 10% Inclusive',
            'amount': 10.0,
            'amount_type': 'percent',
            'price_include': True,
            'type_tax_use': 'sale',
        })

        # Product with Brand Variant (Odoo adds 560)
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Cloud ERP Hosting',
            'list_price': 1000.0,
            'is_subscription': True,
            'brand_name': 'odoo',
        })
        cls.product = cls.product_tmpl.product_variant_id

        # Secondary Product (no surcharge)
        cls.addon_tmpl = cls.env['product.template'].create({
            'name': '24/7 Priority Support',
            'list_price': 200.0,
            'is_subscription': True,
            'brand_name': 'standard',
        })
        cls.addon_product = cls.addon_tmpl.product_variant_id

        # Standard Subscription Plan
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

        # Strict Fixed Plan (No pause, no early close, no renewal)
        cls.strict_plan = cls.env['subscription.plan'].create({
            'name': 'Strict Fixed Annual Contract',
            'price': 500.0,
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
            'allow_pause': False,
            'allow_renewal': False,
            'allow_early_close': False,
            'auto_close': True,
            'auto_close_days': 0,
        })

    def test_01_quotation_creation_and_sequence(self):
        """Step 2: Quotation creation, sequence (SQ-XXXXX), default dates and currency."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
        })
        self.assertEqual(sub.state, 'draft')
        self.assertTrue(sub.name.startswith('SQ-'), f"Quotation sequence must start with SQ-, got {sub.name}")
        self.assertEqual(sub.start_date, date.today())
        self.assertEqual(sub.currency_id, self.env.company.currency_id)

    def test_02_quotation_template_creation_and_constraints(self):
        """Step 3: Quotation template creation, negative validity constraint, and line quantities."""
        tmpl = self.env['subscription.quotation.template'].create({
            'name': 'Enterprise Starter Template',
            'plan_id': self.plan.id,
            'validity_days': 45,
            'terms_and_conditions': '<p>Standard 30-day payment terms apply.</p>',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 3.0,
                'unit_price': 1560.0,
            })],
        })
        self.assertEqual(tmpl.validity_days, 45)
        self.assertEqual(len(tmpl.line_ids), 1)

        # Negative validity days must fail
        with self.assertRaises(ValidationError):
            self.env['subscription.quotation.template'].create({
                'name': 'Invalid Validity Template',
                'plan_id': self.plan.id,
                'validity_days': -5,
            })

        # Sub-zero quantity on template line must fail
        with self.assertRaises(ValidationError):
            self.env['subscription.quotation.template.line'].create({
                'template_id': tmpl.id,
                'product_id': self.addon_product.id,
                'quantity': 0.0,
            })

    def test_03_template_application_to_quotation(self):
        """Step 3: Applying template populates plan, lines, validity date, and terms without mutating template."""
        tmpl = self.env['subscription.quotation.template'].create({
            'name': 'Predefined Cloud Pack',
            'plan_id': self.plan.id,
            'validity_days': 15,
            'terms_and_conditions': '<p>SLA 99.9% uptime guaranteed.</p>',
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 1560.0,
                }),
                (0, 0, {
                    'product_id': self.addon_product.id,
                    'quantity': 1.0,
                    'unit_price': 200.0,
                }),
            ],
        })

        sub = self.env['subscription.subscription'].new({
            'partner_id': self.partner.id,
            'template_id': tmpl.id,
        })
        sub._onchange_template_id()

        self.assertEqual(sub.plan_id, self.plan)
        self.assertEqual(sub.quotation_validity_date, date.today() + relativedelta(days=15))
        self.assertIn('SLA 99.9%', str(sub.terms_and_conditions))
        self.assertEqual(len(sub.line_ids), 2)

        # Mutating quotation lines does not affect original template
        sub_record = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'template_id': tmpl.id,
            'plan_id': tmpl.plan_id.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Customized Description',
                'quantity': 5.0,
                'unit_price': 1200.0,
            })],
            'terms_and_conditions': '<p>Overridden custom SLA 99.99%.</p>',
        })
        self.assertEqual(tmpl.line_ids[0].quantity, 2.0, "Template line quantity must remain unchanged")
        self.assertIn('SLA 99.9%', tmpl.terms_and_conditions, "Template terms must remain intact")
        self.assertEqual(sub_record.line_ids[0].quantity, 5.0)

    def test_04_subscription_line_calculations_exclusive_tax(self):
        """Step 5: Line subtotals, variant surcharges (+560), and tax-exclusive calculations."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,  # base plan price = 150.0
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,  # base 1000 + 560 = 1560.0
                    'quantity': 2.0,
                    'tax_ids': [(6, 0, [self.tax_exclusive.id])],
                }),
                (0, 0, {
                    'product_id': self.addon_product.id,  # 200.0
                    'quantity': 3.0,
                    'tax_ids': [(6, 0, [self.tax_exclusive.id])],
                }),
            ]
        })

        line1 = sub.line_ids.filtered(lambda l: l.product_id == self.product)
        line2 = sub.line_ids.filtered(lambda l: l.product_id == self.addon_product)

        # Line 1: 2 * 1560 = 3120 untaxed; 10% tax = 312.0; total = 3432.0
        self.assertEqual(line1.unit_price, 1560.0)
        self.assertEqual(line1.price_subtotal, 3120.0)
        self.assertEqual(line1.price_tax, 312.0)
        self.assertEqual(line1.price_total, 3432.0)

        # Line 2: 3 * 200 = 600 untaxed; 10% tax = 60.0; total = 660.0
        self.assertEqual(line2.unit_price, 200.0)
        self.assertEqual(line2.price_subtotal, 600.0)
        self.assertEqual(line2.price_tax, 60.0)
        self.assertEqual(line2.price_total, 660.0)

        # Header totals: base_plan (150) + lines_untaxed (3720) = 3870.0; tax = 372.0; total = 4242.0
        self.assertEqual(sub.amount_untaxed, 3870.0)
        self.assertEqual(sub.amount_tax, 372.0)
        self.assertEqual(sub.amount_total, 4242.0)

    def test_05_subscription_line_calculations_inclusive_tax(self):
        """Step 5: Tax-inclusive pricing (price_include=True) without tax double-counting."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,  # base plan price = 150.0, min_quantity = 2.0
            'line_ids': [
                (0, 0, {
                    'product_id': self.addon_product.id,
                    'quantity': 2.0,
                    'unit_price': 110.0,  # 110 inclusive of 10% tax -> 100 untaxed + 10 tax each
                    'tax_ids': [(6, 0, [self.tax_inclusive.id])],
                }),
            ]
        })
        line = sub.line_ids[0]
        self.assertEqual(line.price_subtotal, 200.0, "Subtotal must be untaxed base 200.0")
        self.assertEqual(line.price_tax, 20.0, "Tax amount must be 20.0")
        self.assertEqual(line.price_total, 220.0, "Total inclusive must be 220.0")

        # Header amounts: 150 (plan) + 200 (line) = 350 untaxed; tax = 20; total = 370
        self.assertEqual(sub.amount_untaxed, 350.0)
        self.assertEqual(sub.amount_tax, 20.0)
        self.assertEqual(sub.amount_total, 370.0)

    def test_06_quotation_confirmation_and_sequence(self):
        """Step 2 & 4: Confirming draft/quotation transitions to confirmed and assigns SUB-XXXXX."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2.0,
                'unit_price': 1560.0,
            })],
        })
        self.assertTrue(sub.name.startswith('SQ-'))

        # Send quotation
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')

        # Confirm quotation
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith('SUB-'), f"Confirmed contract must start with SUB-, got {sub.name}")

    def test_07_price_immutability_after_confirmation(self):
        """Step 5: Updating product catalog list price does not alter confirmed subscription lines."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2.0,
                'unit_price': 1560.0,
            })],
        })
        sub.action_confirm()
        initial_subtotal = sub.amount_untaxed
        initial_line_price = sub.line_ids[0].unit_price

        # Catalog price increase on product template
        self.product_tmpl.write({'list_price': 5000.0})
        self.assertEqual(self.product.get_subscription_price(), 5560.0)

        # Confirmed contract remains immutable
        sub.line_ids[0]._compute_line_totals()
        sub._compute_amounts()
        self.assertEqual(sub.line_ids[0].unit_price, initial_line_price)
        self.assertEqual(sub.amount_untaxed, initial_subtotal)

    def test_08_invalid_state_transitions(self):
        """Step 4: Unauthorized and invalid state transitions are blocked by ORM validations."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2.0,
            })],
        })
        self.assertEqual(sub.state, 'draft')

        # Direct jump draft -> active is invalid
        with self.assertRaises(UserError):
            sub.write({'state': 'active'})

        # Direct jump draft -> paused is invalid
        with self.assertRaises(UserError):
            sub.write({'state': 'paused'})

        # Reset to draft from quotation is allowed
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')
        sub.action_draft()
        self.assertEqual(sub.state, 'draft')

        # Cancellation of quotation is allowed
        sub.action_cancel()
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_reason, 'Quotation was cancelled.')

    def test_09_pause_and_resume_shifting_schedule(self):
        """Step 6: Pause allowed/disallowed by plan, schedule shifting on resume, multiple cycles."""
        # A. Disallowed plan
        sub_strict = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.strict_plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0})],
        })
        sub_strict.action_confirm()
        sub_strict.action_activate()
        with self.assertRaises(UserError):
            sub_strict.action_pause()

        # B. Allowed plan with shift
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 2.0})],
        })
        sub.action_confirm()
        sub.action_activate()

        initial_billing_date = date.today() + relativedelta(days=10)
        sub.next_billing_date = initial_billing_date

        # Pause subscription
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')
        self.assertEqual(sub.pause_date, date.today())

        # Simulate 7 days pause
        sub.pause_date = date.today() - relativedelta(days=7)
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertFalse(sub.pause_date)
        self.assertEqual(sub.next_billing_date, initial_billing_date + relativedelta(days=7))

        # Cycle 2: Pause and resume same day -> 0 days shifted
        sub.action_pause()
        sub.action_resume()
        self.assertEqual(sub.next_billing_date, initial_billing_date + relativedelta(days=7))

    def test_10_renewal_active_and_expired(self):
        """Step 7: Renewal allowed/disallowed, duration extension, reactivation of closed contract."""
        # A. Disallowed plan
        sub_strict = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.strict_plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0})],
        })
        sub_strict.action_confirm()
        sub_strict.action_activate()
        with self.assertRaises(UserError):
            sub_strict.action_renew()

        # B. Active subscription renewal
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'expiry_date': date.today() + relativedelta(months=6),
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 2.0})],
        })
        sub.action_confirm()
        with self.assertRaises(UserError):
            sub.action_renew()
        sub.action_activate()
        initial_expiry = sub.expiry_date

        sub.action_renew()
        self.assertEqual(sub.expiry_date, initial_expiry + relativedelta(months=1))
        self.assertEqual(sub.state, 'active')

        sub.action_pause()
        with self.assertRaises(UserError):
            sub.action_renew()

        # C. Expired / Closed subscription renewal
        sub.action_resume()
        sub.state = 'closed'
        sub.close_date = date.today()
        sub.close_reason = "Ended early"
        sub.action_renew()
        self.assertEqual(sub.state, 'active')
        self.assertFalse(sub.close_date)
        self.assertFalse(sub.close_reason)
        self.assertEqual(sub.next_billing_date, date.today())

    def test_11_early_closure_and_manager_override(self):
        """Step 8: Early closure permission, standard user restriction, and manager override."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.strict_plan.id,  # allow_early_close = False
            'expiry_date': date.today() + relativedelta(months=12),
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0})],
        })
        sub.action_confirm()
        sub.action_activate()

        # Standard sales rep cannot early-terminate strict contract
        with self.assertRaises(UserError):
            sub.with_user(self.sales_user).action_close(reason="Customer requested exit")

        # Administrator / Manager can override
        sub.with_user(self.manager_user).action_close(reason="Executive approved exit")
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_date, date.today())
        self.assertEqual(sub.close_reason, "Executive approved exit")

    def test_12_subscription_expiry_and_auto_close(self):
        """Step 4 & 8: Contract expiration, grace period handling, and auto-closing."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,  # auto_close=True, auto_close_days=5
            'start_date': date.today() - relativedelta(months=2),
            'expiry_date': date.today() - relativedelta(days=2),  # expired 2 days ago (within 5-day grace)
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 2.0})],
        })
        sub.action_confirm()
        sub.action_activate()

        # Check expiry within grace period -> marked 'expired'
        sub.action_check_expiry()
        self.assertEqual(sub.state, 'expired')

        # Beyond grace period (e.g. 10 days expired) -> auto-closes
        sub.write({'state': 'active', 'expiry_date': date.today() - relativedelta(days=10)})
        sub.action_check_expiry()
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_date, date.today())

    def test_13_invoice_integration_eligibility(self):
        """Step 11: Generating recurring invoice on active contract; blocked on paused or closed."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2.0,
                'unit_price': 1560.0,
                'tax_ids': [(6, 0, [self.tax_exclusive.id])],
            })],
        })
        sub.action_confirm()
        sub.action_activate()

        # Generate recurring invoice manually
        sub.action_generate_invoice_manual()
        self.assertEqual(sub.invoice_count, 1)
        invoice = sub.invoice_ids[0]

        self.assertEqual(invoice.state, 'confirmed')
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.amount_untaxed, 3270.0)  # 150 plan + 3120 lines
        self.assertEqual(invoice.amount_tax, 312.0)
        self.assertEqual(invoice.amount_total, 3582.0)

        # Paused subscription cannot generate invoice
        sub.action_pause()
        with self.assertRaises(UserError):
            sub.action_generate_invoice_manual()

        # Closed subscription cannot generate invoice
        sub.action_resume()
        sub.action_close()
        with self.assertRaises(UserError):
            sub.action_generate_invoice_manual()

    def test_14_duplicate_sequence_and_idempotency(self):
        """Step 10: Confirmation idempotency and sequence uniqueness."""
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 2.0})],
        })
        sub.action_confirm()
        orig_name = sub.name
        self.assertTrue(orig_name.startswith('SUB-'))

        # Subsequent confirm call on already confirmed contract is disallowed
        with self.assertRaises(UserError):
            sub.action_confirm()
        self.assertEqual(sub.name, orig_name)

        # Separate contract gets unique sequence
        sub2 = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 2.0})],
        })
        sub2.action_confirm()
        self.assertNotEqual(sub2.name, orig_name)
        self.assertTrue(sub2.name.startswith('SUB-'))

    def test_15_currency_fallback_safety(self):
        """Step 10: Currency fallback safety on newly initialized record."""
        sub = self.env['subscription.subscription'].new({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
        })
        sub._compute_currency_id()
        self.assertTrue(sub.currency_id)
        self.assertEqual(sub.currency_id, self.env.company.currency_id)
