"""Complete evidence comparison precedes construction of contract booleans."""
from dataclasses import fields
from ipaddress import ip_interface

from app.readiness import (AdministrativePrivileges, DDLPrivileges, OwnershipPrivileges,
    PrivilegeEvidence, ReadinessObservation, RequiredPrivileges)
from .policy import (BUSINESS_TABLES, COLUMNS, COLUMN_PRIVS, MATRIX, TABLE_PRIVS, REQUIRED_STRUCTURE, REQUIRED_FOREIGN_KEYS, VERIFIER_COLUMNS,
                     Unavailable, canonical, normalize)
from .queries import OWNER_CLASSES


def require(condition):
    if not condition:
        raise Unavailable()


def flags(values):
    require(all(type(v) is bool for v in values))


def system(schema):
    return schema in {"pg_catalog", "information_schema", "pg_toast"}


def permitted(policy, subject, table, col, privilege):
    if subject == policy.target[3]:
        return (table, col, privilege) in MATRIX
    return table in {"public.alembic_version", "public.alembic_security_version"} and privilege == "SELECT"


def validate_contract(policy, data):
    """Also validate the approved manifest: it cannot approve broad app writes.

    System catalog access, PUBLIC origins, routine hashes, structural definitions
    and default ACLs require an independently reviewed, build-specific manifest.
    They are never inferred from the observed server.
    """
    subjects = {policy.target[3], policy.verifier_role}
    roles = data["Q2"]
    require(len(roles) == 2 and {r[0] for r in roles} == subjects)
    role_oids = set()
    for row in roles:
        require(len(row) == 8)
        flags(row[1:7])
        require(row[1] is True and not any(row[2:7]))
        oid(row[7]); require(row[7] not in role_oids)
        role_oids.add(row[7])
    paths = set()
    for row in data["Q3"]:
        if row[0] == "path":
            require(len(row) == 6 and row[1] in subjects and row[2] != row[1])
            require(type(row[2]) is str and bool(row[2]))
            flags(row[3:]); require(not any(row[3:]))
            require((row[1], row[2]) not in paths)
            paths.add((row[1], row[2]))
        else:
            require(row[0] == "edge" and len(row) == 7)
            require(all(type(v) is str and v.isdecimal() for v in row[1:4]))
            flags(row[4:])
            require(not role_oids.intersection(row[1:3]))
    require(all((s, t) in paths for s in subjects for t in subjects if s != t))

    schemas = set()
    for row in data["Q4"]:
        require(len(row) == 8 and row[0] in subjects)
        require(type(row[1]) is str and bool(row[1]))
        flags(row[2:6]); require(row[3:6] == (False, False, False))
        subject, schema, usage = row[:3]
        require((subject, schema) not in schemas); schemas.add((subject, schema))
        if not system(schema):
            allowed = {"security", "inventory", "audit"} if subject == policy.target[3] else {"public"}
            # public USAGE may be an approved PG default, but CREATE is never OK.
            require(usage is (schema in allowed or schema == "public"))
        if schema == "pg_catalog":
            require(usage is True)
    require(all((s, n) in schemas for s in subjects for n in ("public", "inventory", "audit", "security", "pg_catalog", "information_schema", "pg_toast")))
    require({n for s, n in schemas if s == policy.target[3]} == {n for s, n in schemas if s == policy.verifier_role})
    require({n for _, n in schemas} == {"public", "inventory", "audit", "security", "pg_catalog", "information_schema", "pg_toast"})

    relations = {}; columns = {}
    for row in data["Q13"]:
        if row[0] == "relation":
            require(len(row) == 7 and all(type(v) is str and v for v in row[1:]))
            require(row[3] in ("r", "i", "S", "t", "v", "m", "c", "f", "p", "I"))
            require(row[5] in ("p", "u", "t"))
            if row[3] in ("r", "i", "S", "t", "m"):
                require(row[5] == "p")
            if not system(row[1]):
                require(row[3] in ("r", "i") and row[5] == "p")
            key = (row[1], row[2]); require(key not in relations); relations[key] = row[3]
        else:
            require(row[0] == "column" and len(row) == 10)
            schema, table, col, number, typ, notnull, identity, generated, default = row[1:]
            require(all(type(v) is str and v for v in (schema, table, col, typ)))
            require(type(number) is int and number > 0 and type(notnull) is bool)
            require(identity in ("", "a", "d") and generated in ("", "s"))
            require(default is None or type(default) is str)
            key = (schema, table, col); require(key not in columns); columns[key] = number
    require(all((s, t) in relations for s, t, c in columns))
    require(all((s, n) in schemas for s in subjects for n, t in relations))
    actual_business = {s + "." + t for (s, t), kind in relations.items()
                       if not system(s) and kind in ("r", "p", "v", "m", "f", "S")}
    require(actual_business == BUSINESS_TABLES)
    require(all(relations[tuple(t.split("."))] == "r" for t in BUSINESS_TABLES))
    for table, structure in REQUIRED_STRUCTURE.items():
        cols = structure[0]
        require({c for s, t, c in columns if s + "." + t == table} == set(cols))
    for ledger in ("alembic_version", "alembic_security_version"):
        require({c for s, t, c in columns if (s, t) == ("public", ledger)} == {"version_num"})
    table_keys = set(); column_keys = set(); sequence_keys = set()
    for row in data["Q5"]:
        require(len(row) == 6 and row[0] in subjects and row[3] in TABLE_PRIVS)
        subject, schema, table, priv, allowed, grant = row
        flags((allowed, grant)); require(grant is False)
        key = (subject, schema, table, priv); require(key not in table_keys); table_keys.add(key)
        require(relations.get((schema, table)) in ("r", "p", "v", "m", "f"))
        if not system(schema):
            cols = [c for s, t, c in columns if (s, t) == (schema, table)]
            # SELECT/INSERT may be table grants or all-column grants. No broad UPDATE.
            can = bool(cols) and priv in ("SELECT", "INSERT") and all(
                permitted(policy, subject, schema + "." + table, c, priv) for c in cols)
            require(not allowed or can)
    for row in data["Q6"]:
        require(len(row) == 7 and row[0] in subjects and row[4] in COLUMN_PRIVS)
        subject, schema, table, col, priv, allowed, grant = row
        flags((allowed, grant)); require(grant is False)
        key = (subject, schema, table, col, priv)
        require(key not in column_keys); column_keys.add(key)
        require((schema, table, col) in columns)
        require(relations[(schema, table)] in ("r", "p", "v", "m", "f"))
        if not system(schema):
            require(allowed is permitted(policy, subject, schema + "." + table, col, priv))
    for row in data["Q7"]:
        require(len(row) == 6 and row[0] in subjects and row[3] in ("SELECT", "USAGE", "UPDATE"))
        flags(row[4:]); require(row[5] is False)
        require(relations.get((row[1], row[2])) == "S")
        require(system(row[1]) or row[4] is False)
        key = row[:4]; require(key not in sequence_keys); sequence_keys.add(key)
    require(table_keys == {(s, n, t, p) for s in subjects for (n, t), kind in relations.items()
            if kind in ("r", "p", "v", "m", "f") for p in TABLE_PRIVS})
    require(column_keys == {(s, n, t, c, p) for s in subjects for n, t, c in columns
            if relations[(n, t)] in ("r", "p", "v", "m", "f") for p in COLUMN_PRIVS})
    observed_select = {(r[1], r[2], r[3]) for r in data["Q6"]
                       if r[0] == policy.verifier_role and r[4] == "SELECT" and r[5] is True}
    require(all(("pg_catalog", table, col) in observed_select
                for table, cols in VERIFIER_COLUMNS.items() for col in cols.split()))
    require(sequence_keys == {(s, n, t, p) for s in subjects for (n, t), kind in relations.items()
            if kind == "S" for p in ("SELECT", "USAGE", "UPDATE")})
    owners = ownership(data, subjects, roles)
    db_keys = set()
    for row in data["Q9"]:
        if row[0] == "object_acl":
            require(len(row) == 7 and all(type(v) is str and v for v in row[:6])
                    and type(row[6]) is bool)
            require(row[1] in ("type", "language", "fdw", "server", "tablespace", "largeobject"))
            if row[4] in role_oids | {"0"}:
                require(row[1] in ("type", "language") and row[5] == "USAGE" and row[6] is False)
            continue
        require(len(row) == 6 and row[1] in subjects)
        require(all(type(v) is str and v for v in row[:4]))
        flags(row[4:]); require(row[5] is False)
        if row[0] == "database":
            require(row[2] == policy.target[2] and row[3] in ("CONNECT", "CREATE", "TEMPORARY"))
            require(row[4] is (row[3] == "CONNECT")); db_keys.add((row[1], row[3]))
        else:
            require(row[0] == "parameter" and row[3] in ("SET", "ALTER SYSTEM") and row[4] is False)
    require(db_keys == {(s, p) for s in subjects for p in ("CONNECT", "CREATE", "TEMPORARY")})
    require(bool(data["Q11"]))
    for row in data["Q11"]:
        require(len(row) == 13 and row[0] in subjects)
        require(all(type(row[i]) is str and row[i] for i in (1, 2, 3, 5, 6, 8)))
        require(type(row[4]) is str and row[2].isdecimal() and row[6].isdecimal())
        flags((row[7], row[10], row[11])); require(row[11] is False)
        require(row[9] is None or type(row[9]) is tuple)
        require(row[9] is None or all(type(v) is str and v for v in row[9]))
        require(row[5] in ("f", "p", "a", "w"))
        if row[5] in ("f", "p"):
            require(type(row[12]) is str and len(row[12]) == 64
                    and all(c in "0123456789abcdef" for c in row[12]))
        else:
            require(row[12] is None)
        # f066's audited trigger routine is SECURITY INVOKER and normally has
        # PUBLIC EXECUTE. Pin its signature/config/body in the approved manifest.
        baseline_trigger = (row[1] == "audit" and row[3:6] == ("prevent_event_mutation", "", "f")
                            and row[7] is False and row[8] == "plpgsql" and row[9] is None)
        require(system(row[1]) or row[10] is False or baseline_trigger)
    routines = {(row[0], row[2]) for row in data["Q11"]}
    require(len(routines) == len(data["Q11"]))
    require({oid for s, oid in routines if s == policy.target[3]} ==
            {oid for s, oid in routines if s == policy.verifier_role})
    physical_coverage(data, subjects, owners)
    acl_coverage(policy, data, owners)
    default_coverage(data, owners, role_oids)
    physical = data["Q16"]
    require(len(physical) == 1 and len(physical[0]) == 3)
    require(physical[0][0] == policy.system_identifier)
    require(all(type(v) is int and v > 0 for v in physical[0][1:]))


