<div align="center">

<!--
Add screenshots to docs/screenshots/ and uncomment:

| Landing | Dashboard | Cash & Credit |
|---|---|---|
| ![Landing](docs/screenshots/landing.png) | ![Dashboard](docs/screenshots/dashboard.png) | ![Cash and Credit](docs/screenshots/cash-credit.png) |
-->

---

## Why DukaanPulse?

Small wholesalers still run on paper registers (*bahi-khata*), spreadsheets and chat messages. Credit is scattered, stock never matches the bills, and the owner finds out a customer is a bad payer only after the money is stuck.

DukaanPulse keeps the whole trade cycle in one place:

**Buy goods → Keep stock → Sell → Deliver → Collect money → Handle returns**

and adds **Cash & Credit Intelligence**, which reads what has been recorded and answers, in plain words:

- How much do customers owe me, and how much of it is late?
- Which customers should I call first?
- How much credit is safe to give each customer?
- Will I run short of cash in the next five weeks?

It never changes data by itself. Scores and credit limits are **suggestions**, and every one shows its reasons.

---

## Features

### Wholesale operations

- **Products and packaging units** (for example Box = 12 Pieces), categories, customers and suppliers.
- **Purchases** with partial receiving, and supplier payments.
- **Orders**, **partial invoicing** (one order can have several invoices), **deliveries** and **customer payments**.
- **Returns** with an approve → receive flow that puts stock back and turns the value into credit.
- **Stock as a ledger.** Stock is never typed in. It is the sum of append-only movements (purchase, sale, return), so every number can be explained.
- **Dashboard** with sales and purchase trends, low stock and a payment summary.

### Cash & Credit Intelligence

- **Receivables aging**: not due, 1–30, 31–60, 61–90 and 90+ days late.
- **Customer risk score from 0 to 100. Lower is safer.** *Reliable* (below 25), *Keep an eye* (25 to 49), *High risk* (50 and above), or *Too new to rate* (fewer than 3 paid invoices in 6 months).
- A **"Who needs attention"** list with a plain sentence and a suggested action for each customer.
- **Suggested credit limits**, never applied automatically.
- A **five-week cash outlook** with a "be cautious" view that ignores money from high-risk customers.

### Teams and security

- **Multi-tenant**: each business is a private workspace. One business can never see another's data.
- **Roles**: Owner, Admin, Sales, Warehouse, Accounts, Viewer, each with its own permissions.
- **Mobile-number login** with one-time passwords (OTP). Staff join by invitation.
- Opaque server-side sessions in **HttpOnly cookies**, CSRF protection, Argon2 password hashing, rate limits and an audit log.

### Experience

- A **logo intro** and a public **landing page**.
- **Skeleton loading**, a short-lived request cache and a responsive layout with a phone drawer menu.
- A single design system (colour, type, spacing and motion tokens). See [UI/UX Design Brief](docs/04-UIUX-DESIGN-BRIEF.md).

---

## Tech stack

| Layer    | Technology                                                                                |
| -------- | ----------------------------------------------------------------------------------------- |
| Frontend | React 18, Vite, React Router, Axios, Recharts, lucide-react, plain CSS with design tokens |
| Backend  | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2                               |
| Database | PostgreSQL (NUMERIC money, composite keys, check constraints, advisory locks)             |
| Auth     | Server-side sessions, Argon2 (`pwdlib`), HMAC-hashed tokens and OTPs                    |
| Fonts    | Libre Baskerville and IBM Plex Sans (Google Fonts)                                        |

```
Browser (React SPA)
   │  HTTPS · JSON · HttpOnly session cookie + CSRF header
   ▼
FastAPI  ─►  Routers  ─►  Services  ─►  SQLAlchemy  ─►  PostgreSQL
   │                          └─► SMS gateway (OTP)
   └─ Guards on every request: origin, session, CSRF, role permission, workspace scope
```

---

## Getting started

### Prerequisites

- **Python** 3.10 or newer
- **Node.js** 18 or newer
- **PostgreSQL** (a recent version, 14 or newer recommended)

### 1. Get the code

```bash
git clone <your-repository-url>
cd Dukaanplus1
```

### 2. Create the database

```bash
createdb dukaanpulse
```

Then apply the SQL files in order, **once**, on this new, empty database:

