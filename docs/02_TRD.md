
# DukaanPulse: Technical Requirements Document (TRD)

|                             |                                                                                                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Product**           | DukaanPulse                                                                                                                                              |
| **Document type**     | TRD: how the system is built, and the technical rules it must follow                                                                                     |
| **Reads best after**  | [PRD](01-PRD.md)                                                                                                                                          |
| **Related documents** | [App Flow](03-APP-FLOW.md), [UI/UX Brief](04-UIUX-DESIGN-BRIEF.md), [Backend Schema](05-BACKEND-SCHEMA.md), [Implementation Plan](06-IMPLEMENTATION-PLAN.md) |

> **Source of truth.** This document describes the code as it is in the repository. Where something is a known gap, it is listed in section 16 instead of being described as if it were solved.

---

## 1. System summary

DukaanPulse is a **multi-tenant web application**:

- A **React single-page application** (the browser side).
- A **FastAPI REST API** (the server side) that returns and accepts JSON.
- A **PostgreSQL** database.
- An optional **SMS gateway** that delivers one-time passwords.

```
Browser (React SPA)
      │   HTTPS, JSON, HttpOnly session cookie + CSRF header
      ▼
FastAPI application ──► Routers ──► Services ──► SQLAlchemy ORM ──► PostgreSQL
      │                                   │
      │                                   └──► SMS gateway (OTP)
      └── Guards on every request: origin check, session, CSRF, role permission, workspace scope
```

Each business is a **workspace**. Every business table carries a `workspace_id`, and every request is bound to exactly one workspace.

---

## 2. Technology stack

### 2.1 Backend

| Area                    | Choice                                                      |
| ----------------------- | ----------------------------------------------------------- |
| Language                | Python 3                                                    |
| Web framework           | **FastAPI** (ASGI), served by **Uvicorn**       |
| ORM                     | **SQLAlchemy 2.0** (typed `Mapped[]` models)        |
| Validation and settings | **Pydantic v2**, **pydantic-settings**          |
| Database driver         | **psycopg 3** (`psycopg[binary]`)                   |
| Password hashing        | **Argon2** through `pwdlib[argon2]`                 |
| Config                  | `.env` file read by `python-dotenv` / pydantic-settings |
| Time zone data          | `tzdata` (business time zone `Asia/Kolkata`)            |
| Tests                   | **pytest** (see `requirements-dev.txt`)             |

`PyJWT` is still listed in `requirements.txt` and `JWT_SECRET_KEY` / `token_version` still exist in the code, but **login no longer uses JWTs**. It uses opaque server-side sessions (section 6). These are leftovers and can be removed.

### 2.2 Frontend

| Area       | Choice                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------- |
| UI library | **React 18.3**                                                                     |
| Build tool | **Vite**                                                                           |
| Routing    | **React Router 6.26**                                                              |
| HTTP       | **Axios 1.7**                                                                      |
| Charts     | **Recharts 2.12**                                                                  |
| Icons      | **lucide-react 0.446**                                                             |
| Styling    | Plain CSS with **design tokens** (`tokens.css`, `index.css`), no CSS framework |
| Fonts      | Libre Baskerville (titles) and IBM Plex Sans (everything else), loaded from Google Fonts |

### 2.3 Database

**PostgreSQL**, using: `NUMERIC` money columns, `CHECK` constraints for statuses, composite foreign keys for tenant safety, partial and composite indexes, and **advisory locks** for concurrency.

---

## 3. Repository layout

