# DukaanPulse: standing instructions for AI agents (authentication & authorization work)

## What this is

DukaanPulse is an existing, working ERP for a wholesale distributor: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL (psycopg v3, hosted on Neon) in backend/, and React 18 + Vite + react-router 6 + axios in frontend/ (plain JavaScript, plain CSS). If AI_CONTEXT.md exists in the repo root, read it first. Always READ THE CODE before trusting any document. If code and a document disagree, the code wins, and you say so.

## The project we are doing

Make authentication and authorization production-ready in small, reviewable phases. Every phase must leave the app working. The human provides phase approval; do ONLY the currently approved phase, then stop.

The approved product direction and full handoff workflow live in `AUTH_IMPLEMENTATION_PLAN.md`. Read it before any authentication/authorization work. The plan defines the target; the actual repository, SQL files, migrations, and tests are evidence of current implementation. If they disagree, report the discrepancy and do not silently guess.

The next task is **Phase 0: read-only audit only**. Do not implement signup/login, edit code, change schema/migrations, or change database data during Phase 0. Produce the audit report and wait for approval before Phase 1.

## Safety rules (always apply)

1. Never read, print, log or commit .env files or any secret. Never put real secrets in code, tests, docs or examples.
2. Never read, print, log, or expose database connection strings or credentials. AI agents must not directly connect to or execute SQL against Neon production or demo databases. Database changes are delivered as reviewed SQL files in `backend/sql/` (numbered, with a comment header explaining what and why); the human runs them manually. Ordinary migrations are additive. A database reset/data deletion is a separate destructive operation, not a migration: it requires a reviewed reset procedure, verification of the exact Neon branch/environment, a documented backup/recovery decision, and explicit human confirmation immediately before execution. Never run destructive SQL or trigger a reset yourself. Never assume a connection string points to demo or production.
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

## Authentication & authorization decisions

Read `AUTH_IMPLEMENTATION_PLAN.md` for the complete approved requirements, edge cases, API proposals, phases, tests, and handoff instructions. The decisions below supersede older authentication decisions where they conflict. Do not re-open an approved product decision unless repository evidence reveals a concrete security or compatibility problem; explain the evidence and ask before changing direction.

A1 Product flow:
- Public owner signup is required.
- Signup fields: full name, business name, mobile number, username, password, and confirm password.
- Mobile OTP verification is required before the owner account is activated.
- Successful verified signup creates one business workspace and its owner membership initially, atomically.
- Login accepts either username or verified mobile number plus password. Preserve existing username login.
- Staff join through workspace-bound invitations; there is no public staff signup path.
- Password recovery uses OTP sent to the account's verified mobile number.
- Existing users must be considered explicitly; do not silently lock them out or invent mobile numbers. The legacy-user verification/migration policy is a Phase 0 decision based on actual schema and user state.

A2 Passwords: keep Argon2id through a maintained library unless the audit finds a concrete issue. Never log, return, or store plaintext. The current minimum length is 10; Phase 0 must reconcile this with the approved plan's recommendation to evaluate a 12-character minimum before implementation. Support password managers and paste, and never silently truncate.

A3 Session architecture: the approved preference is database-backed opaque sessions, with a session secret generated using a cryptographically secure RNG and only its hash stored server-side. Validate session and current user status on protected requests. Immediate logout/revocation, password-reset revocation, session rotation after login, idle/absolute expiry, and concurrent-session behavior must be specified. Confirm compatibility with the existing code/schema during Phase 0 before implementation.

A4 Browser transport: use HttpOnly cookies, Secure in production, an appropriate SameSite policy, narrow scope, and CSRF protection for state-changing requests. Do not store authentication tokens in `localStorage` or `sessionStorage`. Use explicit CORS origins; never use wildcard origins with credentialed CORS. Cookie settings must match the actual frontend/backend deployment topology.

A5 Login identifiers: username is case-insensitive and unique; mobile number is normalized consistently and unique for the account model. Login accepts username OR verified mobile plus password. Unknown-user and wrong-password responses must not reveal account existence. Preserve timing-hardening with a dummy password hash or an equivalent tested mitigation.

A6 API contract: inspect existing API contracts before changing them. The new browser login may use a JSON request and cookie response if that is the approved implementation contract; do not keep OAuth2PasswordRequestForm solely for Swagger if it conflicts with the approved browser flow. If Swagger authentication is needed in development, document a safe compatible approach separately. Existing unrelated API request/response shapes and business rules remain unchanged.

