#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HACKATHON JUDGE DEMO FLOW VERIFICATION SCRIPT
Simulates the exact end-to-end user journey that a hackathon judge will perform:
1. Verify Menu Navigation & Top-Level Access
2. Open Dashboard and verify non-blank KPIs
3. Create a Subscription Product with Brand Surcharge
4. Create a Subscription Plan
5. Create a Subscription Quotation with product lines
6. Confirm Quotation into Subscription (SUB-XXXXX)
7. Activate Subscription
8. Generate Next Recurring Invoice (INV-XXXXX)
9. Confirm and Register Payment on the Invoice
"""

import xmlrpc.client
import time
from datetime import date

HOST = 'http://localhost:8069'
DB = 'brightloop_test_db'
USER = 'admin'
PWD = 'admin'

def test_judge_journey():
    print("=" * 80)
    print("STARTING HACKATHON JUDGE DEMO USER JOURNEY VERIFICATION")
    print(f"Target: {HOST} | Database: {DB}")
    print("=" * 80)

    # 1. Connect and Authenticate
    common = xmlrpc.client.ServerProxy(f"{HOST}/xmlrpc/2/common")
    uid = common.authenticate(DB, USER, PWD, {})
    assert uid, "Authentication failed!"
    print(f"[PASS] Authenticated successfully as Admin (UID: {uid})")

    models = xmlrpc.client.ServerProxy(f"{HOST}/xmlrpc/2/object")
    def call(model, method, *args, **kwargs):
        res = models.execute_kw(DB, uid, PWD, model, method, list(args), kwargs)
        if method == 'create' and isinstance(res, list) and len(res) == 1:
            return res[0]
        return res

    # 2. Verify Menus
    print("\n--- 1. VERIFYING JUDGE MENU NAVIGATION ---")
    root_menus = call('ir.ui.menu', 'search_read', [('name', '=', 'Brightloop Subscriptions')], ['name', 'action', 'child_id'])
    assert root_menus, "Brightloop Subscriptions root menu not found!"
    root = root_menus[0]
    print(f"[PASS] Root Menu found: '{root['name']}' with default action: {root['action']}")

    child_menus = call('ir.ui.menu', 'search_read', [('id', 'in', root['child_id'])], ['name', 'sequence', 'action'])
    menu_names = [m['name'] for m in child_menus]
    print(f"[PASS] Submenus available in top bar: {menu_names}")
    for required in ['Subscriptions', 'Billing & Invoices', 'Products & Plans']:
        assert required in menu_names, f"Missing expected menu '{required}'"

    # 3. Verify Dashboard Non-Blank default_get
    print("\n--- 2. VERIFYING DASHBOARD KPI CARDS ---")
    default_vals = call('subscription.dashboard.console', 'default_get', ['total_customers', 'total_products', 'total_plans', 'active_subscriptions', 'total_revenue', 'mrr_total'])
    print(f"[PASS] Dashboard default KPIs: Customers={default_vals.get('total_customers')}, Products={default_vals.get('total_products')}, Plans={default_vals.get('total_plans')}, Active Subs={default_vals.get('active_subscriptions')}, Revenue={default_vals.get('total_revenue')}, MRR={default_vals.get('mrr_total')}")
    assert default_vals.get('total_products', 0) > 0, "Dashboard products must not be zero!"

    # 4. Step 1 for Judge: Create a Product
    print("\n--- 3. JUDGE ACTION: CREATE SUBSCRIPTION PRODUCT ---")
    tag = int(time.time())
    product_tmpl_id = call('product.template', 'create', [{
        'name': f'Judge Demo Cloud ERP {tag}',
        'is_subscription': True,
        'type': 'service',
        'list_price': 2000.0,
        'brand_name': 'odoo',
    }])
    prod_data = call('product.template', 'read', [product_tmpl_id], ['name', 'brand_name', 'brand_surcharge', 'subscription_price'])[0]
    print(f"[PASS] Created Product: '{prod_data['name']}'")
    print(f"       Base: ₹2000.0 | Brand: {prod_data['brand_name']} | Surcharge: +₹{prod_data['brand_surcharge']} | Final Price: ₹{prod_data['subscription_price']}")
    assert prod_data['brand_surcharge'] == 560.0, "Odoo brand surcharge must be +560.0"
    assert prod_data['subscription_price'] == 2560.0, "Final price must be 2560.0"

    # 5. Step 2 for Judge: Create a Subscription Plan
    print("\n--- 4. JUDGE ACTION: CREATE SUBSCRIPTION PLAN ---")
    plan_id = call('subscription.plan', 'create', [{
        'name': f'Judge Professional Monthly {tag}',
        'price': 500.0,
        'billing_interval_unit': 'monthly',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
        'allow_pause': True,
        'allow_renewal': True,
        'allow_early_close': True,
    }])
    plan_data = call('subscription.plan', 'read', [plan_id], ['name', 'code', 'price', 'billing_interval_unit'])[0]
    print(f"[PASS] Created Plan: '{plan_data['name']}' (Code: {plan_data['code']}, Base Fee: ₹{plan_data['price']}/{plan_data['billing_interval_unit']})")

    # 6. Step 3 for Judge: Create a Quotation
    print("\n--- 5. JUDGE ACTION: CREATE QUOTATION ---")
    existing_partners = call('res.partner', 'search', [('email', '=', 'judge.demo@example.com')])
    if existing_partners:
        partner_id = existing_partners[0]
    else:
        partner_id = call('res.partner', 'create', [{
            'name': 'Judge Demo Enterprise Customer',
            'email': 'judge.demo@example.com',
            'is_company': True,
        }])

    # Get product variant
    variant_ids = call('product.product', 'search', [('product_tmpl_id', '=', product_tmpl_id)])
    assert variant_ids, "Variant not found for created product template!"
    variant_id = variant_ids[0]

    sub_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_id,
        'start_date': str(date.today()),
        'line_ids': [(0, 0, {
            'product_id': variant_id,
            'name': 'Cloud ERP Subscription License',
            'quantity': 2.0,
            'unit_price': 2560.0,
        })],
    }])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['name', 'state', 'amount_untaxed', 'amount_total'])[0]
    print(f"[PASS] Created Quotation: {sub_data['name']} (State: {sub_data['state']}, Total: ₹{sub_data['amount_total']})")
    assert sub_data['state'] == 'draft', "Initial quotation state must be draft"
    # Plan base fee 500 + 2 * 2560 = 5620.0
    assert sub_data['amount_total'] == 5620.0, f"Expected 5620.0, got {sub_data['amount_total']}"

    # Send Quotation
    call('subscription.subscription', 'action_send_quotation', [sub_id])
    sub_data_sent = call('subscription.subscription', 'read', [sub_id], ['state'])[0]
    assert sub_data_sent['state'] == 'quotation', "State should advance to quotation"
    print(f"[PASS] Advanced to 'Quotation Sent'")

    # 7. Step 4 for Judge: Confirm Order & Activate
    print("\n--- 6. JUDGE ACTION: CONFIRM & ACTIVATE SUBSCRIPTION ---")
    call('subscription.subscription', 'action_confirm', [sub_id])
    sub_data_conf = call('subscription.subscription', 'read', [sub_id], ['name', 'state'])[0]
    print(f"[PASS] Confirmed Order: Assigned Contract Reference: {sub_data_conf['name']} (State: {sub_data_conf['state']})")
    assert sub_data_conf['name'].startswith('SUB-'), "Contract number must start with SUB-"
    assert sub_data_conf['state'] == 'confirmed', "State must be confirmed"

    call('subscription.subscription', 'action_activate', [sub_id])
    sub_data_act = call('subscription.subscription', 'read', [sub_id], ['state', 'next_billing_date', 'mrr'])[0]
    print(f"[PASS] Activated Subscription! State: {sub_data_act['state']} | Next Billing Date: {sub_data_act['next_billing_date']} | MRR: ₹{sub_data_act['mrr']}")
    assert sub_data_act['state'] == 'active', "State must be active"

    # 8. Step 5 for Judge: Generate Invoice
    print("\n--- 7. JUDGE ACTION: GENERATE RECURRING INVOICE ---")
    call('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    inv_ids = call('subscription.invoice', 'search_read', [('subscription_id', '=', sub_id)], ['name', 'state', 'amount_total', 'payment_state'])
    assert inv_ids, "Invoice was not generated!"
    inv = inv_ids[0]
    print(f"[PASS] Generated Invoice: {inv['name']} (State: {inv['state']}, Total: ₹{inv['amount_total']}, Payment Status: {inv['payment_state']})")
    assert inv['name'].startswith('INV-'), "Invoice sequence must start with INV-"
    assert inv['state'] == 'confirmed', "Invoice must be in confirmed/posted state"
    assert inv['amount_total'] == 5620.0, f"Expected 5620.0, got {inv['amount_total']}"

    # 9. Register Payment on Invoice
    print("\n--- 8. JUDGE ACTION: REGISTER PAYMENT ---")
    call('subscription.invoice', 'action_register_payment', [inv['id']], 5620.0, 'card')
    inv_paid = call('subscription.invoice', 'read', [inv['id']], ['state', 'payment_state', 'amount_residual'])[0]
    print(f"[PASS] Payment Registered: State: {inv_paid['state']} | Payment Status: {inv_paid['payment_state']} | Balance Due: ₹{inv_paid['amount_residual']}")
    assert inv_paid['payment_state'] == 'paid', "Payment status must be paid"
    assert inv_paid['amount_residual'] == 0.0, "Outstanding balance must be zero"

    print("\n" + "=" * 80)
    print("ALL 8 HACKATHON JUDGE DEMO FLOW MILESTONES COMPLETED WITH 100% SUCCESS!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    test_judge_journey()
