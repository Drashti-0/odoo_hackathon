# -*- coding: utf-8 -*-
import logging
import traceback
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SubscriptionInvoice(models.Model):
    _name = 'subscription.invoice'
    _description = 'Subscription Invoice & Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'invoice_date desc, id desc'

    name = fields.Char(
        string="Invoice Number",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )
    subscription_id = fields.Many2one(
        comodel_name='subscription.subscription',
        string="Subscription Contract",
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
        index=True,
        tracking=True
    )
    invoice_date = fields.Date(
        string="Invoice Date",
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    due_date = fields.Date(
        string="Payment Due Date",
        tracking=True
    )
    billing_period_start = fields.Date(
        string="Billing Period Start",
        required=True,
        tracking=True,
        index=True
    )
    billing_period_end = fields.Date(
        string="Billing Period End",
        required=True,
        tracking=True,
        index=True
    )
    payment_terms = fields.Char(
        string="Payment Terms",
        default="Immediate Payment"
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed / Posted'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ],
        string="Status",
        default='draft',
        required=True,
        tracking=True,
        index=True
    )

    # Developer 2 Payment Integration Interface
    payment_state = fields.Selection(
        selection=[
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Fully Paid'),
        ],
        string="Payment Status",
        default='not_paid',
        required=True,
        tracking=True,
        compute='_compute_amounts',
        store=True,
        readonly=False,
        help="Maintained by Developer 2 Payment Gateway Module."
    )
    payment_reference = fields.Char(
        string="Payment Reference / Transaction ID",
        tracking=True,
        help="External transaction reference populated upon settlement."
    )
    payment_ids = fields.One2many(
        comodel_name='subscription.payment',
        inverse_name='invoice_id',
        string="Payment Transactions"
    )

    # Developer 2 Discount Integration Interface
    discount_id = fields.Many2one(
        comodel_name='subscription.discount',
        string="Applied Coupon",
        ondelete='set null',
        tracking=True
    )
    discount_code = fields.Char(
        string="Discount Code",
        tracking=True
    )
    discount_type = fields.Selection(
        selection=[
            ('percentage', 'Percentage (%)'),
            ('fixed', 'Fixed Amount'),
        ],
        string="Discount Type"
    )
    discount_value = fields.Float(
        string="Discount Value",
        default=0.0
    )

    # Lines & Financials
    line_ids = fields.One2many(
        comodel_name='subscription.invoice.line',
        inverse_name='invoice_id',
        string="Invoice Lines",
        copy=True
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        compute='_compute_currency_id',
        store=True,
        readonly=False,
        precompute=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        default=lambda self: self.env.company
    )

    @api.depends('company_id', 'subscription_id.currency_id')
    def _compute_currency_id(self):
        for inv in self:
            if not inv.currency_id:
                inv.currency_id = (
                    inv.subscription_id.currency_id
                    or inv.company_id.currency_id
                    or self.env.company.currency_id
                )

    amount_untaxed = fields.Monetary(
        string="Subtotal (Untaxed)",
        compute="_compute_amounts",
        store=True,
        tracking=True
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        compute="_compute_amounts",
        store=True
    )
    amount_discount = fields.Monetary(
        string="Discount Deductions",
        compute="_compute_amounts",
        store=True,
        tracking=True,
        help="Applied discounts from Developer 2 discount engine."
    )
    amount_total = fields.Monetary(
        string="Total Invoiced",
        compute="_compute_amounts",
        store=True,
        tracking=True
    )
    amount_paid = fields.Monetary(
        string="Amount Paid",
        compute="_compute_amounts",
        store=True,
        tracking=True
    )
    amount_residual = fields.Monetary(
        string="Outstanding Balance",
        compute="_compute_amounts",
        store=True,
        tracking=True
    )

    # SQL Constraint for Idempotency: Prevents duplicate invoices for the same period
    _sql_constraints = [
        ('uniq_subscription_period',
         'unique(subscription_id, billing_period_start, billing_period_end)',
         'An invoice has already been generated for this subscription and billing period! Duplicate creation prevented.')
    ]

    # ------------------------------------------------------------
    # COMPUTE & CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.invoice') or _('INV-NEW')
        return super(SubscriptionInvoice, self).create(vals_list)

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('bypass_state_validation'):
            new_state = vals['state']
            valid_transitions = {
                'draft': {'confirmed', 'cancel'},
                'confirmed': {'draft', 'paid', 'cancel'},
                'paid': set(),  # Paid invoices cannot transition directly without refund/credit note
                'cancel': {'draft'},
            }
            for inv in self:
                if inv.state != new_state:
                    allowed = valid_transitions.get(inv.state, set())
                    if new_state not in allowed:
                        raise UserError(_("Direct transition from '%s' to '%s' is not permitted for invoice %s.") % (
                            inv.state, new_state, inv.name
                        ))
                    if new_state == 'paid' and inv.amount_residual > 0.001 and inv.amount_total > 0.001:
                        raise UserError(_("Cannot mark invoice %s as paid when outstanding balance is %s.") % (
                            inv.name, inv.amount_residual
                        ))
        return super(SubscriptionInvoice, self).write(vals)

    @api.depends(
        'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.discount_amount',
        'discount_value', 'discount_type', 'discount_id',
        'payment_ids.amount', 'payment_ids.state'
    )
    def _compute_amounts(self):
        for inv in self:
            untaxed = sum(inv.line_ids.mapped('price_subtotal'))
            tax = sum(inv.line_ids.mapped('price_tax'))
            line_discount = sum(inv.line_ids.mapped('discount_amount'))

            inv_discount = 0.0
            if inv.discount_id or inv.discount_value > 0.0:
                if inv.discount_type == 'percentage':
                    if line_discount == 0.0:
                        inv_discount = (untaxed * (inv.discount_value or 0.0)) / 100.0
                elif inv.discount_type == 'fixed':
                    inv_discount = min(untaxed, inv.discount_value or 0.0)

            total_discount = line_discount + inv_discount
            net_total = max(0.0, untaxed + tax - inv_discount)

            inv.amount_untaxed = untaxed
            inv.amount_tax = tax
            inv.amount_discount = total_discount
            inv.amount_total = net_total

            successful_payments = inv.payment_ids.filtered(lambda p: p.state == 'success')
            total_paid = sum(successful_payments.mapped('amount'))
            inv.amount_paid = total_paid
            residual = max(0.0, net_total - total_paid)
            inv.amount_residual = residual

            if inv.state in ('confirmed', 'paid'):
                if net_total > 0.001 and total_paid <= 0.001:
                    inv.payment_state = 'not_paid'
                    if inv.state == 'paid':
                        inv.state = 'confirmed'
                elif 0.001 < total_paid < net_total - 0.001:
                    inv.payment_state = 'partial'
                    if inv.state == 'paid':
                        inv.state = 'confirmed'
                elif residual <= 0.001 and (total_paid > 0.001 or net_total <= 0.001):
                    inv.payment_state = 'paid'
                    inv.state = 'paid'
                else:
                    inv.payment_state = 'not_paid'

    def _compute_payment_and_residual(self):
        """Deprecated: retained for backwards compatibility; delegates to _compute_amounts."""
        self._compute_amounts()

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_confirm(self):
        """Transitions: Draft -> Confirmed/Posted"""
        for inv in self:
            if inv.state != 'draft':
                raise UserError(_("Only draft invoices can be confirmed."))
            if not inv.line_ids:
                raise UserError(_("Cannot confirm an invoice without lines."))
            inv.state = 'confirmed'
            # Trigger residual and payment status computation upon confirmation
            inv._compute_payment_and_residual()
            inv.message_post(body=_("Invoice %s confirmed and posted for billing period %s to %s.") % (
                inv.name, inv.billing_period_start, inv.billing_period_end
            ))
        return True

    def action_draft(self):
        """Transitions: Confirmed (unpaid) / Cancel -> Draft"""
        for inv in self:
            if inv.state == 'paid' or inv.payment_state == 'paid':
                raise UserError(_("Cannot reset a paid invoice to draft."))
            if inv.amount_paid > 0.0:
                raise UserError(_("Cannot reset an invoice with registered payments to draft. Cancel or unlink payments first."))
            inv.state = 'draft'
            inv.payment_state = 'not_paid'
            inv.message_post(body=_("Invoice %s was reset to draft.") % inv.name)
        return True

    def action_cancel(self):
        """Transitions: Draft / Confirmed -> Cancelled"""
        for inv in self:
            if inv.state == 'paid' or inv.payment_state == 'paid':
                raise UserError(_("Cannot cancel a paid invoice. Please process a refund or credit note."))
            if inv.amount_paid > 0.0:
                raise UserError(_("Cannot cancel an invoice with registered payments. Cancel or refund payments first."))
            inv.state = 'cancel'
            inv.payment_state = 'not_paid'
            inv.message_post(body=_("Invoice %s was cancelled.") % inv.name)
        return True

    def action_register_payment(self, amount=None, ref=None, payment_method='card'):
        """
        Public Developer 2 Hook for Payment Settlement.
        Reconciles payment against outstanding balance, records payment transaction,
        updates payment_state ('partial' or 'paid'), and marks invoice 'paid' once fully settled.
        """
        for inv in self:
            if inv.state != 'confirmed':
                raise UserError(_("Invoices must be confirmed before registering payment."))
            if inv.payment_state == 'paid' or inv.amount_residual <= 0.001:
                raise UserError(_("Invoice %s is already fully paid.") % inv.name)

            settle_amount = amount if amount is not None else inv.amount_residual
            if settle_amount <= 0.0:
                raise UserError(_("Payment amount must be strictly positive."))
            if settle_amount > inv.amount_residual + 0.001:
                raise UserError(_("Payment amount (%s) exceeds outstanding balance (%s).") % (
                    settle_amount, inv.amount_residual
                ))

            pay_ref = ref or f"PAY-{inv.name}-{len(inv.payment_ids) + 1:02d}"
            existing_pay = inv.payment_ids.filtered(lambda p: p.name == pay_ref and p.state == 'success')
            if not existing_pay:
                self.env['subscription.payment'].create({
                    'name': pay_ref,
                    'invoice_id': inv.id,
                    'amount': settle_amount,
                    'payment_method': payment_method,
                    'state': 'success',
                })

            inv._compute_payment_and_residual()

            inv.message_post(body=_(
                "Payment registered. Reference: %s, Amount: %s %s. Remaining Balance: %s %s."
            ) % (
                pay_ref, settle_amount, inv.currency_id.symbol or '',
                inv.amount_residual, inv.currency_id.symbol or ''
            ))
        return True

    def apply_discount_code(self, code):
        """
        Public Developer 2 Hook for Invoice Discount / Coupon Redemption.
        Finds valid subscription.discount, applies it to invoice without double-counting.
        """
        self.ensure_one()
        if self.state not in ('draft', 'confirmed'):
            raise UserError(_("Discounts can only be applied to draft or confirmed unpaid invoices."))
        if self.payment_state == 'paid':
            raise UserError(_("Cannot apply discount to a paid invoice."))
        if self.discount_code and self.discount_code == code:
            raise UserError(_("Coupon code '%s' is already applied to this invoice.") % code)

        discount_rec = self.env['subscription.discount'].search([('code', '=', code), ('active', '=', True)], limit=1)
        if not discount_rec:
            raise UserError(_("Invalid or inactive coupon code: %s") % code)

        today = fields.Date.today()
        if discount_rec.start_date and today < discount_rec.start_date:
            raise UserError(_("Coupon '%s' is not yet active.") % code)
        if discount_rec.end_date and today > discount_rec.end_date:
            raise UserError(_("Coupon '%s' has expired.") % code)

        self.discount_id = discount_rec.id
        self.discount_code = discount_rec.code
        self.discount_type = discount_rec.discount_type
        self.discount_value = discount_rec.value

        self._compute_amounts()
        self._compute_payment_and_residual()

        self.message_post(body=_("Discount coupon '%s' applied: %s (%s).") % (
            code, discount_rec.name,
            f"{discount_rec.value}%" if discount_rec.discount_type == 'percentage' else f"{discount_rec.value} {self.currency_id.symbol or ''}"
        ))
        return True

    def action_send_email(self):
        """Dispatches invoice details via email / chatter."""
        self.ensure_one()
        self.message_post(
            body=_("Invoice %s for amount %s sent to %s (%s).") % (
                self.name, self.amount_total, self.partner_id.name, self.partner_id.email or "no email"
            )
        )
        return True

    def action_print(self):
        """Triggers QWeb Invoice Report action."""
        self.ensure_one()
        return self.env.ref('subscription_management.action_report_subscription_invoice').report_action(self)


class SubscriptionInvoiceLine(models.Model):
    _name = 'subscription.invoice.line'
    _description = 'Subscription Invoice Line'
    _order = 'id'

    invoice_id = fields.Many2one(
        comodel_name='subscription.invoice',
        string="Invoice",
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=False
    )
    name = fields.Text(
        string="Description",
        required=True
    )
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
        digits='Product Unit of Measure'
    )
    unit_price = fields.Float(
        string="Unit Price",
        required=True,
        digits='Product Price'
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes"
    )
    discount_rate = fields.Float(
        string="Discount %",
        default=0.0
    )
    discount_amount = fields.Monetary(
        string="Discount Amount",
        compute="_compute_line_totals",
        store=True
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_line_totals",
        store=True
    )
    price_tax = fields.Monetary(
        string="Tax Amount",
        compute="_compute_line_totals",
        store=True
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_line_totals",
        store=True
    )
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string="Currency",
        readonly=True,
        depends=['invoice_id.currency_id']
    )

    @api.depends('quantity', 'unit_price', 'discount_rate', 'tax_ids', 'currency_id', 'invoice_id.currency_id')
    def _compute_line_totals(self):
        for line in self:
            price = line.unit_price * (1.0 - (line.discount_rate or 0.0) / 100.0)
            subtotal = line.quantity * price

            gross = line.quantity * line.unit_price
            line.discount_amount = (gross * (line.discount_rate or 0.0)) / 100.0

            if line.tax_ids:
                currency = (
                    line.currency_id
                    or line.invoice_id.currency_id
                    or line.invoice_id.company_id.currency_id
                    or self.env.company.currency_id
                )
                partner = line.invoice_id.partner_id if line.invoice_id else False
                taxes = line.tax_ids.compute_all(
                    price,
                    currency=currency,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=partner
                )
                line.price_subtotal = taxes['total_excluded']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
                line.price_total = taxes['total_included']
            else:
                line.price_subtotal = subtotal
                line.price_tax = 0.0
                line.price_total = subtotal


