#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Integration and Functional Verification Script for Product & Variant Management (Module 1).
Connects to actual Odoo 17.0 instance over XML-RPC and validates:
- Product creation & template inheritance
- Product attributes and variant matrix generation
- Brand surcharge mandatory business logic (Odoo +560, Brightloop 0, Brand switching, Non-duplication)
- UI Views and Action registration
- Price constraints validation (negative price rejection)
- Product archiving
- Quotation/Subscription integration and contract price immutability
"""

import sys
import xmlrpc.client

def run_product_live_verification(host="http://localhost:8069", db="brightloop_test_db", user="admin", password="admin"):
    print("=" * 75)
    print("RUNNING LIVE PRODUCT & VARIANT MANAGEMENT FUNCTIONAL VERIFICATION")
    print(f"Target: {host} | Database: {db} | User: {user}")
    print("=" * 75)

    common = xmlrpc.client.ServerProxy(f"{host}/xmlrpc/2/common")
    try:
        ver = common.version()
        print(f"[PASS] Connected to Odoo Server: {ver.get('server_version')}")
    except Exception as e:
        print(f"[FAIL] Could not connect to {host}: {e}")
        return False

    uid = common.authenticate(db, user, password, {})
    if not uid:
        print("[FAIL] Authentication failed.")
        return False
    print(f"[PASS] Authenticated successfully as UID: {uid}")

    models = xmlrpc.client.ServerProxy(f"{host}/xmlrpc/2/object")
    def call(model, method, *args, **kwargs):
        res = models.execute_kw(db, uid, password, model, method, list(args), kwargs)
        if method == 'create' and isinstance(res, list) and len(res) == 1:
            return res[0]
        return res

    # -------------------------------------------------------------
    # 1. UI VIEW & ACTION VERIFICATION
    # -------------------------------------------------------------
    print("\n--- 1. VERIFYING UI VIEWS & MENU ACTIONS ---")
    expected_views = [
        'subscription_management.view_product_template_form_subscription',
        'subscription_management.view_product_template_tree_subscription',
        'subscription_management.view_product_product_tree_subscription',
        'subscription_management.view_product_template_search_subscription',
    ]
    for v_id in expected_views:
        mod, xml_name = v_id.split('.')
        view_rec = call('ir.model.data', 'search_read', [('module', '=', mod), ('name', '=', xml_name)], ['res_id', 'model'])
        if view_rec:
            print(f"[PASS] View registered in Odoo: {v_id} (ID {view_rec[0]['res_id']})")
        else:
            print(f"[FAIL] Missing view: {v_id}")
            return False

    expected_actions = [
        'subscription_management.action_subscription_products',
        'subscription_management.action_subscription_product_variants',
    ]
    for a_id in expected_actions:
        mod, xml_name = a_id.split('.')
        act_rec = call('ir.model.data', 'search_read', [('module', '=', mod), ('name', '=', xml_name)], ['res_id', 'model'])
        if act_rec:
            print(f"[PASS] Action registered in Odoo: {a_id} (ID {act_rec[0]['res_id']})")
        else:
            print(f"[FAIL] Missing action: {a_id}")
            return False

    # -------------------------------------------------------------
    # 2. BRAND SURCHARGE LOGIC (TESTS A, B, C, D)
    # -------------------------------------------------------------
    print("\n--- 2. VERIFYING BRAND SURCHARGE LOGIC ---")

    # TEST A: Base 1,000, Brand = Odoo -> Surcharge 560, Subscription Price 1,560
    tmpl_a_id = call('product.template', 'create', [{
        'name': 'Cloud ERP Hosting Suite',
        'detailed_type': 'service',
        'list_price': 1000.0,
        'standard_price': 400.0,
        'brand_name': 'odoo',
        'is_subscription': True,
    }])
    data_a = call('product.template', 'read', [tmpl_a_id], ['name', 'brand_name', 'brand_surcharge', 'subscription_price'])[0]
    assert data_a['brand_surcharge'] == 560.0, f"Expected surcharge 560.0, got {data_a['brand_surcharge']}"
    assert data_a['subscription_price'] == 1560.0, f"Expected subscription_price 1560.0, got {data_a['subscription_price']}"
    print(f"[PASS] Test A Passed: Odoo Brand -> Base ₹1,000 + Surcharge ₹560 = Final ₹{data_a['subscription_price']}")

    # Check Variant A
    var_a_ids = call('product.product', 'search_read', [('product_tmpl_id', '=', tmpl_a_id)], ['id', 'brand_name', 'brand_surcharge', 'subscription_price'])
    assert len(var_a_ids) >= 1
    var_a = var_a_ids[0]
    assert var_a['brand_surcharge'] == 560.0 and var_a['subscription_price'] == 1560.0
    print(f"[PASS] Variant A verified: Brand={var_a['brand_name']}, Surcharge=₹{var_a['brand_surcharge']}, Price=₹{var_a['subscription_price']}")

    # TEST B: Base 1,000, Brand = Brightloop -> Surcharge 0, Subscription Price 1,000
    tmpl_b_id = call('product.template', 'create', [{
        'name': 'Brightloop Workflow Manager',
        'detailed_type': 'service',
        'list_price': 1000.0,
        'standard_price': 400.0,
        'brand_name': 'brightloop',
        'is_subscription': True,
    }])
    data_b = call('product.template', 'read', [tmpl_b_id], ['name', 'brand_name', 'brand_surcharge', 'subscription_price'])[0]
    assert data_b['brand_surcharge'] == 0.0, f"Expected surcharge 0.0, got {data_b['brand_surcharge']}"
    assert data_b['subscription_price'] == 1000.0, f"Expected subscription_price 1000.0, got {data_b['subscription_price']}"
    print(f"[PASS] Test B Passed: Brightloop Brand -> Base ₹1,000 + Surcharge ₹0 = Final ₹{data_b['subscription_price']}")

    # TEST C: Change Brand from Odoo to Brightloop -> Surcharge removed
    call('product.template', 'write', [tmpl_a_id], {'brand_name': 'brightloop'})
    data_c = call('product.template', 'read', [tmpl_a_id], ['brand_name', 'brand_surcharge', 'subscription_price'])[0]
    assert data_c['brand_surcharge'] == 0.0, f"Expected 0.0 after switch, got {data_c['brand_surcharge']}"
    assert data_c['subscription_price'] == 1000.0, f"Expected 1000.0 after switch, got {data_c['subscription_price']}"
    var_c = call('product.product', 'read', [var_a['id']], ['brand_name', 'brand_surcharge', 'subscription_price'])[0]
    assert var_c['brand_surcharge'] == 0.0 and var_c['subscription_price'] == 1000.0
    print(f"[PASS] Test C Passed: Switched Brand to Brightloop -> Old surcharge removed (Price reverted to ₹1,000)")

    # Switch back to Odoo
    call('product.template', 'write', [tmpl_a_id], {'brand_name': 'odoo'})
    data_c2 = call('product.template', 'read', [tmpl_a_id], ['brand_surcharge', 'subscription_price'])[0]
    assert data_c2['brand_surcharge'] == 560.0 and data_c2['subscription_price'] == 1560.0
    print(f"[PASS] Test C (Re-Switch) Passed: Switched back to Odoo -> Surcharge ₹560 re-applied (Price ₹1,560)")

    # TEST D: Multiple Variants & Attributes (Surcharge not duplicated)
    attr_id = call('product.attribute', 'create', [{
        'name': 'Deployment Environment',
        'value_ids': [
            (0, 0, {'name': 'Shared Cloud'}),
            (0, 0, {'name': 'Dedicated High-Availability'}),
        ]
    }])
    attr_vals = call('product.attribute.value', 'search_read', [('attribute_id', '=', attr_id)], ['id', 'name'])
    val_shared = [v['id'] for v in attr_vals if v['name'] == 'Shared Cloud'][0]
    val_dedicated = [v['id'] for v in attr_vals if v['name'] == 'Dedicated High-Availability'][0]

    tmpl_d_id = call('product.template', 'create', [{
        'name': 'Enterprise Managed Infrastructure',
        'list_price': 1000.0,
        'brand_name': 'odoo',
        'is_subscription': True,
        'attribute_line_ids': [(0, 0, {
            'attribute_id': attr_id,
            'value_ids': [(6, 0, [val_shared, val_dedicated])],
        })]
    }])

    # Configure extra pricing on Dedicated variant (+600.0)
    ptav_ids = call('product.template.attribute.value', 'search_read', [('product_tmpl_id', '=', tmpl_d_id), ('product_attribute_value_id', '=', val_dedicated)], ['id'])
    if ptav_ids:
        call('product.template.attribute.value', 'write', [ptav_ids[0]['id']], {'price_extra': 600.0})

    # Read generated variants
    var_d_list = call('product.product', 'search_read', [('product_tmpl_id', '=', tmpl_d_id)], ['id', 'subscription_price', 'product_template_variant_value_ids'])
    assert len(var_d_list) == 2, f"Expected 2 variants, got {len(var_d_list)}"
    prices = sorted([v['subscription_price'] for v in var_d_list])
    # Variant 1: Base 1000 + Odoo 560 + Extra 0 = 1560
    # Variant 2: Base 1000 + Odoo 560 + Extra 600 = 2160
    assert prices[0] == 1560.0, f"Expected Variant 1 price 1560.0, got {prices[0]}"
    assert prices[1] == 2160.0, f"Expected Variant 2 price 2160.0, got {prices[1]}"
    print(f"[PASS] Test D Passed: Multiple variants generated correctly.")
    print(f"       Variant 1 (Shared Cloud): ₹{prices[0]} (Base 1,000 + Odoo 560 + Extra 0)")
    print(f"       Variant 2 (Dedicated HA): ₹{prices[1]} (Base 1,000 + Odoo 560 + Extra 600)")
    print(f"       No duplication: Exactly ₹560 Odoo surcharge on both variants.")

    # -------------------------------------------------------------
    # 3. CONSTRAINTS VALIDATION (NEGATIVE PRICE REJECTION)
    # -------------------------------------------------------------
    print("\n--- 3. VERIFYING PRICE CONSTRAINTS ---")
    neg_caught = False
    try:
        call('product.template', 'create', [{
            'name': 'Invalid Negative Price Item',
            'list_price': -500.0,
            'is_subscription': True,
        }])
    except Exception as e:
        neg_caught = True
        print(f"[PASS] Negative sales price properly rejected: {e}")
    assert neg_caught, "System should reject negative sales price"

    # -------------------------------------------------------------
    # 4. PRODUCT ARCHIVING & UNARCHIVING
    # -------------------------------------------------------------
    print("\n--- 4. VERIFYING PRODUCT ARCHIVING ---")
    call('product.template', 'write', [tmpl_a_id], {'active': False})
    state_archived = call('product.template', 'read', [tmpl_a_id], ['active'])[0]
    var_archived = call('product.product', 'read', [var_a['id']], ['active'])[0]
    assert not state_archived['active'] and not var_archived['active'], "Template and variant must be inactive"
    print(f"[PASS] Product archiving verified: Template active={state_archived['active']}, Variant active={var_archived['active']}")

    call('product.template', 'write', [tmpl_a_id], {'active': True})
    state_active = call('product.template', 'read', [tmpl_a_id], ['active'])[0]
    var_active = call('product.product', 'read', [var_a['id']], ['active'])[0]
    assert state_active['active'] and var_active['active'], "Template and variant must be active again"
    print(f"[PASS] Product unarchiving verified: Template active={state_active['active']}, Variant active={var_active['active']}")

    # -------------------------------------------------------------
    # 5. SUBSCRIPTION INTEGRATION & CONTRACT PRICE IMMUTABILITY
    # -------------------------------------------------------------
    print("\n--- 5. VERIFYING SUBSCRIPTION INTEGRATION & CONTRACT IMMUTABILITY ---")
    partner_id = call('res.partner', 'create', [{
        'name': 'Pinnacle Technologies Ltd',
        'email': 'accounts@pinnacletech.com',
    }])
    plan_id = call('subscription.plan', 'create', [{
        'name': 'Enterprise Platinum Plan',
        'price': 300.0,
        'billing_interval_unit': 'monthly',
        'billing_interval_count': 1,
        'min_quantity': 1.0,
    }])

    # Retrieve price through public API
    api_price = call('product.product', 'get_subscription_price', [var_a['id']])
    assert api_price == 1560.0, f"Expected get_subscription_price 1560.0, got {api_price}"
    print(f"[PASS] Public API product.get_subscription_price() returned ₹{api_price}")

    # Create quotation using this product variant
    sub_id = call('subscription.subscription', 'create', [{
        'partner_id': partner_id,
        'plan_id': plan_id,
        'line_ids': [(0, 0, {
            'product_id': var_a['id'],
            'name': 'Cloud ERP Hosting Suite',
            'quantity': 2.0,
            'unit_price': api_price,
        })],
    }])
    call('subscription.subscription', 'action_confirm', [sub_id])
    sub_rec = call('subscription.subscription', 'read', [sub_id], ['state', 'amount_untaxed'])[0]
    assert sub_rec['state'] == 'confirmed'
    # Plan 300 + 2 * 1560 = 3420.0
    assert sub_rec['amount_untaxed'] == 3420.0
    print(f"[PASS] Confirmed contract SUB total: ₹{sub_rec['amount_untaxed']} (Plan ₹300 + 2 * ₹1,560)")

    # Modifying the catalog template price to ₹2,500 must NOT alter confirmed contract lines
    call('product.template', 'write', [tmpl_a_id], {'list_price': 2500.0})
    new_cat_price = call('product.product', 'get_subscription_price', [var_a['id']])
    assert new_cat_price == 3060.0  # 2500 + 560
    sub_rec_after = call('subscription.subscription', 'read', [sub_id], ['amount_untaxed'])[0]
    assert sub_rec_after['amount_untaxed'] == 3420.0, "Confirmed contract financial values mutated unexpectedly!"
    print(f"[PASS] Contract Price Immutability verified: Catalog price increased to ₹{new_cat_price}, but confirmed contract line remains locked at original ₹1,560 (Total ₹{sub_rec_after['amount_untaxed']}).")

    print("\n" + "=" * 75)
    print("ALL LIVE PRODUCT & VARIANT MANAGEMENT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75)
    return True


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8069"
    db = sys.argv[2] if len(sys.argv) > 2 else "brightloop_test_db"
    user = sys.argv[3] if len(sys.argv) > 3 else "admin"
    password = sys.argv[4] if len(sys.argv) > 4 else "admin"

    success = run_product_live_verification(host, db, user, password)
    sys.exit(0 if success else 1)
