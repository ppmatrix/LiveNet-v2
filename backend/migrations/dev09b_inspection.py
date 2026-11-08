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
from . import dev09b_inspection_support as support
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
        if name=='identity':
            try:support.host_address(row['address'])
            except support.InspectionInputError as exc:raise h.PrerequisiteRefused(exc.code) from None
        c.canonical(row)
    if name=='settings':
        try:support.settings_inventory(values)
        except support.InspectionInputError as exc:
            if exc.code=='SETTINGS_VALUE_UNAVAILABLE':
                raise h.MissingParameter('dev09b.settings.'+','.join(exc.names)+'.trusted_observation') from None
            raise h.PrerequisiteRefused(exc.code) from None
    result = sorted(values, key=c.canonical)
    h.require(len({c.canonical(row) for row in result}) == len(result), 'Duplicate query row: '+name)
    return result


def check_collector_binding(binding):
    c.closed(binding, set(QUERIES['identity'].fields))
    for k in ('database', 'current_user', 'session_user', 'system_identifier','backend_start','xact_start','virtualxid','address'):
        h.require(type(binding[k]) is str and bool(binding[k]), 'Missing binding: '+k)
    for k in ('pid','port','server_version_num'):
        h.require(type(binding[k]) is int and binding[k] > 0, 'Invalid binding: '+k)
    try:support.host_address(binding['address'])
    except support.InspectionInputError as exc:raise h.PrerequisiteRefused(exc.code) from None
    h.require(160000 <= binding['server_version_num'] < 170000, 'PG16 required')


def check_contract(raw, p):
    v = c.parse(raw, maximum=16*1024*1024)
    c.closed(v, {'schema_version', 'profile_sha256', 'query_inventory_sha256', 'binding', 'source_inventory', 'checkpoints'})
    c.integer(v['schema_version'], 1, 1)
    h.require(v['profile_sha256'] == sha256(p).hexdigest())
    h.require(v['query_inventory_sha256'] == digest({k:{'sql':q.sql,'fields':list(q.fields),'maximum':q.maximum} for k,q in QUERIES.items()}), 'Query inventory divergence')
    binding = v['binding']
    check_collector_binding(binding)
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
                 contract_json=None, source_root=None, independent_baseline=None,
                 detailed_snapshot=None, detailed_session=None, prerequisite_contracts=None):
        # No calls on the connection, filesystem, verifier or database here.
        self._connection = connection
        self._transaction = transaction
        self._verifier = profile_verifier
        self._contract_json = contract_json
        self._root = source_root
        self._baseline = independent_baseline
        self._detailed_snapshot = detailed_snapshot
        self._detailed_session = detailed_session
        self._prerequisite_contracts = prerequisite_contracts
        self._cursor = 0
        self._failed = False

    def assert_connection(self, connection):
        h.require(not self._failed, 'Inspection port failed; no automatic retry')
        h.require(connection is self._connection and connection is not None, 'Connection changed')
        h.require(connection.closed is False and connection.dialect.name == 'postgresql', 'Connection unavailable')
        try:support.check_client_logging(connection)
        except support.InspectionInputError as exc:raise h.PrerequisiteRefused(exc.code) from None
        h.require(connection.in_transaction() is True and connection.get_transaction() is self._transaction
                  and self._transaction is not None and self._transaction.is_active is True, 'Transaction changed')

    def verify_approved_profile(self, profile_json):
        self.assert_connection(self._connection)
        if self._detailed_snapshot is not None:
            raw=self._prerequisite_contract()
            return _detailed_setup(self,profile_json,self._detailed_snapshot,phase='APP-ENTRY',
                session=self._detailed_session,prerequisite=self._cursor,contract_raw=raw)[-1]
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
                try:collected.append(support.row_mapping(row))
                except support.InspectionInputError as exc:raise h.PrerequisiteRefused(exc.code) from None
                if len(collected) > (QUERIES[name].maximum if sql is None else 2):
                    raise h.PrerequisiteRefused('Oversized query: '+name)
            return rows(name,collected) if sql is None else collected
        finally:
            result.close()

    def observe_detailed(self, profile_json, snapshot, *, phase, session=None):
        try:return _observe_detailed(self,profile_json,snapshot,phase=phase,session=session)
        except BaseException:
            self._failed=True
            raise

    def _prerequisite_contract(self):
        h.require(type(self._prerequisite_contracts) is tuple and len(self._prerequisite_contracts)==5
                  and all(type(x) is bytes for x in self._prerequisite_contracts),'Five fixed detailed prerequisite contracts required')
        h.require(self._cursor<5,'Checkpoint sequence exhausted')
        return self._prerequisite_contracts[self._cursor]

    def observe(self, profile_json, requested):
        try:
            if self._detailed_snapshot is not None:
                expected=('environment','inventory','btree_gist','btree_gist','audit')
                raw=self._prerequisite_contract()
                h.require(requested==expected[self._cursor],'Unexpected/repeated checkpoint')
                result=_observe_detailed(self,profile_json,self._detailed_snapshot,phase='APP-ENTRY',
                    session=self._detailed_session,prerequisite=self._cursor,contract_raw=raw)
                h.validate_observation(h.decode_profile(profile_json),result,requested)
                self._cursor+=1
                return result
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
        settings = support.settings_inventory(observations['settings'])
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


