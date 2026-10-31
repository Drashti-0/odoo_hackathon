# -*- coding: utf-8 -*-
import calendar
import logging
from datetime import date, datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class SubscriptionDashboard(models.AbstractModel):
    """
    High-Performance Business Intelligence & Financial Analytics Engine
    Computes key performance indicators (KPIs) and grouped aggregations
    at the database layer using ORM read_group() for maximum performance.
    """
    _name = 'subscription.dashboard'
    _description = 'Subscription Management Financial Analytics Engine'

    @api.model
    def _check_dashboard_access(self):
        """
        Server-side security verification:
        Ensures caller belongs to Subscription Staff or Subscription Manager.
        Portal customers raising AccessError to defeat multi-tenant leaks.
        """
        user = self.env.user
        is_staff_or_admin = (
            user.has_group('subscription_management.group_subscription_user')
            or user.has_group('subscription_management.group_subscription_manager')
            or self.env.is_superuser()
        )
        if not is_staff_or_admin:
            raise AccessError(_("Security Violation: Portal customers are not permitted to view global financial metrics."))

    @api.model
    def _parse_date_range(self, date_range_type, custom_date_from=None, custom_date_to=None):
        """Parses human date range types into date boundaries (date_from, date_to)."""
        today = fields.Date.today()
        if date_range_type == 'today':
            return today, today
        elif date_range_type == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif date_range_type == 'this_month':
            start = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day)
            return start, end
        elif date_range_type == 'this_year':
            return date(today.year, 1, 1), date(today.year, 12, 31)
        elif date_range_type == 'custom':
            return custom_date_from, custom_date_to
        return None, None

    @api.model
    def get_dashboard_metrics(self, date_range='all', date_from=None, date_to=None,
                              partner_id=None, subscription_status=None,
                              invoice_status=None, payment_method=None):
        """
        Computes all dashboard KPIs using database-level aggregations (read_group).
        Returns a dictionary of raw metrics and formatted aggregates.
        """
        self._check_dashboard_access()

        parsed_from, parsed_to = self._parse_date_range(date_range, date_from, date_to)

        # ------------------------------------------------------------
        # 1. ACTIVE & TOTAL SUBSCRIPTIONS
        # ------------------------------------------------------------
        sub_domain = []
        if partner_id:
            sub_domain.append(('partner_id', '=', partner_id))
        if subscription_status and subscription_status != 'all':
            sub_domain.append(('state', '=', subscription_status))
        if parsed_from:
            sub_domain.append(('start_date', '>=', parsed_from))
        if parsed_to:
            sub_domain.append(('start_date', '<=', parsed_to))

        # Separate domain for active subscriptions specifically
        active_sub_domain = [condition for condition in sub_domain if condition[0] != 'state']
        active_sub_domain.append(('state', '=', 'active'))

        active_subs_count = self.env['subscription.subscription'].search_count(active_sub_domain)
        total_subs_count = self.env['subscription.subscription'].search_count(sub_domain)

        # MRR / ARR from active subscriptions
        active_agg = self.env['subscription.subscription'].read_group(
            active_sub_domain,
            ['mrr:sum', 'arr:sum'],
            []
        )
        mrr_total = round(active_agg[0]['mrr'] or 0.0, 2) if active_agg else 0.0
        arr_total = round(active_agg[0]['arr'] or 0.0, 2) if active_agg else 0.0

        # Subscription status distribution
        status_groups = self.env['subscription.subscription'].read_group(
            sub_domain,
            ['id:count', 'mrr:sum'],
            ['state']
        )
        sub_status_distribution = {
            g['state']: {'count': g['id_count'], 'mrr': round(g.get('mrr', 0.0) or 0.0, 2)}
            for g in status_groups
        }

        # ------------------------------------------------------------
        # 2. REVENUE RECEIVED & TOTAL PAYMENTS
        # ------------------------------------------------------------
        # Revenue is sum of confirmed/successful payments only. Draft and failed strictly excluded.
        pay_domain = [('state', '=', 'success')]
        if partner_id:
            pay_domain.append(('partner_id', '=', partner_id))
        if payment_method and payment_method != 'all':
            pay_domain.append(('payment_method', '=', payment_method))

        if parsed_from:
            dt_from = datetime.combine(parsed_from, time.min)
            pay_domain.append(('payment_date', '>=', dt_from))
        if parsed_to:
            dt_to = datetime.combine(parsed_to, time.max)
            pay_domain.append(('payment_date', '<=', dt_to))

        pay_agg = self.env['subscription.payment'].read_group(
            pay_domain,
            ['amount:sum', 'id:count'],
            []
        )
        revenue_received = round(pay_agg[0]['amount'] or 0.0, 2) if pay_agg else 0.0
        total_payments_count = pay_agg[0]['id_count'] if pay_agg else 0
        total_payments_amount = revenue_received

        # Monthly revenue breakdown
        monthly_pay_groups = self.env['subscription.payment'].read_group(
            pay_domain,
            ['amount:sum', 'id:count'],
            ['payment_date:month']
        )
        monthly_revenue = [
            {
                'month': g['payment_date:month'],
                'amount': round(g['amount'] or 0.0, 2),
                'count': g['id_count']
            }
            for g in monthly_pay_groups
        ]

        # Payment method distribution
        method_pay_groups = self.env['subscription.payment'].read_group(
            pay_domain,
            ['amount:sum', 'id:count'],
            ['payment_method']
        )
        payment_method_distribution = {
            g['payment_method']: {
                'amount': round(g['amount'] or 0.0, 2),
                'count': g['id_count']
            }
            for g in method_pay_groups
        }

        # ------------------------------------------------------------
        # 3. OUTSTANDING AMOUNT & OVERDUE INVOICES
        # ------------------------------------------------------------
        # Outstanding is sum of amount_residual on confirmed invoices (draft & cancel excluded).
        inv_domain = [('state', 'in', ('confirmed', 'paid'))]
        if partner_id:
            inv_domain.append(('partner_id', '=', partner_id))
        if invoice_status and invoice_status != 'all':
            inv_domain.append(('state', '=', invoice_status))
        if parsed_from:
            inv_domain.append(('invoice_date', '>=', parsed_from))
        if parsed_to:
            inv_domain.append(('invoice_date', '<=', parsed_to))

        # Outstanding balances (current uncollected receivables)
        outstanding_agg = self.env['subscription.invoice'].read_group(
            inv_domain + [('amount_residual', '>', 0.0)],
            ['amount_residual:sum', 'amount_total:sum', 'amount_paid:sum', 'id:count'],
            []
        )
        outstanding_amount = round(outstanding_agg[0]['amount_residual'] or 0.0, 2) if outstanding_agg else 0.0
        unpaid_invoices_count = outstanding_agg[0]['id_count'] if outstanding_agg else 0

        # Overdue invoices: due_date passed, confirmed state, amount_residual > 0
        today = fields.Date.today()
        overdue_domain = [
            ('state', '=', 'confirmed'),
            ('payment_state', '!=', 'paid'),
            ('amount_residual', '>', 0.0),
            ('due_date', '<', today)
        ]
        if partner_id:
            overdue_domain.append(('partner_id', '=', partner_id))
        if parsed_from:
            overdue_domain.append(('invoice_date', '>=', parsed_from))
        if parsed_to:
            overdue_domain.append(('invoice_date', '<=', parsed_to))

        overdue_agg = self.env['subscription.invoice'].read_group(
            overdue_domain,
            ['amount_residual:sum', 'id:count'],
            []
        )
        overdue_invoices_count = overdue_agg[0]['id_count'] if overdue_agg else 0
        overdue_amount = round(overdue_agg[0]['amount_residual'] or 0.0, 2) if overdue_agg else 0.0

        # Paid vs outstanding grouped by month
        monthly_inv_groups = self.env['subscription.invoice'].read_group(
            inv_domain,
            ['amount_total:sum', 'amount_paid:sum', 'amount_residual:sum', 'id:count'],
            ['invoice_date:month']
        )
        monthly_invoicing = [
            {
                'month': g['invoice_date:month'],
                'total': round(g['amount_total'] or 0.0, 2),
                'paid': round(g['amount_paid'] or 0.0, 2),
                'residual': round(g['amount_residual'] or 0.0, 2),
                'count': g['id_count']
            }
            for g in monthly_inv_groups
        ]

        return {
            # Key 5 Mandatory Metrics
            'active_subscriptions': active_subs_count,
            'revenue_received': revenue_received,
            'outstanding_amount': outstanding_amount,
            'overdue_invoices': overdue_invoices_count,
            'total_payments': total_payments_count,
            # Supplementary Business Metrics
            'total_payments_amount': total_payments_amount,
            'overdue_amount': overdue_amount,
            'unpaid_invoices_count': unpaid_invoices_count,
            'total_subscriptions': total_subs_count,
            'mrr_total': mrr_total,
            'arr_total': arr_total,
            # Visual Breakdown Datasets
            'monthly_revenue': monthly_revenue,
            'monthly_invoicing': monthly_invoicing,
            'payment_method_distribution': payment_method_distribution,
            'subscription_status_distribution': sub_status_distribution,
            # Filter Echo
            'applied_date_from': parsed_from,
            'applied_date_to': parsed_to,
        }


