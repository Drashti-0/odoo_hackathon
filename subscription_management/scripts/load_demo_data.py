"""Load synthetic Brightloop demo records from an Odoo shell session."""

from odoo import fields

DEMO_MODULE = "subscription_management"
demo_env = env
data_model = demo_env["ir.model.data"].sudo()


def xmlid_record(xmlid, model_name):
    data = data_model.search(
        [("module", "=", DEMO_MODULE), ("name", "=", xmlid)],
        limit=1,
    )
    if data:
        if data.model != model_name:
            raise RuntimeError(
                f"Demo XML ID {DEMO_MODULE}.{xmlid} points to {data.model}, "
                f"expected {model_name}."
            )
        record = demo_env[model_name].browse(data.res_id).exists()
        if not record:
            raise RuntimeError(
                f"Demo XML ID {DEMO_MODULE}.{xmlid} points to a missing record."
            )
        return record
    return demo_env[model_name].browse()


def link_xmlid(xmlid, record):
    data = data_model.search(
        [("module", "=", DEMO_MODULE), ("name", "=", xmlid)],
        limit=1,
    )
    if data:
        if data.model != record._name or data.res_id != record.id:
            raise RuntimeError(
                f"Demo XML ID {DEMO_MODULE}.{xmlid} points to a different record."
            )
        return
    data_model.create(
        {
            "module": DEMO_MODULE,
            "name": xmlid,
            "model": record._name,
            "res_id": record.id,
            "noupdate": True,
        }
    )


def demo_record(xmlid, model_name, values):
    record = xmlid_record(xmlid, model_name)
    if record:
        return record
    record = demo_env[model_name].sudo().create(values)
    link_xmlid(xmlid, record)
    return record


module = demo_env["ir.module.module"].sudo().search(
    [("name", "=", DEMO_MODULE), ("state", "=", "installed")],
    limit=1,
)
if not module:
    raise RuntimeError(
        "Install the subscription_management addon before loading demo data."
    )

customers_data = [
    (
        "northstar", "Northstar Analytics", "accounts@northstar.example.test",
        "202-555-0101", True,
    ),
    (
        "pinecone", "Pinecone Cloud Services", "hello@pinecone.example.test",
        "202-555-0102", True,
    ),
    (
        "beacon", "Beacon Retail Group", "it@beacon.example.test",
        "202-555-0103", True,
    ),
    (
        "summit", "Summit Health Systems", "subscriptions@summit.example.test",
        "202-555-0104", True,
    ),
    (
        "elena", "Elena Rossi", "elena.rossi@example.test",
        "202-555-0105", False,
    ),
]
customers = {
    key: demo_record(
        f"demo_customer_{key}",
        "res.partner",
        {
            "name": name,
            "email": email,
            "is_company": is_company,
            "phone": phone,
        },
    )
    for key, name, email, phone, is_company in customers_data
}

products_data = [
    (
        "crm", "Brightloop CRM Team", "BL-DEMO-CRM", 129.0,
        "Shared customer workspace and sales pipeline for growing teams.",
    ),
    (
        "automation", "Brightloop Workflow Automation", "BL-DEMO-AUTO", 249.0,
        "Automated approvals and integrations for recurring business processes.",
    ),
    (
        "insights", "Brightloop Data Insights", "BL-DEMO-DATA", 399.0,
        "Hosted analytics, dashboards, and scheduled reporting.",
    ),
    (
        "storage", "Brightloop Secure Cloud Storage", "BL-DEMO-STORAGE", 89.0,
        "Managed encrypted storage with version history and access controls.",
    ),
    (
        "support", "Brightloop Priority Support", "BL-DEMO-SUPPORT", 149.0,
        "Priority technical support with a dedicated response queue.",
    ),
]
products = {
    key: demo_record(
        f"demo_product_{key}",
        "product.template",
        {
            "name": name,
            "default_code": default_code,
            "type": "service",
            "sale_ok": True,
            "purchase_ok": False,
            "is_subscription": True,
            "brand_name": "brightloop",
            "list_price": price,
            "description_sale": description,
        },
    ).product_variant_id
    for key, name, default_code, price, description in products_data
}

