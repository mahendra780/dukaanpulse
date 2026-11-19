-- DukaanPulse authentication/workspace foundation.
-- Prerequisites: run after 001_create_users.sql through 003_add_login_lockout.sql.
-- Safety: this migration FAILS if existing user or business data is present.
-- It never deletes, truncates, or rewrites data. Review a separate, explicit
-- legacy-data migration before applying it to a non-empty database.
-- Rollback/recovery: take a schema backup first. New tables can be removed only
-- through a separately reviewed rollback procedure; do not run destructive SQL
-- automatically.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM users LIMIT 1)
       OR EXISTS (SELECT 1 FROM categories LIMIT 1)
       OR EXISTS (SELECT 1 FROM products LIMIT 1)
       OR EXISTS (SELECT 1 FROM customers LIMIT 1)
       OR EXISTS (SELECT 1 FROM suppliers LIMIT 1)
       OR EXISTS (SELECT 1 FROM purchases LIMIT 1)
       OR EXISTS (SELECT 1 FROM orders LIMIT 1)
       OR EXISTS (SELECT 1 FROM invoices LIMIT 1) THEN
        RAISE EXCEPTION
            '004_auth_workspace_foundation requires an empty legacy database; no data was changed.';
    END IF;
END $$;

ALTER TABLE users
    ADD COLUMN mobile_e164 VARCHAR(16) NULL,
    ADD COLUMN mobile_verified_at TIMESTAMPTZ NULL;

ALTER TABLE users
    ADD CONSTRAINT uq_users_mobile_e164 UNIQUE (mobile_e164);

CREATE TABLE workspaces (
    workspace_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_workspaces_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE workspace_memberships (
    membership_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workspace_id BIGINT NOT NULL REFERENCES workspaces(workspace_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_workspace_membership UNIQUE (workspace_id, user_id),
    CONSTRAINT chk_workspace_membership_role
        CHECK (role IN ('OWNER', 'ADMIN', 'SALES', 'WAREHOUSE', 'ACCOUNTS', 'VIEWER')),
    CONSTRAINT chk_workspace_membership_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
);
CREATE INDEX idx_workspace_memberships_user ON workspace_memberships(user_id);

CREATE TABLE workspace_invitations (
    invitation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workspace_id BIGINT NOT NULL REFERENCES workspaces(workspace_id),
    created_by_user_id BIGINT NOT NULL REFERENCES users(user_id),
    mobile_e164 VARCHAR(16) NOT NULL,
    role VARCHAR(20) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_workspace_invitation_role
        CHECK (role IN ('ADMIN', 'SALES', 'WAREHOUSE', 'ACCOUNTS', 'VIEWER'))
);
CREATE INDEX idx_workspace_invitations_workspace_mobile
    ON workspace_invitations(workspace_id, mobile_e164);

CREATE TABLE otp_challenges (
    challenge_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id UUID NOT NULL UNIQUE,
    purpose VARCHAR(30) NOT NULL,
    mobile_e164 VARCHAR(16) NOT NULL,
    otp_hash VARCHAR(64) NOT NULL,
    user_id BIGINT NULL REFERENCES users(user_id),
    invitation_id BIGINT NULL REFERENCES workspace_invitations(invitation_id),
    pending_username VARCHAR(50) NULL,
    pending_full_name VARCHAR(100) NULL,
    pending_business_name VARCHAR(150) NULL,
    pending_password_hash TEXT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NULL,
    CONSTRAINT chk_otp_purpose CHECK (purpose IN ('SIGNUP', 'PASSWORD_RESET', 'INVITATION')),
    CONSTRAINT chk_otp_attempts CHECK (attempts >= 0 AND attempts <= 5)
);
CREATE INDEX idx_otp_challenges_mobile_purpose ON otp_challenges(mobile_e164, purpose);

CREATE TABLE password_reset_grants (
    grant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_password_reset_grants_user ON password_reset_grants(user_id);

CREATE TABLE auth_sessions (
    session_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    workspace_id BIGINT NOT NULL REFERENCES workspaces(workspace_id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    csrf_token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    CONSTRAINT fk_auth_sessions_workspace_membership
    FOREIGN KEY (workspace_id, user_id)
    REFERENCES workspace_memberships(workspace_id, user_id)
);
CREATE INDEX idx_auth_sessions_user_active ON auth_sessions(user_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE security_audit_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(user_id),
    workspace_id BIGINT NULL REFERENCES workspaces(workspace_id),
    event_type VARCHAR(60) NOT NULL,
    detail VARCHAR(200) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_security_audit_events_user_time ON security_audit_events(user_id, created_at);
CREATE INDEX idx_security_audit_events_workspace_time ON security_audit_events(workspace_id, created_at);

CREATE TABLE auth_rate_limit_events (
    rate_limit_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scope VARCHAR(40) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_auth_rate_limit_lookup
    ON auth_rate_limit_events(scope, key_hash, event_type, created_at);
