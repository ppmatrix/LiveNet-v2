-- Proposed segregated AUTHORITY database only. NEVER a LiveNet migration.
-- Not installed, not approved deployment, no credentials/roles/grants/bootstrap.
-- Dedicated owner/admin and service ACL, authenticated caller/channel, independent
-- continuity interlock, restore policy and storage durability need real validation.
-- Do not populate control/approvals by observing a target or accepting a fixture.
CREATE SCHEMA dev09b_authority;
REVOKE ALL ON SCHEMA dev09b_authority FROM PUBLIC;
CREATE TABLE dev09b_authority.control (
    singleton boolean PRIMARY KEY CHECK (singleton),
    authority_epoch bigint NOT NULL CHECK (authority_epoch > 0),
    revocation_epoch bigint NOT NULL CHECK (revocation_epoch > 0),
    continuity_token uuid NOT NULL,
    blocked boolean NOT NULL DEFAULT true,
    last_time bigint NOT NULL CHECK (last_time >= 0)
);
CREATE TABLE dev09b_authority.approvals (
    approval_id uuid PRIMARY KEY,
    attempt_id uuid NOT NULL UNIQUE,
    state text NOT NULL CHECK (state IN ('AVAILABLE','CONSUMED','REVOKED','EXPIRED')),
    revoked boolean NOT NULL DEFAULT false,
    envelope bytea NOT NULL,
    payload bytea NOT NULL,
    target bytea NOT NULL,
    executor bytea NOT NULL,
    plan bytea NOT NULL,
    semantic bytea NOT NULL,
    physical bytea NOT NULL,
    provenance bytea NOT NULL,
    session_json text,
    CHECK ((state = 'CONSUMED') = (session_json IS NOT NULL))
);
CREATE TABLE dev09b_authority.nonces (nonce uuid PRIMARY KEY);
CREATE TABLE dev09b_authority.events (
    sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attempt_id uuid NOT NULL REFERENCES dev09b_authority.approvals(attempt_id),
    event text NOT NULL CHECK (event IN ('commit_intent','rollback_attempt','close','independent_reconciliation')),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$')
);
-- No deletion/reset/release in service API. APPROVAL rows/documents are immutable
-- to executor; only the segregated service may consume/revoke, never issue them.
-- Schema ACL and DB roles require a separately authorized deployment script.
