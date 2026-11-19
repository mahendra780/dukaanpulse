# DukaanPulse Authentication & Authorization: Production Implementation Plan

**Status:** Planning approved; implementation not started\
**Document purpose:** This is the single handoff document for the next
ChatGPT conversation, Codex, or another AI coding agent. Read this
document and the repository's `AGENTS.md` before changing anything.\
**Project:** DukaanPulse\
**Current stack:** FastAPI, SQLAlchemy 2.x, Pydantic v2, PostgreSQL
(Neon, psycopg v3), React 18 + Vite, React Router 6, Axios, plain
JavaScript/CSS.\
**Current database rule:** `schema.sql` is the project's schema source
of truth. Inspect the actual repository and migration files before
proposing schema changes. Do not invent or silently change database
fields.\
**Important:** No code, schema, migrations, or database data have been
changed as part of creating this plan.

------------------------------------------------------------------------

## 1. Mission and outcome

Make DukaanPulse's authentication and authorization production-ready for
a multi-tenant wholesaler business application. This is not merely a
login-page task. The system must establish a user's identity, safely
manage sessions, create business workspaces, invite staff, and enforce
business/role permissions on every protected backend operation.

The system should borrow sound security patterns used by mature products
without copying their entire infrastructure. The chosen design should
fit this project's size, stack, and operational needs.

### Product decisions already approved

1.  Signup creates **one business workspace per owner account
    initially**.
2.  A new wholesaler owner signs up directly.
3.  Mobile ownership must be verified by OTP before account activation.
4.  Login accepts **username OR verified mobile number plus password**.
5.  Preserve existing username login compatibility.
6.  Staff join through owner/admin invitations, not public owner signup.
7.  Password recovery uses OTP sent to the account's verified mobile
    number.
8.  Browser authentication should use **HttpOnly, Secure cookies with
    CSRF protection**.
9.  Recommended session model: **database-backed opaque sessions**,
    subject to final repository/schema compatibility audit.
10. The user has stated that demo-seeded data in the isolated Neon demo
    branch can be deleted and data in the Neon production branch can
    also be cleared. This is permission to plan a reset, **not
    permission for an AI agent to immediately execute destructive
    database operations without verification and a final confirmation
    step**. Never assume which branch a connection string targets.

### Not approved yet / must be resolved during Phase 0

-   Actual current state of the production and demo Neon branches and
    their connection strings.
-   Exact existing schema/migration layout and whether `schema.sql`
    fully represents the live schema.
-   Exact SMS provider (evaluate options such as MSG91 or Twilio, or
    choose another provider). Keep an OTP provider interface so business
    logic is not tied to one vendor.
-   Exact password policy and breach-password screening requirements.
-   Session lifetime, idle timeout, absolute timeout, concurrent-session
    policy and device-management scope.
-   Whether every existing account must verify a mobile before its next
    login, or whether a controlled migration/grace period is required.
-   Exact workspace tables and whether any existing tables already model
    tenant membership.
-   Production CORS origins, frontend/backend domains, cookie
    domain/SameSite settings and deployment topology.
-   How production admin bootstrap will be handled securely.
-   Whether email is collected at all. Email must not be treated as
    verified unless separately verified.
-   Whether step-up verification/MFA is required for sensitive owner
    actions in v1.

------------------------------------------------------------------------

## 2. Scope

### In scope

-   Owner signup and mobile OTP verification.
-   Username + password and verified mobile + password login.
-   Password hashing and validation.
-   Secure browser session creation, rotation, renewal, logout and
    revocation.
-   CSRF protection for cookie-authenticated state-changing requests.
-   Forgot/reset/change password flows.
-   Failed-login lockout and request rate limits.
-   Business workspace creation and owner membership.
-   Invitation-based staff onboarding.
-   Roles and permissions using the existing role matrix where
    compatible.
-   Backend tenant isolation and permission enforcement.
-   Frontend signup/login/recovery/invitation pages, auth provider and
    route guards.
-   Audit/security logging without secrets.
-   Automated tests, migration tests, demo setup and production
    deployment checks.

### Out of scope unless separately approved

-   Rebuilding unrelated inventory, billing, analytics or supplier
    features.
-   Adding social login/OAuth login.
-   Replacing the entire application architecture.
-   Automatically deleting database data during ordinary startup or
    migration.
