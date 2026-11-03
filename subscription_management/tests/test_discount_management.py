# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError, UserError


@tagged('post_install', '-at_install')
class TestDiscountManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_manager = cls.env.ref('subscription_management.group_subscription_manager')
        cls.group_user = cls.env.ref('subscription_management.group_subscription_user')
        cls.group_portal = cls.env.ref('subscription_management.group_subscription_portal')

        # Admin user
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Discount Admin',
            'login': 'discount_admin@brightloop.com',
            'email': 'discount_admin@brightloop.com',
            'password': 'AdminSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_manager.id])],
        })

        # Staff user
        cls.staff_user = cls.env['res.users'].with_user(cls.admin_user).create({
            'name': 'Discount Staff',
            'login': 'discount_staff@brightloop.com',
            'email': 'discount_staff@brightloop.com',
            'password': 'StaffSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_user.id])],
        })

        # Customer user
        res_customer = cls.env['res.users'].register_portal_customer(
            name="Discount Customer",
            email="disc_customer@brightloop.com",
            password="CustomerSecurePass123!"
        )
        cls.customer_user = cls.env['res.users'].browse(res_customer['user_id'])
        cls.customer_partner = cls.env['res.partner'].browse(res_customer['partner_id'])

        # Products
        cls.product_a = cls.env['product.product'].create({
            'name': 'Software License Standard',
            'list_price': 100.0,
            'is_subscription': True,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Premium Support Tier',
            'list_price': 200.0,
            'is_subscription': True,
        })

        # Plan
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Standard Monthly Plan',
            'price': 50.0,
            'billing_interval_unit': 'monthly',
        })

        # Admin-created Standard Discounts
        cls.disc_percent = cls.env['subscription.discount'].with_user(cls.admin_user).create({
            'name': 'Ten Percent Off',
            'code': 'SAVE10',
            'discount_type': 'percentage',
            'value': 10.0,
        })
        cls.disc_fixed = cls.env['subscription.discount'].with_user(cls.admin_user).create({
            'name': 'Twenty Dollars Off',
            'code': 'SAVE20',
            'discount_type': 'fixed',
            'value': 20.0,
        })

    # ------------------------------------------------------------
    # 1-5: DISCOUNT CALCULATION TESTS
    # ------------------------------------------------------------
    def test_01_fixed_amount_discount(self):
        """1. Fixed amount discount deduction."""
        amt = self.disc_fixed.calculate_discount_amount(subtotal=150.0)
        self.assertEqual(amt, 20.0)

    def test_02_percentage_discount(self):
        """2. Percentage discount deduction."""
        amt = self.disc_percent.calculate_discount_amount(subtotal=200.0)
        self.assertEqual(amt, 20.0)

    def test_03_percentage_discount_boundary_validation(self):
        """3. Percentage discount boundary validation (<= 0 or > 100 rejected)."""
        with self.assertRaises(ValidationError):
            self.env['subscription.discount'].with_user(self.admin_user).create({
                'name': 'Negative Percentage',
                'code': 'BAD_NEG',
                'discount_type': 'percentage',
                'value': -5.0,
            })
        with self.assertRaises(ValidationError):
            self.env['subscription.discount'].with_user(self.admin_user).create({
                'name': 'Over 100 Percentage',
                'code': 'BAD_OVER',
                'discount_type': 'percentage',
                'value': 105.0,
            })

    def test_04_fixed_discount_validation(self):
        """4. Fixed discount validation (<= 0 rejected)."""
        with self.assertRaises(ValidationError):
            self.env['subscription.discount'].with_user(self.admin_user).create({
                'name': 'Zero Fixed',
                'code': 'BAD_ZERO',
                'discount_type': 'fixed',
                'value': 0.0,
            })

    def test_05_discount_cannot_exceed_eligible_amount(self):
        """5. Fixed discount cannot exceed eligible amount (clamped)."""
        large_fixed = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Large Fixed',
            'code': 'BIG500',
            'discount_type': 'fixed',
            'value': 500.0,
        })
        amt = large_fixed.calculate_discount_amount(subtotal=100.0)
        self.assertEqual(amt, 100.0, "Discount must be clamped to eligible subtotal")

    # ------------------------------------------------------------
    # 6-11: ELIGIBILITY TESTS
    # ------------------------------------------------------------
    def test_06_min_purchase_amount_satisfied(self):
        """6. Minimum purchase amount satisfied."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Min Purchase $100',
            'code': 'MIN100',
            'discount_type': 'fixed',
            'value': 10.0,
            'min_purchase_amount': 100.0,
        })
        is_eligible, _ = disc.check_eligibility(subtotal=150.0)
        self.assertTrue(is_eligible)

    def test_07_min_purchase_amount_not_satisfied(self):
        """7. Minimum purchase amount not satisfied."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Min Purchase $100',
            'code': 'MIN100_FAIL',
            'discount_type': 'fixed',
            'value': 10.0,
            'min_purchase_amount': 100.0,
        })
        is_eligible, reason = disc.check_eligibility(subtotal=80.0)
        self.assertFalse(is_eligible)
        self.assertIn("minimum purchase requirement", reason)

    def test_08_min_quantity_satisfied(self):
        """8. Minimum quantity satisfied."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Min Qty 3',
            'code': 'QTY3_PASS',
            'discount_type': 'percentage',
            'value': 10.0,
            'min_quantity': 3.0,
        })
        is_eligible, _ = disc.check_eligibility(subtotal=100.0, total_quantity=5.0)
        self.assertTrue(is_eligible)

    def test_09_min_quantity_not_satisfied(self):
        """9. Minimum quantity not satisfied."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Min Qty 3',
            'code': 'QTY3_FAIL',
            'discount_type': 'percentage',
            'value': 10.0,
            'min_quantity': 3.0,
        })
        is_eligible, reason = disc.check_eligibility(subtotal=100.0, total_quantity=2.0)
        self.assertFalse(is_eligible)
        self.assertIn("minimum required quantity", reason)

    def test_10_product_specific_discount(self):
        """10. Product-specific discount eligibility."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Product A Only',
            'code': 'PRODA_ONLY',
            'discount_type': 'fixed',
            'value': 15.0,
            'applicable_product_ids': [(6, 0, [self.product_a.id])],
            'apply_to_whole_subscription': False,
        })
        # Eligible product passed
        is_ok, _ = disc.check_eligibility(subtotal=100.0, product_ids=[self.product_a.id])
        self.assertTrue(is_ok)
        # Ineligible product passed
        is_fail, _ = disc.check_eligibility(subtotal=100.0, product_ids=[self.product_b.id])
        self.assertFalse(is_fail)

    def test_11_whole_subscription_discount(self):
        """11. Whole subscription discount applies across total."""
        self.assertTrue(self.disc_percent.apply_to_whole_subscription)
        amt = self.disc_percent.calculate_discount_amount(subtotal=500.0)
        self.assertEqual(amt, 50.0)

    def _create_coupon_test_subscription(self, **values):
        subscription_values = {
            'partner_id': self.customer_partner.id,
            'plan_id': self.plan.id,
            'state': 'draft',
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })],
        }
        subscription_values.update(values)
        return self.env['subscription.subscription'].with_user(self.staff_user).create(subscription_values)

    def test_subscription_form_applies_valid_coupon_with_updated_total(self):
        sub = self._create_coupon_test_subscription()

        result = sub.action_apply_discount_code(code='SAVE10')

        self.assertEqual(sub.discount_id, self.disc_percent)
        self.assertEqual(sub.discount_code, 'SAVE10')
        self.assertEqual(sub.discount_rate, 0.0)
        self.assertEqual(sub.amount_discount, 15.0)
        self.assertEqual(sub.amount_total, 135.0)
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        self.assertIn('135.00', result['params']['message'])

    def test_subscription_form_rejects_invalid_coupon_without_applying(self):
        sub = self._create_coupon_test_subscription(discount_rate=5.0)
        original_total = sub.amount_total

        with self.assertRaises(UserError):
            sub.action_apply_discount_code(code='NOT-A-COUPON')

        self.assertFalse(sub.discount_id)
        self.assertEqual(sub.discount_rate, 5.0)
        self.assertEqual(sub.amount_total, original_total)

    def test_subscription_form_rejects_expired_coupon_without_applying(self):
        expired = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Expired Coupon',
            'code': 'EXPIRED_SUB',
            'discount_type': 'percentage',
            'value': 20.0,
            'end_date': date.today() - relativedelta(days=1),
        })
        sub = self._create_coupon_test_subscription(discount_rate=5.0)
        original_total = sub.amount_total

        with self.assertRaises(UserError):
            sub.action_apply_discount_code(code=expired.code)

        self.assertFalse(sub.discount_id)
        self.assertEqual(sub.discount_rate, 5.0)
        self.assertEqual(sub.amount_total, original_total)

    def test_subscription_form_rejects_inactive_coupon_without_applying(self):
        inactive = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Inactive Coupon',
            'code': 'INACTIVE_SUB',
            'discount_type': 'percentage',
            'value': 20.0,
            'active': False,
        })
        sub = self._create_coupon_test_subscription(discount_rate=5.0)
        original_total = sub.amount_total

        with self.assertRaises(UserError):
            sub.action_apply_discount_code(code=inactive.code)

        self.assertFalse(sub.discount_id)
        self.assertEqual(sub.discount_rate, 5.0)
        self.assertEqual(sub.amount_total, original_total)

    def test_subscription_form_rejects_coupon_for_unselected_products(self):
        product_specific = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Product A Coupon',
            'code': 'ONLY_PRODA_SUB',
            'discount_type': 'percentage',
            'value': 20.0,
            'applicable_product_ids': [(6, 0, [self.product_a.id])],
            'apply_to_whole_subscription': False,
        })
        sub = self._create_coupon_test_subscription(line_ids=[(0, 0, {
            'product_id': self.product_b.id,
            'name': self.product_b.name,
            'quantity': 1.0,
            'unit_price': 200.0,
        })])
        original_total = sub.amount_total

        with self.assertRaises(UserError):
            sub.action_apply_discount_code(code=product_specific.code)

        self.assertFalse(sub.discount_id)
        self.assertEqual(sub.amount_total, original_total)

    def test_subscription_form_does_not_apply_same_coupon_twice(self):
        sub = self._create_coupon_test_subscription()
        sub.action_apply_discount_code(code='SAVE10')
        original_discount = sub.amount_discount
        original_total = sub.amount_total

        result = sub.action_apply_discount_code(code='save10')

        self.assertEqual(sub.discount_id, self.disc_percent)
        self.assertEqual(sub.amount_discount, original_discount)
        self.assertEqual(sub.amount_total, original_total)
        self.assertEqual(result['params']['type'], 'info')
        self.assertIn('already applied', result['params']['message'])

    # ------------------------------------------------------------
    # 12-18: DATE & USAGE TESTS
    # ------------------------------------------------------------
    def test_12_discount_before_start_date(self):
        """12. Discount before start date is rejected."""
        future_start = date.today() + relativedelta(days=10)
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Future Coupon',
            'code': 'FUTURE',
            'discount_type': 'fixed',
            'value': 10.0,
            'start_date': future_start,
        })
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("not active yet", reason)

    def test_13_discount_within_valid_date_range(self):
        """13. Discount within valid date range is accepted."""
        today = date.today()
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Valid Window',
            'code': 'VALID_NOW',
            'discount_type': 'percentage',
            'value': 15.0,
            'start_date': today - relativedelta(days=5),
            'end_date': today + relativedelta(days=5),
        })
        is_ok, _ = disc.check_eligibility()
        self.assertTrue(is_ok)

    def test_14_expired_discount(self):
        """14. Expired discount is rejected."""
        past_end = date.today() - relativedelta(days=2)
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Past Coupon',
            'code': 'EXPIRED',
            'discount_type': 'percentage',
            'value': 20.0,
            'end_date': past_end,
        })
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("has expired", reason)

    def test_15_usage_limit_reached(self):
        """15. Usage limit reached rejects redemption."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Limited Use',
            'code': 'LIMIT1',
            'discount_type': 'fixed',
            'value': 10.0,
            'usage_limit': 1,
        })
        # First use
        disc.record_usage()
        self.assertEqual(disc.usage_count, 1)

        # Second attempt must be rejected
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("maximum usage limit", reason)

    def test_16_usage_limit_not_reached(self):
        """16. Usage limit not reached allows redemption."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Limit 5',
            'code': 'LIMIT5',
            'discount_type': 'fixed',
            'value': 10.0,
            'usage_limit': 5,
        })
        disc.record_usage()
        self.assertEqual(disc.usage_count, 1)
        is_ok, _ = disc.check_eligibility()
        self.assertTrue(is_ok)

    def test_17_concurrent_usage_limit_protection(self):
        """17. Usage limit protection enforces boundary under concurrency."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Strict Single',
            'code': 'STRICT1',
            'discount_type': 'fixed',
            'value': 10.0,
            'usage_limit': 1,
        })
        disc.record_usage()
        with self.assertRaises(UserError):
            disc.record_usage()
        self.assertEqual(disc.usage_count, 1, "Rejected usage must not increment the coupon count")

    def test_18_usage_count_not_duplicated(self):
        """18. Usage count is not incremented on re-computation."""
        disc = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'No Dupe',
            'code': 'NODUPE',
            'discount_type': 'fixed',
            'value': 10.0,
            'usage_limit': 10,
        })
        initial = disc.usage_count
        disc.calculate_discount_amount(subtotal=100.0)
        disc.calculate_discount_amount(subtotal=100.0)
        self.assertEqual(disc.usage_count, initial, "Calculations must not increment usage count")

    # ------------------------------------------------------------
    # 19-24: BILLING ENGINE INTEGRATION TESTS
    # ------------------------------------------------------------
    def test_19_automatic_discount_application_during_invoice_generation(self):
        """19. Invoices generated from subscription automatically inherit active discount."""
        sub = self.env['subscription.subscription'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'plan_id': self.plan.id,
            'state': 'active',
            'start_date': date.today(),
            'discount_id': self.disc_fixed.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })]
        })
        sub._compute_amounts()
        # Plan 50 + Product 100 = 150 gross. Discount 20. Net = 130.
        self.assertEqual(sub.amount_discount, 20.0)
        self.assertEqual(sub.amount_total, 130.0)

        # Trigger recurring billing
        sub._process_recurring_billing_catchup(target_date=date.today())
        self.assertEqual(len(sub.invoice_ids), 1)
        inv = sub.invoice_ids[0]
        self.assertEqual(inv.discount_id, self.disc_fixed)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 130.0)

    def test_20_discount_appears_correctly_in_invoice_totals(self):
        """20. Discount deductions reflect accurately in invoice totals."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 2.0,
                'unit_price': 100.0,
            })],
            'discount_id': self.disc_percent.id,
        })
        inv._compute_amounts()
        # 2 * 100 = 200 gross. 10% discount = 20. Total = 180.
        self.assertEqual(inv.amount_untaxed, 200.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 180.0)

    def test_21_repeated_invoice_calculation_does_not_duplicate_discount(self):
        """21. Repeated invoice calculations are strictly idempotent."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })],
            'discount_id': self.disc_fixed.id,
        })
        inv._compute_amounts()
        first_total = inv.amount_total
        self.assertEqual(first_total, 80.0)

        # Run 5 more times
        for _ in range(5):
            inv._compute_amounts()
        self.assertEqual(inv.amount_total, 80.0, "Repeated compute MUST NOT compound discounts")

    def test_22_invoice_retry_does_not_duplicate_discount(self):
        """22. Billing retry does not increment discount usage count twice."""
        sub = self.env['subscription.subscription'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'plan_id': self.plan.id,
            'state': 'active',
            'start_date': date.today(),
            'discount_id': self.disc_fixed.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })]
        })
        initial_usage = self.disc_fixed.usage_count
        sub._process_recurring_billing_catchup(target_date=date.today())
        new_usage = self.disc_fixed.usage_count
        self.assertEqual(new_usage, initial_usage + 1)

        # Retry billing on same date (Idempotency check)
        sub.next_billing_date = date.today()
        sub._process_recurring_billing_catchup(target_date=date.today())
        self.assertEqual(self.disc_fixed.usage_count, new_usage, "Duplicate retry MUST NOT increment usage count")

    def test_23_tax_calculation_remains_correct(self):
        """23. Tax calculation sequence is preserved."""
        # Gross = 100, line discount = 0. Price subtotal = 100.
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })],
            'discount_id': self.disc_fixed.id, # $20 discount
        })
        inv._compute_amounts()
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 80.0)

    def test_24_existing_billing_engine_remains_functional(self):
        """24. Standard invoices without discounts calculate normally."""
        inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner.id,
            'billing_period_start': date(2026, 1, 1),
            'billing_period_end': date(2026, 1, 31),
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })],
        })
        inv._compute_amounts()
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_discount, 0.0)
        self.assertEqual(inv.amount_total, 100.0)

    # ------------------------------------------------------------
    # 25-28: SECURITY TESTS
    # ------------------------------------------------------------
    def test_25_admin_can_create_discounts(self):
        """25. Admin can create and modify discount rules."""
        rule = self.env['subscription.discount'].with_user(self.admin_user).create({
            'name': 'Admin Promo',
            'code': 'ADMIN_PROMO',
            'discount_type': 'fixed',
            'value': 25.0,
        })
        self.assertTrue(rule.id)
        rule.write({'name': 'Admin Promo Updated'})
        self.assertEqual(rule.name, 'Admin Promo Updated')

    def test_26_internal_staff_cannot_create_or_modify_discounts(self):
        """26. Internal Staff cannot create or modify discount rules."""
        with self.assertRaises(AccessError):
            self.env['subscription.discount'].with_user(self.staff_user).create({
                'name': 'Staff Unauthorized Promo',
                'code': 'STAFF_BAD',
                'discount_type': 'percentage',
                'value': 10.0,
            })
        with self.assertRaises(AccessError):
            self.disc_percent.with_user(self.staff_user).write({'value': 50.0})

    def test_27_customers_cannot_create_or_modify_discounts(self):
        """27. Portal Customers cannot create or modify discount rules."""
        with self.assertRaises(AccessError):
            self.env['subscription.discount'].with_user(self.customer_user).create({
                'name': 'Hacker Customer Promo',
                'code': 'FREE_HACK',
                'discount_type': 'percentage',
                'value': 99.0,
            })
        with self.assertRaises(AccessError):
            self.disc_fixed.with_user(self.customer_user).write({'value': 1000.0})

    def test_28_unauthorized_rpc_requests_are_rejected(self):
        """28. Unauthorized delete or write via RPC is blocked at ORM level."""
        with self.assertRaises(AccessError):
            self.disc_fixed.with_user(self.customer_user).unlink()
        with self.assertRaises(AccessError):
            self.disc_fixed.with_user(self.staff_user).unlink()
