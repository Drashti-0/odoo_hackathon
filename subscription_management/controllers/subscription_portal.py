# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.http import content_disposition, request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from werkzeug.exceptions import InternalServerError, NotFound


class SubscriptionCustomerPortal(CustomerPortal):
    _items_per_page = 20

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kwargs):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        subscriptions = request.env['subscription.subscription'].search([
            ('partner_id', '=', partner.id),
        ], order='create_date desc, id desc')
        invoices = request.env['subscription.invoice'].search([
            ('partner_id', '=', partner.id),
        ], order='invoice_date desc, id desc')
        upcoming = request.env['subscription.subscription'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'active'),
            ('next_billing_date', '!=', False),
        ], order='next_billing_date, id', limit=1)
        today = fields.Date.today()
        plans = request.env['subscription.plan'].search([
            ('active', '=', True),
        ], order='sequence, name').filtered(
            lambda plan: plan.is_available_on(today)
        )[:3]
        values.update({
            'page_name': 'home',
            'portal_subscriptions': subscriptions,
            'portal_active_subscriptions': subscriptions.filtered(
                lambda subscription: subscription.state == 'active'
            ),
            'portal_invoices': invoices[:5],
            'portal_invoice_count': len(invoices),
            'portal_pending_invoice_count': len(invoices.filtered(
                lambda invoice: invoice.payment_state != 'paid'
                and invoice.amount_residual > 0
                and invoice.state not in ('cancel', 'paid')
            )),
            'portal_upcoming_subscription': upcoming,
            'portal_plans': plans,
        })
        return request.render('portal.portal_my_home', values)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'subscription_count' in counters:
            values['subscription_count'] = request.env[
                'subscription.subscription'
            ].search_count([('partner_id', '=', partner.id)])
        if 'quotation_count' in counters:
            values['quotation_count'] = request.env[
                'subscription.subscription'
            ].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('draft', 'quotation')),
            ])
        if 'subscription_invoice_count' in counters:
            values['subscription_invoice_count'] = request.env[
                'subscription.invoice'
            ].search_count([('partner_id', '=', partner.id)])
        return values

    @http.route(
        ['/my/plans', '/my/plans/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_subscription_plans(self, page=1, **kwargs):
        today = fields.Date.today()
        plans_model = request.env['subscription.plan']
        available_plans = plans_model.search(
            [('active', '=', True)],
            order='sequence, name',
        ).filtered(lambda plan: plan.is_available_on(today))
        total = len(available_plans)
        pager = portal_pager(
            url='/my/plans',
            total=total,
            page=page,
            step=self._items_per_page,
        )
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscription_plans',
            'plans': available_plans[pager['offset']:pager['offset'] + self._items_per_page],
            'pager': pager,
        })
        return request.render(
            'subscription_management.portal_subscription_plans', values
        )

    def _get_customer_subscription(self, subscription_id):
        subscription = request.env['subscription.subscription'].search([
            ('id', '=', subscription_id),
            ('partner_id', '=', request.env.user.partner_id.id),
        ], limit=1)
        if not subscription:
            raise NotFound()
        return subscription

    def _get_customer_invoice(self, invoice_id):
        invoice = request.env['subscription.invoice'].search([
            ('id', '=', invoice_id),
            ('partner_id', '=', request.env.user.partner_id.id),
        ], limit=1)
        if not invoice:
            raise NotFound()
        return invoice

    def _prepare_subscription_list(self, url, domain, page, page_name):
        subscriptions_model = request.env['subscription.subscription']
        total = subscriptions_model.search_count(domain)
        pager = portal_pager(
            url=url,
            total=total,
            page=page,
            step=self._items_per_page,
        )
        subscriptions = subscriptions_model.search(
            domain,
            order='create_date desc, id desc',
            limit=self._items_per_page,
            offset=pager['offset'],
        )
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': page_name,
            'subscriptions': subscriptions,
            'pager': pager,
        })
        return values

    @http.route(
        ['/my/subscriptions', '/my/subscriptions/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_subscriptions(self, page=1, **kwargs):
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        return request.render(
            'subscription_management.portal_my_subscriptions',
            self._prepare_subscription_list(
                '/my/subscriptions', domain, page, 'subscription'
            ),
        )

    @http.route(
        ['/my/quotations', '/my/quotations/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_quotations(self, page=1, **kwargs):
        domain = [
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', 'in', ('draft', 'quotation')),
        ]
        return request.render(
            'subscription_management.portal_my_quotations',
            self._prepare_subscription_list(
                '/my/quotations', domain, page, 'quotation'
            ),
        )

    @http.route(
        ['/my/subscriptions/<int:subscription_id>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_subscription_detail(self, subscription_id, **kwargs):
        subscription = self._get_customer_subscription(subscription_id)
        invoices = request.env['subscription.invoice'].search([
            ('subscription_id', '=', subscription.id),
            ('partner_id', '=', request.env.user.partner_id.id),
        ], order='invoice_date desc, id desc')
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscription_detail',
            'subscription': subscription,
            'invoices': invoices,
            'request_status': kwargs.get('request'),
        })
        return request.render(
            'subscription_management.portal_subscription_detail', values
        )

    @http.route(
        ['/my/invoices', '/my/invoices/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_invoices(self, page=1, **kwargs):
        invoices_model = request.env['subscription.invoice']
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        total = invoices_model.search_count(domain)
        pager = portal_pager(
            url='/my/invoices',
            total=total,
            page=page,
            step=self._items_per_page,
        )
        invoices = invoices_model.search(
            domain,
            order='invoice_date desc, id desc',
            limit=self._items_per_page,
            offset=pager['offset'],
        )
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscription_invoice',
            'invoices': invoices,
            'pager': pager,
        })
        return request.render(
            'subscription_management.portal_my_invoices', values
        )

    @http.route(
        ['/my/billing-history', '/my/billing-history/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_billing_history(self, page=1, **kwargs):
        return self.portal_my_invoices(page=page, **kwargs)

    @http.route(
        ['/my/invoices/<int:invoice_id>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_invoice_detail(self, invoice_id, **kwargs):
        invoice = self._get_customer_invoice(invoice_id)
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscription_invoice_detail',
            'invoice': invoice,
        })
        return request.render(
            'subscription_management.portal_invoice_detail', values
        )

    @http.route(
        ['/my/invoices/<int:invoice_id>/pdf'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_invoice_pdf(self, invoice_id, **kwargs):
        invoice = self._get_customer_invoice(invoice_id)
        report = request.env.ref(
            'subscription_management.action_report_subscription_invoice'
        ).sudo()
        document, report_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report, [invoice.id]
        )
        if report_type not in ('pdf', 'html'):
            raise InternalServerError(
                _("The invoice document could not be generated.")
            )
        if report_type == 'pdf' and not document.startswith(b'%PDF-'):
            raise InternalServerError(
                _("The invoice document could not be generated.")
            )
        extension = 'pdf' if report_type == 'pdf' else 'html'
        return request.make_response(document, headers=[
            ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
            ('Content-Disposition', content_disposition(
                '%s.%s' % (invoice.name, extension)
            )),
        ])

    def _submit_staff_request(self, subscription, summary, note):
        model_id = request.env['ir.model']._get_id('subscription.subscription')
        activity_model = request.env['mail.activity'].sudo()
        existing = activity_model.search([
            ('res_model_id', '=', model_id),
            ('res_id', '=', subscription.id),
            ('summary', '=', summary),
        ], limit=1)
        if existing:
            return False

        assignee = subscription.sudo().user_id
        if not assignee or assignee.share:
            assignee = request.env.ref('base.user_admin').sudo()
        activity_model.create({
            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            'date_deadline': fields.Date.today(),
            'summary': summary,
            'note': note,
            'user_id': assignee.id,
            'res_model_id': model_id,
            'res_id': subscription.id,
        })
        return True

    @http.route(
        ['/my/subscriptions/<int:subscription_id>/request-cancellation'],
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
    )
    def portal_request_cancellation(self, subscription_id, **post):
        subscription = self._get_customer_subscription(subscription_id)
        if subscription.state not in ('active', 'paused'):
            raise NotFound()
        submitted = self._submit_staff_request(
            subscription,
            _("Customer cancellation request"),
            _("The customer requested cancellation. Review plan closure rules and contact the customer before changing the contract."),
        )
        status = 'cancellation_submitted' if submitted else 'request_already_submitted'
        return request.redirect(
            '/my/subscriptions/%s?request=%s' % (subscription.id, status)
        )

    @http.route(
        ['/my/subscriptions/<int:subscription_id>/request-renewal'],
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
    )
    def portal_request_renewal(self, subscription_id, **post):
        subscription = self._get_customer_subscription(subscription_id)
        if (
            subscription.state not in ('active', 'expired', 'closed')
            or not subscription.plan_id.allow_renewal
        ):
            raise NotFound()
        submitted = self._submit_staff_request(
            subscription,
            _("Customer renewal request"),
            _("The customer requested renewal. Confirm plan availability and renewal eligibility before processing."),
        )
        status = 'renewal_submitted' if submitted else 'request_already_submitted'
        return request.redirect(
            '/my/subscriptions/%s?request=%s' % (subscription.id, status)
        )