def identity(policy, rows, subject):
    require(len(rows) == 1 and len(rows[0]) == 9)
    db, user, session_user, address, port, version, readonly, isolation, path = rows[0]
    require(db == policy.target[2] and user == session_user == subject)
    require(type(port) is int and port == policy.target[1] and version == policy.server_version)
    require(type(address) is str and "%" not in address)
    ip = ip_interface(address).ip
    require(ip == ip_interface(policy.server_address).ip)
    require((readonly, isolation, path) == ("on", "repeatable read", "pg_catalog"))


def oid(value):
    require(type(value) is str and value.isascii() and value.isdecimal()
            and 0 < int(value) <= 4294967295 and str(int(value)) == value)


def ownership(data, subjects, roles):
    coverage = {}; cells = {}; role_ids = {r[0]: r[7] for r in roles}
    for row in data["Q8"]:
        if row[0] == "coverage":
            require(len(row) == 3 and row[1] in OWNER_CLASSES and row[1] not in coverage)
            require(type(row[2]) is int and row[2] >= 0)
            coverage[row[1]] = row[2]
            continue
        require(len(row) == 5 and row[0] in subjects and row[1] in OWNER_CLASSES)
        oid(row[2]); oid(row[4]); require(type(row[3]) is bool)
        require(row[3] is (row[4] == role_ids[row[0]]) and row[3] is False)
        key = row[:3]; require(key not in cells); cells[key] = row[4]
    require(set(coverage) == set(OWNER_CLASSES))
    owners = {}
    for kind in OWNER_CLASSES:
        partitions = [{obj: owner for (s, k, obj), owner in cells.items() if s == subject and k == kind}
                      for subject in sorted(subjects)]
        require(partitions[0] == partitions[1] and len(partitions[0]) == coverage[kind])
        owners[kind] = partitions[0]
    require(all(coverage[k] > 0 for k in ("database", "schema", "relation", "routine", "type", "language", "tablespace")))
    return owners