```
Dukaanplus1/
├── backend/
│   ├── app/
│   │   ├── main.py                  App creation, CORS, router registration
│   │   ├── core/                    config, security, auth, permissions, roles, mobile
│   │   ├── db/database.py           Engine, session, workspace-scope hook
│   │   ├── models/                  SQLAlchemy models (one file per area)
│   │   ├── schemas/                 Pydantic request and response models
│   │   ├── routers/                 One file per API area
│   │   ├── services/                Business rules: auth_lifecycle, sms_provider,
│   │   │                            inventory, invoice, order, return,
│   │   │                            analytics/ (config, loaders, calculations)
│   │   └── scripts/                 seed_demo.py, demo_personas.py
│   ├── sql/                         000 baseline … 005 workspace scoping
│   ├── tests/                       pytest suites
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html
│   ├── public/favicon.svg
│   └── src/
│       ├── main.jsx                 Entry point (wraps the app in the logo intro)
│       ├── App.jsx                  Routes and providers
│       ├── api/                     client.js (Axios, CSRF, cache), endpoints.js
│       ├── auth/AuthProvider.jsx    Session state, login, logout, workspace switch
│       ├── components/              Layout, Logo, Splash, UserMenu, Modal, Toast, …
│       ├── pages/                   One file per screen, plus Landing
│       ├── tokens.css, index.css    Design tokens and global styles
│       └── lib/                     Small helpers
└── docs/                            These documents
```

---

## 4. Architecture

The code follows the **Model / View / Controller** idea, in layers:

| Layer                | Where                                             | Responsibility                                                   |
| -------------------- | ------------------------------------------------- | ---------------------------------------------------------------- |
| **View**       | `frontend/src/pages`, `components`            | Screens, forms, tables, charts. No business rules.               |
| **Controller** | `backend/app/routers`                           | Receive a request, check permission, call services, return JSON. |
| **Model**      | `backend/app/models`, `services`, `schemas` | Data structures, validation and the business rules.              |

### Request path (every protected call)

1. **CORS and origin check.** Only configured origins are allowed. Unsafe methods must come from a trusted origin.
2. **Session check.** The `dukaanpulse_session` cookie is looked up (hashed) in `auth_sessions`.
3. **CSRF check.** For POST, PATCH and DELETE the `X-CSRF-Token` header must match the session's CSRF token.
4. **Workspace selection.** The session's workspace becomes the active tenant for this request.
5. **Permission check.** `require_permission("resource:action")` compares the user's role with the permission list.
6. **Handler.** The router calls the service layer, which uses the ORM.
7. **Response.** A Pydantic model is returned as JSON. Errors come back as `{ "detail": "..." }`.

---

## 5. Multi-tenancy (keeping businesses separate)

Tenant safety has **three independent layers**, so one mistake does not leak data.

1. **Automatic query filter (application layer).** Business models inherit a `WorkspaceScoped` mixin. A SQLAlchemy hook adds `workspace_id = <current workspace>` to every ORM `SELECT` for those models, using `with_loader_criteria`. New records get the workspace id automatically.
2. **Composite keys (database layer).** Migration `005` adds `workspace_id` to every business table and creates unique keys such as `(workspace_id, product_id)`. Child tables point to their parents through **composite foreign keys**, so a child row cannot reference a parent from another workspace.
3. **Workspace-scoped uniqueness.** Things that must be unique per business (SKU, invoice number, GST number, category name, payment reference) are unique on `(workspace_id, value)`, not globally.

Notes:

- The automatic filter applies to **ORM SELECT** statements. Bulk `UPDATE`/`DELETE` and raw SQL are not filtered, so new code must not use them on business tables without adding the workspace condition by hand.
- The identity tables (`users`, `workspaces`, `workspace_memberships`, sessions, OTP) are **not** workspace-scoped, because they define who belongs where.
- A user can belong to several workspaces through `workspace_memberships`, with a different role in each.

---

## 6. Authentication and sessions

### 6.1 Principles

- Login is by **mobile number (OTP-verified)** and **password**. There is no email.
- Sessions are **opaque random tokens** stored **hashed** in the database. They are not JWTs.
- The session cookie is **HttpOnly**, so JavaScript cannot read it.
- A separate readable **CSRF cookie** is mirrored into an `X-CSRF-Token` header by the frontend.

### 6.2 Cookies and tokens

