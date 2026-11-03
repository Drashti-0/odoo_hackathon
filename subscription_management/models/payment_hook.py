# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SubscriptionPayment(models.Model):
    _name = 'subscription.payment'
    _description = 'Subscription Payment Transaction'
    _order = 'payment_date desc, id desc'

    name = fields.Char(
        string="Transaction Reference",
        required=True,
        default=lambda self: _('New')
    )
    invoice_id = fields.Many2one(
        comodel_name='subscription.invoice',
        string="Invoice",
        required=True,
        ondelete='cascade',
        index=True
    )
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string="Customer",
        store=True
    )
    payment_date = fields.Datetime(
        string="Payment Date",
        default=fields.Datetime.now,
        required=True
    )
    amount = fields.Monetary(
        string="Settled Amount",
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string="Currency"
    )
    payment_method = fields.Selection(
        selection=[
            ('card', 'Credit / Debit Card'),
            ('bank_transfer', 'Bank Wire Transfer'),
            ('stripe', 'Stripe Gateway'),
            ('paypal', 'PayPal Gateway'),
            ('cash', 'Cash / Cheque'),
        ],
        string="Payment Method",
        default='card',
        required=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Initiated'),
            ('success', 'Successful / Settled'),
            ('failed', 'Declined / Failed'),
        ],
        string="Transaction Status",
        default='draft',
        required=True
    )
    gateway_response = fields.Text(
        string="Gateway Raw Response"
    )

    def action_confirm_payment(self):
        """Settles transaction and updates invoice state."""
        for pay in self:
            pay.state = 'success'
            pay.invoice_id.action_register_payment(amount=pay.amount, ref=pay.name)
