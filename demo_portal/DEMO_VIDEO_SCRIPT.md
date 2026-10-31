# Brightloop Subscription Management System — Demo Video Script
**Team:** AuraMinds (Developer 1: Dhruti | Developer 2: Drashti)  
**Target Duration:** 2:30 – 3:00 Minutes  
**Presentation Interface:** `demo_portal/index.html` (Local Browser)  
**Underlying Platform:** Odoo 17.0 Community Edition

> **Transparency & Architecture Note:**  
> This demonstration uses the standalone, presentation-ready SaaS interface (`demo_portal/index.html`) running local sample data. The actual production models, accounting workflows, security record rules, and cron schedulers are implemented in the native Odoo addon `subscription_management`.

---

## Video Outline & Timing Summary

| Scene | Timestamp | Topic / Feature Focus | Target Screen |
|---|---|---|---|
| **Scene 1** | 0:00 – 0:20 | Opening & Problem Overview | Sign In (`screen_login`) |
| **Scene 2** | 0:20 – 0:45 | Authentication, Security & Password Policy | Sign In & Signup (`screen_signup`) |
| **Scene 3** | 0:45 – 1:15 | Executive Dashboard & Financial Intelligence | Admin Dashboard (`screen_admin_dashboard`) |
| **Scene 4** | 1:15 – 1:40 | Product Surcharges & Subscription Plans | Products & Plans (`screen_product_mgmt`, `screen_plan_mgmt`) |
| **Scene 5** | 1:40 – 2:10 | Contract Lifecycle, Discounts & Invoicing | Subscriptions & Invoices (`screen_subscription_mgmt`, `screen_invoice_mgmt`) |
| **Scene 6** | 2:10 – 2:40 | Multi-Gateway Payments & Customer Portal | Payments & Customer Portal (`screen_payment_mgmt`, `screen_customer_portal`) |
| **Scene 7** | 2:40 – 3:00 | Session Security & Closing | Logout & Sign In |

---

## Scene-by-Scene Walkthrough

### Scene 1: Opening & Problem Overview (0:00 – 0:20)
* **Screen:** Standalone Sign In Page (`screen_login`).
* **Visual Action:** 
  - Show the clean Brightloop logo, header, and the active `Odoo 17.0 Engine Live` badge.
  - Hover cursor over the pre-filled demo role buttons (`Admin`, `Staff`, `Alice`).
* **Spoken Narration (Natural English):**
  > "Hello everyone, and welcome. We are Team AuraMinds, presenting the Subscription Management System built for Brightloop Software.
  > Recurring subscription businesses often struggle with fragmented billing, manual invoice reconciliation, and complex pricing tiers.
  > Today, we're demonstrating an integrated, modern SaaS solution that automates subscription lifecycles from contract creation to multi-gateway payment reconciliation."

---

### Scene 2: Authentication, Security & Password Policy (0:20 – 0:45)
* **Screen:** Sign In (`screen_login`) & Customer Registration (`screen_signup`).
* **Visual Action:**
  1. Click the **"Create Account"** link at the bottom of the login card.
  2. Type a short sample password into the password box to show the **live password strength meter** (displays amber warning: *"Use 8+ characters, upper and lowercase, a number, and a symbol"*).
  3. Click **"Back to Sign In"**.
  4. Click the quick **"Admin"** pill button to populate `admin@brightloop.com` and `admin123`.
  5. Click the eye icon to demonstrate the **Show/Hide password** toggle.
  6. Click **"Sign In to Brightloop"**.
* **Spoken Narration:**
  > "Security starts at authentication. Our portal enforces strict password complexity policies requiring uppercase, lowercase, numbers, and symbols.
  > For this demo, we'll sign in using our pre-configured Administrator account.
  > Notice the smooth transition straight into the executive console."

---

### Scene 3: Executive Financial Dashboard (0:45 – 1:15)
* **Screen:** Admin Dashboard (`screen_admin_dashboard`) & Financial Analytics (`screen_financial_reports`).
* **Visual Action:**
  1. Hover over the **5 core KPI cards**: Active Subscriptions (12), Normalized MRR ($14,840.00), ARR ($178,080.00), Outstanding Receivables, and Low Monthly Churn (2.4%).
  2. Scroll slightly to display the interactive **Chart.js MRR Growth curve** and the **Plan Distribution doughnut chart**.
  3. Click **"Financial Analytics"** on the left sidebar to reveal ARPU ($1,236.67), Lifetime Value (LTV), and Net Revenue Retention (114.5%).