# ------------------------------------------------------------
# INTELLIGENT AUTOMATED RECURRING BILLING ENGINE (EXTENSION)
# ------------------------------------------------------------

class SubscriptionSubscriptionBillingExtension(models.Model):
    _inherit = 'subscription.subscription'

    @api.model
    def cron_recurring_billing(self):
        """
        Scheduled Action (Cron) Entry Point.
        Runs daily to execute the intelligent automated recurring billing engine.
        
        Guarantees:
        - Finds all active subscriptions where next_billing_date <= today.
        - Idempotent: safe to run multiple times without duplicate invoices.
        - Concurrency safe: locks records during batch processing (FOR UPDATE SKIP LOCKED).
        - Fault-tolerant: per-subscription savepoint isolation so single-record failures
          never abort the cron run.
        - Catch-up capability: processes all missed cycles up to current date.
        - Audit trail: writes detailed execution logs to subscription.billing.log.
        """
        today = fields.Date.today()
        _logger.info("==================================================")
        _logger.info("STARTING RECURRING BILLING CRON ENGINE FOR DATE: %s", today)
        _logger.info("==================================================")

        # First, run automatic expiry evaluation
        self.action_check_expiry()

        # Query candidate subscriptions: active, started, and billing date due or unassigned
        candidate_ids = self.search([
            ('state', '=', 'active'),
            ('start_date', '<=', today),
            '|',
            ('next_billing_date', '<=', today),
            ('next_billing_date', '=', False),
        ]).ids

        if not candidate_ids:
            _logger.info("No active subscriptions currently due for recurring billing.")
            return True

        _logger.info("Found %d candidate subscription(s) due for billing.", len(candidate_ids))
        
        # Concurrency safety: acquire row lock using FOR UPDATE SKIP LOCKED
        try:
            self.env.cr.execute("""
                SELECT id FROM subscription_subscription
                WHERE id IN %s
                FOR UPDATE SKIP LOCKED
            """, [tuple(candidate_ids)])
            locked_ids = [row[0] for row in self.env.cr.fetchall()]
        except Exception as lock_err:
            _logger.warning("Database row-level lock skipped or not supported by backend: %s", lock_err)
            locked_ids = candidate_ids

        for sub_id in locked_ids:
            sub = self.browse(sub_id)
            try:
                # Per-record transaction savepoint
                with self.env.cr.savepoint():
                    sub._process_recurring_billing_catchup(today)
            except Exception as exc:
                err_msg = traceback.format_exc()
                _logger.error("Failed recurring billing for subscription %s: %s", sub.name, exc)
                self.env['subscription.billing.log'].sudo().create({
                    'execution_date': fields.Datetime.now(),
                    'subscription_id': sub.id,
                    'status': 'failed',
                    'message': _("Billing generation exception: %s") % str(exc),
                    'error_traceback': err_msg,
                })

        _logger.info("RECURRING BILLING CRON ENGINE COMPLETED SUCCESSFULLY.")
        return True

    def _process_recurring_billing_catchup(self, target_date):
        """
        Processes recurring billing for a single subscription, including catch-up
        for any eligible periods up to target_date without leaving gaps.
        """
        self.ensure_one()
        today = target_date or fields.Date.today()
        log_obj = self.env['subscription.billing.log'].sudo()
        inv_obj = self.env['subscription.invoice']

        # Safeguard: Do not bill paused, closed, or draft subscriptions
        if self.state != 'active':
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'status': 'skipped',
                'message': _("Subscription %s is in state '%s'; billing skipped.") % (self.name, self.state)
            })
            return

        # Safeguard: Ensure customer is assigned
        if not self.partner_id:
            raise ValidationError(_("Subscription %s has no customer assigned.") % self.name)

        # Safeguard: Ensure plan is assigned
        if not self.plan_id:
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'status': 'failed',
                'message': _("Subscription %s has no subscription plan assigned; billing skipped.") % self.name
            })
            return

        # Safeguard: Initialize next_billing_date if empty
        if not self.next_billing_date:
            if self.last_billing_date:
                self.next_billing_date = self.plan_id.calculate_next_billing_date(self.last_billing_date)
            else:
                self.next_billing_date = self.start_date or today
            _logger.info("Subscription %s had empty next_billing_date; initialized to %s", self.name, self.next_billing_date)

        # Safeguard: If initialized billing date is in the future, skip gracefully
        if self.next_billing_date > today:
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'status': 'skipped',
                'message': _("Subscription %s next billing date (%s) is in the future; billing skipped.") % (
                    self.name, self.next_billing_date
                )
            })
            return

        # Safeguard: Check contractual expiration
        if self.expiry_date and self.next_billing_date > self.expiry_date:
            if self.plan_id.auto_close:
                self.state = 'closed'
                self.close_date = today
                self.close_reason = _("Contract reached expiry date (%s). Auto-closed.") % self.expiry_date
            else:
                self.state = 'expired'
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'status': 'skipped',
                'message': _("Subscription %s reached expiry date (%s). Contract marked expired/closed.") % (self.name, self.expiry_date)
            })
            return

        # Safeguard: Check plan availability window
        if not self.plan_id.is_available_on(self.next_billing_date):
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'status': 'failed',
                'message': _("Plan '%s' is not active or outside validity window for date %s.") % (self.plan_id.name, self.next_billing_date)
            })
            return

        # Process billing cycle(s)
        # We loop until next_billing_date > today to catch up any missed cycles safely
        iteration_count = 0
        max_catchup_iterations = 365  # Circuit breaker preventing infinite loop

        while self.next_billing_date and self.next_billing_date <= today and self.state == 'active':
            iteration_count += 1
            if iteration_count > max_catchup_iterations:
                _logger.warning("Max catchup iterations reached for subscription %s", self.name)
                log_obj.create({
                    'execution_date': fields.Datetime.now(),
                    'subscription_id': self.id,
                    'status': 'failed',
                    'message': _("Max catchup iterations (%s) reached for subscription %s. Terminating catch-up loop safely.") % (
                        max_catchup_iterations, self.name
                    )
                })
                break

            period_start = self.next_billing_date
            period_end = self.plan_id.calculate_next_billing_date(period_start) - relativedelta(days=1)
            if self.expiry_date and period_end > self.expiry_date:
                period_end = self.expiry_date

            # Do not invoice past contractual expiry
            if self.expiry_date and period_start > self.expiry_date:
                self.state = 'expired'
                break

            # Idempotency Check: Verify if invoice already exists for this exact period
            existing_invoice = inv_obj.search([
                ('subscription_id', '=', self.id),
                ('billing_period_start', '=', period_start),
                ('billing_period_end', '=', period_end),
            ], limit=1)

            if existing_invoice:
                _logger.info("Invoice already exists (%s) for period %s - %s. Advancing billing date.",
                             existing_invoice.name, period_start, period_end)
                log_obj.create({
                    'execution_date': fields.Datetime.now(),
                    'subscription_id': self.id,
                    'invoice_id': existing_invoice.id,
                    'status': 'skipped',
                    'billing_period_start': period_start,
                    'billing_period_end': period_end,
                    'amount': existing_invoice.amount_total,
                    'message': _("Invoice %s already present for cycle %s to %s. Duplicate prevented.") % (
                        existing_invoice.name, period_start, period_end
                    )
                })
                # Advance billing date to prevent stuck loop
                self.last_billing_date = period_start
                self.next_billing_date = self.plan_id.calculate_next_billing_date(period_start)
                continue

            # Build invoice and line items
            invoice_lines = []
            
            # If plan has a base fee, add base plan line
            if self.plan_id.price > 0.0:
                base_prod = self.line_ids[0].product_id if self.line_ids else (
                    self.env['product.product'].search([('is_subscription', '=', True)], limit=1)
                    or self.env['product.product'].search([], limit=1)
                )
                invoice_lines.append((0, 0, {
                    'product_id': base_prod.id if base_prod else False,
                    'name': _("Subscription Plan Fee: %s (%s to %s)") % (self.plan_id.name, period_start, period_end),
                    'quantity': 1.0,
                    'unit_price': self.plan_id.price,
                    'discount_rate': self.discount_rate,
                }))

            # Add product lines with variant pricing & taxes
            for sub_line in self.line_ids:
                invoice_lines.append((0, 0, {
                    'product_id': sub_line.product_id.id,
                    'name': _("%s (Period: %s to %s)") % (sub_line.name, period_start, period_end),
                    'quantity': sub_line.quantity,
                    'unit_price': sub_line.unit_price,
                    'discount_rate': sub_line.discount_rate or self.discount_rate,
                    'tax_ids': [(6, 0, sub_line.tax_ids.ids)],
                }))

            # Calculate due date based on payment terms or default +15 days
            due_date = period_start + relativedelta(days=15)

            # Create Invoice record
            invoice = inv_obj.create({
                'subscription_id': self.id,
                'partner_id': self.partner_id.id,
                'invoice_date': today,
                'due_date': due_date,
                'billing_period_start': period_start,
                'billing_period_end': period_end,
                'payment_terms': self.payment_terms,
                'currency_id': (self.currency_id or self.company_id.currency_id or self.env.company.currency_id).id,
                'company_id': (self.company_id or self.env.company).id,
                'state': 'confirmed',  # Auto-confirm generated recurring invoices
                'line_ids': invoice_lines,
            })

            # Update subscription milestones
            self.last_billing_date = period_start
            self.next_billing_date = self.plan_id.calculate_next_billing_date(period_start)

            # Write Success Audit Log
            log_currency = invoice.currency_id or self.currency_id or self.env.company.currency_id
            log_obj.create({
                'execution_date': fields.Datetime.now(),
                'subscription_id': self.id,
                'invoice_id': invoice.id,
                'status': 'success',
                'billing_period_start': period_start,
                'billing_period_end': period_end,
                'amount': invoice.amount_total,
                'message': _("Successfully generated invoice %s for period %s to %s. Total: %s %s") % (
                    invoice.name, period_start, period_end, invoice.amount_total, log_currency.symbol or ''
                )
            })

            # Post to Subscription Chatter
            self.message_post(
                body=_("Recurring billing generated invoice <a href='#' data-oe-model='subscription.invoice' data-oe-id='%d'>%s</a> for period %s to %s. Total: %s") % (
                    invoice.id, invoice.name, period_start, period_end, invoice.amount_total
                )
            )

    def action_generate_invoice_manual(self):
        """Manual trigger for billing engine from subscription form view."""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_("Invoices can only be generated for active subscriptions. Current state is '%s'.") % self.state)
        today = fields.Date.today()
        self._process_recurring_billing_catchup(today)
        return True