-   Changing business tables without a reviewed tenant-data plan.
-   Treating frontend-only route hiding as authorization.

------------------------------------------------------------------------

## 3. Repository and environment rules

Before any implementation, the agent MUST:

1.  Read `AGENTS.md` fully, especially database, auth, migration,
    testing and code-convention rules.
2.  Inspect the repository tree, existing auth
    router/service/model/schema files, frontend auth state/API
    client/routes, tests, SQL schema and every migration.
3.  Confirm the current branch and working tree. Do not overwrite
    unrelated user changes.
4.  Identify current auth endpoints and response contracts before
    changing them.
5.  Inspect `.env.example` and `.env.demo` templates without printing
    secrets. Never read secrets into chat output or logs.
6.  Map the Neon branch used by each environment using safe,
    non-destructive checks. Do not display full connection strings.
7.  Run baseline tests and frontend build before changing code,
    recording pre-existing failures separately.
8.  Produce an audit report and proposed schema/migration plan before
    implementing Phase 1.

Never: - Commit `.env`, `.env.demo`, API keys, passwords, OTPs, session
secrets, private keys or real customer data. - run destructive SQL
against a database until its identity has been verified and the user has
confirmed the exact target and action immediately beforehand. - use
`DROP SCHEMA`, `DROP DATABASE`, blanket `TRUNCATE`, or broad deletes as
a shortcut. - assume the local `.env` points to demo or production. -
change `schema.sql` without explaining how it stays consistent with the
project's migration strategy. - bypass tests to make a phase appear
complete.

------------------------------------------------------------------------

## 4. High-level user journeys

### 4.1 Owner signup

1.  Visitor opens Create Account.
2.  Enters full name, business name, mobile number, username, password
    and confirm password.
3.  Backend validates input and applies rate limits.
4.  Backend checks username/mobile uniqueness using normalized values
    and database constraints.
5.  Start an OTP challenge. Do not activate the user or create an
    accessible workspace yet.
6.  User enters OTP. OTP must be unexpired, unconsumed, purpose-bound
    and within attempt limits.
7.  On successful verification, perform an atomic operation to create:
    -   verified owner user account,
    -   business workspace,
    -   owner membership/role,
    -   required audit event,
    -   initial session only if the chosen policy allows immediate
        sign-in.
8.  Ensure retries, double-clicks, refreshes and concurrent requests
    cannot create duplicate users/workspaces.
9.  Issue a new secure session and redirect to the business dashboard or
    a minimal onboarding state.
10. Load current user, workspace membership and permissions from
    `/auth/me`.

**Design decision to validate:** For lower abuse risk, prefer creating a
pending signup/OTP challenge before activation, then create the final
user/workspace after OTP verification. If a pending record is needed, it
must expire and be safely cleaned up. Avoid storing plaintext OTPs or
passwords.

### 4.2 Login

1.  User enters username or mobile and password.
2.  Backend normalizes the identifier without changing its meaning.
3.  Lookup must be unambiguous. Username comparison policy should be
    case-insensitive if chosen, with a matching unique constraint.
4.  Verify password using Argon2 (preserve the existing proven password
    hashing implementation unless audit identifies a concrete issue).
5.  Deny inactive, disabled, unverified or locked accounts as policy
    requires. Responses must not leak whether an account exists.
6.  On successful login, rotate/create a new session identifier; never
    reuse a pre-authentication session.
7.  Set the session cookie with secure flags.
8.  Reset the failed-login state after a successful login and write a
    safe audit event.
9.  Frontend fetches `/auth/me` and renders only the authorized UI.
    Backend remains the authority for every operation.

### 4.3 Logout

-   Revoke the server-side session.
-   Clear the cookie with the same cookie path/domain attributes used to
    set it.
-   Require CSRF protection for the logout POST.
-   Subsequent replay of the old cookie must fail.
-   Define separately whether "log out this device" and "log out all
    devices" are supported in v1.

### 4.4 Forgot/reset password

1.  User submits mobile number.
2.  Return a generic response that does not reveal whether the account
    exists.
3.  Apply per-phone, per-IP and global provider rate limits.
4.  Verify a purpose-bound OTP.
5.  Permit a password reset only after valid verification, using a
    short-lived, single-use server-side reset grant or equivalent state.
