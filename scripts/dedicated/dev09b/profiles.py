"""Historical inventory projections plus application-only detailed v2 dispatch.

No import/execution of operational validators. The projections below reuse
their compatible inventory predicates only. Full base/ACL/ownership/catalog
coverage is incomplete and cannot confirm base, success or rollback.
"""
from types import MappingProxyType

from .codec import Unsupported, canonical, require


DETAILED_PROFILE = "dev09b-application-f066-catalog-v2"
# New profile source pins only. Legacy inventories and manifests stay historical.
DETAILED_SOURCES = MappingProxyType({
    'scripts/dedicated/dev09b/codec.py': 'fc63c486379b4b7930da82b8f1e34e0b753ec24e0c95643af188632a54fad92b',
    'scripts/dedicated/dev09b/layers.py': '069dfb6e45974ea8de073b72505cedca9bf2b29a25ca5df76cf568c14554436d',
    'scripts/dedicated/dev09b/physical.py': '0315f4946ff30d42ec21080eadb782bef2772391b2c1aeb54f6bb8bc280ffa28',
    'scripts/dedicated/dev09b/migration_catalog.py': '0eefc15a6e92e8ad9dd94a37e300b2936bc9b32b68b2d496f449f74a4030d494',
    'scripts/dedicated/dev09b/detailed_catalog.py': '85ef171e788bdd5e483ea8f638d2c37f333f1268ac37f77978629b2e42a6c252',
    'backend/migrations/dev09b_inspection.py': '0d93363653f545de70002f10ac7742d3c2eb165d8caf80a2519202d148569aa2',
    'backend/migrations/dev09b_catalog_adapter.py': 'b6631bb462e8f8423b8af34b821c61bc64b8b2503c5431fbc9a1ed0e305f9468',
    'backend/migrations/dev09b_detailed_queries.py': '0aa22d6091bde79c9d4d2ba94c7d3c6b4b2bf5ca52e545e610cae3797df36731',
    'backend/migrations/dev09b_inspection_queries.py': 'ea7b300ba0fd9d47494b785231bbe41d7f3ffb640f319a0bb8edf7db3ec45a57',
    'scripts/dedicated/dev09b/own_settings.py': 'e6d59ab95d125ca8f6158b98094e8d0654645910eba4f423faedff96b535ad86',
    'scripts/dedicated/dev09b/fixed_catalog_sources.py': '2c2b682c523e226242695773fa84237d37bc0507bdeec88940df606323beae58',
    'scripts/dedicated/dev09b/fixed_catalog_context.py': 'fb4db48329f0b5c05e93460e2eb6c45813d92842242103812468a527e2e1e2bc',
    'scripts/dedicated/dev09b/artifacts/pg16-source/sources.candidate.json': 'a29f5605acccce89f6a0de7929b9ac53e9034ff774522c5e1946ceb5f3928193',
    'scripts/dedicated/dev09b/artifacts/pg16-source/COPYRIGHT': '3d6af92ff8a4c2cdf69afb1cf44edea727922f5cd0cf8b5f72b11cdecac8fdfd',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/access/heap/heaptoast.c': '3cdf095a88e65babd39a9b44dfe3898477748838c034f41a7ea7f0320995a980',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/catalog/heap.c': '8203f3ec2c3a876703fda6a4b1387a43e8d252c6d28e38503ce5cfd057bb7da7',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/catalog/index.c': '44f2ff91c6a9e999d87eafdcb09dbc543f8214d63d8481352a0b185f795827e7',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/catalog/pg_type.c': '93237fa37a52ae9799b3d0a2fb1fa72ee36fa52f3158f9c8ac938fd55135b2a4',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/commands/tablecmds.c': 'fdf9777fa925ef3801754dcf7f5da340b90f1f91258220608ee90ab1afb5d8c8',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/commands/typecmds.c': '86f95ebed328ddf37d132e995a4384d2ef7cf8cc5ba2c748fe8a87e811139dfb',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/utils/adt/acl.c': 'd7022b114917f95e3d249e374f211d6bc14db68be8bcb1708ef032103377512c',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/utils/adt/format_type.c': 'c4af9d64e54d9186e133df3cca74c4141d06c5cfc2912d0d945cd9e6812cd8a9',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/utils/adt/regproc.c': '0d0d6d2da1e931b7089d7721cef704e21825409b607e760609dc644a79d522df',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/backend/utils/adt/ruleutils.c': '0898f93834a25de4fda9d72ee450077713353fed464fe7ca556912ca278ad455',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/include/access/heaptoast.h': '9991d0af9e696157415f43573fe5d6d79c4aa09af3cd7565c836df5579495dbc',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/include/access/htup_details.h': '00b88e1c5c687e1933fec1cebf7fdb68f93c9432b2149a180788dc89330fbaa2',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/include/catalog/pg_type.h': '6e5fd32ffe432d6ca640abacb99acc9a1d54ddb216dc363c3f4a2af616761d66',
    'scripts/dedicated/dev09b/artifacts/pg16-source/src/include/pg_config_manual.h': '8b0d42f19610a735f6d59230e6213d2822d808f37f3f6e2c27873ab5ca91771f',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/sources.candidate.json': '4ee133de1dec6c592ec04786774474310107572319262b4042ff887b2d4f4f70',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.2--1.3.sql': '5dc7a402185ddbdff6d4488686ba28e3e89c59a850e54f833114f383cda19123',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.2.sql': '6ce065d3cf6225cdc56d06ce0e8c18f404b658f18d5ae5b5adc652b69b4a66b4',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.3--1.4.sql': '7a7f5ece012f23d7a11f460e7536b65435ee0aeead0717963a428b092135ab84',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.4--1.5.sql': '4e28241668ad1ccc0d645ac46726a160617af4d07a8d77f188776e91b085d3ce',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.5--1.6.sql': '593f167508dc9c6e8be7e5565c15d5fb8d259e38f6139170b72b3da115e2cff4',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist--1.6--1.7.sql': '426340ca65ed9763e3934c39e5f427e743a4947f6e89eba6bb4c7d9bd3ad0bf5',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/btree_gist.control': '3ca06b88ec216596b06215d9c0cc7f08cd10f0f3fdaf48f58b19bce0464c07ee',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/plpgsql--1.0.sql': 'f4e7e05438808ac0da0b3801397d16e36102969af7e2ffc982def5b7524fb557',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/extension/plpgsql.control': '9457c3f51d6bdfab93f13080d177795a9274c025e378fb613218342e3a3c7b45',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/postgres.bki': 'e7ccf0cbdf9a993e2bbfd99e3c4bb2161036ad33233d66281756750c409c983f',
    'scripts/dedicated/dev09b/artifacts/pg16-querytrial/system_functions.sql': '56b935b41d653a9dd7282b7d0871b37a4ecccd72bbfe03e79a89e05e0131347c',
})