@dataclass(frozen=True)
class DetailedSQLBatch:
    historical: dict
    supplemental: dict
    ledger_rows: dict
    collector_id: str
    binding_json: bytes
    # Observations only; no profile approval or operational capability.


def collect_detailed_sql(connection, transaction, *, collector_id, role_names, system_routines, language_names, query_progress=None, expected_binding=None, raw_capture=None, approved_helpers=()):
    """Explicit borrowed connection/transaction; no opening, commit or retry.

    Caller owns rollback/close. Every result is drained and closed. This low-level
    read port does not authenticate an approval or authorize migration dispatch.
    """
    from .dev09b_detailed_queries import DETAIL_QUERIES
    from .dev09b_catalog_adapter import needed_references,supplemental_rows
    c.identifier(collector_id)
    def bound():
        h.require(connection is not None and connection.closed is False and connection.dialect.name=='postgresql','Explicit PG connection required')
        support.check_client_logging(connection)
        h.require(connection.in_transaction() is True and connection.get_transaction() is transaction
                  and transaction.is_active is True,'Detailed collector transaction changed')
    def collect(query,parameters=None,*,label):
        result=None
        try:
            bound();result=connection.execute(text(query.sql),parameters or {})
            values=[]
            for item in result.mappings():
                values.append(support.row_mapping(item))
                h.require(len(values)<=query.maximum,'Detailed result bound exceeded')
            if raw_capture is not None:raw_capture[label]=values
            if query_progress is not None:query_progress(label,dict(status='RETURNED',count=len(values)))
            return values
        except BaseException as exc:
            if query_progress is not None:
                diagnostic=dict(status='REFUSED',exception_class=type(exc).__name__)
                sqlstate=getattr(getattr(exc,'orig',None),'sqlstate',None)
                import re
                if type(sqlstate) is str and re.fullmatch('[0-9A-Z]{5}',sqlstate):diagnostic['sqlstate']=sqlstate
                query_progress(label,diagnostic)
            raise
        finally:
            if result is not None:result.close()
    for selection in (role_names,system_routines,language_names):
        h.require(type(selection) is list and len(selection)==len(set(selection)),'Unique explicit selections required')
        h.require(all(type(x) is str and bool(x) for x in selection),'Selection type')
    first=rows('identity',collect(QUERIES['identity'],label='identity_before'))
    h.require(len(first)==1,'Exactly one detailed collector identity')
    check_collector_binding(first[0])
    if expected_binding is not None:
        h.require(type(expected_binding) is dict and bool(expected_binding)
                  and set(expected_binding)<=set(first[0]),'Detailed expected identity fields')
        h.require(c.canonical({key:first[0][key] for key in expected_binding})==c.canonical(expected_binding),
                  'Detailed identity divergence before collection')
    historical={'identity':first}
    for name,query in QUERIES.items():
        if name!='identity':historical[name]=collect(query,label=name)
    # Do not promote hidden NULL settings to values. Conversion below will
    # refuse; raw collection can still report complete query coverage separately.
    parameters=dict(role_names=role_names,system_routines=system_routines,language_names=language_names)
    # Validate property shapes before resolving their referenced OIDs.
    for name in ('extension_properties','operator_members','type_details'):
        try:historical[name]=rows(name,historical[name])
        except BaseException as exc:
            if query_progress is not None:query_progress('process.'+name,dict(status='REFUSED',exception_class=type(exc).__name__))
            raise
    references=needed_references(historical)
    for catalog in ('pg_namespace','pg_type','pg_opfamily','pg_operator','pg_roles','pg_class','pg_am','pg_collation'):
        parameters['reference_'+catalog]=[oid for family,oid in references if family==catalog]
    supplemental={name:supplemental_rows(name,collect(query,parameters,label='detail.'+name)) for name,query in DETAIL_QUERIES.items() if name!='helper_preload_settings'}
    h.require(type(approved_helpers) in {tuple,list} and len(approved_helpers)<=1,'Fixed helper scope')
    supplemental['helper_preload_settings']=[]
    if approved_helpers:
        from scripts.dedicated.dev09b import own_settings
        own_settings.validate(approved_helpers[0])
        own_settings.verify_observed(historical,supplemental)
        if first[0]['current_user']==own_settings.PROBE:
            query=DETAIL_QUERIES['helper_preload_settings']
            supplemental['helper_preload_settings']=supplemental_rows('helper_preload_settings',collect(query,label='detail.helper_preload_settings'))
            h.require(len(supplemental['helper_preload_settings'])==2 and all(r['backend_pid']==first[0]['pid'] for r in supplemental['helper_preload_settings']),'Helper backend binding')
    relation_map={(r['schema'],r['name']):r for r in historical['relations']}
    h.require(len(relation_map)==len(historical['relations']),'Duplicate relation identity')
    ledgers={}
    for chain,sql in LEDGER_SQL.items():
        table='alembic_version' if chain=='application' else 'alembic_security_version'
        if ('public',table) not in relation_map:ledgers[chain]=None
        else:
            h.require(relation_map[('public',table)]['kind']=='r','Ledger is not ordinary table')
            from .dev09b_inspection_queries import Query
            ledgers[chain]=collect(Query(sql,('version_num',),2),label='ledger.'+chain)
    last=rows('identity',collect(QUERIES['identity'],label='identity_after'))
    h.require(c.canonical(first)==c.canonical(last),'Detailed collector identity/session/transaction changed')
    bound()
    return DetailedSQLBatch(historical,supplemental,ledgers,collector_id,c.canonical(first[0]))