A7 Authorization: the backend is the only security authority. `/auth/me` returns the authenticated user's safe profile, workspace membership/context, and effective permission list. The frontend may use permissions to show/hide UI, but every protected backend route/service must enforce authentication, role permission, and workspace ownership. Do not trust role or permissions supplied by the client or token.

A8 Roles: preserve the existing role matrix where compatible, but explicitly distinguish the business owner from staff roles and any platform-operator/admin role. Public signup must never grant platform-admin privileges. Existing roles are `ADMIN`, `SALES`, `WAREHOUSE`, `ACCOUNTS`, `VIEWER`; inspect `AGENTS.md`, code, and tests to determine the current meaning of `ADMIN`. Do not silently equate `ADMIN` with business owner. Keep the role-to-permission matrix in one backend source of truth.

A9 Lockout: target policy is 5 consecutive wrong passwords -> 15-minute temporary lockout. After lock expiry, a fresh attempt cycle begins; the next wrong password counts as 1/5. Successful login resets failure state. Enforce concurrency-safe account-level behavior plus IP/network rate limiting. Tests must cover expired-lock + wrong-password and expired-lock + correct-password.

A10 OTP: proposed starting policy is 6 digits, 5-minute expiry, 30-60 second resend cooldown, maximum 5 wrong attempts per challenge, purpose-bound and single-use. Enforce per-phone, per-IP and global/provider rate limits. Never store/log plaintext OTPs. Use a secure keyed hash/HMAC or equivalent design suitable for low-entropy OTPs. Test/dev bypass must be isolated and impossible to enable in production. Final provider and configuration are decided after audit.

A11 Password lifecycle: users can change their own password after supplying the current password. Recovery uses verified mobile OTP. By default, password reset/change revokes all existing sessions; confirm any exception during Phase 0. Platform or business admin reset capabilities must be scoped to explicitly authorized accounts and never bypass audit logging.

A12 OTP provider: not yet selected. Keep an interface so signup/recovery business logic is vendor-independent. Evaluate provider cost, India delivery, template/consent requirements, delivery reports, rate limits, secrets management and failure behavior before selecting.

A13 Sessions and API behavior: proposed endpoints and cookie/CSRF details are in `AUTH_IMPLEMENTATION_PLAN.md`. Inspect existing endpoints and keep compatibility where safe. Any contract changes must be documented with frontend changes and regression tests.

A14 Testing: tests ship in the same phase as the code they cover. Test signup, OTP expiry/replay/resend/rate limits, duplicate/concurrent signup, login identifier variants, lockout, cookies, CSRF, logout/session replay, password recovery, invitation lifecycle, route permissions, and cross-workspace access. Do not defer security tests to a final phase.

A15 First platform admin: keep the existing first-admin script at `backend/app/scripts/create_admin.py` and run it as `python -m app.scripts.create_admin` if still needed after the role model audit. Never create an admin using default credentials or public signup. Update this script only in an approved phase.

A16 Database baseline: preserve the repository's migration conventions. If `backend/sql/000_baseline_schema.sql` exists, never invent or "fix" it. SQL files should be numbered and additive unless a separately approved, guarded reset procedure is needed. Known unrelated mismatch: `Delivery.invoice_id` has `unique=True` in the ORM but the live DB uses a partial unique index. Do NOT touch it during auth work unless the human explicitly approves a separate task.

A17 Phase scope: the human's latest explicit phase instruction is authoritative. The next task is Phase 0 read-only audit. Do not begin Phase 1 without reviewing the Phase 0 report and receiving approval.

A18 Page and permission completeness: pages call several GET endpoints when they open. Whenever roles are applied, every page a role can see in the sidebar must load completely for that role, with no unexpected 403 from endpoints the page requires.

A19 Test environment: `httpx` is approved as a DEV-ONLY dependency in `backend/requirements-dev.txt` (pinned) if still needed for FastAPI TestClient tests. It must not be added to `requirements.txt` unless separately approved.

## Decisions made after the earlier auth audit (D9 onward)


