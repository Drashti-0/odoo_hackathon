# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

_logger = logging.getLogger(__name__)


class SubscriptionPayment(models.Model):
    _inherit = 'subscription.payment'

    # Extended payment fields
    payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash / Cheque'),
            ('bank_transfer', 'Bank Wire Transfer'),
            ('upi', 'UPI / Instant Transfer'),
            ('card', 'Credit / Debit Card'),
            ('stripe', 'Stripe Gateway'),
            ('paypal', 'PayPal Gateway'),
            ('other', 'Other Manual Method'),
        ],
        string="Payment Method",
        default='card',
        required=True
    )
    payment_note = fields.Text(
        string="Payment Note / Remarks",
        help="Internal audit note or wire/bank confirmation note."
    )

    # ------------------------------------------------------------
    # CONSTRAINTS & VALIDATIONS
    # ------------------------------------------------------------

    @api.constrains('amount')
    def _check_payment_amount(self):
        for pay in self:
            if pay.amount <= 0.0:
                raise ValidationError(_("Payment amount must be strictly greater than 0.0."))

    @api.constrains('amount', 'invoice_id', 'state')
    def _check_payment_against_residual(self):
        for pay in self:
            if pay.state == 'success' and pay.invoice_id:
                # Calculate what residual would be excluding this payment
                other_settled = sum(
                    pay.invoice_id.payment_ids.filtered(lambda p: p.id != pay.id and p.state == 'success').mapped('amount')
                )
                allowed_max = round(pay.invoice_id.amount_total - other_settled, 2)
                if round(pay.amount, 2) > allowed_max:
                    raise ValidationError(
                        _("Payment amount (%s) exceeds the outstanding invoice balance of %s.") %
                        (pay.amount, allowed_max)
                    )

    # ------------------------------------------------------------
    # ACTIONS & STATE TRANSITIONS
    # ------------------------------------------------------------

    def action_confirm_payment(self):
        """
        Settles transaction and updates invoice payment status.
        - Verifies caller has Staff or Admin permissions (portal customers cannot confirm).
        - Idempotent: re-confirming already settled payment is a safe no-op.
        - Reconciles invoice balance and state.
        """
        is_staff_or_admin = (
            self.env.user.has_group('subscription_management.group_subscription_user')
            or self.env.user.has_group('subscription_management.group_subscription_manager')
            or self.env.is_superuser()
        )
        if not is_staff_or_admin:
            raise AccessError(_("Security Violation: Portal customers cannot confirm or alter payment settlements."))

        for pay in self:
            if pay.state == 'success':
                # Idempotent duplicate check: already settled
                continue

            # Validate against residual balance
            inv = pay.invoice_id
            if round(pay.amount, 2) > round(inv.amount_residual, 2):
                raise UserError(
                    _("Payment amount (%s) exceeds the invoice's outstanding balance (%s).") %
                    (pay.amount, inv.amount_residual)
                )

            pay.state = 'success'
            inv._reconcile_payments()
            inv.message_post(body=_("Payment %s of amount %s settled via %s.") % (
                pay.name, pay.amount, dict(pay._fields['payment_method'].selection).get(pay.payment_method, pay.payment_method)
            ))

    def action_fail_payment(self, reason=None):
        """Marks transaction as failed without modifying invoice balance."""
        is_staff_or_admin = (
            self.env.user.has_group('subscription_management.group_subscription_user')
            or self.env.user.has_group('subscription_management.group_subscription_manager')
            or self.env.is_superuser()
        )
        if not is_staff_or_admin:
            raise AccessError(_("Security Violation: Portal customers cannot alter payment status."))

        for pay in self:
            was_success = (pay.state == 'success')
            pay.state = 'failed'
            if reason:
                pay.gateway_response = reason
            if was_success:
                pay.invoice_id._reconcile_payments()
            pay.invoice_id.message_post(body=_("Payment %s marked as failed. Reason: %s") % (pay.name, reason or "Declined"))


# ------------------------------------------------------------
# EXTENSION: INVOICE PAYMENT RECONCILIATION
# ------------------------------------------------------------

