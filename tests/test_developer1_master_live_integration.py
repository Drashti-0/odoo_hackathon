#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master End-to-End Live Integration Verification Script for Developer 1 Modules
Brightloop Software - Odoo Subscription Management System
Target: Odoo 17.0 CE (http://localhost:8069) | PostgreSQL 16 (brightloop_test_db)
Author: Team AuraMinds (Developer 1 Lead)
"""

import sys
import xmlrpc.client
from datetime import date, datetime, timedelta

ODOO_URL = "http://localhost:8069"
DB_NAME = "brightloop_test_db"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

def main():
    print("=" * 80)
    print("MASTER LIVE E2E INTEGRATION TEST SUITE: DEVELOPER 1 MODULES")
    print(f"Target Server: {ODOO_URL} | Database: {DB_NAME}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 0: CONNECT & AUTHENTICATE
    # -------------------------------------------------------------------------
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    try:
        ver = common.version()
        print(f"[OK] Connected to Odoo Server Version: {ver.get('server_version')}")
        uid = common.authenticate(DB_NAME, ADMIN_USER, ADMIN_PASS, {})
        if not uid:
            print("[FAIL] Authentication failed for user 'admin'")
            sys.exit(1)
        print(f"[OK] Authenticated successfully as admin (UID: {uid})")
    except Exception as e:
        print(f"[FAIL] Could not connect to Odoo XML-RPC: {e}")
        sys.exit(1)

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    def call(model, method, *args, **kwargs):
        return models.execute_kw(DB_NAME, uid, ADMIN_PASS, model, method, list(args), kwargs)

    today = date.today().isoformat()
    test_run_tag = datetime.now().strftime("%H%M%S")

    # =========================================================================
    # WORKFLOW 1: PRODUCT & PRODUCT VARIANT INTEGRATION
    # =========================================================================
    print("\n" + "-" * 70)
    print("WORKFLOW 1: PRODUCT & PRODUCT VARIANT INTEGRATION")
    print("-" * 70)

    # 1.1 Create Product Attribute & Values for Variants
    attr_id = call('product.attribute', 'create', {'name': f'Master RAM Tier {test_run_tag}'})
    val_16_id = call('product.attribute.value', 'create', {'name': '16 GB ECC', 'attribute_id': attr_id})
    val_64_id = call('product.attribute.value', 'create', {'name': '64 GB ECC', 'attribute_id': attr_id})

    # 1.2 Create Product Template with 'odoo' Brand (+560.0 Surcharge)
    tmpl_odoo_id = call('product.template', 'create', {
        'name': f'Cloud Server Enterprise {test_run_tag}',
        'list_price': 1500.0,
        'standard_price': 800.0,
        'is_subscription': True,
        'brand_name': 'odoo',
        'attribute_line_ids': [(0, 0, {
            'attribute_id': attr_id,
            'value_ids': [(6, 0, [val_16_id, val_64_id])],
        })],
    })

    # Add variant price extra for 64GB (+400.0)
    ptav_ids = call('product.template.attribute.value', 'search_read', [
        ('product_tmpl_id', '=', tmpl_odoo_id),
        ('product_attribute_value_id', '=', val_64_id),
    ], ['id'])
    if ptav_ids:
        call('product.template.attribute.value', 'write', [ptav_ids[0]['id']], {'price_extra': 400.0})

    # Read Template Pricing
    tmpl_odoo = call('product.template', 'read', [tmpl_odoo_id], ['brand_surcharge', 'subscription_price'])[0]
    assert tmpl_odoo['brand_surcharge'] == 560.0, f"Expected 560.0 brand surcharge, got {tmpl_odoo['brand_surcharge']}"
    assert tmpl_odoo['subscription_price'] == 2060.0, f"Expected 2060.0 (1500 + 560), got {tmpl_odoo['subscription_price']}"
    print(f"[PASS] Product Template verified: Base = 1500.0 | Brand Surcharge = +{tmpl_odoo['brand_surcharge']} | Price = {tmpl_odoo['subscription_price']}")

    # 1.3 Verify Variants Pricing
    variant_ids = call('product.product', 'search_read', [('product_tmpl_id', '=', tmpl_odoo_id)], [
        'id', 'brand_surcharge', 'subscription_price', 'product_template_variant_value_ids'
    ])
    assert len(variant_ids) == 2, f"Expected 2 variants, got {len(variant_ids)}"
    for var in variant_ids:
        # Check pricing: 1500 base + 560 surcharge + extra
        if var['subscription_price'] == 2060.0:
            var_16_id = var['id']
            print(f"       Variant 16GB RAM: ID {var['id']} | Surcharge = +560.0 | Price = {var['subscription_price']}")
        elif var['subscription_price'] == 2460.0:
            var_64_id = var['id']
            print(f"       Variant 64GB RAM: ID {var['id']} | Surcharge = +560.0 + 400 Extra | Price = {var['subscription_price']}")
        else:
            raise AssertionError(f"Unexpected variant price: {var}")
    print("[PASS] Product Variants pricing verified with additive surcharges.")

    # 1.4 Standard Edition (Zero Surcharge)
    tmpl_std_id = call('product.template', 'create', {
        'name': f'Cloud Storage Backup {test_run_tag}',
        'list_price': 300.0,
        'is_subscription': True,
        'brand_name': 'standard',
    })
    tmpl_std = call('product.template', 'read', [tmpl_std_id], ['brand_surcharge', 'subscription_price'])[0]
    assert tmpl_std['brand_surcharge'] == 0.0, "Standard brand surcharge must be 0.0"
    assert tmpl_std['subscription_price'] == 300.0, "Standard price must equal list price"
    var_std_id = call('product.product', 'search', [('product_tmpl_id', '=', tmpl_std_id)], limit=1)[0]
    print(f"[PASS] Standard Brand Product verified: Zero surcharge | Price = {tmpl_std['subscription_price']}")

    # 1.5 Price Constraint Validation (Negative price blocked)
    neg_blocked = False
    try:
        call('product.template', 'create', {'name': 'Negative Test', 'list_price': -100.0, 'is_subscription': True})
    except Exception:
        neg_blocked = True
    assert neg_blocked, "Negative product price should be blocked by ValidationError!"
    print("[PASS] Product price validation verified: negative price correctly rejected.")

    # =========================================================================
    # WORKFLOW 2: SUBSCRIPTION PLAN INTEGRATION
    # =========================================================================
    print("\n" + "-" * 70)
    print("WORKFLOW 2: SUBSCRIPTION PLAN INTEGRATION")
    print("-" * 70)

    # 2.1 Create Subscription Plans across all 4 cadences
    plan_daily_id = call('subscription.plan', 'create', {
        'name': f'Master Daily Plan {test_run_tag}',
        'code': f'PLAN-DAY-{test_run_tag}',
        'price': 40.0,
        'billing_interval_unit': 'daily',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
    })
    plan_weekly_id = call('subscription.plan', 'create', {
        'name': f'Master Weekly Plan {test_run_tag}',
        'code': f'PLAN-WKL-{test_run_tag}',
        'price': 150.0,
        'billing_interval_unit': 'weekly',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
    })
    plan_monthly_id = call('subscription.plan', 'create', {
        'name': f'Master Monthly Plan {test_run_tag}',
        'code': f'PLAN-MTH-{test_run_tag}',
        'price': 400.0,
        'billing_interval_unit': 'monthly',
        'billing_interval_count': 1,
        'min_quantity': 2.0,
        'allow_pause': True,
        'allow_renewal': True,
        'allow_early_close': True,
        'auto_close': True,
        'auto_close_days': 5,
    })
    plan_yearly_id = call('subscription.plan', 'create', {
        'name': f'Master Annual Plan {test_run_tag}',
        'code': f'PLAN-YRL-{test_run_tag}',
        'price': 4500.0,
        'billing_interval_unit': 'yearly',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
    })
    print("[PASS] Created 4 Subscription Plans (Daily, Weekly, Monthly, Yearly).")

    # 2.2 Cadence Date Calculations via RPC
    test_date = "2026-01-31"
    next_day = call('subscription.plan', 'calculate_next_billing_date', [plan_daily_id], test_date)
    assert next_day == "2026-02-01", f"Daily calculation error: {next_day}"

    next_wk = call('subscription.plan', 'calculate_next_billing_date', [plan_weekly_id], test_date)
    assert next_wk == "2026-02-07", f"Weekly calculation error: {next_wk}"

    # Month-end clamping: Jan 31 -> Feb 28
    next_mth = call('subscription.plan', 'calculate_next_billing_date', [plan_monthly_id], test_date)
    assert next_mth == "2026-02-28", f"Month-end clamping error: expected 2026-02-28, got {next_mth}"

    next_yr = call('subscription.plan', 'calculate_next_billing_date', [plan_yearly_id], test_date)
    assert next_yr == "2027-01-31", f"Yearly calculation error: {next_yr}"
    print(f"[PASS] Plan date calculation & month-end clamping verified: Jan 31 -> Feb 28 -> {next_mth}")

    # 2.3 Link Product Template to Plan
    call('product.template', 'write', [tmpl_odoo_id], {'subscription_plan_ids': [(6, 0, [plan_monthly_id])]})
    linked_plans = call('product.template', 'read', [tmpl_odoo_id], ['subscription_plan_ids'])[0]['subscription_plan_ids']
    assert plan_monthly_id in linked_plans, "Plan not linked to product template!"
    print("[PASS] Linked Subscription Plan to Product Template successfully.")

    # =========================================================================
    # WORKFLOW 3: QUOTATION & SUBSCRIPTION LIFECYCLE
    # =========================================================================
    print("\n" + "-" * 70)
    print("WORKFLOW 3: QUOTATION & SUBSCRIPTION LIFECYCLE")
    print("-" * 70)

    # 3.1 Create Customer
    client_id = call('res.partner', 'create', {
        'name': f'Global Client Corp {test_run_tag}',
        'email': f'billing_{test_run_tag}@globalclient.com',
    })

    # 3.2 Minimum Quantity Validation Check
    min_qty_blocked = False
    try:
        call('subscription.subscription', 'create', {
            'partner_id': client_id,
            'plan_id': plan_monthly_id,  # min_quantity = 2.0
            'start_date': today,
            'line_ids': [(0, 0, {'product_id': var_16_id, 'quantity': 1.0, 'unit_price': 2060.0})],
        })
    except Exception:
        min_qty_blocked = True
    assert min_qty_blocked, "Minimum quantity violation was not blocked!"
    print("[PASS] Plan minimum quantity constraint enforced: quantity 1.0 (< 2.0) rejected.")

    # 3.3 Create Valid Quotation (state = 'draft', sequence = 'SQ-XXXXX')
    sub_id = call('subscription.subscription', 'create', {
        'partner_id': client_id,
        'plan_id': plan_monthly_id,
        'start_date': today,
        'line_ids': [
            (0, 0, {
                'product_id': var_64_id,
                'quantity': 2.0,
                'unit_price': 2460.0,
            }),
            (0, 0, {
                'product_id': var_std_id,
                'quantity': 2.0,
                'unit_price': 300.0,
            }),
        ],
    })
    sub_data = call('subscription.subscription', 'read', [sub_id], [
        'name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total'
    ])[0]
    assert sub_data['state'] == 'draft', f"Expected draft, got {sub_data['state']}"
    assert sub_data['name'].startswith('SQ-'), f"Expected SQ- sequence, got {sub_data['name']}"
    # Untaxed = Plan (400) + Line 1 (2 * 2460 = 4920) + Line 2 (2 * 300 = 600) = 5920.0
    assert sub_data['amount_untaxed'] == 5920.0, f"Expected 5920.0, got {sub_data['amount_untaxed']}"
    print(f"[PASS] Quotation created: {sub_data['name']} (State: {sub_data['state']}, Total: {sub_data['amount_total']})")

    # 3.4 Confirm Quotation -> Transitions to 'confirmed', assigns 'SUB-XXXXX' contract number
    call('subscription.subscription', 'action_confirm', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['name', 'state'])[0]
    assert sub_data['state'] == 'confirmed', f"Expected confirmed, got {sub_data['state']}"
    assert sub_data['name'].startswith('SUB-'), f"Expected SUB- sequence, got {sub_data['name']}"
    print(f"[PASS] Quotation confirmed. Generated contract: {sub_data['name']} (State: {sub_data['state']})")

    # 3.5 Price Immutability after confirmation:
    # Update catalog list_price from 1500 to 5000; verify contract amounts remain 5920.0
    call('product.template', 'write', [tmpl_odoo_id], {'list_price': 5000.0})
    sub_data_immut = call('subscription.subscription', 'read', [sub_id], ['amount_untaxed'])[0]
    assert sub_data_immut['amount_untaxed'] == 5920.0, f"Confirmed contract amounts changed! Expected 5920.0, got {sub_data_immut['amount_untaxed']}"
    print(f"[PASS] Price immutability verified: catalog price change did not alter contract amounts ({sub_data_immut['amount_untaxed']}).")

    # 3.6 Activate Contract -> State 'active', initializes next_billing_date
    call('subscription.subscription', 'action_activate', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['state', 'next_billing_date', 'start_date'])[0]
    assert sub_data['state'] == 'active', f"Expected active, got {sub_data['state']}"
    assert sub_data['next_billing_date'] == today, f"Expected next_billing_date = {today}, got {sub_data['next_billing_date']}"
    print(f"[PASS] Contract activated: State: {sub_data['state']} | Next Billing Date: {sub_data['next_billing_date']}")

    # 3.7 Pause and Resume Lifecycle
    call('subscription.subscription', 'action_pause', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['state', 'pause_date'])[0]
    assert sub_data['state'] == 'paused', f"Expected paused, got {sub_data['state']}"
    assert sub_data['pause_date'] == today, f"Expected pause_date {today}, got {sub_data['pause_date']}"

    call('subscription.subscription', 'action_resume', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['state', 'pause_date'])[0]
    assert sub_data['state'] == 'active', f"Expected active, got {sub_data['state']}"
    assert sub_data['pause_date'] is False, "pause_date should be cleared on resume"
    print(f"[PASS] Pause & Resume verified: Active -> Paused ({today}) -> Resumed (Active)")

    # =========================================================================
    # WORKFLOW 4: INVOICE & AUTOMATED BILLING INTEGRATION
    # =========================================================================
    print("\n" + "-" * 70)
    print("WORKFLOW 4: INVOICE & AUTOMATED BILLING INTEGRATION")
    print("-" * 70)

    # 4.1 Generate Recurring Invoice Manually from Active Subscription
    call('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['invoice_ids', 'invoice_count', 'next_billing_date', 'last_billing_date'])[0]
    assert sub_data['invoice_count'] == 1, f"Expected 1 invoice, got {sub_data['invoice_count']}"
    inv_id = sub_data['invoice_ids'][0]

    # Verify Invoice Fields
    inv_data = call('subscription.invoice', 'read', [inv_id], [
        'name', 'state', 'partner_id', 'subscription_id', 'amount_untaxed', 'amount_total',
        'amount_paid', 'amount_residual', 'payment_state', 'billing_period_start', 'billing_period_end', 'line_ids'
    ])[0]
    assert inv_data['state'] == 'confirmed', f"Expected invoice state confirmed, got {inv_data['state']}"
    assert inv_data['partner_id'][0] == client_id, "Invoice partner mismatch!"
    assert inv_data['subscription_id'][0] == sub_id, "Invoice subscription linkage mismatch!"
    assert inv_data['amount_untaxed'] == 5920.0, f"Expected 5920.0 untaxed, got {inv_data['amount_untaxed']}"
    assert inv_data['amount_total'] == 5920.0, f"Expected 5920.0 total, got {inv_data['amount_total']}"
    assert inv_data['amount_residual'] == 5920.0, f"Expected 5920.0 residual, got {inv_data['amount_residual']}"
    assert inv_data['payment_state'] == 'not_paid'
    print(f"[PASS] Generated Recurring Invoice: {inv_data['name']} (State: {inv_data['state']}, Total: {inv_data['amount_total']}, Residual: {inv_data['amount_residual']})")

    # Verify Invoice Lines breakdown (Base plan line + 2 product lines)
    inv_lines = call('subscription.invoice.line', 'read', inv_data['line_ids'], ['name', 'quantity', 'unit_price', 'price_subtotal'])
    assert len(inv_lines) == 3, f"Expected 3 invoice lines (1 plan fee + 2 product lines), got {len(inv_lines)}"
    for line in inv_lines:
        print(f"       Line: {line['name'][:45]}... | Qty: {line['quantity']} | Unit: {line['unit_price']} | Subtotal: {line['price_subtotal']}")
    print("[PASS] Invoice line itemization verified with base plan fee and product variant prices.")

    # 4.2 Verify Next Billing Date Milestone Advance
    expected_next = call('subscription.plan', 'calculate_next_billing_date', [plan_monthly_id], today)
    assert sub_data['next_billing_date'] == expected_next, f"Expected next billing {expected_next}, got {sub_data['next_billing_date']}"
    assert sub_data['last_billing_date'] == today, f"Expected last billing {today}, got {sub_data['last_billing_date']}"
    print(f"[PASS] Billing schedule milestones advanced: Last = {sub_data['last_billing_date']} | Next = {sub_data['next_billing_date']}")

    # 4.3 Idempotency & Duplicate Invoice Prevention Check
    initial_inv_count = sub_data['invoice_count']
    # Attempt duplicate generation on same period
    call('subscription.subscription', 'write', [sub_id], {'next_billing_date': today})
    call('subscription.subscription', 'action_generate_invoice_manual', [sub_id])
    sub_data_post = call('subscription.subscription', 'read', [sub_id], ['invoice_count'])[0]
    assert sub_data_post['invoice_count'] == initial_inv_count, f"Duplicate invoice created! Count changed: {sub_data_post['invoice_count']}"
    print(f"[PASS] Idempotency confirmed: repeated generation skipped duplicate (Count = {sub_data_post['invoice_count']}).")

    # 4.4 Billing Audit Log Verification
    log_ids = call('subscription.billing.log', 'search_read', [('subscription_id', '=', sub_id)], ['status', 'message', 'amount'])
    assert len(log_ids) >= 2, f"Expected at least 2 logs, got {len(log_ids)}"
    statuses = [l['status'] for l in log_ids]
    assert 'success' in statuses, "Missing success log!"
    assert 'skipped' in statuses, "Missing skipped idempotency log!"
    print(f"[PASS] Billing Audit Trail verified: Found {len(log_ids)} log records (Statuses: {statuses})")

    # 4.5 Cron Scheduled Action Execution
    call('subscription.subscription', 'cron_recurring_billing')
    print("[PASS] Automated Recurring Billing Cron executed safely via RPC.")

    # =========================================================================
    # WORKFLOW 5: CROSS-MODULE END-TO-END WORKFLOW & DEVELOPER 2 HOOKS
    # =========================================================================
    print("\n" + "-" * 70)
    print("WORKFLOW 5: CROSS-MODULE INTEGRATION & DEV 2 HOOKS")
    print("-" * 70)

    # 5.1 Create Coupon for Developer 2 Discount Hook
    coupon_id = call('subscription.discount', 'search', [('code', '=', 'MASTER10')], limit=1)
    if not coupon_id:
        coupon_id = [call('subscription.discount', 'create', {
            'name': 'Master 10% Discount Coupon',
            'code': 'MASTER10',
            'discount_type': 'percentage',
            'value': 10.0,
            'active': True,
        })]
    coupon_id = coupon_id[0]

    # Reset invoice to draft for coupon application per Developer 2 contract
    call('subscription.invoice', 'action_draft', [inv_id])
    inv_data = call('subscription.invoice', 'read', [inv_id], ['state'])[0]
    assert inv_data['state'] == 'draft', f"Expected draft, got {inv_data['state']}"

    # Apply Coupon Hook
    call('subscription.invoice', 'apply_discount_code', [inv_id], 'MASTER10')
    inv_data = call('subscription.invoice', 'read', [inv_id], [
        'discount_code', 'amount_discount', 'amount_total', 'amount_residual'
    ])[0]
    assert inv_data['discount_code'] == 'MASTER10'
    assert inv_data['amount_discount'] == 592.0, f"Expected discount 592.0 (10% of 5920), got {inv_data['amount_discount']}"
    assert inv_data['amount_total'] == 5328.0, f"Expected total 5328.0, got {inv_data['amount_total']}"
    assert inv_data['amount_residual'] == 5328.0, f"Expected residual 5328.0, got {inv_data['amount_residual']}"
    print(f"[PASS] Developer 2 Discount Hook verified: Applied MASTER10 -> -{inv_data['amount_discount']} deducted. Total: {inv_data['amount_total']}")

    # Re-confirm Invoice
    call('subscription.invoice', 'action_confirm', [inv_id])
    inv_data = call('subscription.invoice', 'read', [inv_id], ['state'])[0]
    assert inv_data['state'] == 'confirmed'

    # 5.2 Developer 2 Payment Settlement Hook (Partial Payment)
    call('subscription.invoice', 'action_register_payment', [inv_id], 2328.0, "STRIPE-TX-PARTIAL")
    inv_data = call('subscription.invoice', 'read', [inv_id], [
        'state', 'payment_state', 'amount_paid', 'amount_residual'
    ])[0]
    assert inv_data['payment_state'] == 'partial', f"Expected partial, got {inv_data['payment_state']}"
    assert inv_data['state'] == 'confirmed', "Invoice should remain confirmed on partial payment"
    assert inv_data['amount_paid'] == 2328.0, f"Expected amount_paid 2328.0, got {inv_data['amount_paid']}"
    assert inv_data['amount_residual'] == 3000.0, f"Expected residual 3000.0, got {inv_data['amount_residual']}"
    print(f"[PASS] Partial payment registered: Paid 2328.0 -> Status: 'partial', Outstanding Balance: {inv_data['amount_residual']}")

    # 5.3 Overpayment Guard Verification
    overpay_blocked = False
    try:
        call('subscription.invoice', 'action_register_payment', [inv_id], 5000.0, "STRIPE-OVERPAY")
    except Exception:
        overpay_blocked = True
    assert overpay_blocked, "Overpayment exceeding residual balance was not blocked!"
    print("[PASS] Overpayment guard verified: payment exceeding residual balance (3000.0) rejected.")

    # 5.4 Final Payment Settlement Hook
    call('subscription.invoice', 'action_register_payment', [inv_id], 3000.0, "STRIPE-TX-FINAL")
    inv_data = call('subscription.invoice', 'read', [inv_id], [
        'state', 'payment_state', 'amount_paid', 'amount_residual'
    ])[0]
    assert inv_data['payment_state'] == 'paid', f"Expected paid, got {inv_data['payment_state']}"
    assert inv_data['state'] == 'paid', f"Expected state paid, got {inv_data['state']}"
    assert inv_data['amount_paid'] == 5328.0, f"Expected total paid 5328.0, got {inv_data['amount_paid']}"
    assert inv_data['amount_residual'] == 0.0, f"Expected residual 0.0, got {inv_data['amount_residual']}"
    print(f"[PASS] Final payment settlement verified: Invoice {inv_data} fully paid and reconciled. State: 'paid'")

    # 5.5 Renewal and Contract Termination
    call('subscription.subscription', 'action_renew', [sub_id])
    sub_data = call('subscription.subscription', 'read', [sub_id], ['expiry_date'])[0]
    print(f"[PASS] Subscription renewal verified: Contract extended to {sub_data['expiry_date']}")

    call('subscription.subscription', 'action_close', [sub_id], "End-to-End Test Completed")
    sub_data = call('subscription.subscription', 'read', [sub_id], ['state', 'close_date', 'close_reason'])[0]
    assert sub_data['state'] == 'closed', f"Expected closed, got {sub_data['state']}"
    print(f"[PASS] Subscription lifecycle closure verified: State = {sub_data['state']}, Reason = '{sub_data['close_reason']}'")

    print("\n" + "=" * 80)
    print("ALL 5 END-TO-END WORKFLOW INTEGRATION TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == '__main__':
    main()
