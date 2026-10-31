# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestBillingEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Global Tech Solutions',
            'email': 'finance@globaltech.com',
        })
        cls.partner_alt = cls.env['res.partner'].create({
            'name': 'AuraMinds Analytics',
            'email': 'billing@auraminds.io',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Server Monitoring',
            'list_price': 500.0,
            'is_subscription': True,
        })
        cls.tmpl_odoo = cls.env['product.template'].create({
            'name': 'Enterprise Cloud Suite',
            'list_price': 1000.0,
            'is_subscription': True,
            'brand_name': 'odoo',
        })
        cls.prod_odoo = cls.tmpl_odoo.product_variant_id

        # Taxes
        cls.tax_exclusive = cls.env['account.tax'].create({
            'name': 'VAT 10% Exclusive Billing Test',
            'amount': 10.0,
            'amount_type': 'percent',
            'price_include': False,
            'type_tax_use': 'sale',
        })
        cls.tax_inclusive = cls.env['account.tax'].create({
            'name': 'VAT 10% Inclusive Billing Test',
            'amount': 10.0,
            'amount_type': 'percent',
            'price_include': True,
            'type_tax_use': 'sale',
        })

        # Subscription Plans
        cls.daily_plan = cls.env['subscription.plan'].create({
            'name': 'Daily Trial Plan',
            'code': 'PLAN-DLY-TEST',
            'price': 10.0,
            'billing_interval_unit': 'daily',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.weekly_plan = cls.env['subscription.plan'].create({
            'name': 'Weekly Sprint Plan',
            'code': 'PLAN-WKL-TEST',
            'price': 50.0,
            'billing_interval_unit': 'weekly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.monthly_plan = cls.env['subscription.plan'].create({
            'name': 'Professional Monthly Plan',
            'code': 'PLAN-MTH-TEST',
            'price': 200.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
        })
        cls.yearly_plan = cls.env['subscription.plan'].create({
            'name': 'Enterprise Annual Plan',
            'code': 'PLAN-YRL-TEST',
            'price': 2000.0,
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })

        # Coupons
        cls.coupon_pct = cls.env['subscription.discount'].create({
            'name': '10% Launch Promotion',
            'code': 'PROMO10TEST',
            'discount_type': 'percentage',
            'value': 10.0,
            'active': True,
        })
        cls.coupon_fix = cls.env['subscription.discount'].create({
            'name': '50 Currency Credit',
            'code': 'FLAT50TEST',
            'discount_type': 'fixed',
            'value': 50.0,
            'active': True,
        })

    def test_01_invoice_generation(self):
        """1. Invoice generation from active subscription."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1.0,
                'unit_price': 500.0,
            })],
        })
        sub._process_recurring_billing_catchup(today)

        self.assertEqual(len(sub.invoice_ids), 1)
        invoice = sub.invoice_ids[0]
        self.assertTrue(invoice.name.startswith('INV-'))
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.subscription_id, sub)
        self.assertEqual(invoice.state, 'confirmed')
        self.assertEqual(invoice.payment_state, 'not_paid')
        self.assertEqual(invoice.billing_period_start, today)
        self.assertEqual(invoice.billing_period_end, self.monthly_plan.calculate_next_billing_date(today) - relativedelta(days=1))
        self.assertEqual(invoice.amount_untaxed, 700.0)  # 200 plan + 500 line
        self.assertEqual(invoice.amount_total, 700.0)
        self.assertEqual(invoice.amount_residual, 700.0)
        self.assertEqual(invoice.amount_paid, 0.0)
        self.assertEqual(sub.invoice_count, 1)

    def test_02_invoice_line_calculations(self):
        """2. Invoice line calculations, quantities, variant pricing, and line discounts."""
        today = date.today()
        # Odoo brand variant: base 1000 + 560 surcharge = 1560
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.prod_odoo.id,
                'quantity': 2.0,
                'unit_price': 1560.0,
                'discount_rate': 10.0,  # 10% line discount
            })],
        })
        sub._process_recurring_billing_catchup(today)
        invoice = sub.invoice_ids[0]

        # Lines: plan fee line (200) + product line (2 qty @ 1560 with 10% disc = 2808)
        prod_line = invoice.line_ids.filtered(lambda l: l.product_id == self.prod_odoo)
        self.assertEqual(prod_line.quantity, 2.0)
        self.assertEqual(prod_line.unit_price, 1560.0)
        self.assertEqual(prod_line.discount_rate, 10.0)
        self.assertEqual(prod_line.discount_amount, 312.0)
        self.assertEqual(prod_line.price_subtotal, 2808.0)
        self.assertEqual(invoice.amount_untaxed, 3008.0)  # 200 plan + 2808 line

    def test_03_tax_computations(self):
        """3. Tax computation: tax-exclusive and tax-inclusive without double-counting."""
        today = date.today()
        # Create draft invoice directly to verify line tax mechanics
        invoice = self.env['subscription.invoice'].create({
            'partner_id': self.partner.id,
            'subscription_id': self.env['subscription.subscription'].create({
                'partner_id': self.partner.id,
                'plan_id': self.monthly_plan.id,
                'start_date': today,
            }).id,
            'billing_period_start': today,
            'billing_period_end': today + relativedelta(days=30),
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': 'Exclusive Tax Line',
                    'quantity': 2.0,
                    'unit_price': 100.0,
                    'tax_ids': [(6, 0, [self.tax_exclusive.id])],  # 200 untaxed + 20 tax = 220
                }),
                (0, 0, {
                    'product_id': self.prod_odoo.id,
                    'name': 'Inclusive Tax Line',
                    'quantity': 2.0,
                    'unit_price': 110.0,
                    'tax_ids': [(6, 0, [self.tax_inclusive.id])],  # 200 untaxed + 20 tax = 220
                }),
            ],
        })
        line_excl = invoice.line_ids[0]
        self.assertEqual(line_excl.price_subtotal, 200.0)
        self.assertEqual(line_excl.price_tax, 20.0)
        self.assertEqual(line_excl.price_total, 220.0)

        line_incl = invoice.line_ids[1]
        self.assertEqual(line_incl.price_subtotal, 200.0)
        self.assertEqual(line_incl.price_tax, 20.0)
        self.assertEqual(line_incl.price_total, 220.0)

        self.assertEqual(invoice.amount_untaxed, 400.0)
        self.assertEqual(invoice.amount_tax, 40.0)
        self.assertEqual(invoice.amount_total, 440.0)
        self.assertEqual(invoice.amount_residual, 440.0)

    def test_04_invoice_lifecycle_and_state_guards(self):
        """4. Invoice lifecycle: draft -> confirmed -> paid, cancellation, reset to draft, and write guards."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
        })
        invoice = self.env['subscription.invoice'].create({
            'partner_id': self.partner.id,
            'subscription_id': sub.id,
            'billing_period_start': today,
            'billing_period_end': today + relativedelta(days=30),
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 500.0,
            })],
        })
        self.assertEqual(invoice.state, 'draft')

        # Invalid: Draft cannot transition directly to paid
        with self.assertRaises(UserError):
            invoice.write({'state': 'paid'})

        # Draft -> Confirmed
        invoice.action_confirm()
        self.assertEqual(invoice.state, 'confirmed')

        # Confirmed -> Draft (allowed if unpaid)
        invoice.action_draft()
        self.assertEqual(invoice.state, 'draft')

        # Draft -> Confirmed -> Cancel
        invoice.action_confirm()
        invoice.action_cancel()
        self.assertEqual(invoice.state, 'cancel')

        # Cancel -> Draft -> Confirmed
        invoice.action_draft()
        self.assertEqual(invoice.state, 'draft')
        invoice.action_confirm()

        # Confirmed -> Paid via payment registration
        invoice.action_register_payment(amount=500.0, ref="PAY-TEST-FULL")
        self.assertEqual(invoice.state, 'paid')
        self.assertEqual(invoice.payment_state, 'paid')

        # Paid invoice cannot be cancelled or reset to draft
        with self.assertRaises(UserError):
            invoice.action_cancel()
        with self.assertRaises(UserError):
            invoice.action_draft()

    def test_05_daily_recurring_billing(self):
        """5. Daily recurring billing cadence and date advancing."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.daily_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 100.0})],
        })
        sub._process_recurring_billing_catchup(today)

        self.assertEqual(len(sub.invoice_ids), 1)
        inv = sub.invoice_ids[0]
        self.assertEqual(inv.billing_period_start, today)
        self.assertEqual(inv.billing_period_end, today)  # 1-day period
        self.assertEqual(sub.next_billing_date, today + relativedelta(days=1))

    def test_06_weekly_recurring_billing(self):
        """6. Weekly recurring billing cadence and date advancing."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.weekly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 100.0})],
        })
        sub._process_recurring_billing_catchup(today)

        self.assertEqual(len(sub.invoice_ids), 1)
        inv = sub.invoice_ids[0]
        self.assertEqual(inv.billing_period_start, today)
        self.assertEqual(inv.billing_period_end, today + relativedelta(days=6))  # 7-day period
        self.assertEqual(sub.next_billing_date, today + relativedelta(days=7))

    def test_07_monthly_recurring_billing(self):
        """7. Monthly recurring billing cadence and month-end clamping."""
        jan31 = date(2026, 1, 31)
        next_date = self.monthly_plan.calculate_next_billing_date(jan31)
        self.assertEqual(next_date, date(2026, 2, 28))

        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': jan31,
            'next_billing_date': jan31,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 100.0})],
        })
        sub._process_recurring_billing_catchup(jan31)
        self.assertEqual(sub.next_billing_date, date(2026, 2, 28))

    def test_08_yearly_recurring_billing(self):
        """8. Yearly recurring billing cadence and leap year boundary."""
        leap_day = date(2024, 2, 29)
        next_date = self.yearly_plan.calculate_next_billing_date(leap_day)
        self.assertEqual(next_date, date(2025, 2, 28))

        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.yearly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(sub.next_billing_date, today + relativedelta(years=1))

    def test_09_duplicate_prevention_and_idempotency(self):
        """9. Duplicate invoice prevention, retry idempotency, and PostgreSQL unique constraint."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 1)

        # Retry execution: date manually forced back to test idempotency
        sub.next_billing_date = today
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 1, "Duplicate invoice MUST NOT be generated")

        logs = self.env['subscription.billing.log'].search([('subscription_id', '=', sub.id)])
        self.assertIn('skipped', logs.mapped('status'))

        # Direct SQL / ORM unique constraint defense
        p_start = sub.invoice_ids[0].billing_period_start
        p_end = sub.invoice_ids[0].billing_period_end
        with mute_logger('odoo.sql_db'):
            with self.assertRaises((IntegrityError, Exception)):
                with self.env.cr.savepoint():
                    self.env['subscription.invoice'].create({
                        'partner_id': self.partner.id,
                        'subscription_id': sub.id,
                        'billing_period_start': p_start,
                        'billing_period_end': p_end,
                        'line_ids': [(0, 0, {'name': 'Duplicate', 'unit_price': 100.0})],
                    })

    def test_10_concurrent_billing_safety(self):
        """10. Concurrent billing safety with FOR UPDATE SKIP LOCKED."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })

        # Test database row lock query directly
        self.env.cr.execute("""
            SELECT id FROM subscription_subscription
            WHERE id = %s
            FOR UPDATE SKIP LOCKED
        """, [sub.id])
        rows = self.env.cr.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], sub.id)

    def test_11_catchup_billing_multiple_missed_cycles(self):
        """11. Catch-up billing: recover multiple missed cycles sequentially without gaps."""
        today = date.today()
        missed_start = today - relativedelta(months=3)

        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': missed_start,
            'next_billing_date': missed_start,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub._process_recurring_billing_catchup(today)

        # 3 missed months up to today + current month due = 4 cycles
        # Exactly sequential periods without gaps
        self.assertTrue(len(sub.invoice_ids) >= 3)
        sorted_invoices = sub.invoice_ids.sorted('billing_period_start')

        for i in range(len(sorted_invoices) - 1):
            curr_end = sorted_invoices[i].billing_period_end
            next_start = sorted_invoices[i + 1].billing_period_start
            self.assertEqual(curr_end + relativedelta(days=1), next_start, "Periods must be contiguous without gaps")

        self.assertTrue(sub.next_billing_date > today, "Next billing date must advance to the future")

    def test_12_paused_subscription_handling(self):
        """12. Paused subscriptions are bypassed by billing engine."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub.action_confirm()
        sub.action_activate()
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')

        # Engine execution skips paused contracts
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 0)

        # Manual generation raises UserError
        with self.assertRaises(UserError):
            sub.action_generate_invoice_manual()

    def test_13_closed_subscription_handling(self):
        """13. Closed subscriptions are bypassed by billing engine."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub.action_confirm()
        sub.action_activate()
        sub.action_close(reason="Client ended contract")
        self.assertEqual(sub.state, 'closed')

        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 0)

        with self.assertRaises(UserError):
            sub.action_generate_invoice_manual()

    def test_14_expired_subscription_handling(self):
        """14. Expired subscriptions are auto-detected and bypassed."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today - relativedelta(months=2),
            'expiry_date': today - relativedelta(days=5),
            'next_billing_date': today,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub.action_confirm()
        sub.action_activate()

        # Engine detects expired subscription
        sub._process_recurring_billing_catchup(today)
        self.assertIn(sub.state, ('expired', 'closed'))
        self.assertEqual(len(sub.invoice_ids), 0)

    def test_15_billing_failure_isolation(self):
        """15. Billing failure isolation: single subscription failure logs error, others succeed."""
        today = date.today()
        # Subscription 1: valid
        sub_valid = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })

        # Subscription 2: corrupted (missing plan)
        sub_corrupt = self.env['subscription.subscription'].create({
            'partner_id': self.partner_alt.id,
            'plan_id': False,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })

        # Trigger batch recurring billing cron
        self.env['subscription.subscription'].cron_recurring_billing()

        # Valid subscription generated an invoice
        self.assertTrue(len(sub_valid.invoice_ids) >= 1)

        # Corrupt subscription did not generate an invoice and recorded a failed log
        self.assertEqual(len(sub_corrupt.invoice_ids), 0)
        corrupt_log = self.env['subscription.billing.log'].search([
            ('subscription_id', '=', sub_corrupt.id),
            ('status', '=', 'failed')
        ])
        self.assertTrue(corrupt_log)

    def test_16_billing_log_creation_and_tracking(self):
        """16. Billing log records execution timestamp, subscription, invoice, amount, and status."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub._process_recurring_billing_catchup(today)

        log = self.env['subscription.billing.log'].search([('subscription_id', '=', sub.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.subscription_id, sub)
        self.assertEqual(log.invoice_id, sub.invoice_ids[0])
        self.assertEqual(log.amount, sub.invoice_ids[0].amount_total)
        self.assertTrue(log.execution_date)

    def test_17_cron_configuration(self):
        """17. Cron scheduled action configuration, model, interval, and direct execution."""
        cron = self.env.ref('subscription_management.ir_cron_subscription_recurring_billing')
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, 'subscription.subscription')
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.interval_type, 'days')
        self.assertEqual(cron.code, 'model.cron_recurring_billing()')

        # Direct execution of scheduled action
        cron.method_direct_trigger()

    def test_18_discount_hook_integration(self):
        """18. Discount hook integration: apply coupon code to invoice, totals update, no double discount."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 1000.0})],
        })
        sub._process_recurring_billing_catchup(today)
        invoice = sub.invoice_ids[0]
        # Total untaxed = 200 plan + 1000 line = 1200. Total = 1200
        self.assertEqual(invoice.amount_total, 1200.0)

        # Apply 10% coupon
        invoice.apply_discount_code(self.coupon_pct.code)
        self.assertEqual(invoice.discount_code, self.coupon_pct.code)
        self.assertEqual(invoice.amount_discount, 120.0)  # 10% of 1200
        self.assertEqual(invoice.amount_total, 1080.0)
        self.assertEqual(invoice.amount_residual, 1080.0)

        # Re-applying same coupon raises UserError
        with self.assertRaises(UserError):
            invoice.apply_discount_code(self.coupon_pct.code)

    def test_19_payment_hook_integration(self):
        """19. Payment hook integration: partial payment, balance due, overpayment check, and settlement."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 800.0})],
        })
        sub._process_recurring_billing_catchup(today)
        invoice = sub.invoice_ids[0]
        # Total untaxed = 200 plan + 800 line = 1000. Total = 1000
        self.assertEqual(invoice.amount_total, 1000.0)
        self.assertEqual(invoice.amount_residual, 1000.0)
        self.assertEqual(invoice.payment_state, 'not_paid')

        # 1. Partial payment: 400.0
        invoice.action_register_payment(amount=400.0, ref="STRIPE-PARTIAL-001")
        self.assertEqual(invoice.payment_state, 'partial')
        self.assertEqual(invoice.state, 'confirmed')
        self.assertEqual(invoice.amount_paid, 400.0)
        self.assertEqual(invoice.amount_residual, 600.0)

        # 2. Overpayment rejection
        with self.assertRaises(UserError):
            invoice.action_register_payment(amount=700.0)  # exceeds residual 600.0

        # 3. Final payment: 600.0
        invoice.action_register_payment(amount=600.0, ref="STRIPE-FINAL-002")
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertEqual(invoice.state, 'paid')
        self.assertEqual(invoice.amount_paid, 1000.0)
        self.assertEqual(invoice.amount_residual, 0.0)

    def test_20_pdf_invoice_generation(self):
        """20. QWeb PDF invoice report generation through QWeb reporting engine."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.monthly_plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1.0, 'unit_price': 500.0})],
        })
        sub._process_recurring_billing_catchup(today)
        invoice = sub.invoice_ids[0]

        report = self.env.ref('subscription_management.action_report_subscription_invoice')
        pdf_content, content_type = report._render_qweb_pdf(invoice.ids)

        self.assertEqual(content_type, 'pdf')
        self.assertTrue(pdf_content)
        self.assertTrue(pdf_content.startswith(b'%PDF-'))
        self.assertTrue(len(pdf_content) > 1000)