def physical_coverage(data, subjects, owners):
    relations = {}; names = {}; attrs = {}
    for row in data["Q13"]:
        if row[0] == "relation":
            oid(row[6]); oid(row[4]); require(row[6] not in relations)
            relations[row[6]] = row; names[(row[1], row[2])] = row[6]
    for row in data["Q13"]:
        if row[0] == "column":
            key = (names[(row[1], row[2])], row[4])
            require(key not in attrs); attrs[key] = row[3]
    require(owners["relation"] == {i: r[4] for i, r in relations.items()})
    schemas = {}
    for row in data["Q4"]:
        oid(row[6]); oid(row[7])
        if row[1] in schemas: require(schemas[row[1]] == row[6:8])
        schemas[row[1]] = row[6:8]
    require(owners["schema"] == {i: owner for i, owner in schemas.values()})
    require(len(owners["schema"]) == len(schemas))
    routines = {}
    for r in data["Q11"]:
        if r[2] in routines: require(routines[r[2]][1:10] == r[1:10])
        routines[r[2]] = r
    require(owners["routine"] == {i: r[6] for i, r in routines.items()})
    require(len(owners["type"]) >= sum(r[3] in ("r", "p", "v", "m", "f", "c") for r in relations.values()))

    groups = {k: {} for k in ("constraint", "index", "trigger", "rule", "policy", "rls")}
    coverage = {}; totals = {}; rule_names = set()
    for row in data["Q14"]:
        kind = row[0]
        if kind == "catalog":
            require(len(row) == 3 and row[1] in groups and row[1] != "rls" and row[1] not in totals)
            require(type(row[2]) is int and row[2] >= 0); totals[row[1]] = row[2]
            continue
        if kind == "coverage":
            require(len(row) == 7 and row[1] in relations and row[1] not in coverage)
            require(all(type(v) is int and v >= 0 for v in row[2:]))
            coverage[row[1]] = row[2:]; continue
        require(kind in groups)
        if kind == "rule":
            require(len(row) == 10 and row[3] in relations)
            rel = relations[row[3]]
            require(row[1:3] == rel[1:3])
            oid(row[4]); ident = row[4]
            require(all(type(row[i]) is str and row[i] for i in (5, 6, 8, 9)))
            require(row[6] in ("1", "2", "3", "4") and type(row[7]) is bool and row[8] in ("O", "D", "R", "A"))
            rule_key = (row[3], row[5]); require(rule_key not in rule_names); rule_names.add(rule_key)
            # D05 has no approved application-table rewrite rules. System view
            # _RETURN rules are independently inventoried and pinned by manifest.
            require(system(row[1]) and rel[3] == "v" and row[5:8] == ("_RETURN", "1", True) and row[8] == "O")
        elif kind == "constraint":
            require(len(row) == 11 and row[4] is True and row[6] in ("p", "f", "u", "c", "x"))
            require(all(type(row[i]) is str and row[i] for i in (1, 2, 3, 5, 7, 9)))
            ident = row[1]
            if row[7] != "0": oid(row[7])
            if row[6] == "c": require(row[7] == "0")
            if row[2] == "0":
                require(row[6] == "c" and row[8] is None)
            else:
                require(row[2] in relations)
                require(type(row[8]) is tuple and all(type(n) is int and ((row[2], n) in attrs or (n == 0 and row[6] == "x")) for n in row[8]))
            if row[6] == "f":
                require(row[9] in relations and type(row[10]) is tuple and len(row[10]) == len(row[8]))
                require(all(type(n) is int and (row[9], n) in attrs for n in row[10]))
            else:
                require(row[9] == "0" and row[10] is None)
        elif kind == "index":
            require(len(row) == 10 and row[1] in relations and row[2] in relations)
            require(relations[row[1]][3] in ("i", "I") and relations[row[1]][2] == row[6])
            flags((row[3], row[4], row[7], row[8])); require(row[3:5] == (True, True))
            require(type(row[5]) is str and bool(row[5]) and type(row[9]) is tuple and bool(row[9]))
            require(all(type(n) is int and (n == 0 or (row[2], n) in attrs) for n in row[9]))
            ident = row[1]
        elif kind == "trigger":
            require(len(row) == 9 and row[2] in relations and row[3] in routines)
            require(row[4] in ("O", "A") and type(row[5]) is bool)
            require(all(type(row[i]) is str and row[i] for i in (1, 6, 7, 8)))
            if not row[5]: require(row[8] == "0")
            ident = row[1]
        elif kind == "rls":
            require(len(row) == 4 and row[1] in relations)
            flags(row[2:]); require(row[2:] == (False, False)); ident = row[1]
        else:
            # No RLS policies approved in this profile.
            raise Unavailable()
        oid(ident)
        require(ident not in groups[kind]); groups[kind][ident] = row
    require(set(coverage) == set(relations) == set(groups["rls"]))
    require(set(totals) == set(groups) - {"rls"})
    require(all(totals[k] == len(groups[k]) for k in totals))
    for constraint in groups["constraint"].values():
        if constraint[6] == "f":
            require(constraint[7] in groups["index"])
            require(groups["index"][constraint[7]][2] == constraint[9])
    for rel, counts in coverage.items():
        actual = tuple(sum((row[3] if k == "rule" else row[2]) == rel for row in groups[k].values())
                       for k in ("constraint", "index", "trigger", "rule", "policy"))
        require(actual == counts)
        if relations[rel][3] == "v": require(counts[3] == 1)

    for qualified, spec in REQUIRED_STRUCTURE.items():
        rel = names[tuple(qualified.split("."))]
        constraints = [r for r in groups["constraint"].values() if r[2] == rel]
        require(len({r[3] for r in constraints}) == len(constraints))
        require({k: sum(r[6] == k for r in constraints) for k, _ in spec[1]} == dict(spec[1]))
        require(set(spec[2]) <= {(r[3], r[6]) for r in constraints})
        foreign = {(tuple(attrs[(rel, n)] for n in r[8]),
                    relations[r[9]][1] + "." + relations[r[9]][2],
                    tuple(attrs[(r[9], n)] for n in r[10])) for r in constraints if r[6] == "f"}
        require(foreign == set(REQUIRED_FOREIGN_KEYS.get(qualified, ())))
        indexes = [r for r in groups["index"].values() if r[2] == rel]
        require(set(spec[3]) <= {r[6] for r in indexes})
        primary = next(r for r in constraints if r[6] == "p")
        require(tuple(attrs[(rel, n)] for n in primary[8]) == (spec[0][0],))
        backing = set()
        for r in constraints:
            if r[6] in ("p", "u", "x"):
                require(r[7] in groups["index"])
                idx = groups["index"][r[7]]; backing.add(r[7])
                require(idx[2] == rel and idx[9] == r[8])
                require(idx[8] is (r[6] == "p"))
                if r[6] in ("p", "u"): require(idx[7] is True)
        require(all(r[1] in backing or r[6] in spec[3] for r in indexes))
    # Every user index must belong to one of those reviewed tables.
    require(all(i in groups["index"] and relations[groups["index"][i][2]][1] in ("public", "inventory", "audit", "security")
                for i, r in relations.items() if not system(r[1]) and r[3] == "i"))
    required_triggers = {("audit", "events"): ("trg_audit_events_immutable", "audit", "prevent_event_mutation"),
                         ("inventory", "policy_versions"): ("trg_policy_versions_immutable", "inventory", "prevent_policy_version_mutation")}
    for key, (name, schema, function) in required_triggers.items():
        candidates = [r for r in groups["trigger"].values() if r[2] == names[key] and r[7] == name]
        require(len(candidates) == 1)
        trigger = candidates[0]; routine = routines[trigger[3]]
        require(trigger[4:6] == ("O", False) and trigger[8] == "0")
        require((routine[1], routine[3], routine[4], routine[5], routine[7]) == (schema, function, "", "f", False))
    # Internal FK triggers must refer to an observed FK, never a dangling id.
    for trigger in groups["trigger"].values():
        if trigger[5]:
            require(trigger[8] in groups["constraint"] and groups["constraint"][trigger[8]][6] == "f")
    for constraint in groups["constraint"].values():
        if constraint[6] == "f" and not system(relations[constraint[2]][1]):
            for rel in {constraint[2], constraint[9]}:
                expected = 4 if constraint[2] == constraint[9] else 2
                require(sum(t[5] and t[8] == constraint[1] and t[2] == rel for t in groups["trigger"].values()) == expected)


