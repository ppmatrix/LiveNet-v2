"""Authenticated discovery API. Disabled without administrator scope."""
from flask import Blueprint,current_app,jsonify,request
from werkzeug.exceptions import HTTPException
from app.inventory.routes import _caller,_read_scope,InventoryHTTPError
from app.inventory.schemas import InventoryValidationError,validate_resource_id,validate_query
from app.security.errors import SecurityError
from .service import Repository,Problem
from .worker import Worker

bp=Blueprint('discovery',__name__)


@bp.errorhandler(Exception)
def failure(error):
    if isinstance(error,Problem):status,code=error.status,error.code
    elif isinstance(error,InventoryHTTPError):status,code=error.status,error.code
    elif isinstance(error,SecurityError):status,code=error.code,error.error_code
    elif isinstance(error,(InventoryValidationError,ValueError)):status,code=400,'invalid_request'
    elif isinstance(error,HTTPException):status,code=error.code,'invalid_request'
    else:status,code=503,'discovery_unavailable'
    return jsonify(error=dict(code=code,message='Não foi possível concluir o pedido de descoberta.')),status


def access(write=False,enabled=True):
    dependencies,identity=_caller();scope=_read_scope(dependencies,identity)
    if write and dependencies.access.can_create(identity,{}) is not True:raise Problem(403,'forbidden')
    extension=current_app.extensions['discovery']
    if enabled and extension['policy'] is None:raise Problem(503,'discovery_not_configured')
    return extension,dependencies,identity,scope


@bp.get('/config')
def configuration():
    extension,*_=access(enabled=False);policy=extension['policy']
    return jsonify(enabled=policy is not None,policy=policy.snapshot() if policy else None)


@bp.get('/jobs')
def jobs():
    extension,*_=access()
    return jsonify(items=extension['repository'].jobs())


@bp.post('/jobs')
def start():
    extension,_,identity,_=access(write=True)
    request.max_content_length=16384
    payload=request.get_json()
    if not isinstance(payload,dict) or set(payload)!={'target'}:raise Problem(400,'invalid_request')
    return jsonify(extension['repository'].enqueue(extension['policy'],payload['target'],identity)),202


@bp.get('/jobs/<identifier>')
def job(identifier):
    extension,*_=access(enabled=False)
    return jsonify(extension['repository'].job(validate_resource_id(identifier)))


@bp.post('/jobs/<identifier>/cancel')
def cancel(identifier):
    extension,_,identity,_=access(write=True)
    return jsonify(extension['repository'].cancel(validate_resource_id(identifier),identity))


@bp.get('/candidates/<identifier>')
def candidate(identifier):
    extension,_,_,scope=access()
    return jsonify(extension['repository'].candidate(validate_resource_id(identifier),scope))


@bp.get('/resources/<identifier>/history')
def resource_history(identifier):
    # Reading existing history does not require enabling new network detection.
    extension,_,_,scope=access(enabled=False)
    if set(request.args)-{'page','per_page'}:raise Problem(400,'invalid_request')
    query=validate_query(request.args)
    return jsonify(extension['repository'].resource_history(validate_resource_id(identifier),scope,
        page=query['page'],per_page=query['per_page']))


@bp.post('/candidates/<identifier>/decision')
def decision(identifier):
    extension,dependencies,identity,scope=access(write=True)
    request.max_content_length=16384
    return jsonify(extension['repository'].decide(validate_resource_id(identifier),request.get_json(),identity,scope,dependencies.access.can_create))


def init_discovery(app,policy=None,leader_factory=None,network_probe=None):
    repository=Repository(app.extensions['inventory'].open_session)
    app.extensions['discovery']=dict(policy=policy,repository=repository,worker=None)
    app.register_blueprint(bp,url_prefix='/api/v1/discovery')
    if policy is not None and leader_factory is not None:
        worker=Worker(repository,policy,leader_factory,**({'network_probe':network_probe} if network_probe else {}))
        app.extensions['discovery']['worker']=worker
        worker.start()
