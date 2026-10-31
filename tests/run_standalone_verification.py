#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Verification Suite for Brightloop Subscription Management System
Developer 1 Assigned Modules (1, 2, 3, 4) Verification
Author: Team AuraMinds (Developer 1 - Dhruti Viradiya)
"""

import sys
import unittest
from datetime import date, datetime, timedelta
import calendar

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Pure Python fallback using standard library for environments without dateutil
    class relativedelta:
        def __init__(self, days=0, weeks=0, months=0, years=0):
            self.days = days + (weeks * 7)
            self.months = months
            self.years = years

        def __radd__(self, other):
            if isinstance(other, date):
                # 1. Add years
                y = other.year + self.years
                m = other.month + self.months
                # Normalize month overflow/underflow
                y += (m - 1) // 12
                m = ((m - 1) % 12) + 1
                # Clamp day to max days in target month
                max_d = calendar.monthrange(y, m)[1]
                d = min(other.day, max_d)
                res = date(y, m, d)
                # 2. Add days
                if self.days:
                    res += timedelta(days=self.days)
                return res
            return NotImplemented

        def __rsub__(self, other):
            if isinstance(other, date):
                # Reverse signs
                inv = relativedelta(days=-self.days, months=-self.months, years=-self.years)
                return inv.__radd__(other)
            return NotImplemented



# ============================================================================
# LOGICAL MOCK & ORM SIMULATION LAYER
# (Simulates Odoo Model & ORM logic directly adhering to models/*.py rules)
# ============================================================================

class MockProductTemplate:
    def __init__(self, name, list_price=100.0, standard_price=0.0,
                 brand_name='standard', is_subscription=True, brand_surcharge=None):
        if list_price < 0.0:
            raise ValueError("Sales price cannot be negative.")
        if standard_price < 0.0:
            raise ValueError("Cost price cannot be negative.")
        if brand_surcharge is not None and brand_surcharge < 0.0:
            raise ValueError("Brand surcharge cannot be negative.")
        self.name = name
        self.list_price = float(list_price)
        self.standard_price = float(standard_price)
        self._brand_name = brand_name
        self.is_subscription = is_subscription
        self._recompute_surcharge()

    @property
    def brand_name(self):
        return self._brand_name

    @brand_name.setter
    def brand_name(self, value):
        self._brand_name = value
        self._recompute_surcharge()

    def _recompute_surcharge(self):
        self.brand_surcharge = 560.0 if self._brand_name == 'odoo' else 0.0
        self.subscription_price = self.list_price + self.brand_surcharge

    def get_subscription_price(self, plan=None, partner=None):
        return self.subscription_price


class MockProductProduct:
    def __init__(self, template, variant_extra=0.0, variant_attr_name=None):
        self.template = template
        self.name = template.name
        self.variant_extra = float(variant_extra)
        self.variant_attr_name = variant_attr_name

    @property
    def brand_name(self):
        return self.template.brand_name

    @property
    def brand_surcharge(self):
        return self.template.brand_surcharge

    @property
    def subscription_price(self):
        return self.get_subscription_price()

    def get_subscription_price(self, plan=None, partner=None):
        base = self.template.list_price
        is_odoo_template = (self.brand_name == 'odoo')
        has_odoo_attr = (self.variant_attr_name and self.variant_attr_name.strip().lower() == 'odoo')

        if is_odoo_template or has_odoo_attr:
            if has_odoo_attr and self.variant_extra >= 560.0:
                brand_extra = 0.0
            else:
                brand_extra = 560.0
        else:
            brand_extra = self.template.brand_surcharge

        return base + brand_extra + self.variant_extra


class MockSubscriptionPlan:
    def __init__(self, name, code, price, billing_interval_unit='monthly',
                 billing_interval_count=1, min_quantity=1.0, start_date=None,
                 end_date=None, auto_close=True, auto_close_days=0,
                 allow_early_close=True, allow_pause=True, allow_renewal=True):
        if price < 0.0:
            raise ValueError("Plan price cannot be negative.")
        if min_quantity < 1.0:
            raise ValueError("Minimum quantity must be at least 1.0.")
        if billing_interval_count < 1:
            raise ValueError("Billing interval count must be at least 1.")
        if auto_close_days < 0:
            raise ValueError("Auto-close grace period cannot be negative.")
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"Availability end date ({end_date}) cannot precede start date ({start_date}).")

        self.name = name
        self.code = code
        self.price = float(price)
        self.billing_interval_unit = billing_interval_unit
        self.billing_interval_count = billing_interval_count
        self.min_quantity = float(min_quantity)
        self.start_date = start_date
        self.end_date = end_date
        self.auto_close = auto_close
        self.auto_close_days = auto_close_days
        self.allow_early_close = allow_early_close
        self.allow_pause = allow_pause
        self.allow_renewal = allow_renewal
        self.active = True

    def is_available_on(self, check_date=None):
        if not self.active:
            return False
        target = check_date or date.today()
        if self.start_date and target < self.start_date:
            return False
        if self.end_date and target > self.end_date:
            return False
        return True

    def calculate_next_billing_date(self, current_date):
        if not current_date:
            current_date = date.today()
        count = self.billing_interval_count
        unit = self.billing_interval_unit
        if unit == 'daily':
            return current_date + relativedelta(days=count)
        elif unit == 'weekly':
            return current_date + relativedelta(weeks=count)
        elif unit == 'monthly':
            return current_date + relativedelta(months=count)
        elif unit == 'yearly':
            return current_date + relativedelta(years=count)
        return current_date + relativedelta(months=1)


class MockQuotationTemplate:
    def __init__(self, name, plan, validity_days=30, terms_and_conditions=""):
        if validity_days < 0:
            raise ValueError("Quotation validity days cannot be negative.")
        self.name = name
        self.plan = plan
        self.validity_days = int(validity_days)
        self.terms_and_conditions = terms_and_conditions
        self.line_ids = []

    def add_line(self, product, quantity=1.0, unit_price=None):
        if quantity <= 0:
            raise ValueError("Template line quantity must be strictly greater than 0.")
        price = unit_price if unit_price is not None else product.get_subscription_price(self.plan)
        line = {'product': product, 'quantity': float(quantity), 'unit_price': float(price)}
        self.line_ids.append(line)
        return line


class MockSubscriptionLine:
    def __init__(self, product, quantity, unit_price, tax_rate=0.0, price_include=False, discount_rate=0.0):
        self.product = product
        self.name = product.name
        self.quantity = float(quantity)
        self.unit_price = float(unit_price)
        self.tax_rate = float(tax_rate)
        self.price_include = bool(price_include)
        self.discount_rate = float(discount_rate)

    @property
    def price_subtotal(self):
        gross = self.quantity * self.unit_price
        disc_price = gross * (1.0 - (self.discount_rate / 100.0))
        if self.tax_rate and self.price_include:
            return round(disc_price / (1.0 + (self.tax_rate / 100.0)), 2)
        return disc_price

    @property
    def price_tax(self):
        if self.price_include and self.tax_rate:
            gross = self.quantity * self.unit_price
            disc_price = gross * (1.0 - (self.discount_rate / 100.0))
            return round(disc_price - self.price_subtotal, 2)
        return round(self.price_subtotal * (self.tax_rate / 100.0), 2)

    @property
    def price_total(self):
        return round(self.price_subtotal + self.price_tax, 2)


class MockSubscription:
    _seq_counter = 1

    def __init__(self, partner_name, plan, start_date=None, expiry_date=None, discount_rate=0.0):
        self.id = MockSubscription._seq_counter
        MockSubscription._seq_counter += 1
        self.name = f"SQ-{self.id:05d}"
        self.partner_name = partner_name
        self.plan = plan
        self.state = 'draft'
        self.start_date = start_date or date.today()
        self.expiry_date = expiry_date
        self.quotation_validity_date = date.today() + relativedelta(days=30)
        self.terms_and_conditions = ""
        self.next_billing_date = None
        self.last_billing_date = None
        self.pause_date = None
        self.close_date = None
        self.close_reason = None
        self.discount_rate = float(discount_rate)
        self.line_ids = []
        self.invoice_ids = []
        self.billing_logs = []

        if self.start_date and self.expiry_date and self.expiry_date < self.start_date:
            raise ValueError("Expiry date cannot be earlier than start date.")

    def apply_template(self, template):
        self.plan = template.plan
        if template.validity_days:
            self.quotation_validity_date = date.today() + relativedelta(days=template.validity_days)
        if template.terms_and_conditions:
            self.terms_and_conditions = template.terms_and_conditions
        self.line_ids = []
        for tl in template.line_ids:
            self.add_line(tl['product'], tl['quantity'], tl['unit_price'])

    def add_line(self, product, quantity, unit_price=None, tax_rate=0.0, price_include=False, discount_rate=0.0):
        if quantity < self.plan.min_quantity:
            raise ValueError(f"Quantity {quantity} is below plan minimum {self.plan.min_quantity}.")
        price = unit_price if unit_price is not None else product.get_subscription_price(self.plan)
        line = MockSubscriptionLine(product, quantity, price, tax_rate, price_include, discount_rate)
        self.line_ids.append(line)
        return line

    @property
    def amount_untaxed(self):
        base_plan = self.plan.price
        lines_untaxed = sum(l.price_subtotal for l in self.line_ids)
        total_untaxed = base_plan + lines_untaxed
        discount_deduction = (total_untaxed * self.discount_rate) / 100.0
        return max(0.0, total_untaxed - discount_deduction)

    @property
    def amount_tax(self):
        return sum(l.price_tax for l in self.line_ids)

    @property
    def amount_total(self):
        return self.amount_untaxed + self.amount_tax

    @property
    def currency_symbol(self):
        """Currency fallback safety: returns currency symbol or default company fallback."""
        if getattr(self, 'currency_id', None) and hasattr(self.currency_id, 'symbol'):
            return self.currency_id.symbol
        return "$"

    @property
    def mrr(self):
        if self.state not in ('active', 'paused'):
            return 0.0
        unit = self.plan.billing_interval_unit
        mult = self.plan.billing_interval_count or 1
        total = self.amount_total
        if unit == 'daily':
            return (total / mult) * 30.0
        elif unit == 'weekly':
            return (total / mult) * (30.0 / 7.0)
        elif unit == 'monthly':
            return total / mult
        elif unit == 'yearly':
            return (total / mult) / 12.0
        return total

    @property
    def arr(self):
        return self.mrr * 12.0

    # Lifecycle State Transitions
    def action_send_quotation(self):
        if self.state != 'draft':
            raise RuntimeError("Only draft subscriptions can be sent as quotation.")
        self.state = 'quotation'

    def action_draft(self):
        if self.state not in ('quotation', 'closed'):
            raise RuntimeError("Only quotation or closed subscriptions can be reset to draft.")
        self.state = 'draft'

    def action_cancel(self):
        if self.state not in ('draft', 'quotation'):
            raise RuntimeError("Only draft or quotation can be cancelled.")
        self.state = 'closed'
        self.close_date = date.today()
        self.close_reason = "Quotation was cancelled."

    def action_confirm(self):
        if self.state not in ('draft', 'quotation'):
            raise RuntimeError("Only draft or quotation can be confirmed.")
        if not self.line_ids and not (self.plan and self.plan.price > 0):
            raise ValueError("Cannot confirm a subscription with no lines and zero plan price.")
        if not self.plan.is_available_on(self.start_date):
            raise ValueError(f"Plan {self.plan.name} is not available on {self.start_date}.")
        self.name = f"SUB-{self.id:05d}"
        self.state = 'confirmed'

    def action_activate(self):
        if self.state != 'confirmed':
            raise RuntimeError("Only confirmed subscriptions can be activated.")
        self.state = 'active'
        if not self.next_billing_date:
            self.next_billing_date = self.start_date

    def write(self, vals):
        if 'state' in vals:
            new_state = vals['state']
            valid_transitions = {
                'draft': {'quotation', 'confirmed', 'closed'},
                'quotation': {'draft', 'confirmed', 'closed'},
                'confirmed': {'active', 'closed'},
                'active': {'paused', 'closed', 'expired'},
                'paused': {'active', 'closed'},
                'expired': {'active', 'closed'},
                'closed': {'active', 'draft'},
            }
            if new_state not in valid_transitions.get(self.state, set()):
                raise RuntimeError(f"Direct transition from '{self.state}' to '{new_state}' is not permitted.")
            self.state = new_state

    def action_pause(self):
        if self.state != 'active':
            raise RuntimeError("Only active subscriptions can be paused.")
        if not self.plan.allow_pause:
            raise RuntimeError(f"Plan {self.plan.name} does not permit pause.")
        self.state = 'paused'
        self.pause_date = date.today()

    def action_resume(self):
        if self.state != 'paused':
            raise RuntimeError("Only paused subscriptions can be resumed.")
        today = date.today()
        if self.pause_date and self.next_billing_date:
            days = (today - self.pause_date).days
            if days > 0:
                self.next_billing_date = self.next_billing_date + relativedelta(days=days)
        self.pause_date = None
        self.state = 'active'

    def action_renew(self):
        if not self.plan.allow_renewal:
            raise RuntimeError(f"Plan {self.plan.name} does not permit renewal.")
        today = date.today()
        base = max(today, self.expiry_date) if self.expiry_date else today
        self.expiry_date = self.plan.calculate_next_billing_date(base)
        if self.state in ('closed', 'expired'):
            self.state = 'active'
            self.next_billing_date = today

    def action_close(self, reason=None, is_manager=False):
        today = date.today()
        is_early = self.expiry_date and today < self.expiry_date
        if is_early and not self.plan.allow_early_close and not is_manager:
            raise RuntimeError("Early closure disallowed by plan.")
        self.state = 'closed'
        self.close_date = today
        self.close_reason = reason or "Normal termination"

    def action_check_expiry(self, check_date=None):
        today = check_date or date.today()
        if self.state == 'active' and self.expiry_date and self.expiry_date < today:
            grace = self.plan.auto_close_days
            threshold = self.expiry_date + relativedelta(days=grace)
            if today >= threshold and self.plan.auto_close:
                self.state = 'closed'
                self.close_date = today
                self.close_reason = "Auto-closed on expiry."
            else:
                self.state = 'expired'


class MockInvoice:
    _inv_counter = 1

    def __init__(self, subscription, period_start, period_end, invoice_date=None, state='confirmed'):
        self.id = MockInvoice._inv_counter
        MockInvoice._inv_counter += 1
        self.name = f"INV-{self.id:05d}"
        self.subscription_id = subscription.id
        self.partner_name = subscription.partner_name
        self.billing_period_start = period_start
        self.billing_period_end = period_end
        self.invoice_date = invoice_date or date.today()
        self.due_date = self.invoice_date + relativedelta(days=15)
        self.state = state
        self.payment_state = 'not_paid'
        self.amount_untaxed = subscription.amount_untaxed
        self.amount_tax = subscription.amount_tax
        self.amount_discount = 0.0
        self.amount_total = subscription.amount_total
        self.amount_paid = 0.0
        self.amount_residual = self.amount_total
        self.discount_code = None
        self.payment_ids = []

    def action_confirm(self):
        if self.state != 'draft':
            raise RuntimeError("Only draft invoices can be confirmed.")
        self.state = 'confirmed'

    def action_draft(self):
        if self.state not in ('confirmed', 'cancel'):
            raise RuntimeError("Cannot reset to draft.")
        if self.amount_paid > 0:
            raise RuntimeError("Cannot reset invoice with payments to draft.")
        self.state = 'draft'
        self.payment_state = 'not_paid'

    def action_cancel(self):
        if self.state == 'paid' or self.payment_state == 'paid':
            raise RuntimeError("Cannot cancel paid invoice.")
        if self.amount_paid > 0:
            raise RuntimeError("Cannot cancel invoice with payments.")
        self.state = 'cancel'
        self.payment_state = 'not_paid'

    def write(self, vals):
        if 'state' in vals:
            new_state = vals['state']
            valid_transitions = {
                'draft': {'confirmed', 'cancel'},
                'confirmed': {'draft', 'paid', 'cancel'},
                'paid': set(),
                'cancel': {'draft'},
            }
            if new_state not in valid_transitions.get(self.state, set()):
                raise RuntimeError(f"Direct transition from '{self.state}' to '{new_state}' is not permitted.")
            if new_state == 'paid' and self.amount_residual > 0.001 and self.amount_total > 0.001:
                raise RuntimeError(f"Cannot mark invoice as paid with remaining balance {self.amount_residual}.")
            self.state = new_state

    def register_payment(self, amount=None, ref=None, payment_method='card'):
        if self.state != 'confirmed':
            raise RuntimeError("Invoices must be confirmed before registering payment.")
        if self.payment_state == 'paid' or self.amount_residual <= 0.001:
            raise RuntimeError("Invoice is already fully paid.")

        settle_amount = amount if amount is not None else self.amount_residual
        if settle_amount <= 0.0:
            raise ValueError("Payment amount must be positive.")
        if settle_amount > self.amount_residual + 0.001:
            raise ValueError(f"Payment amount {settle_amount} exceeds balance {self.amount_residual}.")

        pay_ref = ref or f"PAY-{self.name}-{len(self.payment_ids) + 1:02d}"
        self.payment_ids.append({
            'name': pay_ref,
            'amount': settle_amount,
            'payment_method': payment_method,
            'state': 'success',
        })
        self.amount_paid = sum(p['amount'] for p in self.payment_ids if p['state'] == 'success')
        self.amount_residual = max(0.0, self.amount_total - self.amount_paid)

        if self.amount_residual <= 0.001:
            self.payment_state = 'paid'
            self.state = 'paid'
        elif self.amount_paid > 0:
            self.payment_state = 'partial'
        else:
            self.payment_state = 'not_paid'

    def apply_discount_code(self, code, discount_type='percentage', value=10.0):
        if self.state not in ('draft', 'confirmed'):
            raise RuntimeError("Cannot apply discount.")
        if self.payment_state == 'paid':
            raise RuntimeError("Cannot apply discount to paid invoice.")
        if self.discount_code == code:
            raise ValueError("Coupon code already applied.")

        self.discount_code = code
        if discount_type == 'percentage':
            disc = (self.amount_untaxed * value) / 100.0
        else:
            disc = min(self.amount_untaxed, value)
        self.amount_discount += disc
        self.amount_total = max(0.0, self.amount_untaxed + self.amount_tax - self.amount_discount)
        self.amount_residual = max(0.0, self.amount_total - self.amount_paid)


class MockBillingEngine:
    """Intelligent Automated Recurring Billing Engine Simulator."""

    @staticmethod
    def process_subscription_catchup(sub, target_date=None):
        today = target_date or date.today()

        # 1. Check active status
        if sub.state != 'active':
            sub.billing_logs.append({
                'status': 'skipped',
                'message': f"Subscription {sub.name} in state {sub.state}; skipped."
            })
            return 0

        # 2. Check plan assignment
        if not sub.plan:
            sub.billing_logs.append({
                'status': 'failed',
                'message': f"Subscription {sub.name} has no plan assigned."
            })
            return 0

        # 3. Handle empty next_billing_date safely
        if not sub.next_billing_date:
            if sub.last_billing_date:
                sub.next_billing_date = sub.plan.calculate_next_billing_date(sub.last_billing_date)
            else:
                sub.next_billing_date = sub.start_date or today

        if sub.next_billing_date > today:
            sub.billing_logs.append({
                'status': 'skipped',
                'message': f"Subscription {sub.name} next billing date {sub.next_billing_date} in future; skipped."
            })
            return 0

        # 4. Check contract expiry
        if sub.expiry_date and sub.next_billing_date > sub.expiry_date:
            sub.state = 'expired'
            sub.billing_logs.append({
                'status': 'skipped',
                'message': f"Subscription {sub.name} expired on {sub.expiry_date}."
            })
            return 0

        # 5. Check plan availability
        if not sub.plan.is_available_on(sub.next_billing_date):
            sub.billing_logs.append({
                'status': 'failed',
                'message': f"Plan {sub.plan.name} not available on {sub.next_billing_date}."
            })
            return 0

        generated_invoices = 0
        iteration_count = 0
        max_catchup = 365

        # Catch-up loop: processes all due cycles sequentially without leaving gaps
        while sub.next_billing_date <= today and sub.state == 'active':
            iteration_count += 1
            if iteration_count > max_catchup:
                break

            p_start = sub.next_billing_date
            p_end = sub.plan.calculate_next_billing_date(p_start) - relativedelta(days=1)

            if sub.expiry_date and p_start > sub.expiry_date:
                sub.state = 'expired'
                break

            # Idempotency Defense: Check if invoice already exists for (sub_id, p_start, p_end)
            already_exists = any(
                inv.billing_period_start == p_start and inv.billing_period_end == p_end
                for inv in sub.invoice_ids
            )

            if already_exists:
                sub.billing_logs.append({
                    'status': 'skipped',
                    'period': (p_start, p_end),
                    'message': f"Invoice already exists for {p_start} to {p_end}. Duplicate prevented."
                })
                # Advance date
                sub.last_billing_date = p_start
                sub.next_billing_date = sub.plan.calculate_next_billing_date(p_start)
                continue

            # Create Invoice
            inv = MockInvoice(sub, p_start, p_end, invoice_date=today)
            sub.invoice_ids.append(inv)
            generated_invoices += 1

            sub.last_billing_date = p_start
            sub.next_billing_date = sub.plan.calculate_next_billing_date(p_start)

            sub.billing_logs.append({
                'status': 'success',
                'invoice_name': inv.name,
                'period': (p_start, p_end),
                'amount': inv.amount_total,
                'message': f"Successfully generated invoice {inv.name}."
            })

        return generated_invoices


# ============================================================================
# UNIT TEST CASES
# ============================================================================

class TestSubscriptionModules(unittest.TestCase):

    def setUp(self):
        self.plan_monthly = MockSubscriptionPlan(
            name="Professional Monthly",
            code="PLAN-M01",
            price=100.0,
            billing_interval_unit="monthly",
            billing_interval_count=1,
            min_quantity=2.0,
            auto_close=True,
            auto_close_days=5,
            allow_early_close=True,
            allow_pause=True,
            allow_renewal=True
        )

        self.plan_daily = MockSubscriptionPlan(
            name="Daily Trial",
            code="PLAN-D01",
            price=10.0,
            billing_interval_unit="daily",
            billing_interval_count=1,
            min_quantity=1.0
        )

        self.plan_weekly = MockSubscriptionPlan(
            name="Weekly Starter",
            code="PLAN-W01",
            price=40.0,
            billing_interval_unit="weekly",
            billing_interval_count=1,
            min_quantity=1.0
        )

        self.plan_yearly = MockSubscriptionPlan(
            name="Enterprise Annual",
            code="PLAN-Y01",
            price=1000.0,
            billing_interval_unit="yearly",
            billing_interval_count=1,
            min_quantity=1.0
        )

    # ------------------------------------------------------------------------
    # MODULE 1: PRODUCT & PRODUCT VARIANT MANAGEMENT TESTS
    # ------------------------------------------------------------------------
    def test_01_product_and_odoo_variant_surcharge(self):
        """Test Product Creation and mandatory Odoo brand +560 surcharge."""
        tmpl_standard = MockProductTemplate("Brightloop CRM Base", list_price=800.0, standard_price=300.0, brand_name='standard')
        self.assertEqual(tmpl_standard.brand_surcharge, 0.0)
        self.assertEqual(tmpl_standard.subscription_price, 800.0)

        # Mandatory Example: Selecting Odoo brand variant must add 560 to price
        tmpl_odoo = MockProductTemplate("Brightloop ERP Suite", list_price=1000.0, standard_price=400.0, brand_name='odoo')
        self.assertEqual(tmpl_odoo.brand_surcharge, 560.0, "Odoo brand must add 560 surcharge")
        self.assertEqual(tmpl_odoo.subscription_price, 1560.0, "Total price must be 1000 + 560 = 1560")

        # Variant pricing engine API
        var_odoo = MockProductProduct(tmpl_odoo)
        self.assertEqual(var_odoo.get_subscription_price(), 1560.0)

        # Variant with extra attribute
        var_odoo_premium = MockProductProduct(tmpl_odoo, variant_extra=100.0)
        self.assertEqual(var_odoo_premium.get_subscription_price(), 1660.0)

        # Negative price validation
        with self.assertRaises(ValueError):
            MockProductTemplate("Invalid Negative Price", list_price=-50.0)

    # ------------------------------------------------------------------------
    # MODULE 2: SUBSCRIPTION PLAN MANAGEMENT TESTS
    # ------------------------------------------------------------------------
    def test_02_plan_validation_and_cadence_calculations(self):
        """Test Plan constraints and date calculations for Daily, Weekly, Monthly, Yearly."""
        # Validation checks
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad Plan", "BP1", price=-20.0)

        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad Qty Plan", "BP2", price=50.0, min_quantity=0.0)

        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad Dates", "BP3", price=50.0, start_date=date(2026, 12, 1), end_date=date(2026, 1, 1))

        # Cadence date tests
        dt = date(2026, 3, 15)
        self.assertEqual(self.plan_daily.calculate_next_billing_date(dt), date(2026, 3, 16))
        self.assertEqual(self.plan_weekly.calculate_next_billing_date(dt), date(2026, 3, 22))
        self.assertEqual(self.plan_monthly.calculate_next_billing_date(dt), date(2026, 4, 15))
        self.assertEqual(self.plan_yearly.calculate_next_billing_date(dt), date(2027, 3, 15))

        # Month-end boundary: Jan 31 -> Feb 28
        jan31 = date(2026, 1, 31)
        self.assertEqual(self.plan_monthly.calculate_next_billing_date(jan31), date(2026, 2, 28))

        # Leap year boundary: Feb 29 2024 -> Feb 28 2025
        leap_day = date(2024, 2, 29)
        self.assertEqual(self.plan_yearly.calculate_next_billing_date(leap_day), date(2025, 2, 28))

    # ------------------------------------------------------------------------
    # MODULE 3: QUOTATION & SUBSCRIPTION LIFECYCLE TESTS
    # ------------------------------------------------------------------------
    def test_03_subscription_lifecycle_and_state_machine(self):
        """Test Complete Lifecycle: Draft -> Quotation -> Confirmed -> Active -> Paused -> Closed."""
        sub = MockSubscription("TechCorp Inc.", self.plan_monthly, start_date=date(2026, 4, 1), expiry_date=date(2026, 10, 1))
        self.assertEqual(sub.state, 'draft')
        self.assertTrue(sub.name.startswith("SQ-"))

        # Add Product with Odoo variant (+560)
        tmpl_odoo = MockProductTemplate("Brightloop Suite", list_price=1000.0, brand_name='odoo')
        product_odoo = MockProductProduct(tmpl_odoo)

        # Quantity constraint: min_quantity is 2.0
        with self.assertRaises(ValueError):
            sub.add_line(product_odoo, quantity=1.0)  # less than min_quantity 2.0

        line = sub.add_line(product_odoo, quantity=2.0, tax_rate=10.0)
        self.assertEqual(line.unit_price, 1560.0)
        self.assertEqual(line.price_subtotal, 3120.0)
        self.assertEqual(line.price_tax, 312.0)
        self.assertEqual(line.price_total, 3432.0)

        # Subscription totals: Base Plan (100) + Line (3120) = 3220 untaxed
        self.assertEqual(sub.amount_untaxed, 3220.0)
        self.assertEqual(sub.amount_tax, 312.0)
        self.assertEqual(sub.amount_total, 3532.0)

        # 1. Draft -> Quotation
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')

        # 2. Quotation -> Confirmed
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith("SUB-"))

        # 3. Confirmed -> Active
        sub.action_activate()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, date(2026, 4, 1))

        # Check MRR / ARR Analytics
        self.assertAlmostEqual(sub.mrr, 3532.0, places=2)
        self.assertAlmostEqual(sub.arr, 3532.0 * 12.0, places=2)

        # 4. Active -> Paused
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')
        self.assertEqual(sub.pause_date, date.today())

        # 5. Paused -> Resumed
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertIsNone(sub.pause_date)

        # 6. Active -> Closed
        sub.action_close(reason="Client migrated systems")
        self.assertEqual(sub.state, 'closed')
        self.assertEqual(sub.close_reason, "Client migrated systems")

    # ------------------------------------------------------------------------
    # MODULE 4: INTELLIGENT AUTOMATED RECURRING BILLING ENGINE TESTS
    # ------------------------------------------------------------------------
    def test_04_automated_billing_engine_and_idempotency(self):
        """Test Recurring Billing Engine: Invoice creation, Idempotency defense, and Retry Safety."""
        sub = MockSubscription("Global Logistics", self.plan_monthly, start_date=date(2026, 1, 1))
        tmpl = MockProductTemplate("Logistics Module", list_price=200.0, brand_name='standard')
        prod = MockProductProduct(tmpl)
        sub.add_line(prod, quantity=2.0)

        sub.action_confirm()
        sub.action_activate()
        sub.next_billing_date = date(2026, 1, 1)

        # Run Billing Engine for Jan 1 2026
        inv_count = MockBillingEngine.process_subscription_catchup(sub, target_date=date(2026, 1, 1))
        self.assertEqual(inv_count, 1, "Should generate exactly 1 invoice for Jan 1")
        self.assertEqual(len(sub.invoice_ids), 1)

        first_invoice = sub.invoice_ids[0]
        self.assertEqual(first_invoice.billing_period_start, date(2026, 1, 1))
        self.assertEqual(first_invoice.billing_period_end, date(2026, 1, 31))
        self.assertEqual(sub.next_billing_date, date(2026, 2, 1))
        self.assertEqual(first_invoice.state, 'confirmed')

        # Test Payment Hook (Dev 2 interface)
        first_invoice.register_payment(ref="STRIPE-CH-998822")
        self.assertEqual(first_invoice.payment_state, 'paid')
        self.assertEqual(first_invoice.state, 'paid')

        # Idempotency Test: Attempting to bill again on the same period MUST NOT duplicate
        sub.next_billing_date = date(2026, 1, 1)  # intentionally point back to tested period
        inv_count_retry = MockBillingEngine.process_subscription_catchup(sub, target_date=date(2026, 1, 1))
        self.assertEqual(inv_count_retry, 0, "Retry on already billed period must generate 0 invoices")
        self.assertEqual(len(sub.invoice_ids), 1, "Invoice count must remain strictly 1")
        self.assertTrue(any(l['status'] == 'skipped' for l in sub.billing_logs), "Skipped duplicate must be logged")

    def test_05_catchup_billing_engine(self):
        """Test Catch-up Billing: Cron didn't run for 3 months, engine must generate 3 distinct invoices without gaps."""
        sub = MockSubscription("Enterprise Catchup Client", self.plan_monthly, start_date=date(2026, 1, 1))
        tmpl = MockProductTemplate("Cloud Server", list_price=500.0, brand_name='standard')
        prod = MockProductProduct(tmpl)
        sub.add_line(prod, quantity=2.0)

        sub.action_confirm()
        sub.action_activate()
        sub.next_billing_date = date(2026, 1, 1)

        # Simulate Cron execution on March 15, 2026 (Jan 1, Feb 1, Mar 1 cycles are due)
        target = date(2026, 3, 15)
        invoices_generated = MockBillingEngine.process_subscription_catchup(sub, target_date=target)

        self.assertEqual(invoices_generated, 3, "Engine must catch up exactly 3 billing cycles (Jan, Feb, Mar)")
        self.assertEqual(len(sub.invoice_ids), 3)

        periods = [(inv.billing_period_start, inv.billing_period_end) for inv in sub.invoice_ids]
        expected_periods = [
            (date(2026, 1, 1), date(2026, 1, 31)),
            (date(2026, 2, 1), date(2026, 2, 28)),
            (date(2026, 3, 1), date(2026, 3, 31)),
        ]
        self.assertEqual(periods, expected_periods, "All cycles must be sequential without gaps")
        self.assertEqual(sub.next_billing_date, date(2026, 4, 1), "Next billing date must advance to April 1")

    def test_06_paused_and_expired_subscription_safety(self):
        """Verify billing engine ignores paused, closed, and expired contracts."""
        sub = MockSubscription("Paused Corp", self.plan_monthly, start_date=date(2026, 1, 1))
        tmpl = MockProductTemplate("App", list_price=100.0)
        prod = MockProductProduct(tmpl)
        sub.add_line(prod, quantity=2.0)
        sub.action_confirm()
        sub.action_activate()
        sub.action_pause()
        sub.next_billing_date = date(2026, 1, 1)

        count = MockBillingEngine.process_subscription_catchup(sub, target_date=date(2026, 2, 1))
        self.assertEqual(count, 0, "Paused subscriptions must never be invoiced")
        self.assertEqual(len(sub.invoice_ids), 0)

    def test_07_renewal_and_early_close_policies(self):
        """Test Contract Renewal extension and early closure permissions."""
        today = date.today()
        sub = MockSubscription("Renewal Client", self.plan_monthly, start_date=today, expiry_date=today + relativedelta(months=6))
        prod = MockProductProduct(MockProductTemplate("SaaS Tier", list_price=300.0))
        sub.add_line(prod, quantity=2.0)
        sub.action_confirm()
        sub.action_activate()

        # Test Renewal: Extends expiry date by 1 month (plan interval)
        initial_expiry = sub.expiry_date
        sub.action_renew()
        self.assertEqual(sub.expiry_date, initial_expiry + relativedelta(months=1))


        # Test Early Closure Permission Disallowed
        plan_no_early_close = MockSubscriptionPlan(
            name="Strict Annual", code="STRICT-01", price=500.0,
            billing_interval_unit="yearly", allow_early_close=False
        )
        sub_strict = MockSubscription("Strict Client", plan_no_early_close, start_date=date(2026, 1, 1), expiry_date=date(2027, 1, 1))
        sub_strict.add_line(prod, quantity=1.0)
        sub_strict.action_confirm()
        sub_strict.action_activate()

        # Regular user attempt to close early must raise error
        with self.assertRaises(RuntimeError):
            sub_strict.action_close(reason="Try to leave", is_manager=False)

        # Manager override is permitted
        sub_strict.action_close(reason="Manager authorized waiver", is_manager=True)
        self.assertEqual(sub_strict.state, 'closed')
        self.assertEqual(sub_strict.close_reason, "Manager authorized waiver")

    def test_08_discounts_and_multi_tax_computations(self):
        """Test line discounts, overall subscription discount, and multi-tax calculations."""
        sub = MockSubscription("Discounted Client", self.plan_monthly, start_date=date(2026, 1, 1), discount_rate=10.0)
        prod = MockProductProduct(MockProductTemplate("Module A", list_price=200.0))
        # Line with 20% line-level discount and 15% VAT
        sub.add_line(prod, quantity=2.0, tax_rate=15.0, discount_rate=20.0)

        # Base Plan = 100
        # Line gross = 2 * 200 = 400. With 20% discount = 320.
        # Total line subtotal = 320.
        # Combined untaxed = 100 + 320 = 420.
        # Overall 10% subscription discount deduction = 42.0.
        # Amount untaxed = 420 - 42 = 378.0.
        # Line tax (15% on 320) = 48.0.
        # Total = 378.0 + 48.0 = 426.0.
        self.assertEqual(sub.amount_untaxed, 378.0)
        self.assertEqual(sub.amount_tax, 48.0)
        self.assertEqual(sub.amount_total, 426.0)

    def test_09_duplicate_surcharge_prevention(self):
        """Test Product ORM logic: Odoo +560 surcharge must not be double applied."""
        tmpl_odoo = MockProductTemplate("Odoo Cloud Host", list_price=1000.0, brand_name='odoo')
        self.assertEqual(tmpl_odoo.brand_surcharge, 560.0)
        self.assertEqual(tmpl_odoo.subscription_price, 1560.0)

        # Standard variant inherits 560 surcharge
        prod_standard = MockProductProduct(tmpl_odoo)
        self.assertEqual(prod_standard.get_subscription_price(), 1560.0)

        # If a variant attribute already configured 560 surcharge, do not double-add to 2120
        prod_with_odoo_attr = MockProductProduct(tmpl_odoo, variant_extra=560.0, variant_attr_name='Odoo')
        self.assertEqual(prod_with_odoo_attr.get_subscription_price(), 1560.0)

    def test_10_empty_next_billing_date_safety(self):
        """Test Recurring Billing Cron: Active subscription with empty next_billing_date is safely initialized and billed."""
        today = date(2026, 6, 1)
        sub = MockSubscription("Unset Date Client", self.plan_monthly, start_date=today)
        prod = MockProductProduct(MockProductTemplate("Service A", list_price=200.0))
        sub.add_line(prod, quantity=2.0)
        sub.action_confirm()
        sub.action_activate()

        # Explicitly simulate missing/empty next_billing_date
        sub.next_billing_date = None

        # Run cron billing engine
        invoices_count = MockBillingEngine.process_subscription_catchup(sub, target_date=today)
        self.assertEqual(invoices_count, 1, "Should generate exactly 1 invoice")
        self.assertEqual(len(sub.invoice_ids), 1)
        self.assertEqual(sub.next_billing_date, today + relativedelta(months=1))

        # Re-run same day (idempotent duplicate defense)
        sub.next_billing_date = today  # force date back
        retry_count = MockBillingEngine.process_subscription_catchup(sub, target_date=today)
        self.assertEqual(retry_count, 0, "Retry must not create duplicate invoice")
        self.assertEqual(len(sub.invoice_ids), 1)

    def test_11_currency_fallback_safety(self):
        """Test Currency Fallback Safety: Records with missing/unset currency do not crash tax/total computations."""
        sub = MockSubscription("Currency Test Client", self.plan_monthly, start_date=date(2026, 1, 1))
        prod = MockProductProduct(MockProductTemplate("Test Service", list_price=150.0))
        sub.add_line(prod, quantity=2.0, tax_rate=10.0)

        # Confirm calculation worked without errors
        # plan 100 + 2 * 150 = 400 untaxed. Tax 10% on 300 = 30. Total = 430
        self.assertEqual(sub.amount_tax, 30.0)
        self.assertEqual(sub.amount_total, 430.0)
        self.assertEqual(sub.currency_symbol, "$")

    def test_12_brand_surcharge_tests_a_b_c_d(self):
        """Step 3: Test A, B, C, D Brand Surcharge Validation in Standalone Suite."""
        # Test A: Base 1,000, Brand Odoo -> Surcharge 560, Price 1,560
        tmpl_a = MockProductTemplate("ERP Suite", list_price=1000.0, brand_name='odoo')
        prod_a = MockProductProduct(tmpl_a)
        self.assertEqual(tmpl_a.brand_surcharge, 560.0)
        self.assertEqual(tmpl_a.subscription_price, 1560.0)
        self.assertEqual(prod_a.subscription_price, 1560.0)

        # Test B: Base 1,000, Brand Brightloop -> Surcharge 0, Price 1,000
        tmpl_b = MockProductTemplate("Workflow App", list_price=1000.0, brand_name='brightloop')
        prod_b = MockProductProduct(tmpl_b)
        self.assertEqual(tmpl_b.brand_surcharge, 0.0)
        self.assertEqual(tmpl_b.subscription_price, 1000.0)
        self.assertEqual(prod_b.subscription_price, 1000.0)

        # Test C: Change Brand from Odoo to Brightloop -> Surcharge removed
        tmpl_a.brand_name = 'brightloop'
        self.assertEqual(tmpl_a.brand_surcharge, 0.0)
        self.assertEqual(tmpl_a.subscription_price, 1000.0)
        self.assertEqual(prod_a.subscription_price, 1000.0)

        # Switch back to Odoo
        tmpl_a.brand_name = 'odoo'
        self.assertEqual(tmpl_a.brand_surcharge, 560.0)
        self.assertEqual(tmpl_a.subscription_price, 1560.0)
        self.assertEqual(prod_a.subscription_price, 1560.0)

        # Test D: Multiple Variants with extra pricing (no duplicate surcharge)
        var_shared = MockProductProduct(tmpl_a, variant_extra=0.0)
        var_dedicated = MockProductProduct(tmpl_a, variant_extra=500.0)
        self.assertEqual(var_shared.subscription_price, 1560.0)
        self.assertEqual(var_dedicated.subscription_price, 2060.0)

        # Negative price validations
        with self.assertRaises(ValueError):
            MockProductTemplate("Invalid", list_price=-50.0)
        with self.assertRaises(ValueError):
            MockProductTemplate("Invalid", list_price=100.0, standard_price=-10.0)
        with self.assertRaises(ValueError):
            MockProductTemplate("Invalid", list_price=100.0, brand_surcharge=-5.0)

    def test_13_plan_cadence_clamping_and_policies(self):
        """Step 3, 4, 5, 6: Test Cadences, Clamping, Leap Years, and Policies in Standalone Suite."""
        # A. Daily
        plan_daily = MockSubscriptionPlan("Daily Plan", "PLAN-D", price=10.0, billing_interval_unit='daily', billing_interval_count=1)
        self.assertEqual(plan_daily.calculate_next_billing_date(date(2026, 5, 1)), date(2026, 5, 2))
        plan_daily.billing_interval_count = 14
        self.assertEqual(plan_daily.calculate_next_billing_date(date(2026, 5, 1)), date(2026, 5, 15))

        # B. Weekly
        plan_weekly = MockSubscriptionPlan("Weekly Plan", "PLAN-W", price=40.0, billing_interval_unit='weekly', billing_interval_count=1)
        self.assertEqual(plan_weekly.calculate_next_billing_date(date(2026, 6, 1)), date(2026, 6, 8))
        plan_weekly.billing_interval_count = 4
        self.assertEqual(plan_weekly.calculate_next_billing_date(date(2026, 6, 1)), date(2026, 6, 29))

        # C. Monthly & Clamping
        plan_monthly = MockSubscriptionPlan("Monthly Plan", "PLAN-M", price=100.0, billing_interval_unit='monthly', billing_interval_count=1)
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2026, 4, 15)), date(2026, 5, 15))
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2026, 1, 31)), date(2026, 2, 28))
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2028, 1, 31)), date(2028, 2, 29))
        self.assertEqual(plan_monthly.calculate_next_billing_date(date(2026, 3, 31)), date(2026, 4, 30))

        # D. Yearly & Leap Year
        plan_yearly = MockSubscriptionPlan("Yearly Plan", "PLAN-Y", price=1000.0, billing_interval_unit='yearly', billing_interval_count=1)
        self.assertEqual(plan_yearly.calculate_next_billing_date(date(2026, 8, 20)), date(2027, 8, 20))
        self.assertEqual(plan_yearly.calculate_next_billing_date(date(2028, 2, 29)), date(2029, 2, 28))

        # E. Boundary Dates & Inactive
        plan_avail = MockSubscriptionPlan("Window Plan", "PLAN-WIN", price=50.0, start_date=date(2026, 6, 1), end_date=date(2026, 8, 31))
        self.assertFalse(plan_avail.is_available_on(date(2026, 5, 31)))
        self.assertTrue(plan_avail.is_available_on(date(2026, 6, 1)))
        self.assertTrue(plan_avail.is_available_on(date(2026, 7, 15)))
        self.assertTrue(plan_avail.is_available_on(date(2026, 8, 31)))
        self.assertFalse(plan_avail.is_available_on(date(2026, 9, 1)))

        plan_avail.active = False
        self.assertFalse(plan_avail.is_available_on(date(2026, 7, 15)))

        # F. Constraints
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad", "B", price=-10.0)
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad", "B", price=10.0, min_quantity=0.0)
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad", "B", price=10.0, billing_interval_count=0)
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad", "B", price=10.0, auto_close_days=-2)
        with self.assertRaises(ValueError):
            MockSubscriptionPlan("Bad", "B", price=10.0, start_date=date(2026, 12, 1), end_date=date(2026, 1, 1))

    def test_14_quotation_and_subscription_management(self):
        """Module 3: Complete Quotation & Subscription Management verification in Standalone Suite."""
        tmpl_hosting = MockProductTemplate("Cloud Hosting", list_price=1000.0, brand_name='standard')
        prod_hosting = MockProductProduct(tmpl_hosting)
        tmpl_support = MockProductTemplate("Priority Support", list_price=200.0, brand_name='standard')
        prod_support = MockProductProduct(tmpl_support)

        # 1. Quotation Template and constraints
        tmpl = MockQuotationTemplate("Cloud Bundle", self.plan_monthly, validity_days=45, terms_and_conditions="Net 30")
        tmpl.add_line(prod_hosting, quantity=2.0)
        self.assertEqual(len(tmpl.line_ids), 1)

        with self.assertRaises(ValueError):
            MockQuotationTemplate("Bad", self.plan_monthly, validity_days=-1)
        with self.assertRaises(ValueError):
            tmpl.add_line(prod_hosting, quantity=0.0)

        # 2. Quotation Creation and Template Application
        sub = MockSubscription("Enterprise Client", self.plan_monthly)
        self.assertTrue(sub.name.startswith("SQ-"))
        self.assertEqual(sub.state, 'draft')

        sub.apply_template(tmpl)
        self.assertEqual(len(sub.line_ids), 1)
        self.assertEqual(sub.terms_and_conditions, "Net 30")
        self.assertEqual(sub.quotation_validity_date, date.today() + relativedelta(days=45))

        # 3. Tax-inclusive vs Tax-exclusive Line Calculations
        # Line 1: prod_hosting 2 qty @ 1000 = 2000 untaxed, 10% tax = 200
        line1 = sub.line_ids[0]
        line1.tax_rate = 10.0
        line1.price_include = False
        self.assertEqual(line1.price_subtotal, 2000.0)
        self.assertEqual(line1.price_tax, 200.0)
        self.assertEqual(line1.price_total, 2200.0)

        # Line 2: 2 qty @ 110 with 10% tax-included -> 200 untaxed, 20 tax, 220 total
        line2 = sub.add_line(prod_support, quantity=2.0, unit_price=110.0, tax_rate=10.0, price_include=True)
        self.assertEqual(line2.price_subtotal, 200.0)
        self.assertEqual(line2.price_tax, 20.0)
        self.assertEqual(line2.price_total, 220.0)

        # Header totals: plan (100) + line1 (2000) + line2 (200) = 2300 untaxed; tax = 220; total = 2520
        self.assertEqual(sub.amount_untaxed, 2300.0)
        self.assertEqual(sub.amount_tax, 220.0)
        self.assertEqual(sub.amount_total, 2520.0)

        # 4. Confirmation & Sequence
        sub.action_send_quotation()
        self.assertEqual(sub.state, 'quotation')

        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertTrue(sub.name.startswith("SUB-"))

        # Price immutability
        initial_subtotal = sub.amount_untaxed
        tmpl_hosting.list_price = 9999.0
        self.assertEqual(sub.amount_untaxed, initial_subtotal)

        # 5. Invalid State Transitions
        with self.assertRaises(RuntimeError):
            sub.write({'state': 'draft'})  # confirmed cannot jump back to draft
        with self.assertRaises(RuntimeError):
            sub.write({'state': 'paused'})  # must be active first

        sub.action_activate()
        self.assertEqual(sub.state, 'active')

        # 6. Pause / Resume Schedule Shifting
        initial_next_billing = date(2026, 6, 1)
        sub.next_billing_date = initial_next_billing
        sub.action_pause()
        self.assertEqual(sub.state, 'paused')

        # Simulate 10 days paused
        sub.pause_date = date.today() - relativedelta(days=10)
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.next_billing_date, initial_next_billing + relativedelta(days=10))

        # 7. Renewal
        sub.expiry_date = date(2026, 12, 31)
        sub.action_renew()
        self.assertEqual(sub.expiry_date, date(2027, 1, 31))

        # 8. Reset to draft & cancellation on quotation
        sub_quote = MockSubscription("Prospect Corp", self.plan_monthly)
        sub_quote.action_send_quotation()
        self.assertEqual(sub_quote.state, 'quotation')
        sub_quote.action_draft()
        self.assertEqual(sub_quote.state, 'draft')
        sub_quote.action_cancel()
        self.assertEqual(sub_quote.state, 'closed')

    def test_15_invoice_management_and_billing_engine(self):
        """Module 4: Complete Invoice Management & Intelligent Automated Billing Engine."""
        today = date.today()
        sub = MockSubscription("Cloud Services Ltd", self.plan_monthly, start_date=today)
        tmpl = MockProductTemplate("Database Cluster", list_price=800.0, brand_name='standard')
        prod = MockProductProduct(tmpl)
        sub.add_line(prod, quantity=2.0, tax_rate=10.0)
        sub.action_confirm()
        sub.action_activate()

        # 1. Invoice creation and lines
        # Untaxed = plan 100 + lines (2 * 800) = 1700. Tax = 160. Total = 1860.
        inv = MockInvoice(sub, today, today + relativedelta(months=1) - relativedelta(days=1), invoice_date=today, state='draft')
        self.assertEqual(inv.state, 'draft')
        self.assertEqual(inv.amount_untaxed, 1700.0)
        self.assertEqual(inv.amount_tax, 160.0)
        self.assertEqual(inv.amount_total, 1860.0)
        self.assertEqual(inv.amount_residual, 1860.0)
        self.assertEqual(inv.amount_paid, 0.0)

        # 2. Lifecycle transitions
        # Cannot register payment on draft invoice
        with self.assertRaises(RuntimeError):
            inv.register_payment(500.0)

        inv.action_confirm()
        self.assertEqual(inv.state, 'confirmed')

        # Invalid transition: confirmed cannot jump to draft if payments exist
        inv.action_draft()
        self.assertEqual(inv.state, 'draft')
        inv.action_confirm()

        # Invalid transition: cannot jump directly to paid via write if balance remains
        with self.assertRaises(RuntimeError):
            inv.write({'state': 'paid'})

        # 3. Partial Payment settlement
        inv.register_payment(amount=860.0, ref="PAY-PARTIAL-01")
        self.assertEqual(inv.payment_state, 'partial')
        self.assertEqual(inv.state, 'confirmed')
        self.assertEqual(inv.amount_paid, 860.0)
        self.assertEqual(inv.amount_residual, 1000.0)

        # Cannot cancel invoice with payments
        with self.assertRaises(RuntimeError):
            inv.action_cancel()

        # Overpayment rejection
        with self.assertRaises(ValueError):
            inv.register_payment(amount=1500.0)  # exceeds residual 1000.0

        # Full Payment settlement
        inv.register_payment(amount=1000.0, ref="PAY-FINAL-02")
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.state, 'paid')
        self.assertEqual(inv.amount_paid, 1860.0)
        self.assertEqual(inv.amount_residual, 0.0)

        # Cannot register payment on already paid invoice
        with self.assertRaises(RuntimeError):
            inv.register_payment(100.0)

        # 4. Coupon discount application
        inv_disc = MockInvoice(sub, today, today + relativedelta(days=30), invoice_date=today, state='confirmed')
        inv_disc.apply_discount_code("PROMO10", discount_type='percentage', value=10.0)
        self.assertEqual(inv_disc.discount_code, "PROMO10")
        self.assertEqual(inv_disc.amount_discount, 170.0)  # 10% of 1700
        self.assertEqual(inv_disc.amount_total, 1690.0)
        self.assertEqual(inv_disc.amount_residual, 1690.0)

        # Duplicate discount rejection
        with self.assertRaises(ValueError):
            inv_disc.apply_discount_code("PROMO10")

# Import Developer 2 User Management Verification Suite
try:
    from test_user_management_standalone import TestUserManagementAuthentication
except ImportError:
    try:
        from tests.test_user_management_standalone import TestUserManagementAuthentication
    except ImportError:
        pass

# Import Developer 2 Discount Management Verification Suite
try:
    from test_discount_management_standalone import TestDiscountManagementStandalone
except ImportError:
    try:
        from tests.test_discount_management_standalone import TestDiscountManagementStandalone
    except ImportError:
        pass

# Import Developer 2 Payment Management Verification Suite
try:
    from test_payment_management_standalone import TestPaymentManagementStandalone
except ImportError:
    try:
        from tests.test_payment_management_standalone import TestPaymentManagementStandalone
    except ImportError:
        pass

# Import Developer 2 Dashboard & Financial Reports Verification Suite
try:
    from test_dashboard_reports_standalone import TestDashboardReportsStandalone
except ImportError:
    try:
        from tests.test_dashboard_reports_standalone import TestDashboardReportsStandalone
    except ImportError:
        pass


if __name__ == '__main__':
    unittest.main()