D9  Permission names: one resource per area, exactly: categories, products, customers, suppliers, purchases, orders, invoices, deliveries, payments (customer payments), purchase_payments (supplier payments, SEPARATE from payments), returns (actions: read, write, approve, receive), inventory, dashboard, system, users. Actions: read, write, plus approve / receive / manage where listed. In the role matrix, "catalog" means products + categories. GET /health/db requires system:read (ADMIN only).
D10 If JWTs remain in use for any approved purpose after the session architecture audit, the env var is `JWT_SECRET_KEY` (not `SECRET_KEY`), with no default value and a minimum 32-character secret. `.env.example` holds only an obviously non-working placeholder. If the approved browser-session design removes JWT use from auth, do not retain or require an unused JWT secret solely because of this historical decision.
D11 `/docs`, `/redoc` and `/openapi.json` may stay public in development for API exploration and are disabled when `ENVIRONMENT=production` (hardening phase). Do not assume Swagger's Bearer `Authorize` button works with cookie-based sessions; document and test the chosen development authentication workflow without weakening production security.
D12 Existing approved dependencies include `pwdlib[argon2]`, PyJWT, and `python-multipart` (added when required by an endpoint). Reuse installed dependencies where appropriate. A database-backed session design may not need PyJWT for browser auth; do not remove dependencies or alter unrelated unpinned dependencies without evidence and approval. Pin every newly added dependency and explain why.
D13 Password lifecycle: every user can change their own password after supplying the current one. Password recovery uses verified mobile OTP. Any administrator reset capability must be explicitly scoped to the approved owner/platform-admin model, audited, and must revoke sessions by default.
D14 Tests ship IN THE SAME PHASE as the code they cover. Never defer them to a final phase. The route-audit test (every non-public route requires login, later also an explicit permission) lands in the phase that enforces it.
D15 The first-admin script lives at backend/app/scripts/create_admin.py and runs as `python -m app.scripts.create_admin`. Not in backend/scripts/.
D16 Database baseline: if `backend/sql/000_baseline_schema.sql` exists, never invent or "fix" it. Inspect actual repository files to determine whether the human still needs to add it. New SQL files follow the existing numbered migration convention and are additive for ordinary changes. A data reset is a separate, explicitly approved operation with target verification and recovery planning, never an ordinary auth migration. Known unrelated mismatch: Delivery.invoice_id has unique=True in the ORM but the live DB uses a partial unique index. Do NOT touch it during auth phases.
D17 The phase numbering and scope in the prompts the human gives you are authoritative. The Phase 0 report's phase list was a proposal and is not.
D18 Pages call several GET endpoints when they open. Whenever roles are applied, every page a role can see in the sidebar must load completely for that role, with no 403 from any endpoint that page calls.

D19 httpx is approved as a DEV-ONLY dependency, in a new file backend/requirements-dev.txt (pinned). It is never added to requirements.txt. It is used for FastAPI TestClient tests.

## Analytics project: "Cash & Credit Intelligence" (decisions D21-D31)

D21 Goal: real business use AND portfolio. Every number must be explainable: each metric returns its inputs and a plain-language reason list, and the UI shows the formula. Outputs are SUGGESTIONS; nothing is ever applied automatically (no auto credit-limit changes, no auto-blocking).
D22 Honesty over polish: with too little history say "Not enough history" and why (need N settled invoices). Never invent a score. No machine learning in v1; rule-based and transparent.
D23 Architecture: backend/app/services/analytics/ with loaders.py (DB -> plain dataclasses, a few BULK queries, no per-customer query loops), calculations.py (PURE functions: no DB, no clock; today is passed in), config.py (every threshold in one documented place). Routers call loaders then calculations. Tests target the pure functions with hand-built data.
D24 Definitions:

