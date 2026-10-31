# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SubscriptionQuotationTemplate(models.Model):
    _name = 'subscription.quotation.template'
    _description = 'Subscription Quotation Template'
    _order = 'name'

    name = fields.Char(
        string="Template Name",
        required=True,
        help="Template name e.g. 'Standard SaaS Starter Pack', 'Enterprise Cloud Tier'."
    )
    plan_id = fields.Many2one(
        comodel_name='subscription.plan',
        string="Default Subscription Plan",
        required=True
    )
    validity_days = fields.Integer(
        string="Quotation Validity (Days)",
        default=30,
        help="Number of days quotation remains valid from issue date."
    )
    line_ids = fields.One2many(
        comodel_name='subscription.quotation.template.line',
        inverse_name='template_id',
        string="Predefined Products"
    )
    terms_and_conditions = fields.Html(
        string="Default Terms & Conditions"
    )

    @api.constrains('validity_days')
    def _check_validity_days(self):
        for tmpl in self:
            if tmpl.validity_days < 0:
                raise ValidationError(_("Quotation validity days cannot be negative."))


class SubscriptionQuotationTemplateLine(models.Model):
    _name = 'subscription.quotation.template.line'
    _description = 'Subscription Quotation Template Line'

    template_id = fields.Many2one(
        comodel_name='subscription.quotation.template',
        string="Quotation Template",
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True
    )
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True
    )
    unit_price = fields.Float(
        string="Unit Price",
        digits='Product Price'
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Template line quantity must be strictly greater than 0."))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            plan = self.template_id.plan_id if self.template_id else False
            self.unit_price = self.product_id.get_subscription_price(plan=plan)


class SubscriptionSubscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription & Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string="Subscription Number",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
        index=True,
        tracking=True,
        help="Customer account subscribed to this contract."
    )
    plan_id = fields.Many2one(
        comodel_name='subscription.plan',
        string="Subscription Plan",
        required=True,
        tracking=True,
        help="Governing billing frequency, renewal, pause and closure policies."
    )
    template_id = fields.Many2one(
        comodel_name='subscription.quotation.template',
        string="Quotation Template",
        tracking=True,
        help="Predefined template applied to build this quotation."
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('quotation', 'Quotation Sent'),
            ('confirmed', 'Confirmed'),
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('closed', 'Closed'),
            ('expired', 'Expired'),
        ],
        string="Status",
        default='draft',
        required=True,
        tracking=True,
        index=True,
        help="Strict lifecycle stage: Draft -> Quotation -> Confirmed -> Active -> Closed/Expired."
    )
    start_date = fields.Date(
        string="Start Date",
        default=fields.Date.today,
        tracking=True,
        help="Subscription commencement date."
    )
    expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True,
        help="End of contractual period."
    )
    quotation_validity_date = fields.Date(
        string="Quotation Valid Until",
        tracking=True,
        help="Date until which the proposed pricing and terms are guaranteed."
    )
    payment_terms = fields.Char(
        string="Payment Terms",
        default="Immediate Payment",
        help="Terms of payment for generated invoices."
    )
    terms_and_conditions = fields.Html(
        string="Terms & Conditions",
        help="Terms and contractual clauses applicable to this subscription quotation."
    )
    next_billing_date = fields.Date(
        string="Next Billing Date",
        index=True,
        tracking=True,
        help="Calculated date when the automated recurring billing engine will next generate an invoice."
    )
    last_billing_date = fields.Date(
        string="Last Billing Date",
        readonly=True,
        help="Date when the most recent recurring billing invoice was produced."
    )
    pause_date = fields.Date(
        string="Pause Date",
        readonly=True,
        help="Timestamp of when the subscription was set to paused."
    )
    close_date = fields.Date(
        string="Closed Date",
        readonly=True,
        help="Date when subscription was terminated or expired."
    )
    close_reason = fields.Text(
        string="Close Reason / Note",
        help="Explanation provided for early closure or cancellation."
    )

    line_ids = fields.One2many(
        comodel_name='subscription.line',
        inverse_name='subscription_id',
        string="Subscription Lines",
        copy=True
    )
    invoice_ids = fields.One2many(
        comodel_name='subscription.invoice',
        inverse_name='subscription_id',
        string="Generated Invoices",
        readonly=True
    )
    invoice_count = fields.Integer(
        string="Invoices Count",
        compute="_compute_invoice_count"
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

    @api.depends('company_id')
    def _compute_currency_id(self):
        for sub in self:
            if not sub.currency_id:
                sub.currency_id = sub.company_id.currency_id or self.env.company.currency_id
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Salesperson / Rep",
        default=lambda self: self.env.user,
        tracking=True
    )

    # Financial Totals & Integration Fields
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
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
        string="Discount Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True,
        help="Deduction calculated through Developer 2 Discount Management hook."
    )
    amount_total = fields.Monetary(
        string="Total Recurring Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True
    )

    # Developer 2 Interface Fields
    discount_code = fields.Char(
        string="Promo / Coupon Code",
        tracking=True,
        help="Discount coupon entered by customer or sales rep (Developer 2 interface)."
    )
    discount_rate = fields.Float(
        string="Overall Discount %",
        default=0.0,
        help="Discount percentage applied to untaxed amount."
    )

    # Developer 2 Analytics Metrics (Stored for fast reporting)
    mrr = fields.Monetary(
        string="MRR (Monthly Recurring Revenue)",
        compute="_compute_mrr_arr",
        store=True,
        help="Normalized monthly recurring revenue for financial analytics."
    )
    arr = fields.Monetary(
        string="ARR (Annual Recurring Revenue)",
        compute="_compute_mrr_arr",
        store=True,
        help="Normalized annual recurring revenue (MRR * 12)."
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Subscription Reference must be unique!'),
    ]

    # ------------------------------------------------------------
    # ONCHANGE & COMPUTE METHODS
    # ------------------------------------------------------------

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.plan_id = self.template_id.plan_id
            if self.template_id.validity_days:
                self.quotation_validity_date = fields.Date.today() + relativedelta(days=self.template_id.validity_days)
            if self.template_id.terms_and_conditions:
                self.terms_and_conditions = self.template_id.terms_and_conditions
            new_lines = []
            for t_line in self.template_id.line_ids:
                new_lines.append((0, 0, {
                    'product_id': t_line.product_id.id,
                    'name': t_line.product_id.display_name,
                    'quantity': t_line.quantity,
                    'unit_price': t_line.unit_price or t_line.product_id.get_subscription_price(plan=self.plan_id),
                }))
            self.line_ids = [(5, 0, 0)] + new_lines

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id and not self.next_billing_date:
            self.next_billing_date = self.start_date or fields.Date.today()

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'discount_rate', 'plan_id.price')
    def _compute_amounts(self):
        for sub in self:
            base_plan_price = sub.plan_id.price if sub.plan_id else 0.0
            lines_untaxed = sum(sub.line_ids.mapped('price_subtotal'))
            lines_tax = sum(sub.line_ids.mapped('price_tax'))
            
            subtotal_untaxed = base_plan_price + lines_untaxed
            
            # Developer 2 Hook for discount calculation
            disc_amount = sub._hook_compute_discount(subtotal_untaxed)
            
            sub.amount_untaxed = subtotal_untaxed
            sub.amount_discount = disc_amount
            sub.amount_tax = lines_tax
            sub.amount_total = max(0.0, subtotal_untaxed - disc_amount + lines_tax)

    def _hook_compute_discount(self, untaxed_base):
        """
        Extensible hook for Developer 2 Discount Management.
        Calculates discount amount from discount_rate or external discount engine.
        """
        self.ensure_one()
        if self.discount_rate > 0.0:
            return (untaxed_base * self.discount_rate) / 100.0
        return 0.0

    @api.depends('amount_total', 'plan_id.billing_interval_unit', 'state')
    def _compute_mrr_arr(self):
        for sub in self:
            if sub.state not in ('active', 'paused'):
                sub.mrr = 0.0
                sub.arr = 0.0
                continue

            unit = sub.plan_id.billing_interval_unit if sub.plan_id else 'monthly'
            mult = sub.plan_id.billing_interval_count or 1
            total = sub.amount_total or 0.0

            if unit == 'daily':
                sub.mrr = (total / mult) * 30.0
            elif unit == 'weekly':
                sub.mrr = (total / mult) * 4.3333
            elif unit == 'monthly':
                sub.mrr = total / mult
            elif unit == 'yearly':
                sub.mrr = (total / mult) / 12.0
            else:
                sub.mrr = total

            sub.arr = sub.mrr * 12.0

    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    # ------------------------------------------------------------
    # CONSTRAINTS & VALIDATIONS
    # ------------------------------------------------------------

    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        for sub in self:
            if sub.start_date and sub.expiry_date and sub.expiry_date < sub.start_date:
                raise ValidationError(_("Expiry date (%s) cannot be earlier than start date (%s).") % (sub.expiry_date, sub.start_date))

    @api.constrains('line_ids', 'plan_id')
    def _check_plan_min_quantity(self):
        for sub in self:
            if sub.plan_id:
                for line in sub.line_ids:
                    eligible_plans = line.product_id.product_tmpl_id.subscription_plan_ids
                    if eligible_plans and sub.plan_id not in eligible_plans:
                        raise ValidationError(
                            _("Product '%s' is not eligible for subscription plan '%s'.") %
                            (line.product_id.display_name, sub.plan_id.name)
                        )
                    if line.quantity < sub.plan_id.min_quantity:
                        raise ValidationError(
                            _("Product '%s' has quantity %s, which is below the minimum required quantity (%s) for plan '%s'.") %
                            (line.product_id.name, line.quantity, sub.plan_id.min_quantity, sub.plan_id.name)
                        )

    # ------------------------------------------------------------
    # LIFECYCLE STATE TRANSITIONS
    # ------------------------------------------------------------

    def action_send_quotation(self):
        """Transitions: Draft -> Quotation"""
        for sub in self:
            if sub.state != 'draft':
                raise UserError(_("Only draft records can be sent as quotations."))
            if not sub.line_ids and not (sub.plan_id and sub.plan_id.price > 0):
                raise UserError(_("Please add products or select a priced plan before sending a quotation."))
            if not sub.quotation_validity_date:
                sub.quotation_validity_date = fields.Date.today() + relativedelta(days=30)
            sub.state = 'quotation'
            sub.message_post(body=_("Quotation created and sent to customer %s.") % sub.partner_id.name)
        return True

    def action_draft(self):
        """Transitions: Quotation / Closed -> Draft (Only if no active invoices)"""
        for sub in self:
            if sub.state not in ('quotation', 'closed'):
                raise UserError(_("Only quotations or closed contracts can be reset to draft."))
            if any(inv.state != 'cancel' for inv in sub.invoice_ids):
                raise UserError(_("Cannot reset to draft a subscription with active invoices."))
            sub.state = 'draft'
            sub.message_post(body=_("Subscription reset to draft stage."))
        return True

    def action_cancel(self):
        """Transitions: Draft / Quotation -> Closed (Cancellation)"""
        for sub in self:
            if sub.state not in ('draft', 'quotation'):
                raise UserError(_("Only draft or sent quotations can be cancelled."))
            sub.state = 'closed'
            sub.close_date = fields.Date.today()
            sub.close_reason = _("Quotation was cancelled.")
            sub.message_post(body=_("Quotation was cancelled."))
        return True

    def action_confirm(self):
        """Transitions: Draft / Quotation -> Confirmed"""
        for sub in self:
            if sub.state not in ('draft', 'quotation'):
                raise UserError(_("Only draft or quotation records can be confirmed."))

            if not sub.line_ids and not (sub.plan_id and sub.plan_id.price > 0):
                raise ValidationError(_("Cannot confirm a subscription with no product lines and a zero-priced plan."))

            # Validate plan minimum quantity
            sub._check_plan_min_quantity()

            # Validate plan availability
            if not sub.plan_id.is_available_on(sub.start_date or fields.Date.today()):
                raise ValidationError(_("Plan '%s' is not active or outside its availability window.") % sub.plan_id.name)

            # Assign permanent subscription sequence SUB-XXXXX
            if sub.name == _('New') or sub.name.startswith('SQ'):
                sub.name = self.env['ir.sequence'].next_by_code('subscription.subscription') or _('SUB-%05d') % sub.id

            sub.state = 'confirmed'
            sub.message_post(body=_("Subscription confirmed. Formal contract generated with code %s.") % sub.name)
        return True

    def action_activate(self):
        """Transitions: Confirmed -> Active"""
        for sub in self:
            if sub.state != 'confirmed':
                raise UserError(_("Only confirmed subscriptions can be activated."))

            sub.state = 'active'
            if not sub.start_date:
                sub.start_date = fields.Date.today()
            if not sub.next_billing_date:
                sub.next_billing_date = sub.start_date

            sub.message_post(body=_("Subscription activated on %s. Next scheduled billing date is %s.") % (sub.start_date, sub.next_billing_date))
        return True

    def action_pause(self):
        """Transitions: Active -> Paused (Requires plan.allow_pause)"""
        for sub in self:
            if sub.state != 'active':
                raise UserError(_("Only active subscriptions can be paused."))
            if not sub.plan_id.allow_pause:
                raise UserError(_("The plan '%s' does not permit pausing subscriptions.") % sub.plan_id.name)

            sub.state = 'paused'
            sub.pause_date = fields.Date.today()
            sub.message_post(body=_("Subscription paused on %s. Automated recurring billing is suspended.") % sub.pause_date)
        return True

    def action_resume(self):
        """Transitions: Paused -> Active (Adjusts next_billing_date)"""
        today = fields.Date.today()
        for sub in self:
            if sub.state != 'paused':
                raise UserError(_("Only paused subscriptions can be resumed."))

            # If paused for X days, shift next_billing_date forward by paused duration
            if sub.pause_date and sub.next_billing_date:
                paused_days = (today - sub.pause_date).days
                if paused_days > 0:
                    sub.next_billing_date = sub.next_billing_date + relativedelta(days=paused_days)

            sub.pause_date = False
            sub.state = 'active'
            sub.message_post(body=_("Subscription resumed on %s. Next billing date scheduled for %s.") % (today, sub.next_billing_date))
        return True

    def action_renew(self):
        """Transitions: Active / Expired / Closed -> Renewed (Requires plan.allow_renewal)"""
        today = fields.Date.today()
        for sub in self:
            if sub.state in ('draft', 'quotation'):
                raise UserError(_("Quotations cannot be renewed before confirmation."))
            if not sub.plan_id.allow_renewal:
                raise UserError(_("The plan '%s' does not permit renewal.") % sub.plan_id.name)

            old_expiry = sub.expiry_date or today
            base_date = max(today, old_expiry)
            new_expiry = sub.plan_id.calculate_next_billing_date(base_date)

            sub.expiry_date = new_expiry
            if sub.state in ('closed', 'expired'):
                sub.state = 'active'
                sub.next_billing_date = today
                sub.close_date = False
                sub.close_reason = False

            sub.message_post(body=_("Subscription renewed. Contract extended until %s.") % new_expiry)
        return True

    def action_close(self, reason=None):
        """Transitions: Active / Paused / Confirmed -> Closed (Checks plan.allow_early_close)"""
        today = fields.Date.today()
        for sub in self:
            if sub.state in ('closed', 'expired'):
                raise UserError(_("Subscription is already terminated."))

            is_early = sub.expiry_date and today < sub.expiry_date
            if is_early and not sub.plan_id.allow_early_close:
                # Check if current user is manager
                if not self.env.user.has_group('subscription_management.group_subscription_manager'):
                    raise UserError(_("Early termination is disallowed by plan '%s'. Administrator override required.") % sub.plan_id.name)

            sub.state = 'closed'
            sub.close_date = today
            if reason:
                sub.close_reason = reason
            sub.message_post(body=_("Subscription closed on %s. Reason: %s") % (today, sub.close_reason or "Customer request / Standard termination"))
        return True

    def action_check_expiry(self):
        """Automated check for expiring contracts."""
        today = fields.Date.today()
        expiring = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '!=', False),
            ('expiry_date', '<', today)
        ])
        for sub in expiring:
            grace_days = sub.plan_id.auto_close_days or 0
            close_threshold = sub.expiry_date + relativedelta(days=grace_days)
            if today >= close_threshold and sub.plan_id.auto_close:
                sub.state = 'closed'
                sub.close_date = today
                sub.close_reason = _("Automatic closing upon reaching contractual expiry date.")
                sub.message_post(body=_("Subscription auto-closed following expiration of grace period."))
            else:
                sub.state = 'expired'
                sub.message_post(body=_("Subscription reached contractual expiry date on %s.") % sub.expiry_date)
        return True

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _("Invoices for %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.invoice',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.quotation') or _('SQ-NEW')
            if not vals.get('plan_id') and vals.get('template_id'):
                tmpl = self.env['subscription.quotation.template'].browse(vals['template_id'])
                if tmpl.plan_id:
                    vals['plan_id'] = tmpl.plan_id.id
            if 'line_ids' not in vals and vals.get('template_id'):
                tmpl = self.env['subscription.quotation.template'].browse(vals['template_id'])
                if tmpl.line_ids:
                    plan = tmpl.plan_id
                    vals['line_ids'] = [
                        (0, 0, {
                            'product_id': tl.product_id.id,
                            'name': tl.product_id.display_name,
                            'quantity': tl.quantity,
                            'unit_price': tl.unit_price or tl.product_id.get_subscription_price(plan=plan),
                        }) for tl in tmpl.line_ids
                    ]
            if not vals.get('terms_and_conditions') and vals.get('template_id'):
                tmpl = self.env['subscription.quotation.template'].browse(vals['template_id'])
                if tmpl.terms_and_conditions:
                    vals['terms_and_conditions'] = tmpl.terms_and_conditions
        return super(SubscriptionSubscription, self).create(vals_list)

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('bypass_state_validation'):
            new_state = vals['state']
            valid_transitions = {
                'draft': {'quotation', 'confirmed', 'closed'},
                'quotation': {'draft', 'confirmed', 'closed'},
                'confirmed': {'active', 'closed'},
                'active': {'paused', 'closed', 'expired'},
                'paused': {'active', 'closed'},
                'expired': {'active', 'closed'},
                'closed': {'active', 'draft'},
            }
            for sub in self:
                if sub.state != new_state:
                    allowed = valid_transitions.get(sub.state, set())
                    if new_state not in allowed:
                        raise UserError(_("Direct transition from '%s' to '%s' is not permitted.") % (sub.state, new_state))

                    # Guard early close if state is manually written
                    if new_state == 'closed' and sub.expiry_date and fields.Date.today() < sub.expiry_date and not sub.plan_id.allow_early_close:
                        if not self.env.user.has_group('subscription_management.group_subscription_manager'):
                            raise UserError(_("Early termination is disallowed by plan '%s'. Administrator override required.") % sub.plan_id.name)

                    # Guard pause if state is manually written
                    if new_state == 'paused' and not sub.plan_id.allow_pause:
                        raise UserError(_("The plan '%s' does not permit pausing subscriptions.") % sub.plan_id.name)

                    # Guard renewal if state is manually written from closed/expired to active
                    if sub.state in ('closed', 'expired') and new_state == 'active' and not sub.plan_id.allow_renewal:
                        raise UserError(_("The plan '%s' does not permit renewal.") % sub.plan_id.name)

        return super(SubscriptionSubscription, self).write(vals)


class SubscriptionLine(models.Model):
    _name = 'subscription.line'
    _description = 'Subscription Product Line'
    _order = 'id'

    subscription_id = fields.Many2one(
        comodel_name='subscription.subscription',
        string="Subscription",
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product / Variant",
        required=True,
        help="Selected product variant. Surcharges (e.g. Odoo brand +560) are automatically calculated."
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
        digits='Product Price',
        help="Price per unit. Automatically reflects product variant price and brand surcharge."
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        help="Applicable sales taxes."
    )
    discount_rate = fields.Float(
        string="Line Discount %",
        default=0.0,
        help="Line-level discount percentage."
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
        related='subscription_id.currency_id',
        string="Currency",
        readonly=True,
        depends=['subscription_id.currency_id']
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                if not vals.get('name'):
                    vals['name'] = product.display_name or product.name
                if 'unit_price' not in vals:
                    sub_plan = False
                    if vals.get('subscription_id'):
                        sub_rec = self.env['subscription.subscription'].browse(vals['subscription_id'])
                        sub_plan = sub_rec.plan_id
                    vals['unit_price'] = product.get_subscription_price(plan=sub_plan)
        return super(SubscriptionLine, self).create(vals_list)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name or self.product_id.name
            # Compute price using variant-aware method (e.g. Odoo brand adds 560)
            self.unit_price = self.product_id.get_subscription_price(plan=self.subscription_id.plan_id)
            if self.subscription_id.plan_id and self.quantity < self.subscription_id.plan_id.min_quantity:
                self.quantity = self.subscription_id.plan_id.min_quantity

    @api.depends('quantity', 'unit_price', 'discount_rate', 'tax_ids', 'currency_id', 'subscription_id.currency_id')
    def _compute_line_totals(self):
        for line in self:
            price = line.unit_price * (1.0 - (line.discount_rate or 0.0) / 100.0)
            subtotal = line.quantity * price

            if line.tax_ids:
                currency = (
                    line.currency_id
                    or line.subscription_id.currency_id
                    or line.subscription_id.company_id.currency_id
                    or self.env.company.currency_id
                )
                partner = line.subscription_id.partner_id if line.subscription_id else False
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