* **Spoken Narration:**
  > "As an Administrator, we get real-time executive visibility. 
  > The system automatically normalizes all subscription cadences into Monthly Recurring Revenue and Annual Run Rate.
  > With built-in cohort analytics, Brightloop executives can track expansion revenue, customer churn, and outstanding invoice balances at a glance."

---

### Scene 4: Products with Surcharges & Billing Cadences (1:15 – 1:40)
* **Screen:** Products (`screen_product_mgmt`) & Subscription Plans (`screen_plan_mgmt`).
* **Visual Action:**
  1. Click **"Products & Variants"** in the sidebar. Highlight the *Cloud ERP Dedicated Hosting* card, showing the Base List Price ($1,000.00) + the mandatory **Odoo Brand Edition Surcharge (+ $560.00)** for a total calculated price of $1,560.00.
  2. Click **"Subscription Plans"** in the sidebar. Highlight the 4 cadences: Daily Trial, Weekly Starter, Monthly Pro, and Annual Enterprise.
* **Spoken Narration:**
  > "In the catalog, Brightloop can configure products with edition-based surcharges, such as dedicated Odoo variant add-ons.
  > Our subscription plans support daily, weekly, monthly, and yearly intervals, complete with automated grace periods and February leap-year clamping."

---

### Scene 5: Contract Lifecycle, Discounts & Invoicing (1:40 – 2:10)
* **Screen:** Subscriptions (`screen_subscription_mgmt`) & Invoices (`screen_invoice_mgmt`).
* **Visual Action:**
  1. Click **"Subscriptions"** in the sidebar.
  2. In the search box, type `Alice` to show instantaneous client-side table filtering. Clear the search.
  3. Click **"Pause"** on contract `SUB-2026-001`, then click **"Resume"** to show instant state transition feedback.
  4. Click the top navbar button **"Run Billing Cron"** to demonstrate automated recurring billing execution (toast notification pops up).
  5. Click **"Recurring Invoices"** in the sidebar to review generated invoices, showing `INV-2026-001` (Fully Paid) and `INV-2026-002` (Partially Paid with residual balance).
* **Spoken Narration:**
  > "Subscriptions progress through a formal state machine: from Draft, to Quotation, Confirmed, Active, Paused, and Closed.
  > With a single click or scheduled cron, our automated recurring engine generates tax invoices while applying active promo codes like LAUNCH20.
  > Outstanding residuals are automatically tracked until full settlement."

---

### Scene 6: Payments Hub & Customer Self-Service Portal (2:10 – 2:40)
* **Screen:** Payments (`screen_payment_mgmt`) & Customer Portal (`screen_customer_portal`).
* **Visual Action:**
  1. Click **"Payments & Settled"** to display multi-gateway reconciliation (Stripe, Credit Card, Bank Wire).
  2. In the top navbar, click the role switcher button **"Portal Alice"**.
  3. Notice how the view instantly restricts to Alice Customer's multi-tenant isolated portal (`screen_customer_dashboard` / `screen_customer_portal`).
  4. Point out Alice's active contract, lifetime savings ($664.00), and click **"Download demo receipt"**.
* **Spoken Narration:**
  > "Payment settlements integrate with multiple gateways, including Stripe, Credit Cards, and Direct Bank Transfers.
  > When we switch to Alice's customer view, multi-tenant security strictly isolates her data.
  > Alice can review her active cloud services, monitor her promo savings, and download payment receipts on demand."

---

### Scene 7: Session Security & Closing (2:40 – 3:00)
* **Screen:** Top Header & Return to Sign In (`screen_login`).
* **Visual Action:**
  1. Click the **"Logout"** button in the top right navbar.
  2. Show that the application shell cleanly hides and returns directly to the Sign In screen.
* **Spoken Narration:**
  > "Clicking Logout securely clears the session and returns the user to the Sign In page.
  > This completes our demonstration of the Subscription Management System for Brightloop Software.
  > Thank you from Team AuraMinds!"

---

## Practical Recording Tips for the Presenter

1. **Resolution & Scaling:** Set browser zoom to 90% or 100% on a standard 1080p display for ideal card spacing.
2. **Smooth Cursor Motion:** Pause for half a second after each click before speaking to let viewers digest each screen change.
3. **Pacing:** Speak calmly and naturally; the script is structured for 130–140 words per minute.
4. **Local Launch Command:**
   ```powershell
   Start-Process "c:\Users\Bhanderi Drashti\OneDrive\Desktop\ODOO_Hackathon\odoo_hackathon\demo_portal\index.html"
   ```
