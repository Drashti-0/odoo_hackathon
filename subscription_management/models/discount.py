# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

_logger = logging.getLogger(__name__)


class SubscriptionDiscount(models.Model):
    _inherit = 'subscription.discount'

    # Additional Configuration Fields for Developer 2 Discount Engine
    min_purchase_amount = fields.Monetary(
        string="Minimum Purchase Amount",
        default=0.0,
        currency_field='currency_id',
        help="Minimum untaxed subtotal required for discount eligibility."
    )
    min_quantity = fields.Float(
        string="Minimum Total Quantity",
        default=0.0,
        help="Minimum cumulative item quantity required to trigger the discount."
    )
    usage_limit = fields.Integer(
        string="Maximum Usage Limit",
        default=0,
        help="Maximum number of times this coupon can be redeemed across all subscriptions (0 = unlimited)."
    )
    usage_count = fields.Integer(
        string="Usage Count",
        default=0,
        readonly=True,
        copy=False,
        help="Number of times this coupon has been successfully applied to confirmed invoices."
    )
    applicable_product_ids = fields.Many2many(
        comodel_name='product.product',
        relation='subscription_discount_product_rel',
        column1='discount_id',
        column2='product_id',
        string="Applicable Products",
        help="Specific products eligible for this discount. If left empty, applies to all products."
    )
    apply_to_whole_subscription = fields.Boolean(
        string="Apply to Whole Subscription",
        default=True,
        help="If True, discount applies across the entire subscription/invoice total."
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )

    is_expired = fields.Boolean(
        string="Is Expired",
        compute="_compute_status",
        store=False,
        help="Calculates if the discount is past its end date."
    )
    is_available = fields.Boolean(
        string="Is Available",
        compute="_compute_status",
        store=False,
        help="Calculates if the discount is currently valid and within usage limits."
    )

    # ------------------------------------------------------------
    # CONSTRAINTS & VALIDATIONS
    # ------------------------------------------------------------

    @api.constrains('discount_type', 'value')
    def _check_discount_value(self):
        for disc in self:
            if disc.discount_type == 'percentage':
                if disc.value <= 0.0 or disc.value > 100.0:
                    raise ValidationError(_("Percentage discount must be greater than 0% and cannot exceed 100%."))
            elif disc.discount_type == 'fixed':
                if disc.value <= 0.0:
                    raise ValidationError(_("Fixed discount amount must be strictly greater than 0.0."))

    @api.constrains('min_purchase_amount')
    def _check_min_purchase(self):
        for disc in self:
            if disc.min_purchase_amount < 0.0:
                raise ValidationError(_("Minimum purchase amount cannot be negative."))

    @api.constrains('min_quantity')
    def _check_min_quantity(self):
        for disc in self:
            if disc.min_quantity < 0.0:
                raise ValidationError(_("Minimum quantity cannot be negative."))

    @api.constrains('usage_limit')
    def _check_usage_limit(self):
        for disc in self:
            if disc.usage_limit < 0:
                raise ValidationError(_("Usage limit cannot be negative."))

    @api.constrains('start_date', 'end_date')
    def _check_validity_dates(self):
        for disc in self:
            if disc.start_date and disc.end_date and disc.end_date < disc.start_date:
                raise ValidationError(
                    _("Validity End Date (%s) cannot be earlier than Start Date (%s).") % (disc.end_date, disc.start_date)
                )

    @api.depends('active', 'start_date', 'end_date', 'usage_limit', 'usage_count')
    def _compute_status(self):
        today = fields.Date.today()
        for disc in self:
            expired = False
            if disc.end_date and today > disc.end_date:
                expired = True
            disc.is_expired = expired

            available = disc.active and not expired
            if disc.start_date and today < disc.start_date:
                available = False
            if disc.usage_limit > 0 and disc.usage_count >= disc.usage_limit:
                available = False
            disc.is_available = available

    # ------------------------------------------------------------
    # ADMIN-ONLY CRUD ENFORCEMENT
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('subscription_management.group_subscription_manager') and not self.env.is_superuser():
            raise AccessError(_("Security Violation: Only Subscription Administrators can create discount rules."))
        return super().create(vals_list)

    def write(self, vals):
        is_usage_increment = set(vals.keys()) == {'usage_count'}
        if not is_usage_increment and not self.env.user.has_group('subscription_management.group_subscription_manager') and not self.env.is_superuser():
            raise AccessError(_("Security Violation: Only Subscription Administrators can modify discount rules."))
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('subscription_management.group_subscription_manager') and not self.env.is_superuser():
            raise AccessError(_("Security Violation: Only Subscription Administrators can delete discount rules."))
        return super().unlink()

    # ------------------------------------------------------------
    # CORE ELIGIBILITY & CALCULATION ENGINE
    # ------------------------------------------------------------

    def check_eligibility(self, target_date=None, subtotal=0.0, total_quantity=0.0, product_ids=None):
        """
        Server-side validation for discount eligibility:
        - Active status
        - Date validity (start_date <= today <= end_date)
        - Usage limit exhaustion check
        - Minimum purchase amount check
        - Minimum total quantity check
        - Product applicability check
        Returns (is_eligible: bool, reason_message: str)
        """
        self.ensure_one()
        check_date = target_date or fields.Date.today()

        if not self.active:
            return False, _("Discount coupon '%s' is deactivated.") % self.name
        if self.start_date and check_date < self.start_date:
            return False, _("Discount coupon '%s' is not active yet (Valid from: %s).") % (self.name, self.start_date)
        if self.end_date and check_date > self.end_date:
            return False, _("Discount coupon '%s' has expired on %s.") % (self.name, self.end_date)
        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            return False, _("Discount coupon '%s' has reached its maximum usage limit (%d/%d).") % (
                self.name, self.usage_count, self.usage_limit
            )
        if self.min_purchase_amount > 0.0 and subtotal < self.min_purchase_amount:
            return False, _("Subtotal amount (%s) does not meet the minimum purchase requirement of %s.") % (
                subtotal, self.min_purchase_amount
            )
        if self.min_quantity > 0.0 and total_quantity < self.min_quantity:
            return False, _("Total item quantity (%s) is below the minimum required quantity (%s).") % (
                total_quantity, self.min_quantity
            )
        if self.applicable_product_ids and product_ids:
            matching = set(self.applicable_product_ids.ids).intersection(set(product_ids))
            if not matching:
                return False, _("Discount coupon '%s' does not apply to any of the selected products.") % self.name

        return True, _("Discount is eligible.")

    def calculate_discount_amount(self, subtotal, matching_subtotal=None):
        """
        Calculates exact discount deduction based on rule type:
        - Percentage: eligible_amount * (value / 100.0)
        - Fixed: min(value, eligible_amount)
        Guarantees discount never exceeds eligible amount or produces negative totals.
        """
        self.ensure_one()
        base_amount = matching_subtotal if matching_subtotal is not None else subtotal
        if base_amount <= 0.0:
            return 0.0

        if self.discount_type == 'percentage':
            deduction = (base_amount * self.value) / 100.0
        elif self.discount_type == 'fixed':
            deduction = min(self.value, base_amount)
        else:
            deduction = 0.0

        return max(0.0, round(deduction, 2))

    def record_usage(self, invoice_or_contract=None):
        """
        Increments usage count safely with concurrency lock protection:
        - Locks discount record with SELECT FOR UPDATE to prevent race conditions.
        - Enforces usage_limit strictly.
        """
        self.ensure_one()
        try:
            self.env.cr.execute(
                "SELECT id, usage_count, usage_limit FROM subscription_discount WHERE id = %s FOR UPDATE",
                [self.id]
            )
            row = self.env.cr.fetchone()
            if row:
                current_count = row[1]
                limit = row[2]
                if limit > 0 and current_count >= limit:
                    raise UserError(_("Coupon '%s' has reached its maximum usage limit.") % self.code)
                self.sudo().write({'usage_count': current_count + 1})
                _logger.info("Discount %s usage recorded. New count: %d", self.code, current_count + 1)
        except Exception as e:
            # Fallback if raw SQL lock unavailable
            if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
                raise UserError(_("Coupon '%s' has reached its maximum usage limit.") % self.code)
            self.sudo().write({'usage_count': self.usage_count + 1})


