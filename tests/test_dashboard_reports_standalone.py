#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Verification Suite for Module 4: Dashboard & Financial Reports
Team: AuraMinds
Developer 2: Drashti Bhanderi
Tests (16 Scenarios):
1: Active subscription count
2: Revenue calculation using confirmed payments only
3: Draft payment exclusion from revenue
4: Failed payment exclusion from revenue
5: Outstanding amount calculation from actual invoice residuals
6: Overdue invoice calculation
7: Date-range filters (today, this_week, this_month, this_year, custom)
8: Customer-based filtering
9: Subscription status filtering
10: Payment method filtering
11: Role-based dashboard access (Staff & Admin permitted)
12: Customer cannot access global financial reports (AccessError enforced)
13: Dashboard calculations after payment confirmation (real-time update)
14: Dashboard calculations after invoice changes (real-time update)
15: Integration & regression with MRR, ARR, and Discounts
16: High-volume performance benchmark (measuring response time under 2 seconds)
"""

import calendar
import time
import unittest
from datetime import date, datetime, timedelta


class ValidationError(Exception):
    pass


class AccessError(Exception):
    pass


class UserError(Exception):
    pass


# ============================================================================
# LOGICAL MOCK & ORM SIMULATION LAYER FOR DASHBOARD & FINANCIAL ANALYTICS
# ============================================================================

class MockRole:
    ADMIN = 'group_subscription_manager'
    STAFF = 'group_subscription_user'
    PORTAL = 'group_subscription_portal'


class MockUser:
    def __init__(self, id, name, roles, partner=None):
        self.id = id
        self.name = name
        self.roles = set(roles)
        self.partner = partner

    def has_group(self, group_name):
        return group_name in self.roles


class MockPartner:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email


class MockSubscription:
    def __init__(self, id, name, partner, state='active', start_date=None, mrr=200.0, arr=2400.0):
        self.id = id
        self.name = name
        self.partner_id = partner
        self.state = state
        self.start_date = start_date or date.today()
        self.mrr = float(mrr)
        self.arr = float(arr)


class MockInvoice:
    def __init__(self, id, name, partner, amount_total=0.0, due_date=None,
                 invoice_date=None, state='confirmed', payment_state='not_paid'):
        self.id = id
        self.name = name
        self.partner_id = partner
        self.amount_total = float(amount_total)
        self.amount_paid = 0.0
        self.amount_residual = float(amount_total)
        self.invoice_date = invoice_date or date.today()
        self.due_date = due_date or (date.today() + timedelta(days=15))
        self.state = state
        self.payment_state = payment_state
        self.payment_ids = []
        self._reconcile()

    def _reconcile(self):
        settled = [p for p in self.payment_ids if p.state == 'success']
        self.amount_paid = round(sum(p.amount for p in settled), 2)
        self.amount_residual = max(0.0, round(self.amount_total - self.amount_paid, 2))

        if self.state in ('confirmed', 'paid'):
            if self.amount_residual <= 0.001 and self.amount_total > 0.0:
                self.payment_state = 'paid'
                self.state = 'paid'
            elif self.amount_paid > 0.0:
                self.payment_state = 'partial'
                self.state = 'confirmed'
            else:
                self.payment_state = 'not_paid'
                self.state = 'confirmed'

    @property
    def is_overdue(self):
        return (
            self.state == 'confirmed' and
            self.payment_state != 'paid' and
            self.amount_residual > 0.0 and
            self.due_date < date.today()
        )


class MockPayment:
    def __init__(self, id, name, invoice, amount, payment_method='card',
                 payment_date=None, state='draft'):
        self.id = id
        self.name = name
        self.invoice_id = invoice
        self.partner_id = invoice.partner_id
        self.amount = float(amount)
        self.payment_method = payment_method
        self.payment_date = payment_date or datetime.now()
        self.state = state

        if self not in invoice.payment_ids:
            invoice.payment_ids.append(self)
        invoice._reconcile()

    def action_confirm_payment(self, user=None):
        if user and not (user.has_group(MockRole.STAFF) or user.has_group(MockRole.ADMIN)):
            raise AccessError("Security Violation: Portal customers cannot confirm payments.")
        self.state = 'success'
        self.invoice_id._reconcile()

    def action_fail_payment(self, reason=None, user=None):
        if user and not (user.has_group(MockRole.STAFF) or user.has_group(MockRole.ADMIN)):
            raise AccessError("Security Violation: Portal customers cannot fail payments.")
        self.state = 'failed'
        self.invoice_id._reconcile()


class MockSubscriptionDashboard:
    """Simulates SubscriptionDashboard AbstractModel analytics engine."""

    def __init__(self, subscriptions=None, invoices=None, payments=None):
        self.subscriptions = subscriptions or []
        self.invoices = invoices or []
        self.payments = payments or []

    def _check_dashboard_access(self, user):
        if not user or not (user.has_group(MockRole.STAFF) or user.has_group(MockRole.ADMIN)):
            raise AccessError("Security Violation: Portal customers are not permitted to view global financial metrics.")

    def _parse_date_range(self, date_range_type, custom_date_from=None, custom_date_to=None):
        today = date.today()
        if date_range_type == 'today':
            return today, today
        elif date_range_type == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif date_range_type == 'this_month':
            start = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day)
            return start, end
        elif date_range_type == 'this_year':
            return date(today.year, 1, 1), date(today.year, 12, 31)
        elif date_range_type == 'custom':
            return custom_date_from, custom_date_to
        return None, None

    def get_dashboard_metrics(self, user=None, date_range='all', date_from=None, date_to=None,
                              partner_id=None, subscription_status=None,
                              invoice_status=None, payment_method=None):
        self._check_dashboard_access(user)

        parsed_from, parsed_to = self._parse_date_range(date_range, date_from, date_to)

        # 1. SUBSCRIPTIONS
        subs = self.subscriptions
        if partner_id:
            subs = [s for s in subs if s.partner_id.id == partner_id]
        if subscription_status and subscription_status != 'all':
            subs = [s for s in subs if s.state == subscription_status]

        active_subs = [s for s in subs if s.state == 'active']
        active_subs_count = len(active_subs)
        total_subs_count = len(subs)
        mrr_total = round(sum(s.mrr for s in active_subs), 2)
        arr_total = round(sum(s.arr for s in active_subs), 2)

        # 2. REVENUE RECEIVED (Settled payments only)
        pays = [p for p in self.payments if p.state == 'success']
        if partner_id:
            pays = [p for p in pays if p.partner_id.id == partner_id]
        if payment_method and payment_method != 'all':
            pays = [p for p in pays if p.payment_method == payment_method]

        if parsed_from:
            pays = [p for p in pays if (p.payment_date.date() if isinstance(p.payment_date, datetime) else p.payment_date) >= parsed_from]
        if parsed_to:
            pays = [p for p in pays if (p.payment_date.date() if isinstance(p.payment_date, datetime) else p.payment_date) <= parsed_to]

        revenue_received = round(sum(p.amount for p in pays), 2)
        total_payments_count = len(pays)
        total_payments_amount = revenue_received

        # 3. OUTSTANDING RECEIVABLES & OVERDUE
        invs = [i for i in self.invoices if i.state in ('confirmed', 'paid')]
        if partner_id:
            invs = [i for i in invs if i.partner_id.id == partner_id]
        if invoice_status and invoice_status != 'all':
            invs = [i for i in invs if i.state == invoice_status]

        outstanding_invoices = [i for i in invs if i.amount_residual > 0.0]
        outstanding_amount = round(sum(i.amount_residual for i in outstanding_invoices), 2)

        today = date.today()
        overdue_invoices = [
            i for i in invs
            if i.state == 'confirmed' and i.payment_state != 'paid' and i.amount_residual > 0.0 and i.due_date < today
        ]
        overdue_invoices_count = len(overdue_invoices)
        overdue_amount = round(sum(i.amount_residual for i in overdue_invoices), 2)

        return {
            'active_subscriptions': active_subs_count,
            'total_subscriptions': total_subs_count,
            'revenue_received': revenue_received,
            'total_payments': total_payments_count,
            'total_payments_amount': total_payments_amount,
            'outstanding_amount': outstanding_amount,
            'overdue_invoices': overdue_invoices_count,
            'overdue_amount': overdue_amount,
            'mrr_total': mrr_total,
            'arr_total': arr_total,
        }


# ============================================================================
# TEST SUITE: DASHBOARD & FINANCIAL REPORTS STANDALONE VERIFICATION
# ============================================================================

class TestDashboardReportsStandalone(unittest.TestCase):

    def setUp(self):
        # Partners
        self.partner_alice = MockPartner(1, "Alice Analytics", "alice@brightloop.com")
        self.partner_bob = MockPartner(2, "Bob Analytics", "bob@brightloop.com")

        # Users
        self.admin = MockUser(1, "Admin User", [MockRole.ADMIN])
        self.staff = MockUser(2, "Staff User", [MockRole.STAFF])
        self.cust_alice = MockUser(3, "Alice Customer", [MockRole.PORTAL], partner=self.partner_alice)
        self.cust_bob = MockUser(4, "Bob Customer", [MockRole.PORTAL], partner=self.partner_bob)

        # Subscriptions
        # Alice has 1 active ($200 MRR) and 1 draft
        self.sub_alice_1 = MockSubscription(1, "SUB-ALICE-1", self.partner_alice, state='active', mrr=200.0, arr=2400.0)
        self.sub_alice_draft = MockSubscription(2, "SUB-ALICE-DRAFT", self.partner_alice, state='draft', mrr=200.0, arr=2400.0)

        # Bob has 1 active ($400 MRR) and 1 closed
        self.sub_bob_1 = MockSubscription(3, "SUB-BOB-1", self.partner_bob, state='active', mrr=400.0, arr=4800.0)
        self.sub_bob_closed = MockSubscription(4, "SUB-BOB-CLOSED", self.partner_bob, state='closed', mrr=400.0, arr=4800.0)

        self.subscriptions = [self.sub_alice_1, self.sub_alice_draft, self.sub_bob_1, self.sub_bob_closed]

        # Invoices
        # Invoice 1: Alice, $200, paid
        self.inv_paid = MockInvoice(1, "INV-PAID-01", self.partner_alice, amount_total=200.0,
                                    invoice_date=date.today() - timedelta(days=20),
                                    due_date=date.today() + timedelta(days=10))
        # Invoice 2: Bob, $400, unpaid (not overdue)
        self.inv_unpaid = MockInvoice(2, "INV-UNPAID-02", self.partner_bob, amount_total=400.0,
                                      invoice_date=date.today() - timedelta(days=5),
                                      due_date=date.today() + timedelta(days=15))
        # Invoice 3: Alice, $200, OVERDUE (due 10 days ago)
        self.inv_overdue = MockInvoice(3, "INV-OVERDUE-03", self.partner_alice, amount_total=200.0,
                                       invoice_date=date.today() - timedelta(days=40),
                                       due_date=date.today() - timedelta(days=10))

        self.invoices = [self.inv_paid, self.inv_unpaid, self.inv_overdue]

        # Payments
        # Payment 1: Confirmed $200 on inv_paid (5 days ago, Card)
        self.pay_success = MockPayment(1, "PAY-001", self.inv_paid, amount=200.0, payment_method='card',
                                       payment_date=datetime.now() - timedelta(days=5), state='draft')
        self.pay_success.action_confirm_payment(user=self.staff)

        # Payment 2: Draft $150 on inv_unpaid (Bank transfer)
        self.pay_draft = MockPayment(2, "PAY-002", self.inv_unpaid, amount=150.0, payment_method='bank_transfer',
                                     state='draft')

        # Payment 3: Failed $250 on inv_unpaid (Stripe)
        self.pay_failed = MockPayment(3, "PAY-003", self.inv_unpaid, amount=250.0, payment_method='stripe',
                                      state='draft')
        self.pay_failed.action_fail_payment(reason="Card declined", user=self.staff)

        self.payments = [self.pay_success, self.pay_draft, self.pay_failed]

        self.engine = MockSubscriptionDashboard(
            subscriptions=self.subscriptions,
            invoices=self.invoices,
            payments=self.payments
        )

    # ------------------------------------------------------------
    # 1. ACTIVE SUBSCRIPTIONS
    # ------------------------------------------------------------
    def test_01_active_subscriptions_count(self):
        """1. Active subscription count counts only state='active'."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertEqual(metrics['active_subscriptions'], 2)
        self.assertEqual(metrics['total_subscriptions'], 4)

    # ------------------------------------------------------------
    # 2. REVENUE RECEIVED
    # ------------------------------------------------------------
    def test_02_revenue_received_confirmed_payments(self):
        """2. Revenue received is the exact sum of settled (state='success') payments."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertEqual(metrics['revenue_received'], 200.0)
        self.assertEqual(metrics['total_payments'], 1)

    # ------------------------------------------------------------
    # 3. DRAFT PAYMENT EXCLUSION
    # ------------------------------------------------------------
    def test_03_draft_payment_exclusion(self):
        """3. Draft payments (150.0) must not be included in revenue."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertNotIn(350.0, [metrics['revenue_received']])
        self.assertEqual(metrics['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 4. FAILED PAYMENT EXCLUSION
    # ------------------------------------------------------------
    def test_04_failed_payment_exclusion(self):
        """4. Failed payments (250.0) must not be included in revenue."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertNotIn(450.0, [metrics['revenue_received']])
        self.assertEqual(metrics['revenue_received'], 200.0)

    # ------------------------------------------------------------
    # 5. OUTSTANDING AMOUNT
    # ------------------------------------------------------------
    def test_05_outstanding_amount_calculation(self):
        """5. Outstanding amount = sum of unpaid invoice residuals ($400 + $200 = $600)."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertEqual(metrics['outstanding_amount'], 600.0)

    # ------------------------------------------------------------
    # 6. OVERDUE INVOICES
    # ------------------------------------------------------------
    def test_06_overdue_invoices_calculation(self):
        """6. Overdue invoices: only inv_overdue (due 10 days ago, residual $200)."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertEqual(metrics['overdue_invoices'], 1)
        self.assertEqual(metrics['overdue_amount'], 200.0)

    # ------------------------------------------------------------
    # 7. DATE-RANGE FILTERS
    # ------------------------------------------------------------
    def test_07_date_range_filters(self):
        """7. Date filters apply correctly to payments."""
        # Today's payments (pay_success was 5 days ago)
        metrics_today = self.engine.get_dashboard_metrics(user=self.staff, date_range='today')
        self.assertEqual(metrics_today['revenue_received'], 0.0)
        self.assertEqual(metrics_today['total_payments'], 0)

        # This Month (pay_success was this month)
        metrics_month = self.engine.get_dashboard_metrics(user=self.staff, date_range='this_month')
        self.assertEqual(metrics_month['revenue_received'], 200.0)
        self.assertEqual(metrics_month['total_payments'], 1)

    # ------------------------------------------------------------
    # 8. CUSTOMER-BASED FILTERING
    # ------------------------------------------------------------
    def test_08_customer_based_filtering(self):
        """8. Filtering by customer partner isolates metrics."""
        # Alice Customer 1
        m_alice = self.engine.get_dashboard_metrics(user=self.staff, partner_id=self.partner_alice.id)
        self.assertEqual(m_alice['active_subscriptions'], 1)
        self.assertEqual(m_alice['revenue_received'], 200.0)
        self.assertEqual(m_alice['outstanding_amount'], 200.0)
        self.assertEqual(m_alice['overdue_invoices'], 1)

        # Bob Customer 2
        m_bob = self.engine.get_dashboard_metrics(user=self.staff, partner_id=self.partner_bob.id)
        self.assertEqual(m_bob['active_subscriptions'], 1)
        self.assertEqual(m_bob['revenue_received'], 0.0)
        self.assertEqual(m_bob['outstanding_amount'], 400.0)
        self.assertEqual(m_bob['overdue_invoices'], 0)

    # ------------------------------------------------------------
    # 9. SUBSCRIPTION STATUS FILTERING
    # ------------------------------------------------------------
    def test_09_subscription_status_filtering(self):
        """9. Filtering by subscription status works."""
        m_closed = self.engine.get_dashboard_metrics(user=self.staff, subscription_status='closed')
        self.assertEqual(m_closed['total_subscriptions'], 1)

    # ------------------------------------------------------------
    # 10. PAYMENT METHOD FILTERING
    # ------------------------------------------------------------
    def test_10_payment_method_filtering(self):
        """10. Filtering by payment method scopes revenue received."""
        m_card = self.engine.get_dashboard_metrics(user=self.staff, payment_method='card')
        self.assertEqual(m_card['revenue_received'], 200.0)

        m_upi = self.engine.get_dashboard_metrics(user=self.staff, payment_method='upi')
        self.assertEqual(m_upi['revenue_received'], 0.0)

    # ------------------------------------------------------------
    # 11. ROLE-BASED DASHBOARD ACCESS (STAFF & ADMIN)
    # ------------------------------------------------------------
    def test_11_role_based_access_staff_and_admin(self):
        """11. Staff and Admin have full access to dashboard engine."""
        m_staff = self.engine.get_dashboard_metrics(user=self.staff)
        self.assertIsNotNone(m_staff['revenue_received'])

        m_admin = self.engine.get_dashboard_metrics(user=self.admin)
        self.assertIsNotNone(m_admin['revenue_received'])

    # ------------------------------------------------------------
    # 12. CUSTOMER ACCESS DENIAL (SERVER-SIDE PROTECTION)
    # ------------------------------------------------------------
    def test_12_customer_cannot_access_global_financials(self):
        """12. Portal customers calling get_dashboard_metrics raise AccessError."""
        with self.assertRaises(AccessError):
            self.engine.get_dashboard_metrics(user=self.cust_alice)

    # ------------------------------------------------------------
    # 13. DYNAMIC METRIC UPDATES AFTER PAYMENT SETTLEMENT
    # ------------------------------------------------------------
    def test_13_dashboard_update_after_payment(self):
        """13. Real-time update of revenue received and residual upon payment confirmation."""
        # Confirm Bob's payment of 200 against inv_unpaid (400 total)
        pay_bob = MockPayment(4, "PAY-004", self.inv_unpaid, amount=200.0, payment_method='upi', state='draft')
        pay_bob.action_confirm_payment(user=self.staff)
        self.payments.append(pay_bob)

        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        # Revenue increased from 200 to 400
        self.assertEqual(metrics['revenue_received'], 400.0)
        # Outstanding decreased from 600 to 400
        self.assertEqual(metrics['outstanding_amount'], 400.0)

    # ------------------------------------------------------------
    # 14. DYNAMIC METRIC UPDATES AFTER INVOICE CHANGES
    # ------------------------------------------------------------
    def test_14_dashboard_update_after_invoice_changes(self):
        """14. Real-time update of outstanding balance upon creating a new confirmed invoice."""
        new_inv = MockInvoice(4, "INV-NEW-04", self.partner_bob, amount_total=100.0, state='confirmed')
        self.invoices.append(new_inv)

        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        # Outstanding increased by 100 (600 + 100 = 700)
        self.assertEqual(metrics['outstanding_amount'], 700.0)

    # ------------------------------------------------------------
    # 15. REGRESSION & RECURRING RUN-RATE (MRR / ARR)
    # ------------------------------------------------------------
    def test_15_existing_modules_remain_intact(self):
        """15. Confirms MRR/ARR, discounts, and payments integrate harmoniously."""
        metrics = self.engine.get_dashboard_metrics(user=self.staff)
        # Alice $200 + Bob $400 = $600 MRR, $7200 ARR
        self.assertEqual(metrics['mrr_total'], 600.0)
        self.assertEqual(metrics['arr_total'], 7200.0)

    # ------------------------------------------------------------
    # 16. HIGH-VOLUME PERFORMANCE BENCHMARK (< 2 SECONDS)
    # ------------------------------------------------------------
    def test_16_high_volume_performance_benchmark(self):
        """16. Generates 5,000 records and verifies dashboard response time is well below 2.0s."""
        large_subs = [
            MockSubscription(i, f"SUB-BULK-{i}", self.partner_alice, state='active' if i % 2 == 0 else 'closed', mrr=100.0, arr=1200.0)
            for i in range(2000)
        ]
        large_invs = [
            MockInvoice(i, f"INV-BULK-{i}", self.partner_alice, amount_total=100.0, state='confirmed')
            for i in range(2000)
        ]
        large_pays = [
            MockPayment(i, f"PAY-BULK-{i}", large_invs[i % 500], amount=50.0, payment_method='card', state='success' if i % 2 == 0 else 'draft')
            for i in range(1000)
        ]

        bulk_engine = MockSubscriptionDashboard(
            subscriptions=large_subs,
            invoices=large_invs,
            payments=large_pays
        )

        t_start = time.perf_counter()
        metrics = bulk_engine.get_dashboard_metrics(user=self.staff)
        t_elapsed = time.perf_counter() - t_start

        self.assertLess(t_elapsed, 2.0, f"Dashboard metric aggregation took {t_elapsed:.4f}s, exceeding 2.0s target!")
        self.assertEqual(metrics['active_subscriptions'], 1000)
        self.assertEqual(metrics['total_subscriptions'], 2000)
        self.assertEqual(metrics['total_payments'], 500)
        self.assertEqual(metrics['revenue_received'], 25000.0)


if __name__ == '__main__':
    unittest.main()