| Item             | Value                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------- |
| Session cookie   | `dukaanpulse_session`, HttpOnly, `SameSite=Lax`, `Secure` in production                                   |
| CSRF cookie      | `dukaanpulse_csrf`, readable by JS                                                                            |
| CSRF header      | `X-CSRF-Token` (compared with a hash stored on the session)                                                   |
| Token storage    | Only **HMAC hashes** are stored (session token with `SESSION_TOKEN_PEPPER`, OTPs with `OTP_HMAC_KEY`) |
| Passwords        | Argon2 hashes, minimum **12 characters**                                                                  |
| Idle timeout     | **30 minutes** (`SESSION_IDLE_MINUTES`)                                                                 |
| Absolute timeout | **8 hours** (`SESSION_ABSOLUTE_HOURS`)                                                                  |

### 6.3 One-time passwords

| Rule                    | Value                                                                     |
| ----------------------- | ------------------------------------------------------------------------- |
| Purposes                | `SIGNUP`, `PASSWORD_RESET`, `INVITATION`                            |
| Length                  | 6 digits                                                                  |
| Validity                | 5 minutes                                                                 |
| Wrong attempts per code | 5, then the code is locked                                                |
| Resend wait             | 30 seconds                                                                |
| Send limits             | 5 per mobile per hour, 10 per IP per hour, 500 in total per hour          |
| Verify limits           | 30 per IP and 10 per mobile per 15 minutes, 1,000 in total per 15 minutes |

### 6.4 Login protection

- **5** failed passwords lock the account for **15 minutes** (`FAILED_LOGIN_ATTEMPT_THRESHOLD`, `LOGIN_LOCKOUT_MINUTES`).
- Unknown users still pay the cost of a password check, so timing does not reveal whether an account exists.
- Login creates a fresh session and revokes the user's other sessions.
- Password change and admin password reset revoke sessions.
- Important events go to `security_audit_events` (login, invitation, password reset and so on).

### 6.5 Invitations

- An Owner or Admin creates an invitation for a mobile number and a role. The server returns a one-time token.
- The invited person opens the link, and the server sends an OTP to the **invited mobile number**.
- A new person chooses a name, username and password. A person who already has an account must **enter their current password** before the OTP is sent, so an OTP alone never signs someone in to an existing account.
- The invitation, membership and session are created together in one transaction.

### 6.6 Authorisation

Roles live on `workspace_memberships.role`: `OWNER`, `ADMIN`, `SALES`, `WAREHOUSE`, `ACCOUNTS`, `VIEWER`.

Permissions are strings like `invoices:write`, defined in `core/permissions.py`:

| Role                   | Permissions in short                                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Owner, Admin** | Everything except `system:read` (includes `users:manage`)                                                                                    |
| **Sales**        | Read: categories, products, suppliers, deliveries, inventory, dashboard. Read and write: customers, orders, invoices, payments, returns (create) |
| **Warehouse**    | Write: categories, products, suppliers, purchases, deliveries. Read: customers, orders, invoices, inventory, dashboard. Can receive returns      |
| **Accounts**     | Read and write: payments, purchase payments. Can approve returns. Read: most business data, dashboard and **reports**                      |
| **Viewer**       | Read-only on all business resources **except reports**                                                                                     |

A route-audit test fails if any endpoint is added without a permission.

---

## 7. API design

### 7.1 Conventions

- **REST + JSON.** `GET` reads, `POST` creates or runs an action, `PATCH` updates, `DELETE` removes (used only for sessions).
- Routers are registered with the workspace dependency; the auth and invitation routers are public or session-only.
- Request and response bodies use **Pydantic** models. Invalid input returns `422`, rule violations `400` or `409`, missing login `401`, missing permission `403`, unknown records `404`.
- Status changes use dedicated routes such as `PATCH /orders/{id}/status` or `PATCH /returns/{id}/receive`.

### 7.2 Endpoint groups