# ------------------------------------------------------------
# EXTENSION: SUBSCRIPTION DISCOUNT INTEGRATION
# ------------------------------------------------------------

class SubscriptionSubscriptionDiscountExtension(models.Model):
    _inherit = 'subscription.subscription'

    discount_id = fields.Many2one(
        comodel_name='subscription.discount',
        string="Applied Discount / Coupon",
        tracking=True,
        help="Discount rule applied to this subscription contract."
    )

    def _hook_compute_discount(self, untaxed_base):
        """
        Overrides Developer 1's hook in subscription.subscription.
        Calculates eligible discount from discount_id (fixed or percentage) or fallback discount_rate.
        """
        self.ensure_one()
        if not self.discount_id:
            # Fallback to Developer 1's percentage rate
            if self.discount_rate > 0.0:
                return (untaxed_base * self.discount_rate) / 100.0
            return 0.0

        disc = self.discount_id
        today = fields.Date.today()
        total_qty = sum(self.line_ids.mapped('quantity'))
        product_ids = self.line_ids.mapped('product_id').ids

        # Check product applicability
        matching_subtotal = untaxed_base
        if disc.applicable_product_ids:
            matching_lines = self.line_ids.filtered(lambda l: l.product_id.id in disc.applicable_product_ids.ids)
            matching_subtotal = sum(matching_lines.mapped('price_subtotal'))
            if not disc.apply_to_whole_subscription and not matching_lines:
                return 0.0

        is_eligible, _msg = disc.check_eligibility(
            target_date=today,
            subtotal=untaxed_base,
            total_quantity=total_qty,
            product_ids=product_ids
        )

        if not is_eligible:
            return 0.0

        calc_base = untaxed_base if disc.apply_to_whole_subscription else matching_subtotal
        return disc.calculate_discount_amount(subtotal=untaxed_base, matching_subtotal=calc_base)

    def action_apply_discount_code(self, code=None):
        """
        Public API for applying discount coupon to subscription:
        - Validates code existence and eligibility
        - Assigns discount_id without duplicating the coupon as a line discount
        - Recomputes contract financial totals
        """
        self.ensure_one()
        promo_code = (code or self.discount_code or '').strip().upper()
        if not promo_code:
            raise UserError(_("Please provide a valid promo or coupon code."))

        disc = self.env['subscription.discount'].search([('code', '=ilike', promo_code)], limit=1)
        if not disc:
            raise UserError(_("No active discount rule found matching code '%s'.") % promo_code)

        today = fields.Date.today()
        base_plan_price = self.plan_id.price if self.plan_id else 0.0
        subtotal = base_plan_price + sum(self.line_ids.mapped('price_subtotal'))
        total_qty = sum(self.line_ids.mapped('quantity'))
        product_ids = self.line_ids.mapped('product_id').ids

        is_eligible, reason = disc.check_eligibility(
            target_date=today,
            subtotal=subtotal,
            total_quantity=total_qty,
            product_ids=product_ids
        )
        if not is_eligible:
            raise UserError(reason)

        self.discount_id = disc.id
        self.discount_code = disc.code
        self.discount_rate = 0.0

        self._compute_amounts()
        self.message_post(body=_("Discount '%s' (%s) successfully applied. Deduction: %s") % (
            disc.name, disc.code, self.amount_discount
        ))
        return True


