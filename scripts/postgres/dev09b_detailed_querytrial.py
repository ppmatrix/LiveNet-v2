"""Candidate READ ONLY capture/conversion on the EXISTING prepared querytrial.

No Docker lifecycle, admin SQL, grants, migrations, authority or retry. Future
explicit CLI only. Inputs must be fixed before collection; NULL context is an
explicit incomplete source declaration, NEVER learned from captured observations.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from scripts.postgres import dev09b_querytrial_launcher as q
from migrations import dev09b_inspection as ins,dev09b_catalog_adapter as adapter
from migrations.dev09b_detailed_queries import DETAIL_QUERIES
from scripts.dedicated.dev09b import detailed_catalog as d,codec as c

SID='7705421224394444834'


def validate_inputs(raw):
    value=c.parse(raw,maximum=16*1024*1024,maximum_depth=32)
    c.closed(value,{'schema_version','status','collector_id','selections','context'}|({'approved_helpers'} if 'approved_helpers' in value else set())|({'comparison_profile'} if 'comparison_profile' in value else set()))
    c.integer(value['schema_version'],1,1)
    q.require(value['status']=='PROPOSED_READ_ONLY_INPUTS','INPUT_STATUS')
    c.identifier(value['collector_id']);c.closed(value['selections'],{'role_names','system_routines','language_names'})
    for names in value['selections'].values():
        q.require(type(names) is list and bool(names) and all(type(n) is str and n for n in names) and len(set(names))==len(names),'INPUT_SELECTION')
    if value['context'] is not None:
        c.closed(value['context'],{'metadata','fixed_properties','deparse','implicit_objects'}|({'approved_helpers'} if 'approved_helpers' in value['context'] else set()))
    if 'approved_helpers' in value:
        from scripts.dedicated.dev09b import own_settings
        c.require(type(value['approved_helpers']) is list and len(value['approved_helpers'])<=1)
        for helper in value['approved_helpers']:own_settings.validate(helper)
        if value['context'] is not None:c.require(c.canonical(value['approved_helpers'])==c.canonical(value['context'].get('approved_helpers',[])))
    if 'comparison_profile' in value:
        from scripts.dedicated.dev09b.fixed_catalog_context import querytrial_inputs
        fixed,_=querytrial_inputs(q.ROOT)
        c.require(c.canonical(value,maximum_depth=32)==c.canonical(fixed,maximum_depth=32))
    return value


def read_private_large(path):
    q.private_dir(path.parent)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as handle:
        info=os.fstat(handle.fileno())
        q.require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600
                  and info.st_nlink==1 and info.st_size<=16*1024*1024,'PRIVATE_INPUT_FILE')
        return handle.read(16*1024*1024+1)


def read_only_trial(connection,inputs,expected,*,raw_capture=None):
    """Owns rollback and close on EVERY path; never creates a connection."""
    report=dict(classification='UNAUTHENTICATED_READ_ONLY_CAPTURE',status='REFUSED',queries={},
                operational_authorization=False,rollback='NOT_ATTEMPTED',close='NOT_ATTEMPTED')
    batch=None;tx=None;phase='configuration'
    try:
        q.require(connection is not None and connection.closed is False and not connection.in_transaction(),'IDLE_EXPLICIT_CONNECTION_REQUIRED')
        ins.support.check_client_logging(connection)
        tx=connection.begin()
        from sqlalchemy import text
        for statement in ('SET TRANSACTION READ ONLY',"SET LOCAL statement_timeout='5s'","SET LOCAL lock_timeout='1s'","SET LOCAL idle_in_transaction_session_timeout='15s'"):
            result=connection.execute(text(statement));result.close()
        phase='collection'
        batch=ins.collect_detailed_sql(connection,tx,collector_id=inputs['collector_id'],
            query_progress=lambda name,value:report['queries'].__setitem__(name,value),expected_binding=expected,raw_capture=raw_capture,approved_helpers=inputs.get('approved_helpers',[]) if inputs['context'] is None else inputs['context'].get('approved_helpers',[]),**inputs['selections'])
        identity=c.parse(batch.binding_json)
        q.require(all(identity.get(k)==v for k,v in expected.items()),'READ_ONLY_TRIAL_TARGET_DIVERGENCE')
        report['identity_before_after']='MATCH'

        report['unavailable_settings']=[r['name'] for r in batch.historical['settings'] if r['setting'] is None]
        report['helper_observed_settings']=[r['name'] for r in batch.supplemental['helper_preload_settings']]
        phase='conversion'
        if inputs['context'] is None:raise adapter.MissingParameter('trial.fixed_conversion_context')
        converted=adapter.convert_results(batch.historical,batch.supplemental,inputs['context'],phase='DEV-BASE',
                                          collector_id=batch.collector_id,ledger_rows=batch.ledger_rows)
        report['conversion']='RETURNED'
        report['status']='READ_ONLY_COLLECTION_CONVERSION_RETURNED'
        if 'comparison_profile' in inputs:
            phase='technical_baseline_comparison'
            from scripts.dedicated.dev09b.fixed_catalog_context import compare_querytrial_baseline
            report['comparison']=compare_querytrial_baseline(q.ROOT,inputs,d.parse(converted.rows_json))
            report['status']='READ_ONLY_COLLECTION_BASELINE_EQUAL'
            report['operational_profile_validation']='NOT_PERFORMED'
            report['post_f066_validation']='NOT_PERFORMED'
            report['declared_not_observed']=['template provenance','Alembic/SQLAlchemy executor provenance','operational target/executor authentication']
        # No signed phase/profile decision or outcome confirmation is implied.
    except BaseException as exc:
        report['failure_phase']=phase;report['exception_class']=type(exc).__name__
        if isinstance(exc,(adapter.MissingParameter,ins.h.MissingParameter)):report['code']=str(exc)
        else:
            if isinstance(exc,ins.h.PrerequisiteRefused) and re.fullmatch('[A-Z][A-Z0-9_]*',str(exc)):report['code']=str(exc)
            sqlstate=getattr(getattr(exc,'orig',None),'sqlstate',None)
            if type(sqlstate) is str and re.fullmatch('[0-9A-Z]{5}',sqlstate):report['sqlstate']=sqlstate
    finally:
        if connection is not None:
            try:
                if tx is not None:tx.rollback()
                else:connection.rollback()
                report['rollback']='RETURNED'
            except BaseException:report['rollback']='FAILED';report['status']='REFUSED'
            try:connection.close();report['close']='RETURNED'
            except BaseException:report['close']='FAILED';report['status']='REFUSED'
    return report,batch


def run(input_name,report_name,confirm):
    q.require(confirm==SID,'PREPARED_QUERYTRIAL_SID_REQUIRED')
    for name in (input_name,report_name):q.require(type(name) is str and re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,100}',name),'PRIVATE_BASENAME')
    state=q.state_dir();raw=read_private_large(state/input_name);inputs=validate_inputs(raw)
    q.require(not (state/report_name).exists() and not (state/(report_name+'.capture.json')).exists(),'OUTPUT_ALREADY_EXISTS')
    record=q.checked_record(confirm)  # same image/container/volume; no creation or preparation
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    from sqlalchemy.pool import NullPool
    engine=create_engine(URL.create('postgresql+psycopg',username=q.PROBE,password=q.password(state/'probe_password'),
                         host=record['address'],port=5432,database=q.DATABASE),echo=False,hide_parameters=True,poolclass=NullPool,
                         connect_args={'connect_timeout':5,'sslmode':'disable','gssencmode':'disable'})
    try:
        partial={}
        report,batch=read_only_trial(engine.connect(),inputs,dict(database=q.DATABASE,system_identifier=confirm,
            current_user=q.PROBE,session_user=q.PROBE,address=record['address'],port=5432),raw_capture=partial)
        report['input_sha256']=sha256(raw).hexdigest()
        if batch is not None:
            capture=d.encode(dict(classification='LIVE_READ_ONLY_TRIAL_NOT_OPERATIONAL',collector_id=batch.collector_id,
                                  binding=c.parse(batch.binding_json),historical=batch.historical,supplemental=batch.supplemental,ledgers=batch.ledger_rows))
            q.write_new(state/(report_name+'.capture.json'),capture);report['capture_sha256']=sha256(capture).hexdigest()
        elif partial:
            capture=d.encode(dict(classification='INCOMPLETE_UNAUTHENTICATED_READ_ONLY_CAPTURE',queries=partial))
            q.write_new(state/(report_name+'.capture.json'),capture);report['partial_capture_sha256']=sha256(capture).hexdigest()
        q.write_new(state/report_name,d.encode(report)+b'\n')
        # Summary only; SQL rows, function bodies and credentials stay private.
        print(json.dumps(report,sort_keys=True))
        return 0 if report['status'].startswith('READ_ONLY_COLLECTION_') else 1
    finally:engine.dispose()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('validate-only','run'))
    parser.add_argument('--inputs',required=True,help='validate: local source declaration; run: private basename')
    parser.add_argument('--report',default='detailed-readonly-01.json')
    parser.add_argument('--confirm-system-identifier')
    args=parser.parse_args(argv)
    try:
        if args.action=='validate-only':
            inputs=validate_inputs(Path(args.inputs).read_bytes())
            print('STATIC_INPUTS_VALID; conversion_context='+('MISSING' if inputs['context'] is None else 'SUPPLIED_NOT_APPROVED'))
            return 0
        return run(args.inputs,args.report,args.confirm_system_identifier)
    except Exception as exc:
        print('DETAILED_READ_ONLY_REFUSED:'+type(exc).__name__)
        return 1


if __name__=='__main__':raise SystemExit(main())