| Group                | Prefix                         | Main routes                                                                                                                                                                                                                              |
| -------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth                 | `/auth`                      | `signup`, `signup/verify-otp`, `signup/resend-otp`, `otp/resend`, `login`, `logout`, `me`, `switch-workspace`, `change-password`, `forgot-password`, `reset-password/verify-otp`, `reset-password`, `sessions` |
| Invitations          | `/business`                  | `invitations`, `invitations/accept`, `invitations/verify-otp`                                                                                                                                                                      |
| Users                | `/users`                     | list, update role or status, reset a member's password                                                                                                                                                                                   |
| Categories           | `/categories`                | list, create                                                                                                                                                                                                                             |
| Products             | `/products`                  | list, create, read, update                                                                                                                                                                                                               |
| Customers, Suppliers | `/customers`, `/suppliers` | list, create, read, update                                                                                                                                                                                                               |
| Purchases            | `/purchases`                 | create, list, read, `status`, `receive`                                                                                                                                                                                              |
| Purchase payments    | `/purchase-payments`         | create, list                                                                                                                                                                                                                             |
| Orders               | `/orders`                    | create, list, read, `status`                                                                                                                                                                                                           |
| Invoices             | `/invoices`                  | create, list, read, `status` (cancel)                                                                                                                                                                                                  |
| Deliveries           | `/deliveries`                | create, list, `status`                                                                                                                                                                                                                 |
| Payments             | `/payments`                  | create, list, `apply-credit`                                                                                                                                                                                                           |
| Returns              | `/returns`                   | create, list, read, `approve`, `receive`                                                                                                                                                                                             |
| Inventory            | `/inventory`                 | `stock/{product_id}`                                                                                                                                                                                                                   |
| Dashboard            | `/dashboard`                 | `summary`, `sales`, `sales/daily`, `purchases`, `top-products`, `low-stock`, `payment-summary`                                                                                                                             |
| Reports              | `/reports`                   | `receivables`, `customer-risk`, `cash-flow`                                                                                                                                                                                        |

The full list with permissions is in [Backend Schema, section 9](05-BACKEND-SCHEMA.md).

---

## 8. Core business rules in code

### 8.1 Stock is a ledger

- `inventory_movements` is **append-only**. Types: `OPENING`, `PURCHASE`, `SALE`, `RETURN`, `DAMAGE`, `ADJUSTMENT`.
- Current stock = `SUM(base_quantity)` for a product. Quantities are stored in the product's **base unit**; packaging units convert through `conversion_to_base`.
- A database `CHECK` ties each movement type to the right source row and sign (a `SALE` must point to an invoice item and be negative, and so on).
- A **sale movement** is created when a delivery is marked `DELIVERED`. Before inserting it, the server takes a **PostgreSQL advisory lock** on the product and checks that stock is sufficient.

### 8.2 Orders and invoices

- Order statuses: `PENDING`, `CONFIRMED`, `PARTIALLY_FULFILLED`, `COMPLETED`, `CANCELLED`. The partly-fulfilled and completed states are **derived** from how much has been invoiced.
- An invoice may cover part of an order. For each product the invoiced total may not exceed the ordered quantity.
- The server checks that line totals add up to the invoice totals.
- A new invoice always starts as `UNPAID`. Its status is **derived** from payments: `UNPAID`, `PARTIALLY_PAID`, `PAID`. Only an unpaid invoice with no active delivery can be cancelled.

### 8.3 Payments

- Payment methods: `CASH`, `UPI`, `BANK_TRANSFER`, `CHEQUE`, plus system methods `RETURN_CREDIT` and `CREDIT_APPLIED`.
- A payment lock (advisory lock on the invoice) makes sure two payments cannot both pass the "amount within remaining balance" check.
- A cancelled invoice rejects payments and credit.
- **Apply credit** uses a database row lock on the customer, so one credit balance cannot be spent twice. Each application gets a unique reference.

### 8.4 Returns

- Flow: `REQUESTED` → `APPROVED` → `RECEIVED` (or `REJECTED` / `CANCELLED`).
- A return line cannot exceed the quantity sold minus quantities already returned or requested.
- On **receive**, inside one transaction and under a row lock on the return: add a `RETURN` stock movement, compute credit from the invoice line value (line total, including discount and tax), apply it to the invoice as a `RETURN_CREDIT` payment, and add any remainder to the customer's `credit_balance`.

