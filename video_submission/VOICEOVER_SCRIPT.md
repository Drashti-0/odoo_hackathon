# Voiceover Narration Script: Natural & Conversational English

**Instructions for Speaker:**  
- Speak clearly at a moderate, confident pace (approx. 130 words per minute).
- Pause slightly (1 second) between bullet points as you switch tabs on screen.

---

### Scene 1: Introduction (0:00 – 0:20)
> *"Hello judges! Welcome to Brightloop Software's Subscription Management System, proudly engineered by Team AuraMinds: Dhruti Viradiya and Drashti Bhanderi. Built natively for Odoo 17 and 18, our platform automates the entire recurring subscription lifecycle—from quotation to intelligent billing, payment settlement, and real-time financial reporting."*

---

### Scene 2: Problem Statement (0:20 – 0:45)
> *"Modern SaaS and cloud service businesses need more than static one-time invoices. They need flexible recurring cadences, protection against billing server downtime, coupon engines that don't compound calculation errors, and instant multi-gateway payment reconciliation. Without automation, companies suffer from revenue leakage, missed billing periods, and messy accounting spreadsheets."*

---

### Scene 3: Architecture & Engineering Strategy (0:45 – 1:10)
> *"To ensure enterprise stability, our team established a strict integration contract. Developer 1, Dhruti, engineered the Core Engine: product variant surcharges, plan cadences, the contract lifecycle state machine, and the recurring billing cron. Developer 2, Drashti, delivered the Operations Layer: authentication, password hardening, promotional discount rules, multi-gateway payments, and executive dashboards. Every extension was achieved cleanly using Odoo class inheritance, with zero destructive edits to core files."*

---

### Scene 4: Customer Registration & Security (1:10 – 1:35)
> *"Security begins at onboarding. Here on our portal registration screen, our custom policy enforces strict password complexity: passwords must exceed eight characters and contain uppercase letters, lowercase letters, numbers, and special symbols. Notice how weak passwords are immediately rejected, while valid credentials safely create customer accounts with automated portal role assignment."*

---

### Scene 5: Products & Pricing Plans (1:35 – 2:00)
> *"In our service catalog, products support automated brand-tier surcharges. For example, our Cloud ERP Dedicated Hosting automatically adds a mandatory five-hundred-and-sixty dollar surcharge when the Odoo edition variant is selected, bringing the price to fifteen-sixty. Under Subscription Plans, we support daily, weekly, monthly, and annual intervals with trial periods, grace periods, and built-in calendar clamping for month-end dates."*

---

### Scene 6: Subscription Lifecycle (2:00 – 2:25)
> *"Subscribing a customer follows an audited state machine. Contracts transition smoothly from Draft to Quotation, then to Confirmed and Active. Here, contract SUB-2026-001 includes two enterprise hosting instances and our monthly base plan, computing an initial untaxed subtotal of thirty-three hundred and twenty dollars."*

---

### Scene 7: Discount Management (2:25 – 2:45)
> *"Next, we apply our promotional engine. Our coupon code LAUNCH20 validates date availability, minimum purchase requirements, and maximum usage caps. Applying the coupon deducts twenty percent—a six-hundred-and-sixty-four dollar saving—lowering the order balance to twenty-six hundred and fifty-six dollars, while atomically updating our redemption counter."*

---

### Scene 8: Intelligent Recurring Billing Engine (2:45 – 3:10)
> *"When billing day arrives, our automated cron engine generates recurring invoices automatically. What sets our engine apart is its Catch-Up Downtime Recovery: if the billing server goes offline for multiple cycles, it generates all missed invoices sequentially without gaps. Strict idempotency guarantees that repeated cron executions will never create duplicate charges."*

---

### Scene 9: Multi-Gateway Payments & Reconciliation (3:10 – 3:35)
> *"Invoicing seamlessly reconciles with our payment hub across Stripe, credit cards, and bank wire. Watch as we register a partial payment of one thousand dollars via credit card: the invoice residual balance drops to sixteen-fifty-six and marks the status as Partially Paid. Once the remaining balance is settled via Stripe, the invoice transitions to Fully Paid, automatically activating the subscription."*

---

### Scene 10: Executive Financial Dashboard (3:35 – 4:00)
> *"For company executives, our financial dashboard aggregates business intelligence in real time using database-layer read_group queries in under fifty milliseconds. In one unified view, leadership tracks normalized Monthly Recurring Revenue, Annual Recurring Revenue, active subscribers, collections aging, and customer churn rate."*

---

### Scene 11: Multi-Tenant Data Isolation (4:00 – 4:20)
> *"Customer privacy is strictly protected. Switching to our customer portal for Alice Customer, row-level record rules ensure Alice sees only her own contracts and payment receipts. Competitor records and executive financial reports are completely inaccessible, preventing cross-tenant data leaks."*

---

### Scene 12: Conclusion & Verification (4:20 – 4:40)
> *"Finally, quality assurance is proven with a flawless one-hundred percent pass rate across one-hundred-and-three automated unit and integration tests. On behalf of Team AuraMinds—Dhruti Viradiya and Drashti Bhanderi—thank you for watching our presentation!"*
