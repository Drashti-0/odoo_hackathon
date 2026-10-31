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
    def _normalized_timezone(self):
        timezone = self.env.context.get('tz')
        return 'Asia/Kolkata' if timezone == 'Asia/Calcutta' else timezone

    @api.model
    def get_dashboard_metrics(self, date_range='all', date_from=None, date_to=None,
                              partner_id=None, subscription_status=None,
                              invoice_status=None, payment_method=None,
                              billing_frequency=None):
        """
        Computes all dashboard KPIs using database-level aggregations (read_group).
        Returns a dictionary of raw metrics and formatted aggregates.
        """
        self._check_dashboard_access()
        timezone = self._normalized_timezone()
        if timezone and timezone != self.env.context.get('tz'):
            self = self.with_context(tz=timezone)

        parsed_from, parsed_to = self._parse_date_range(date_range, date_from, date_to)
        if parsed_from and parsed_to and parsed_to < parsed_from:
            raise ValidationError(_("The end date cannot be earlier than the start date."))

        # ------------------------------------------------------------
        # 1. SUBSCRIPTION, CUSTOMER, PRODUCT & PLAN COUNTS
        # ------------------------------------------------------------
        sub_domain = []
        if partner_id:
            sub_domain.append(('partner_id', '=', partner_id))
        if subscription_status and subscription_status != 'all':
            sub_domain.append(('state', '=', subscription_status))
        if billing_frequency and billing_frequency != 'all':
            sub_domain.append(('plan_id.billing_interval_unit', '=', billing_frequency))
        if parsed_from:
            sub_domain.append(('create_date', '>=', datetime.combine(parsed_from, time.min)))
        if parsed_to:
            sub_domain.append(('create_date', '<=', datetime.combine(parsed_to, time.max)))

        active_sub_domain = sub_domain + [('state', '=', 'active')]
        pending_sub_domain = sub_domain + [('state', 'in', ('draft', 'quotation', 'confirmed'))]
        closed_sub_domain = sub_domain + [('state', '=', 'closed')]
        if parsed_from:
            sub_domain.append(('start_date', '>=', parsed_from))
        if parsed_to:
            sub_domain.append(('start_date', '<=', parsed_to))

        # Separate domain for active subscriptions specifically
        active_sub_domain = [condition for condition in sub_domain if condition[0] != 'state']
        active_sub_domain.append(('state', '=', 'active'))

        active_subs_count = self.env['subscription.subscription'].search_count(active_sub_domain)
        total_subs_count = self.env['subscription.subscription'].search_count(sub_domain)
        pending_subscriptions = self.env['subscription.subscription'].search_count(pending_sub_domain)
        cancelled_subscriptions = self.env['subscription.subscription'].search_count(closed_sub_domain)
        customer_groups = self.env['subscription.subscription'].read_group(
            sub_domain, ['partner_id'], ['partner_id']
        )
        total_customers = len(customer_groups)
        total_products = self.env['product.template'].search_count([
            ('is_subscription', '=', True)
        ])
        total_plans = self.env['subscription.plan'].with_context(
            active_test=False
        ).search_count([])

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
            g['state']: {
                'count': g.get('state_count', g.get('id', 0)),
                'mrr': round(g.get('mrr', 0.0) or 0.0, 2),
            }
            for g in status_groups
        }

        # ------------------------------------------------------------
        # 2. REVENUE RECEIVED & TOTAL PAYMENTS
        # ------------------------------------------------------------
        # Revenue is sum of confirmed/successful payments only. Draft and failed strictly excluded.
        pay_domain = [('state', '=', 'success')]
        if partner_id:
            pay_domain.append(('partner_id', '=', partner_id))
        if subscription_status and subscription_status != 'all':
            pay_domain.append(('invoice_id.subscription_id.state', '=', subscription_status))
        if billing_frequency and billing_frequency != 'all':
            pay_domain.append(
                ('invoice_id.subscription_id.plan_id.billing_interval_unit', '=', billing_frequency)
            )
        if invoice_status and invoice_status != 'all':
            pay_domain.append(('invoice_id.state', '=', invoice_status))
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
        total_payments_count = (
            pay_agg[0].get('id_count', pay_agg[0].get('id', 0)) if pay_agg else 0
        )
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
                'count': g.get('payment_date_count', g.get('id', 0)),
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
                'count': g.get('payment_method_count', g.get('id', 0)),
            }
            for g in method_pay_groups
        }

        # ------------------------------------------------------------
        # 3. OUTSTANDING AMOUNT & OVERDUE INVOICES
        # ------------------------------------------------------------
        # Outstanding is sum of amount_residual on confirmed invoices (draft & cancel excluded).
        invoice_domain = []
        if partner_id:
            invoice_domain.append(('partner_id', '=', partner_id))
        if subscription_status and subscription_status != 'all':
            invoice_domain.append(('subscription_id.state', '=', subscription_status))
        if billing_frequency and billing_frequency != 'all':
            invoice_domain.append(
                ('subscription_id.plan_id.billing_interval_unit', '=', billing_frequency)
            )
        if invoice_status and invoice_status != 'all':
            invoice_domain.append(('state', '=', invoice_status))
        if parsed_from:
            invoice_domain.append(('invoice_date', '>=', parsed_from))
        if parsed_to:
            invoice_domain.append(('invoice_date', '<=', parsed_to))
            inv_domain.append(('state', '=', invoice_status))
        if parsed_from:
            inv_domain.append(('invoice_date', '>=', parsed_from))
        if parsed_to:
            inv_domain.append(('invoice_date', '<=', parsed_to))

        # Outstanding balances (current uncollected receivables)
        outstanding_agg = self.env['subscription.invoice'].read_group(
            invoice_domain + [
                ('state', 'in', ('confirmed', 'paid')),
                ('amount_residual', '>', 0.0),
            ],
            ['amount_residual:sum', 'amount_total:sum', 'amount_paid:sum', 'id:count'],
            []
        )
        outstanding_amount = round(outstanding_agg[0]['amount_residual'] or 0.0, 2) if outstanding_agg else 0.0
        unpaid_invoices_count = (
            outstanding_agg[0].get('id_count', outstanding_agg[0].get('id', 0))
            if outstanding_agg else 0
        )

        # Overdue invoices: due_date passed, confirmed state, amount_residual > 0
        today = fields.Date.today()
        overdue_domain = [
            ('state', '=', 'confirmed'),
            ('payment_state', '!=', 'paid'),
            ('amount_residual', '>', 0.0),
            ('due_date', '<', today)
        ] + invoice_domain
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
        overdue_invoices_count = (
            overdue_agg[0].get('id_count', overdue_agg[0].get('id', 0))
            if overdue_agg else 0
        )
        overdue_amount = round(overdue_agg[0]['amount_residual'] or 0.0, 2) if overdue_agg else 0.0

        # Paid vs outstanding grouped by month
        monthly_inv_groups = self.env['subscription.invoice'].read_group(
            invoice_domain + [('state', 'in', ('confirmed', 'paid'))],
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
                'count': g.get('invoice_date_count', g.get('id', 0)),
            }
            for g in monthly_inv_groups
        ]

        return {
            'total_customers': total_customers,
            'total_products': total_products,
            'total_plans': total_plans,
            'pending_subscriptions': pending_subscriptions,
            'cancelled_subscriptions': cancelled_subscriptions,
            'total_invoices': self.env['subscription.invoice'].search_count(invoice_domain),
            'total_revenue': revenue_received,
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
    billing_frequency = fields.Selection(
        selection=[
            ('all', 'All Billing Frequencies'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        string="Billing Frequency",
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

    # Computed Live Metrics
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
    total_customers = fields.Integer(
        string="Total Customers",
        compute="_compute_dashboard_metrics",
        help="Distinct customers with subscriptions matching the current filters."
    )
    total_products = fields.Integer(
        string="Total Subscription Products",
        compute="_compute_dashboard_metrics"
    )
    total_plans = fields.Integer(
        string="Total Subscription Plans",
        compute="_compute_dashboard_metrics"
    )
    pending_subscriptions = fields.Integer(
        string="Pending Subscriptions",
        compute="_compute_dashboard_metrics"
    )
    cancelled_subscriptions = fields.Integer(
        string="Closed / Cancelled Subscriptions",
        compute="_compute_dashboard_metrics"
    )
    total_invoices = fields.Integer(
        string="Total Invoices",
        compute="_compute_dashboard_metrics"
    )
    total_revenue = fields.Monetary(
        string="Total Revenue",
        compute="_compute_dashboard_metrics",
        currency_field='currency_id',
        help="Revenue received from successful payment transactions."
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
    recent_subscription_ids = fields.Many2many(
        comodel_name='subscription.subscription',
        compute="_compute_dashboard_activity",
        string="Recently Created Subscriptions"
    )
    recently_confirmed_ids = fields.Many2many(
        comodel_name='subscription.subscription',
        compute="_compute_dashboard_activity",
        string="Recently Confirmed Quotations"
    )
    latest_invoice_ids = fields.Many2many(
        comodel_name='subscription.invoice',
        compute="_compute_dashboard_activity",
        string="Latest Invoices"
    )
    upcoming_billing_ids = fields.Many2many(
        comodel_name='subscription.subscription',
        compute="_compute_dashboard_activity",
        string="Upcoming Billing Dates"
    )

    @api.onchange('date_range_type', 'date_from', 'date_to', 'partner_id',
                  'subscription_status', 'billing_frequency', 'invoice_status',
                  'payment_method')
    def _onchange_filter_criteria(self):
        engine = self.env['subscription.dashboard']
        d_from, d_to = engine._parse_date_range(self.date_range_type, self.date_from, self.date_to)
        if self.date_range_type != 'custom':
            self.date_from = d_from
            self.date_to = d_to
        try:
            metrics = engine.get_dashboard_metrics(
                date_range=self.date_range_type,
                date_from=self.date_from,
                date_to=self.date_to,
                partner_id=self.partner_id.id if self.partner_id else None,
                subscription_status=self.subscription_status,
                invoice_status=self.invoice_status,
                payment_method=self.payment_method,
                billing_frequency=self.billing_frequency,
            )
            self.total_customers = metrics['total_customers']
            self.total_products = metrics['total_products']
            self.total_plans = metrics['total_plans']
            self.pending_subscriptions = metrics['pending_subscriptions']
            self.cancelled_subscriptions = metrics['cancelled_subscriptions']
            self.total_invoices = metrics['total_invoices']
            self.total_revenue = metrics['total_revenue']
            self.active_subscriptions = metrics['active_subscriptions']
            self.revenue_received = metrics['revenue_received']
            self.outstanding_amount = metrics['outstanding_amount']
            self.overdue_invoices = metrics['overdue_invoices']
            self.overdue_amount = metrics['overdue_amount']
            self.total_payments_count = metrics['total_payments']
            self.total_payments_amount = metrics['total_payments_amount']
            self.mrr_total = metrics['mrr_total']
            self.arr_total = metrics['arr_total']
        except Exception as e:
            _logger.warning("Could not recompute onchange filter criteria: %s", e)

    @api.depends('date_range_type', 'date_from', 'date_to', 'partner_id',
                 'subscription_status', 'billing_frequency', 'invoice_status',
                 'payment_method')
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
                payment_method=rec.payment_method,
                billing_frequency=rec.billing_frequency,
            )
            rec.total_customers = metrics['total_customers']
            rec.total_products = metrics['total_products']
            rec.total_plans = metrics['total_plans']
            rec.pending_subscriptions = metrics['pending_subscriptions']
            rec.cancelled_subscriptions = metrics['cancelled_subscriptions']
            rec.total_invoices = metrics['total_invoices']
            rec.total_revenue = metrics['total_revenue']
            rec.active_subscriptions = metrics['active_subscriptions']
            rec.revenue_received = metrics['revenue_received']
            rec.outstanding_amount = metrics['outstanding_amount']
            rec.overdue_invoices = metrics['overdue_invoices']
            rec.overdue_amount = metrics['overdue_amount']
            rec.total_payments_count = metrics['total_payments']
            rec.total_payments_amount = metrics['total_payments_amount']
            rec.mrr_total = metrics['mrr_total']
            rec.arr_total = metrics['arr_total']

    def _get_dashboard_domains(self):
        self.ensure_one()
        engine = self.env['subscription.dashboard']
        date_from, date_to = engine._parse_date_range(
            self.date_range_type, self.date_from, self.date_to
        )
        if date_from and date_to and date_to < date_from:
            raise ValidationError(_("The end date cannot be earlier than the start date."))

        subscription_domain = []
        invoice_domain = []
        if self.partner_id:
            subscription_domain.append(('partner_id', '=', self.partner_id.id))
            invoice_domain.append(('partner_id', '=', self.partner_id.id))
        if self.subscription_status and self.subscription_status != 'all':
            subscription_domain.append(('state', '=', self.subscription_status))
            invoice_domain.append(
                ('subscription_id.state', '=', self.subscription_status)
            )
        if self.billing_frequency and self.billing_frequency != 'all':
            subscription_domain.append(
                ('plan_id.billing_interval_unit', '=', self.billing_frequency)
            )
            invoice_domain.append(
                ('subscription_id.plan_id.billing_interval_unit', '=', self.billing_frequency)
            )
        if self.invoice_status and self.invoice_status != 'all':
            invoice_domain.append(('state', '=', self.invoice_status))
        if date_from:
            subscription_domain.append(
                ('create_date', '>=', datetime.combine(date_from, time.min))
            )
            invoice_domain.append(('invoice_date', '>=', date_from))
        if date_to:
            subscription_domain.append(
                ('create_date', '<=', datetime.combine(date_to, time.max))
            )
            invoice_domain.append(('invoice_date', '<=', date_to))
        return subscription_domain, invoice_domain, date_from, date_to

    @api.depends('date_range_type', 'date_from', 'date_to', 'partner_id',
                 'subscription_status', 'billing_frequency', 'invoice_status')
    def _compute_dashboard_activity(self):
        today = fields.Date.today()
        for rec in self:
            engine = rec.env['subscription.dashboard']
            engine._check_dashboard_access()
            subscription_domain, invoice_domain, date_from, date_to = (
                rec._get_dashboard_domains()
            )
            rec.recent_subscription_ids = rec.env['subscription.subscription'].search(
                subscription_domain, order='create_date desc, id desc', limit=5
            )
            rec.recently_confirmed_ids = rec.env['subscription.subscription'].search(
                subscription_domain + [('state', '=', 'confirmed')],
                order='write_date desc, id desc',
                limit=5,
            )
            rec.latest_invoice_ids = rec.env['subscription.invoice'].search(
                invoice_domain, order='invoice_date desc, id desc', limit=5
            )
            upcoming_domain = subscription_domain + [
                ('state', '=', 'active'),
                ('next_billing_date', '>=', today),
                ('next_billing_date', '<=', today + timedelta(days=30)),
            ]
            rec.upcoming_billing_ids = rec.env['subscription.subscription'].search(
                upcoming_domain, order='next_billing_date, id', limit=5
            )

    @api.model
    def default_get(self, fields_list):
        res = super(SubscriptionDashboardConsole, self).default_get(fields_list)
        res.setdefault('date_range_type', 'all')
        res.setdefault('subscription_status', 'all')
        res.setdefault('billing_frequency', 'all')
        res.setdefault('invoice_status', 'all')
        res.setdefault('payment_method', 'all')
        try:
            metrics = self.env['subscription.dashboard'].get_dashboard_metrics(
                date_range='all',
                subscription_status='all',
                invoice_status='all',
                billing_frequency='all',
            )
            res.update({
                'total_customers': metrics['total_customers'],
                'total_products': metrics['total_products'],
                'total_plans': metrics['total_plans'],
                'pending_subscriptions': metrics['pending_subscriptions'],
                'cancelled_subscriptions': metrics['cancelled_subscriptions'],
                'total_invoices': metrics['total_invoices'],
                'total_revenue': metrics['total_revenue'],
                'active_subscriptions': metrics['active_subscriptions'],
                'revenue_received': metrics['revenue_received'],
                'outstanding_amount': metrics['outstanding_amount'],
                'overdue_invoices': metrics['overdue_invoices'],
                'overdue_amount': metrics['overdue_amount'],
                'total_payments_count': metrics['total_payments'],
                'total_payments_amount': metrics['total_payments_amount'],
                'mrr_total': metrics['mrr_total'],
                'arr_total': metrics['arr_total'],
            })
            today = fields.Date.today()
            recent_subs = self.env['subscription.subscription'].search([], order='create_date desc, id desc', limit=5)
            recent_conf = self.env['subscription.subscription'].search([('state', '=', 'confirmed')], order='write_date desc, id desc', limit=5)
            latest_invs = self.env['subscription.invoice'].search([], order='invoice_date desc, id desc', limit=5)
            upcoming_bills = self.env['subscription.subscription'].search([('state', '=', 'active'), ('next_billing_date', '>=', today)], order='next_billing_date, id', limit=5)
            res['recent_subscription_ids'] = [(6, 0, recent_subs.ids)]
            res['recently_confirmed_ids'] = [(6, 0, recent_conf.ids)]
            res['latest_invoice_ids'] = [(6, 0, latest_invs.ids)]
            res['upcoming_billing_ids'] = [(6, 0, upcoming_bills.ids)]
        except Exception as e:
            _logger.warning("Could not precompute dashboard metrics in default_get: %s", e)
        return res

    @api.model
    def action_open_dashboard(self):
        """Open or initialize the interactive dashboard console."""
        self.env['subscription.dashboard']._check_dashboard_access()
        record = self.search([('create_uid', '=', self.env.uid)], order='id desc', limit=1)
        if not record:
            record = self.create({
                'date_range_type': 'all',
                'subscription_status': 'all',
                'billing_frequency': 'all',
                'invoice_status': 'all',
                'payment_method': 'all',
            })
        return {
            'name': _("Subscription Financial & Operational Dashboard"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.dashboard.console',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------
    # DRILL-DOWN ACTION METHODS
    # ------------------------------------------------------------

    def action_view_active_subscriptions(self):
        """Drills down to active subscriptions matching filter."""
        self.ensure_one()
        subscription_domain, _invoice_domain, _date_from, _date_to = (
            self._get_dashboard_domains()
        )
        domain = [term for term in subscription_domain if term[0] != 'state']
        domain.append(('state', '=', 'active'))
        return {
            'name': _("Active Subscriptions"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'context': {'default_state': 'active'}
        }

    def action_create_product(self):
        self.ensure_one()
        return {
            'name': _("Create Subscription Product"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_is_subscription': True,
                'default_type': 'service',
            },
        }

    def action_create_plan(self):
        self.ensure_one()
        return {
            'name': _("Create Subscription Plan"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.plan',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_billing_interval_unit': 'monthly'},
        }

    def action_create_quotation(self):
        self.ensure_one()
        return {
            'name': _("Create Subscription Quotation"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_state': 'draft'},
        }

    def action_view_invoices(self):
        self.ensure_one()
        _subscription_domain, invoice_domain, _date_from, _date_to = (
            self._get_dashboard_domains()
        )
        return {
            'name': _("Subscription Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.invoice',
            'view_mode': 'tree,form,graph,pivot',
            'domain': invoice_domain,
        }

    def action_open_dashboard_chart(self):
        self.ensure_one()
        self.env['subscription.dashboard']._check_dashboard_access()
        chart_actions = {
            'status': (
                'subscription_management.action_subscription_status_chart',
                'subscription.subscription',
            ),
            'growth': (
                'subscription_management.action_subscription_growth_chart',
                'subscription.subscription',
            ),
            'invoices': (
                'subscription_management.action_subscription_invoice_generation_chart',
                'subscription.invoice',
            ),
            'revenue': (
                'subscription_management.action_subscription_revenue_trend_chart',
                'subscription.payment',
            ),
            'plans': (
                'subscription_management.action_subscription_plan_popularity_chart',
                'subscription.subscription',
            ),
        }
        chart_name = self.env.context.get('dashboard_chart')
        if chart_name not in chart_actions:
            raise UserError(_("Select a valid dashboard chart."))

        action_xmlid, model_name = chart_actions[chart_name]
        action = self.env.ref(action_xmlid).sudo().read()[0]
        subscription_domain, invoice_domain, date_from, date_to = (
            self._get_dashboard_domains()
        )
        if model_name == 'subscription.subscription':
            action_domain = subscription_domain
            if chart_name == 'status':
                action_domain = action_domain + [
                    ('state', 'in', ('active', 'closed'))
                ]
        elif model_name == 'subscription.invoice':
            action_domain = invoice_domain + [('state', '!=', 'cancel')]
        else:
            action_domain = [('state', '=', 'success')]
            if self.partner_id:
                action_domain.append(('partner_id', '=', self.partner_id.id))
            if self.subscription_status and self.subscription_status != 'all':
                action_domain.append(
                    ('invoice_id.subscription_id.state', '=', self.subscription_status)
                )
            if self.billing_frequency and self.billing_frequency != 'all':
                action_domain.append(
                    (
                        'invoice_id.subscription_id.plan_id.billing_interval_unit',
                        '=',
                        self.billing_frequency,
                    )
                )
            if self.invoice_status and self.invoice_status != 'all':
                action_domain.append(('invoice_id.state', '=', self.invoice_status))
            if self.payment_method and self.payment_method != 'all':
                action_domain.append(('payment_method', '=', self.payment_method))
            if date_from:
                action_domain.append(
                    ('payment_date', '>=', datetime.combine(date_from, time.min))
                )
            if date_to:
                action_domain.append(
                    ('payment_date', '<=', datetime.combine(date_to, time.max))
                )

        action['domain'] = action_domain
        action_context = (
            {'search_default_filter_success': 1}
            if chart_name == 'revenue' else {}
        )
        timezone = self.env['subscription.dashboard']._normalized_timezone()
        if timezone and timezone != self.env.context.get('tz'):
            action_context['tz'] = timezone
        action['context'] = action_context
        return action

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
