"""FIX01 offline adversarial checks. No Docker, build, DB or service access."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/dedicated'))
import dev09a2_packaging as old
import dev09fix01_packaging as fix

IMAGE = 'example.invalid/livenet/executor@sha256:' + 'a' * 64  # synthetic syntax, no image claim
PROJECT = 'livenet-dev09b-4c96595539'


def document(**changes):
    values = dict(project=PROJECT, image=IMAGE, uid='10001', gid='10001')
    values.update(changes)
    return fix.compose_document(**values)


@pytest.mark.parametrize('field', ['uid', 'gid'])
@pytest.mark.parametrize('value', ['', '0', '00', '01', '-1', '+1', '1.0', 'root', '1000 ',
    ' 1000', '${UID}', '$UID', '$$UID', '1:2', '1\n', '4294967295', None, True, 1000])
def test_invalid_ids(field, value):
    with pytest.raises(fix.Refused):
        document(**{field: value})


@pytest.mark.parametrize('uid,gid', [('1','1'),('10001','10001'),('65534','65534'),('4294967294','4294967294')])
def test_explicit_positive_ids(uid, gid):
    assert fix.verify_compose(document(uid=uid, gid=gid))['services']['executor']['user'] == uid+':'+gid


@pytest.mark.parametrize('image', ['', 'executor', 'executor:latest', 'registry.local/repo:v1',
    'sha256:'+'a'*64, 'repo@sha256:short', 'Repo@sha256:'+'a'*64,
    'repo@sha256:'+'A'*64, 'repo@sha256:'+'g'*64, 'repo@sha256:'+'0'*63,
    'repo@sha256:'+'a'*64+' ', 'https://repo@sha256:'+'a'*64,
    '${IMAGE}', '$IMAGE', '$$IMAGE', 'repo:latest@sha256:'+'a'*64,
    'reg:0/repo@sha256:'+'a'*64, 'reg:65536/repo@sha256:'+'a'*64, None, True])
def test_image_must_be_named_immutable_and_literal(image):
    with pytest.raises(fix.Refused):
        document(image=image)


@pytest.mark.parametrize('image', [IMAGE, 'repo@sha256:'+'b'*64,
    'registry.local:5000/namespace/executor@sha256:'+'c'*64])
def test_immutable_image_reference(image):
    assert fix.verify_compose(document(image=image))['services']['executor']['image'] == image


@pytest.mark.parametrize('project', ['', 'livenet', 'livenet-dev09a1-0123456789', '${PROJECT}', None])
def test_no_implicit_or_interpolated_project(project):
    with pytest.raises(fix.Refused):
        document(project=project)


def test_template_has_no_direct_runnable_image_or_build():
    template=fix.compose_template()
    service=template['services']['executor']
    assert service['image'] is None and service['user'] is None
    assert 'build' not in service and '${' not in json.dumps(template)
    with pytest.raises(fix.Refused):
        fix.verify_compose(template)
    valid=fix.verify_compose(document())['services']['executor']
    assert valid['entrypoint'] == ['/bin/sh','-c','exit 78'] and valid['network_mode']=='none'
    assert valid['read_only'] is True and valid['privileged'] is False
    assert valid['cap_drop']==['ALL'] and valid['security_opt']==['no-new-privileges:true']
    assert not {'ports','volumes','secrets','networks','build','environment'} & set(valid)


@pytest.mark.parametrize('field,value', [('user','0:0'),('image','repo:latest'),
    ('privileged',True),('network_mode','host'),('ports',['5432:5432']),
    ('volumes',['/:/host']),('secrets',['operational']),('entrypoint',['python']),
    ('build','.'),('read_only',False),('privileged',0),('read_only',1),('pids_limit',64.0),
    ('cap_add',['SYS_ADMIN']),('environment',{'UID':'0'})])
def test_tampered_descriptor_refused(field, value):
    doc=document();doc['services']['executor'][field]=value
    with pytest.raises(fix.Refused):
        fix.verify_compose(doc)


def test_added_services_and_top_level_overrides_refused():
    for mutate in (lambda d:d['services'].update(db={'image':'postgres:16'}),
                   lambda d:d.update(volumes={'operational':{}}),lambda d:d.update(extends='other')):
        doc=document();mutate(doc)
        with pytest.raises(fix.Refused):
            fix.verify_compose(doc)


def test_cli_rejects_invalid_parameters_without_io(capsys):
    args=['compose','--project',PROJECT,'--image',IMAGE,'--uid','10001','--gid','10001']
    assert fix.main(args)==0
    assert json.loads(capsys.readouterr().out)['services']['executor']['image']==IMAGE
    args[-1]='0'
    assert fix.main(args)==2
    assert json.loads(capsys.readouterr().out)['status']=='REFUSED'


VIRTUAL = ('backend/tests/test_security_migration.py','backend/app/not-reviewed.py',
    'backend/.env','scripts/postgres/not-reviewed.key','backend/app/.hidden',
    'backend/app/new-secrets-with-unusual-name.data','backend/app/nested/new.py',
    'backend/security_migrations/new.py','scripts/postgres/g4/unexpected.py')


def test_real_ancestor_reinclusion_is_detected_and_leaf_rules_refuse_it():
    historical=(ROOT/'docs/operations/proposals/dev09a2/scripts__postgres__auth03_executor.Dockerfile.dockerignore.proposed').read_text()
    assert set(VIRTUAL) <= old.selected_files(historical,VIRTUAL)
    corrected=fix.proposed_ignore()
    assert old.selected_files(corrected,VIRTUAL)==set()
    assert not any(line.endswith('/') for line in corrected.splitlines())
    expected=set(fix.context_inventory())
    assert old.selected_files(corrected,(*expected,*VIRTUAL))==expected


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    root=tmp_path/'repo';root.mkdir(mode=0o700)
    needed=set(fix.frozen_inventory())|{fix.CANDIDATE,fix.AGGREGATE,fix.APP02_COPY,fix.DOCKERFILE,fix.IGNORE}
    for name in needed:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    monkeypatch.setattr(fix,'ROOT',root)
    return root


def test_physical_context_independent_of_matcher(source_copy, tmp_path, monkeypatch):
    for name in VIRTUAL:
        p=source_copy/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('BENIGN SYNTHETIC SENTINEL')
    monkeypatch.setattr(old,'selected_files',lambda *a:pytest.fail('physical verification must not trust matcher'))
    actual=fix.materialize_context(tmp_path/'context')
    assert len(actual)==68 and not set(VIRTUAL)&set(actual)
    assert actual[fix.DOCKERFILE]==fix.APP02_FILE_SHA
    assert actual[fix.IGNORE]==sha256(fix.proposed_ignore().encode()).hexdigest()
    assert fix.verify_context(tmp_path/'context')==actual


def test_unlisted_symlink_is_not_followed_or_copied(source_copy, tmp_path):
    outside=tmp_path/'outside';outside.write_text('BENIGN SYNTHETIC SENTINEL')
    link=source_copy/'backend/app/unlisted-link';link.symlink_to(outside)
    actual=fix.materialize_context(tmp_path/'context')
    assert 'backend/app/unlisted-link' not in actual and outside.read_text()=='BENIGN SYNTHETIC SENTINEL'


def test_copy_import_and_lock_closure(source_copy, tmp_path):
    destination=tmp_path/'context';fix.materialize_context(destination)
    snapshot={name:(destination/name).read_bytes() for name in fix.context_inventory()}
    proof=fix.verify_dependencies(snapshot)
    assert proof['copied_sources']==66 and proof['locked_distributions']==14
    assert proof['external_import_roots']==['alembic','flask','itsdangerous','sqlalchemy','werkzeug']
    assert proof['dynamic_imports_or_built_image']=='NOT_VERIFIED'
    missing=dict(snapshot);del missing['backend/alembic-security.ini']
    with pytest.raises(fix.Refused,match='COPY_DEPENDENCY_MISSING'):fix.verify_dependencies(missing)
    missing=dict(snapshot)
    missing['scripts/postgres/dev09a2-executor.lock']=b'\n'
    with pytest.raises(fix.Refused,match='LOCK_CLOSURE_DIVERGENCE'):fix.verify_dependencies(missing)
    unknown=dict(snapshot);unknown['backend/app/config.py']+=b'\nimport dependency_not_in_lock\n'
    with pytest.raises(fix.Refused,match='PYTHON_DEPENDENCY_MISSING'):fix.verify_dependencies(unknown)


@pytest.mark.parametrize('kind', ['leaf_symlink','parent_symlink','directory_instead_of_file','hardlink'])
def test_irregular_attested_path_refused_before_output(source_copy, tmp_path, kind):
    target=source_copy/'backend/app/config.py'
    if kind=='parent_symlink':
        directory=source_copy/'backend/app/health'
        directory.rename(directory.with_name('health-real'))
        directory.symlink_to('health-real',target_is_directory=True)
    else:
        contents=target.read_bytes();target.unlink()
        if kind=='leaf_symlink':
            outside=tmp_path/'outside';outside.write_bytes(contents);target.symlink_to(outside)
        elif kind=='directory_instead_of_file':target.mkdir()
        else:
            outside=tmp_path/'outside';outside.write_bytes(contents);os.link(outside,target)
    with pytest.raises(fix.Refused):fix.materialize_context(tmp_path/'context')
    assert not (tmp_path/'context').exists()


@pytest.mark.parametrize('kind', ['missing','modified','manifest','candidate','approved_app02'])
def test_unattested_or_missing_dependency_refused(source_copy, tmp_path, kind):
    target=source_copy/({'manifest':fix.MANIFEST,'candidate':fix.CANDIDATE,
                       'approved_app02':fix.APP02_COPY}.get(kind,'backend/app/config.py'))
    if kind=='missing':target.unlink()
    else:target.write_bytes(target.read_bytes()+b'\n# BENIGN DRIFT\n')
    with pytest.raises(fix.Refused):fix.materialize_context(tmp_path/'context')
    assert not (tmp_path/'context').exists()


@pytest.mark.parametrize('kind', ['extra','modified','symlink'])
def test_independent_output_check_catches_tampering(source_copy, tmp_path, kind):
    destination=tmp_path/'context';fix.materialize_context(destination)
    if kind=='extra':(destination/'backend/app/.unexpected').write_text('BENIGN')
    elif kind=='modified':
        p=destination/'backend/app/config.py';p.chmod(0o600);p.write_text('BENIGN')
    else:(destination/'link').symlink_to(tmp_path)
    with pytest.raises(fix.Refused):fix.verify_context(destination)


@pytest.mark.parametrize('path', ['', '.', '..', '../file','backend//file','/etc/passwd',
    'backend/./file','backend/.env','backend/../../file','backend/file\nother',None])
def test_unexpected_paths_refused(path):
    with pytest.raises(fix.Refused):fix.path_parts(path)


def test_existing_or_repository_destination_refused(source_copy, tmp_path):
    with pytest.raises(fix.Refused):fix.materialize_context(tmp_path)
    with pytest.raises(fix.Refused):fix.materialize_context(source_copy/'context')


def test_patch_files_have_one_protected_target_each():
    folder=ROOT/'docs/operations/proposals/dev09fix01'
    for name,path in [('APP-01','compose.auth03-executor.yaml'),('APP-03',fix.IGNORE)]:
        text=(folder/(name+'.NOT-APPROVED.patch')).read_text()
        assert text==fix.patch_for(name)
        assert text.count('--- a/')==1 and text.count('+++ b/')==1
        assert text.startswith('--- a/'+path+'\n+++ b/'+path+'\n')
        assert 'auth03_alembic_executor.py' not in '\n'.join(x for x in text.splitlines() if x.startswith(('---','+++')))
