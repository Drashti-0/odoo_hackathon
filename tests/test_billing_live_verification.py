#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live XML-RPC Verification Script for Module 4: Invoice Management & Automated Billing Engine
Runs against the live running Odoo 17 CE server at http://localhost:8069.
Verifies real database persistence, ORM methods, state machines, and cron automation.
"""

import sys
import xmlrpc.client
from datetime import date, datetime, timedelta

ODOO_URL = "http://localhost:8069"
DB_NAME = "brightloop_test_db"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

def main():
    print("=" * 70)
    print("LIVE XML-RPC VERIFICATION: MODULE 4 INVOICE & AUTOMATED BILLING ENGINE")
    print(f"Target: {ODOO_URL} | Database: {DB_NAME}")
    print("=" * 70)

    # 1. Connection & Authentication
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    try:
        uid = common.authenticate(DB_NAME, ADMIN_USER, ADMIN_PASS, {})
        if not uid:
            print("[FAIL] Authentication failed: invalid credentials or database.")
            sys.exit(1)
        print(f"[PASS] Connected & Authenticated successfully (UID: {uid})")
    except Exception as e:
        print(f"[FAIL] Could not connect to Odoo XML-RPC: {e}")
        sys.exit(1)

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    def execute(model, method, *args, **kwargs):
        return models.execute_kw(DB_NAME, uid, ADMIN_PASS, model, method, list(args), kwargs)

    today = date.today().isoformat()
    period_start = today
    period_end = (date.today() + timedelta(days=30)).isoformat()

    # 2. Setup Partner, Plan, Product
    partner_id = execute('res.partner', 'search', [('name', '=', 'Live Billing Test Corp')], limit=1)
    if not partner_id:
        partner_id = [execute('res.partner', 'create', {'name': 'Live Billing Test Corp', 'email': 'live_test@example.com'})]
    partner_id = partner_id[0]

    plan_id = execute('subscription.plan', 'search', [('code', '=', 'PLAN-LIVE-MTH')], limit=1)
    if not plan_id:
        plan_id = [execute('subscription.plan', 'create', {
            'name': 'Live Monthly Professional Plan',
            'code': 'PLAN-LIVE-MTH',
            'price': 250.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
        })]
    plan_id = plan_id[0]

    prod_id = execute('product.product', 'search', [('name', '=', 'Live Cloud Hosting Engine')], limit=1)
    if not prod_id:
        tmpl_id = execute('product.template', 'create', {
            'name': 'Live Cloud Hosting Engine',
            'list_price': 750.0,
            'is_subscription': True,
            'brand_name': 'odoo',  # +560 surcharge -> 1310.0
        })
        prod_id = execute('product.product', 'search', [('product_tmpl_id', '=', tmpl_id)], limit=1)
    prod_id = prod_id[0]

    coupon_id = execute('subscription.discount', 'search', [('code', '=', 'LIVE10')], limit=1)
    if not coupon_id:
        coupon_id = [execute('subscription.discount', 'create', {
            'name': 'Live 10% Coupon',
            'code': 'LIVE10',
            'discount_type': 'percentage',
            'value': 10.0,
            'active': True,
        })]
    coupon_id = coupon_id[0]

    print("[PASS] Master data initialized (Partner, Plan, Variant Product, Coupon)")

    # 3. Create Subscription and Activate
    sub_id = execute('subscription.subscription', 'create', {
        'partner_id': partner_id,
        'plan_id': plan_id,
        'start_date': today,
        'next_billing_date': today,
        'line_ids': [(0, 0, {
            'product_id': prod_id,
            'quantity': 1.0,
            'unit_price': 1310.0,
        })],
    })
    execute('subscription.subscription', 'action_confirm', [sub_id])
    execute('subscription.subscription', 'action_activate', [sub_id])
    sub_data = execute('subscription.subscription', 'read', [sub_id], ['name', 'state'])[0]
    assert sub_data['state'] == 'active', f"Subscription should be active: {sub_data}"
    print(f"[PASS] Active subscription created: {sub_data['name']} (ID: {sub_id})")

    # 4. Trigger Recurring Billing Catch-up Engine
    execute('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    sub_data = execute('subscription.subscription', 'read', [sub_id], ['invoice_ids', 'invoice_count'])[0]
    assert sub_data['invoice_count'] >= 1, "Invoice count should be at least 1"
    inv_id = sub_data['invoice_ids'][0]

    inv_data = execute('subscription.invoice', 'read', [inv_id], [
        'name', 'state', 'payment_state', 'amount_untaxed', 'amount_total', 'amount_paid', 'amount_residual'
    ])[0]
    print(f"[PASS] Invoice generated via Billing Engine: {inv_data['name']}")
    print(f"       State: {inv_data['state']} | Payment Status: {inv_data['payment_state']}")
    print(f"       Untaxed: {inv_data['amount_untaxed']} | Total: {inv_data['amount_total']} | Residual: {inv_data['amount_residual']}")
    assert inv_data['state'] == 'confirmed', "Generated recurring invoice should be confirmed"
    assert inv_data['amount_untaxed'] == 1560.0, f"Expected untaxed 1560.0 (250 plan + 1310 prod), got {inv_data['amount_untaxed']}"
    assert inv_data['amount_residual'] == 1560.0, f"Expected residual 1560.0, got {inv_data['amount_residual']}"
    assert inv_data['payment_state'] == 'not_paid'

    # 5. Idempotency Check: Running Billing Engine again on same day should not generate duplicate invoice
    initial_count = sub_data['invoice_count']
    execute('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    sub_data_post = execute('subscription.subscription', 'read', [sub_id], ['invoice_count'])[0]
    assert sub_data_post['invoice_count'] == initial_count, "Duplicate invoice was generated! Idempotency check failed."
    print(f"[PASS] Idempotency verified: re-running billing engine did not create duplicate (Count: {sub_data_post['invoice_count']})")

    # 6. Audit Trail: Verify billing log entry exists
    log_ids = execute('subscription.billing.log', 'search', [('subscription_id', '=', sub_id)])
    assert len(log_ids) >= 1, "No billing log generated!"
    logs = execute('subscription.billing.log', 'read', log_ids, ['status', 'message', 'amount'])
    statuses = [l['status'] for l in logs]
    assert 'success' in statuses, f"Expected success log: {statuses}"
    print(f"[PASS] Billing audit log verified: found {len(log_ids)} log entry/entries (Statuses: {statuses})")

    # 7. Discount Hook Application
    # Reset to draft for coupon application per contract
    execute('subscription.invoice', 'action_draft', [inv_id])
    inv_data_draft = execute('subscription.invoice', 'read', [inv_id], ['state'])[0]
    assert inv_data_draft['state'] == 'draft', "Invoice should be in draft after action_draft"

    execute('subscription.invoice', 'apply_discount_code', [inv_id], "LIVE10")
    inv_data_disc = execute('subscription.invoice', 'read', [inv_id], [
        'discount_code', 'amount_discount', 'amount_total', 'amount_residual'
    ])[0]
    assert inv_data_disc['discount_code'] == 'LIVE10', "Discount code not applied"
    assert inv_data_disc['amount_discount'] == 156.0, f"Expected discount 156.0 (10% of 1560), got {inv_data_disc['amount_discount']}"
    assert inv_data_disc['amount_total'] == 1404.0, f"Expected total 1404.0, got {inv_data_disc['amount_total']}"
    print(f"[PASS] Discount hook verified: Applied LIVE10 -> -{inv_data_disc['amount_discount']} deducted. New Total: {inv_data_disc['amount_total']}")

    # Confirm invoice with discount applied
    execute('subscription.invoice', 'action_confirm', [inv_id])
    inv_data_conf = execute('subscription.invoice', 'read', [inv_id], ['state', 'amount_residual'])[0]
    assert inv_data_conf['state'] == 'confirmed'
    assert inv_data_conf['amount_residual'] == 1404.0

    # 8. Partial Payment Settlement
    execute('subscription.invoice', 'action_register_payment', [inv_id], 404.0, "STRIPE-LIVE-PARTIAL")
    inv_data_part = execute('subscription.invoice', 'read', [inv_id], [
        'state', 'payment_state', 'amount_paid', 'amount_residual'
    ])[0]
    assert inv_data_part['payment_state'] == 'partial', f"Expected partial payment status, got {inv_data_part['payment_state']}"
    assert inv_data_part['state'] == 'confirmed', "Invoice should remain confirmed on partial payment"
    assert inv_data_part['amount_paid'] == 404.0, f"Expected amount_paid 404.0, got {inv_data_part['amount_paid']}"
    assert inv_data_part['amount_residual'] == 1000.0, f"Expected residual 1000.0, got {inv_data_part['amount_residual']}"
    print(f"[PASS] Partial payment registered: Paid 404.0 -> Status: 'partial', Balance Due: {inv_data_part['amount_residual']}")

    # 9. Overpayment Rejection
    overpayment_blocked = False
    try:
        execute('subscription.invoice', 'action_register_payment', [inv_id], 2000.0, "OVERPAY-FAIL")
    except Exception:
        overpayment_blocked = True
    assert overpayment_blocked, "Overpayment should be rejected with exception!"
    print("[PASS] Overpayment guard verified: payment exceeding residual was properly rejected")

    # 10. Full Payment Settlement
    execute('subscription.invoice', 'action_register_payment', [inv_id], 1000.0, "STRIPE-LIVE-FINAL")
    inv_data_paid = execute('subscription.invoice', 'read', [inv_id], [
        'state', 'payment_state', 'amount_paid', 'amount_residual'
    ])[0]
    assert inv_data_paid['payment_state'] == 'paid', f"Expected paid payment status, got {inv_data_paid['payment_state']}"
    assert inv_data_paid['state'] == 'paid', f"Expected state 'paid', got {inv_data_paid['state']}"
    assert inv_data_paid['amount_paid'] == 1404.0, f"Expected total paid 1404.0, got {inv_data_paid['amount_paid']}"
    assert inv_data_paid['amount_residual'] == 0.0, f"Expected residual 0.0, got {inv_data_paid['amount_residual']}"
    print(f"[PASS] Full payment settlement verified: Invoice {inv_data['name']} fully paid and reconciled. State: 'paid'")

    # 11. Automated Recurring Billing Cron Execution
    cron_res = execute('subscription.subscription', 'cron_recurring_billing')
    print("[PASS] Cron automated recurring billing engine executed successfully via XML-RPC")

    print("\n" + "=" * 70)
    print("ALL 11 LIVE XML-RPC VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == '__main__':
    main()
