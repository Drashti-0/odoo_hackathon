# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Billing Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string="Plan Name",
        required=True,
        tracking=True,
        help="Name of the subscription plan (e.g. Daily Trial, Weekly Starter, Monthly Pro, Annual Enterprise)."
    )
    code = fields.Char(
        string="Plan Code",
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help="Unique identifier code for API and integration."
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="If unchecked, this plan will be hidden without being deleted."
    )
    price = fields.Float(
        string="Plan Base Price",
        required=True,
        default=0.0,
        digits='Product Price',
        tracking=True,
        help="Base recurring subscription fee charged per interval (excluding line items)."
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )
    billing_interval_unit = fields.Selection(
        selection=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        string="Billing Frequency",
        required=True,
        default='monthly',
        tracking=True,
        help="Recurring billing interval cadence."
    )
    billing_interval_count = fields.Integer(
        string="Interval Multiplier",
        default=1,
        required=True,
        help="Cycle frequency count (e.g. 1 Month, 3 Months, 1 Year)."
    )
    min_quantity = fields.Float(
        string="Minimum Order Quantity",
        default=1.0,
        required=True,
        tracking=True,
        help="Minimum required product quantity for subscription lines under this plan."
    )
    start_date = fields.Date(
        string="Availability Start Date",
        tracking=True,
        help="Date from which this plan becomes available for new subscriptions."
    )
    end_date = fields.Date(
        string="Availability End Date",
        tracking=True,
        help="Date after which this plan is retired or unavailable for new subscriptions."
    )
    auto_close = fields.Boolean(
        string="Automatic Closing Upon Expiry",
        default=True,
        tracking=True,
        help="If enabled, active subscriptions on this plan will automatically close once their expiry date passes."
    )
    auto_close_days = fields.Integer(
        string="Auto-Close Grace Period (Days)",
        default=0,
        help="Number of grace period days after expiry before the subscription is automatically closed."
    )
    allow_early_close = fields.Boolean(
        string="Permit Early Closure",
        default=True,
        tracking=True,
        help="Permits customers or account managers to terminate the subscription prior to its expiry date."
    )
    allow_pause = fields.Boolean(
        string="Permit Subscription Pause",
        default=True,
        tracking=True,
        help="Allows subscribers to temporarily pause billing and services."
    )
    allow_renewal = fields.Boolean(
        string="Permit Subscription Renewal",
        default=True,
        tracking=True,
        help="Enables automatic or one-click manual renewal upon expiration."
    )
    description = fields.Html(
        string="Terms & Plan Description",
        help="Customer-facing description of SLA, terms, and included services."
    )
    subscription_count = fields.Integer(
        string="Active Subscriptions",
        compute="_compute_subscription_count",
        help="Total number of active subscriptions utilizing this plan."
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Subscription plan code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('subscription.plan') or vals.get('name', 'PLAN')
        return super(SubscriptionPlan, self).create(vals_list)

    @api.constrains('price')
    def _check_price(self):
        for plan in self:
            if plan.price < 0.0:
                raise ValidationError(_("Plan price cannot be negative."))

    @api.constrains('min_quantity')
    def _check_min_quantity(self):
        for plan in self:
            if plan.min_quantity < 1.0:
                raise ValidationError(_("Minimum quantity must be at least 1.0."))

    @api.constrains('billing_interval_count')
    def _check_interval_count(self):
        for plan in self:
            if plan.billing_interval_count < 1:
                raise ValidationError(_("Billing interval count must be at least 1."))

    @api.constrains('auto_close_days')
    def _check_auto_close_days(self):
        for plan in self:
            if plan.auto_close_days < 0:
                raise ValidationError(_("Auto-close grace period days cannot be negative."))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for plan in self:
            if plan.start_date and plan.end_date and plan.end_date < plan.start_date:
                raise ValidationError(_("Availability end date (%s) cannot precede start date (%s).") % (plan.end_date, plan.start_date))

    def is_available_on(self, check_date=None):
        """Validates if the plan is eligible for use on the specified date."""
        self.ensure_one()
        if not self.active:
            return False
        target = fields.Date.to_date(check_date) if check_date else fields.Date.today()
        if self.start_date and target < self.start_date:
            return False
        if self.end_date and target > self.end_date:
            return False
        return True

    def calculate_next_billing_date(self, current_date):
        """
        Calculates the next billing date based on interval and count.
        Handles daily, weekly, monthly (including end-of-month), and yearly (including leap years).
        """
        self.ensure_one()
        c_date = fields.Date.to_date(current_date) if current_date else fields.Date.today()

        count = self.billing_interval_count or 1
        unit = self.billing_interval_unit

        if unit == 'daily':
            return c_date + relativedelta(days=count)
        elif unit == 'weekly':
            return c_date + relativedelta(weeks=count)
        elif unit == 'monthly':
            return c_date + relativedelta(months=count)
        elif unit == 'yearly':
            return c_date + relativedelta(years=count)
        return c_date + relativedelta(months=1)

    def _compute_subscription_count(self):
        # We can dynamically count linked subscriptions
        sub_data = self.env['subscription.subscription'].read_group(
            domain=[('plan_id', 'in', self.ids), ('state', '=', 'active')],
            fields=['plan_id'],
            groupby=['plan_id']
        )
        data_dict = {d['plan_id'][0]: d.get('plan_id_count', d.get('__count', 0)) for d in sub_data}
        for plan in self:
            plan.subscription_count = data_dict.get(plan.id, 0)

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'name': _("Subscriptions - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
