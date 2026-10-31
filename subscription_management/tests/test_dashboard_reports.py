# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError, ValidationError, UserError


@tagged('post_install', '-at_install')
class TestDashboardReports(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_manager = cls.env.ref('subscription_management.group_subscription_manager')
        cls.group_user = cls.env.ref('subscription_management.group_subscription_user')
        cls.group_portal = cls.env.ref('subscription_management.group_subscription_portal')

        # Admin User
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Dashboard Admin',
            'login': 'dashboard_admin@brightloop.com',
            'email': 'dashboard_admin@brightloop.com',
            'password': 'AdminSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_manager.id])],
        })

        # Staff User
        cls.staff_user = cls.env['res.users'].sudo().create({
            'name': 'Dashboard Staff',
            'login': 'dashboard_staff@brightloop.com',
            'email': 'dashboard_staff@brightloop.com',
            'password': 'StaffSecurePassword123!',
            'groups_id': [(6, 0, [cls.group_user.id])],
        })

        # Customer 1
        res1 = cls.env['res.users'].register_portal_customer(
            name="Alice Analytics",
            email="alice_dash@brightloop.com",
            password="AliceSecurePass123!"
        )
        cls.customer_user_1 = cls.env['res.users'].browse(res1['user_id'])
        cls.customer_partner_1 = cls.env['res.partner'].browse(res1['partner_id'])

        # Customer 2
        res2 = cls.env['res.users'].register_portal_customer(
            name="Bob Analytics",
            email="bob_dash@brightloop.com",
            password="BobSecurePass123!"
        )
        cls.customer_user_2 = cls.env['res.users'].browse(res2['user_id'])
        cls.customer_partner_2 = cls.env['res.partner'].browse(res2['partner_id'])

        # Subscription Plan
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Monthly Pro Cloud',
            'code': 'CLOUD-PRO',
            'price': 200.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Cloud Storage 1TB',
            'list_price': 200.0,
            'is_subscription': True,
        })

        # Active Subscription for Customer 1
        cls.sub_active_1 = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'plan_id': cls.plan.id,
            'start_date': date.today() - timedelta(days=60),
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 1.0,
                'unit_price': 200.0,
            })]
        })
        cls.sub_active_1._compute_mrr_arr()

        # Active Subscription for Customer 2
        cls.sub_active_2 = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_2.id,
            'plan_id': cls.plan.id,
            'start_date': date.today() - timedelta(days=30),
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 2.0,
                'unit_price': 200.0,
            })]
        })
        cls.sub_active_2._compute_mrr_arr()

        # Draft & Closed Subscriptions (Should NOT be counted as active)
        cls.sub_draft = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'plan_id': cls.plan.id,
            'state': 'draft',
        })
        cls.sub_closed = cls.env['subscription.subscription'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_2.id,
            'plan_id': cls.plan.id,
            'state': 'closed',
        })

        # Invoice 1: Customer 1 (Paid - 200)
        cls.inv_paid = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'subscription_id': cls.sub_active_1.id,
            'invoice_date': date.today() - timedelta(days=20),
            'due_date': date.today() + timedelta(days=10),
            'billing_period_start': date.today() - timedelta(days=20),
            'billing_period_end': date.today() + timedelta(days=10),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 1.0,
                'unit_price': 200.0,
            })]
        })
        cls.pay_success_1 = cls.env['subscription.payment'].with_user(cls.staff_user).create({
            'invoice_id': cls.inv_paid.id,
            'amount': 200.0,
            'payment_method': 'card',
            'payment_date': fields.Datetime.now() - timedelta(days=5),
            'state': 'draft',
        })
        cls.pay_success_1.action_confirm_payment()

        # Invoice 2: Customer 2 (Unpaid / Outstanding - 400, NOT overdue)
        cls.inv_unpaid = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_2.id,
            'subscription_id': cls.sub_active_2.id,
            'invoice_date': date.today() - timedelta(days=5),
            'due_date': date.today() + timedelta(days=15),
            'billing_period_start': date.today() - timedelta(days=5),
            'billing_period_end': date.today() + timedelta(days=25),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 2.0,
                'unit_price': 200.0,
            })]
        })

        # Invoice 3: Customer 1 (OVERDUE - 200, due 10 days ago)
        cls.inv_overdue = cls.env['subscription.invoice'].with_user(cls.staff_user).create({
            'partner_id': cls.customer_partner_1.id,
            'subscription_id': cls.sub_active_1.id,
            'invoice_date': date.today() - timedelta(days=40),
            'due_date': date.today() - timedelta(days=10),
            'billing_period_start': date.today() - timedelta(days=40),
            'billing_period_end': date.today() - timedelta(days=10),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'quantity': 1.0,
                'unit_price': 200.0,
            })]
        })
        cls.inv_overdue._reconcile_payments()

        # Draft and Failed Payments for testing exclusion
        cls.pay_draft = cls.env['subscription.payment'].with_user(cls.staff_user).create({
            'invoice_id': cls.inv_unpaid.id,
            'amount': 150.0,
            'payment_method': 'bank_transfer',
            'state': 'draft',
        })
        cls.pay_failed = cls.env['subscription.payment'].with_user(cls.staff_user).create({
            'invoice_id': cls.inv_unpaid.id,
            'amount': 250.0,
            'payment_method': 'stripe',
            'state': 'draft',
        })
        cls.pay_failed.action_fail_payment(reason="Card processor error")

    # ------------------------------------------------------------
    # 1. ACTIVE SUBSCRIPTION COUNT
    # ------------------------------------------------------------
    def test_01_active_subscription_count(self):
        """1. Active subscription count counts only state='active'."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertEqual(metrics['active_subscriptions'], 2)
        self.assertEqual(metrics['total_subscriptions'], 4)

    # ------------------------------------------------------------
    # 2. REVENUE RECEIVED USES CONFIRMED PAYMENTS ONLY
    # ------------------------------------------------------------
    def test_02_revenue_calculation_confirmed_payments(self):
        """2. Revenue received is the exact sum of state='success' payments."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertEqual(metrics['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 3. DRAFT PAYMENT EXCLUSION
    # ------------------------------------------------------------
    def test_03_draft_payment_exclusion(self):
        """3. Draft payments (150.0) must not be included in revenue."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertNotIn(350.0, [metrics['revenue_received']])
        self.assertEqual(metrics['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 4. FAILED PAYMENT EXCLUSION
    # ------------------------------------------------------------
    def test_04_failed_payment_exclusion(self):
        """4. Failed payments (250.0) must not be included in revenue."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertNotIn(450.0, [metrics['revenue_received']])
        self.assertEqual(metrics['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 5. OUTSTANDING AMOUNT CALCULATION
    # ------------------------------------------------------------
    def test_05_outstanding_amount_calculation(self):
        """5. Outstanding amount = sum of unpaid invoice residuals (400 + 200 = 600)."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertEqual(metrics['outstanding_amount'], 600.0)

    # ------------------------------------------------------------
    # 6. OVERDUE INVOICE CALCULATION
    # ------------------------------------------------------------
    def test_06_overdue_invoice_calculation(self):
        """6. Overdue invoices: only inv_overdue (due 10 days ago, residual 200)."""
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertEqual(metrics['overdue_invoices'], 1)
        self.assertEqual(metrics['overdue_amount'], 200.0)

    # ------------------------------------------------------------
    # 7. DATE-RANGE FILTERS
    # ------------------------------------------------------------
    def test_07_date_range_filters(self):
        """7. Date filters apply correctly to payments."""
        # Today's payments (pay_success_1 was 5 days ago)
        metrics_today = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            date_range='today'
        )
        self.assertEqual(metrics_today['revenue_received'], 0.0)

        # This Month (pay_success_1 occurred this month)
        metrics_month = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            date_range='this_month'
        )
        self.assertEqual(metrics_month['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 8. CUSTOMER-BASED FILTERING
    # ------------------------------------------------------------
    def test_08_customer_based_filtering(self):
        """8. Filtering by customer partner isolates metrics."""
        # Alice Customer 1: 1 active sub, 200 paid, 200 overdue
        m_alice = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            partner_id=self.customer_partner_1.id
        )
        self.assertEqual(m_alice['active_subscriptions'], 1)
        self.assertEqual(m_alice['revenue_received'], 200.0)
        self.assertEqual(m_alice['outstanding_amount'], 200.0)
        self.assertEqual(m_alice['overdue_invoices'], 1)

        # Bob Customer 2: 1 active sub, 0 paid, 400 outstanding, 0 overdue
        m_bob = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            partner_id=self.customer_partner_2.id
        )
        self.assertEqual(m_bob['active_subscriptions'], 1)
        self.assertEqual(m_bob['revenue_received'], 0.0)
        self.assertEqual(m_bob['outstanding_amount'], 400.0)
        self.assertEqual(m_bob['overdue_invoices'], 0)

    # ------------------------------------------------------------
    # 9. SUBSCRIPTION STATUS FILTERING
    # ------------------------------------------------------------
    def test_09_subscription_status_filtering(self):
        """9. Filtering by subscription status works."""
        m_closed = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            subscription_status='closed'
        )
        self.assertEqual(m_closed['total_subscriptions'], 1)

    # ------------------------------------------------------------
    # 10. PAYMENT METHOD FILTERING
    # ------------------------------------------------------------
    def test_10_payment_method_filtering(self):
        """10. Filtering by payment method scopes revenue received."""
        m_card = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            payment_method='card'
        )
        self.assertEqual(m_card['revenue_received'], 200.0)

        m_upi = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            payment_method='upi'
        )
        self.assertEqual(m_upi['revenue_received'], 0.0)

    # ------------------------------------------------------------
    # 11. ROLE-BASED DASHBOARD ACCESS (STAFF & ADMIN)
    # ------------------------------------------------------------
    def test_11_role_based_access_staff_and_admin(self):
        """11. Staff and Admin have full access to dashboard engine."""
        # Staff
        m_staff = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertIsNotNone(m_staff['revenue_received'])

        # Admin
        m_admin = self.env['subscription.dashboard'].with_user(self.admin_user).get_dashboard_metrics()
        self.assertIsNotNone(m_admin['revenue_received'])

    # ------------------------------------------------------------
    # 12. CUSTOMER ACCESS DENIAL (SERVER-SIDE PROTECTION)
    # ------------------------------------------------------------
    def test_12_customer_cannot_access_global_financials(self):
        """12. Portal customers calling get_dashboard_metrics raise AccessError."""
        with self.assertRaises(AccessError):
            self.env['subscription.dashboard'].with_user(self.customer_user_1).get_dashboard_metrics()

    # ------------------------------------------------------------
    # 13. DYNAMIC METRIC UPDATES AFTER PAYMENT SETTLEMENT
    # ------------------------------------------------------------
    def test_13_dashboard_update_after_payment(self):
        """13. Real-time update of revenue received and residual upon payment confirmation."""
        # Confirm Bob's payment of 200 against inv_unpaid (400 total)
        pay_bob = self.env['subscription.payment'].with_user(self.staff_user).create({
            'invoice_id': self.inv_unpaid.id,
            'amount': 200.0,
            'payment_method': 'upi',
            'state': 'draft',
        })
        pay_bob.action_confirm_payment()

        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        # Revenue increased from 200 to 400
        self.assertEqual(metrics['revenue_received'], 400.0)
        # Outstanding decreased from 600 to 400
        self.assertEqual(metrics['outstanding_amount'], 400.0)

    # ------------------------------------------------------------
    # 14. DYNAMIC METRIC UPDATES AFTER INVOICE CHANGES
    # ------------------------------------------------------------
    def test_14_dashboard_update_after_invoice_changes(self):
        """14. Real-time update of outstanding balance upon creating a new confirmed invoice."""
        new_inv = self.env['subscription.invoice'].with_user(self.staff_user).create({
            'partner_id': self.customer_partner_2.id,
            'subscription_id': self.sub_active_2.id,
            'invoice_date': date.today(),
            'due_date': date.today() + timedelta(days=15),
            'billing_period_start': date.today(),
            'billing_period_end': date.today() + timedelta(days=30),
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 100.0,
            })]
        })
        new_inv._reconcile_payments()

        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        # Outstanding increased by 100
        self.assertEqual(metrics['outstanding_amount'], 700.0)

    # ------------------------------------------------------------
    # 15. REGRESSION TEST COMPATIBILITY
    # ------------------------------------------------------------
    def test_15_existing_modules_remain_intact(self):
        """15. Confirms MRR/ARR, discounts, and payments integrate harmoniously."""
        self.assertEqual(self.sub_active_1.mrr, 200.0)
        self.assertEqual(self.sub_active_2.mrr, 400.0)
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics()
        self.assertEqual(metrics['mrr_total'], 600.0)
        self.assertEqual(metrics['arr_total'], 7200.0)

    def test_16_dashboard_overview_matches_live_records(self):
        dashboard = self.env['subscription.dashboard'].with_user(self.staff_user)
        metrics = dashboard.get_dashboard_metrics()
        subscriptions = self.env['subscription.subscription'].with_user(self.staff_user)
        invoices = self.env['subscription.invoice'].with_user(self.staff_user)
        products = self.env['product.template'].with_user(self.staff_user)
        plans = self.env['subscription.plan'].with_user(self.staff_user)

        customer_groups = subscriptions.read_group([], ['partner_id'], ['partner_id'])
        self.assertEqual(metrics['total_customers'], len(customer_groups))
        self.assertEqual(
            metrics['total_products'],
            products.search_count([('is_subscription', '=', True)]),
        )
        self.assertEqual(
            metrics['total_plans'],
            plans.with_context(active_test=False).search_count([]),
        )
        self.assertEqual(
            metrics['total_invoices'],
            invoices.search_count([]),
        )
        self.assertEqual(
            metrics['pending_subscriptions'],
            subscriptions.search_count([('state', 'in', ('draft', 'quotation', 'confirmed'))]),
        )
        self.assertEqual(
            metrics['cancelled_subscriptions'],
            subscriptions.search_count([('state', '=', 'closed')]),
        )
        self.assertEqual(metrics['total_revenue'], metrics['revenue_received'])

    def test_17_subscription_status_and_frequency_filters(self):
        dashboard = self.env['subscription.dashboard'].with_user(self.staff_user)
        active_metrics = dashboard.get_dashboard_metrics(subscription_status='active')
        active_count = self.env['subscription.subscription'].search_count([
            ('state', '=', 'active'),
        ])
        self.assertEqual(active_metrics['total_subscriptions'], active_count)
        self.assertEqual(active_metrics['active_subscriptions'], active_count)
        self.assertEqual(active_metrics['pending_subscriptions'], 0)
        self.assertEqual(active_metrics['cancelled_subscriptions'], 0)

        monthly_metrics = dashboard.get_dashboard_metrics(billing_frequency='monthly')
        expected_monthly = self.env['subscription.subscription'].search_count([
            ('plan_id.billing_interval_unit', '=', 'monthly'),
        ])
        self.assertEqual(monthly_metrics['total_subscriptions'], expected_monthly)

    def test_18_dashboard_empty_customer_filter_returns_zero_activity(self):
        partner = self.env['res.partner'].create({'name': 'Dashboard Empty Customer'})
        metrics = self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
            partner_id=partner.id
        )
        self.assertEqual(metrics['total_customers'], 0)
        self.assertEqual(metrics['total_subscriptions'], 0)
        self.assertEqual(metrics['total_invoices'], 0)
        self.assertEqual(metrics['outstanding_amount'], 0.0)
        self.assertEqual(metrics['total_revenue'], 0.0)

    def test_19_dashboard_console_activity_and_quick_actions(self):
        dashboard = self.env['subscription.dashboard.console'].with_user(self.staff_user).create({
            'date_range_type': 'all',
            'subscription_status': 'all',
            'billing_frequency': 'all',
            'invoice_status': 'all',
            'payment_method': 'all',
        })
        self.assertEqual(
            dashboard.active_subscriptions,
            self.env['subscription.subscription'].search_count([('state', '=', 'active')]),
        )
        self.assertIn(self.sub_active_1, dashboard.recent_subscription_ids)
        self.assertTrue(dashboard.latest_invoice_ids)
        self.assertTrue(all(invoice._name == 'subscription.invoice' for invoice in dashboard.latest_invoice_ids))

        expected_models = {
            'action_create_product': 'product.template',
            'action_create_plan': 'subscription.plan',
            'action_create_quotation': 'subscription.subscription',
            'action_view_invoices': 'subscription.invoice',
        }
        for method_name, model_name in expected_models.items():
            action = getattr(dashboard, method_name)()
            self.assertEqual(action['res_model'], model_name)

        chart_action = dashboard.with_context(
            dashboard_chart='status'
        ).action_open_dashboard_chart()
        self.assertEqual(chart_action['res_model'], 'subscription.subscription')
        self.assertIn(('state', 'in', ('active', 'closed')), chart_action['domain'])

    def test_20_dashboard_custom_date_range_validation(self):
        with self.assertRaises(ValidationError):
            self.env['subscription.dashboard'].with_user(self.staff_user).get_dashboard_metrics(
                date_range='custom',
                date_from=date.today(),
                date_to=date.today() - timedelta(days=1),
            )
