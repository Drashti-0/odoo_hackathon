# Video Demonstration Storyboard: 12-Scene Sequence

**Project:** Brightloop Subscription Management System  
**Team:** AuraMinds (Dhruti Viradiya & Drashti Bhanderi)  
**Estimated Video Duration:** 4 Minutes 30 Seconds  

---

| Scene # | Scene Title | Screen / Page to Open | On-Screen Actions & Highlights | Est. Duration |
|:---:|---|---|---|:---:|
| **Scene 1** | **Project Introduction & Team AuraMinds** | Admin Dashboard (`demo_portal/index.html`) | • Display full-screen executive dashboard.<br>• Point cursor to team badge: "Team AuraMinds (Dhruti & Drashti)".<br>• Show Odoo 17.0 compatibility indicator. | **20s** |
| **Scene 2** | **Problem Statement & Business Need** | Slide / Dashboard Overview | • Highlight recurring billing challenges: complex cadences, month-end clamping, downtime recovery, and multi-gateway payments. | **25s** |
| **Scene 3** | **Architecture & Integration Contract** | Architecture diagram (`docs/SYSTEM_ARCHITECTURE.md`) | • Present two-developer architectural split: Developer 1 Core vs. Developer 2 Operations.<br>• Highlight non-invasive hooks (`discount_hook.py`, `payment_hook.py`). | **25s** |
| **Scene 4** | **Customer Registration & Strong Password Policy** | Auth & Signup Demo Screen | • Demonstrate strong password validator.<br>• Type weak password ("weak") $\rightarrow$ show failure message.<br>• Type "EmmaStrongPass2026!" $\rightarrow$ show green checkmark and complete signup. | **25s** |
| **Scene 5** | **Products & Subscription Plans** | Products & Plans Screens | • Show "Cloud ERP Dedicated Hosting" with automatic **+$560 Odoo brand surcharge** ($1,000 + 560 = $1,560).<br>• Show Daily, Weekly, Monthly, and Annual cadences. | **25s** |
| **Scene 6** | **Subscription Contract Lifecycle** | Subscriptions Screen | • Walk through state machine: Draft $\rightarrow$ Quotation $\rightarrow$ Confirmed $\rightarrow$ Active.<br>• Highlight contract `SUB-2026-001` with line items. | **25s** |
| **Scene 7** | **Promotional Discount Application** | Discounts Screen & Contract View | • Show coupon `LAUNCH20` (20% off, min subtotal $50, usage cap 100).<br>• Show automatic deduction of $664.00 from $3,320.00 subtotal (Net: $2,656.00). | **20s** |
| **Scene 8** | **Recurring Billing Engine & Catch-Up Logic** | Invoices Screen & Cron Trigger | • Click "Run Billing Cron" button.<br>• Show automatic recurring invoice generation (`INV-2026-001`).<br>• Explain catch-up recovery and idempotency defense against duplicates. | **25s** |
| **Scene 9** | **Payment Settlement & Invoice Reconciliation** | Payments & Invoices Screens | • Show partial payment of $1,000 via Credit Card $\rightarrow$ residual drops to $1,656 (State: Partially Paid).<br>• Show final payment of $1,656 via Stripe $\rightarrow$ residual becomes $0.00 (State: Fully Paid). | **25s** |
| **Scene 10** | **Admin Financial Dashboard & Real-Time KPIs** | Executive Financial Dashboard | • Highlight 5 core KPI cards: Active Subscriptions (12), MRR ($14,840), ARR ($178,080), Outstanding ($3,420), Churn Rate (2.4%).<br>• Show interactive MRR growth line chart and plan distribution doughnut chart. | **25s** |
| **Scene 11** | **Multi-Tenant Security & Customer Isolation** | Customer Portal Screen | • Click Role Switcher $\rightarrow$ switch to "Portal Alice".<br>• Verify Alice can ONLY see her own contract and zero invoices from Bob.<br>• Point out that Alice cannot view the Admin Financial Dashboard. | **20s** |
| **Scene 12** | **Conclusion & Verification Results** | Terminal / Summary View | • Show terminal running test suites: **103/103 tests passed (100%)**.<br>• Closing remarks thanking the jury on behalf of Team AuraMinds. | **20s** |