def _detailed_setup(self,profile_json,snapshot,*,phase,session=None,prerequisite=None,contract_raw=None):
    """Trusted versioned contract; raw SQL never authorizes a profile by itself."""
    from .dev09b_catalog_adapter import convert_results
    from .dev09b_detailed_queries import DETAIL_QUERIES
    from scripts.dedicated.dev09b import detailed_catalog as detail,layers
    self.assert_connection(self._connection)
    c.validate_layers(snapshot);detail.validate_profile_binding(snapshot,profile_json)
    raw=self._contract_json if contract_raw is None else contract_raw
    if raw is None or self._verifier is None:raise h.MissingParameter('dev09b.detailed_trusted_inspection_contract')
    contract=c.parse(raw,maximum=16*1024*1024,maximum_depth=32)
    c.closed(contract,{'schema_version','profile_sha256','snapshot_sha256','query_inventory_sha256','binding','collector_id','context','selections','subject_session','conversion_source'}|({'prerequisite'} if prerequisite is not None else set()))
    c.integer(contract['schema_version'],3 if prerequisite is not None else 2,3 if prerequisite is not None else 2)
    if prerequisite is not None:
        c.integer(prerequisite,0,4);h.require(type(contract['prerequisite']) is int and contract['prerequisite']==prerequisite,'Detailed checkpoint binding')
    check_collector_binding(contract['binding'])
    h.require(contract['profile_sha256']==sha256(profile_json).hexdigest(),'Detailed profile bytes changed')
    h.require(contract['snapshot_sha256']==sha256(snapshot.physical).hexdigest(),'Detailed snapshot changed')
    query_inventory={**QUERIES,**{'detail.'+k:v for k,v in DETAIL_QUERIES.items()}}
    h.require(contract['query_inventory_sha256']==sha256(detail.encode({k:{'sql':q.sql,'fields':list(q.fields),'maximum':q.maximum} for k,q in query_inventory.items()})).hexdigest(),'Detailed query inventory changed')
    approval=self._verifier.verify(profile_json,raw)
    h.require(type(approval) is InspectionApproval,'Trusted detailed approval required')
    att=approval.attestation;p=h.decode_profile(profile_json)
    h.require(type(att) is h.ProfileAttestation and att.operationally_authenticated is True and att.classification=='OPERATIONAL'
              and att.profile_sha256==contract['profile_sha256'] and att.target_sha256==p['target_sha256'] and att.bundle_sha256==p['bundle_sha256'],'Detailed profile authentication')
    h.require(approval.contract_sha256==sha256(raw).hexdigest() and approval.binding_sha256==digest(contract['binding'])
              and type(approval.decision_reference) is str and bool(approval.decision_reference),'Detailed approval binding')
    from dataclasses import asdict
    subject=None if session is None else asdict(session)
    h.require(detail.encode(contract['subject_session'])==detail.encode(subject),'Detailed subject session changed')
    target=layers.read_snapshot(snapshot)[1]
    from scripts.dedicated.dev09b import own_settings
    parameters=layers.read_snapshot(snapshot)[5]['parameters']
    declared=contract['context'].get('approved_helpers',[])
    installed=[o for o in parameters['system_objects'] if o['family']=='routine' and o['identity']==own_settings.IDENTITY]
    h.require(type(declared) is list and len(declared)==len(installed),'Detailed fixed helper declaration coverage')
    if declared:own_settings.validate(declared[0])
    h.require(contract['binding']['database']==target['database_name'] and contract['binding']['system_identifier']==target['system_identifier'],'Detailed target identity changed')
    collector_role=target['migrator_role'] if phase in {'APP-ENTRY','APP-F066-PRECOMMIT'} else target['inspector_role']
    h.require(contract['binding']['current_user']==collector_role and contract['binding']['session_user']==collector_role,'Detailed collector role changed')
    if session is not None and phase in {'APP-ENTRY','APP-F066-PRECOMMIT'}:
        h.require(contract['binding']['pid']==session.backend_pid,'Detailed backend PID changed')
    # Numeric transaction IDs are not inferred from virtualxid/timestamp strings.
    # The explicit trusted verifier must attest that cross-representation binding.
    if self._root is None:raise h.MissingParameter('dev09b.source_root')
    root=Path(self._root)
    for source in layers.read_snapshot(snapshot)[6]['source_inventory']:
        file=root/source['path']
        h.require(not any(x.is_symlink() for x in (file,*file.parents)),'Detailed symlink source')
        h.require(file.is_file() and sha256(file.read_bytes()).hexdigest()==source['sha256'],'Detailed source divergence')
    ref=contract['conversion_source'];c.closed(ref,{'path','sha256'})
    h.require(ref in layers.read_snapshot(snapshot)[6]['source_inventory'],'Conversion source not signed')
    h.require(sha256(detail.encode(contract['context'])).hexdigest()==ref['sha256'],'Conversion source bytes changed')
    # Every source-side conversion declaration must be authenticated by this
    # explicit verifier, including deparse/fixed properties; no synthetic default.
    c.closed(contract['selections'],{'role_names','system_routines','language_names'})
    return contract,target,p,subject,att