SOURCES = MappingProxyType({
    "scripts/postgres/auth03_alembic_executor.py": "66c18319414c29f49ae163ef86b098924592102b566cd894fd4824933704d00b",
    "scripts/postgres/m12b_security_migration.py": "c2608a2c8d0391dc3e5960fe797d4c8f77be5165475cb0058de4f66dd51ed9fe",
    "backend/security_migrations/contract.py": "0a29cbc074907a4b9023709a7a8770ea5a48e1d000bcd0197255d4dcf49fb41b",
    "backend/app/readiness_postgres/evaluate.py": "0137f9343672a95fc0138b9e6ac5207fdb23b468162dce65b5867fd2758210d5",
    "backend/app/readiness_postgres/policy.py": "7dc4100d063e4cb3c09957e8fb117f2b84fddc7b5b28f73f57422061042bff81",
    "backend/app/readiness_postgres/queries.py": "9ddad5dc61f2c5f81ca5db8e410064e506b9a93607b3f2cde3add86c3ad1ed2b",
})
PROFILES = MappingProxyType({
    "auth03-base-inventory-v1": ("scripts/postgres/auth03_alembic_executor.py",),
    "m12b-f066-inventory-v1": ("scripts/postgres/m12b_security_migration.py", "backend/security_migrations/contract.py"),
    "m12b-b12-inventory-v1": ("scripts/postgres/m12b_security_migration.py", "backend/security_migrations/contract.py"),
    "g2-f066-b12-d05-v1": ("backend/app/readiness_postgres/evaluate.py", "backend/app/readiness_postgres/policy.py", "backend/app/readiness_postgres/queries.py"),
})
PREPARED_SOURCES = MappingProxyType({
    "backend/migrations/dev09b_inspection_queries.py":"6c6651e5b607bcafb54490f64935a4eac27cbe9141267967b22b6e6a083ae5cd",
    "backend/migrations/dev09b_inspection.py":"663850ec07f1ddeac8d2094b415451cc6b1bce4b508499536e6b97ea80b754bd",
    "backend/migrations/dev09b_prerequisites.py":"e2c018ab635ecab4965728e1a3a85fb8dc52121a863749644526c36a0fa7796b",
    "backend/migrations/env.py":"c3c087f52aad22e20fc36a911a30c2d3c211054c30f1a9537bdecbe21271afda",
    "backend/security_migrations/env.py":"82d77a4a50b0433de469afb62a94aa8f85ad5f6c45faa7cedcf0470e9756a5ea",
    "backend/migrations/versions/af62df027d9d_create_inventory_resources_baseline.py":"775dbc0c8df3857f52d5907466413f2efbece62e07e6c2f1086ee7775bf0a2b2",
    "backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py":"beb9fdf625b211753c8bb11d218dad75b62cb243144a886e79e143c4708611b0",
    "backend/security_migrations/versions/b12b01a7230_create_security.py":"ecd89d568ae888ce0faa24965be0916f82be090257cf6ad486f592093278bfc9",
    "backend/migrations/versions/ba06dd956da9_create_inventory_group_memberships.py":"da5553776449de5584c45015ad8156235d7f0fcb7591e462763beeb14a0b0d21",
    "backend/migrations/versions/9e1b7c42a630_create_inventory_resource_tags.py":"aa7201329e8440a07f6e700fb04b485c16e38cf6232d26df0f41518107d58698",
})
PREPARED_PROFILES=frozenset({"dev09b-prepared-base-v1","dev09b-prepared-f066-v1","dev09b-prepared-b12-v1"})
INVENTORY = frozenset("resources resource_identifiers resource_relations groups group_memberships group_rules tags resource_tags policies policy_versions policy_assignments effective_configs".split())
SECURITY = frozenset("local_users login_sessions global_role_grants login_throttles".split())


