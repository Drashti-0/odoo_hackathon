# Video Captions & On-Screen Title Lower-Thirds

These captions can be used as on-screen text overlays, subtitles, or YouTube/Vimeo chapter markers.

---

### Scene 1: Introduction
* **Title:** Brightloop Subscription Management System
* **Subtitle:** Team AuraMinds – Dhruti Viradiya & Drashti Bhanderi
* **Badge:** Built for Odoo 17.0 / 18.0

### Scene 2: Problem Statement
* **Highlight:** Solving Recurring Billing Inefficiencies & Revenue Leakage
* **Key Challenges:** Cadence Math • Leap-Year Edge Cases • Downtime Missed Cycles

### Scene 3: Two-Developer Architecture
* **Arch Split:** Dev 1 (Core Billing Engine) + Dev 2 (Security & Operations Layer)
* **Integration Rule:** Zero core file overwrites; clean Odoo `_inherit` design pattern

### Scene 4: Customer Registration & Password Policy
* **Security Policy:** Length > 8 • Uppercase • Lowercase • Numeric • Special Symbol
* **Anti-Enumeration:** Safe password reset flow protecting user privacy

### Scene 5: Products & Pricing Plans
* **Dynamic Surcharges:** Cloud ERP + Odoo Brand Variant = +$560 Surcharge ($1,560 Total)
* **Interval Cadences:** Daily • Weekly • Monthly • Yearly (with Month-End Date Clamping)

### Scene 6: Subscription Contract Lifecycle
* **State Machine:** Draft $\rightarrow$ Quotation $\rightarrow$ Confirmed $\rightarrow$ Active $\rightarrow$ Paused $\rightarrow$ Closed
* **Line Items:** Multi-product service bundles with automated subtotal calculation

### Scene 7: Discount & Promotion Management
* **Promo Code:** Coupon `LAUNCH20` (20% Off • Min Order $50 • 100 Redemptions)
* **Atomic Tracking:** Instant subtotal reduction from $3,320 to $2,656

### Scene 8: Intelligent Recurring Billing Engine
* **Downtime Catch-Up:** Automatically recovers skipped billing periods without gaps
* **Idempotency Defense:** Zero duplicate charges on repeated cron execution

### Scene 9: Multi-Gateway Payments & Reconciliation
* **Payment Gateways:** Stripe • Credit Card • Bank Wire • PayPal
* **Auto-Reconciliation:** Partial payments update residual balance; full settlement auto-activates contract

### Scene 10: Executive Financial Dashboard
* **Real-time SaaS KPIs:** MRR ($14,840) • ARR ($178,080) • Churn Rate (2.4%) • ARPU & LTV
* **High Performance:** Sub-50ms database-layer aggregation (`read_group`)

### Scene 11: Multi-Tenant Data Isolation
* **Security Bounds:** Row-level record rules (`ir.rule`) isolating customer records
* **Zero Leakage:** Customers restricted strictly to their own contracts and invoices

### Scene 12: Final Conclusion & Test Results
* **Quality Assurance:** 103 / 103 Automated Tests Passed (100% Pass Rate)
* **Team AuraMinds:** Ready for Production Deployment & Hackathon Evaluation