6.  Hash the new password using Argon2.
7.  Revoke all existing sessions by default.
8.  Invalidate all outstanding reset grants/OTP challenges.
9.  Record a safe audit event and require login again.
10. Never change roles, workspace ownership or account status as a side
    effect of password recovery.

### 4.5 Staff invitation

1.  Authorized owner/admin selects a role from an allowlisted set and
    supplies the invitee's mobile number.
2.  Backend confirms inviter has permission to invite staff and assign
    the requested role.
3.  Generate a cryptographically random, high-entropy, single-use
    invitation token; store only its hash.
4.  Invitation is bound to a specific workspace, intended mobile, role,
    expiry and creator.
5.  Send invitation through the approved channel. Do not expose raw
    invitation tokens in logs.
6.  Invitee verifies identity/OTP and accepts before expiry.
7.  Create or link the user and workspace membership atomically. A staff
    user must not become an owner unless a separately authorized
    ownership-transfer flow exists.
8.  Revoke expired, accepted or manually cancelled invitations.
9.  Test that an invite cannot be used for another workspace, another
    mobile, another role or twice.

------------------------------------------------------------------------

## 5. Proposed page requirements

### Signup page

Required fields: - Full name. - Business name. - Indian mobile number,
normalized to a canonical format (prefer E.164 internally). - Unique
username. - Password. - Confirm password.

Behavior: - Inline validation and accessible error messages. - Submit
disabled while request is in flight, but backend remains idempotent. -
Do not say "mobile already registered" if that creates an
account-enumeration risk; decide exact user-facing messages during UX
review. - OTP page shows masked number, expiry/resend state and
remaining attempts where safe. - Provide retry and support guidance
without revealing account details. - Do not create active
account/workspace before verification.

### Login page

Fields: - Username or mobile number. - Password. - Optional show/hide
password control. - Forgot password link. - Signup link.

Behavior: - Generic invalid-credentials message. - Accessible loading,
offline, server-error and lockout states. - Do not store password or
session token in `localStorage` or `sessionStorage`. - Do not log
credentials. - After successful login, obtain current user and
permissions from backend. - Do not rely on frontend role claims as
security enforcement.

### Password recovery pages

-   Enter mobile.
-   Enter OTP.
-   Set new password and confirm it.
-   Clear success/failure states.
-   Prevent reuse of consumed OTP/reset grant.
-   Avoid account-existence disclosure.
-   Require fresh login after reset.

### Staff invitation pages

-   Owner/admin invitation form with only authorized roles.
-   Pending/accepted/expired/revoked status.
-   Invite acceptance and mobile verification.
-   No self-service privilege escalation.

------------------------------------------------------------------------

## 6. Authentication and session security requirements

### Passwords

-   Keep Argon2 password hashing (verify parameters and library
    configuration).
-   Never store or log plaintext passwords.
-   Use a long passphrase-friendly policy. Recommended minimum is 12
    characters, with a sensible maximum that avoids silent truncation.
    Final policy should be tested against the current password library.
-   Allow password managers and paste.
-   Do not impose arbitrary composition rules that harm usability.
-   Consider known-compromised password screening if a practical
    privacy-preserving option is available.
-   Password changes and resets revoke sessions by default.

### OTPs

Recommended initial policy, to be confirmed in Phase 0: - 6-digit
numeric OTP. - 5-minute expiry. - 30--60 second resend cooldown. -
Maximum 5 failed attempts per challenge. - Single use, purpose-bound
(signup vs password reset vs invitation verification). - Invalidate the
previous code on resend. - Enforce per-phone, per-IP and provider/global
rate limits. - Use cryptographically secure generation. - Store a keyed
hash/HMAC or another carefully designed non-plaintext representation; a
simple unsalted hash of a six-digit OTP is not sufficient against
offline brute force. - Never expose OTPs in production API responses,
logs, traces or analytics. - Development/test OTP bypass must be
explicitly restricted to isolated test/demo environments and must be
impossible to enable accidentally in production.

### Failed login and lockout

