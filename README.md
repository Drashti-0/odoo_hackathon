# Brightloop Subscription Management

Brightloop is an Odoo 17 addon for managing software subscription products, recurring plans, quotations, subscription contracts, subscription invoices, payments, discounts, and internal operational dashboards.

The addon is named `subscription_management` and is in `subscription_management/`. Its Odoo manifest depends on `base`, `mail`, `product`, `account`, and `portal`. The local Docker setup mounts the addon's directory into the Odoo container.

## What is implemented

- Subscription products and product variants with brand and variant pricing fields.
- Daily, weekly, monthly, and yearly billing plans with availability and lifecycle policy.
- Quotations and contract lifecycle states: draft, quotation, confirmed, active, paused, closed, and expired.
- Recurring invoices, billing-period duplicate protection, scheduled billing jobs, and billing audit logs.
- Discount rules and invoice/subscription discount hooks.
- Payment transaction records and invoice payment/residual tracking. Payment-method labels include card, bank transfer, Stripe, PayPal, and cash/cheque; a live payment-provider integration was not verified.
- Staff, administrator, and portal roles; customer-scoped portal pages for subscriptions, quotations, plans, invoices, and billing history.
- Odoo backend list, form, search, graph, and pivot views; an invoice QWeb report.
- A database-backed internal dashboard and synthetic, repeatable demo data loader.

See [docs/PROJECT_ARCHITECTURE.md](docs/PROJECT_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for implementation details.

## Run locally

The repository includes Docker Compose for Odoo 17 and PostgreSQL. Before exposing this setup beyond a local development machine, replace development-only configuration with private local settings and rotate any default administration secrets. Do not commit `.env` files or credentials.

1. Install Docker Desktop with Docker Compose.
2. From the repository root, create `.env` from `.env.example` only if you do not already have a private local `.env`, then replace development values with local-only values:

   ```bash
   test -f .env || cp .env.example .env
   ```

3. Start the services:

   ```bash
   docker compose up -d
   docker compose ps
   ```

4. Open [http://localhost:8069](http://localhost:8069). Create/select a development database as needed, sign in with the locally configured administrator, and install **Brightloop Subscription Management** from Apps. The addon is mounted at `/mnt/extra-addons/subscription_management`.
5. Assign the appropriate Subscription Administrator or Officer / Staff group to internal users.
6. To load synthetic demo records in a development database only, see [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md).

Detailed installation, upgrade, demo data, and stop commands are in [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md).

## Verification snapshot

At the 2026-10-31 verification snapshot, the standalone regression runner passed **92 tests** and all **16 addon XML files** parsed. A native Odoo suite run against the already-populated local database reported **14 failures and 6 errors out of 132 tests**; see [docs/TESTING_REPORT.md](docs/TESTING_REPORT.md). Do not interpret that database run as a clean isolated test pass.

Actual demo evidence and known verification gaps are recorded in [docs/FINAL_PROJECT_REPORT.md](docs/FINAL_PROJECT_REPORT.md). Screenshot capture/export limitations are documented in [docs/screenshots/README.md](docs/screenshots/README.md).

## Project and submission documents

- [Project architecture](docs/PROJECT_ARCHITECTURE.md)
- [Database design](docs/DATABASE_DESIGN.md)
- [User guide](docs/USER_GUIDE.md)
- [Installation guide](docs/INSTALLATION_GUIDE.md)
- [Testing report](docs/TESTING_REPORT.md)
- [Final project report](docs/FINAL_PROJECT_REPORT.md)
- [Hackathon presentation content](docs/PRESENTATION_CONTENT.md)
- [Integration contract](INTEGRATION_CONTRACT.md)

## License and team

The module manifest declares LGPL-3. The project is by Team AuraMinds. See the integration contract for ownership/interface details.