- Due date = invoice_date + customer.payment_terms_days. Cancelled invoices are ignored everywhere.
- Credit rows (payment_method RETURN_CREDIT, CREDIT_APPLIED) are not customer payment behaviour. Real payments are CASH, UPI, BANK_TRANSFER, CHEQUE. For BEHAVIOUR metrics, owed = total_amount minus the invoice's credit rows. An invoice is SETTLED on the payment_date of the real payment that makes cumulative real payments reach what is owed. If owed is 0 it is excluded from lateness metrics.
- Days late of a settled invoice = max(0, settle_date - due_date). Overdue days of an OPEN invoice = max(0, today - due_date) while remaining > 0, where remaining = total_amount minus ALL payments including credit rows.
- Aging buckets of OPEN remaining balances by days past due: not_yet_due, 1-30, 31-60, 61-90, 90+.
- customers.credit_balance (credit WE owe them) is shown separately and never netted against overdue.
  D25 Risk score 0-100 (higher = riskier); defaults live in config.py. Window = settled invoices with settle_date in the last 180 days; need >= 3 of them, else band INSUFFICIENT_HISTORY (still show open overdue and aging). Components: lateness 0-40 = 40*min(avg_days_late,45)/45; frequency 0-20 = 20*share of window invoices settled late; overdue_now 0-25 = 25*min(oldest overdue open days,60)/60; utilisation 0-15 = 15*clamp((outstanding/credit_limit - 0.7)/0.3, 0, 1) (0 plus the note "no credit limit set" when credit_limit is 0). Bands: <25 RELIABLE, 25-49 WATCH, >=50 RISKY. Trend: average days late over the last 90 days vs the previous 90 days (needs >=2 invoices in each) -> IMPROVING / STABLE / WORSENING, else null.
  D26 Suggested credit limit (suggestion only): RELIABLE -> max(current_limit, 1.2*peak outstanding in the last 180 days) rounded up to the nearest 1000; WATCH -> keep current_limit; RISKY -> max(current outstanding, 0.5*current_limit) rounded to the nearest 1000, never below current outstanding. Return the formula inputs with it.
  D27 30-day cash projection: weekly buckets for the next 5 weeks from today. Expected IN per open invoice = its remaining, on max(due_date, today) + the customer's median days late (0 if insufficient history, capped at 30). Expected OUT per non-cancelled purchase with remaining > 0 = purchase_date + supplier.payment_terms_days (today if already past); remaining = total_amount - purchase_payments. We do NOT track cash on hand: return net movement per week and cumulative net. The UI may take an OPTIONAL opening balance typed by the user (never stored). Also return a "conservative" series that excludes customers banded RISKY from expected IN.
  D28 Permission: new resource `reports`, action `read`; ADMIN and ACCOUNTS only. The Reports page may call ONLY /reports/* endpoints (so D18 holds). Update the permission matrix, route audit and page-mapping tests.
  D29 Demo data: the synthetic generator talks to the real HTTP API (so every business rule holds), logs in with a password typed at a prompt (never a CLI arg or env var), is deterministic (fixed seed), REFUSES to run unless products, customers, suppliers, purchases and orders are all empty on the target, prints the base URL and requires typing SEED DEMO. It must never be pointed at the real database. Planted personas are defined in ONE data structure shared with tests.
  D30 Real data is never committed; screenshots and README use demo data only. An optional VITE_DEMO_BANNER flag shows "Demo data" on the Reports page.
  D31 Data-quality note: payment_date must be the date the money actually arrived; say so in the UI help and docs.
- D32 Run Python and tests ONLY with backend\venv\Scripts\python.exe (from backend/). If imports are missing there, STOP and tell me. Never stub modules, skip tests, or install packages to make tests load. A test total counts only if it comes from one `discover` run; never add up partial runs.
  D33 `tzdata` is an approved, pinned dependency (timezone support on Windows).

## Required handoff plan and database-reset safeguards

- `AUTH_IMPLEMENTATION_PLAN.md` is the approved detailed handoff plan. Keep it updated when the human approves changes to the product direction.
- Start with a read-only Phase 0 audit. Do not modify code, SQL, migrations, or data until the audit is reviewed and the next phase is approved.
- The user has said that demo-seeded data on a separate Neon demo branch and data on the production branch may be cleared. This is permission to plan a reset, not permission to execute it immediately. Before any reset, verify the exact branch/environment using safe metadata checks, never print credentials, document backup/recovery, provide a reviewed reset procedure, and obtain explicit confirmation immediately before the destructive operation. Agents must not directly execute destructive SQL against Neon. The human runs approved SQL manually.
- Reset demo and production separately. Never infer environment from a filename or connection-string variable name alone. Do not reset any environment if its identity is ambiguous.
- After approved reset and schema implementation, demo data must be regenerated using the project's deterministic demo workflow. Never let a production process run demo seed/reset logic.
- Do not include secrets, `.env`, `.env.demo`, `venv`, `.venv`, `node_modules`, database dumps, or real user data in shareable archives.

## Public routes (review during Phase 0)

Current known public routes from the earlier implementation are `GET /`, `GET /health`, and `POST /auth/login`. During Phase 0, audit the actual route table and classify the target public routes needed for signup, OTP verification/resend, password recovery, and invitation acceptance. Everything else must require authentication and, where relevant, explicit permission and workspace authorization. Keep health/docs exposure aligned with environment hardening rules. Do not assume this list is complete without checking code.

## Every phase ends with this report, then you stop

- Files changed (paths) and new dependencies
- SQL the human must run (file name), or "none"
- What you actually ran/verified, and what you could NOT verify (be explicit)
- Manual test steps for the human
- Risks / questions
  Do not begin the next phase.