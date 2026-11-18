"""INV-ID-01 routes on the existing authenticated Inventory blueprint."""
from flask import jsonify, request, url_for
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.sql.elements import ColumnElement
from werkzeug.datastructures import MultiDict

from . import identifiers as service
from .models import ResourceIdentifier
from .schemas import validate_resource_id, validate_query


def register(bp):
    from .routes import _caller, _read_scope, InventoryHTTPError

    @bp.errorhandler(service.IdentifierError)
    def identifier_error(error):
        value = dict(error=dict(code=error.code, message='Não foi possível concluir a operação de identificadores.'))
        if error.details is not None:value['details'] = error.details
        return jsonify(value), error.status

    @bp.errorhandler(DBAPIError)
    def database_error(error):
        from .routes import handle_unexpected_error
        if request.endpoint not in {'inventory.list_identifiers','inventory.get_identifier','inventory.add_identifier','inventory.close_identifier'}:
            return handle_unexpected_error(error)
        code = getattr(error.orig, 'sqlstate', None)
        if code in ('55P03','57014','40P01'):
            return identifier_error(service.IdentifierError(503,'operation_busy'))
        if code == '23505' and getattr(getattr(error.orig,'diag',None),'constraint_name',None) == 'uq_identifiers_manual_ipv4_open':
            return identifier_error(service.IdentifierError(409,'identifier_conflict'))
        # Preserve the existing sanitized handling for other Inventory failures.
        return handle_unexpected_error(error)

    def dependencies(write=False):
        deps, identity = _caller(); read_scope = _read_scope(deps, identity)
        scope = deps.access.update_scope(identity) if write else read_scope
        if scope is None:raise InventoryHTTPError(403,'forbidden','Operação não permitida.')
        if not isinstance(scope,ColumnElement):raise RuntimeError('Invalid scope integration')
        return deps, identity, scope, read_scope

    def body(close=False):
        request.max_content_length = 16384
        if not request.is_json:raise InventoryHTTPError(415,'unsupported_media_type','É necessário application/json.')
        return service.payload(request.get_json(),close=close)

    def readonly(session):
        if session.get_bind().dialect.name == 'postgresql':
            session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))

    @bp.get('/resources/<resource_id>/identifiers')
    def list_identifiers(resource_id):
        deps, _, scope, _ = dependencies(); rid = validate_resource_id(resource_id)
        args = request.args
        if set(args)-{'state','page','per_page','namespace'} or any(len(args.getlist(k))!=1 for k in args):
            raise service.IdentifierError(400,'invalid_request')
        state = args.get('state','active')
        if state not in ('active','closed','all'):raise service.IdentifierError(400,'invalid_request')
        paging = validate_query(MultiDict({k:args[k] for k in ('page','per_page') if k in args}))
        ns = service.namespace(args['namespace']) if 'namespace' in args else None
        with deps.open_session() as session:
            with session.begin():
                readonly(session)
                result = service.list_rows(session,rid,scope,state=state,page=paging['page'],per_page=paging['per_page'],ns=ns)
        return jsonify(result)

    @bp.get('/resources/<resource_id>/identifiers/<identifier_id>')
    def get_identifier(resource_id,identifier_id):
        deps, _, scope, _ = dependencies(); rid = validate_resource_id(resource_id); iid = validate_resource_id(identifier_id)
        with deps.open_session() as session:
            with session.begin():
                readonly(session); parent = service.resource(session,rid,scope)
                row = session.scalar(select(ResourceIdentifier).where(ResourceIdentifier.id==iid,
                    ResourceIdentifier.resource_id==rid,ResourceIdentifier.identifier_type.in_(('ipv4','IPv4'))))
                if row is None:raise service.IdentifierError(404,'not_found')
                result = service.result(row,parent,False)
        return jsonify(result)

    @bp.post('/resources/<resource_id>/identifiers')
    def add_identifier(resource_id):
        deps, identity, scope, read_scope = dependencies(True); rid = validate_resource_id(resource_id); data = body()
        with deps.open_session() as session:
            with session.begin():result = service.add(session,rid,data,identity,scope,read_scope)
        response = jsonify(result); response.status_code = 201 if result['changed'] else 200
        response.headers['Location'] = url_for('inventory.get_identifier',resource_id=rid,identifier_id=result['identifier']['id'])
        return response

    @bp.post('/resources/<resource_id>/identifiers/<identifier_id>/close')
    def close_identifier(resource_id,identifier_id):
        deps, identity, scope, _ = dependencies(True)
        rid = validate_resource_id(resource_id); iid = validate_resource_id(identifier_id); data = body(True)
        with deps.open_session() as session:
            with session.begin():result = service.close(session,rid,iid,data,identity,scope)
        return jsonify(result)