plans_data = [
    ("monthly", "Brightloop Monthly", "BL-DEMO-MONTHLY", 1, "monthly", 99.0),
    ("quarterly", "Brightloop Quarterly", "BL-DEMO-QUARTERLY", 3, "monthly", 269.0),
    ("yearly", "Brightloop Yearly", "BL-DEMO-YEARLY", 1, "yearly", 999.0),
]
plans = {
    key: demo_record(
        f"demo_plan_{key}",
        "subscription.plan",
        {
            "name": name,
            "code": code,
            "sequence": sequence,
            "billing_interval_count": interval_count,
            "billing_interval_unit": interval_unit,
            "price": price,
            "min_quantity": 1.0,
            "allow_pause": True,
            "allow_renewal": True,
            "auto_close": True,
        },
    )
    for sequence, (key, name, code, interval_count, interval_unit, price)
    in enumerate(plans_data, start=10)
}

subscriptions_data = [
    ("northstar", "monthly", "crm", "active"),
    ("pinecone", "quarterly", "automation", "quotation"),
    ("beacon", "yearly", "insights", "quotation"),
    ("summit", "monthly", "storage", "quotation"),
    ("elena", "yearly", "support", "quotation"),
]
subscriptions = {}
for customer_key, plan_key, product_key, target_state in subscriptions_data:
    customer = customers[customer_key]
    plan = plans[plan_key]
    product = products[product_key]
    xmlid = f"demo_subscription_{customer_key}"
    subscription = demo_record(
        xmlid,
        "subscription.subscription",
        {
            "partner_id": customer.id,
            "plan_id": plan.id,
            "start_date": fields.Date.today(),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": product.display_name,
                        "quantity": 1.0,
                        "unit_price": product.get_subscription_price(plan=plan),
                    },
                )
            ],
            "terms_and_conditions": (
                "<p>Demo terms: recurring service access, subject to the selected "
                "plan and its billing cadence.</p>"
            ),
        },
    )
    subscriptions[customer_key] = subscription

    if target_state == "quotation":
        if subscription.state == "draft":
            subscription.action_send_quotation()
        elif subscription.state != "quotation":
            raise RuntimeError(
                f"Expected {subscription.name} to remain a quotation; "
                f"found state {subscription.state!r}."
            )
        continue

    if subscription.state == "draft":
        subscription.action_send_quotation()
    if subscription.state == "quotation":
        subscription.action_confirm()
    if subscription.state == "confirmed":
        subscription.action_activate()
    if subscription.state != "active":
        raise RuntimeError(
            f"Expected {subscription.name} to be active; "
            f"found state {subscription.state!r}."
        )
    if not subscription.invoice_ids:
        subscription.action_generate_invoice_manual()
    if not subscription.invoice_ids:
        raise RuntimeError(
            f"The billing action did not generate an invoice for {subscription.name}."
        )

    invoice = subscription.invoice_ids.sorted("id")[0]
    link_xmlid("demo_invoice_northstar", invoice)

print("Brightloop demo data is ready.")
print(f"Customers: {len(customers)}")
print(f"Subscription products: {len(products)}")
print(f"Plans: {len(plans)}")
print(
    "Subscriptions: "
    f"{sum(record.state == 'quotation' for record in subscriptions.values())} quotations, "
    f"{sum(record.state == 'active' for record in subscriptions.values())} active"
)
for subscription in subscriptions.values():
    print(
        f"{subscription.name}: {subscription.partner_id.display_name} | "
        f"{subscription.plan_id.display_name} | {subscription.state} | "
        f"next billing: {subscription.next_billing_date or 'not scheduled'}"
    )
for invoice in subscriptions["northstar"].invoice_ids:
    print(
        f"Generated invoice: {invoice.name} | {invoice.state} | "
        f"{invoice.payment_state} | total {invoice.amount_total:.2f} "
        f"{invoice.currency_id.name}"
    )
demo_env.cr.commit()
