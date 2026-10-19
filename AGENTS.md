# DukaanPulse: standing instructions for AI agents (authentication & authorization work)

## What this is

DukaanPulse is an existing, working ERP for a wholesale distributor: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL (psycopg v3, hosted on Neon) in backend/, and React 18 + Vite + react-router 6 + axios in frontend/ (plain JavaScript, plain CSS). If AI_CONTEXT.md exists in the repo root, read it first. Always READ THE CODE before trusting any document. If code and a document disagree, the code wins, and you say so.

## The project we are doing

Add login and role-based access control, in small phases. Every phase must leave the app working. Phases are given to you one at a time. Do ONLY the phase you are given, then stop.

## Safety rules (always apply)

1. Never read, print, log or commit .env files or any secret. Never put real secrets in code, tests, docs or examples.
2. Never connect to, or run anything against, the real database. All database changes are delivered as SQL files in backend/sql/ (numbered, with a comment header explaining what and why). The human runs them manually in the Neon SQL editor. Never write destructive SQL (DROP, TRUNCATE, DELETE of data). Additive changes only, unless told otherwise.
3. Do not change existing API request/response shapes or business rules. Only add authentication/authorization around them. If you believe an existing behaviour must change, stop and explain instead.
4. Minimal diffs. Do not reformat or "clean up" unrelated code. Some files use Windows CRLF line endings: preserve each file's existing line endings.
5. Add only the dependencies a phase needs. Pin versions, and name every new dependency and why in your report.
6. If anything in these instructions conflicts with what you find in the code, stop and ask rather than guess.

## Codebase conventions to follow

Backend

- Models live in app/models/ and every model must be imported in app/models/__init__.py. Routers live in app/routers/ and each is included in app/main.py. Shared logic lives in app/services/. Settings come from app/core/config.py (reads .env).
- Primary keys are BigInteger Identity. Status-like columns are strings guarded by DB CHECK constraints. Timestamps are timestamptz with server default now().
- Write endpoints use try/except: HTTPException -> rollback and re-raise, IntegrityError -> rollback and 409, SQLAlchemyError -> rollback and 500.
- The frontend shows the backend's `detail` text to end users, so keep `detail` messages human-readable and specific, never technical.
- Some endpoints take `data: dict = Body(...)`. Leave their contracts alone.
  Frontend
- Reuse the existing patterns: api/client.js (axios + extractErrorMessage, which already maps 401/403 to friendly text), ToastProvider (toast.success / toast.error), ConfirmProvider (await confirm({...}) before destructive actions), Modal, Feedback (Spinner / EmptyState / ErrorBanner), formValidation.js (needs each <label></label> inside a `.field` wrapper), and the design tokens in src/index.css. Success toast wording: "[Entity] [action] successfully."
- No new UI libraries and no auth libraries on the frontend.

## Decisions already made (do not re-open; flag only a real problem)

D1 Passwords: Argon2id via a maintained library. Never log, return or store plaintext. Minimum length 10.
D2 Sessions: signed JWT access token (HS256) with claims `sub` (user_id), `iat`, `exp`. NEVER trust role or permissions from the token. On every request load the user from the database and reject if missing or INACTIVE, so deactivation and role changes apply immediately.
D3 Lifetime: ACCESS_TOKEN_EXPIRE_MINUTES default 480, configurable. No refresh tokens in v1.
D4 Transport: `Authorization: Bearer <token>`. The frontend keeps the token in localStorage (accepted tradeoff for portability; mitigations: short lifetime, no dangerouslySetInnerHTML anywhere).
D5 Login identifier is a `username` (not email): case-insensitive, unique. No self-registration; admins create users. The first admin is created by a CLI script, never by default credentials.
D6 Login uses FastAPI's OAuth2PasswordRequestForm (form-encoded) so Swagger's Authorize button works.
D7 Login errors are generic ("Incorrect username or password.") and identical for unknown user and wrong password. Hash a dummy password for unknown users so timing does not reveal which usernames exist.
D8 One role per user: ADMIN, SALES, WAREHOUSE, ACCOUNTS, VIEWER. The role -> permissions matrix lives in ONE backend file. The backend is the only authority. /auth/me returns the user's permission list and the frontend only reads it (no role logic duplicated in the frontend). Hiding things in the UI is cosmetic; the backend enforces.

## Decisions made after the Phase 0 audit (these override anything earlier)

D9  Permission names: one resource per area, exactly: categories, products, customers, suppliers, purchases, orders, invoices, deliveries, payments (customer payments), purchase_payments (supplier payments, SEPARATE from payments), returns (actions: read, write, approve, receive), inventory, dashboard, system, users. Actions: read, write, plus approve / receive / manage where listed. In the role matrix, "catalog" means products + categories. GET /health/db requires system:read (ADMIN only).
D10 The env var is JWT_SECRET_KEY (not SECRET_KEY). No default value. The app refuses to start if it is missing or shorter than 32 characters. .env.example holds only an obviously non-working placeholder.
D11 /docs, /redoc and /openapi.json stay public in development so Swagger's Authorize button works (tokenUrl = "auth/login"). They are disabled when ENVIRONMENT=production (hardening phase).
D12 Approved, pinned dependencies: pwdlib[argon2], PyJWT, python-multipart (python-multipart is added in the phase that adds the login endpoint). JWT `sub` is the user id as a STRING. Do not touch the existing unpinned dependencies.
D13 Password lifecycle: every user can change their own password (must supply the current one); an ADMIN can reset any user's password by setting a new one.
D14 Tests ship IN THE SAME PHASE as the code they cover. Never defer them to a final phase. The route-audit test (every non-public route requires login, later also an explicit permission) lands in the phase that enforces it.
D15 The first-admin script lives at backend/app/scripts/create_admin.py and runs as `python -m app.scripts.create_admin`. Not in backend/scripts/.
D16 Database baseline: the human adds backend/sql/000_baseline_schema.sql (a pg_dump of the live schema). Never invent or "fix" the baseline. Your SQL files start at 001 and are additive only. Known unrelated mismatch: Delivery.invoice_id has unique=True in the ORM but the live DB uses a partial unique index. Do NOT touch it during the auth phases.
D17 The phase numbering and scope in the prompts the human gives you are authoritative. The Phase 0 report's phase list was a proposal and is not.
D18 Pages call several GET endpoints when they open. Whenever roles are applied, every page a role can see in the sidebar must load completely for that role, with no 403 from any endpoint that page calls.

D19 httpx is approved as a DEV-ONLY dependency, in a new file backend/requirements-dev.txt (pinned). It is never added to requirements.txt. It is used for FastAPI TestClient tests.

## Public routes (everything else requires login)

GET /, GET /health, POST /auth/login.

## Every phase ends with this report, then you stop

- Files changed (paths) and new dependencies
- SQL the human must run (file name), or "none"
- What you actually ran/verified, and what you could NOT verify (be explicit)
- Manual test steps for the human
- Risks / questions
  Do not begin the next phase.
