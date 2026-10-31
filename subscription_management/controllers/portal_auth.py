# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class SubscriptionPortalAuthController(http.Controller):

    @http.route(['/subscription/api/register', '/subscription/register'], type='json', auth='public', methods=['POST'], csrf=False)
    def register_customer_json(self, **kwargs):
        """
        Secure JSON API Endpoint for Portal Customer Self-Registration:
        - Payload: {name, email, password, company_name (optional)}
        - Validates unique case-insensitive email
        - Enforces password complexity (> 8 chars, uppercase, lowercase, special char)
        - Prevents privilege escalation
        """
        data = request.httprequest.data
        params = kwargs
        if data:
            try:
                parsed = json.loads(data)
                params.update(parsed)
            except Exception:
                pass

        name = params.get('name')
        email = params.get('email')
        password = params.get('password')
        company = params.get('company_name')

        if not name or not email or not password:
            return {
                'status': 'error',
                'error_code': 'MISSING_FIELDS',
                'message': _("Name, email, and password are required fields.")
            }

        try:
            res = request.env['res.users'].sudo().register_portal_customer(
                name=name,
                email=email,
                password=password,
                company_name=company
            )
            return {
                'status': 'success',
                'user_id': res.get('user_id'),
                'partner_id': res.get('partner_id'),
                'message': res.get('message'),
            }
        except (ValidationError, AccessError) as err:
            return {
                'status': 'error',
                'error_code': 'VALIDATION_FAILED',
                'message': str(err),
            }
        except Exception as exc:
            _logger.error("Unhandled error during customer registration: %s", exc)
            return {
                'status': 'error',
                'error_code': 'SERVER_ERROR',
                'message': _("Unable to process registration at this time. Please contact support."),
            }

    @http.route(['/subscription/api/reset-password', '/subscription/reset-password'], type='json', auth='public', methods=['POST'], csrf=False)
    def reset_password_json(self, **kwargs):
        """
        Secure JSON API Endpoint for Password Reset Request:
        - Payload: {email}
        - Triggers native password reset
        - Defends against user account enumeration attacks
        """
        data = request.httprequest.data
        params = kwargs
        if data:
            try:
                parsed = json.loads(data)
                params.update(parsed)
            except Exception:
                pass

        email = params.get('email')
        if not email:
            return {
                'status': 'error',
                'error_code': 'MISSING_EMAIL',
                'message': _("Email address is required.")
            }

        try:
            res = request.env['res.users'].sudo().request_password_reset(email)
            return {
                'status': 'success',
                'message': res.get('message'),
            }
        except Exception as exc:
            _logger.error("Error in reset_password_json: %s", exc)
            return {
                'status': 'success',
                'message': _("If this email is registered with Brightloop, reset instructions have been dispatched."),
            }

    @http.route('/subscription/my/contracts', type='json', auth='user', methods=['POST', 'GET'])
    def get_my_subscriptions(self, **kwargs):
        """
        Isolated Portal API: Returns contracts belonging strictly to the authenticated user's partner.
        Customers cannot access other customers' subscriptions.
        """
        current_partner = request.env.user.partner_id
        subs = request.env['subscription.subscription'].search([
            ('partner_id', '=', current_partner.id)
        ])
        results = []
        for sub in subs:
            results.append({
                'id': sub.id,
                'name': sub.name,
                'plan': sub.plan_id.name,
                'state': sub.state,
                'amount_total': sub.amount_total,
                'start_date': str(sub.start_date) if sub.start_date else None,
                'expiry_date': str(sub.expiry_date) if sub.expiry_date else None,
            })
        return {'status': 'success', 'subscriptions': results}

    @http.route('/subscription/my/invoices', type='json', auth='user', methods=['POST', 'GET'])
    def get_my_invoices(self, **kwargs):
        """
        Isolated Portal API: Returns invoices belonging strictly to the authenticated user's partner.
        """
        current_partner = request.env.user.partner_id
        invoices = request.env['subscription.invoice'].search([
            ('partner_id', '=', current_partner.id)
        ])
        results = []
        for inv in invoices:
            results.append({
                'id': inv.id,
                'name': inv.name,
                'invoice_date': str(inv.invoice_date) if inv.invoice_date else None,
                'amount_total': inv.amount_total,
                'payment_state': inv.payment_state,
                'state': inv.state,
            })
        return {'status': 'success', 'invoices': results}