# ------------------------------------------------------------
# EXTENSION: INVOICE DISCOUNT INTEGRATION & DUPLICATE DEFENSE
# ------------------------------------------------------------

class SubscriptionInvoiceDiscountExtension(models.Model):
    _inherit = 'subscription.invoice'

    discount_id = fields.Many2one(
        comodel_name='subscription.discount',
        string="Discount Rule",
        readonly=True,
        tracking=True,
        help="Discount rule linked to this recurring invoice."
    )
    discount_code = fields.Char(
        string="Applied Coupon Code",
        readonly=True,
        tracking=True
    )
    discount_usage_recorded = fields.Boolean(
        string="Discount Usage Recorded",
        default=False,
        copy=False,
        help="Prevents duplicate usage increments during retries or multiple confirmations."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Automatic Discount Inheritance upon invoice generation:
        When the automated billing engine generates an invoice for a subscription with
        an active discount, the invoice automatically inherits the discount rule.
        """
        for vals in vals_list:
            sub_id = vals.get('subscription_id')
            if sub_id and not vals.get('discount_id'):
                sub = self.env['subscription.subscription'].browse(sub_id)
                if sub.discount_id and sub.discount_id.is_available:
                    vals['discount_id'] = sub.discount_id.id
                    vals['discount_code'] = sub.discount_id.code

        invoices = super().create(vals_list)

        for inv in invoices:
            # If created in confirmed state (e.g. by recurring billing cron), record usage safely
            if inv.state == 'confirmed' and inv.discount_id and not inv.discount_usage_recorded:
                inv.discount_id.record_usage(invoice_or_contract=inv)
                inv.discount_usage_recorded = True

        return invoices

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.discount_amount', 'discount_id')
    def _compute_amounts(self):
        """
        Idempotent invoice amount calculation:
        - Calculates line-level subtotal and taxes
        - Applies eligible discount without duplicate deductions on repeated execution
        - Guarantees amount_total >= 0.0
        """
        super()._compute_amounts()
        for inv in self:
            if not inv.discount_id:
                continue

            disc = inv.discount_id
            gross_untaxed = sum(inv.line_ids.mapped('price_subtotal'))
            total_qty = sum(inv.line_ids.mapped('quantity'))
            product_ids = inv.line_ids.mapped('product_id').ids

            is_eligible, _msg = disc.check_eligibility(
                target_date=inv.invoice_date or fields.Date.today(),
                subtotal=gross_untaxed,
                total_quantity=total_qty,
                product_ids=product_ids
            )

            if is_eligible:
                matching_base = gross_untaxed
                if disc.applicable_product_ids:
                    matching_lines = inv.line_ids.filtered(lambda l: l.product_id.id in disc.applicable_product_ids.ids)
                    matching_base = sum(matching_lines.mapped('price_subtotal'))
                    if not disc.apply_to_whole_subscription and not matching_lines:
                        matching_base = 0.0

                calc_base = gross_untaxed if disc.apply_to_whole_subscription else matching_base
                disc_deduction = disc.calculate_discount_amount(subtotal=gross_untaxed, matching_subtotal=calc_base)

                inv.amount_discount = disc_deduction
                # Recompute total with safe non-negative floor
                inv.amount_total = max(0.0, gross_untaxed + inv.amount_tax - disc_deduction)

    def action_confirm(self):
        """
        Transitions: Draft -> Confirmed.
        Records discount usage count exactly once.
        """
        res = super().action_confirm()
        for inv in self:
            if inv.discount_id and not inv.discount_usage_recorded:
                inv.discount_id.record_usage(invoice_or_contract=inv)
                inv.discount_usage_recorded = True
        return res

    def action_cancel(self):
        """
        Transitions: Confirmed -> Cancelled.
        Decrements discount usage count if it was previously recorded.
        """
        for inv in self:
            if inv.discount_id and inv.discount_usage_recorded:
                inv.discount_id.sudo().write({'usage_count': max(0, inv.discount_id.usage_count - 1)})
                inv.discount_usage_recorded = False
        return super().action_cancel()

    def apply_discount_code(self, code):
        """
        Public API for manual coupon redemption on an invoice:
        - Prevents duplicate application of the same coupon
        - Idempotent: re-applying the same coupon returns clean confirmation
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Discounts can only be added to draft invoices."))

        clean_code = (code or '').strip().upper()
        if not clean_code:
            raise UserError(_("Please provide a coupon code."))

        # Idempotency check: Already applied
        if self.discount_id and self.discount_id.code == clean_code:
            return True

        disc = self.env['subscription.discount'].search([('code', '=ilike', clean_code)], limit=1)
        if not disc:
            raise UserError(_("No valid discount rule found for code '%s'.") % clean_code)

        gross = sum(self.line_ids.mapped('price_subtotal'))
        total_qty = sum(self.line_ids.mapped('quantity'))
        product_ids = self.line_ids.mapped('product_id').ids

        is_eligible, reason = disc.check_eligibility(
            target_date=self.invoice_date or fields.Date.today(),
            subtotal=gross,
            total_quantity=total_qty,
            product_ids=product_ids
        )
        if not is_eligible:
            raise UserError(reason)

        self.discount_id = disc.id
        self.discount_code = disc.code
        self._compute_amounts()
        self.message_post(body=_("Coupon '%s' applied. Discount deduction: %s") % (disc.code, self.amount_discount))
        return True