```bash
cd backend
for f in sql/00*.sql; do psql -d dukaanpulse -f "$f"; done
```

On Windows PowerShell:

```powershell
cd backend
Get-ChildItem sql\00*.sql | Sort-Object Name | ForEach-Object { psql -d dukaanpulse -f $_.FullName }
```

> `005_workspace_scope_business_data.sql` stops with an error if any business data already exists. Run it before entering real data.

### 3. Run the backend

Create `backend/.env`:

```ini
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/dukaanpulse
SMS_PROVIDER=console
```

`SMS_PROVIDER=console` prints each OTP in the backend terminal, so you do not need an SMS account in development.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. In development, interactive docs are at `/docs` and `/redoc`, and `GET /health` shows it is alive.

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. If your API is not at `http://127.0.0.1:8000`, create `frontend/.env.local`:

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 5. Create your first business

1. Click **Get started**.
2. Fill in your name, business name, mobile number, username and a password of at least 12 characters.
3. A six-digit code is **printed in the backend terminal**. Enter it.
4. You are signed in as the **Owner** of a new workspace.

### 6. (Optional) Load demo data

The demo seeder fills a **throwaway** workspace with synthetic customers who pay in different ways (reliable, chronically late, worsening, near their limit, brand new), so you can see every rating and the cash outlook.

1. Add `DEMO_SEED_ALLOWED=true` to the environment file of that **demo-only** backend.
2. Create an account as in step 5.
3. From `backend/`, with the virtual environment active:

```bash
python -m app.scripts.seed_demo --base-url http://127.0.0.1:8000 --months 12 --seed 42
```

Use `--dry-run` first to see the plan without sending anything. The script asks for that account's username and password and for you to type `SEED DEMO`.

> **Never run the seeder against a real database.** It only accepts a loopback address, but choosing the right target is your job.

---

## Configuration

