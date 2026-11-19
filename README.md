# DukaanPulse

DukaanPulse is a full-stack ERP for a wholesale distributor. It supports the
operational flow from catalogue and purchasing through orders, invoices,
delivery, returns, payments, and stock lookup. Its Cash & Credit Intelligence
feature adds explainable receivables, customer-risk, and next-5-weeks
cash-movement views for real operational review and portfolio demonstration.

The project is deliberately opinionated about honesty: report outputs expose
their inputs and reasons, insufficient history is shown as such, and credit
recommendations are suggestions rather than automatic actions.

## Features

### Wholesale operations

- Product categories, products, packaging, customers, and suppliers.
- Purchasing and incremental stock receiving.
- Customer orders, partial invoicing, deliveries, customer payments, supplier
  payments, and returns.
- Append-only inventory movements: stock changes only through the relevant
  business workflow.
- Role-based access control with ADMIN, SALES, WAREHOUSE, ACCOUNTS, and VIEWER
  roles.

### Cash & Credit Intelligence

- Portfolio receivable, overdue, customer-store-credit, and aging views.
- Transparent customer risk score, band, trend, inputs, and reasons.
- Explicit INSUFFICIENT_HISTORY handling rather than fabricated scores.
- Non-binding, explainable suggested credit limits.
- Next 5 weeks expected cash IN and OUT, cumulative net, and a conservative
  series that excludes RISKY-customer receipts.
- Optional browser-only opening balance for viewing projected balances.
- API-provided methodology, formulas, thresholds, and payment-date reminder.

Cash & Credit reports require reports:read and are currently available to
ADMIN and ACCOUNTS. They do not make credit decisions, change customer limits,
or block transactions.

## Architecture overview

    React 18 + Vite frontend
        |
        | Axios bearer-token requests
        v
    FastAPI application
        |
        | SQLAlchemy 2.0
        v
    PostgreSQL

The frontend is plain JavaScript and CSS. It uses React Router for protected
pages, Axios for API requests, Recharts for charts, and lucide-react for icons.

The FastAPI backend owns authentication, authorization, business rules, and
database access. JWTs carry a user identifier, while the backend reloads the
user and permissions on authenticated requests. Passwords use Argon2 through
pwdlib.

Cash & Credit calculations are separated from database loading:

    app/services/analytics/loaders.py       fixed bulk database queries
    app/services/analytics/calculations.py  pure, explainable calculations
    app/services/analytics/config.py        all report thresholds
    app/routers/reports.py                  authenticated report endpoints

The loader runs six bulk queries for customers, invoices, customer payments,
suppliers, purchases, and supplier payments. The report endpoints expose the
as-of date, methodology, thresholds, inputs, and reasons alongside results.

## Running locally

Use only a local or otherwise authorised database. The application does not
run migrations automatically. Follow docs/deployment-checklist.md for the
manual baseline and additive-migration process; do not rerun the baseline dump
against a database that already has it.

### Backend

From backend:

    .\venv\Scripts\python.exe -m pip install -r requirements.txt
    .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

Create a local environment file from backend/.env.example and set the required
local DATABASE_URL and JWT_SECRET_KEY values without committing them. The API
is then normally available at http://127.0.0.1:8000, with development API docs
at /docs.

Create the first administrator interactively:

    .\venv\Scripts\python.exe -m app.scripts.create_admin

### Frontend

From frontend:

    npm.cmd install
    npm.cmd run dev

Create a local environment file from frontend/.env.example if the API is not
at the default local URL. Vite normally serves the app at
http://localhost:5173.

### Safe demo environment

For a complete synthetic portfolio walkthrough, including the isolated
database setup, demo-only environment files, seeding safety checks, and
five-minute script, use docs/demo-guide.md. The generator only accepts a
loopback URL, requires a demo-only backend to declare seeding enabled, requires
the exact confirmation SEED DEMO, and refuses a non-empty target.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, Vite, React Router 6, Axios, Recharts, lucide-react |
| API | FastAPI, Uvicorn, Pydantic Settings |
| Data | PostgreSQL, SQLAlchemy 2.0, psycopg 3 |
| Security | Argon2 via pwdlib, PyJWT, OAuth2 password form |
| Testing and demo HTTP client | httpx |

## Documentation

- docs/analytics-methodology.md explains the exact Cash & Credit definitions,
  formulas, thresholds, examples, and limitations.
- docs/demo-guide.md provides the safe synthetic demo procedure and script.
- docs/deployment-checklist.md covers production environment, migration,
  account, and operational safeguards.

## Screenshot checklist

Use synthetic demo data only. Do not capture real customer, supplier, payment,
database, account, token, or network information.

- A Cash & Credit overview with the visible Demo data banner, KPI cards, and
  aging chart.
- The risk table showing text and icons for bands and trends.
- An expanded RISKY-customer row showing reasons and calculation inputs.
- An INSUFFICIENT_HISTORY row showing why a score was not produced.
- Next 5 weeks cash flow with optional opening-balance projections.
- The expanded methodology panel.

## What I would build next

- Supplier-payables and stock-valuation reporting, after defining the relevant
  business rules and costing method.
- Exportable report snapshots with appropriate access controls and audit data.
- Bank-balance and non-purchase-outflow integrations, clearly separated from
  the current expected-movement projection.
- Per-IP rate limiting, MFA, password recovery, and an audit-log UI.
- Broader automated browser coverage for workflows and accessibility.