# ============================================================================
# INTERACTIVE DASHBOARD CONSOLE (TRANSIENT MODEL)
# ============================================================================

class SubscriptionDashboardConsole(models.TransientModel):
    """
    Interactive Dashboard Console for Staff and Administrators.
    Provides live metric cards, date-range filters, customer filters,
    and drill-down actions to underlying records.
    """
    _name = 'subscription.dashboard.console'
    _description = 'Interactive Subscription Financial Dashboard Console'

    # Filter Controls
    date_range_type = fields.Selection(
        selection=[
            ('all', 'All Time'),
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        string="Date Period",
        default='all',
        required=True
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Filter by Customer",
        help="Limit dashboard calculations to a specific subscriber."
    )
    subscription_status = fields.Selection(
        selection=[
            ('all', 'All Subscriptions'),
            ('draft', 'Draft'),
            ('quotation', 'Quotation'),
            ('confirmed', 'Confirmed'),
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('closed', 'Closed'),
            ('expired', 'Expired'),
        ],
        string="Subscription Status",
        default='all'
    )
    invoice_status = fields.Selection(
        selection=[
            ('all', 'All Invoices'),
            ('draft', 'Draft'),
            ('confirmed', 'Posted / Confirmed'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ],
        string="Invoice Status",
        default='all'
    )
    payment_method = fields.Selection(
        selection=[
            ('all', 'All Payment Methods'),
            ('cash', 'Cash / Cheque'),
            ('bank_transfer', 'Bank Wire Transfer'),
            ('upi', 'UPI / Instant Transfer'),
            ('card', 'Credit / Debit Card'),
            ('stripe', 'Stripe Gateway'),
            ('paypal', 'PayPal Gateway'),
            ('other', 'Other Manual Method'),
        ],
        string="Payment Method",
        default='all'
    )

    # Computed Live Metrics (5 Key Metrics + Supporting Financials)
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id
    )
    active_subscriptions = fields.Integer(
        string="Active Subscriptions",
        compute="_compute_dashboard_metrics",
        help="Number of currently active subscription contracts."
    )
    revenue_received = fields.Monetary(
        string="Revenue Received",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id',
        help="Total amount received and confirmed from settled payments."
    )
    outstanding_amount = fields.Monetary(
        string="Outstanding Receivables",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id',
        help="Total unpaid balance remaining on confirmed invoices."
    )
    overdue_invoices = fields.Integer(
        string="Overdue Invoices",
        compute="_compute_dashboard_metrics",
        help="Number of invoices past due date with remaining balance."
    )
    overdue_amount = fields.Monetary(
        string="Overdue Amount",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id',
        help="Total unpaid balance past due date."
    )
    total_payments_count = fields.Integer(
        string="Total Payments (#)",
        compute="_compute_dashboard_metrics",
        help="Total number of confirmed payments."
    )
    total_payments_amount = fields.Monetary(
        string="Total Payments Amount",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id',
        help="Gross amount of settled payments."
    )
    mrr_total = fields.Monetary(
        string="Monthly Recurring Revenue (MRR)",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id'
    )
    arr_total = fields.Monetary(
        string="Annual Recurring Revenue (ARR)",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id'
    )

    @api.onchange('date_range_type')
    def _onchange_date_range_type(self):
        engine = self.env['subscription.dashboard']
        d_from, d_to = engine._parse_date_range(self.date_range_type, self.date_from, self.date_to)
        if self.date_range_type != 'custom':
            self.date_from = d_from
            self.date_to = d_to

    @api.depends('date_range_type', 'date_from', 'date_to', 'partner_id',
                 'subscription_status', 'invoice_status', 'payment_method')
    def _compute_dashboard_metrics(self):
        engine = self.env['subscription.dashboard']
        for rec in self:
            metrics = engine.get_dashboard_metrics(
                date_range=rec.date_range_type,
                date_from=rec.date_from,
                date_to=rec.date_to,
                partner_id=rec.partner_id.id if rec.partner_id else None,
                subscription_status=rec.subscription_status,
                invoice_status=rec.invoice_status,
                payment_method=rec.payment_method
            )
            rec.active_subscriptions = metrics['active_subscriptions']
            rec.revenue_received = metrics['revenue_received']
            rec.outstanding_amount = metrics['outstanding_amount']
            rec.overdue_invoices = metrics['overdue_invoices']
            rec.overdue_amount = metrics['overdue_amount']
            rec.total_payments_count = metrics['total_payments']
            rec.total_payments_amount = metrics['total_payments_amount']
            rec.mrr_total = metrics['mrr_total']
            rec.arr_total = metrics['arr_total']

    # ------------------------------------------------------------
    # DRILL-DOWN ACTION METHODS
    # ------------------------------------------------------------

    def action_view_active_subscriptions(self):
        """Drills down to active subscriptions matching filter."""
        self.ensure_one()
        domain = [('state', '=', 'active')]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return {
            'name': _("Active Subscriptions"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'context': {'default_state': 'active'}
        }

    def action_view_received_payments(self):
        """Drills down to settled payments matching filter."""
        self.ensure_one()
        domain = [('state', '=', 'success')]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.payment_method and self.payment_method != 'all':
            domain.append(('payment_method', '=', self.payment_method))
        if self.date_from:
            domain.append(('payment_date', '>=', datetime.combine(self.date_from, time.min)))
        if self.date_to:
            domain.append(('payment_date', '<=', datetime.combine(self.date_to, time.max)))
        return {
            'name': _("Settled Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.payment',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'context': {'search_default_filter_success': 1}
        }

    def action_view_outstanding_invoices(self):
        """Drills down to unpaid invoices with outstanding residual."""
        self.ensure_one()
        domain = [('state', 'in', ('confirmed', 'paid')), ('amount_residual', '>', 0.0)]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return {
            'name': _("Outstanding Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.invoice',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'context': {'search_default_filter_unpaid': 1}
        }

    def action_view_overdue_invoices(self):
        """Drills down to invoices currently past due date."""
        self.ensure_one()
        today = fields.Date.today()
        domain = [
            ('state', '=', 'confirmed'),
            ('payment_state', '!=', 'paid'),
            ('amount_residual', '>', 0.0),
            ('due_date', '<', today)
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return {
            'name': _("Overdue Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.invoice',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'context': {'search_default_filter_unpaid': 1}
        }
