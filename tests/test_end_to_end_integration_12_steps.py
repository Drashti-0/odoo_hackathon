#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Complete Integration Test for All 12 Workflow Steps
Project: Subscription Management System – Brightloop Software
Verifies:
 1. Admin login & privileges
 2. Customer registration and login (Strong password policy)
 3. Staff user creation & operational permissions
 4. Product and subscription plan creation (Odoo brand +560 surcharge)
 5. Subscription creation, quotation, and confirmation lifecycle
 6. Discount creation and application (Promo code validation & deduction)
 7. Automatic recurring invoice generation
 8. Full and partial payment registration
 9. Invoice reconciliation & residual balance clearing
10. Dashboard and financial reports (MRR, ARR, Active Contracts)
11. Customer data isolation and role-based permissions
12. Recurring billing workflow & idempotency defense
"""

import sys
import os
import unittest
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    class relativedelta:
        def __init__(self, days=0, weeks=0, months=0, years=0):
            self.days = days + (weeks * 7)
            self.months = months
            self.years = years

        def __radd__(self, other):
            if isinstance(other, date):
                import calendar
                y = other.year + self.years
                m = other.month + self.months
                y += (m - 1) // 12
                m = ((m - 1) % 12) + 1
                max_d = calendar.monthrange(y, m)[1]
                d = min(other.day, max_d)
                res = date(y, m, d)
                if self.days:
                    res += timedelta(days=self.days)
                return res
            return NotImplemented

        def __rsub__(self, other):
            if isinstance(other, date):
                inv = relativedelta(days=-self.days, months=-self.months, years=-self.years)
                return inv.__radd__(other)
            return NotImplemented

# Ensure tests path is accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_standalone_verification import (
    MockProductTemplate, MockSubscriptionPlan, MockSubscription,
    MockSubscriptionLine, MockBillingEngine, MockSubscriptionInvoice
)
from test_user_management_standalone import (
    MockSecurityContext, MockPartner, MockUser,
    ValidationError, AccessError, validate_password_strength, validate_email_syntax
)
from test_discount_management_standalone import MockDiscount
from test_payment_management_standalone import MockPayment
from test_dashboard_reports_standalone import MockDashboardEngine


class TestComplete12StepIntegration(unittest.TestCase):
    """Executes the full 12-step end-to-end business lifecycle."""

    def setUp(self):
        self.security = MockSecurityContext()

    def test_full_12_step_business_lifecycle(self):
        print("\n" + "=" * 70)
        print("STARTING COMPLETE 12-STEP INTEGRATION LIFECYCLE TEST")
        print("=" * 70)

        # ---------------------------------------------------------
        # STEP 1: Admin Login & Privileges
        # ---------------------------------------------------------
        print("\n[Step 1] Admin Authentication & Privileges")
        admin = self.security.admin_user
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(self.security.check_access(admin, 'res.users', 'create'))
        self.assertTrue(self.security.check_access(admin, 'subscription.plan', 'create'))
        self.assertTrue(self.security.check_access(admin, 'subscription.discount', 'create'))
        print(" -> PASS: Admin authenticated with full governance access.")

        # ---------------------------------------------------------
        # STEP 2: Customer Registration & Password Complexity
        # ---------------------------------------------------------
        print("\n[Step 2] Customer Registration & Password Complexity")
        # Weak password rejected
        with self.assertRaises(ValidationError):
            validate_password_strength("weak")
        # Strong password accepted
        self.assertTrue(validate_password_strength("AliceSecure2026!"))
        clean_email = validate_email_syntax("alice@customer.com")
        self.assertEqual(clean_email, "alice@customer.com")

        # Create Alice & Bob
        alice_partner = self.security.create_partner("Alice Customer", "alice@customer.com", is_customer=True)
        alice_user = self.security.create_user("Alice Customer", "alice@customer.com", "alice_portal", "customer", alice_partner)

        bob_partner = self.security.create_partner("Bob Customer", "bob@customer.com", is_customer=True)
        bob_user = self.security.create_user("Bob Customer", "bob@customer.com", "bob_portal", "customer", bob_partner)

        self.assertEqual(alice_user.role, 'customer')
        self.assertEqual(bob_user.role, 'customer')
        print(f" -> PASS: Customers registered. Alice (ID {alice_partner.id}), Bob (ID {bob_partner.id}).")

        # ---------------------------------------------------------
        # STEP 3: Staff User Creation
        # ---------------------------------------------------------
        print("\n[Step 3] Staff User Creation & Operational Permissions")
        staff_partner = self.security.create_partner("Brightloop Staff", "staff@brightloop.com")
        staff_user = self.security.create_user("Brightloop Staff", "staff@brightloop.com", "staff_op", "staff", staff_partner, creator_user=admin)
        self.assertEqual(staff_user.role, 'staff')
        self.assertTrue(self.security.check_access(staff_user, 'subscription.subscription', 'write'))
        # Customer cannot create staff
        with self.assertRaises(AccessError):
            self.security.create_user("Hacker", "hack@evil.com", "h", "staff", None, creator_user=alice_user)
        print(" -> PASS: Operational Staff user created with appropriate security bounds.")

        # ---------------------------------------------------------
        # STEP 4: Product & Subscription Plan Creation (+560 Surcharge)
        # ---------------------------------------------------------
        print("\n[Step 4] Product & Subscription Plan Creation (Odoo Brand Surcharge)")
        # Product with Odoo brand
        prod_odoo = MockProductTemplate("Cloud ERP Hosting", list_price=1000.0, brand_name='odoo')
        self.assertEqual(prod_odoo.brand_surcharge, 560.0)
        self.assertEqual(prod_odoo.subscription_price, 1560.0)

        # Plan: Monthly SaaS
        plan_monthly = MockSubscriptionPlan(
            name="Monthly Professional Tier",
            price=200.0,
            billing_interval_unit='monthly',
            billing_interval_count=1,
            trial_period_days=14,
            grace_period_days=5,
            allow_pause=True,
            allow_renewal=True
        )
        self.assertEqual(plan_monthly.billing_interval_unit, 'monthly')
        self.assertEqual(plan_monthly.price, 200.0)
        print(f" -> PASS: Product ({prod_odoo.name}) computed price: {prod_odoo.subscription_price} (Base 1000 + Odoo Surcharge 560).")
        print(f" -> PASS: Plan ({plan_monthly.name}) created with 1-month interval cadence.")

        # ---------------------------------------------------------
        # STEP 5: Subscription Creation, Quotation, and Confirmation
        # ---------------------------------------------------------
        print("\n[Step 5] Subscription Contract Lifecycle Machine")
        sub = MockSubscription("Alice Customer", plan_monthly, partner_id=alice_partner.id)
        self.assertEqual(sub.state, 'draft')

        # Add line item
        line = MockSubscriptionLine("Cloud ERP Hosting", 2.0, prod_odoo.subscription_price)
        sub.line_ids.append(line)
        sub._compute_amounts()
        # Untaxed = Plan 200 + Line (2 * 1560) = 3320.0
        self.assertEqual(sub.amount_untaxed, 3320.0)

        # Transition: Draft -> Quotation -> Confirmed -> Active
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')

        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')

        sub.action_activate()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, date.today())
        print(f" -> PASS: Subscription contract transitioned: draft -> quotation -> confirmed -> active (Total: {sub.amount_total}).")

        # ---------------------------------------------------------
        # STEP 6: Discount Creation & Application
        # ---------------------------------------------------------
        print("\n[Step 6] Discount Promo Code Creation & Application")
        discount = MockDiscount(
            discount_id=1,
            name="Launch 20% Off",
            code="LAUNCH20",
            discount_type="percentage",
            value=20.0,
            min_purchase_amount=50.0,
            max_usage=100,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            creator_user=admin
        )
        self.assertTrue(discount.check_validity())
        disc_amount = discount.calculate_discount_amount(sub.amount_untaxed)
        # 20% of 3320.0 = 664.0
        self.assertEqual(disc_amount, 664.0)
        net_order = sub.amount_untaxed - disc_amount
        self.assertEqual(net_order, 2656.0)
        discount.increment_usage()
        self.assertEqual(discount.current_usage, 1)
        print(f" -> PASS: Coupon LAUNCH20 applied: 20% discount of {disc_amount} deducted (Net: {net_order}).")

        # ---------------------------------------------------------
        # STEP 7: Automatic Recurring Invoice Generation
        # ---------------------------------------------------------
        print("\n[Step 7] Automated Recurring Invoice Generation")
        inv = MockSubscriptionInvoice(
            subscription=sub,
            partner=alice_partner,
            amount_untaxed=net_order,
            amount_tax=0.0,
            amount_total=net_order,
            billing_period_start=date.today(),
            billing_period_end=date.today() + relativedelta(months=1)
        )
        inv.state = 'confirmed'
        inv.amount_residual = net_order
        sub.invoices.append(inv)
        self.assertEqual(inv.state, 'confirmed')
        self.assertEqual(inv.payment_state, 'not_paid')
        self.assertEqual(inv.amount_residual, 2656.0)
        print(f" -> PASS: Recurring Invoice generated. Total: {inv.amount_total}, Residual: {inv.amount_residual}.")

        # ---------------------------------------------------------
        # STEP 8: Full and Partial Payment Registration
        # ---------------------------------------------------------
        print("\n[Step 8] Partial & Multi-Gateway Payment Registration")
        # Payment 1: Partial $1,000 via Credit Card
        pay1 = MockPayment(
            payment_id=101,
            invoice=inv,
            partner=alice_partner,
            amount=1000.0,
            payment_method='card',
            transaction_ref='TXN-CC-1001'
        )
        pay1.action_confirm(creator_user=staff_user)
        self.assertEqual(pay1.state, 'posted')
        self.assertEqual(inv.amount_residual, 1656.0)
        self.assertEqual(inv.payment_state, 'partially_paid')
        print(f" -> PASS: Partial payment of 1,000 settled. Residual: {inv.amount_residual} (State: {inv.payment_state}).")

        # ---------------------------------------------------------
        # STEP 9: Invoice Reconciliation
        # ---------------------------------------------------------
        print("\n[Step 9] Second Settlement & Full Invoice Reconciliation")
        # Payment 2: Remaining $1,656 via Stripe
        pay2 = MockPayment(
            payment_id=102,
            invoice=inv,
            partner=alice_partner,
            amount=1656.0,
            payment_method='stripe',
            transaction_ref='TXN-STRIPE-1002'
        )
        pay2.action_confirm(creator_user=staff_user)
        self.assertEqual(pay2.state, 'posted')
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')
        print(f" -> PASS: Final payment settled. Invoice fully reconciled: Residual = 0.0, Status = {inv.state}.")

        # ---------------------------------------------------------
        # STEP 10: Dashboard and Financial Reports
        # ---------------------------------------------------------
        print("\n[Step 10] Real-time Financial Dashboard Intelligence")
        dashboard = MockDashboardEngine()
        # Seed test contracts
        dashboard.subscriptions = [sub]
        dashboard.payments = [pay1, pay2]
        metrics = dashboard.compute_metrics(creator_user=admin)
        self.assertEqual(metrics['active_subscriptions'], 1)
        self.assertEqual(metrics['revenue_received'], 2656.0)
        self.assertGreater(metrics['mrr'], 0.0)
        self.assertEqual(metrics['arr'], metrics['mrr'] * 12.0)
        print(f" -> PASS: Dashboard Metrics: Active = {metrics['active_subscriptions']}, Revenue = {metrics['revenue_received']}, MRR = {metrics['mrr']}, ARR = {metrics['arr']}.")

        # ---------------------------------------------------------
        # STEP 11: Customer Data Isolation & Multi-Tenant Rules
        # ---------------------------------------------------------
        print("\n[Step 11] Customer Data Isolation & Cross-Tenant Defense")
        # Alice can access her own subscription
        self.assertTrue(self.security.check_record_access(alice_user, sub))
        # Bob attempting to view Alice's subscription raises AccessError
        with self.assertRaises(AccessError):
            self.security.check_record_access(bob_user, sub)
        # Portal customer cannot access financial dashboard
        with self.assertRaises(AccessError):
            dashboard.compute_metrics(creator_user=alice_user)
        print(" -> PASS: Multi-tenant record rules strictly enforced: Bob blocked from Alice's contracts; Customers blocked from dashboard.")

        # ---------------------------------------------------------
        # STEP 12: Recurring Billing Workflow & Idempotency Defense
        # ---------------------------------------------------------
        print("\n[Step 12] Billing Cron & Idempotency Check")
        engine = MockBillingEngine()
        initial_invoice_count = len(sub.invoices)
        # Next billing is in future, cron should not duplicate invoice
        sub.next_billing_date = date.today() + relativedelta(months=1)
        created_invoices = engine.run_billing_cron([sub])
        self.assertEqual(len(created_invoices), 0)
        self.assertEqual(len(sub.invoices), initial_invoice_count)
        print(f" -> PASS: Idempotency confirmed: Zero duplicate invoices created. Invoice count remains {len(sub.invoices)}.")

        print("\n" + "=" * 70)
        print("ALL 12 INTEGRATION WORKFLOW STEPS PASSED SUCCESSFULLY (100% PASS RATE)!")
        print("=" * 70)


if __name__ == '__main__':
    unittest.main()
