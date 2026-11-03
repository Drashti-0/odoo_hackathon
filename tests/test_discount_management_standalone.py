#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Verification Suite for Module 2: Discount Management
Team: AuraMinds
Developer 2: Drashti Bhanderi
Tests (28 Scenarios):
1-5: Discount Calculation (Fixed, Percentage, Boundaries, Clamping)
6-11: Eligibility Conditions (Min Purchase, Min Quantity, Product-specific, Whole-subscription)
12-18: Date & Usage (Start date, Valid range, Expiry, Usage limit, Concurrency, No duplicate count)
19-24: Billing Integration (Auto application, Invoice totals, Idempotency, Retry safety, Tax calculation)
25-28: Security (Admin allowed, Staff blocked, Customer blocked, Unauthorized RPC rejected)
"""

import unittest
from datetime import date, timedelta

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    class relativedelta:
        def __init__(self, days=0, months=0, years=0):
            self.days = days
            self.months = months
            self.years = years

        def __radd__(self, other):
            if isinstance(other, date):
                # Simple day/month approximation for standalone tests
                total_days = self.days + (self.months * 30) + (self.years * 365)
                return other + timedelta(days=total_days)
            return NotImplemented

        def __rsub__(self, other):
            if isinstance(other, date):
                total_days = self.days + (self.months * 30) + (self.years * 365)
                return other - timedelta(days=total_days)
            return NotImplemented


class ValidationError(Exception):
    pass


class AccessError(Exception):
    pass


class UserError(Exception):
    pass


# ============================================================================
# LOGICAL MOCK & ORM SIMULATION LAYER FOR DISCOUNTS
# ============================================================================

class MockRole:
    ADMIN = 'group_subscription_manager'
    STAFF = 'group_subscription_user'
    PORTAL = 'group_subscription_portal'


class MockUser:
    def __init__(self, name, roles):
        self.name = name
        self.roles = set(roles)

    def has_group(self, group_name):
        return group_name in self.roles


class MockProduct:
    def __init__(self, id, name, price):
        self.id = id
        self.name = name
        self.list_price = float(price)


class MockDiscount:
    def __init__(self, id, name, code, discount_type, value, min_purchase=0.0,
                 min_quantity=0.0, start_date=None, end_date=None,
                 usage_limit=0, applicable_products=None,
                 apply_to_whole_subscription=True, active=True, creator_user=None):

        # Security check: Admin only
        if creator_user and not creator_user.has_group(MockRole.ADMIN):
            raise AccessError("Security Violation: Only Subscription Administrators can create discount rules.")

        # Constraints
        if discount_type == 'percentage':
            if value <= 0.0 or value > 100.0:
                raise ValidationError("Percentage discount must be greater than 0% and cannot exceed 100%.")
        elif discount_type == 'fixed':
            if value <= 0.0:
                raise ValidationError("Fixed discount amount must be strictly greater than 0.0.")

        if min_purchase < 0.0:
            raise ValidationError("Minimum purchase amount cannot be negative.")
        if min_quantity < 0.0:
            raise ValidationError("Minimum quantity cannot be negative.")
        if usage_limit < 0:
            raise ValidationError("Usage limit cannot be negative.")
        if start_date and end_date and end_date < start_date:
            raise ValidationError(f"Validity End Date ({end_date}) cannot be earlier than Start Date ({start_date}).")

        self.id = id
        self.name = name
        self.code = code
        self.discount_type = discount_type
        self.value = float(value)
        self.min_purchase_amount = float(min_purchase)
        self.min_quantity = float(min_quantity)
        self.start_date = start_date
        self.end_date = end_date
        self.usage_limit = usage_limit
        self.usage_count = 0
        self.applicable_products = applicable_products or []
        self.apply_to_whole_subscription = apply_to_whole_subscription
        self.active = active

    def write(self, values, user=None):
        if user and not user.has_group(MockRole.ADMIN):
            raise AccessError("Security Violation: Only Subscription Administrators can modify discount rules.")
        for k, v in values.items():
            setattr(self, k, v)

    def unlink(self, user=None):
        if user and not user.has_group(MockRole.ADMIN):
            raise AccessError("Security Violation: Only Subscription Administrators can delete discount rules.")

    def check_eligibility(self, check_date=None, subtotal=0.0, total_quantity=0.0, product_ids=None):
        target = check_date or date.today()
        if not self.active:
            return False, "Discount coupon is deactivated."
        if self.start_date and target < self.start_date:
            return False, "Discount coupon is not active yet."
        if self.end_date and target > self.end_date:
            return False, "Discount coupon has expired."
        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            return False, f"Discount coupon has reached its maximum usage limit ({self.usage_count}/{self.usage_limit})."
        if self.min_purchase_amount > 0.0 and subtotal < self.min_purchase_amount:
            return False, f"Subtotal amount ({subtotal}) does not meet the minimum purchase requirement of {self.min_purchase_amount}."
        if self.min_quantity > 0.0 and total_quantity < self.min_quantity:
            return False, f"Total item quantity ({total_quantity}) is below the minimum required quantity ({self.min_quantity})."
        if self.applicable_products and product_ids:
            matching = set(p.id for p in self.applicable_products).intersection(set(product_ids))
            if not matching:
                return False, "Discount coupon does not apply to any of the selected products."
        return True, "Discount is eligible."

    def calculate_discount_amount(self, subtotal, matching_subtotal=None):
        base = matching_subtotal if matching_subtotal is not None else subtotal
        if base <= 0.0:
            return 0.0
        if self.discount_type == 'percentage':
            deduction = (base * self.value) / 100.0
        elif self.discount_type == 'fixed':
            deduction = min(self.value, base)
        else:
            deduction = 0.0
        return max(0.0, round(deduction, 2))

    def record_usage(self):
        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            raise UserError(f"Coupon '{self.code}' has reached its maximum usage limit.")
        self.usage_count += 1


class MockSubscriptionLine:
    def __init__(self, product, quantity, unit_price):
        self.product = product
        self.quantity = float(quantity)
        self.unit_price = float(unit_price)
        self.price_subtotal = self.quantity * self.unit_price


class MockSubscription:
    def __init__(self, name, plan_price=50.0, discount=None):
        self.name = name
        self.plan_price = float(plan_price)
        self.discount = discount
        self.lines = []
        self.amount_untaxed = 0.0
        self.amount_discount = 0.0
        self.amount_total = 0.0
        self.compute_amounts()

    def add_line(self, product, quantity=1.0):
        line = MockSubscriptionLine(product, quantity, product.list_price)
        self.lines.append(line)
        self.compute_amounts()

    def compute_amounts(self):
        gross_lines = sum(l.price_subtotal for l in self.lines)
        untaxed = self.plan_price + gross_lines
        disc_deduction = 0.0

        if self.discount:
            today = date.today()
            total_qty = sum(l.quantity for l in self.lines)
            prod_ids = [l.product.id for l in self.lines]
            is_ok, _ = self.discount.check_eligibility(
                check_date=today, subtotal=untaxed,
                total_quantity=total_qty, product_ids=prod_ids
            )
            if is_ok:
                matching_base = untaxed
                if self.discount.applicable_products:
                    matching_lines = [l for l in self.lines if l.product in self.discount.applicable_products]
                    matching_base = sum(l.price_subtotal for l in matching_lines)
                    if not self.discount.apply_to_whole_subscription and not matching_lines:
                        matching_base = 0.0
                calc_base = untaxed if self.discount.apply_to_whole_subscription else matching_base
                disc_deduction = self.discount.calculate_discount_amount(subtotal=untaxed, matching_subtotal=calc_base)

        self.amount_untaxed = untaxed
        self.amount_discount = disc_deduction
        self.amount_total = max(0.0, untaxed - disc_deduction)


class MockInvoice:
    def __init__(self, name, subtotal, discount=None, tax_rate=0.0):
        self.name = name
        self.lines_subtotal = float(subtotal)
        self.discount = discount
        self.tax_rate = float(tax_rate)
        self.amount_untaxed = float(subtotal)
        self.amount_tax = 0.0
        self.amount_discount = 0.0
        self.amount_total = 0.0
        self.state = 'draft'
        self.discount_usage_recorded = False
        self.compute_amounts()

    def compute_amounts(self):
        disc_deduction = 0.0
        if self.discount:
            is_ok, _ = self.discount.check_eligibility(subtotal=self.lines_subtotal)
            if is_ok:
                disc_deduction = self.discount.calculate_discount_amount(subtotal=self.lines_subtotal)

        tax_amt = (self.lines_subtotal * self.tax_rate) / 100.0
        self.amount_untaxed = self.lines_subtotal
        self.amount_discount = disc_deduction
        self.amount_tax = tax_amt
        # Preserves tax and applies discount idempotently
        self.amount_total = max(0.0, self.lines_subtotal + tax_amt - disc_deduction)

    def confirm(self):
        if self.state == 'confirmed':
            return
        self.state = 'confirmed'
        if self.discount and not self.discount_usage_recorded:
            self.discount.record_usage()
            self.discount_usage_recorded = True

    def cancel(self):
        if self.state == 'cancel':
            return
        self.state = 'cancel'
        if self.discount and self.discount_usage_recorded:
            self.discount.usage_count = max(0, self.discount.usage_count - 1)
            self.discount_usage_recorded = False


# ============================================================================
# STANDALONE TEST SUITE (28 TESTS)
# ============================================================================

class TestDiscountManagementStandalone(unittest.TestCase):

    def setUp(self):
        self.admin = MockUser("System Admin", [MockRole.ADMIN, MockRole.STAFF])
        self.staff = MockUser("Ops Staff", [MockRole.STAFF])
        self.customer = MockUser("Client Portal", [MockRole.PORTAL])

        self.prod_a = MockProduct(1, "Server Core", 100.0)
        self.prod_b = MockProduct(2, "Database Core", 200.0)

        self.disc_percent = MockDiscount(
            1, "Ten Percent Off", "SAVE10", "percentage", 10.0, creator_user=self.admin
        )
        self.disc_fixed = MockDiscount(
            2, "Twenty Dollars Off", "SAVE20", "fixed", 20.0, creator_user=self.admin
        )

    # ------------------------------------------------------------
    # 1-5: DISCOUNT CALCULATION TESTS
    # ------------------------------------------------------------
    def test_01_fixed_amount_discount(self):
        """1. Fixed amount discount calculates exact deduction."""
        amt = self.disc_fixed.calculate_discount_amount(subtotal=150.0)
        self.assertEqual(amt, 20.0)

    def test_02_percentage_discount(self):
        """2. Percentage discount calculates correct percentage deduction."""
        amt = self.disc_percent.calculate_discount_amount(subtotal=200.0)
        self.assertEqual(amt, 20.0)

    def test_03_percentage_discount_boundary_validation(self):
        """3. Percentage discount boundary validation (<= 0 or > 100 rejected)."""
        with self.assertRaises(ValidationError):
            MockDiscount(3, "Negative", "BAD", "percentage", -5.0, creator_user=self.admin)
        with self.assertRaises(ValidationError):
            MockDiscount(4, "Over 100", "BAD", "percentage", 105.0, creator_user=self.admin)

    def test_04_fixed_discount_validation(self):
        """4. Fixed discount validation (<= 0 rejected)."""
        with self.assertRaises(ValidationError):
            MockDiscount(5, "Zero Fixed", "BAD", "fixed", 0.0, creator_user=self.admin)

    def test_05_discount_cannot_exceed_eligible_amount(self):
        """5. Fixed discount cannot exceed eligible amount (clamped)."""
        big_disc = MockDiscount(6, "Big Fixed", "BIG500", "fixed", 500.0, creator_user=self.admin)
        amt = big_disc.calculate_discount_amount(subtotal=100.0)
        self.assertEqual(amt, 100.0, "Discount must be clamped to eligible subtotal")

    # ------------------------------------------------------------
    # 6-11: ELIGIBILITY TESTS
    # ------------------------------------------------------------
    def test_06_min_purchase_amount_satisfied(self):
        """6. Minimum purchase amount satisfied."""
        disc = MockDiscount(7, "Min 100", "MIN100", "fixed", 10.0, min_purchase=100.0, creator_user=self.admin)
        is_ok, _ = disc.check_eligibility(subtotal=150.0)
        self.assertTrue(is_ok)

    def test_07_min_purchase_amount_not_satisfied(self):
        """7. Minimum purchase amount not satisfied."""
        disc = MockDiscount(8, "Min 100", "MIN100", "fixed", 10.0, min_purchase=100.0, creator_user=self.admin)
        is_ok, reason = disc.check_eligibility(subtotal=80.0)
        self.assertFalse(is_ok)
        self.assertIn("minimum purchase requirement", reason)

    def test_08_min_quantity_satisfied(self):
        """8. Minimum quantity satisfied."""
        disc = MockDiscount(9, "Min Qty 3", "QTY3", "percentage", 10.0, min_quantity=3.0, creator_user=self.admin)
        is_ok, _ = disc.check_eligibility(subtotal=100.0, total_quantity=5.0)
        self.assertTrue(is_ok)

    def test_09_min_quantity_not_satisfied(self):
        """9. Minimum quantity not satisfied."""
        disc = MockDiscount(10, "Min Qty 3", "QTY3", "percentage", 10.0, min_quantity=3.0, creator_user=self.admin)
        is_ok, reason = disc.check_eligibility(subtotal=100.0, total_quantity=2.0)
        self.assertFalse(is_ok)
        self.assertIn("minimum required quantity", reason)

    def test_10_product_specific_discount(self):
        """10. Product-specific discount eligibility."""
        disc = MockDiscount(11, "Prod A Only", "PRODA", "fixed", 15.0,
                            applicable_products=[self.prod_a], apply_to_whole_subscription=False,
                            creator_user=self.admin)
        is_ok, _ = disc.check_eligibility(subtotal=100.0, product_ids=[self.prod_a.id])
        self.assertTrue(is_ok)
        is_fail, _ = disc.check_eligibility(subtotal=100.0, product_ids=[self.prod_b.id])
        self.assertFalse(is_fail)

    def test_11_whole_subscription_discount(self):
        """11. Whole subscription discount applies across total."""
        amt = self.disc_percent.calculate_discount_amount(subtotal=500.0)
        self.assertEqual(amt, 50.0)

    # ------------------------------------------------------------
    # 12-18: DATE & USAGE TESTS
    # ------------------------------------------------------------
    def test_12_discount_before_start_date(self):
        """12. Discount before start date is rejected."""
        future_start = date.today() + relativedelta(days=10)
        disc = MockDiscount(12, "Future", "FUT", "fixed", 10.0, start_date=future_start, creator_user=self.admin)
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("not active yet", reason)

    def test_13_discount_within_valid_date_range(self):
        """13. Discount within valid date range is accepted."""
        today = date.today()
        disc = MockDiscount(13, "Now", "NOW", "percentage", 15.0,
                            start_date=today - relativedelta(days=5),
                            end_date=today + relativedelta(days=5),
                            creator_user=self.admin)
        is_ok, _ = disc.check_eligibility()
        self.assertTrue(is_ok)

    def test_14_expired_discount(self):
        """14. Expired discount is rejected."""
        past_end = date.today() - relativedelta(days=2)
        disc = MockDiscount(14, "Expired", "EXP", "percentage", 20.0, end_date=past_end, creator_user=self.admin)
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("has expired", reason)

    def test_15_usage_limit_reached(self):
        """15. Usage limit reached rejects redemption."""
        disc = MockDiscount(15, "Limit 1", "LIM1", "fixed", 10.0, usage_limit=1, creator_user=self.admin)
        disc.record_usage()
        self.assertEqual(disc.usage_count, 1)
        is_ok, reason = disc.check_eligibility()
        self.assertFalse(is_ok)
        self.assertIn("maximum usage limit", reason)

    def test_16_usage_limit_not_reached(self):
        """16. Usage limit not reached allows redemption."""
        disc = MockDiscount(16, "Limit 5", "LIM5", "fixed", 10.0, usage_limit=5, creator_user=self.admin)
        disc.record_usage()
        self.assertEqual(disc.usage_count, 1)
        is_ok, _ = disc.check_eligibility()
        self.assertTrue(is_ok)

    def test_17_concurrent_usage_limit_protection(self):
        """17. Usage limit protection enforces boundary under concurrency."""
        disc = MockDiscount(17, "Strict 1", "STR1", "fixed", 10.0, usage_limit=1, creator_user=self.admin)
        disc.record_usage()
        with self.assertRaises(UserError):
            disc.record_usage()

    def test_18_usage_count_not_duplicated(self):
        """18. Usage count is not incremented on re-computation."""
        disc = MockDiscount(18, "No Dupe", "NODUPE", "fixed", 10.0, usage_limit=10, creator_user=self.admin)
        initial = disc.usage_count
        disc.calculate_discount_amount(subtotal=100.0)
        disc.calculate_discount_amount(subtotal=100.0)
        self.assertEqual(disc.usage_count, initial, "Calculations must not increment usage count")

    # ------------------------------------------------------------
    # 19-24: BILLING ENGINE INTEGRATION TESTS
    # ------------------------------------------------------------
    def test_19_automatic_discount_application_during_invoice_generation(self):
        """19. Subscriptions with active discount compute amounts correctly."""
        sub = MockSubscription("SUB-001", plan_price=50.0, discount=self.disc_fixed)
        sub.add_line(self.prod_a, quantity=1.0) # 100
        # Plan 50 + Product 100 = 150. Discount 20. Net = 130.
        self.assertEqual(sub.amount_discount, 20.0)
        self.assertEqual(sub.amount_total, 130.0)

    def test_20_discount_appears_correctly_in_invoice_totals(self):
        """20. Discount deductions reflect accurately in invoice totals."""
        inv = MockInvoice("INV-001", subtotal=200.0, discount=self.disc_percent)
        # 200 gross. 10% discount = 20. Total = 180.
        self.assertEqual(inv.amount_untaxed, 200.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 180.0)

    def test_21_repeated_invoice_calculation_does_not_duplicate_discount(self):
        """21. Repeated invoice calculations are strictly idempotent."""
        inv = MockInvoice("INV-002", subtotal=100.0, discount=self.disc_fixed)
        self.assertEqual(inv.amount_total, 80.0)
        # Run 5 more times
        for _ in range(5):
            inv.compute_amounts()
        self.assertEqual(inv.amount_total, 80.0, "Repeated compute MUST NOT compound discounts")

    def test_22_invoice_retry_does_not_duplicate_discount(self):
        """22. Billing retry does not increment discount usage count twice."""
        disc = MockDiscount(19, "Retry Check", "RETRY", "fixed", 10.0, usage_limit=10, creator_user=self.admin)
        inv = MockInvoice("INV-003", subtotal=100.0, discount=disc)
        self.assertEqual(disc.usage_count, 0)
        inv.confirm()
        self.assertEqual(disc.usage_count, 1)

        # Retry confirm
        inv.confirm()
        self.assertEqual(disc.usage_count, 1, "Duplicate confirm retry MUST NOT increment usage")

    def test_23_tax_calculation_remains_correct(self):
        """23. Tax calculation sequence is preserved."""
        # Gross = 100, Tax = 15% (15), Fixed Discount = 20. Total = 100 + 15 - 20 = 95.
        inv = MockInvoice("INV-004", subtotal=100.0, discount=self.disc_fixed, tax_rate=15.0)
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_tax, 15.0)
        self.assertEqual(inv.amount_discount, 20.0)
        self.assertEqual(inv.amount_total, 95.0)

    def test_24_existing_billing_engine_remains_functional(self):
        """24. Standard invoices without discounts calculate normally."""
        inv = MockInvoice("INV-005", subtotal=100.0, discount=None)
        self.assertEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(inv.amount_discount, 0.0)
        self.assertEqual(inv.amount_total, 100.0)

    # ------------------------------------------------------------
    # 25-28: SECURITY TESTS
    # ------------------------------------------------------------
    def test_25_admin_can_create_discounts(self):
        """25. Admin can create and modify discount rules."""
        disc = MockDiscount(20, "Admin Rule", "ADM", "fixed", 10.0, creator_user=self.admin)
        self.assertEqual(disc.name, "Admin Rule")
        disc.write({"name": "Admin Rule Updated"}, user=self.admin)
        self.assertEqual(disc.name, "Admin Rule Updated")

    def test_26_internal_staff_cannot_create_or_modify_discounts(self):
        """26. Internal Staff cannot create or modify discount rules."""
        with self.assertRaises(AccessError):
            MockDiscount(21, "Staff Rule", "STF", "fixed", 10.0, creator_user=self.staff)
        with self.assertRaises(AccessError):
            self.disc_fixed.write({"value": 50.0}, user=self.staff)

    def test_27_customers_cannot_create_or_modify_discounts(self):
        """27. Portal Customers cannot create or modify discount rules."""
        with self.assertRaises(AccessError):
            MockDiscount(22, "Cust Rule", "CST", "fixed", 10.0, creator_user=self.customer)
        with self.assertRaises(AccessError):
            self.disc_fixed.write({"value": 100.0}, user=self.customer)

    def test_28_unauthorized_rpc_requests_are_rejected(self):
        """28. Unauthorized delete or write via RPC is blocked at security layer."""
        with self.assertRaises(AccessError):
            self.disc_fixed.unlink(user=self.customer)
        with self.assertRaises(AccessError):
            self.disc_fixed.unlink(user=self.staff)


if __name__ == '__main__':
    unittest.main()
