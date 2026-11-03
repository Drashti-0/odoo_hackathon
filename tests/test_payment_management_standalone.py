#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Verification Suite for Module 3: Payment Management
Team: AuraMinds
Developer 2: Drashti Bhanderi
Tests (16 Scenarios):
1: Creating a valid payment
2: Rejecting zero and negative payment amounts
3: Full payment (payment_state='paid', state='paid')
4: Partial payment (payment_state='partial', state='confirmed')
5: Multiple partial payments accumulating to full settlement
6: Correct outstanding balance calculation
7: Failed payment not affecting invoice balance
8: Draft payment not affecting invoice balance
9: Duplicate confirmation prevention (idempotent no-op)
10: Payment linked to correct invoice and customer
11: Customer can view only their own payments (record-level security)
12: Customer cannot access another customer's payment (isolation)
13: Staff and Admin permissions (portal customers cannot confirm)
14: Existing discount and invoice calculations remain intact
15: Overpayment validation rejection
16: Interactive Payment Registration Wizard simulation
"""

import unittest
from datetime import date, timedelta


class ValidationError(Exception):
    pass


class AccessError(Exception):
    pass


class UserError(Exception):
    pass


# ============================================================================
# LOGICAL MOCK & ORM SIMULATION LAYER FOR PAYMENTS
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


class MockDiscount:
    def __init__(self, name, discount_type, value):
        self.name = name
        self.discount_type = discount_type
        self.value = float(value)

    def compute_discount(self, gross_amount):
        if self.discount_type == 'percentage':
            return round(gross_amount * (self.value / 100.0), 2)
        elif self.discount_type == 'fixed':
            return min(gross_amount, round(self.value, 2))
        return 0.0


class MockInvoice:
    def __init__(self, id, name, partner, amount_total=0.0, due_date=None, discount=None):
        self.id = id
        self.name = name
        self.partner_id = partner
        self.currency_id = 'USD'
        self.state = 'confirmed'
        self.payment_state = 'not_paid'
        self.discount = discount

        # Gross & Totals
        self.amount_untaxed = float(amount_total)
        self.amount_discount = 0.0
        if discount:
            self.amount_discount = discount.compute_discount(self.amount_untaxed)
        self.amount_total = max(0.0, round(self.amount_untaxed - self.amount_discount, 2))

        self.due_date = due_date or (date.today() + timedelta(days=15))
        self.payment_ids = []
        self.amount_paid = 0.0
        self.amount_residual = self.amount_total
        self.is_overdue = False
        self.days_overdue = 0
        self.message_log = []

    def message_post(self, body):
        self.message_log.append(body)

    def _compute_payment_totals(self):
        settled_payments = [p for p in self.payment_ids if p.state == 'success']
        paid = round(sum(p.amount for p in settled_payments), 2)
        total = round(self.amount_total, 2)
        residual = max(0.0, round(total - paid, 2))

        self.amount_paid = paid
        self.amount_residual = residual

        if self.state in ('confirmed', 'paid'):
            if residual <= 0.001 and total > 0.0:
                self.payment_state = 'paid'
                self.state = 'paid'
            elif paid > 0.0:
                self.payment_state = 'partial'
                self.state = 'confirmed'
            else:
                self.payment_state = 'not_paid'
                self.state = 'confirmed'

        # Compute overdue
        today = date.today()
        if self.due_date and self.state == 'confirmed' and self.payment_state != 'paid' and self.due_date < today:
            self.is_overdue = True
            self.days_overdue = (today - self.due_date).days
        else:
            self.is_overdue = False
            self.days_overdue = 0

    def action_register_payment(self, amount, ref=None, payment_method='card', note=None, user=None):
        if self.state not in ('confirmed', 'paid'):
            raise UserError("Invoices must be confirmed before registering payment.")

        pay_amount = float(amount)
        if pay_amount <= 0.0:
            raise UserError("Payment amount must be strictly greater than 0.0.")
        if round(pay_amount, 2) > round(self.amount_residual, 2):
            raise UserError(f"Payment amount ({pay_amount}) exceeds invoice outstanding balance ({self.amount_residual}).")

        payment = MockPayment(
            id=len(self.payment_ids) + 1,
            name=ref or f"PAY-{self.name}",
            invoice=self,
            amount=pay_amount,
            payment_method=payment_method,
            payment_note=note,
            state='draft'
        )
        payment.action_confirm_payment(user=user)
        return payment


class MockPayment:
    ALLOWED_METHODS = {'cash', 'bank_transfer', 'upi', 'card', 'stripe', 'paypal', 'other'}

    def __init__(self, id, name, invoice, amount, payment_method='card', payment_note=None,
                 payment_date=None, state='draft'):
        if amount <= 0.0:
            raise ValidationError("Payment amount must be strictly greater than 0.0.")

        if payment_method not in self.ALLOWED_METHODS:
            raise ValidationError(f"Invalid payment method: {payment_method}")

        self.id = id
        self.name = name
        self.invoice_id = invoice
        self.partner_id = invoice.partner_id
        self.amount = float(amount)
        self.payment_method = payment_method
        self.payment_note = payment_note
        self.payment_date = payment_date or date.today()
        self.state = state
        self.gateway_response = None

        # Check against residual if state is success immediately
        if state == 'success':
            self._check_against_residual()

        if self not in invoice.payment_ids:
            invoice.payment_ids.append(self)
        invoice._compute_payment_totals()

    def _check_against_residual(self):
        other_settled = sum(p.amount for p in self.invoice_id.payment_ids if p.id != self.id and p.state == 'success')
        allowed_max = round(self.invoice_id.amount_total - other_settled, 2)
        if round(self.amount, 2) > allowed_max:
            raise ValidationError(f"Payment amount ({self.amount}) exceeds outstanding balance ({allowed_max}).")

    def action_confirm_payment(self, user=None):
        if user:
            is_staff_or_admin = (
                user.has_group(MockRole.STAFF) or
                user.has_group(MockRole.ADMIN)
            )
            if not is_staff_or_admin:
                raise AccessError("Security Violation: Portal customers cannot confirm or alter payment settlements.")

        if self.state == 'success':
            # Idempotent no-op
            return

        if round(self.amount, 2) > round(self.invoice_id.amount_residual, 2):
            raise UserError(f"Payment amount ({self.amount}) exceeds invoice outstanding balance ({self.invoice_id.amount_residual}).")

        self.state = 'success'
        self.invoice_id._compute_payment_totals()
        self.invoice_id.message_post(f"Payment {self.name} of amount {self.amount} settled via {self.payment_method}.")

    def action_fail_payment(self, reason=None, user=None):
        if user:
            is_staff_or_admin = (
                user.has_group(MockRole.STAFF) or
                user.has_group(MockRole.ADMIN)
            )
            if not is_staff_or_admin:
                raise AccessError("Security Violation: Portal customers cannot alter payment status.")

        was_success = (self.state == 'success')
        self.state = 'failed'
        if reason:
            self.gateway_response = reason
        if was_success:
            self.invoice_id._compute_payment_totals()
        self.invoice_id.message_post(f"Payment {self.name} marked as failed. Reason: {reason or 'Declined'}")

    def read_secured(self, user):
        """Simulates Odoo record rule: customer can only read their own payments."""
        if user.has_group(MockRole.ADMIN) or user.has_group(MockRole.STAFF):
            return {'id': self.id, 'name': self.name, 'amount': self.amount, 'state': self.state}
        if user.has_group(MockRole.PORTAL):
            if user.partner and user.partner.id == self.partner_id.id:
                return {'id': self.id, 'name': self.name, 'amount': self.amount, 'state': self.state}
            raise AccessError(f"Access Denied: Customer {user.name} cannot view payment {self.name} belonging to {self.partner_id.name}.")
        raise AccessError("Access Denied.")


class MockPaymentRegisterWizard:
    """Simulates SubscriptionPaymentRegisterWizard TransientModel."""
    def __init__(self, invoice, amount=None, payment_method='card', reference=None, note=None, user=None):
        self.invoice_id = invoice
        self.amount = float(amount if amount is not None else invoice.amount_residual)
        self.payment_method = payment_method
        self.payment_reference = reference or f"PAY-{invoice.name}"
        self.payment_note = note
        self.user = user

    def action_submit_payment(self):
        if self.amount <= 0.0:
            raise ValidationError("Payment amount must be strictly greater than 0.0.")
        if round(self.amount, 2) > round(self.invoice_id.amount_residual, 2):
            raise ValidationError(f"Payment amount ({self.amount}) exceeds outstanding balance ({self.invoice_id.amount_residual}).")

        payment = MockPayment(
            id=len(self.invoice_id.payment_ids) + 1,
            name=self.payment_reference,
            invoice=self.invoice_id,
            amount=self.amount,
            payment_method=self.payment_method,
            payment_note=self.payment_note,
            state='draft'
        )
        payment.action_confirm_payment(user=self.user)
        return payment


# ============================================================================
# TEST SUITE: PAYMENT MANAGEMENT STANDALONE VERIFICATION
# ============================================================================

class TestPaymentManagementStandalone(unittest.TestCase):

    def setUp(self):
        # Partners
        self.partner_alice = MockPartner(1, "Alice Subscriber", "alice@brightloop.com")
        self.partner_bob = MockPartner(2, "Bob Subscriber", "bob@brightloop.com")

        # Users
        self.admin = MockUser(1, "Admin User", [MockRole.ADMIN])
        self.staff = MockUser(2, "Staff User", [MockRole.STAFF])
        self.cust_alice = MockUser(3, "Alice Customer", [MockRole.PORTAL], partner=self.partner_alice)
        self.cust_bob = MockUser(4, "Bob Customer", [MockRole.PORTAL], partner=self.partner_bob)

        # Standard Invoices
        self.inv_alice = MockInvoice(1, "INV-2026-0001", self.partner_alice, amount_total=500.0)
        self.inv_bob = MockInvoice(2, "INV-2026-0002", self.partner_bob, amount_total=800.0)

    # ------------------------------------------------------------
    # 1. CREATING A VALID PAYMENT
    # ------------------------------------------------------------
    def test_01_create_valid_payment(self):
        """1. Creating a valid payment record."""
        pay = MockPayment(
            id=101,
            name="PAY-WIRE-001",
            invoice=self.inv_alice,
            amount=200.0,
            payment_method='bank_transfer',
            payment_note="Wire transfer reference TXN-998811",
            state='draft'
        )
        self.assertEqual(pay.amount, 200.0)
        self.assertEqual(pay.payment_method, 'bank_transfer')
        self.assertEqual(pay.partner_id, self.partner_alice)
        self.assertEqual(pay.state, 'draft')
        self.assertIn(pay, self.inv_alice.payment_ids)

    # ------------------------------------------------------------
    # 2. REJECTING ZERO AND NEGATIVE PAYMENT AMOUNTS
    # ------------------------------------------------------------
    def test_02_rejecting_zero_and_negative_amounts(self):
        """2. Rejecting zero and negative payment amounts."""
        with self.assertRaises(ValidationError):
            MockPayment(102, "PAY-ZERO", self.inv_alice, amount=0.0, payment_method='card')

        with self.assertRaises(ValidationError):
            MockPayment(103, "PAY-NEG", self.inv_alice, amount=-50.0, payment_method='cash')

    # ------------------------------------------------------------
    # 3. FULL PAYMENT SETTLES INVOICE
    # ------------------------------------------------------------
    def test_03_full_payment_settles_invoice(self):
        """3. Full payment transitions invoice state='paid' and payment_state='paid'."""
        inv = MockInvoice(3, "INV-FULL-01", self.partner_alice, amount_total=350.0)
        self.assertEqual(inv.amount_residual, 350.0)
        self.assertEqual(inv.payment_state, 'not_paid')

        pay = MockPayment(104, "PAY-FULL", inv, amount=350.0, payment_method='card', state='draft')
        pay.action_confirm_payment(user=self.staff)

        self.assertEqual(pay.state, 'success')
        self.assertEqual(inv.amount_paid, 350.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')

    # ------------------------------------------------------------
    # 4. PARTIAL PAYMENT UPDATES BALANCE
    # ------------------------------------------------------------
    def test_04_partial_payment(self):
        """4. Partial payment updates balance and sets payment_state='partial'."""
        inv = MockInvoice(4, "INV-PARTIAL-01", self.partner_alice, amount_total=600.0)
        pay = MockPayment(105, "PAY-PART-1", inv, amount=250.0, payment_method='upi', state='draft')
        pay.action_confirm_payment(user=self.staff)

        self.assertEqual(pay.state, 'success')
        self.assertEqual(inv.amount_paid, 250.0)
        self.assertEqual(inv.amount_residual, 350.0)
        self.assertEqual(inv.payment_state, 'partial')
        self.assertEqual(inv.state, 'confirmed')

    # ------------------------------------------------------------
    # 5. MULTIPLE PARTIAL PAYMENTS ACCUMULATING TO FULL SETTLEMENT
    # ------------------------------------------------------------
    def test_05_multiple_partial_payments(self):
        """5. Multiple partial payments accumulate correctly until full settlement."""
        inv = MockInvoice(5, "INV-MULTI-01", self.partner_alice, amount_total=1000.0)

        # Batch 1: $300
        p1 = MockPayment(106, "PAY-BATCH-1", inv, amount=300.0, payment_method='cash', state='draft')
        p1.action_confirm_payment(user=self.staff)
        self.assertEqual(inv.amount_paid, 300.0)
        self.assertEqual(inv.amount_residual, 700.0)
        self.assertEqual(inv.payment_state, 'partial')

        # Batch 2: $500
        p2 = MockPayment(107, "PAY-BATCH-2", inv, amount=500.0, payment_method='bank_transfer', state='draft')
        p2.action_confirm_payment(user=self.staff)
        self.assertEqual(inv.amount_paid, 800.0)
        self.assertEqual(inv.amount_residual, 200.0)
        self.assertEqual(inv.payment_state, 'partial')

        # Batch 3: $200 (Final settlement)
        p3 = MockPayment(108, "PAY-BATCH-3", inv, amount=200.0, payment_method='upi', state='draft')
        p3.action_confirm_payment(user=self.staff)
        self.assertEqual(inv.amount_paid, 1000.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')

    # ------------------------------------------------------------
    # 6. CORRECT OUTSTANDING BALANCE CALCULATION
    # ------------------------------------------------------------
    def test_06_correct_outstanding_balance_calculation(self):
        """6. Residual balance is exactly amount_total - amount_paid."""
        inv = MockInvoice(6, "INV-BAL-01", self.partner_alice, amount_total=1250.0)
        self.assertEqual(inv.amount_residual, 1250.0)

        pay = MockPayment(109, "PAY-BAL", inv, amount=475.25, payment_method='stripe', state='draft')
        pay.action_confirm_payment(user=self.staff)

        self.assertEqual(inv.amount_paid, 475.25)
        self.assertEqual(inv.amount_residual, 774.75)

    # ------------------------------------------------------------
    # 7. FAILED PAYMENT NOT AFFECTING BALANCE
    # ------------------------------------------------------------
    def test_07_failed_payment_not_affecting_balance(self):
        """7. Failed payment does not reduce invoice balance."""
        inv = MockInvoice(7, "INV-FAIL-01", self.partner_alice, amount_total=400.0)
        pay = MockPayment(110, "PAY-DECLINED", inv, amount=400.0, payment_method='card', state='draft')
        pay.action_fail_payment(reason="Insufficient funds", user=self.staff)

        self.assertEqual(pay.state, 'failed')
        self.assertEqual(pay.gateway_response, "Insufficient funds")
        self.assertEqual(inv.amount_paid, 0.0)
        self.assertEqual(inv.amount_residual, 400.0)
        self.assertEqual(inv.payment_state, 'not_paid')

    # ------------------------------------------------------------
    # 8. DRAFT PAYMENT NOT AFFECTING BALANCE
    # ------------------------------------------------------------
    def test_08_draft_payment_not_affecting_balance(self):
        """8. Draft payment does not reduce invoice balance."""
        inv = MockInvoice(8, "INV-DRAFT-01", self.partner_alice, amount_total=300.0)
        pay = MockPayment(111, "PAY-DRAFT", inv, amount=300.0, payment_method='paypal', state='draft')

        self.assertEqual(pay.state, 'draft')
        self.assertEqual(inv.amount_paid, 0.0)
        self.assertEqual(inv.amount_residual, 300.0)
        self.assertEqual(inv.payment_state, 'not_paid')

    # ------------------------------------------------------------
    # 9. DUPLICATE CONFIRMATION PREVENTION (IDEMPOTENT)
    # ------------------------------------------------------------
    def test_09_duplicate_confirmation_prevention(self):
        """9. Re-confirming already settled payment is a safe idempotent no-op."""
        inv = MockInvoice(9, "INV-IDEMP-01", self.partner_alice, amount_total=500.0)
        pay = MockPayment(112, "PAY-IDEMP", inv, amount=250.0, payment_method='card', state='draft')
        pay.action_confirm_payment(user=self.staff)
        self.assertEqual(inv.amount_paid, 250.0)

        # Confirm again
        pay.action_confirm_payment(user=self.staff)
        self.assertEqual(inv.amount_paid, 250.0, "Duplicate confirm must not double-count amount")
        self.assertEqual(inv.amount_residual, 250.0)

    # ------------------------------------------------------------
    # 10. PAYMENT LINKED TO CORRECT INVOICE AND CUSTOMER
    # ------------------------------------------------------------
    def test_10_payment_linked_to_correct_invoice_and_customer(self):
        """10. Payment correctly associates with invoice and customer partner."""
        pay = MockPayment(113, "PAY-ASSOC", self.inv_alice, amount=100.0, payment_method='card')
        self.assertEqual(pay.invoice_id, self.inv_alice)
        self.assertEqual(pay.partner_id, self.partner_alice)
        self.assertIn(pay, self.inv_alice.payment_ids)

    # ------------------------------------------------------------
    # 11. CUSTOMER CAN VIEW ONLY OWN PAYMENTS
    # ------------------------------------------------------------
    def test_11_customer_can_view_only_own_payments(self):
        """11. Customer can view their own payment transactions."""
        pay_alice = MockPayment(114, "PAY-ALICE-OWN", self.inv_alice, amount=50.0, payment_method='upi')
        rec = pay_alice.read_secured(user=self.cust_alice)
        self.assertEqual(rec['name'], "PAY-ALICE-OWN")
        self.assertEqual(rec['amount'], 50.0)

    # ------------------------------------------------------------
    # 12. CUSTOMER CANNOT ACCESS ANOTHER CUSTOMER'S PAYMENT
    # ------------------------------------------------------------
    def test_12_customer_cannot_access_another_customer_payment(self):
        """12. Alice cannot view Bob's payment transactions."""
        pay_bob = MockPayment(115, "PAY-BOB-ISOLATED", self.inv_bob, amount=150.0, payment_method='card')
        with self.assertRaises(AccessError):
            pay_bob.read_secured(user=self.cust_alice)

    # ------------------------------------------------------------
    # 13. STAFF AND ADMIN PERMISSIONS (CUSTOMERS CANNOT CONFIRM)
    # ------------------------------------------------------------
    def test_13_staff_and_admin_permissions(self):
        """13. Staff/Admin can confirm; portal customers raise AccessError."""
        pay = MockPayment(116, "PAY-SEC-CHECK", self.inv_alice, amount=80.0, payment_method='card', state='draft')

        # Customer attempts to settle -> blocked
        with self.assertRaises(AccessError):
            pay.action_confirm_payment(user=self.cust_alice)

        # Customer attempts to fail -> blocked
        with self.assertRaises(AccessError):
            pay.action_fail_payment(reason="Fraud", user=self.cust_alice)

        # Staff can settle
        pay.action_confirm_payment(user=self.staff)
        self.assertEqual(pay.state, 'success')

        # Admin can also settle another payment
        pay2 = MockPayment(117, "PAY-ADM-CONFIRM", self.inv_alice, amount=20.0, payment_method='cash', state='draft')
        pay2.action_confirm_payment(user=self.admin)
        self.assertEqual(pay2.state, 'success')

    # ------------------------------------------------------------
    # 14. EXISTING DISCOUNT AND INVOICE CALCULATIONS REMAIN CORRECT
    # ------------------------------------------------------------
    def test_14_existing_discount_and_invoice_calculations(self):
        """14. Existing discount logic remains intact alongside payment reconciliation."""
        disc = MockDiscount("Save 20 Fixed", "fixed", 20.0)
        # Gross = 100, Discount = 20, Amount Total = 80
        inv = MockInvoice(10, "INV-DISC-01", self.partner_alice, amount_total=100.0, discount=disc)
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 80.0)
        self.assertEqual(inv.amount_residual, 80.0)

        pay = MockPayment(118, "PAY-DISC-SETTLE", inv, amount=80.0, payment_method='card', state='draft')
        pay.action_confirm_payment(user=self.staff)

        self.assertEqual(inv.amount_paid, 80.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')

    # ------------------------------------------------------------
    # 15. OVERPAYMENT VALIDATION REJECTION
    # ------------------------------------------------------------
    def test_15_overpayment_validation(self):
        """15. Payment amount exceeding outstanding residual is strictly rejected."""
        inv = MockInvoice(11, "INV-OVERPAY", self.partner_alice, amount_total=100.0)

        # Attempt to confirm payment of 150 against residual of 100
        pay = MockPayment(119, "PAY-OVER", inv, amount=150.0, payment_method='card', state='draft')
        with self.assertRaises(UserError):
            pay.action_confirm_payment(user=self.staff)

    # ------------------------------------------------------------
    # 16. PAYMENT REGISTRATION WIZARD
    # ------------------------------------------------------------
    def test_16_payment_registration_wizard(self):
        """16. Interactive registration wizard validates and settles payments."""
        inv = MockInvoice(12, "INV-WIZARD", self.partner_alice, amount_total=250.0)

        # Wizard with invalid overpayment
        wiz_bad = MockPaymentRegisterWizard(inv, amount=300.0, payment_method='card', user=self.staff)
        with self.assertRaises(ValidationError):
            wiz_bad.action_submit_payment()

        # Wizard with valid amount
        wiz_ok = MockPaymentRegisterWizard(
            inv,
            amount=250.0,
            payment_method='bank_transfer',
            reference='WIZ-WIRE-889',
            note='Processed at counter',
            user=self.staff
        )
        pay = wiz_ok.action_submit_payment()
        self.assertEqual(pay.state, 'success')
        self.assertEqual(inv.amount_paid, 250.0)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')


if __name__ == '__main__':
    unittest.main()