### 8.5 Purchases

- Statuses: `PENDING`, `PARTIALLY_RECEIVED`, `RECEIVED`, `CANCELLED`. Receiving adds `PURCHASE` movements and updates `received_quantity`.

---

## 9. Cash & Credit analytics engine

Lives in `backend/app/services/analytics/`:

| File                | Role                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| `config.py`       | All thresholds in one place                                                |
| `loaders.py`      | Read invoices, payments, returns and dues from the database                |
| `calculations.py` | **Pure functions** with no database access, so they are easy to test |
| `models.py`       | Plain data classes for results                                             |

The `/reports` routes only call the loaders and the calculations. They **never write** data.

### 9.1 Receivables aging

Unpaid invoice balances are grouped by days past due: not yet due, 1–30, 31–60, 61–90, 90+.

### 9.2 Customer risk score (0 to 100, lower is safer)

History used: the last **180 days**. A customer needs at least **3** settled invoices, otherwise the band is `INSUFFICIENT_HISTORY` ("Too new to rate").

| Part           | Maximum points | How it is worked out                                     |
| -------------- | -------------- | -------------------------------------------------------- |
| Lateness       | 40             | Average days late on settled invoices, capped at 45 days |
| Late frequency | 20             | Share of settled invoices that were paid late            |
| Overdue now    | 25             | Age of the oldest overdue invoice, capped at 60 days     |
| Credit used    | 15             | Starts at 70% of the credit limit, full points at 100%   |

| Score          | Band         |
| -------------- | ------------ |
| Below 25       | `RELIABLE` |
| 25 to below 50 | `WATCH`    |
| 50 and above   | `RISKY`    |

**Trend:** average lateness in the latest 90 days compared with the previous 90 days (needs 2 settled invoices in each window): `IMPROVING`, `STABLE`, `WORSENING` or `UNKNOWN`.

### 9.3 Suggested credit limit

Rule-based and non-binding, rounded up to ₹1,000. Each suggestion carries its reasons.

| Band                     | Suggested limit                                                                                                                           |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `RELIABLE`             | The larger of the current limit and **1.2 x the peak outstanding** amount in the last 180 days                                      |
| `WATCH`                | Keep the **current limit**                                                                                                          |
| `RISKY`                | The larger of the **current outstanding** amount and **0.5 x the current limit** (never below what the customer already owes) |
| `INSUFFICIENT_HISTORY` | No suggestion                                                                                                                             |

### 9.4 Five-week cash outlook