Proposed product policy: - 5 consecutive wrong passwords triggers a
15-minute account lockout. - On lockout expiry, start a fresh
failed-attempt cycle; the next wrong password counts as 1/5 rather than
immediately re-locking. - Successful login resets the counter and clears
expired lockout state. - Add IP/device/network-level rate limiting so an
attacker cannot simply rotate accounts or repeatedly lock out a
victim. - Consider progressive throttling and alerts for repeated
abuse. - Do not allow a login error to disclose account existence or
internal lockout state. - Use atomic database updates or
transaction-safe logic to avoid concurrent requests bypassing the
threshold. - Tests must cover both expired-lock + wrong password and
expired-lock + correct password.

### Cookie and CSRF security

Recommended cookie settings: - `HttpOnly`. - `Secure` in production. -
`SameSite=Lax` when deployment allows; use `Strict` only if compatible
with the UX and flows. - Narrowest practical path/domain. - Do not store
auth tokens in browser storage. - Protect all state-changing
cookie-authenticated operations with a CSRF strategy, such as a
synchronizer token or properly implemented double-submit pattern, plus
Origin/Referer validation. - CORS must use explicit trusted origins and
credentials only where required; never combine credentialed CORS with
wildcard origin. - Login/session creation must be protected from
CSRF/login-CSRF. - Use HTTPS in production. - Rotate the session
identifier after login and privilege changes where appropriate. - Apply
idle and absolute expiry; exact durations to be decided. - Revoke
sessions on logout, password reset and account disablement.

### Recommended session model

Prefer database-backed opaque sessions: - High-entropy random session ID
generated using a cryptographic RNG. - Store only a hash of the session
secret in the database. - Bind session to user and lifecycle
timestamps. - Track created, last-seen, expires, revoked and optional
non-sensitive device metadata. - Avoid invasive device fingerprinting. -
Validate session and current user status on each protected request. -
Make session revocation immediate. - Never store raw session secret in
logs. - Decide idle timeout, absolute timeout and concurrent-session
behavior before implementation.

------------------------------------------------------------------------

## 7. Authorization and multi-tenancy

Authentication answers "who is the user?" Authorization answers "what
can this user do, in which workspace, to which records?"

### Core rules

1.  Every business-owned record must be accessed within a validated
    workspace/tenant context.
2.  Never trust `business_id`, `tenant_id`, owner ID, role or permission
    values supplied by the client without backend authorization.
3.  Derive allowed workspace membership from the authenticated user and
    server-side membership records.
4.  Every API handler/service must enforce permissions, not merely the
    React UI.
5.  For object IDs, enforce both object-level permission and workspace
    ownership to prevent IDOR/BOLA.
6.  Return consistent 403/404 behavior according to the chosen
    information-disclosure policy.
7.  Background tasks, exports, reports and analytics queries must carry
    workspace context and enforce tenant boundaries.
8.  Cache keys, file storage paths and generated downloads must be
    tenant-scoped.
9.  Prevent staff from changing their own role or assigning a higher
    role than they are permitted to grant.
10. Test cross-tenant reads, updates, deletes, reports, invoices,
    inventory and exports.

### Initial role model

Preserve and audit the existing roles: - `ADMIN` - `SALES` -
`WAREHOUSE` - `ACCOUNTS` - `VIEWER`

Before implementation, clarify whether `ADMIN` means a platform operator
or a workspace owner. Recommended separation: - **Platform operator**:
internal, tightly restricted support role; never automatically assigned
during public signup. - **Business owner**: workspace owner role or an
explicitly defined owner permission set. - **Business staff**: assigned
one of the approved staff roles. - **Viewer**: read-only access subject
to explicit resource permissions.

Do not silently equate the current `ADMIN` role with the new owner role.
Review the current permission matrix in `AGENTS.md` and map it
explicitly. A user must never gain platform-level privileges by signing
up.

### Tenant data reset implications

A clean database does not by itself make a multi-tenant application
secure. Tenant ownership must be represented and enforced in schema and
queries. During the audit, identify all business tables that need a
workspace relationship, foreign-key strategy, unique constraints scoped
to workspace, and query filters. Do not implement a partial tenant model
that protects some routers but leaves reports, returns, payments or
exports exposed.

------------------------------------------------------------------------

## 8. Proposed API contract

