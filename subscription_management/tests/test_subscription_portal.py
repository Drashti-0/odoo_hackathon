# -*- coding: utf-8 -*-
import re

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSubscriptionCustomerPortal(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'name': 'Portal Test Customer',
            'email': 'portal.customer@example.test',
        })
        cls.other_customer = cls.env['res.partner'].create({
            'name': 'Other Portal Customer',
            'email': 'portal.other@example.test',
        })
        portal_group = cls.env.ref(
            'subscription_management.group_subscription_portal'
        )
        cls.login = 'portal.customer@example.test'
        cls.password = 'PortalSecure!2026'
        cls.portal_user = cls.env['res.users'].sudo().with_context(
            no_reset_password=True
        ).create({
            'name': 'Portal Test Customer',
            'login': cls.login,
            'email': cls.login,
            'partner_id': cls.customer.id,
            'password': cls.password,
            'groups_id': [(6, 0, [portal_group.id])],
        })
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Portal Test Monthly Plan',
            'code': 'PORTAL-MONTHLY-TEST',
            'price': 49.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
            'allow_renewal': True,
            'allow_early_close': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Portal Test Service',
            'list_price': 20.0,
            'is_subscription': True,
        })
        cls.own_subscription = cls.env['subscription.subscription'].create({
            'partner_id': cls.customer.id,
            'plan_id': cls.plan.id,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': 'Portal Test Service',
                'quantity': 1.0,
                'unit_price': 20.0,
            })],
        })
        cls.other_subscription = cls.env['subscription.subscription'].create({
            'partner_id': cls.other_customer.id,
            'plan_id': cls.plan.id,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': 'Portal Test Service',
                'quantity': 1.0,
                'unit_price': 20.0,
            })],
        })
        cls.own_invoice = cls.env['subscription.invoice'].create({
            'partner_id': cls.customer.id,
            'subscription_id': cls.own_subscription.id,
            'billing_period_start': cls.own_subscription.start_date,
            'billing_period_end': cls.own_subscription.start_date,
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': 'Portal invoice line',
                'quantity': 1.0,
                'unit_price': 20.0,
            })],
        })
        cls.other_invoice = cls.env['subscription.invoice'].create({
            'partner_id': cls.other_customer.id,
            'subscription_id': cls.other_subscription.id,
            'billing_period_start': cls.other_subscription.start_date,
            'billing_period_end': cls.other_subscription.start_date,
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': 'Private invoice line',
                'quantity': 1.0,
                'unit_price': 20.0,
            })],
        })

    def test_portal_login_and_lists_are_customer_scoped(self):
        self.assertTrue(self.authenticate(self.login, self.password))

        home = self.url_open('/my')
        subscriptions = self.url_open('/my/subscriptions')
        quotations = self.url_open('/my/quotations')
        invoices = self.url_open('/my/invoices')

        self.assertEqual(home.status_code, 200)
        self.assertEqual(subscriptions.status_code, 200)
        self.assertEqual(quotations.status_code, 200)
        self.assertEqual(invoices.status_code, 200)
        self.assertIn(self.own_subscription.name.encode(), subscriptions.content)
        self.assertNotIn(self.other_subscription.name.encode(), subscriptions.content)
        self.assertIn(self.own_invoice.name.encode(), invoices.content)
        self.assertNotIn(self.other_invoice.name.encode(), invoices.content)

    def test_details_and_invoice_documents_enforce_ownership(self):
        self.assertTrue(self.authenticate(self.login, self.password))

        own_subscription = self.url_open(
            '/my/subscriptions/%s' % self.own_subscription.id
        )
        other_subscription = self.url_open(
            '/my/subscriptions/%s' % self.other_subscription.id
        )
        own_invoice = self.url_open('/my/invoices/%s' % self.own_invoice.id)
        other_invoice = self.url_open(
            '/my/invoices/%s' % self.other_invoice.id
        )
        own_pdf = self.url_open(
            '/my/invoices/%s/pdf' % self.own_invoice.id
        )
        other_pdf = self.url_open(
            '/my/invoices/%s/pdf' % self.other_invoice.id
        )

        self.assertEqual(own_subscription.status_code, 200)
        self.assertIn(self.own_subscription.name.encode(), own_subscription.content)
        self.assertEqual(other_subscription.status_code, 404)
        self.assertEqual(own_invoice.status_code, 200)
        self.assertEqual(other_invoice.status_code, 404)
        self.assertEqual(own_pdf.status_code, 200)
        self.assertIn('application/pdf', own_pdf.headers.get('Content-Type', ''))
        self.assertTrue(own_pdf.content.startswith(b'%PDF'))
        self.assertEqual(other_pdf.status_code, 404)

    def test_customer_requests_review_without_changing_subscription_state(self):
        self.assertTrue(self.authenticate(self.login, self.password))
        page = self.url_open(
            '/my/subscriptions/%s' % self.own_subscription.id
        )
        token = re.search(
            rb'name="csrf_token"\s+value="([^"]+)"', page.content
        )
        self.assertTrue(token, "Portal cancellation form must include a CSRF token.")

        response = self.url_open(
            '/my/subscriptions/%s/request-cancellation'
            % self.own_subscription.id,
            data={'csrf_token': token.group(1).decode()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.own_subscription.state, 'active')
        request_activity = self.env['mail.activity'].sudo().search([
            ('res_model', '=', 'subscription.subscription'),
            ('res_id', '=', self.own_subscription.id),
            ('summary', '=', 'Customer cancellation request'),
        ])
        self.assertEqual(len(request_activity), 1)

    def test_subscription_and_invoice_record_rules_scope_portal_reads(self):
        own_subscriptions = self.env['subscription.subscription'].with_user(
            self.portal_user
        ).search([])
        own_invoices = self.env['subscription.invoice'].with_user(
            self.portal_user
        ).search([])
        own_subscription_lines = self.env['subscription.line'].with_user(
            self.portal_user
        ).search([])
        own_invoice_lines = self.env['subscription.invoice.line'].with_user(
            self.portal_user
        ).search([])
        billing_logs = self.env['subscription.billing.log'].with_user(
            self.portal_user
        )

        self.assertEqual(own_subscriptions.mapped('partner_id'), self.customer)
        self.assertEqual(own_invoices.mapped('partner_id'), self.customer)
        self.assertEqual(
            own_subscription_lines.mapped('subscription_id'),
            self.own_subscription,
        )
        self.assertEqual(
            own_invoice_lines.mapped('invoice_id'),
            self.own_invoice,
        )
        self.assertFalse(billing_logs.check_access_rights('read', raise_exception=False))
