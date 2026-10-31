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
        help="Maintained by Developer 2 Payment Gateway Module."
    )
    payment_reference = fields.Char(
        string="Payment Reference / Transaction ID",
        tracking=True,
        help="External transaction reference populated upon settlement."
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

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.discount_amount')
    def _compute_amounts(self):
        for inv in self:
            untaxed = sum(inv.line_ids.mapped('price_subtotal'))
            tax = sum(inv.line_ids.mapped('price_tax'))
            discount = sum(inv.line_ids.mapped('discount_amount'))
            
            inv.amount_untaxed = untaxed
            inv.amount_tax = tax
            inv.amount_discount = discount
            inv.amount_total = max(0.0, untaxed + tax)

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
            inv.message_post(body=_("Invoice %s confirmed and posted for billing period %s to %s.") % (
                inv.name, inv.billing_period_start, inv.billing_period_end
            ))

    def action_cancel(self):
        """Transitions: Draft / Confirmed -> Cancelled"""
        for inv in self:
            if inv.state == 'paid':
                raise UserError(_("Cannot cancel a paid invoice. Please process a refund or credit note."))
            inv.state = 'cancel'
            inv.payment_state = 'not_paid'
            inv.message_post(body=_("Invoice %s was cancelled.") % inv.name)

    def action_register_payment(self, amount=None, ref=None):
        """
        Public Developer 2 Hook for Payment Settlement.
        Marks invoice as paid and triggers notification.
        """
        for inv in self:
            if inv.state != 'confirmed':
                raise UserError(_("Invoices must be confirmed before registering payment."))
            inv.state = 'paid'
            inv.payment_state = 'paid'
            if ref:
                inv.payment_reference = ref
            inv.message_post(body=_("Payment received and reconciled. Reference: %s, Amount: %s") % (
                ref or "Direct Settlement", amount or inv.amount_total
            ))

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
        required=True
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
            gross = line.quantity * line.unit_price
            disc = (gross * (line.discount_rate or 0.0)) / 100.0
            net = gross - disc
            
            line.discount_amount = disc
            line.price_subtotal = net

            if line.tax_ids:
                currency = (
                    line.currency_id
                    or line.invoice_id.currency_id
                    or line.invoice_id.company_id.currency_id
                    or self.env.company.currency_id
                )
                partner = line.invoice_id.partner_id if line.invoice_id else False
                unit_tax_base = net / (line.quantity or 1.0) if line.quantity else 0.0
                taxes = line.tax_ids.compute_all(
                    unit_tax_base,
                    currency=currency,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=partner
                )
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
                line.price_total = taxes['total_included']
            else:
                line.price_tax = 0.0
                line.price_total = net


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

            # Do not invoice past contractual expiry
            if self.expiry_date and period_start > self.expiry_date:
                self.state = 'expired'
                break

            # Idempotency Check: Verify if invoice already exists for this exact period
            existing_invoice = inv_obj.search([
                ('subscription_id', '=', self.id),
                ('billing_period_start', '=', period_start),
                ('billing_period_end', '=', period_end),
                ('state', '!=', 'cancel')
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
                invoice_lines.append((0, 0, {
                    'product_id': self.line_ids[0].product_id.id if self.line_ids else False,
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
        today = fields.Date.today()
        self._process_recurring_billing_catchup(today)
        return True