def acl_coverage(policy, data, owners):
    """Complete provenance AND independent effective privilege cells must agree."""
    subjects = {r[0]: r[7] for r in data["Q2"]}
    rels = {(r[1], r[2]): r for r in data["Q13"] if r[0] == "relation"}
    expected = {}
    for r in data["Q4"]:
        expected[("schema", (r[1], r[6]))] = r[7]
    for r in rels.values():
        if r[3] in ("r", "p", "v", "m", "f", "S"):
            expected[("relation", (r[1], r[2], r[6]))] = r[4]
    for r in data["Q13"]:
        if r[0] == "column":
            relation = rels[r[1:3]]
            expected[("column", (r[1], r[2], r[3], relation[6], r[4]))] = relation[4]
    for r in data["Q11"]:
        expected[("routine", (r[1], r[3], r[4], r[2]))] = r[6]
    for kind in ("type", "language", "fdw", "server", "tablespace", "largeobject"):
        for ident, owner in owners[kind].items(): expected[(kind, (ident,))] = owner
    objects = {}; grants = {}; database_ids = set(); parameters = {}
    for row in data["Q10"]:
        require(len(row) in (6, 7) and row[0] in ("object", "grant") and type(row[2]) is tuple)
        key = row[1:3]
        if row[0] == "object":
            require(len(row) == 6 and key not in objects)
            if row[1] == "parameter":
                require(row[3] is None and row[4] == "explicit")
                require(len(row[2]) == 2 and type(row[2][0]) is str and row[2][0] and row[2][0] not in parameters)
                oid(row[2][1]); parameters[row[2][0]] = key; expected[key] = None
            else:
                oid(row[3])
            require(row[4] in ("default", "explicit") and type(row[5]) is int and row[5] >= 0)
            if row[1] == "database":
                require(len(row[2]) == 2 and type(row[2][0]) is str and row[2][0])
                oid(row[2][1]); require(row[2][1] not in database_ids); database_ids.add(row[2][1])
                require(owners["database"].get(row[2][1]) == row[3])
                expected[key] = row[3]
            objects[key] = row
        else:
            require(len(row) == 7 and all(type(row[i]) is str and row[i].isascii() and row[i].isdecimal() for i in (3, 4)))
            oid(row[3])
            if row[4] != "0": oid(row[4])
            require(type(row[5]) is str and row[5] and type(row[6]) is bool)
            # PUBLIC cannot receive a grant option.
            require(row[4] != "0" or row[6] is False)
            ace = row[3:6]
            bucket = grants.setdefault(key, {})
            require(ace not in bucket); bucket[ace] = row[6]
    require(set(objects) == set(expected) and database_ids == set(owners["database"]))
    require(set(grants) <= set(objects))
    for key, row in objects.items():
        require(row[3] == expected[key] and row[5] == len(grants.get(key, {})))
        if key[0] == "column" and row[4] == "default": require(row[5] == 0)
        privileges = {"database": ("CONNECT", "CREATE", "TEMPORARY"), "schema": ("USAGE", "CREATE"),
            "column": COLUMN_PRIVS, "routine": ("EXECUTE",), "type": ("USAGE",), "language": ("USAGE",),
            "fdw": ("USAGE",), "server": ("USAGE",), "tablespace": ("CREATE",), "largeobject": ("SELECT", "UPDATE"),
            "parameter": ("SET", "ALTER SYSTEM")}
        if key[0] == "relation":
            allowed = ("USAGE", "SELECT", "UPDATE") if rels[key[1][:2]][3] == "S" else TABLE_PRIVS
        else:
            allowed = privileges[key[0]]
        require(all(ace[2] in allowed for ace in grants.get(key, {})))

    def effective(key, role, privilege):
        entries = [(ace, option) for ace, option in grants.get(key, {}).items()
                   if ace[1] in ("0", subjects[role]) and ace[2] == privilege]
        return (bool(entries), any(option for _, option in entries))

    for r in data["Q4"]:
        key = ("schema", (r[1], r[6]))
        require(effective(key, r[0], "USAGE") + effective(key, r[0], "CREATE") == r[2:6])
    for r in data["Q5"]:
        rel = rels[r[1:3]]
        require(effective(("relation", (r[1], r[2], rel[6])), r[0], r[3]) == r[4:6])
    column_numbers = {(r[1], r[2], r[3]): r[4] for r in data["Q13"] if r[0] == "column"}
    for r in data["Q6"]:
        rel = rels[r[1:3]]
        table = effective(("relation", (r[1], r[2], rel[6])), r[0], r[4])
        column = effective(("column", (r[1], r[2], r[3], rel[6], column_numbers[r[1:4]])), r[0], r[4])
        require((table[0] or column[0], table[1] or column[1]) == r[5:7])
    for r in data["Q7"]:
        rel = rels[r[1:3]]
        require(effective(("relation", (r[1], r[2], rel[6])), r[0], r[3]) == r[4:6])
    for r in data["Q11"]:
        require(effective(("routine", (r[1], r[3], r[4], r[2])), r[0], "EXECUTE") == (r[10], r[11]))
    databases = {key[1][0]: key for key in objects if key[0] == "database"}
    require(policy.target[2] in databases)
    parameter_cells = set()
    for r in data["Q9"]:
        if r[0] == "database": require(effective(databases[r[2]], r[1], r[3]) == r[4:6])
        if r[0] == "parameter":
            require(r[2] in parameters and r[1:4] not in parameter_cells)
            parameter_cells.add(r[1:4])
            require(effective(parameters[r[2]], r[1], r[3]) == r[4:6])
    require(parameter_cells == {(s, n, p) for s in subjects for n in parameters for p in ("SET", "ALTER SYSTEM")})
    auxiliary = {(r[1], (r[2],), r[3], r[4], r[5], r[6]) for r in data["Q9"] if r[0] == "object_acl"}
    actual_auxiliary = {(key[0], key[1], ace[0], ace[1], ace[2], option)
                        for key, entries in grants.items() if key[0] in ("type", "language", "fdw", "server", "tablespace", "largeobject")
                        for ace, option in entries.items()}
    require(auxiliary == actual_auxiliary)
    # Queries cannot succeed without these explicitly qualified functions. Exact
    # overloads and catalog visibility still require the real PG16 gate.
    from .queries import CATALOG
    import re
    functions = {name for q in CATALOG.values() for name in re.findall(r"pg_catalog\.([a-z_]+)\(", q.sql)}
    require(functions <= {r[3] for r in data["Q11"] if r[0] == policy.verifier_role and r[1] == "pg_catalog" and r[10] is True})
    require({"jsonb_build_array", "current_database", "inet_server_addr", "inet_server_port", "current_setting"} <=
            {r[3] for r in data["Q11"] if r[0] == policy.target[3] and r[1] == "pg_catalog" and r[10] is True})


