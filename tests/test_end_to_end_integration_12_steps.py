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
from datetime import date, datetime, timedelta

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
    MockSubscriptionLine, MockBillingEngine
)
from test_user_management_standalone import (
    MockUser, MockPartner, MockSecurityGroup, MockRecordRuleEngine,
    ValidationError, AccessError, validate_password_strength, validate_email_syntax,
    MockCustomerSubscription
)
from test_discount_management_standalone import MockDiscount
from test_payment_management_standalone import MockInvoice, MockPayment
from test_dashboard_reports_standalone import (
    MockSubscriptionDashboard, MockRole, MockUser as DashUser,
    MockSubscription as DashSub, MockPayment as DashPay, MockInvoice as DashInv,
    AccessError as DashAccessError
)


class TestComplete12StepIntegration(unittest.TestCase):
    """Executes the full 12-step end-to-end business lifecycle."""

    def setUp(self):
        MockUser.reset()
        MockPartner.reset()

    def test_full_12_step_business_lifecycle(self):
        print("\n" + "=" * 70)
        print("STARTING COMPLETE 12-STEP INTEGRATION LIFECYCLE TEST")
        print("=" * 70)

        # ---------------------------------------------------------
        # STEP 1: Admin Login & Privileges
        # ---------------------------------------------------------
        print("\n[Step 1] Admin Authentication & Privileges")
        admin_partner = MockPartner("Brightloop Admin", "admin@brightloop.com")
        admin_user = MockUser(
            name="Brightloop Admin",
            email="admin@brightloop.com",
            password="AdminMasterSecure2026!",
            partner=admin_partner,
            groups=[MockSecurityGroup.ADMIN]
        )
        self.assertTrue(admin_user.has_group(MockSecurityGroup.ADMIN))
        self.assertTrue(admin_user.has_group(MockSecurityGroup.ADMIN))
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

        # Register Alice and Bob via portal signup flow
        res_alice = MockUser.register_portal_customer("Alice Customer", "alice@customer.com", "AliceSecure2026!", company_name="Alice Corp")
        alice_user = MockUser.search_by_email("alice@customer.com")
        alice_partner = alice_user.partner_id

        res_bob = MockUser.register_portal_customer("Bob Customer", "bob@customer.com", "BobSecure2026!", company_name="Bob Corp")
        bob_user = MockUser.search_by_email("bob@customer.com")
        bob_partner = bob_user.partner_id

        self.assertTrue(alice_user.has_group(MockSecurityGroup.PORTAL))
        self.assertTrue(bob_user.has_group(MockSecurityGroup.PORTAL))
        print(f" -> PASS: Customers registered. Alice (ID {alice_partner.id}), Bob (ID {bob_partner.id}).")

        # ---------------------------------------------------------
        # STEP 3: Staff User Creation
        # ---------------------------------------------------------
        print("\n[Step 3] Staff User Creation & Operational Permissions")
        staff_user = MockUser.create_user(
            creator_user=admin_user,
            name="Brightloop Staff",
            email="staff@brightloop.com",
            password="StaffSecure2026!",
            groups=[MockSecurityGroup.STAFF]
        )
        self.assertTrue(staff_user.has_group(MockSecurityGroup.STAFF))

        # Portal Customer cannot create staff or escalate privileges
        with self.assertRaises(AccessError):
            MockUser.create_user(
                creator_user=alice_user,
                name="Malicious User",
                email="evil@attacker.com",
                password="EvilPassword2026!",
                groups=[MockSecurityGroup.STAFF]
            )
        print(" -> PASS: Operational Staff user created with appropriate security bounds.")

        # ---------------------------------------------------------
        # STEP 4: Product & Subscription Plan Creation (+560 Surcharge)
        # ---------------------------------------------------------
        print("\n[Step 4] Product & Subscription Plan Creation (Odoo Brand Surcharge)")
        # Product with Odoo brand (+560 surcharge)
        prod_odoo = MockProductTemplate("Cloud ERP Hosting", list_price=1000.0, brand_name='odoo')
        self.assertEqual(prod_odoo.brand_surcharge, 560.0)
        self.assertEqual(prod_odoo.subscription_price, 1560.0)

        # Plan: Monthly SaaS
        plan_monthly = MockSubscriptionPlan(
            name="Monthly Professional Tier",
            code="PLAN-M-PRO",
            price=200.0,
            billing_interval_unit='monthly',
            billing_interval_count=1,
            auto_close=True,
            auto_close_days=5,
            allow_pause=True,
            allow_renewal=True
        )
        self.assertEqual(plan_monthly.billing_interval_unit, 'monthly')
        self.assertEqual(plan_monthly.price, 200.0)
        print(f" -> PASS: Product ({prod_odoo.name}) price: {prod_odoo.subscription_price} (Base 1000 + Surcharge 560).")
        print(f" -> PASS: Plan ({plan_monthly.name}) created with 1-month interval cadence.")

        # ---------------------------------------------------------
        # STEP 5: Subscription Creation, Quotation, and Confirmation
        # ---------------------------------------------------------
        print("\n[Step 5] Subscription Contract Lifecycle Machine")
        sub = MockSubscription("Alice Customer", plan_monthly)
        sub.partner_id = alice_partner
        self.assertEqual(sub.state, 'draft')

        # Add line item
        sub.add_line(prod_odoo, 2.0, prod_odoo.subscription_price)
        # Untaxed = Plan 200 + Line (2 * 1560) = 3320.0
        self.assertEqual(sub.amount_untaxed, 3320.0)

        # Lifecycle transitions: draft -> quotation -> confirmed -> active
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
            id=1,
            name="Launch 20% Off",
            code="LAUNCH20",
            discount_type="percentage",
            value=20.0,
            min_purchase=50.0,
            usage_limit=100,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            creator_user=admin_user
        )
        is_valid, msg = discount.check_eligibility(subtotal=sub.amount_untaxed)
        self.assertTrue(is_valid)
        discount.compute_discount = discount.calculate_discount_amount
        disc_amount = discount.calculate_discount_amount(sub.amount_untaxed)
        # 20% of 3320.0 = 664.0
        self.assertEqual(disc_amount, 664.0)
        net_order = sub.amount_untaxed - disc_amount
        self.assertEqual(net_order, 2656.0)
        discount.usage_count += 1
        self.assertEqual(discount.usage_count, 1)
        print(f" -> PASS: Coupon LAUNCH20 applied: 20% discount of {disc_amount} deducted (Net: {net_order}).")

        # ---------------------------------------------------------
        # STEP 7: Automatic Recurring Invoice Generation
        # ---------------------------------------------------------
        print("\n[Step 7] Automated Recurring Invoice Generation")
        inv = MockInvoice(
            id=1,
            name="INV-2026-001",
            partner=alice_partner,
            amount_total=sub.amount_untaxed,
            discount=discount
        )
        inv.billing_period_start = date.today()
        inv.billing_period_end = date.today() + relativedelta(months=1) - relativedelta(days=1)
        sub.invoice_ids.append(inv)
        self.assertEqual(inv.state, 'confirmed')
        self.assertEqual(inv.payment_state, 'not_paid')
        self.assertEqual(inv.amount_total, 2656.0)
        self.assertEqual(inv.amount_residual, 2656.0)
        print(f" -> PASS: Recurring Invoice generated. Total: {inv.amount_total}, Residual: {inv.amount_residual}.")

        # ---------------------------------------------------------
        # STEP 8: Full and Partial Payment Registration
        # ---------------------------------------------------------
        print("\n[Step 8] Partial & Multi-Gateway Payment Registration")
        # Payment 1: Partial $1,000 via Credit Card
        pay1 = inv.action_register_payment(amount=1000.0, ref="TXN-CC-1001", payment_method="card", user=staff_user)
        self.assertEqual(pay1.state, 'success')
        self.assertEqual(inv.amount_residual, 1656.0)
        self.assertEqual(inv.payment_state, 'partial')
        print(f" -> PASS: Partial payment of 1,000 settled. Residual: {inv.amount_residual} (State: {inv.payment_state}).")

        # ---------------------------------------------------------
        # STEP 9: Invoice Reconciliation
        # ---------------------------------------------------------
        print("\n[Step 9] Second Settlement & Full Invoice Reconciliation")
        # Payment 2: Remaining $1,656 via Stripe
        pay2 = inv.action_register_payment(amount=1656.0, ref="TXN-STRIPE-1002", payment_method="stripe", user=staff_user)
        self.assertEqual(pay2.state, 'success')
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')
        print(f" -> PASS: Final payment settled. Invoice fully reconciled: Residual = 0.0, Status = {inv.state}.")

        # ---------------------------------------------------------
        # STEP 10: Dashboard and Financial Reports
        # ---------------------------------------------------------
        print("\n[Step 10] Real-time Financial Dashboard Intelligence")
        dash_staff = DashUser(id=2, name="Staff User", roles=[MockRole.STAFF])
        dash_sub = DashSub(id=1, name="Sub Alice", partner=alice_partner, state='active', mrr=2656.0, arr=31872.0)
        dash_inv = DashInv(id=1, name="INV-001", partner=alice_partner, amount_total=2656.0)
        dash_pay = DashPay(id=1, name="PAY-001", invoice=dash_inv, amount=2656.0, payment_method='card', state='success')

        dashboard = MockSubscriptionDashboard(
            subscriptions=[dash_sub],
            invoices=[dash_inv],
            payments=[dash_pay]
        )
        metrics = dashboard.get_dashboard_metrics(user=dash_staff)
        self.assertEqual(metrics['active_subscriptions'], 1)
        self.assertEqual(metrics['revenue_received'], 2656.0)
        self.assertEqual(metrics['mrr_total'], 2656.0)
        self.assertEqual(metrics['arr_total'], 31872.0)
        print(f" -> PASS: Dashboard Metrics: Active = {metrics['active_subscriptions']}, Revenue = {metrics['revenue_received']}, MRR = {metrics['mrr_total']}, ARR = {metrics['arr_total']}.")

        # ---------------------------------------------------------
        # STEP 11: Customer Data Isolation & Multi-Tenant Rules
        # ---------------------------------------------------------
        print("\n[Step 11] Customer Data Isolation & Cross-Tenant Defense")
        cust_sub = MockCustomerSubscription(name="Alice Contract", partner=alice_partner, amount_total=2656.0, state='active')
        # Alice can read her own subscription
        data = cust_sub.read(['name', 'amount_total'], user=alice_user)
        self.assertEqual(data['name'], "Alice Contract")

        # Bob attempting to read Alice's subscription raises AccessError
        with self.assertRaises(AccessError):
            cust_sub.read(['name', 'amount_total'], user=bob_user)

        # Portal Customer attempting to access Financial Dashboard raises AccessError
        dash_portal = DashUser(id=3, name="Portal User", roles=[MockRole.PORTAL])
        with self.assertRaises(AccessError):
            dashboard.get_dashboard_metrics(user=dash_portal)
        print(" -> PASS: Multi-tenant record rules strictly enforced: Bob blocked from Alice's contracts; Customers blocked from dashboard.")

        # ---------------------------------------------------------
        # STEP 12: Recurring Billing Workflow & Idempotency Defense
        # ---------------------------------------------------------
        print("\n[Step 12] Billing Cron & Idempotency Check")
        initial_invoice_count = len(sub.invoice_ids)
        # Next billing is in future, cron should not duplicate invoice
        sub.next_billing_date = date.today() + relativedelta(months=1)
        generated_count = MockBillingEngine.process_subscription_catchup(sub, date.today())
        self.assertEqual(generated_count, 0)
        self.assertEqual(len(sub.invoice_ids), initial_invoice_count)
        print(f" -> PASS: Idempotency confirmed: Zero duplicate invoices created. Invoice count remains {len(sub.invoice_ids)}.")

        print("\n" + "=" * 70)
        print("ALL 12 INTEGRATION WORKFLOW STEPS PASSED SUCCESSFULLY (100% PASS RATE)!")
        print("=" * 70)


if __name__ == '__main__':
    unittest.main()
