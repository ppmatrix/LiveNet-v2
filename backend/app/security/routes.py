"""Local login API. Remains unavailable until M1.2B supplies persistence/config."""

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import HTTPException

from app.security.csrf import issue_csrf, verify_csrf
from app.security.errors import SecurityError
from app.security.service import normalize_credentials


security_bp = Blueprint("security", __name__)


def _runtime():
    runtime = current_app.extensions["security"]
    policy = runtime.policy()
    policy.check_transport(request)
    return runtime, policy


def _set_cookie(response, name, value, max_age):
    response.set_cookie(name, value, max_age=max_age, secure=True, httponly=True,
                        samesite="Lax", path="/")  # No Domain: host-only.


def _clear_cookie(response, name):
    response.delete_cookie(name, secure=True, httponly=True, samesite="Lax", path="/")


@security_bp.errorhandler(Exception)
def security_error(error):
    if isinstance(error, SecurityError):
        return jsonify(error={"code": error.error_code, "message": error.description}), error.code
    if isinstance(error, HTTPException):
        return jsonify(error={"code": "invalid_request", "message": "Pedido inválido."}), error.code
    return jsonify(error={"code": "security_unavailable", "message": "Autenticação indisponível."}), 503


@security_bp.get("/csrf")
def csrf():
    _, policy = _runtime()
    token = issue_csrf(request, policy)
    response = jsonify(csrf_token=token)
    _set_cookie(response, policy.csrf_cookie, token, policy.csrf_seconds)
    return response


@security_bp.post("/login")
def login():
    runtime, policy = _runtime()
    verify_csrf(request, policy)
    request.max_content_length = 16384
    if not request.is_json:
        raise SecurityError(415, "invalid_request", "É necessário application/json.")
    identifier, password = normalize_credentials(request.get_json())
    user, token = runtime.service(policy).login(
        identifier, password, request.remote_addr or "unknown",
        request.cookies.get(policy.session_cookie),
    )
    response = jsonify(user=user.public())
    _set_cookie(response, policy.session_cookie, token, policy.absolute_seconds)
    _clear_cookie(response, policy.csrf_cookie)  # Pre-login CSRF cannot survive login.
    return response


@security_bp.post("/logout")
def logout():
    runtime, policy = _runtime()
    verify_csrf(request, policy)
    runtime.service(policy).logout(request.cookies.get(policy.session_cookie))
    response = current_app.response_class(status=204)
    _clear_cookie(response, policy.session_cookie)
    _clear_cookie(response, policy.csrf_cookie)
    return response


@security_bp.get("/me")
def me():
    runtime, _ = _runtime()
    user = runtime.authenticated()
    if user is None:
        raise SecurityError(401, "unauthenticated", "Autenticação necessária.")
    return jsonify(user=user.public())


def init_security(app, session_factory=None):
    from app.security.access import SecurityRuntime, SessionInventoryAccess

    runtime = SecurityRuntime(app, session_factory)
    app.extensions["security"] = runtime
    access = SessionInventoryAccess(runtime)
    app.register_blueprint(security_bp, url_prefix="/api/v1/auth")

    @app.before_request
    def protect_inventory_writes():
        # Trusted dependency injection used by M1.1 tests is not an HTTP switch.
        installed = app.extensions["inventory"].access
        if ((isinstance(installed, SessionInventoryAccess) or app.config.get("SECURITY_ENABLED") is True)
                and request.path.startswith("/api/v1/inventory/")
                and request.method not in {"GET", "HEAD", "OPTIONS"}):
            identity = access.resolve_identity()
            if identity is None:
                raise SecurityError(401, "unauthenticated", "Autenticação necessária.")
            verify_csrf(request, runtime.policy())

    @app.after_request
    def prevent_auth_caching(response):
        if request.path.startswith(("/api/v1/auth/", "/api/v1/inventory/")):
            response.headers["Cache-Control"] = "no-store"
            response.vary.add("Cookie")
        return response

    return access
