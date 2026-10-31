# Security and Access Review

**Review date:** 2026-10-31  
**Scope:** Source/configuration review of the current Odoo 17 checkout and bounded live route checks. This is not a penetration test or a formal security certification.

## Role model

The current security definitions in `subscription_management/security/security.xml` declare:

| Group | Intended access |
|---|---|
| `group_subscription_manager` — Administrator | Subscription administration, including configuration and reporting privileges. |
| `group_subscription_user` — Officer / Staff | Internal subscription operations. |
| `group_subscription_portal` — Portal Customer | Customer-facing portal and read access constrained by record ownership. |

ACLs are in `subscription_management/security/ir.model.access.csv`. Portal users are not granted internal dashboard access. Do not assign a portal user the internal staff/manager groups to make a demonstration work.

## Customer record isolation

- Portal HTTP routes use authenticated Odoo users and partner-scoped searches before returning subscription/invoice detail.
- Subscription and invoice record rules restrict records by the user's partner/commercial-partner hierarchy in the current security definitions.
- The invoice-PDF route resolves the invoice through the customer ownership lookup before using elevated privileges to render the report.
- Portal cancellation/renewal controls create staff-review activities; they do not let the customer directly write lifecycle state.
- The payment settlement methods check that the caller is staff/manager or superuser.

**Verification limit:** No separate authorized portal account was available for two-customer adversarial access tests in the final run. Source inspection is evidence of intended enforcement, not a dynamic proof that all routes are isolated.

## `sudo()` review

Targeted source inspection found elevated calls in registration/onboarding, background billing/audit/activity handling, invoice report rendering, and staff-request creation. The reviewed PDF/request paths first scope the target invoice or subscription to the authenticated customer. This review did not prove every `sudo()` call safe under all contexts, and should not be represented as a complete security audit.

## Configuration and secrets

- `.env` is ignored by Git and was not tracked in the checked repository state.
- `.env.example` contains blank password fields rather than working credentials.
- Compose requires password values via local environment configuration and binds the published Odoo port to loopback.
- Do not paste local secrets into docs, source control, issue comments, screenshots, or presentation material.
- The Odoo master password is supplied at runtime from local environment configuration; rotate it before hosting outside a development workstation.

These are repository/configuration checks only. They do not prove the local developer's environment variables or database credentials are safe.

## Current gaps and risks

1. **Duplicate portal endpoint:** both `controllers/portal_auth.py` and `controllers/subscription_portal.py` declare `/my/subscriptions`. The live request rendered a subscription list, but duplicate route registration should be consolidated by the portal owner to remove order-dependent ambiguity.
2. **Public registration/reset endpoints:** the auth controller declares public JSON routes. Input validation and generic reset responses are present in code, but this review did not test abuse throttling; no rate-limit behavior was verified. Apply suitable proxy/application throttling before public exposure.
3. **Portal verification:** no authenticated customer with a known synthetic subscription was available for cross-customer testing.
4. **Payment provider security:** no actual provider credentials, webhook signing, or gateway transaction was tested. Payment method labels do not imply an operational gateway integration.
5. **Native Odoo test suite:** a previous run against the populated database had failures/errors and was not an isolated security regression run.

## Live checks

- Odoo 17 runtime was available.
- Anonymous `/web`, `/my`, `/my/subscriptions`, `/my/plans`, `/my/invoices`, and `/my/billing-history` requests redirected to login.
- Authenticated internal dashboard rendering and reload produced no observed browser console/page errors during the bounded check.
- No ACLs or record rules were modified during this final work.

For general test status, see [TESTING_REPORT.md](TESTING_REPORT.md). For the exact demo boundary, see [FINAL_HACKATHON_DEMO.md](FINAL_HACKATHON_DEMO.md).