These are target routes for discussion, not an instruction to duplicate
or overwrite existing endpoints. Inspect existing contracts first and
preserve compatibility where appropriate.

  ----------------------------------------------------------------------------
  Endpoint                                 Purpose
  ---------------------------------------- -----------------------------------
  `POST /auth/signup`                      Validate signup details and start
                                           verification

  `POST /auth/signup/verify-otp`           Verify signup challenge and
                                           atomically create
                                           account/workspace/membership

  `POST /auth/signup/resend-otp`           Resend OTP under rate limits

  `POST /auth/login`                       Username/mobile + password; set
                                           session cookie

  `POST /auth/logout`                      CSRF-protected session revocation

  `GET /auth/me`                           Current user, memberships/workspace
                                           context and effective permissions

  `POST /auth/forgot-password`             Start generic mobile recovery flow

  `POST /auth/reset-password/verify-otp`   Verify recovery OTP

  `POST /auth/reset-password`              Set new password using a
                                           short-lived verified reset grant

  `POST /auth/change-password`             Change password for authenticated
                                           user, normally requiring current
                                           password

  `GET /auth/sessions`                     List current user's active
                                           sessions, if included in v1

  `DELETE /auth/sessions/{id}`             Revoke a session belonging to
                                           current user

  `POST /business/invitations`             Authorized owner/admin creates
                                           staff invitation

  `POST /business/invitations/accept`      Accept invitation and create/link
                                           membership
  ----------------------------------------------------------------------------

Use Pydantic request/response schemas, explicit response status codes,
safe errors and transaction boundaries. Never return password hashes,
OTP material, session hashes, internal secret values or unnecessary user
data.

------------------------------------------------------------------------

## 9. Database design and migration approach

Potential logical entities (not final table names/columns): - User
identity and status. - Verified mobile and normalized identifier. -
Workspace/business. - User-to-workspace membership and role. - OTP
challenge with purpose, expiry, attempts and consumption. -
Database-backed session. - Staff invitation. - Security audit event.

Before schema work: 1. Compare `schema.sql`, current migrations and
actual database schemas. 2. Determine whether `schema.sql` is a
baseline, full snapshot or single source used by a project-specific
process. 3. Identify existing auth tables, foreign keys, unique
constraints and role fields. 4. Produce a table-by-table tenant mapping
matrix. 5. Decide identifier normalization and uniqueness rules. 6.
Design additive, versioned migrations compatible with current repository
conventions. 7. Add indexes and constraints that protect correctness
under concurrency. 8. Document upgrade, verification and
rollback/recovery steps. 9. Validate against a disposable test database
before any shared environment. 10. Update `schema.sql` only according to
the project's documented single-source-of-truth workflow.

Never delete production data just because the user has said it can be
cleared. The reset must be a separately reviewed operation with a
verified target branch, explicit confirmation immediately before
execution, and a backup/recovery decision.

------------------------------------------------------------------------

## 10. Demo and production database reset plan

The user has stated that demo-seeded data on the separate Neon demo
branch can be deleted and that production-branch data can also be
cleared. This must be handled carefully.

### Required safeguards

-   Do not perform any deletion during planning or ordinary
    implementation.
-   First identify exact Neon branch names and which connection string
    is used by each environment.
-   Never print complete database URLs or passwords.
-   Verify target identity through safe database metadata queries.
-   Confirm whether production currently contains any data that must be
    preserved, including accounts, billing records, user-created test
    data or audit history.
-   Take a backup/snapshot or record the approved recovery strategy
    before clearing data.
-   Use a reviewed reset script with an explicit environment guard and
    an allowlist of expected database/branch identity.
-   Make the reset fail closed if the branch/environment cannot be
    verified.
-   Never run destructive commands automatically on application startup,
    test setup, seed scripts or migrations.
-   Run the reset on the demo branch first, verify, then separately
    handle production only after a fresh target verification and
    immediate confirmation.
-   Recreate deterministic demo data using the existing demo seeding
    workflow after schema/auth implementation. Preserve the existing
    requirement that rerunning demo seeds produces exactly the same
    values.
-   Keep `backend/.env.demo` separate from production configuration, use
    a unique demo JWT/session secret, and restrict demo seed flags to
    the demo environment.
-   Test that a production process refuses to start or seed when
    `DEMO_SEED_ALLOWED=true` or a demo environment selector is present.
-   Never put `.env`, `.env.demo`, virtual environments, `node_modules`,
    secrets or database dumps into a shareable ZIP.

Clearing data is separate from schema migration. Prefer a reviewed
environment-specific reset script over broad ad-hoc SQL.

------------------------------------------------------------------------

