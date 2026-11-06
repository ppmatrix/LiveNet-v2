-- R1-PG-LAB-01: ONLY a fresh, private disposable cluster created by run_lab.py.
-- Experimental local boundary, NOT an AUTH-03 migration or production gate.
CREATE ROLE lab_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE lab_caller LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE lab_gate NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA lab;
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
GRANT USAGE ON SCHEMA lab TO lab_writer, lab_caller, lab_gate;

CREATE TABLE lab.cell (
    id integer PRIMARY KEY CHECK (id = 1),
    value integer NOT NULL,
    row_version integer NOT NULL CHECK (row_version >= 0)
);
INSERT INTO lab.cell VALUES (1, 0, 0);
CREATE TABLE lab.policy (
    id integer PRIMARY KEY CHECK (id = 1),
    epoch bigint NOT NULL,
    revoked boolean NOT NULL,
    latch boolean NOT NULL
);
INSERT INTO lab.policy VALUES (1, 1, false, false);
CREATE TABLE lab.burn (
    approval text PRIMARY KEY,
    attempt text UNIQUE NOT NULL,
    caller name NOT NULL,
    backend_pid integer NOT NULL,
    transaction_id text NOT NULL,
    plan text NOT NULL CHECK (plan = 'fixed-update-v1'),
    generation text NOT NULL CHECK (generation = 'lab-generation-1'),
    epoch bigint NOT NULL,
    not_before timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > not_before)
);
-- This transaction-local start record is deliberately tested against SAVEPOINT
-- rollback. It does NOT claim rollback-independent initiation exclusivity.
CREATE TABLE lab.local_start (approval text PRIMARY KEY);
GRANT INSERT, SELECT ON lab.burn TO lab_writer;
GRANT SELECT ON lab.burn, lab.cell, lab.policy TO lab_gate;
GRANT UPDATE(value, row_version) ON lab.cell TO lab_gate;
-- Row-lock privileges only; gate cannot UPDATE epoch/revoked.
GRANT UPDATE(latch) ON lab.policy TO lab_gate;
GRANT INSERT ON lab.local_start TO lab_gate;

CREATE FUNCTION lab.fixed_update(p_approval text, p_expected integer, p_value integer)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, lab AS $gate$
DECLARE
    b lab.burn%ROWTYPE;
    p lab.policy%ROWTYPE;
    n integer;
BEGIN
    SELECT * INTO STRICT b FROM lab.burn WHERE approval = p_approval;
    IF b.caller <> session_user OR b.backend_pid <> pg_backend_pid()
       OR b.transaction_id <> txid_current()::text THEN
        RAISE EXCEPTION 'binding refused';
    END IF;
    SELECT * INTO STRICT p FROM lab.policy WHERE id = 1 FOR SHARE;
    IF p.revoked OR p.epoch <> b.epoch
       OR clock_timestamp() < b.not_before OR clock_timestamp() >= b.expires_at THEN
        RAISE EXCEPTION 'eligibility refused';
    END IF;
    -- Test observer only: survives transaction rollback in the private server
    -- log, but is NOT independent evidence of the tuple's first effect.
    RAISE LOG 'R1_LAB_CHECK %', p_approval;
    INSERT INTO lab.local_start VALUES (p_approval);
    UPDATE ONLY lab.cell SET value = p_value, row_version = row_version + 1
      WHERE id = 1 AND row_version = p_expected;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'row/version refused'; END IF;
    RETURN n;
END;
$gate$;
ALTER FUNCTION lab.fixed_update(text, integer, integer) OWNER TO lab_gate;
REVOKE ALL ON FUNCTION lab.fixed_update(text, integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lab.fixed_update(text, integer, integer) TO lab_caller;
