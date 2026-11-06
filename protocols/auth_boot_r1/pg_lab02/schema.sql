-- R1-PG-LAB-02. Only the NEW private disposable cluster from run_lab.py.
-- Requires LAB-01 schema for reproductions; this disables its old callable gate.
-- Candidate session guard + persistent burn, NOT a durable advisory lock.
CREATE SCHEMA lab02;
REVOKE ALL ON SCHEMA lab02 FROM PUBLIC;
GRANT USAGE ON SCHEMA lab02 TO lab_caller, lab_writer, lab_gate;
REVOKE EXECUTE ON FUNCTION lab.fixed_update(text,integer,integer) FROM lab_caller;
CREATE TABLE lab02.guard_key (
    approval text PRIMARY KEY REFERENCES lab.burn(approval),
    lock_key integer UNIQUE NOT NULL CHECK (lock_key > 0)
);
GRANT INSERT, SELECT ON lab02.guard_key TO lab_writer;
GRANT SELECT ON lab02.guard_key TO lab_gate;
-- Explicit table-level privilege required by LOCK TABLE; column UPDATE rights
-- from LAB-01 are insufficient. The caller still receives EXECUTE only.
GRANT UPDATE ON lab.cell TO lab_gate;

-- Restrict ALL overloads, not only unlock_all. These ACL changes affect ONLY
-- this lab's freshly initialized cluster. No existing server is contacted.
DO $acl$
DECLARE f record;
BEGIN
    FOR f IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
        JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='pg_catalog'
          AND (p.proname LIKE 'pg_advisory_%' OR p.proname LIKE 'pg_try_advisory_%')
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', f.signature);
    END LOOP;
END;
$acl$;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_try_advisory_lock(integer,integer) TO lab_gate;
-- Only needed by the ADMIN-ONLY fault-injection variant installed by the harness.
GRANT EXECUTE ON FUNCTION pg_catalog.pg_advisory_lock(integer,integer) TO lab_gate;

CREATE FUNCTION lab02.fixed_update(p_approval text, p_expected integer, p_value integer)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab,lab02,pg_temp AS $gate$
DECLARE
    b lab.burn%ROWTYPE;
    p lab.policy%ROWTYPE;
    k integer;
    n integer;
BEGIN
    SELECT * INTO STRICT b FROM lab.burn WHERE approval=p_approval;
    IF b.caller <> session_user OR b.backend_pid <> pg_backend_pid()
       OR b.transaction_id <> txid_current()::text THEN
        RAISE EXCEPTION 'binding refused';
    END IF;
    SELECT lock_key INTO STRICT k FROM lab02.guard_key WHERE approval=p_approval;
    -- Advisory locks are reentrant! Try-lock alone is NOT an entry guard.
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_locks WHERE locktype='advisory'
               AND pid=pg_backend_pid() AND classid=92001 AND objid=k::oid
               AND objsubid=2 AND granted) THEN
        RAISE EXCEPTION 'attempt already entered in this session';
    END IF;
    IF NOT pg_try_advisory_lock(92001,k) THEN
        RAISE EXCEPTION 'attempt held elsewhere';
    END IF;
    -- Session guard survives SAVEPOINT / transaction rollback. Never unlock
    -- here, even on failure. New backend/xid must fail the persistent binding.

    -- No waiting on the known business/policy relation and tuple locks after
    -- the final time check. Deliberately coarse locking: one lab row only.
    LOCK TABLE ONLY lab.cell IN EXCLUSIVE MODE NOWAIT;
    PERFORM id FROM ONLY lab.cell WHERE id=1 FOR UPDATE NOWAIT;
    SELECT * INTO STRICT p FROM lab.policy WHERE id=1 FOR SHARE NOWAIT;
    IF p.revoked OR p.epoch <> b.epoch
       OR clock_timestamp() < b.not_before OR clock_timestamp() >= b.expires_at THEN
        RAISE EXCEPTION 'eligibility refused';
    END IF;
    RAISE LOG 'R1_LAB02_AFTER_CHECK %', p_approval;
    -- LAB02_ADMIN_FAULT_AFTER_CHECK
    UPDATE ONLY lab.cell SET value=p_value,row_version=row_version+1
      WHERE id=1 AND row_version=p_expected;
    GET DIAGNOSTICS n=ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'row/version refused'; END IF;
    RETURN n;
END;
$gate$;
ALTER FUNCTION lab02.fixed_update(text,integer,integer) OWNER TO lab_gate;
REVOKE ALL ON FUNCTION lab02.fixed_update(text,integer,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lab02.fixed_update(text,integer,integer) TO lab_caller;
