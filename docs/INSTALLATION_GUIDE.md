# Installation Guide — Odoo 17

## What is included

The repository's `docker-compose.yml` starts PostgreSQL and Odoo 17 and bind-mounts `./subscription_management` at `/mnt/extra-addons/subscription_management`. The Odoo config adds `/mnt/extra-addons` to the addons path and targets the local development database configured for this project.

## Prerequisites

- Docker Desktop with Docker Compose v2.
- Git checkout of this repository.
- A local-only `.env` file based on `.env.example`, with development values replaced as appropriate.
- Port 8069 available for the Odoo web server (and the configured PostgreSQL host port if access from outside the Compose network is needed).

Do not reuse development defaults on a public host. Keep `.env` private; rotate administration secrets before exposing Odoo outside a trusted local environment.

## Start the stack

Run from the repository root:

```bash
test -f .env || cp .env.example .env
# Edit .env locally; do not commit it.
docker compose up -d
docker compose ps
```

Wait until PostgreSQL is healthy and Odoo is running. Open [http://localhost:8069](http://localhost:8069). For a new environment, use the Odoo database manager to create a development database, then sign in with the administrator account configured for that environment. The existing local demo instance uses `brightloop_test_db`; do not assume that database exists in a fresh checkout.

## Install the addon

1. Sign in as a local Odoo administrator.
2. Enable developer mode if required.
3. Go to **Apps → Update Apps List**.
4. Search for **Brightloop Subscription Management** or `subscription_management`.
5. Install the module.
6. Assign appropriate module groups to internal users: **Administrator** or **Officer / Staff**. Portal users should remain portal users and should not receive internal roles.

The declared manifest dependencies are `base`, `mail`, `product`, `account`, and `portal`; no additional Python package dependency is declared by the addon manifest.

## Upgrade

For a development database, stop-after-init upgrade can be run with:

```bash
docker exec brightloop_odoo_server \
  odoo --config=/etc/odoo/odoo.conf \
  --database=brightloop_test_db \
  --update=subscription_management --stop-after-init
docker restart brightloop_odoo_server
```

Use the database name actually configured for your environment. Back up data before upgrades outside a disposable local environment. This documentation task did not run an upgrade.

## Load synthetic demo data

The loader uses stable external IDs for synthetic customers, products, plans, subscriptions, quotations, and an unpaid invoice. It does not create payment-success records. Run only on a development database:

```bash
docker exec -i brightloop_odoo_server \
  odoo shell --config=/etc/odoo/odoo.conf \
  --database=brightloop_test_db --no-http \
  < subscription_management/scripts/load_demo_data.py
```

The loader was not rerun as part of this documentation task to avoid changing the existing database. To load into a different database, replace the database argument with its name.

## Run automated verification

The standalone verification suite:

```bash
python3 tests/run_standalone_verification.py -v
```

The repository also contains Odoo `TransactionCase` and `HttpCase` tests under `subscription_management/tests/`. They require a configured Odoo test database. Do not run broad test suites against a shared demo/production database; test setup may create records, and the previously recorded native run against the populated database was not clean.

See [TESTING_REPORT.md](TESTING_REPORT.md) for the observed results and known limitations.

## Stop services

```bash
docker compose stop
```

`docker compose down` removes the containers but retains named Docker volumes. Do not add `-v` unless you explicitly intend to delete local PostgreSQL/Odoo data.

## Local URLs

- Odoo root: [http://localhost:8069](http://localhost:8069)
- Internal web client: [http://localhost:8069/web](http://localhost:8069/web)
- Customer portal home: [http://localhost:8069/my](http://localhost:8069/my)

Portal and internal routes require their respective authenticated accounts.
