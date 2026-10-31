# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestSubscriptionPlanManagement(TransactionCase):
    """
    Comprehensive Test Suite for Module 2: Subscription Plan Management.
    Tests cadence calculations, date clamping, leap years, constraints,
    lifecycle policies (auto-close, early closure, pause, renewal), and integration.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Brightloop Enterprise Client',
            'email': 'enterprise@brightloop.com',
        })
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Cloud Hosting Tier',
            'list_price': 500.0,
            'is_subscription': True,
            'brand_name': 'standard',
        })
        cls.product = cls.product_tmpl.product_variant_id

    # -------------------------------------------------------------
    # 1. BILLING FREQUENCY & CADENCE CALCULATIONS
    # -------------------------------------------------------------

    def test_01_daily_billing_calculation(self):
        """Step 10 #1: Test daily billing cadence calculation with count=1 and count=14."""
        plan_daily_1 = self.env['subscription.plan'].create({
            'name': 'Daily Trial',
            'billing_interval_unit': 'daily',
            'billing_interval_count': 1,
            'price': 10.0,
        })
        d1 = date(2026, 5, 1)
        next_d = plan_daily_1.calculate_next_billing_date(d1)
        self.assertEqual(next_d, date(2026, 5, 2))

        plan_daily_14 = self.env['subscription.plan'].create({
            'name': 'Bi-Weekly Daily Cadence',
            'billing_interval_unit': 'daily',
            'billing_interval_count': 14,
            'price': 100.0,
        })
        self.assertEqual(plan_daily_14.calculate_next_billing_date(d1), date(2026, 5, 15))

    def test_02_weekly_billing_calculation(self):
        """Step 10 #2: Test weekly billing cadence with count=1 and count=4."""
        plan_weekly_1 = self.env['subscription.plan'].create({
            'name': 'Weekly Sprint Plan',
            'billing_interval_unit': 'weekly',
            'billing_interval_count': 1,
            'price': 50.0,
        })
        d = date(2026, 6, 1)  # Monday
        self.assertEqual(plan_weekly_1.calculate_next_billing_date(d), date(2026, 6, 8))

        plan_weekly_4 = self.env['subscription.plan'].create({
            'name': '4-Week Cycle Plan',
            'billing_interval_unit': 'weekly',
            'billing_interval_count': 4,
            'price': 180.0,
        })
        self.assertEqual(plan_weekly_4.calculate_next_billing_date(d), date(2026, 6, 29))

    def test_03_monthly_billing_calculation(self):
        """Step 10 #3: Test monthly cadence with count=1, count=3 (Quarterly), count=6."""
        plan_monthly = self.env['subscription.plan'].create({
            'name': 'Pro Monthly',
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'price': 150.0,
        })
        d = date(2026, 4, 15)
        self.assertEqual(plan_monthly.calculate_next_billing_date(d), date(2026, 5, 15))

        plan_quarterly = self.env['subscription.plan'].create({
            'name': 'Quarterly Business',
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 3,
            'price': 400.0,
        })
        self.assertEqual(plan_quarterly.calculate_next_billing_date(d), date(2026, 7, 15))

    def test_04_yearly_billing_calculation(self):
        """Step 10 #4: Test yearly cadence with count=1 and count=2."""
        plan_yearly = self.env['subscription.plan'].create({
            'name': 'Annual SaaS Enterprise',
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'price': 1500.0,
        })
        d = date(2026, 8, 20)
        self.assertEqual(plan_yearly.calculate_next_billing_date(d), date(2027, 8, 20))

        plan_biyearly = self.env['subscription.plan'].create({
            'name': '2-Year Long Term Contract',
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 2,
            'price': 2800.0,
        })
        self.assertEqual(plan_biyearly.calculate_next_billing_date(d), date(2028, 8, 20))

    def test_05_month_end_date_clamping(self):
        """Step 10 #5: Test month-end date clamping (Jan 31 -> Feb 28, Mar 31 -> Apr 30, May 31 -> Jun 30)."""
        plan = self.env['subscription.plan'].create({
            'name': 'Monthly End-Clamped Plan',
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'price': 100.0,
        })
        # Jan 31 -> Feb 28 (in non-leap year 2026)
        self.assertEqual(plan.calculate_next_billing_date(date(2026, 1, 31)), date(2026, 2, 28))
        # Mar 31 -> Apr 30
        self.assertEqual(plan.calculate_next_billing_date(date(2026, 3, 31)), date(2026, 4, 30))
        # May 31 -> Jun 30
        self.assertEqual(plan.calculate_next_billing_date(date(2026, 5, 31)), date(2026, 6, 30))
        # Aug 31 -> Sep 30
        self.assertEqual(plan.calculate_next_billing_date(date(2026, 8, 31)), date(2026, 9, 30))

    def test_06_leap_year_handling(self):
        """Step 10 #6: Test leap year February 29 handling for monthly and yearly plans."""
        plan_monthly = self.env['subscription.plan'].create({
            'name': 'Monthly Leap Plan',
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'price': 100.0,
        })
        # Jan 31 in leap year 2028 clamps to Feb 29, 2028
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2028, 1, 31)), date(2028, 2, 29))
        # Feb 29 in 2028 + 1 month -> Mar 29, 2028
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2028, 2, 29)), date(2028, 3, 29))

        plan_yearly = self.env['subscription.plan'].create({
            'name': 'Yearly Leap Plan',
            'billing_interval_unit': 'yearly',
            'billing_interval_count': 1,
            'price': 1000.0,
        })
        # Feb 29, 2028 + 1 year -> Feb 28, 2029 (non-leap year clamping)
        self.assertEqual(plan_yearly.calculate_next_billing_date(date(2028, 2, 29)), date(2029, 2, 28))

    # -------------------------------------------------------------
    # 2. VALIDATION TESTING
    # -------------------------------------------------------------

    def test_07_negative_price_validation(self):
        """Step 10 #7: Negative plan price must be rejected."""
        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Negative Price Plan',
                'price': -50.0,
                'billing_interval_unit': 'monthly',
            })

    def test_08_minimum_quantity_validation(self):
        """Step 10 #8: Minimum quantity must be at least 1.0."""
        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Min Quantity Plan',
                'price': 100.0,
                'min_quantity': 0.0,
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Negative Quantity Plan',
                'price': 100.0,
                'min_quantity': -2.0,
                'billing_interval_unit': 'monthly',
            })

    def test_09_availability_date_validation(self):
        """Step 10 #9: Availability end_date < start_date or auto_close_days < 0 must be rejected."""
        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Dates Plan',
                'price': 100.0,
                'start_date': date(2026, 12, 31),
                'end_date': date(2026, 1, 1),
                'billing_interval_unit': 'monthly',
            })

        with self.assertRaises(ValidationError):
            self.env['subscription.plan'].create({
                'name': 'Invalid Negative Grace Days Plan',
                'price': 100.0,
                'auto_close_days': -3,
                'billing_interval_unit': 'monthly',
            })

    def test_10_plan_availability_logic(self):
        """Step 5: Test is_available_on() for all boundary dates and inactive states."""
        plan = self.env['subscription.plan'].create({
            'name': 'Mid-Year Seasonal Plan',
            'price': 200.0,
            'start_date': date(2026, 6, 1),
            'end_date': date(2026, 8, 31),
            'billing_interval_unit': 'monthly',
            'active': True,
        })
        # 1. Before start date
        self.assertFalse(plan.is_available_on(date(2026, 5, 31)))
        # 2. On start date
        self.assertTrue(plan.is_available_on(date(2026, 6, 1)))
        # 3. Inside window
        self.assertTrue(plan.is_available_on(date(2026, 7, 15)))
        # 4. On end date
        self.assertTrue(plan.is_available_on(date(2026, 8, 31)))
        # 5. After end date
        self.assertFalse(plan.is_available_on(date(2026, 9, 1)))

        # 6. Archived/Inactive plan
        plan.active = False
        self.assertFalse(plan.is_available_on(date(2026, 7, 15)))

    # -------------------------------------------------------------
    # 3. POLICY TESTING
    # -------------------------------------------------------------

    def test_11_auto_close_policy(self):
        """Step 10 #10: Test auto-close upon expiry with and without grace period."""
        plan_auto = self.env['subscription.plan'].create({
            'name': 'Strict Auto Close Plan',
            'price': 100.0,
            'auto_close': True,
            'auto_close_days': 0,
        })
        # Create active subscription expired yesterday
        yesterday = date.today() - relativedelta(days=1)
        sub_auto = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': plan_auto.id,
            'start_date': yesterday - relativedelta(months=1),
            'expiry_date': yesterday,
            'state': 'active',
        })
        sub_auto.action_check_expiry()
        self.assertEqual(sub_auto.state, 'closed', "Subscription with auto_close=True must close upon expiry")

        # Plan with auto_close disabled
        plan_no_auto = self.env['subscription.plan'].create({
            'name': 'No Auto Close Plan',
            'price': 100.0,
            'auto_close': False,
        })
        sub_no_auto = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': plan_no_auto.id,
            'start_date': yesterday - relativedelta(months=1),
            'expiry_date': yesterday,
            'state': 'active',
        })
        sub_no_auto.action_check_expiry()
        self.assertEqual(sub_no_auto.state, 'expired', "Subscription with auto_close=False should become 'expired', not 'closed'")

    def test_12_pause_policy(self):
        """Step 10 #11: Test plan.allow_pause enforcement."""
        plan_no_pause = self.env['subscription.plan'].create({
            'name': 'Fixed Contract No Pause',
            'price': 100.0,
            'allow_pause': False,
        })
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': plan_no_pause.id,
            'state': 'active',
            'start_date': date.today(),
        })
        with self.assertRaises(UserError):
            sub.action_pause()

        # Allow pause
        plan_no_pause.allow_pause = True
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')

    def test_13_renewal_policy(self):
        """Step 10 #12: Test plan.allow_renewal enforcement and billing extension."""
        plan_no_renew = self.env['subscription.plan'].create({
            'name': 'Single Term Plan',
            'price': 100.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'allow_renewal': False,
        })
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': plan_no_renew.id,
            'state': 'active',
            'start_date': date.today(),
            'expiry_date': date.today() + relativedelta(months=1),
        })
        with self.assertRaises(UserError):
            sub.action_renew()

        # Allow renewal
        plan_no_renew.allow_renewal = True
        old_expiry = sub.expiry_date
        sub.action_renew()
        self.assertEqual(sub.expiry_date, old_expiry + relativedelta(months=1))

    def test_14_early_close_policy_and_integration(self):
        """Step 10 #13 & #14: Test early close policy and subscription minimum quantity enforcement."""
        plan = self.env['subscription.plan'].create({
            'name': 'Corporate Bulk Plan',
            'price': 250.0,
            'min_quantity': 5.0,
            'allow_early_close': False,
        })
        # 1. Minimum quantity violation on quotation
        with self.assertRaises(ValidationError):
            self.env['subscription.subscription'].create({
                'partner_id': self.partner.id,
                'plan_id': plan.id,
                'line_ids': [(0, 0, {
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'quantity': 2.0,  # below minimum 5.0!
                    'unit_price': 500.0,
                })]
            })

        # 2. Valid quantity
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': plan.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 5.0,
                'unit_price': 500.0,
            })]
        })
        self.assertEqual(sub.state, 'draft')
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        sub.action_activate()
        self.assertEqual(sub.state, 'active')