def default_coverage(data, owners, role_ids):
    objects = {}; grants = {}
    for r in data["Q12"]:
        require(r[0] in ("default", "grant"))
        require(len(r) == (6 if r[0] == "default" else 9))
        oid(r[1]); oid(r[4])
        require(type(r[2]) is str and r[2].isdecimal() and r[3] in ("r", "S", "f", "T", "n"))
        require(r[2] == "0" or r[2] in owners["schema"])
        if r[0] == "default":
            require(r[4] not in objects and type(r[5]) is int and r[5] >= 0)
            require(owners["defaultacl"].get(r[4]) == r[1]); objects[r[4]] = r
        else:
            oid(r[5]); oid(r[6])
            require(type(r[7]) is str and r[7] and type(r[8]) is bool)
            require(r[7] in {"r": TABLE_PRIVS, "S": ("USAGE", "SELECT", "UPDATE"),
                    "f": ("EXECUTE",), "T": ("USAGE",), "n": ("USAGE", "CREATE")}[r[3]])
            require(r[6] not in role_ids | {"0"})
            bucket = grants.setdefault(r[4], {})
            require(r[5:8] not in bucket); bucket[r[5:8]] = r
    require(set(objects) == set(owners["defaultacl"]) and set(grants) <= set(objects))
    for ident, marker in objects.items():
        require(marker[5] == len(grants.get(ident, {})))
        require(all(r[1:5] == marker[1:5] for r in grants.get(ident, {}).values()))


