#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Live Integration Verification Script for Odoo 17.0
Executes real XML-RPC transactions against containerized Odoo + PostgreSQL instance.
Tests full business lifecycle: Product Variant (+560 Surcharge) -> Plan -> Quotation ->
Contract -> Invoice -> Automated Recurring Billing Engine -> Idempotency Check.
"""

import sys
import time
import xmlrpc.client
from datetime import date

def run_live_verification(host="http://localhost:8069", db="brightloop_test_db", user="admin", password="admin"):
    print("=" * 70)
    print("STARTING ODOO LIVE END-TO-END VERIFICATION")
    print(f"Target URL: {host} | Database: {db} | User: {user}")
    print("=" * 70)

    # 1. Connect and Authenticate
    common = xmlrpc.client.ServerProxy(f"{host}/xmlrpc/2/common")
    try:
        version_info = common.version()
        print(f" [PASS] Connected to Odoo Server Version: {version_info.get('server_version')}")
    except Exception as e:
        print(f" [FAIL] Connection to {host} failed: {e}")
        return False

    uid = common.authenticate(db, user, password, {})
    if not uid:
        print(" [FAIL] Authentication failed. Check database and credentials.")
        return False
    print(f" [PASS] Authenticated successfully as user ID: {uid}")
    models = xmlrpc.client.ServerProxy(f"{host}/xmlrpc/2/object")
    def call(model, method, *args, **kwargs):
        res = models.execute_kw(db, uid, password, model, method, list(args), kwargs)
        if method == 'create' and isinstance(res, list) and len(res) == 1:
            return res[0]
        return res

    # 2. Check Module Installation State
    mod_ids = call('ir.module.module', 'search_read', [('name', '=', 'subscription_management')], ['name', 'state', 'latest_version'])
    if not mod_ids or mod_ids[0]['state'] != 'installed':
        print(f" [FAIL] subscription_management is not installed! State: {mod_ids}")
        return False
    print(f" [PASS] Addon subscription_management is INSTALLED (Version: {mod_ids[0].get('latest_version')})")

    # 3. Verify Custom Models Registered
    expected_models = [
        'subscription.plan',
        'subscription.subscription',
        'subscription.line',
        'subscription.invoice',
        'subscription.invoice.line',
        'subscription.billing.log',
    ]
    reg_models = call('ir.model', 'search_read', [('model', 'in', expected_models)], ['model', 'name'])
    found_models = {m['model'] for m in reg_models}
    for m in expected_models:
        if m in found_models:
            print(f" [PASS] Model registered in ORM: {m}")
        else:
            print(f" [FAIL] Model missing in ORM: {m}")
            return False

    # 4. BUSINESS FLOW TEST
    print("\n--- RUNNING BUSINESS FLOW TESTS ---")

    # Step 4.1: Product & Odoo Variant Surcharge (+560.0)
    tmpl_id = call('product.template', 'create', [{
        'name': 'Cloud Hosting Enterprise',
        'list_price': 1000.0,
        'standard_price': 400.0,
        'is_subscription': True,
        'brand_name': 'odoo',
    }])
    tmpl_data = call('product.template', 'read', [tmpl_id], ['name', 'brand_name', 'brand_surcharge', 'subscription_price'])[0]
    assert tmpl_data['brand_surcharge'] == 560.0, f"Expected 560.0 brand surcharge, got {tmpl_data['brand_surcharge']}"
    assert tmpl_data['subscription_price'] == 1560.0, f"Expected 1560.0 subscription price, got {tmpl_data['subscription_price']}"
    print(f" [PASS] Product Template created with Odoo brand (+560.0 surcharge). Price = {tmpl_data['subscription_price']}")

    prod_ids = call('product.product', 'search_read', [('product_tmpl_id', '=', tmpl_id)], ['id', 'subscription_price', 'brand_name'])
    variant_id = prod_ids[0]['id']
    variant_price = prod_ids[0]['subscription_price']
    assert variant_price == 1560.0, f"Expected variant price 1560.0, got {variant_price}"
    print(f" [PASS] Product Variant (ID {variant_id}) price verified: {variant_price}")

    # Step 4.2: Create Subscription Plan
    plan_id = call('subscription.plan', 'create', [{
        'name': 'Enterprise Monthly SaaS',
        'price': 200.0,
        'billing_interval_unit': 'monthly',
        'billing_interval_count': 1,
        'min_quantity': 2.0,
        'allow_pause': True,
        'allow_renewal': True,
        'allow_early_close': True,
        'auto_close': True,
    }])
    plan_data = call('subscription.plan', 'read', [plan_id], ['code', 'name', 'price'])[0]
    print(f" [PASS] Subscription Plan created: {plan_data['name']} (Code: {plan_data['code']})")

    # Step 4.3: Create Customer
    partner_id = call('res.partner', 'create', [{
        'name': 'Acme Global Software Corp',
        'email': 'billing@acmeglobal.com',
    }])
    print(f" [PASS] Customer created: Acme Global Software Corp (ID {partner_id})")

    # Step 4.4: Create Subscription Quotation
    today_str = str(date.today())
    sub_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_id,
        'start_date': today_str,
        'line_ids': [(0, 0, {
            'product_id': variant_id,
            'name': 'Cloud Hosting Enterprise',
            'quantity': 2.0,
            'unit_price': 1560.0,
        })],
    }])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['name', 'state', 'amount_untaxed', 'amount_total'])[0]
    assert sub_data['state'] == 'draft', f"Expected state draft, got {sub_data['state']}"
    assert sub_data['amount_untaxed'] == 3320.0, f"Expected 3320.0 untaxed (200 base + 2*1560), got {sub_data['amount_untaxed']}"
    print(f" [PASS] Quotation created: {sub_data['name']} (State: {sub_data['state']}, Amount: {sub_data['amount_total']})")

    # Step 4.5: Quotation -> Confirmed
    call('subscription.subscription', 'action_confirm', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['name', 'state'])[0]
    assert sub_data['state'] == 'confirmed', f"Expected state confirmed, got {sub_data['state']}"
    assert sub_data['name'].startswith('SUB-'), f"Expected name to start with SUB-, got {sub_data['name']}"
    print(f" [PASS] Quotation confirmed. Generated contract: {sub_data['name']}")

    # Step 4.6: Confirmed -> Active
    call('subscription.subscription', 'action_activate', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['state', 'next_billing_date', 'start_date'])[0]
    assert sub_data['state'] == 'active', f"Expected state active, got {sub_data['state']}"
    assert sub_data['next_billing_date'] == today_str, f"Expected next_billing_date {today_str}, got {sub_data['next_billing_date']}"
    print(f" [PASS] Contract activated. State: {sub_data['state']}, Next Billing Date: {sub_data['next_billing_date']}")

    # Step 4.7: Generate Recurring Invoice
    call('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    inv_ids = call('subscription.invoice', 'search_read', [('subscription_id', '=', sub_id)], ['name', 'state', 'amount_untaxed', 'amount_total'])
    assert len(inv_ids) == 1, f"Expected exactly 1 invoice, found {len(inv_ids)}"
    inv = inv_ids[0]
    assert inv['state'] == 'confirmed', f"Expected invoice state confirmed, got {inv['state']}"
    assert inv['amount_untaxed'] == 3320.0, f"Expected invoice amount 3320.0, got {inv['amount_untaxed']}"
    print(f" [PASS] Generated Recurring Invoice: {inv['name']} (Total: {inv['amount_total']}, State: {inv['state']})")

    # Step 4.8: Check Billing Audit Log
    logs = call('subscription.billing.log', 'search_read', [('subscription_id', '=', sub_id)], ['status', 'message', 'amount'])
    assert len(logs) >= 1, "Expected at least 1 billing log entry"
    assert logs[0]['status'] == 'success', f"Expected log status success, got {logs[0]['status']}"
    print(f" [PASS] Billing Audit Log verified: Status = {logs[0]['status']}, Amount = {logs[0]['amount']}")

    # Step 4.9: Idempotency & Duplicate Invoice Prevention Check
    print("Testing Idempotency & Duplicate Invoice Prevention...")
    # Trigger recurring billing cron
    call('subscription.subscription', 'cron_recurring_billing')
    inv_ids_after = call('subscription.invoice', 'search_read', [('subscription_id', '=', sub_id)], ['name'])
    assert len(inv_ids_after) == 1, f"Duplicate invoice created! Expected 1 invoice, got {len(inv_ids_after)}"
    print(f" [PASS] Idempotency confirmed: Zero duplicate invoices created. Count remains {len(inv_ids_after)}.")

    print("\n" + "=" * 70)
    print("ALL LIVE ODOO END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8069"
    db = sys.argv[2] if len(sys.argv) > 2 else "brightloop_test_db"
    user = sys.argv[3] if len(sys.argv) > 3 else "admin"
    password = sys.argv[4] if len(sys.argv) > 4 else "admin"

    success = run_live_verification(host, db, user, password)
    sys.exit(0 if success else 1)
