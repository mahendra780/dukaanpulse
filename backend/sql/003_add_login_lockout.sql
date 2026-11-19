-- Adds per-user failed-login state for generic, database-enforced account lockout.
-- This is additive: existing users start unlocked with zero failed attempts.

ALTER TABLE users
    ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN locked_until TIMESTAMPTZ NULL;
