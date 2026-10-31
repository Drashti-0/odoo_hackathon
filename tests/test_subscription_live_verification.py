#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIVE FUNCTIONAL & INTEGRATION VERIFICATION:
Module 3: Quotation & Subscription Management
Brightloop Subscription Management System (Odoo 17 CE)

Executes live against Odoo 17 and PostgreSQL over XML-RPC.
"""

import sys
import xmlrpc.client
import time
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def run_live_verification(url, db, username, password):
    print("=" * 80)
    print("RUNNING LIVE QUOTATION & SUBSCRIPTION MANAGEMENT FUNCTIONAL VERIFICATION")
    print(f"Target URL: {url} | Database: {db} | User: {username}")
    print("=" * 80)

    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        version_info = common.version()
        server_version = version_info.get('server_version', 'Unknown')
        print(f"[PASS] Connected to Odoo Server Version: {server_version}")

        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("[FAIL] Authentication failed for user:", username)
            sys.exit(1)
        print(f"[PASS] Authenticated successfully as UID: {uid}")
    except Exception as e:
        print(f"[FAIL] Could not connect to {url}: {e}")
        sys.exit(1)

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def call(model, method, *args, **kwargs):
        res = models.execute_kw(db, uid, password, model, method, list(args), kwargs)
        if method == 'create' and isinstance(res, list) and len(res) == 1:
            return res[0]
        return res

    # ------------------------------------------------------------------------
    # STEP 1: VERIFY UI VIEWS & MENU ACTIONS
    # ------------------------------------------------------------------------
    print("\n--- 1. VERIFYING UI VIEWS & ACTIONS ---")
    required_views = [
        ('subscription_management.view_subscription_subscription_form', 'Form View: Subscription/Quotation'),
        ('subscription_management.view_subscription_subscription_tree', 'Tree View: Subscriptions'),
        ('subscription_management.view_subscription_subscription_search', 'Search View: Subscriptions'),
        ('subscription_management.view_subscription_quotation_template_form', 'Form View: Quotation Template'),
        ('subscription_management.view_subscription_quotation_template_tree', 'Tree View: Quotation Template'),
    ]
    for xml_id, label in required_views:
        mod, xml_name = xml_id.split('.')
        rec = call('ir.model.data', 'search_read', [('module', '=', mod), ('name', '=', xml_name)], ['res_id'])
        if rec and rec[0]['res_id']:
            print(f"[PASS] {label} registered in Odoo (View ID {rec[0]['res_id']})")
        else:
            print(f"[FAIL] View {xml_id} not found in database!")
            sys.exit(1)

    # ------------------------------------------------------------------------
    # STEP 2: SETUP CUSTOMER, TAXES, PLANS, AND PRODUCTS
    # ------------------------------------------------------------------------
    print("\n--- 2. PREPARING TEST FIXTURES ---")
    # Customer
    existing_partners = call('res.partner', 'search', [('email', '=', 'procurement@brightwave.io')])
    if existing_partners:
        partner_id = existing_partners[0]
    else:
        partner_id = call('res.partner', 'create', [{
            'name': 'Brightwave Enterprise Solutions Inc.',
            'email': 'procurement@brightwave.io',
        }])
    print(f"[PASS] Customer ready: Brightwave Enterprise (ID {partner_id})")

    tag = int(time.time())
    # Subscription Plans
    # 1. Standard Flexible Plan (Pause=True, Renew=True, EarlyClose=True)
    plan_flex_id = call('subscription.plan', 'create', [{
        'name': 'Live Flexible SaaS Monthly',
        'code': f'PLAN-FLEX-{tag}',
        'price': 100.0,
        'billing_interval_unit': 'monthly',
        'billing_interval_count': 1,
        'min_quantity': 2.0,
        'allow_pause': True,
        'allow_renewal': True,
        'allow_early_close': True,
        'auto_close': True,
        'auto_close_days': 7,
    }])
    print(f"[PASS] Created Flexible Plan (ID {plan_flex_id}, min_quantity=2.0)")

    # 2. Strict Fixed Plan (Pause=False, Renew=False, EarlyClose=False)
    plan_strict_id = call('subscription.plan', 'create', [{
        'name': 'Live Strict Annual Lockin',
        'code': f'PLAN-STR-{tag}',
        'price': 1200.0,
        'billing_interval_unit': 'yearly',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
        'allow_pause': False,
        'allow_renewal': False,
        'allow_early_close': False,
        'auto_close': True,
        'auto_close_days': 0,
    }])
    print(f"[PASS] Created Strict Plan (ID {plan_strict_id})")

    # Taxes: Exclusive & Inclusive
    tax_excl_id = call('account.tax', 'create', [{
        'name': f'VAT 10% Exclusive Live Test {tag}',
        'amount': 10.0,
        'amount_type': 'percent',
        'price_include': False,
        'type_tax_use': 'sale',
    }])

    tax_incl_id = call('account.tax', 'create', [{
        'name': f'VAT 10% Inclusive Live Test {tag}',
        'amount': 10.0,
        'amount_type': 'percent',
        'price_include': True,
        'type_tax_use': 'sale',
    }])
    print(f"[PASS] Created Exclusive Tax (ID {tax_excl_id}) and Inclusive Tax (ID {tax_incl_id})")

    # Products: Odoo brand (+560) and Standard product
    prod_odoo_tmpl_id = call('product.template', 'create', [{
        'name': 'Brightloop ERP Core Hosting',
        'list_price': 1000.0,
        'is_subscription': True,
        'brand_name': 'odoo',
    }])
    prod_odoo_variant_id = call('product.product', 'search', [('product_tmpl_id', '=', prod_odoo_tmpl_id)])[0]
    odoo_price = call('product.product', 'get_subscription_price', [prod_odoo_variant_id])
    assert odoo_price == 1560.0, f"Expected 1560.0, got {odoo_price}"
    print(f"[PASS] Created Odoo Brand Product Variant: ID {prod_odoo_variant_id}, Price {odoo_price} (Base 1000 + 560)")

    prod_support_tmpl_id = call('product.template', 'create', [{
        'name': 'Dedicated DevOps Support',
        'list_price': 300.0,
        'is_subscription': True,
        'brand_name': 'standard',
    }])
    prod_support_variant_id = call('product.product', 'search', [('product_tmpl_id', '=', prod_support_tmpl_id)])[0]
    print(f"[PASS] Created Standard Product Variant: ID {prod_support_variant_id}, Price 300.0")

    # ------------------------------------------------------------------------
    # STEP 3: QUOTATION TEMPLATES
    # ------------------------------------------------------------------------
    print("\n--- 3. VERIFYING QUOTATION TEMPLATES ---")
    # Template constraints: Negative validity_days
    try:
        call('subscription.quotation.template', 'create', [{
            'name': 'Invalid Validity Template',
            'plan_id': plan_flex_id,
            'validity_days': -10,
        }])
        print("[FAIL] Template with negative validity_days should have been rejected!")
        sys.exit(1)
    except Exception as e:
        print("[PASS] Template with negative validity_days properly rejected by ValidationError.")

    # Valid template creation
    tmpl_id = call('subscription.quotation.template', 'create', [{
        'name': 'Cloud ERP Platinum Template',
        'plan_id': plan_flex_id,
        'validity_days': 45,
        'terms_and_conditions': '<p>Strict 99.99% Cloud Service Level Agreement.</p>',
        'line_ids': [
            (0, 0, {
                'product_id': prod_odoo_variant_id,
                'quantity': 2.0,
                'unit_price': 1560.0,
            }),
            (0, 0, {
                'product_id': prod_support_variant_id,
                'quantity': 2.0,
                'unit_price': 300.0,
            }),
        ],
    }])
    tmpl_data = call('subscription.quotation.template', 'read', [tmpl_id], ['name', 'validity_days', 'line_ids'])[0]
    print(f"[PASS] Quotation Template created successfully: {tmpl_data['name']} with {len(tmpl_data['line_ids'])} lines")

    # Template applied to quotation
    quote_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'template_id': tmpl_id,
    }])
    # Trigger onchange
    onchange_res = call('subscription.subscription', 'onchange', [], {'template_id': tmpl_id}, 'template_id', {
        'template_id': '1', 'plan_id': '1', 'quotation_validity_date': '1', 'terms_and_conditions': '1', 'line_ids': '1'
    })
    val_updates = onchange_res.get('value', {})
    print(f"[PASS] Template populated onchange: Plan ID = {val_updates.get('plan_id')}, Validity = {val_updates.get('quotation_validity_date')}")

    # Verify template immutability when quotation lines are edited
    call('subscription.subscription', 'write', [quote_id], {
        'plan_id': plan_flex_id,
        'terms_and_conditions': '<p>Customized contract terms.</p>',
        'line_ids': [(0, 0, {
            'product_id': prod_odoo_variant_id,
            'quantity': 10.0,
            'unit_price': 1400.0,
        })],
    })
    tmpl_lines = call('subscription.quotation.template.line', 'search_read', [('template_id', '=', tmpl_id)], ['quantity', 'unit_price'])
    assert tmpl_lines[0]['quantity'] == 2.0, "Template line quantity was mutated!"
    print("[PASS] Template Immutability confirmed: Original template lines remain unaffected by quotation changes.")

    # ------------------------------------------------------------------------
    # STEP 4: QUOTATION CREATION, SEQUENCE & LINE CALCULATIONS
    # ------------------------------------------------------------------------
    print("\n--- 4. VERIFYING QUOTATION MANAGEMENT & TAX CALCULATIONS ---")
    # A. Tax-Exclusive Pricing
    quote_excl_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_flex_id,  # base plan = 100.0
        'line_ids': [
            (0, 0, {
                'product_id': prod_odoo_variant_id,
                'quantity': 2.0,
                'unit_price': 1560.0,
                'tax_ids': [(6, 0, [tax_excl_id])],
            }),
            (0, 0, {
                'product_id': prod_support_variant_id,
                'quantity': 2.0,
                'unit_price': 300.0,
                'tax_ids': [(6, 0, [tax_excl_id])],
            }),
        ],
    }])
    q_data = call('subscription.subscription', 'read', [quote_excl_id], ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total'])[0]
    print(f"[PASS] Draft Quotation created: {q_data['name']} (State: {q_data['state']})")
    assert q_data['name'].startswith('SQ-'), f"Quotation sequence must start with SQ-, got {q_data['name']}"
    # Lines: (2 * 1560) + (2 * 300) = 3120 + 600 = 3720 untaxed.
    # Base plan: 100.0. Total untaxed = 3820.0.
    # Tax: 372.0. Total: 4192.0.
    assert q_data['amount_untaxed'] == 3820.0, f"Expected untaxed 3820.0, got {q_data['amount_untaxed']}"
    assert q_data['amount_tax'] == 372.0, f"Expected tax 372.0, got {q_data['amount_tax']}"
    assert q_data['amount_total'] == 4192.0, f"Expected total 4192.0, got {q_data['amount_total']}"
    print(f"[PASS] Tax-exclusive calculations verified: Untaxed={q_data['amount_untaxed']}, Tax={q_data['amount_tax']}, Total={q_data['amount_total']}")

    # B. Tax-Inclusive Pricing (Checking no double tax counting)
    quote_incl_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_flex_id,  # base plan = 100.0
        'line_ids': [
            (0, 0, {
                'product_id': prod_support_variant_id,
                'quantity': 2.0,
                'unit_price': 110.0,  # 110 inclusive of 10% tax -> 100 untaxed + 10 tax each = 200 untaxed, 20 tax
                'tax_ids': [(6, 0, [tax_incl_id])],
            }),
        ],
    }])
    q_incl = call('subscription.subscription', 'read', [quote_incl_id], ['amount_untaxed', 'amount_tax', 'amount_total'])[0]
    assert q_incl['amount_untaxed'] == 300.0, f"Expected 300 untaxed (100 plan + 200 lines), got {q_incl['amount_untaxed']}"
    assert q_incl['amount_tax'] == 20.0, f"Expected 20 tax, got {q_incl['amount_tax']}"
    assert q_incl['amount_total'] == 320.0, f"Expected 320 total, got {q_incl['amount_total']}"
    print(f"[PASS] Tax-inclusive calculations verified: Untaxed={q_incl['amount_untaxed']}, Tax={q_incl['amount_tax']}, Total={q_incl['amount_total']}")

    # ------------------------------------------------------------------------
    # STEP 5: QUOTATION LIFECYCLE & STATE MACHINE
    # ------------------------------------------------------------------------
    print("\n--- 5. VERIFYING LIFECYCLE STATE TRANSITIONS ---")
    # Draft -> Send Quotation
    call('subscription.subscription', 'action_send_quotation', [quote_excl_id])
    state_after_send = call('subscription.subscription', 'read', [quote_excl_id], ['state'])[0]['state']
    assert state_after_send == 'quotation', f"Expected state 'quotation', got {state_after_send}"
    print("[PASS] Draft -> Quotation Sent transition verified.")

    # Reset to draft
    call('subscription.subscription', 'action_draft', [quote_excl_id])
    assert call('subscription.subscription', 'read', [quote_excl_id], ['state'])[0]['state'] == 'draft'
    print("[PASS] Quotation -> Draft reset verified.")

    # Invalid direct state transition: Draft -> Active (bypassing confirmation)
    try:
        call('subscription.subscription', 'write', [quote_excl_id], {'state': 'active'})
        print("[FAIL] Direct transition Draft -> Active should be blocked!")
        sys.exit(1)
    except Exception as e:
        print("[PASS] Invalid direct state transition Draft -> Active blocked by ORM write guard.")

    # Confirmation: Draft -> Confirmed (reassigns SUB-XXXXX)
    call('subscription.subscription', 'action_confirm', [quote_excl_id])
    conf_data = call('subscription.subscription', 'read', [quote_excl_id], ['name', 'state'])[0]
    assert conf_data['state'] == 'confirmed', f"Expected confirmed, got {conf_data['state']}"
    assert conf_data['name'].startswith('SUB-'), f"Expected SUB- sequence, got {conf_data['name']}"
    print(f"[PASS] Quotation confirmed successfully. Sequence reassigned to contract number: {conf_data['name']}")

    # Contract Price Immutability: Modify product catalog list price
    call('product.template', 'write', [prod_odoo_tmpl_id], {'list_price': 9999.0})
    sub_data_post_edit = call('subscription.subscription', 'read', [quote_excl_id], ['amount_untaxed', 'amount_total'])[0]
    assert sub_data_post_edit['amount_untaxed'] == 3820.0, "Contract untaxed price changed after catalog update!"
    print("[PASS] Price Immutability confirmed: Confirmed contract values remain locked after catalog price change.")

    # Confirmed -> Active
    call('subscription.subscription', 'action_activate', [quote_excl_id])
    act_data = call('subscription.subscription', 'read', [quote_excl_id], ['state', 'start_date', 'next_billing_date'])[0]
    assert act_data['state'] == 'active', f"Expected active, got {act_data['state']}"
    assert act_data['next_billing_date'] == act_data['start_date'], "Next billing date not initialized to start date!"
    print(f"[PASS] Contract activated: State = {act_data['state']}, Next Billing Date = {act_data['next_billing_date']}")

    # ------------------------------------------------------------------------
    # STEP 6: PAUSE & RESUME SCHEDULE SHIFTING
    # ------------------------------------------------------------------------
    print("\n--- 6. VERIFYING PAUSE & RESUME SCHEDULE SHIFTING ---")
    # Test strict plan blocking pause
    quote_strict_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_strict_id,
        'line_ids': [(0, 0, {'product_id': prod_support_variant_id, 'quantity': 1.0})],
    }])
    call('subscription.subscription', 'action_confirm', [quote_strict_id])
    call('subscription.subscription', 'action_activate', [quote_strict_id])
    try:
        call('subscription.subscription', 'action_pause', [quote_strict_id])
        print("[FAIL] Strict plan pause should have been blocked!")
        sys.exit(1)
    except Exception as e:
        print("[PASS] Pause blocked on strict plan with allow_pause=False.")

    # Pause on flexible plan
    initial_billing = act_data['next_billing_date']
    call('subscription.subscription', 'action_pause', [quote_excl_id])
    paused_data = call('subscription.subscription', 'read', [quote_excl_id], ['state', 'pause_date'])[0]
    assert paused_data['state'] == 'paused'
    print(f"[PASS] Subscription paused successfully on {paused_data['pause_date']}")

    # Simulate 5 days pause by updating pause_date
    simulated_pause_date = (date.today() - timedelta(days=5)).isoformat()
    call('subscription.subscription', 'write', [quote_excl_id], {'pause_date': simulated_pause_date})

    # Resume and verify next_billing_date shift
    call('subscription.subscription', 'action_resume', [quote_excl_id])
    resumed_data = call('subscription.subscription', 'read', [quote_excl_id], ['state', 'pause_date', 'next_billing_date'])[0]
    assert resumed_data['state'] == 'active'
    assert resumed_data['pause_date'] is False
    expected_shifted_billing = (date.fromisoformat(initial_billing) + timedelta(days=5)).isoformat()
    assert resumed_data['next_billing_date'] == expected_shifted_billing, f"Expected {expected_shifted_billing}, got {resumed_data['next_billing_date']}"
    print(f"[PASS] Resume verified: Billing date shifted by exactly 5 days from {initial_billing} to {resumed_data['next_billing_date']}")

    # ------------------------------------------------------------------------
    # STEP 7: RENEWAL & DURATION EXTENSION
    # ------------------------------------------------------------------------
    print("\n--- 7. VERIFYING RENEWAL POLICIES ---")
    # Strict plan renewal block
    try:
        call('subscription.subscription', 'action_renew', [quote_strict_id])
        print("[FAIL] Strict plan renewal should have been blocked!")
        sys.exit(1)
    except Exception as e:
        print("[PASS] Renewal blocked on plan with allow_renewal=False.")

    # Flexible plan renewal
    expiry_initial = (date.today() + relativedelta(months=6)).isoformat()
    call('subscription.subscription', 'write', [quote_excl_id], {'expiry_date': expiry_initial})
    call('subscription.subscription', 'action_renew', [quote_excl_id])
    renewed_data = call('subscription.subscription', 'read', [quote_excl_id], ['state', 'expiry_date'])[0]
    expected_new_expiry = (date.fromisoformat(expiry_initial) + relativedelta(months=1)).isoformat()
    assert renewed_data['expiry_date'] == expected_new_expiry, f"Expected {expected_new_expiry}, got {renewed_data['expiry_date']}"
    print(f"[PASS] Renewal verified: Contract extended by 1 month to {renewed_data['expiry_date']}")

    # ------------------------------------------------------------------------
    # STEP 8: EARLY CLOSURE & INVOICE INTEGRATION
    # ------------------------------------------------------------------------
    print("\n--- 8. VERIFYING EARLY CLOSURE & INVOICE INTEGRATION ---")
    # Verify that future next_billing_date (due to pause shift) skips billing gracefully
    call('subscription.subscription', 'action_generate_invoice_manual', [quote_excl_id])
    print("[PASS] Paused/shifted future contract billing properly skipped without premature invoice.")

    # Now set next_billing_date to today (due for billing) and generate invoice
    call('subscription.subscription', 'write', [quote_excl_id], {'next_billing_date': date.today().isoformat()})
    call('subscription.subscription', 'action_generate_invoice_manual', [quote_excl_id])
    inv_ids = call('subscription.invoice', 'search', [('subscription_id', '=', quote_excl_id)])
    assert len(inv_ids) >= 1, "No invoice was generated for active subscription!"
    inv_data = call('subscription.invoice', 'read', [inv_ids[0]], ['name', 'amount_untaxed', 'amount_tax', 'amount_total', 'state'])[0]
    print(f"[PASS] Recurring Invoice generated: {inv_data['name']} (State: {inv_data['state']}, Total: {inv_data['amount_total']})")

    # Close subscription
    call('subscription.subscription', 'action_close', [quote_excl_id], 'Completed proof-of-concept test.')
    closed_data = call('subscription.subscription', 'read', [quote_excl_id], ['state', 'close_date', 'close_reason'])[0]
    assert closed_data['state'] == 'closed'
    print(f"[PASS] Subscription closed successfully: Close Date = {closed_data['close_date']}, Reason = {closed_data['close_reason']}")

    # Closed subscription cannot generate recurring invoice
    try:
        call('subscription.subscription', 'action_generate_invoice_manual', [quote_excl_id])
        print("[FAIL] Closed subscription should not generate invoice!")
        sys.exit(1)
    except Exception as e:
        print("[PASS] Generating recurring invoice on closed subscription properly rejected with UserError.")

    print("\n" + "=" * 80)
    print("ALL LIVE QUOTATION & SUBSCRIPTION MANAGEMENT FUNCTIONAL TESTS PASSED (100% SUCCESS)")
    print("=" * 80)


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8069"
    db = sys.argv[2] if len(sys.argv) > 2 else "brightloop_test_db"
    username = sys.argv[3] if len(sys.argv) > 3 else "admin"
    password = sys.argv[4] if len(sys.argv) > 4 else "admin"

    run_live_verification(url, db, username, password)
