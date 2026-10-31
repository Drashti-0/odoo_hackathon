# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SubscriptionBillingLog(models.Model):
    _name = 'subscription.billing.log'
    _description = 'Subscription Billing Audit & Error Log'
    _order = 'execution_date desc, id desc'

    execution_date = fields.Datetime(
        string="Execution Timestamp",
        default=fields.Datetime.now,
        required=True,
        index=True
    )
    subscription_id = fields.Many2one(
        comodel_name='subscription.subscription',
        string="Subscription",
        index=True,
        ondelete='cascade'
    )
    invoice_id = fields.Many2one(
        comodel_name='subscription.invoice',
        string="Generated Invoice",
        index=True,
        ondelete='set null'
    )
    status = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('skipped', 'Skipped / Idempotent'),
            ('failed', 'Failed / Error'),
        ],
        string="Execution Status",
        required=True,
        default='success',
        index=True
    )
    billing_period_start = fields.Date(
        string="Period Start"
    )
    billing_period_end = fields.Date(
        string="Period End"
    )
    amount = fields.Monetary(
        string="Amount Invoiced",
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )
    message = fields.Text(
        string="Log Message / Summary"
    )
    error_traceback = fields.Text(
        string="Error Traceback / Diagnostics"
    )
