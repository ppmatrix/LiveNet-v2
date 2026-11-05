-- R1-PROTO-03: DESIGN ONLY, NOT APPROVED, NEVER APPLIED.
-- Not an Alembic migration, not a runner, not an authorization mechanism.
-- PostgreSQL 16 candidate syntax has NOT been parsed/validated by a server.
-- Deliberately abort before DDL. Even clients continuing after an error keep
-- this transaction aborted until the final ROLLBACK. Do not remove the guard.
BEGIN;
DO $r1_disabled$
BEGIN
    RAISE EXCEPTION 'R1-PROTO-03 experimental SQL: application forbidden';
END;
$r1_disabled$;

-- A new schema would violate current exact catalog checks. Integration would
-- require separate review; never insert these objects into existing migrations.
CREATE SCHEMA r1_boundary_candidate;

-- Ordinary logged table: not TEMP, not UNLOGGED. No sequences/identity values.
-- Strings and limits are candidate representations, not recovered F03/F04.
CREATE TABLE r1_boundary_candidate.burned_attempt (
    authority_id text NOT NULL CHECK (length(authority_id) BETWEEN 1 AND 128),
    approval_id text NOT NULL CHECK (length(approval_id) BETWEEN 1 AND 128),
    attempt_id text NOT NULL CHECK (length(attempt_id) BETWEEN 1 AND 128),
    executor_id text NOT NULL,
    executor_incarnation text NOT NULL,
    session_binding text NOT NULL,
    transaction_binding text NOT NULL,
    target_identity_sha256 text NOT NULL
        CHECK (target_identity_sha256 ~ '^[0-9a-f]{64}$'),
    target_generation text NOT NULL,
    execution_plan_sha256 text NOT NULL
        CHECK (execution_plan_sha256 ~ '^[0-9a-f]{64}$'),
    global_digest_sha256 text NOT NULL
        CHECK (global_digest_sha256 ~ '^[0-9a-f]{64}$'),
    authority_epoch numeric(20,0) NOT NULL CHECK (authority_epoch >= 0),
    revocation_epoch numeric(20,0) NOT NULL CHECK (revocation_epoch >= 0),
    not_before timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > not_before),
    marker_state text NOT NULL CHECK (marker_state = 'BURNED'),
    -- Neither generation nor session is part of the uniqueness scope:
    -- changing them must NOT make the approval or attempt reusable.
    PRIMARY KEY (authority_id, approval_id),
    UNIQUE (authority_id, attempt_id)
);

-- Candidate write shape, intentionally comments rather than runnable DML:
-- INSERT INTO r1_boundary_candidate.burned_attempt (...) VALUES (...);
-- No ON CONFLICT DO UPDATE, DELETE, reset, lease expiry or replay-as-success.
-- Confirm the marker in a DISTINCT control transaction before protected work.
-- That extra transaction is NOT authorized by the current single-transaction
-- executor contract. Commit uncertainty => BLOCKED, never retry/resume.
-- A row is only a burn record, never an executable ticket or proof of start.

-- Ownership/ACL are NOT implemented here. No roles, GRANT or SECURITY DEFINER.
-- Future writer must have only reviewed insert rights, no protected DDL powers;
-- a separate protected boundary would have to prevent direct SQL bypass.
-- The current exact source/catalog/security contracts remain untouched.
ROLLBACK;