For five weekly buckets: expected money in (each open invoice is placed on its due date plus the customer's **median days late**, capped at 30) and expected money out (supplier dues on their due dates). A **cautious** series leaves out money from `RISKY` customers. The screen adds the owner's optional opening balance in the browser only; it is not saved.

### 9.5 Explainability

Every score, band and suggestion returns a `reasons` list. The UI shows plain-language sentences first and the raw reasons under "calculation details".

---

## 10. Frontend technical design

### 10.1 Application structure

- `main.jsx` wraps the app in `SplashGate` (logo intro, once per browser session).
- `App.jsx` sets up providers (toast, confirm dialogs, router, auth) and routes (see [App Flow](03-APP-FLOW.md)).
- `ProtectedRoute` guards private pages. `Layout` renders the sidebar, mobile top bar, account menu and the page area, inside an `ErrorBoundary` keyed by path.
- `/` is the public **landing page** for signed-out visitors and redirects signed-in users to `/dashboard`.

### 10.2 State and data loading

- **No global store.** Pages load their own data with `useEffect` and keep it in local state. Auth state lives in `AuthProvider`.
- **GET cache** in `api/client.js`: responses are reused for **30 seconds**, identical in-flight requests share one network call, and **any write clears the cache**. `/auth/*` is never cached. A "Refresh" button clears it on purpose.
- Loading states use **skeleton** components instead of spinners.

### 10.3 Security on the client

- Cookies are HttpOnly, so no token is kept in `localStorage`.
- The CSRF cookie value is sent as `X-CSRF-Token` on every write.
- A `401` on a normal request sends the user to `/login` and remembers the page; a `401` from the first "am I signed in?" check (`GET /auth/me`) is **not** treated as an expired session, which keeps the landing page, signup and invitation pages open to signed-out visitors.
- React escapes all rendered text, which prevents most cross-site scripting.

### 10.4 Performance

- Per-request auth work is kept light: `last_seen_at` is updated at most once a minute instead of on every request.
- Dashboard and report screens request their data in parallel.
- Animations use only `opacity` and `transform`, and stop for users who prefer reduced motion.

---

## 11. Configuration (environment variables)

| Variable                                     | Purpose                                                    | Default                                       |
| -------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------- |
| `DATABASE_URL`                             | PostgreSQL connection string                               | required                                      |
| `ENVIRONMENT`                              | `development` or `production`                          | `development`                               |
| `SESSION_TOKEN_PEPPER`                     | Secret for hashing session tokens (32+ chars)              | required in production                        |
| `OTP_HMAC_KEY`                             | Secret for hashing OTPs (32+ chars)                        | required in production                        |
| `JWT_SECRET_KEY`                           | Legacy, unused by login                                    | optional                                      |
| `SESSION_IDLE_MINUTES`                     | Idle session timeout                                       | 30                                            |
| `SESSION_ABSOLUTE_HOURS`                   | Maximum session length                                     | 8                                             |
| `PASSWORD_RESET_GRANT_MINUTES`             | Reset grant lifetime                                       | 10                                            |
| `FAILED_LOGIN_ATTEMPT_THRESHOLD`           | Failures before lockout                                    | 5                                             |
| `LOGIN_LOCKOUT_MINUTES`                    | Lockout length                                             | 15                                            |
| `CORS_ALLOWED_ORIGINS`                     | Comma-separated allowed origins                            | local dev origins                             |
| `COOKIE_NAME`, `CSRF_COOKIE_NAME`        | Cookie names                                               | `dukaanpulse_session`, `dukaanpulse_csrf` |
| `COOKIE_DOMAIN`, `COOKIE_SECURE`         | Cookie scope and secure flag                               | unset                                         |
| `SMS_PROVIDER`                             | `disabled`, `console` (prints OTP) or `generic_http` | `disabled`                                  |
| `SMS_HTTP_URL`, `SMS_HTTP_AUTHORIZATION` | Settings for the HTTP SMS gateway                          | unset                                         |
| `DEMO_SEED_ALLOWED`                        | Allows the demo seeding script                             | `false`                                     |
| `BUSINESS_TIMEZONE`                        | Business time zone                                         | `Asia/Kolkata`                              |

**Production rules enforced at startup** (`validate_production_security` in `core/config.py`): `SESSION_TOKEN_PEPPER` and `OTP_HMAC_KEY` must be set (32+ characters), `COOKIE_SECURE` must be on, and `SMS_PROVIDER` must not be `console`. `CORS_ALLOWED_ORIGINS` may never contain `*`, because cookies are sent with credentials. In production the frontend and the API must be **same-site** (for example `app.example.com` and `api.example.com`) so the `SameSite=Lax` cookies are sent.

---

## 12. Deployment

| Piece      | Run as                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------- |
| Database   | Managed PostgreSQL                                                                                |
| API        | `uvicorn app.main:app` behind HTTPS (with proxy headers enabled if a reverse proxy is used)     |
| Frontend   | `npm run build`, serve the `dist/` folder as static files                                     |
| Migrations | Run `backend/sql/000` to `005` in order (see [Implementation Plan](06-IMPLEMENTATION-PLAN.md)) |

A detailed checklist is in `docs/deployment-checklist.md`.

---

## 13. Testing

- **Automated:** pytest suites in `backend/tests` covering analytics calculations, authentication (logic and HTTP), permissions, user management, reports, security checks, configuration, the demo seeder, and a **route audit** that fails if an endpoint has no permission.
- **Demo data:** `scripts/seed_demo.py` builds synthetic customers with different payment behaviours (for example "Reliable Retailers", "Chronic Late Stores", "Worsening Wholesale", "Near Limit Mart", "Newly Opened Shop", "Credit Holder Traders") so the analytics can be checked end to end.
- **Manual checks** for the flows in [App Flow](03-APP-FLOW.md), especially: concurrent delivery, double-click on return receive, credit applied twice, and a viewer trying to write.
- **Not yet covered:** automated browser (end-to-end) tests and load tests.

---

## 14. Non-functional requirements

| Area                      | Requirement                                                                                                                                         |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Security**        | Hashed tokens and OTPs, Argon2 passwords, HttpOnly cookies, CSRF protection, role checks on the server, tenant isolation, rate limits, audit events |
| **Correctness**     | Money and stock rules enforced on the server and in database constraints                                                                            |
| **Performance**     | Skeleton screens at once, repeat visits served from cache, parallel loading                                                                         |
| **Reliability**     | Writes happen in transactions; locks prevent double-spending and overselling                                                                        |
| **Accessibility**   | Keyboard use, visible focus, labels on inputs, readable contrast, reduced-motion support                                                            |
| **Responsiveness**  | Works from small phones to wide desktops                                                                                                            |
| **Browser support** | Current versions of Chrome, Edge, Firefox and Safari                                                                                                |
| **Maintainability** | Thresholds in one config file, pure calculation functions, one router per area                                                                      |

---

## 15. Data handling and privacy

- Personal data stored: name, username, mobile number, password hash, and business contact details of customers and suppliers.
- Passwords, session tokens, OTPs and reset tokens are never stored in plain form.
- Audit events store the event type, user, workspace and time, not secrets.
- Demo seeding is blocked unless `DEMO_SEED_ALLOWED=true`, and must never be run on a real database.

---

## 16. Known gaps and technical debt

These are real, known issues. They are listed here so nobody assumes they are solved. Priorities are in the [Implementation Plan](06-IMPLEMENTATION-PLAN.md).

| #  | Gap                                                                                                       | Why it matters                                                                                                                                    |
| -- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **Money is handled as floating-point in Python** (database columns are `NUMERIC`).                | Tiny rounding errors can appear. Should use `Decimal` end to end.                                                                               |
| 2  | **Delivery status changes have no row lock.**                                                       | Two simultaneous "Delivered" clicks could create duplicate stock movements.                                                                       |
| 3  | **Invoice unit price and discount come from the client.**                                           | A user with invoice permission can bill at any price. Prices should come from the product, or overrides need a permission.                        |
| 4  | **List endpoints return all rows, with no pagination.**                                             | Invoices, payments and returns get slow as data grows.                                                                                            |
| 5  | **Advisory lock keys are raw ids shared across tenants and record types.**                          | Unrelated actions can wait on each other. Use a two-part key.                                                                                     |
| 6  | **Rate limits use the direct client IP.**                                                           | Behind a proxy everyone shares one IP unless proxy headers are trusted. Any country's number is accepted for OTP, which allows SMS-pumping fraud. |
| 7  | **Login revokes all other sessions, and lockout is per account.**                                   | A third party who knows a username can lock someone out for 15 minutes.                                                                           |
| 8  | **Account existence can be guessed** (signup conflict message, forgot-password timing).             | Minor privacy leak.                                                                                                                               |
| 9  | **`/health/db` needs a permission no role has.** `/health` shows a demo flag.                   | A health check that cannot be used.                                                                                                               |
| 10 | **Several routes accept an untyped `dict` body** (apply credit, invoice cancel, delivery status). | No schema validation.                                                                                                                             |
| 11 | **The tenant filter covers ORM SELECTs only** and the database has no row-level security.           | New bulk updates or raw SQL could bypass tenant filtering.                                                                                        |
| 12 | **Legacy JWT settings and `token_version` remain.**                                               | Dead code that can confuse readers.                                                                                                               |
| 13 | **No automated browser tests or load tests.**                                                       | Regressions in screens and performance are found by hand.                                                                                         |