def _observe_detailed(self,profile_json,snapshot,*,phase,session=None,prerequisite=None,contract_raw=None):
    from .dev09b_catalog_adapter import convert_results
    from scripts.dedicated.dev09b import detailed_catalog as detail,layers,physical
    contract,target,p,subject,att=_detailed_setup(self,profile_json,snapshot,phase=phase,session=session,
        prerequisite=prerequisite,contract_raw=contract_raw)
    batch=collect_detailed_sql(self._connection,self._transaction,collector_id=contract['collector_id'],expected_binding=contract['binding'],approved_helpers=contract['context'].get('approved_helpers',[]),**contract['selections'])
    h.require(batch.binding_json==c.canonical(contract['binding']),'Detailed collector binding divergence')
    converted=convert_results(batch.historical,batch.supplemental,contract['context'],phase=phase,
                              collector_id=batch.collector_id,session=subject,ledger_rows=batch.ledger_rows)
    observation=detail.parse(converted.rows_json)
    if prerequisite is None:
        detail.compare_observations(snapshot,phase,observation,session=session)
        return converted
    # Validate the same signed subject binding before comparing a source-derived
    # prefix. No observed row supplies the prefix or changes its expectation.
    parts=layers.read_snapshot(snapshot);payload,_,_,_,semantic,phys,provenance=parts
    detail.validate_subject(snapshot,'APP-ENTRY',observation,session)
    expected=physical.compile_profile('APP-ENTRY',target,phys['parameters'],
        detail.migration_inputs(phys,semantic,provenance),prerequisite=prerequisite)
    physical.compare_profile(expected,detail.normalize_observations(observation))
    raw=batch.historical;identity=c.parse(batch.binding_json);schema_rows={r['name']:r for r in raw['schemas']}
    extension=[r for r in raw['extension'] if r['name']=='btree_gist'];h.require(len(extension)==1)
    extension={k:v for k,v in extension[0].items() if k!='name'}
    extension['members_sha256']=digest(rows('extension_members',[r for r in raw['extension_members'] if r['extension']=='btree_gist']))
    extension['acl_sha256']=digest(rows('extension_acl',[r for r in raw['extension_acl'] if r['extension']=='btree_gist']))
    h.require(extension==p['btree_gist'],'Detailed legacy digest binding')
    return {**{k:identity[k] for k in ('database','system_identifier','current_user','session_user')},
        **raw['privileges'][0],'extension_install_power':False,'memberships':[],
        'schemas':{n:{'owner':schema_rows[n]['owner'],'owner_login':schema_rows[n]['owner_login']} for n in p['schema_owners']},
        'extension':extension,'residual_objects':[],
        'schema_create':sorted(r['name'] for r in raw['schemas'] if r['can_create']),
        'schema_usage':sorted(r['name'] for r in raw['schemas'] if r['name'] in {'inventory','audit','security','public'} and r['can_use']),
        'prior_application_confirmed':False,'source_inventory_sha256':p['source_inventory_sha256']}
