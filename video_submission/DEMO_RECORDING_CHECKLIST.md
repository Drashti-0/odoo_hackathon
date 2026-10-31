# Step-by-Step Demo Recording Guide & Checklist

Follow this checklist to record your final 4–5 minute hackathon presentation video smoothly and within your 1-hour window.

---

## 1. Recording Setup & Preparation (5 Minutes)

- [ ] **Open Demo Portal in Browser:**
  - File Location: `demo_portal/index.html` (Double-click or open directly in Google Chrome / Microsoft Edge).
  - Press `F11` in Chrome/Edge to enter Clean Full-Screen presentation mode.
- [ ] **Screen Recording Software:**
  - Recommended free tools: **OBS Studio**, **Windows Game Bar** (`Win + G`), or **Loom**.
  - Capture Area: Full Screen (1920x1080 resolution recommended).
  - Audio: Ensure your microphone is clear, without background echo.
- [ ] **Tab Placement:**
  - Browser Window 1: `demo_portal/index.html` (Active presentation).
  - Window 2 (Optional for Scene 12): VS Code terminal showing test output `python tests/test_end_to_end_integration_12_steps.py`.

---

## 2. Step-by-Step Recording Sequence (Follow Scene Order)

| Step | Time | What to Show on Screen | What to Say / Focus On |
|:---:|:---:|---|---|
| **1** | 0:00 - 0:20 | **Admin Dashboard** (`demo_portal/index.html`) | Introduce Team AuraMinds (Dhruti & Drashti) and the Brightloop Subscription Management System for Odoo 17/18. |
| **2** | 0:20 - 0:45 | **Dashboard Overview** | State the problem: manual billing overhead, leap-year edge cases, missed cron downtime, and payment reconciliation. |
| **3** | 0:45 - 1:10 | **Architecture Overview** | Explain Developer 1 Core Engine vs. Developer 2 Operations Layer and zero destructive core overwrites. |
| **4** | 1:10 - 1:35 | Click **"Auth & Signup Demo"** in sidebar | Demonstrate password policy: show rejection of weak password, then type strong password `EmmaStrongPass2026!` and submit. |
| **5** | 1:35 - 2:00 | Click **"Products & Variants"**, then **"Subscription Plans"** | Point out the Odoo brand variant surcharge (+560). Show the 4 plan intervals (Daily, Weekly, Monthly, Annual). |
| **6** | 2:00 - 2:25 | Click **"Subscriptions"** in sidebar | Explain the state machine (Draft $\rightarrow$ Quotation $\rightarrow$ Confirmed $\rightarrow$ Active). Highlight contract `SUB-2026-001`. |
| **7** | 2:25 - 2:45 | Click **"Discounts & Promos"** in sidebar | Show coupon code `LAUNCH20`. Explain how 20% discount is deducted from the subtotal and tracks usage counts. |
| **8** | 2:45 - 3:10 | Click **"Run Billing Cron"** button in navbar | Show that invoices are automatically generated (`INV-2026-001`). Highlight downtime catch-up and duplicate prevention. |
| **9** | 3:10 - 3:35 | Click **"Recurring Invoices"**, then **"Payments & Settled"** | Show partial payment of $1,000 via card, then remaining balance settled via Stripe $\rightarrow$ invoice marked Paid. |
| **10** | 3:35 - 4:00 | Click **"Admin Dashboard"** in sidebar | Walk through the 5 KPI cards: Active Subscriptions (12), MRR ($14,840), ARR ($178,080), Churn (2.4%), and charts. |
| **11** | 4:00 - 4:20 | Click **"Portal Alice"** in top persona switcher | Show Customer Alice's view: verify she can ONLY see her own contract and cannot access the admin financial dashboard. |
| **12** | 4:20 - 4:40 | Switch to Terminal (or click Admin Dashboard) | Highlight **103/103 tests passing (100% pass rate)**. Thank the judges and conclude the presentation. |

---

## 3. Post-Recording Review Checklist

- [ ] Video duration is between **3 and 5 minutes**.
- [ ] Audio narration is clear, confident, and audible throughout.
- [ ] Screen captures are crisp with no lag or UI stutter.
- [ ] All 12 scenes are covered without missing core features.
- [ ] Export format: **MP4** (H.264 video, AAC audio) for submission.