| Variable                                             | Purpose                                                | Default                                         |
| ---------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| `DATABASE_URL`                                     | PostgreSQL connection string                           | **required**                              |
| `ENVIRONMENT`                                      | `development` or `production`                      | `development`                                 |
| `SMS_PROVIDER`                                     | `disabled`, `console` or `generic_http`          | `disabled`                                    |
| `SMS_HTTP_URL`, `SMS_HTTP_AUTHORIZATION`         | Settings for the HTTP SMS gateway                      | unset                                           |
| `SESSION_TOKEN_PEPPER`, `OTP_HMAC_KEY`           | Secrets for hashing sessions and OTPs (32+ characters) | **required in production**                |
| `CORS_ALLOWED_ORIGINS`                             | Comma-separated allowed origins (never `*`)          | `http://localhost:5173,http://127.0.0.1:5173` |
| `SESSION_IDLE_MINUTES`, `SESSION_ABSOLUTE_HOURS` | Session timeouts                                       | 30 minutes, 8 hours                             |
| `COOKIE_SECURE`, `COOKIE_DOMAIN`                 | Cookie settings                                        | `COOKIE_SECURE` required in production        |
| `DEMO_SEED_ALLOWED`                                | Allow the demo seeder                                  | `false`                                       |
| `DUKAANPULSE_ENV_FILE`                             | Use a different env file than `.env`                 | `.env`                                        |

Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The full list is in the [TRD](docs/02-TRD.md#11-configuration-environment-variables).

---

## Roles

| Role                | What they mainly do                                                               |
| ------------------- | --------------------------------------------------------------------------------- |
| **Owner**     | Everything. Creates the business, manages staff. The last Owner cannot be removed |
| **Admin**     | Everything except changing ownership                                              |
| **Sales**     | Customers, orders, invoices, customer payments, return requests                   |
| **Warehouse** | Products, suppliers, purchases, deliveries, receiving returns                     |
| **Accounts**  | Customer and supplier payments, return approval, Cash & Credit                    |
| **Viewer**    | Read-only (no reports)                                                            |

The server enforces these rules on every request, and the app only shows what a role may use. Exact permissions are in `backend/app/core/permissions.py` and [App Flow](docs/03-APP-FLOW.md#34-who-sees-what).

---

## Project structure

```
Dukaanplus1/
├── backend/
│   ├── app/
│   │   ├── main.py             App, CORS, router registration
│   │   ├── core/               Config, security, auth, permissions, roles
│   │   ├── db/                 Engine, session, workspace-scope hook
│   │   ├── models/             SQLAlchemy models
│   │   ├── schemas/            Pydantic request and response models
│   │   ├── routers/            One file per API area
│   │   ├── services/           Business rules, auth lifecycle, analytics/
│   │   └── scripts/            Demo data seeder
│   ├── sql/                    Migrations 000 to 005 (apply in order)
│   └── tests/                  Test suites
├── frontend/
│   └── src/
│       ├── api/                Axios client (CSRF, cache) and endpoints
│       ├── auth/               Session state
│       ├── components/         Layout, Logo, Splash, UserMenu, Skeleton, …
│       ├── pages/              One file per screen, plus Landing
│       └── tokens.css          Design tokens
└── docs/                       Product, technical and design documents
```

---

## Testing

From `backend/`, with the virtual environment active:

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests
```

The tests are plain `unittest` classes, so `pytest` also runs them if you install it. They cover the analytics calculations, authentication (logic and HTTP), permissions, user management, reports, security checks, configuration and the demo seeder. A **route-audit test fails if any endpoint is added without a permission**.

There are no automated browser or load tests yet.

---

## Security at a glance

- Sessions are random tokens stored **hashed**, sent in **HttpOnly** cookies. No token lives in `localStorage`.
- A **CSRF token** (`X-CSRF-Token`) is required on every write, and unsafe requests must come from an allowed origin.
- Passwords use **Argon2** (12 characters minimum). Repeated wrong passwords lock the account for 15 minutes.
- **OTP**: 6 digits, valid 5 minutes, 5 attempts, with send and verify rate limits.
- **Tenant isolation in three layers**: an automatic `workspace_id` filter on every query, composite foreign keys, and per-business unique keys.
- Money and stock rules are enforced on the server and in database constraints, with locks to stop double-spending and overselling.
- Production start-up refuses weak or missing secrets, insecure cookies, a console SMS provider and wildcard CORS.

See [TRD section 6](docs/02-TRD.md#6-authentication-and-sessions) and [Backend Schema section 7](docs/05-BACKEND-SCHEMA.md#7-authentication-and-data-flows).

---

## Documentation

| Document                                             | What it covers                                               |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| [PRD](docs/01-PRD.md)                                 | What we are building, for whom and why, in plain language    |
| [TRD](docs/02-TRD.md)                                 | Architecture, stack, security, business rules, configuration |
| [App Flow](docs/03-APP-FLOW.md)                       | Screens, navigation, user journeys, status flows             |
| [UI/UX Design Brief](docs/04-UIUX-DESIGN-BRIEF.md)    | Logo, colour, type, spacing, components, screens             |
| [Backend Schema](docs/05-BACKEND-SCHEMA.md)           | Tables, relationships, login flows, API routes               |
| [Implementation Plan](docs/06-IMPLEMENTATION-PLAN.md) | Build order, current status, what is left                    |

---

## Deploying

In short: a managed PostgreSQL with backups, long random secrets, HTTPS, the frontend and API on the **same site** (for example `app.example.com` and `api.example.com`) so cookies are sent, a real SMS provider, and `npm run build` for the frontend. The full checklist is in [Implementation Plan, phase 19](docs/06-IMPLEMENTATION-PLAN.md#phase-19-deployment--m).

---

## Known limitations

DukaanPulse is a working application with some known gaps. The honest list, with priorities, is in [TRD section 16](docs/02-TRD.md#16-known-gaps-and-technical-debt). The main ones:

- Money is handled as floating-point in Python (the database columns are exact `NUMERIC`).
- List screens load all rows (no pagination yet).
- Invoice unit prices come from the client rather than the product.
- Delivery status changes need a row lock.

---

## Roadmap

Printable invoices and Excel export, WhatsApp or SMS payment reminders, GST-ready invoices, barcode scanning, multiple godowns per business, offline mode and Hindi screens. See [PRD section 5.3](docs/01-PRD.md).

---

## Contributing

1. Create a branch for your change.
2. Update the relevant document in `docs/` **in the same change**.
3. Add or update tests. New routes need a permission decision, or the route-audit test fails.
4. Use only design tokens for colour, spacing and radius.
5. Open a pull request that says what changed and why.

---

## License

Add a `LICENSE` file before sharing this repository publicly. Until then, all rights are reserved by the author.

## Author

Mahendra Singh
