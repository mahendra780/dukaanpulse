# DukaanPulse deployment checklist

This checklist is based on the repository configuration and code. It does not
replace an organisation's change-control, secret-management, or database
recovery procedures. Do not put passwords, connection strings, JWT keys, or
real user data in this file, source control, logs, or tickets.

## 1. HTTPS and production mode

Publish both the frontend and API through HTTPS only. The current FastAPI code
does not redirect HTTP to HTTPS or add an HTTPS-only transport policy; enforce
that at the deployment platform, load balancer, or reverse proxy.

Set this backend setting in the deployment environment:

```env
ENVIRONMENT=production
```

In production, the application sets `/docs`, `/redoc`, and `/openapi.json` to
`None`, disabling those routes. It does not change the login or business-route
authorization rules. `GET /` and `GET /health` remain public; `GET /health/db`
requires an authenticated user with `system:read` (ADMIN under the current role
matrix).

## 2. Backend secrets and credentials

### JWT signing key

`JWT_SECRET_KEY` is required and must be at least 32 characters. Generate a
new value locally in a trusted shell, then store it only in the deployment
secret manager:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Do not reuse a development key in a deployed environment. To rotate it:

1. Generate a new key and update `JWT_SECRET_KEY` for every backend instance.
2. Restart or redeploy those instances as one coordinated change.
3. Ask users to sign in again and verify an ADMIN can use `/health/db`.

JWTs are signed with this key. Rotating it makes every previously issued access
token fail signature validation on its next request. The backend returns 401;
the frontend clears its stored session and sends the user to Login. Rotation
does not update user rows, passwords, roles, or permissions.

### Database password

`DATABASE_URL` supplies the PostgreSQL connection used by the backend. Rotate
the database credential through the database provider's approved procedure,
then replace the deployment secret value for `DATABASE_URL` and restart or
redeploy all backend instances. Verify with an authenticated ADMIN request to
`GET /health/db`; do not expose the URL in command history, output, or issue
trackers.

The repository does not automate database-password rotation or database-secret
distribution.

## 3. Frontend/API origin configuration

Set the backend's comma-separated `CORS_ALLOWED_ORIGINS` to the exact HTTPS
origins that host the frontend. The backend trims whitespace and rejects an
empty list. For example:

```env
CORS_ALLOWED_ORIGINS=https://app.example.invalid,https://admin.example.invalid
```

Use origins only (scheme, host, and optional port), not paths. Do not use the
development defaults (`http://localhost:5173` and `http://127.0.0.1:5173`) for
a public deployment.

Build the frontend with `VITE_API_BASE_URL` set to the public HTTPS API base
URL, for example:

```env
VITE_API_BASE_URL=https://api.example.invalid
```

The frontend reads this value at build time and otherwise falls back to
`http://127.0.0.1:8000`. The frontend origin must appear in
`CORS_ALLOWED_ORIGINS`, and the API URL must use HTTPS in deployment.

## 4. Database migrations and a safe Neon workflow

The application does not run migrations automatically. SQL files are applied
manually by an authorised operator. Their intended order is:

| Order | File | Purpose |
| ---: | --- | --- |
| 000 | `backend/sql/000_baseline_schema.sql` | Reference pg_dump of the existing baseline schema. It is **not** an additive migration to rerun against an existing database. |
| 001 | `backend/sql/001_create_users.sql` | Additive `users` table, constraints, and case-insensitive username index. |
| 002 | `backend/sql/002_add_user_token_version.sql` | Additive `users.token_version` for password-change session invalidation. |
| 003 | `backend/sql/003_add_login_lockout.sql` | Additive `failed_login_count` and `locked_until` fields. |

Safe procedure:

1. Record the target environment, current migration state, and rollback/recovery
   owner. Back up first.
2. Create a Neon branch from the intended target database and apply only the
   missing additive migrations there, in numeric order. Do not run a migration
   twice.
3. Verify the branch: start the application with branch-specific secrets, sign
   in as an ADMIN, check the business pages, and test the intended schema
   change.
4. Have an authorised reviewer approve the result. Promote the branch or repeat
   the same reviewed, ordered migration procedure on the target according to
   the team's Neon release process.

For a database that already corresponds to the baseline dump, do not execute
`000_baseline_schema.sql`; apply only the missing numbered additive migrations.
Do not run this checklist's SQL against production as an unreviewed experiment.

## 5. First and backup administrator accounts

After the `users` table migration is applied and the backend environment is
configured, create the first administrator from the backend directory:

```powershell
python -m app.scripts.create_admin
```

The script interactively requests a username, full name, and matching password
confirmation; passwords must be at least 10 characters. It creates an active
`ADMIN` user and stores only the Argon2 password hash.

Immediately sign in and create a second, independently controlled active ADMIN
account in the Users page. Keep both accounts available and protected by the
organisation's normal access controls. The app prevents an administrator from
demoting/deactivating themselves and prevents removal of the last active ADMIN,
but it does not replace an account-recovery process.

## 6. Login lockout operations

Current defaults are five consecutive failed passwords for an active user and a
15-minute lock. Both are configurable through
`FAILED_LOGIN_ATTEMPT_THRESHOLD` and `LOGIN_LOCKOUT_MINUTES`. Login failures
remain deliberately generic, including for locked and inactive accounts.

For an authorised support case, first identify the correct account in a Neon
branch or approved target. Use a verified numeric user ID for the reset rather
than a loosely copied username:

```sql
SELECT user_id, username, failed_login_count, locked_until
FROM users
WHERE lower(username) = lower('<approved username>');

UPDATE users
SET failed_login_count = 0,
    locked_until = NULL
WHERE user_id = <verified-user-id>;
```

Do not run the `UPDATE` until the `SELECT` result has been reviewed. This clears
only the application's lockout state; it does not change a password, role,
status, or `token_version`. Record the authorised support action according to
the organisation's operating procedure.

## 7. Backups and recovery

The repository does not configure backups, retention, point-in-time recovery,
or restore testing. Before schema or credential changes, use the database
provider's approved backup/branch/recovery capability, verify who can restore,
and periodically prove that a restore can be used by the application in a
non-production environment. Keep a record of applied migrations with the
backup/release record.

## 8. Not implemented in the current code

- Per-IP rate limiting or distributed login throttling.
- Multi-factor authentication (MFA).
- Password-recovery/reset-by-email or self-service recovery.
- Audit-log storage or audit-log viewing.
- Forced password change for users created or reset by an administrator.

The existing account lockout is per active user account, not per IP address.