def validator_inventory(profile):
    if profile == DETAILED_PROFILE:
        return [{"path":p,"sha256":h} for p,h in sorted(DETAILED_SOURCES.items())]
    if type(profile) is str and profile in PREPARED_PROFILES:
        return [{"path":p,"sha256":h} for p,h in sorted(PREPARED_SOURCES.items())]
    if type(profile) is not str or profile not in PROFILES:
        raise Unsupported("Unknown or unversioned DEV09B catalog profile")
    return [{"path": p, "sha256": SOURCES[p]} for p in sorted(PROFILES[profile])]


def validate_profile_reference(catalog):
    require(canonical(catalog["validator_inventory"]) == canonical(validator_inventory(catalog["profile"])))
    if catalog["profile"] == DETAILED_PROFILE:
        from .detailed_catalog import validate_catalog
        validate_catalog(catalog)
    else:require(catalog["detailed_catalog"] == {"profile": catalog["profile"]})


def validate_inventory_projection(catalog):
    """Validate only the compatible inventory predicate, never full coverage."""
    from .layers import catalog as validate_catalog
    validate_catalog(catalog)
    validate_profile_reference(catalog)
    profile = catalog["profile"]
    if profile == DETAILED_PROFILE:return
    prepared=profile in PREPARED_PROFILES
    schemas = {"public","inventory","audit","security"} if prepared else {"public"}
    relations = set()
    if profile not in {"auth03-base-inventory-v1","dev09b-prepared-base-v1"}:
        schemas |= {"inventory", "audit"}
        relations |= {("inventory", n, "r") for n in INVENTORY}
        relations |= {("audit", "events", "r"), ("public", "alembic_version", "r")}
    if profile in {"m12b-b12-inventory-v1", "g2-f066-b12-d05-v1","dev09b-prepared-b12-v1"}:
        schemas.add("security")
        relations |= {("security", n, "r") for n in SECURITY}
        relations.add(("public", "alembic_security_version", "r"))
    if profile == "g2-f066-b12-d05-v1":
        # G2's inventory projection includes these system schemas; the M1.2B
        # readers above explicitly filter them. They are not interchangeable.
        schemas |= {"pg_catalog", "information_schema", "pg_toast"}
    require(catalog["schemas"] == sorted(schemas))
    require({(r["schema"], r["name"], r["kind"]) for r in catalog["relations"]} == relations)


def require_complete_profile(profile, *, snapshot=None):
    validator_inventory(profile)
    if profile == DETAILED_PROFILE and snapshot is not None:
        from .layers import read_snapshot
        from .detailed_catalog import validate_contract
        payload,target,executor,plan,semantic,physical,provenance=read_snapshot(snapshot)
        return validate_contract(physical,target,semantic,provenance)
    raise Unsupported("Detailed catalog/defaults/extensions/ownership/ACL profile not complete; cannot confirm migration")
