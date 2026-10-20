-- Adds a per-user token version so password changes can revoke existing sessions.
-- This is additive: existing users receive version 0 and retain no changed data.

ALTER TABLE users
    ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;
