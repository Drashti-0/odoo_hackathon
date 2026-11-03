# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SubscriptionDiscount(models.Model):
    _name = 'subscription.discount'
    _description = 'Subscription Discount Rule & Coupon'
    _order = 'name'

    name = fields.Char(
        string="Discount Name / Promotion",
        required=True
    )
    code = fields.Char(
        string="Coupon / Promo Code",
        required=True,
        index=True
    )
    discount_type = fields.Selection(
        selection=[
            ('percentage', 'Percentage (%)'),
            ('fixed', 'Fixed Amount'),
        ],
        string="Discount Type",
        default='percentage',
        required=True
    )
    value = fields.Float(
        string="Discount Value",
        required=True,
        default=0.0
    )
    start_date = fields.Date(
        string="Valid From"
    )
    end_date = fields.Date(
        string="Valid Until"
    )
    active = fields.Boolean(
        string="Active",
        default=True
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Coupon code must be unique!'),
    ]

    def validate_and_apply(self, subscription):
        """
        Public API for Developer 2 Discount Management.
        Validates date availability and applies discount rate/amount to subscription.
        """
        self.ensure_one()
        today = fields.Date.today()
        if self.start_date and today < self.start_date:
            return False, _("Coupon not yet active.")
        if self.end_date and today > self.end_date:
            return False, _("Coupon has expired.")
        if not self.active:
            return False, _("Coupon is deactivated.")

        if self.discount_type == 'percentage':
            subscription.discount_rate = self.value
        return True, _("Coupon successfully applied.")
