# Brightloop Software — 2–3 Minute Demo Script

## Before recording

- Open `demo_portal/index.html` in a browser with internet access for CDN-hosted styles, icons, and charts.
- This is a standalone browser simulation. It does not authenticate with Odoo or contact payment providers.
- Demo sign-in credentials appear on the login screen. Use the `admin@brightloop.com` demo account first, then `alice@customer.com` for the customer view.
- The UI may retain local demo changes between visits. Use the seeded sample records; avoid entering real customer information.

## Recording sequence (about 2 minutes 40 seconds)

### 0:00–0:20 — Sign in and frame the demo

**On screen:** Sign In page; use the Admin quick sign-in.

**Narration:** “This is Brightloop Software’s subscription-management demo by Team AuraMinds. The screen explicitly identifies authentication and data as a local simulation; this recording does not imply a live Odoo connection.”

### 0:20–0:45 — Dashboard and reports

**On screen:** Admin Dashboard, then Financial Analytics.

**Narration:** “The dashboard summarizes the sample subscriptions, invoices, and recorded payments. The charts are rendered from this browser’s demo data and update as we perform the next actions.”

### 0:45–1:25 — Coupon, subscription, and lifecycle

**On screen:** Subscriptions → Create Subscription. Select Alice, the Monthly Professional plan, and coupon `LAUNCH20`; save. Pause and resume the new subscription.

**Narration:** “I’m creating a sample monthly subscription and applying the seeded 20-percent coupon. The demo calculates the amount locally, then lets us pause and resume the subscription. These actions change only the browser’s local demo records.”

### 1:25–1:55 — Invoice and payment simulation

**On screen:** Generate an invoice from the subscription. Open Payments or use the invoice’s payment action. Show the invoice total and the simulated payment method.

**Narration:** “The invoice shown here is a local sample record, not an Odoo accounting move. The payment form rejects an amount above the remaining balance. Recording the correct amount updates this demo invoice and payment history; no card, bank, Stripe, or PayPal transaction occurs.”

### 1:55–2:25 — Customer portal view

**On screen:** Log out; sign in as the Alice demo customer; open Customer Dashboard and Customer Portal.

**Narration:** “Now we’re viewing the customer persona. The standalone UI filters the sample subscription and invoice lists to Alice’s demo records. This is a presentation behavior, not a server-enforced access-control test.”

### 2:25–2:40 — Close

**On screen:** Return to sign-in; briefly show the demo-only notice.

**Narration:** “This recording demonstrates the standalone interface only. The Odoo addon, portal routes, database access rules, scheduled billing, and accounting behavior still need live Odoo 17 verification.”
