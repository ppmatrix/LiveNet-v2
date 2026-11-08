"""Portable standard factory: real security + Inventory share configured sessions.

No account/schema creation at startup. The historical dedicated factory remains
unchanged. HTTPS origin is environment data, never a lab hostname in this core.
"""
from pathlib import Path

from flask import request, send_from_directory, abort
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import create_app
from app.dedicated import _secret
from app.security.policy import SecurityPolicy
from app.trusted_proxy import TrustedProxy
from installation import require
from installation.config import Settings


def runtime_connection(settings):
    conn=settings.connect('runtime')
    try:
        row=conn.execute(text("""SELECT current_database() AS database,session_user::text AS principal,current_user::text AS effective_principal,
          r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls AS elevated,
          EXISTS(SELECT FROM pg_catalog.pg_auth_members WHERE member=r.oid) AS memberships,
          EXISTS(SELECT FROM pg_catalog.pg_namespace n WHERE n.nspname IN ('inventory','audit','security','public')
            AND (n.nspowner=r.oid OR pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'))) AS ddl,
          EXISTS(SELECT FROM pg_catalog.pg_shdepend WHERE refclassid='pg_catalog.pg_authid'::pg_catalog.regclass AND refobjid=r.oid AND deptype='o') AS ownership,
          d.datdba=r.oid OR pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE') OR pg_catalog.has_database_privilege(r.oid,d.oid,'TEMP') AS database_power
          FROM pg_catalog.pg_roles r JOIN pg_catalog.pg_database d ON d.datname=current_database() WHERE r.rolname=current_user""")).mappings().one()
        require(row['database']==settings.values['database']['name'] and
            row['principal']==row['effective_principal']==settings.values['roles']['runtime'],'WRONG_RUNTIME_DESTINATION')
        require(all(row[key] is False for key in ('elevated','memberships','ddl','ownership','database_power')),'RUNTIME_EXCESS_PRIVILEGES')
        conn.rollback()
        return conn
    except BaseException:
        conn.close();raise


def create_standard_app(config_file):
    settings=Settings.load(config_file)
    class RuntimeSession(Session):
        def __init__(self):
            self.owned_connection=runtime_connection(settings)
            try:super().__init__(bind=self.owned_connection,expire_on_commit=False,autoflush=False)
            except BaseException:self.owned_connection.close();raise
        def close(self):
            try:super().close()
            finally:self.owned_connection.close()
    app=create_app('production',security_config=dict(SECURITY_ENABLED=True,
        SECURITY_HTTPS_ORIGIN=settings.values['https']['origin'],
        SECURITY_CSRF_KEY=_secret(settings.values['csrf_key_file'])),
        inventory_session_factory=RuntimeSession,security_session_factory=RuntimeSession)
    SecurityPolicy.load(app.config)
    app.wsgi_app=TrustedProxy(app.wsgi_app,enabled=False,peers=(),authority='')
    dist=Path(settings.values['frontend_dist'])

    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path=''):
        if path=='api' or path.startswith('api/'):abort(404)
        if path in {'','login','login/','inventory','inventory/'} or path.startswith('inventory/'):
            response=send_from_directory(dist,'index.html')
            response.headers['Cache-Control']='no-store'
            return response
        if path.startswith('.') or any(part.startswith('.') for part in Path(path).parts):abort(404)
        return send_from_directory(dist,path)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        return response
    return app
