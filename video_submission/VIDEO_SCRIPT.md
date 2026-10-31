# Video Presentation Script: Brightloop Subscription Management System

**Team Name:** AuraMinds  
**Authors:** Developer 1 (Dhruti Viradiya - Core Engine) & Developer 2 (Drashti Bhanderi - Operations & Analytics)  
**Hackathon Target:** Odoo Subscription & Intelligent Recurring Billing Hackathon  
**Target Video Duration:** 4 to 5 Minutes  

---

## I. Executive Introduction & Team Presentation (0:00 – 0:30)

* **Visual:** Open on Brightloop Executive Dashboard with live KPI metric cards and charts.
* **Speaker:** "Hello judges and evaluators! We are **Team AuraMinds**—comprising Dhruti Viradiya and Drashti Bhanderi. Today, we are proud to present our enterprise-grade **Subscription Management System** engineered natively for **Odoo 17.0 and 18.0** for **Brightloop Software**."

---

## II. The Problem Statement (0:30 – 1:00)

* **Visual:** Screen highlighting the challenges of recurring billing (cadences, leap-years, downtime, multi-gateways).
* **Speaker:** "As modern software and service companies transition from one-off transactions to recurring business models, standard ERP billing workflows struggle. Traditional systems lack native automation for daily, weekly, monthly, and yearly recurring intervals; they fail to handle calendar edge cases like February month-end clamping; and most critically, if a billing server goes offline, missed billing periods are either skipped or compounded with duplicate charges. Furthermore, companies need promotional coupon engines, partial payment reconciliation across Stripe and wire transfers, and strict multi-tenant customer isolation."

---

## III. System Architecture & Two-Developer Engineering Split (1:00 – 1:30)

* **Visual:** Architectural diagram showing Core Engine vs. Operations Layer.
* **Speaker:** "To build an enterprise-resilient platform, Team AuraMinds established a strict architectural Integration Contract:
  * **Developer 1 (Dhruti Viradiya)** built the Core Domain Engine: product templates with brand variant surcharges, subscription plan cadences, the contract lifecycle state machine, and an intelligent automated recurring billing engine with catch-up logic.
  * **Developer 2 (Drashti Bhanderi)** delivered the Operations & Governance Layer: multi-role security authentication, password complexity policies, discount promotional rules, multi-gateway payment reconciliation, and real-time database-aggregated SaaS metrics.
  * All extensions adhere to clean Odoo class inheritance without a single destructive edit to core files."

---

## IV. Feature Walkthrough: Authentication & Customer Registration (1:30 – 2:00)

* **Visual:** Switch to Customer Signup screen; demonstrate password policy validation and successful portal registration.
* **Speaker:** "Let's begin with user access. Our system implements a strict 3-tier security hierarchy: Subscription Customer, Operational Staff, and Administrator. During customer registration, our custom constraint validates password complexity requiring over 8 characters, uppercase, lowercase, numeric digits, and special characters. We also enforce case-insensitive duplicate prevention and anti-enumeration security on password resets."

---

## V. Catalog & Plan Cadence Engine (2:00 – 2:30)

* **Visual:** Navigate to Products & Variants; highlight Odoo brand +560 surcharge, then switch to Subscription Plans.
* **Speaker:** "Next, in our product catalog, we support variant-based surcharges. For instance, our Cloud ERP Hosting includes an automated 560-dollar brand surcharge for Odoo edition deployments. Under Subscription Plans, we support Daily, Weekly, Monthly, and Yearly intervals with configurable trial periods, grace periods, auto-renewals, and built-in calendar clamping—ensuring that a subscription billed on January 31st clamps cleanly to February 28th."

---

## VI. Contract Lifecycle & Promotional Discounts (2:30 – 3:00)

* **Visual:** Subscription Management Screen; show Draft $\rightarrow$ Quotation $\rightarrow$ Confirmed $\rightarrow$ Active transition and apply coupon `LAUNCH20`.
* **Speaker:** "Creating a subscription follows a robust state machine. We quote a contract, confirm it, and activate it. Here, we apply our promotional discount engine: coupon code `LAUNCH20` validates date availability, minimum purchase amounts, and usage caps, automatically deducting 20% off the untaxed subtotal while atomically tracking usage."

---

## VII. Recurring Billing Engine & Catch-Up Logic (3:00 – 3:30)

* **Visual:** Trigger Billing Cron; show invoice generation with audit logs.
* **Speaker:** "Our recurring billing engine is fully automated via an Odoo cron job. What makes it intelligent is its **Catch-Up Downtime Recovery**: if the cron is offline for multiple cycles, it generates every missed invoice sequentially without leaving gaps. Furthermore, strict idempotency ensures that repeated runs never generate duplicate invoices for the same billing window."

---

## VIII. Multi-Gateway Payment Reconciliation & Auto-Activation (3:30 – 4:00)

* **Visual:** Invoices & Payments screen; register partial credit card payment of $1,000, then settle remaining balance via Stripe.
* **Speaker:** "When an invoice is issued, our payment management module reconciles transactions across credit cards, bank wire, Stripe, and PayPal. Here, we register a partial payment of 1,000 dollars—the invoice immediately updates its residual balance to Partially Paid. When the remaining balance is settled via Stripe, the invoice transitions to Fully Paid, automatically triggering subscription contract activation."

---

## IX. Executive Financial Dashboard & Analytics (4:00 – 4:30)

* **Visual:** Admin Financial Dashboard; demonstrate MRR, ARR, Churn Rate %, ARPU, and LTV.
* **Speaker:** "For executive decision-makers, our financial dashboard computes real-time SaaS metrics using database-level `read_group` aggregation in under 50 milliseconds. It calculates normalized Monthly Recurring Revenue across different cadences, Annual Recurring Revenue, customer churn rate, Average Revenue Per User, and Customer Lifetime Value."

---

## X. Multi-Tenant Security & Verification Suite (4:30 – 5:00)

* **Visual:** Switch role to Portal Customer Alice; show that Bob's contracts are invisible. Terminal showing 103/103 tests passed.
* **Speaker:** "Security is paramount. Row-level multi-tenant record rules ensure that portal customers can only view their own contracts and invoices, completely blocking cross-customer access and restricting portal users from financial reports. Finally, our automated test suite boasts a **100% pass rate across 103 unit, integration, and standalone test cases**. 

Thank you for your time, and we look forward to your questions!"