def evaluate(policy, data, runtime_identity, verifier_identity, started):
    identity(policy, runtime_identity, policy.target[3])
    identity(policy, verifier_identity, policy.verifier_role)
    require(set(data) == {f"Q{i}" for i in range(2, 17)})
    # Receiving all family names is not proof of structural coverage.
    validate_contract(policy, data)
    expected = dict(policy.manifest)
    for q, rows in data.items():
        if q != "Q15":
            # Exact canonical comparison preserves NULL/bool/int distinctions.
            require(canonical(rows) == canonical(expected[q]))
    require(data["Q15"] == normalize((("application", "f066a01a7230"), ("security", "b12b01a7230")), 2))
    # Only after complete validation; no values replace missing query evidence.
    evidence = PrivilegeEvidence(policy.target,
        RequiredPrivileges(**{f.name: True for f in fields(RequiredPrivileges)}),
        AdministrativePrivileges(**{f.name: False for f in fields(AdministrativePrivileges)}),
        OwnershipPrivileges(**{f.name: False for f in fields(OwnershipPrivileges)}),
        DDLPrivileges(**{f.name: False for f in fields(DDLPrivileges)}))
    schemas = frozenset(row[1] for row in data["Q4"])
    return ReadinessObservation(policy.target, started, True, True, schemas,
                                "f066a01a7230", "b12b01a7230", evidence)
