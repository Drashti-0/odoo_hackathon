# -*- coding: utf-8 -*-
"""
End-to-End Integration Test Suite for Developer 1 Modules:
1. Product & Product Variants
2. Subscription Plans
3. Quotation & Subscription Lifecycle
4. Invoice & Automated Billing
5. Cross-Module Integration (Product -> Plan -> Quotation -> Subscription -> Invoice -> Billing)
"""

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError
from psycopg2 import IntegrityError


@tagged('post_install', '-at_install')
class TestDeveloper1Integration(TransactionCase):
    """
    Comprehensive End-to-End Integration Test Suite validating all 4 Developer 1 modules
    and their unified business workflows inside the Odoo ORM environment.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Brightloop Enterprise Client',
            'email': 'enterprise@brightloop.com',
            'street': '100 Technology Parkway',
            'city': 'San Jose',
            'zip': '95110',
        })

        # 2. Taxes (Exclusive and Inclusive)
        cls.tax_exclusive = cls.env['account.tax'].create({
            'name': 'Sales Tax 10% Excl',
            'amount': 10.0,
            'amount_type': 'percent',
            'price_include': False,
            'type_tax_use': 'sale',
        })
        cls.tax_inclusive = cls.env['account.tax'].create({
            'name': 'VAT 20% Incl',
            'amount': 20.0,
            'amount_type': 'percent',
            'price_include': True,
            'type_tax_use': 'sale',
        })

        # 3. Product Attributes for Variants
        cls.attr_storage = cls.env['product.attribute'].create({'name': 'Storage Capacity'})
        cls.val_256 = cls.env['product.attribute.value'].create({
            'name': '256 GB NVMe',
            'attribute_id': cls.attr_storage.id,
        })
        cls.val_512 = cls.env['product.attribute.value'].create({
            'name': '512 GB NVMe',
            'attribute_id': cls.attr_storage.id,
        })

        # 4. Product Template with Odoo Brand (+560.0 Surcharge)
        cls.tmpl_odoo = cls.env['product.template'].create({
            'name': 'Brightloop Dedicated Cloud Server',
            'list_price': 1200.0,
            'standard_price': 600.0,
            'is_subscription': True,
            'brand_name': 'odoo',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.attr_storage.id,
                'value_ids': [(6, 0, [cls.val_256.id, cls.val_512.id])],
            })],
        })
        # Add price extra for 512GB
        attr_line = cls.tmpl_odoo.attribute_line_ids[0]
        val_512_line = cls.tmpl_odoo.attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == cls.val_512
        )
        if val_512_line:
            val_512_line.price_extra = 300.0

        # Retrieve generated variants
        cls.var_256 = cls.tmpl_odoo.product_variant_ids.filtered(
            lambda p: cls.val_256 in p.product_template_attribute_value_ids.product_attribute_value_id
        )
        cls.var_512 = cls.tmpl_odoo.product_variant_ids.filtered(
            lambda p: cls.val_512 in p.product_template_attribute_value_ids.product_attribute_value_id
        )

        # Standard non-Odoo Product (Zero Surcharge)
        cls.tmpl_standard = cls.env['product.template'].create({
            'name': 'Managed Backup Service',
            'list_price': 250.0,
            'is_subscription': True,
            'brand_name': 'standard',
        })
        cls.prod_backup = cls.tmpl_standard.product_variant_id

        # 5. Subscription Plans
        cls.plan_daily = cls.env['subscription.plan'].create({
            'name': 'E2E Daily Hotfix Plan',
            'code': 'PLAN-E2E-DAY',
            'price': 25.0,
            'billing_interval_unit': 'daily',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.plan_weekly = cls.env['subscription.plan'].create({
            'name': 'E2E Weekly Sprint Plan',
            'code': 'PLAN-E2E-WKL',
            'price': 100.0,
            'billing_interval_unit': 'weekly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })
        cls.plan_monthly = cls.env['subscription.plan'].create({
            'name': 'E2E Monthly Enterprise Plan',
            'code': 'PLAN-E2E-MTH',
            'price': 300.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 2.0,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
            'auto_close': True,
            'auto_close_days': 7,
        })
        cls.plan_yearly = cls.env['subscription.plan'].create({
            'name': 'E2E Annual VIP Contract',
            'code': 'PLAN-E2E-YRL',
            'price': 3000.0,
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })

        # Link plans to product template
        cls.tmpl_odoo.subscription_plan_ids = [(6, 0, [cls.plan_monthly.id])]
        cls.tmpl_standard.subscription_plan_ids = [(6, 0, [cls.plan_monthly.id])]

        # 6. Developer 2 Coupons
        cls.coupon_pct = cls.env['subscription.discount'].create({
            'name': 'E2E 15% Launch Coupon',
            'code': 'E2EPROMO15',
            'discount_type': 'percentage',
            'value': 15.0,
            'active': True,
        })

    # =========================================================================
    # WORKFLOW 1: PRODUCT INTEGRATION
    # =========================================================================

    def test_01_product_integration(self):
        """1. Verify Product & Variant Management, pricing surcharges, constraints, and plan linkage."""
        # 1.1 Product Template Surcharge
        self.assertEqual(self.tmpl_odoo.brand_surcharge, 560.0)
        self.assertEqual(self.tmpl_odoo.subscription_price, 1760.0)  # 1200 base + 560 Odoo surcharge

        # 1.2 Variants Pricing
        # 256GB variant: 1200 base + 560 surcharge + 0 extra = 1760.0
        self.assertEqual(self.var_256.brand_surcharge, 560.0)
        self.assertEqual(self.var_256.subscription_price, 1760.0)

        # 512GB variant: 1200 base + 560 surcharge + 300 price_extra = 2060.0
        self.assertEqual(self.var_512.brand_surcharge, 560.0)
        self.assertEqual(self.var_512.subscription_price, 2060.0)

        # Standard Brand Surcharge: must be 0.0
        self.assertEqual(self.tmpl_standard.brand_surcharge, 0.0)
        self.assertEqual(self.tmpl_standard.subscription_price, 250.0)
        self.assertEqual(self.prod_backup.subscription_price, 250.0)

        # 1.3 Negative Price Constraint
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Faulty Product',
                'list_price': -50.0,
                'is_subscription': True,
            })

        # 1.4 Plan Linkage
        self.assertIn(self.plan_monthly, self.tmpl_odoo.subscription_plan_ids)
        self.assertIn(self.plan_monthly, self.tmpl_standard.subscription_plan_ids)

    # =========================================================================
    # WORKFLOW 2: SUBSCRIPTION PLAN INTEGRATION
    # =========================================================================

    def test_02_subscription_plan_integration(self):
        """2. Verify Subscription Plan configuration, cadences, date calculations, and policies."""
        today = date(2026, 1, 31)

        # 2.1 Cadence calculations
        next_daily = self.plan_daily.calculate_next_billing_date(today)
        self.assertEqual(next_daily, date(2026, 2, 1))

        next_weekly = self.plan_weekly.calculate_next_billing_date(today)
        self.assertEqual(next_weekly, date(2026, 2, 7))

        # Month-end clamping: Jan 31 -> Feb 28
        next_monthly = self.plan_monthly.calculate_next_billing_date(today)
        self.assertEqual(next_monthly, date(2026, 2, 28))

        # Yearly cadence
        next_yearly = self.plan_yearly.calculate_next_billing_date(today)
        self.assertEqual(next_yearly, date(2027, 1, 31))

        # 2.2 Plan Validation Constraints
        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Negative Price Plan',
                'price': -10.0,
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Zero Min Qty Plan',
                'price': 50.0,
                'min_quantity': 0.0,
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Inverted Dates Plan',
                'price': 50.0,
                'billing_interval_unit': 'monthly',
                'start_date': date(2026, 6, 1),
                'end_date': date(2026, 5, 1),
            })

        # 2.3 Plan Availability Window Check
        plan_window = self.env['subscription.plan'].create({
            'name': 'Spring 2026 Limited Plan',
            'price': 80.0,
            'billing_interval_unit': 'monthly',
            'start_date': date(2026, 3, 1),
            'end_date': date(2026, 5, 31),
        })
        self.assertFalse(plan_window.is_available_on(date(2026, 2, 28)))
        self.assertTrue(plan_window.is_available_on(date(2026, 4, 15)))
        self.assertFalse(plan_window.is_available_on(date(2026, 6, 1)))

    # =========================================================================
    # WORKFLOW 3: QUOTATION & SUBSCRIPTION LIFECYCLE
    # =========================================================================

    def test_03_quotation_and_subscription_lifecycle(self):
        """3. Verify Quotation creation, sequence changes, state transitions, pause/resume, and renewal."""
        today = date.today()

        # 3.1 Minimum Quantity Validation
        with self.assertRaises(ValidationError):
            self.env['subscription.subscription'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_monthly.id,  # min_quantity = 2.0
                'start_date': today,
                'line_ids': [(0, 0, {
                    'product_id': self.var_256.id,
                    'quantity': 1.0,  # Below min_quantity 2.0
                    'unit_price': 1760.0,
                })],
            })

        # 3.2 Quotation Creation: state = 'draft', sequence = 'SQ-XXXXX'
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': today,
            'line_ids': [
                (0, 0, {
                    'product_id': self.var_512.id,
                    'quantity': 2.0,
                    'unit_price': 2060.0,
                    'tax_ids': [(6, 0, [self.tax_exclusive.id])],
                }),
                (0, 0, {
                    'product_id': self.prod_backup.id,
                    'quantity': 2.0,
                    'unit_price': 250.0,
                }),
            ],
        })
        self.assertEqual(sub.state, 'draft')
        self.assertTrue(sub.name.startswith('SQ-'))

        # Check line totals:
        # Base Plan = 300. Line 1 = 2 * 2060 = 4120 (tax 412). Line 2 = 2 * 250 = 500.
        # Untaxed = 300 + 4120 + 500 = 4920.0. Tax = 412.0. Total = 5332.0.
        self.assertEqual(sub.amount_untaxed, 4920.0)
        self.assertEqual(sub.amount_tax, 412.0)
        self.assertEqual(sub.amount_total, 5332.0)

        # 3.3 Quotation Confirmation: SQ -> SUB contract sequence
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith('SUB-'))

        # 3.4 Price Immutability after confirmation: catalog changes do not alter contract
        self.tmpl_odoo.write({'list_price': 5000.0})
        self.assertEqual(sub.amount_untaxed, 4920.0)
        self.assertEqual(sub.line_ids[0].unit_price, 2060.0)

        # 3.5 Contract Activation
        sub.action_activate()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, today)

        # 3.6 Pause and Resume with Schedule Shift
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')
        self.assertEqual(sub.pause_date, today)

        # Simulating 5 days pause duration
        sub.pause_date = today - timedelta(days=5)
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, today + timedelta(days=5))

        # Reset next_billing_date for billing test
        sub.next_billing_date = today

        # 3.7 Renewal
        old_expiry = today + relativedelta(months=1)
        sub.expiry_date = old_expiry
        expected_new_expiry = self.plan_monthly.calculate_next_billing_date(old_expiry)
        sub.action_renew()
        self.assertEqual(sub.expiry_date, expected_new_expiry)

        # 3.8 Early Closure
        sub.action_close(reason="Customer requested early cancellation")
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_date, today)

    # =========================================================================
    # WORKFLOW 4: INVOICE & AUTOMATED BILLING INTEGRATION
    # =========================================================================

    def test_04_invoice_and_automated_billing_integration(self):
        """4. Verify automated recurring invoice generation, catch-up, idempotency, and audit logging."""
        today = date.today()
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.var_256.id,
                'quantity': 2.0,
                'unit_price': 1760.0,
                'tax_ids': [(6, 0, [self.tax_exclusive.id])],
            })],
        })

        # 4.1 Invoice Generation: Plan (300) + Line (2 * 1760 = 3520, tax 352) = Untaxed 3820, Total 4172
        sub.action_generate_invoice_manual()
        self.assertEqual(sub.invoice_count, 1)
        invoice = sub.invoice_ids[0]

        self.assertEqual(invoice.state, 'confirmed')
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.amount_untaxed, 3820.0)
        self.assertEqual(invoice.amount_tax, 352.0)
        self.assertEqual(invoice.amount_total, 4172.0)
        self.assertEqual(invoice.amount_residual, 4172.0)
        self.assertEqual(invoice.amount_paid, 0.0)
        self.assertEqual(invoice.payment_state, 'not_paid')

        # 4.2 Next Billing Date Milestone Advance
        expected_next = self.plan_monthly.calculate_next_billing_date(today)
        self.assertEqual(sub.next_billing_date, expected_next)
        self.assertEqual(sub.last_billing_date, today)

        # 4.3 Idempotency Check: Immediate re-triggering does NOT create duplicate invoice
        sub.next_billing_date = today  # Attempt to force duplicate
        sub.action_generate_invoice_manual()
        self.assertEqual(sub.invoice_count, 1)

        # 4.4 SQL Database-level Unique Constraint Verification
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['subscription.invoice'].create({
                    'subscription_id': sub.id,
                    'partner_id': self.partner.id,
                    'billing_period_start': invoice.billing_period_start,
                    'billing_period_end': invoice.billing_period_end,
                    'state': 'draft',
                    'line_ids': [(0, 0, {
                        'name': 'Duplicate Test Line',
                        'quantity': 1.0,
                        'unit_price': 100.0,
                    })],
                })

        # 4.5 Billing Log Verification
        logs = self.env['subscription.billing.log'].search([('subscription_id', '=', sub.id)])
        self.assertTrue(len(logs) >= 2)  # 1 success + 1 skipped
        statuses = logs.mapped('status')
        self.assertIn('success', statuses)
        self.assertIn('skipped', statuses)

        # 4.6 Catch-Up Billing for Multiple Missed Cycles
        sub_catchup = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': today - relativedelta(months=3),
            'next_billing_date': today - relativedelta(months=3),
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.prod_backup.id,
                'quantity': 2.0,
                'unit_price': 250.0,
            })],
        })
        sub_catchup._process_recurring_billing_catchup(today)

        # 4 missed cycles caught up -> exactly 4 non-overlapping invoices
        self.assertEqual(len(sub_catchup.invoice_ids), 4)
        sorted_invoices = sub_catchup.invoice_ids.sorted('billing_period_start')
        for i in range(len(sorted_invoices) - 1):
            inv_curr = sorted_invoices[i]
            inv_next = sorted_invoices[i + 1]
            self.assertEqual(inv_curr.billing_period_end + timedelta(days=1), inv_next.billing_period_start)

    # =========================================================================
    # WORKFLOW 5: CROSS-MODULE END-TO-END WORKFLOW
    # =========================================================================

    def test_05_cross_module_end_to_end_workflow(self):
        """5. Full lifecycle: Product Variant -> Plan -> Quotation -> Subscription -> Billing -> Payment -> Close."""
        today = date.today()

        # Step 1: Create Quotation with Variant Product and Monthly Plan
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': today,
            'line_ids': [(0, 0, {
                'product_id': self.var_512.id,
                'quantity': 2.0,
                'unit_price': 2060.0,
            })],
        })
        self.assertEqual(sub.state, 'draft')
        self.assertTrue(sub.name.startswith('SQ-'))

        # Step 2: Confirm and Activate
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith('SUB-'))

        sub.action_activate()
        self.assertEqual(sub.state, 'active')

        # Step 3: Automated Recurring Billing
        sub._process_recurring_billing_catchup(today)
        self.assertEqual(len(sub.invoice_ids), 1)
        invoice = sub.invoice_ids[0]
        # Total: Plan 300 + 2 * 2060 = 4420.0
        self.assertEqual(invoice.amount_total, 4420.0)
        self.assertEqual(invoice.amount_residual, 4420.0)

        # Step 4: Developer 2 Coupon Hook (Reset to draft -> Apply Coupon -> Confirm)
        invoice.action_draft()
        self.assertEqual(invoice.state, 'draft')
        invoice.apply_discount_code(self.coupon_pct.code)
        self.assertEqual(invoice.discount_code, self.coupon_pct.code)
        # 15% discount on 4420.0 = 663.0. Net total = 3757.0
        self.assertEqual(invoice.amount_discount, 663.0)
        self.assertEqual(invoice.amount_total, 3757.0)
        self.assertEqual(invoice.amount_residual, 3757.0)

        invoice.action_confirm()
        self.assertEqual(invoice.state, 'confirmed')

        # Step 5: Developer 2 Partial Payment Hook
        invoice.action_register_payment(amount=1757.0, ref="STRIPE-E2E-PARTIAL")
        self.assertEqual(invoice.payment_state, 'partial')
        self.assertEqual(invoice.state, 'confirmed')
        self.assertEqual(invoice.amount_paid, 1757.0)
        self.assertEqual(invoice.amount_residual, 2000.0)

        # Step 6: Overpayment Guard
        with self.assertRaises(UserError):
            invoice.action_register_payment(amount=2500.0)

        # Step 7: Final Payment Settlement
        invoice.action_register_payment(amount=2000.0, ref="STRIPE-E2E-FINAL")
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertEqual(invoice.state, 'paid')
        self.assertEqual(invoice.amount_paid, 3757.0)
        self.assertEqual(invoice.amount_residual, 0.0)

        # Step 8: QWeb PDF Invoice Report Generation
        report = self.env.ref('subscription_management.action_report_subscription_invoice')
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report, invoice.ids)
        self.assertIn(content_type, ('pdf', 'html'))
        self.assertTrue(len(pdf_content) > 100)

        # Step 9: Contract Expiry and Auto-Closure
        sub.write({
            'start_date': today - relativedelta(months=1),
            'expiry_date': today - relativedelta(days=10),
        })
        sub.action_check_expiry()
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_date, today)