class SubscriptionInvoicePaymentExtension(models.Model):
    _inherit = 'subscription.invoice'

    payment_ids = fields.One2many(
        comodel_name='subscription.payment',
        inverse_name='invoice_id',
        string="Payment Transactions",
        copy=False,
        readonly=True
    )
    amount_paid = fields.Monetary(
        string="Amount Paid",
        compute="_compute_payment_totals",
        store=True,
        tracking=True,
        currency_field='currency_id',
        help="Total amount received and confirmed across all successful payments."
    )
    amount_residual = fields.Monetary(
        string="Outstanding Balance",
        compute="_compute_payment_totals",
        store=True,
        tracking=True,
        currency_field='currency_id',
        help="Remaining unpaid balance on this invoice."
    )
    is_overdue = fields.Boolean(
        string="Is Overdue",
        compute="_compute_overdue",
        store=True,
        help="Flag indicating invoice payment is past due date."
    )
    days_overdue = fields.Integer(
        string="Days Overdue",
        compute="_compute_overdue",
        help="Number of days past due date."
    )

    @api.depends('amount_total', 'payment_ids.state', 'payment_ids.amount')
    def _compute_payment_totals(self):
        """
        Reconciles all payments for this invoice:
        - Sums only settled payments (state == 'success').
        - Draft and Failed payments do NOT affect balance.
        - Idempotent: repeated re-computation does not compound amounts.
        - Sets payment_state: 'paid', 'partial', or 'not_paid'.
        - Updates invoice state: transitions to 'paid' when residual is 0.
        """
        for inv in self:
            settled_payments = inv.payment_ids.filtered(lambda p: p.state == 'success')
            paid = round(sum(settled_payments.mapped('amount')), 2)
            total = round(inv.amount_total or 0.0, 2)
            residual = max(0.0, round(total - paid, 2))

            inv.amount_paid = paid
            inv.amount_residual = residual

            if inv.state in ('confirmed', 'paid'):
                if residual <= 0.001 and total > 0.0:
                    inv.payment_state = 'paid'
                    inv.state = 'paid'
                elif paid > 0.0:
                    inv.payment_state = 'partial'
                    inv.state = 'confirmed'
                else:
                    inv.payment_state = 'not_paid'
                    inv.state = 'confirmed'

    @api.depends('due_date', 'payment_state', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for inv in self:
            if inv.due_date and inv.state == 'confirmed' and inv.payment_state != 'paid' and inv.due_date < today:
                inv.is_overdue = True
                inv.days_overdue = (today - inv.due_date).days
            else:
                inv.is_overdue = False
                inv.days_overdue = 0

    def _reconcile_payments(self):
        """Public helper to recompute payment totals and status."""
        self._compute_payment_totals()
        self._compute_overdue()

    def action_register_payment(self, amount=None, ref=None, payment_method='card', note=None):
        """
        Programmatic and UI action for registering a payment:
        - If amount is None, opens the interactive Payment Registration Wizard.
        - If amount is provided, creates a payment record and confirms settlement.
        """
        self.ensure_one()
        if self.state not in ('confirmed', 'paid'):
            raise UserError(_("Invoices must be confirmed before registering payment."))

        # If called without amount from UI button, open registration wizard
        if amount is None:
            return {
                'name': _("Register Payment"),
                'type': 'ir.actions.act_window',
                'res_model': 'subscription.payment.register.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_invoice_id': self.id,
                    'default_amount': self.amount_residual,
                }
            }

        # Programmatic registration
        pay_amount = float(amount)
        if pay_amount <= 0.0:
            raise UserError(_("Payment amount must be strictly greater than 0.0."))
        if round(pay_amount, 2) > round(self.amount_residual, 2):
            raise UserError(
                _("Payment amount (%s) exceeds invoice outstanding balance (%s).") %
                (pay_amount, self.amount_residual)
            )

        payment = self.env['subscription.payment'].create({
            'invoice_id': self.id,
            'name': ref or _('PAY-') + self.name,
            'amount': pay_amount,
            'payment_method': payment_method,
            'payment_note': note,
            'state': 'draft',
        })
        payment.action_confirm_payment()
        return True


# ------------------------------------------------------------
# PAYMENT REGISTRATION WIZARD
# ------------------------------------------------------------

class SubscriptionPaymentRegisterWizard(models.TransientModel):
    _name = 'subscription.payment.register.wizard'
    _description = 'Register Subscription Payment'

    invoice_id = fields.Many2one(
        comodel_name='subscription.invoice',
        string="Invoice",
        required=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string="Customer",
        readonly=True
    )
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string="Currency",
        readonly=True
    )
    amount_total = fields.Monetary(
        related='invoice_id.amount_total',
        string="Total Invoiced",
        readonly=True
    )
    amount_residual = fields.Monetary(
        related='invoice_id.amount_residual',
        string="Outstanding Balance",
        readonly=True
    )
    amount = fields.Monetary(
        string="Payment Amount",
        required=True,
        currency_field='currency_id'
    )
    payment_date = fields.Datetime(
        string="Payment Date",
        default=fields.Datetime.now,
        required=True
    )
    payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash / Cheque'),
            ('bank_transfer', 'Bank Wire Transfer'),
            ('upi', 'UPI / Instant Transfer'),
            ('card', 'Credit / Debit Card'),
            ('stripe', 'Stripe Gateway'),
            ('paypal', 'PayPal Gateway'),
            ('other', 'Other Manual Method'),
        ],
        string="Payment Method",
        default='card',
        required=True
    )
    payment_reference = fields.Char(
        string="Transaction Reference / Cheque #",
        placeholder="e.g. WIRE-889922, CHQ-0012"
    )
    payment_note = fields.Text(
        string="Payment Note / Memo",
        placeholder="Add any internal transaction notes..."
    )

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.amount = self.invoice_id.amount_residual

    def action_submit_payment(self):
        self.ensure_one()
        if self.amount <= 0.0:
            raise ValidationError(_("Payment amount must be strictly greater than 0.0."))
        if round(self.amount, 2) > round(self.amount_residual, 2):
            raise ValidationError(
                _("Payment amount (%s) exceeds outstanding balance (%s).") %
                (self.amount, self.amount_residual)
            )

        payment = self.env['subscription.payment'].create({
            'invoice_id': self.invoice_id.id,
            'name': self.payment_reference or _('PAY-') + self.invoice_id.name,
            'amount': self.amount,
            'payment_date': self.payment_date,
            'payment_method': self.payment_method,
            'payment_note': self.payment_note,
            'state': 'draft',
        })
        payment.action_confirm_payment()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Payment Recorded"),
                'message': _("Payment of %s has been successfully recorded against invoice %s.") %
                           (self.amount, self.invoice_id.name),
                'type': 'success',
                'sticky': False,
            }
        }