## 11. Frontend implementation requirements

Audit existing React Router and Axios patterns first. Expected target
behavior: - Signup, OTP verification, login, forgot-password,
reset-password and invitation acceptance routes. -
`AuthProvider`/equivalent loads `/auth/me` at startup. - Axios sends
cookies using the appropriate credentials configuration. - CSRF token is
attached to state-changing requests according to the selected
strategy. - Protected route redirects unauthenticated users without
treating client-side state as proof of authorization. - Permission-aware
UI improves usability but backend remains authoritative. - Logout calls
the backend and clears client auth state. - Session expiry returns the
user to login with a safe message. - Avoid tokens in `localStorage`,
`sessionStorage`, URL query parameters or logs. - Handle loading,
offline, expired-session, validation and server-error states. - Keep
accessibility and keyboard navigation in signup/login/OTP forms. - No
hardcoded OTP, credentials or secrets in frontend code.

------------------------------------------------------------------------

## 12. Testing and acceptance criteria

### Signup and OTP

-   Valid owner signup verifies OTP and creates exactly one user, one
    workspace and one owner membership.
-   User/workspace are not active before verification.
-   Duplicate username/mobile rejected safely.
-   OTP expiry, purpose mismatch, wrong OTP, max attempts, resend and
    replay tested.
-   Concurrent requests and retries do not duplicate accounts or
    workspaces.
-   SMS provider outage does not activate an unverified account.
-   Demo OTP bypass is unavailable in production.

### Login and session

-   Username login works for existing accounts.
-   Verified mobile login works.
-   Wrong password and unknown identifier use generic errors.
-   Disabled/unverified/locked account behavior is correct.
-   5 wrong attempts lock for 15 minutes.
-   After lock expiry, a wrong password begins a new attempt cycle at
    1/5.
-   Successful login resets failure state.
-   Login rotates session identifier.
-   Cookie flags and expiry are correct.
-   Missing/invalid CSRF token rejects state-changing requests.
-   Logout revokes session; replay fails.
-   Session expiry and deactivated-user behavior work.

### Password recovery

-   Generic responses prevent account enumeration.
-   OTP is purpose-bound, expires, is single-use and rate-limited.
-   New password is hashed correctly.
-   Old password stops working after reset.
-   All sessions are revoked by default.
-   Existing OTPs/reset grants become invalid.

### Invitations and authorization

-   Only authorized owner/admin can invite staff and assign allowed
    roles.
-   Invitation is single-use, expiring, revocable, workspace-bound and
    mobile-bound.
-   Staff cannot self-upgrade or become platform admin.
-   Every protected backend route enforces authentication, role
    permission and workspace ownership.
-   Cross-tenant ID substitution fails for all business resources,
    reports, exports and analytics.
-   Deactivated users and revoked sessions lose access.
-   UI restrictions are not the only permission enforcement.

### Quality gates

-   Backend test suite passes.
-   Frontend production build passes.
-   Lint/type/static checks pass if configured.
-   Migration tests pass on disposable PostgreSQL.
-   Existing business flows pass regression tests.
-   Security tests for IDOR/BOLA, CSRF, session replay, OTP replay, rate
    limits and account enumeration pass.
-   Manual production checklist is completed before deployment.

------------------------------------------------------------------------

## 13. Implementation phases and required deliverables

### Phase 0: Read-only audit and baseline

**No code or DB changes.** - Read `AGENTS.md`. - Inspect auth backend,
user model, routes, permissions, frontend auth handling, tests, schema
and migrations. - Map environment/branch configuration without exposing
secrets. - Run baseline backend tests and frontend build. - Produce
current-vs-target gap report, endpoint inventory, schema map and risk
list.

**Exit gate:** User reviews the audit and proposed migration/reset
strategy.

### Phase 1: Identity, workspace and schema foundation

-   Finalize role/owner semantics and tenant data model.
-   Add reviewed migrations and update schema source of truth.
-   Implement workspace/membership foundations.
-   Add constraints and transaction tests.
-   Decide legacy account policy.

**Exit gate:** Migrations pass on disposable PostgreSQL; no production
reset performed without explicit confirmation.

### Phase 2: OTP provider and signup

-   Provider abstraction and test fake.
-   Signup validation, OTP challenge, expiry, resend and abuse
    protection.
