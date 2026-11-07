"""Explicit-connection PREPARED inspection adapter. No connection/authority issuer.

Queries and comparisons are implemented; running on PostgreSQL is a separate
operation. Trusted approval and independent f066 verification are injected ports.
Fixed expectations must be supplied before collecting observations. This adapter
is not a migration executor or evidence-of-success/rollback implementation.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from sqlalchemy import text
from . import dev09b_prerequisites as h
from .dev09b_inspection_queries import QUERIES, LEDGER_SQL
from scripts.dedicated.dev09b import codec as c


@dataclass(frozen=True)
class InspectionApproval:
    attestation: h.ProfileAttestation
    contract_sha256: str
    binding_sha256: str
    decision_reference: str


class ProfileVerifier(Protocol):
    def verify(self, profile_json: bytes, contract_json: bytes) -> InspectionApproval: ...


@dataclass(frozen=True)
class BaselineConfirmation:
    target_sha256: str
    catalog_sha256: str
    application_revision: str
    evidence_reference: str


class IndependentBaseline(Protocol):
    def confirm(self, profile_json: bytes, catalog_json: bytes) -> BaselineConfirmation: ...


def digest(value):
    return sha256(c.canonical(value)).hexdigest()


def rows(name, values):
    """No LIMIT/silent truncation; fixed row fields and exact JSON scalar types."""
    q = QUERIES[name]
    h.require(type(values) is list and len(values) <= q.maximum, 'Incomplete/oversized query: '+name)
    for row in values:
        h.require(type(row) is dict and set(row) == set(q.fields), 'Incomplete row: '+name)
        for key,value in row.items():
            if key in {'superuser','createdb','createrole','replication','bypassrls','database_owner','database_create','database_temporary',
                       'owner_login','can_create','can_use','grant_create','grant_use','member','inherited','can_set',
                       'row_security','force_row_security','not_null','validated','deferrable','initially_deferred','valid','ready','live',
                       'security_definer','internal','permissive','cycle','grant_option'}:
                h.require(type(value) is bool, 'Boolean required: '+name+'.'+key)
            elif key in {'position','subid','pid','port','server_version_num','entries'}:
                h.require(type(value) is int, 'Integer required: '+name+'.'+key)
            elif key in {'options','config'}:
                h.require(value is None or type(value) is list and all(type(x) is str for x in value))
            elif key=='properties':
                schemas = {
                    'pg_type': set('typname typnamespace typowner typlen typbyval typtype typcategory typispreferred typisdefined typdelim typrelid typsubscript typelem typarray typinput typoutput typreceive typsend typmodin typmodout typanalyze typalign typstorage typnotnull typbasetype typtypmod typndims typcollation typdefaultbin typdefault typacl'.split()),
                    'pg_range': set('rngtypid rngsubtype rngmultitypid rngcollation rngsubopc rngcanonical rngsubdiff'.split()),
                    'pg_operator': set('oprname oprnamespace oprowner oprkind oprcanmerge oprcanhash oprleft oprright oprresult oprcom oprnegate oprcode oprrest oprjoin'.split()),
                    'pg_opclass': set('opcmethod opcname opcnamespace opcowner opcfamily opcintype opcdefault opckeytype'.split()),
                    'pg_opfamily': set('opfmethod opfname opfnamespace opfowner'.split()),
                    'operator': set('amopfamily amoplefttype amoprighttype amopstrategy amoppurpose amopopr amopmethod amopsortfamily'.split()),
                    'function': set('amprocfamily amproclefttype amprocrighttype amprocnum amproc'.split()),
                }
                family = ('pg_type' if name=='type_details' else 'pg_range' if name=='ranges' else
                          row.get('catalog','').removeprefix('pg_catalog.') if name=='extension_properties' else row.get('kind'))
                if family in schemas:
                    h.require(type(value) is dict and set(value)==schemas[family], 'Incomplete extension properties')
                    for prop,cell in value.items():
                        if prop=='typacl':h.require(cell is None or type(cell) is list and all(type(x) is str for x in cell))
                        elif prop in {'typdefaultbin','typdefault'}:h.require(cell is None or type(cell) is str)
                        elif prop in {'oprcanmerge','oprcanhash','opcdefault','typbyval','typispreferred','typisdefined','typnotnull'}:h.require(type(cell) is bool)
                        elif prop in {'oprname','oprkind','oprcode','oprrest','oprjoin','opcname','opfname','amoppurpose','amproc','typname','typtype','typcategory','typdelim','typsubscript','typinput','typoutput','typreceive','typsend','typmodin','typmodout','typanalyze','typalign','typstorage','rngcanonical','rngsubdiff'}:h.require(type(cell) is str)
                        else:h.require(type(cell) is int)
                else:h.require(value is None, 'Unsupported extension property family')
            else:
                h.require(value is None or type(value) is str, 'String required: '+name+'.'+key)
        c.canonical(row)
    result = sorted(values, key=c.canonical)
    h.require(len({c.canonical(row) for row in result}) == len(result), 'Duplicate query row: '+name)
    return result


def check_contract(raw, p):
    v = c.parse(raw, maximum=16*1024*1024)
    c.closed(v, {'schema_version', 'profile_sha256', 'query_inventory_sha256', 'binding', 'source_inventory', 'checkpoints'})
    c.integer(v['schema_version'], 1, 1)
    h.require(v['profile_sha256'] == sha256(p).hexdigest())
    h.require(v['query_inventory_sha256'] == digest({k:{'sql':q.sql,'fields':list(q.fields),'maximum':q.maximum} for k,q in QUERIES.items()}), 'Query inventory divergence')
    binding = v['binding']
    c.closed(binding, set(QUERIES['identity'].fields))
    for k in ('database', 'current_user', 'session_user', 'system_identifier','backend_start','xact_start','virtualxid','address'):
        h.require(type(binding[k]) is str and bool(binding[k]), 'Missing binding: '+k)
    for k in ('pid','port','server_version_num'):
        h.require(type(binding[k]) is int and binding[k] > 0, 'Invalid binding: '+k)
    h.require(160000 <= binding['server_version_num'] < 170000, 'PG16 required')
    sources = v['source_inventory']
    h.require(type(sources) is list and bool(sources))
    for s in sources:
        c.closed(s, {'path', 'sha256'});c.digest_text(s['sha256'])
        h.require(type(s['path']) is str and not Path(s['path']).is_absolute()
                  and all(part not in {'','.', '..'} for part in s['path'].split('/')))
    h.require(sources == sorted(sources,key=lambda x:x['path']) and len({s['path'] for s in sources})==len(sources))
    profile = h.decode_profile(p)
    h.require(digest(sources) == profile['source_inventory_sha256'])
    h.require((binding['database'], binding['system_identifier'], binding['current_user'], binding['session_user']) ==
              (profile['database'], profile['system_identifier'], profile['migrator'], profile['migrator']))
    checkpoints = v['checkpoints']
    h.require(type(checkpoints) is list and bool(checkpoints))
    expected_order = ['environment','inventory','btree_gist','btree_gist','audit'] if profile['operation'].startswith('application-') else ['environment','security']
    h.require([x.get('requested') for x in checkpoints] == expected_order, 'Incomplete checkpoint sequence')
    expected_ledgers = ([({'presence':'ABSENT','revisions':[]},{'presence':'ABSENT','revisions':[]}),
        *[({'presence':'PRESENT','revisions':rev},{'presence':'ABSENT','revisions':[]}) for rev in ([],['da34876e4210'],['7c4e2a91b605'],['f065d01a7230'])]]
        if profile['operation'].startswith('application-') else
        [({'presence':'PRESENT','revisions':['f066a01a7230']},{'presence':'ABSENT','revisions':[]}),
         ({'presence':'PRESENT','revisions':['f066a01a7230']},{'presence':'PRESENT','revisions':[]})])
    for index, point in enumerate(checkpoints):
        c.closed(point, {'requested', 'queries', 'ledgers'})
        # Identity is dynamic only in the sense of explicitly supplied binding;
        # all catalog/ACL/settings expectations remain fixed and authenticated.
        c.closed(point['queries'], set(QUERIES)-{'identity'})
        for name, value in point['queries'].items():
            h.require(value == rows(name,value), 'Expectation rows must be ordered')
        c.closed(point['ledgers'], set(LEDGER_SQL))
        h.require(point['ledgers'] == dict(zip(LEDGER_SQL,expected_ledgers[index])), 'Checkpoint ledger semantics mismatch')
        for state in point['ledgers'].values():
            c.closed(state, {'presence','revisions'})
            h.require(state['presence'] in {'ABSENT','PRESENT'} and type(state['revisions']) is list)
            h.require(all(type(x) is str and bool(x) for x in state['revisions']))
            h.require(len(set(state['revisions'])) == len(state['revisions']))
            h.require(state['presence'] != 'ABSENT' or state['revisions']==[])
    return v


class PreparedInspectionPort:
    def __init__(self, connection, transaction, *, profile_verifier=None,
                 contract_json=None, source_root=None, independent_baseline=None):
        # No calls on the connection, filesystem, verifier or database here.
        self._connection = connection
        self._transaction = transaction
        self._verifier = profile_verifier
        self._contract_json = contract_json
        self._root = source_root
        self._baseline = independent_baseline
        self._cursor = 0
        self._failed = False

    def assert_connection(self, connection):
        h.require(not self._failed, 'Inspection port failed; no automatic retry')
        h.require(connection is self._connection and connection is not None, 'Connection changed')
        h.require(connection.closed is False and connection.dialect.name == 'postgresql', 'Connection unavailable')
        h.require(connection.in_transaction() is True and connection.get_transaction() is self._transaction
                  and self._transaction is not None and self._transaction.is_active is True, 'Transaction changed')

    def verify_approved_profile(self, profile_json):
        self.assert_connection(self._connection)
        if self._verifier is None:raise h.MissingParameter('dev09b.trusted_profile_verifier')
        if type(self._contract_json) is not bytes:raise h.MissingParameter('dev09b.fixed_inspection_contract')
        contract = check_contract(self._contract_json, profile_json)
        result = self._verifier.verify(profile_json, self._contract_json)
        h.require(type(result) is InspectionApproval, 'Trusted profile verification unavailable')
        p = h.decode_profile(profile_json)
        a = result.attestation
        h.require(type(a) is h.ProfileAttestation and a.operationally_authenticated is True
                  and a.classification == 'OPERATIONAL' and a.profile_sha256 == sha256(profile_json).hexdigest()
                  and a.target_sha256 == p['target_sha256'] and a.bundle_sha256 == p['bundle_sha256'])
        h.require(result.contract_sha256 == sha256(self._contract_json).hexdigest()
                  and result.binding_sha256 == digest(contract['binding'])
                  and type(result.decision_reference) is str and bool(result.decision_reference), 'Approval binding mismatch')
        self.assert_connection(self._connection)
        return a

    def _collect(self, name, sql=None):
        self.assert_connection(self._connection)
        statement = QUERIES[name].sql if sql is None else sql
        result = self._connection.execute(text(statement))
        try:
            collected = []
            for row in result.mappings():
                collected.append(dict(row))
                if len(collected) > (QUERIES[name].maximum if sql is None else 2):
                    raise h.PrerequisiteRefused('Oversized query: '+name)
            return rows(name,collected) if sql is None else collected
        finally:
            result.close()

    def observe(self, profile_json, requested):
        try:
            return self._observe(profile_json, requested)
        except Exception:
            self._failed = True
            raise

    def _observe(self, profile_json, requested):
        self.verify_approved_profile(profile_json)
        p = h.decode_profile(profile_json)
        contract = check_contract(self._contract_json, profile_json)
        h.require(self._cursor < len(contract['checkpoints']), 'Checkpoint sequence exhausted')
        point = contract['checkpoints'][self._cursor]
        h.require(point['requested'] == requested, 'Unexpected/repeated checkpoint')
        if self._root is None:raise h.MissingParameter('dev09b.source_root')
        root = Path(self._root)
        for s in contract['source_inventory']:
            file = root / s['path']
            h.require(not any(x.is_symlink() for x in (file,*file.parents)), 'Symlink source')
            h.require(file.is_file() and sha256(file.read_bytes()).hexdigest()==s['sha256'], 'Source inventory divergence')
        first = self._collect('identity')
        h.require(c.canonical(first) == c.canonical([contract['binding']]), 'Target/session/transaction changed')
        observations = {}
        for name in QUERIES:
            if name == 'identity':continue
            observations[name] = self._collect(name)
            h.require(c.canonical(observations[name]) == c.canonical(point['queries'][name]), 'Catalog/ACL/settings mismatch: '+name)
        h.require({r['name'] for r in observations['settings']} == {
            'search_path','session_replication_role','row_security','standard_conforming_strings',
            'shared_preload_libraries','session_preload_libraries','local_preload_libraries',
            'server_encoding','lc_collate','lc_ctype','transaction_isolation','transaction_read_only'}, 'Settings coverage incomplete')
        settings = {r['name']:r['setting'] for r in observations['settings']}
        h.require(len(settings)==len(observations['settings']), 'Duplicate setting')
        h.require(settings['search_path']=='public' and settings['session_replication_role']=='origin' and settings['row_security']=='on'
                  and settings['standard_conforming_strings']=='on', 'Unsafe execution settings')
        # Distinct ABSENT, PRESENT-empty, PRESENT-revision; never infer base from
        # a missing row. Catalog was compared before reading a literal ledger.
        relations = {(r['schema'],r['name']):r for r in observations['relations']}
        ledgers = {}
        for chain, sql in LEDGER_SQL.items():
            table = 'alembic_version' if chain=='application' else 'alembic_security_version'
            row = relations.get(('public',table))
            if row is None:state = {'presence':'ABSENT','revisions':[]}
            else:
                h.require(row['kind']=='r', 'Ledger is not an ordinary table')
                ledger_rows = self._collect('identity',sql)
                h.require(all(set(x)=={'version_num'} and type(x['version_num']) is str for x in ledger_rows), 'Malformed ledger')
                revisions = sorted(x['version_num'] for x in ledger_rows)
                h.require(len(set(revisions))==len(revisions), 'Duplicate ledger revision')
                state = {'presence':'PRESENT','revisions':revisions}
            h.require(state == point['ledgers'][chain], 'Ledger divergence: '+chain)
            ledgers[chain] = state
        h.require(not observations['executable_definers'], 'Executable SECURITY DEFINER installation/bypass path unsupported')
        privileges = observations['privileges']
        h.require(len(privileges)==1 and all(type(v) is bool and v is False for v in privileges[0].values()), 'Excessive privileges')
        memberships = observations['memberships']
        h.require(all(type(r[k]) is bool and r[k] is False for r in memberships for k in ('member','inherited','can_set')), 'Role membership')
        schema_rows = {r['name']:r for r in observations['schemas']}
        h.require(len(schema_rows)==len(observations['schemas']), 'Duplicate schema')
        for name,owner in p['schema_owners'].items():
            row = schema_rows.get(name)
            h.require(row is not None and row['owner']==owner and row['owner_login'] is False, 'Schema owner divergence')
        allowed = {'inventory','audit','public'} if p['operation'].startswith('application-') else {'security','public'}
        schema_create = sorted(r['name'] for r in observations['schemas'] if r['can_create'] is True)
        schema_usage = sorted(r['name'] for r in observations['schemas'] if r['can_use'] is True and r['name'] in {'inventory','audit','security','public'})
        # System USAGE is normal. CREATE on ANY additional schema is not.
        h.require(set(schema_create)==allowed and set(schema_usage)==allowed)
        for r in observations['schemas']:
            for k in ('owner_login','can_create','can_use','grant_create','grant_use'):h.require(type(r[k]) is bool)
            h.require(r['grant_create'] is False and r['grant_use'] is False, 'Grant option not allowed')
        ext = [r for r in observations['extension'] if r['name']=='btree_gist']
        h.require(len(ext)==1)
        ext = {k:v for k,v in ext[0].items() if k!='name'}
        # Fixed query rows define versioned member/ACL digest normal forms. These
        # differ from offline phase-normalized object schemas: no equivalence claim.
        members = [r for r in observations['extension_members'] if r['extension']=='btree_gist']
        h.require(bool(members), 'Extension member inventory empty')
        ext['members_sha256'] = digest(members)
        ext['acl_sha256'] = digest([r for r in observations['extension_acl'] if r['extension']=='btree_gist'])
        h.require(ext == p['btree_gist'], 'Extension binding divergence')
        confirmed = False
        if p['operation'].startswith('security-'):
            h.require(ledgers['application']=={'presence':'PRESENT','revisions':['f066a01a7230']}, 'f066 ledger required')
            if self._baseline is None:raise h.MissingParameter('dev09b.independent_f066_verifier')
            result = self._baseline.confirm(profile_json,c.canonical(observations))
            h.require(type(result) is BaselineConfirmation and result.target_sha256==p['target_sha256']
                      and result.catalog_sha256==digest(observations) and result.application_revision=='f066a01a7230'
                      and type(result.evidence_reference) is str and bool(result.evidence_reference), 'Independent f066 confirmation unavailable')
            confirmed = True
        last = self._collect('identity')
        h.require(c.canonical(last)==c.canonical(first), 'Binding changed during inspection')
        self.verify_approved_profile(profile_json)
        result = {**{k:first[0][k] for k in ('database','system_identifier','current_user','session_user')},
                  **privileges[0], 'extension_install_power':False, 'memberships':[],
                  'schemas':{n:{'owner':schema_rows[n]['owner'],'owner_login':schema_rows[n]['owner_login']} for n in p['schema_owners']},
                  'extension':ext,'residual_objects':[], 'schema_create':schema_create,'schema_usage':schema_usage,
                  'prior_application_confirmed':confirmed,'source_inventory_sha256':digest(contract['source_inventory'])}
        h.validate_observation(p,result,requested)
        self._cursor += 1
        return result
