# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Subscription Management',
    'version': '17.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Enterprise Subscription Lifecycle & Intelligent Recurring Billing Engine',
    'description': """
Brightloop Subscription Management System
==========================================
Developed by Team AuraMinds for Hackathon.

Modules Included (Developer 1 Core):
------------------------------------
1. Product & Product Variant Management (Variant Surcharges, Odoo Brand +560)
2. Subscription Plan Management (Daily, Weekly, Monthly, Yearly Billing Intervals)
3. Quotation & Subscription Management (Full Lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed)
4. Invoice & Intelligent Automated Billing Engine (Cron, Catch-up, Idempotency, Concurrency Safe)

Integration Ready:
------------------
- Developer 2 Modules: User Auth, Discounts, Payments, Financial Dashboards
- Full specifications in INTEGRATION_CONTRACT.md
    """,
    'author': 'Team AuraMinds (Dhruti Viradiya & Drashti Bhanderi)',
    'website': 'https://brightloopsoftware.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'account', 'portal', 'website'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/user_security.xml',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'reports/invoice_report.xml',
        'views/product_views.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_views.xml',
        'views/invoice_views.xml',
        'views/billing_log_views.xml',
        'views/menu_views.xml',
        'views/user_views.xml',
        'views/customer_views.xml',
        'views/discount_views.xml',
        'views/payment_views.xml',
        'views/dashboard_views.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'subscription_management/static/src/css/brightloop_backend.css',
            'subscription_management/static/src/js/brightloop_backend.js',
        ],
        'web.assets_frontend': [
            'subscription_management/static/src/css/brightloop_portal.css',
            'subscription_management/static/src/js/brightloop_portal.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