-   Atomic owner/workspace/membership creation.
-   Frontend signup and OTP verification.
-   Automated tests.

**Exit gate:** All signup, OTP and duplicate-creation tests pass.

### Phase 3: Session system and login/logout

-   Database-backed sessions.
-   Cookie configuration and CSRF strategy.
-   Username/mobile login, `/auth/me`, logout, session revocation.
-   Lockout and IP/phone rate limiting.
-   Frontend AuthProvider, Axios and protected routes.

**Exit gate:** Session, CSRF, lockout, replay and regression tests pass.

### Phase 4: Password recovery and session lifecycle

-   Forgot/reset/change password.
-   OTP verification and reset grants.
-   Revoke sessions on reset/change as approved.
-   Tests and UI.

**Exit gate:** Recovery and session-revocation tests pass.

### Phase 5: Staff invitations and RBAC

-   Invitation lifecycle.
-   Existing role matrix mapped to owner/staff roles.
-   Backend permission enforcement.
-   Frontend permission-aware UI.
-   Tenant isolation audit across every router/service/report/export.

**Exit gate:** Cross-tenant and role-based security test matrix passes.

### Phase 6: Environment reset, demo seeding and deployment hardening

-   Only after the reset target is verified and immediately confirmed.
-   Reset demo and production separately, if still required.
-   Recreate deterministic demo seed data.
-   Validate production environment variables, CORS, HTTPS, cookies,
    logging, backups and monitoring.
-   Complete deployment and rollback runbook.

**Exit gate:** Production-readiness checklist and owner approval.

------------------------------------------------------------------------

## 14. Operational and monitoring requirements

-   Log security events: login success/failure, lockout, OTP
    request/verification outcome, password reset, session revocation,
    invitation creation/acceptance, permission changes.
-   Use structured logs with request/correlation IDs.
-   Never log passwords, raw OTPs, session cookies, raw session IDs,
    reset tokens or full connection strings.
-   Monitor unusual OTP volume, repeated login failures, repeated
    account lockouts and invitation abuse.
-   Set alerts and documented response actions.
-   Use least-privilege database credentials and rotate secrets if
    exposed.
-   Keep production secrets in environment/secret management, never in
    source control.
-   Document backup and restore, database migration recovery and
    incident response.
-   Avoid leaking internal stack traces or secret configuration in API
    responses.

------------------------------------------------------------------------

## 15. Definition of done

Authentication and authorization are not complete just because signup
and login screens work.

The work is done only when: - The approved product flows work
end-to-end. - Existing username login is preserved or an explicit
migration path is tested. - Mobile verification and recovery are
secure. - Sessions and CSRF are implemented and tested. - Staff
invitations and role permissions work. - Every protected backend
operation enforces workspace ownership and permissions. - Tenant
isolation tests pass. - Migrations are reviewed, repeatable and tested
on disposable PostgreSQL. - Demo reset/seeding is environment-guarded
and deterministic. - Backend tests, frontend build and regression tests
pass. - Production secrets/configuration, logging, monitoring, backup
and rollback guidance are documented. - No destructive database
operation is performed without verified target identity and immediate
confirmation.

------------------------------------------------------------------------

## 16. Instructions for the next AI agent

Start the next conversation with this document and the current
repository/ZIP. The agent must:

1.  State that it will read this plan and `AGENTS.md`.
2.  Begin with **Phase 0 only**.
3.  Inspect the actual files rather than assuming this document proves
    current implementation state.
4.  Do not implement signup, login, schema changes or database reset
    during the initial audit.
5.  Do not delete data, connect to a destructive database operation, or
    run migrations without a separate explicit confirmation of the
    verified target.
6.  Return a read-only audit report with:
    -   Current file/endpoint inventory.
    -   Existing schema/migration summary.
    -   Current behavior versus target requirements.
    -   Security findings with severity and evidence.
    -   Compatibility risks.
    -   Proposed migrations and environment-reset plan.
    -   Baseline test results.
    -   Exact next implementation tasks.
7.  Ask for approval at the Phase 0 exit gate before starting Phase 1.

**Handoff instruction:** Treat this document as the approved product
direction, but treat repository code, SQL schema, migrations,
environment settings and tests as the evidence of the current
implementation. Where they disagree, report the conflict and propose a
safe resolution instead of silently guessing.
