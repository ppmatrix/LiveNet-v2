"""Signed double-submit CSRF, bound to pre-login or the current opaque session."""

import hashlib
import hmac
import secrets

from itsdangerous import BadData, URLSafeTimedSerializer

from app.security.errors import SecurityError


def _binding(request, policy):
    token = request.cookies.get(policy.session_cookie)
    return hashlib.sha256(token.encode()).hexdigest() if token else "pre-login"


def _serializer(policy):
    return URLSafeTimedSerializer(policy.csrf_key, salt="livenet.application.csrf.v1",
                                  signer_kwargs={"digest_method": hashlib.sha256})


def issue_csrf(request, policy):
    return _serializer(policy).dumps({"binding": _binding(request, policy),
                                      "nonce": secrets.token_urlsafe(32)})


def verify_csrf(request, policy):
    policy.check_origin(request)
    header = request.headers.get("X-CSRF-Token", "")
    cookie = request.cookies.get(policy.csrf_cookie, "")
    try:
        if (not header or len(header) > 2048 or not cookie
                or not hmac.compare_digest(header.encode(), cookie.encode())):
            raise BadData("invalid")
        data = _serializer(policy).loads(header, max_age=policy.csrf_seconds)
        if (not isinstance(data, dict) or data.get("binding") != _binding(request, policy)
                or not isinstance(data.get("nonce"), str)):
            raise BadData("invalid")
    except (BadData, ValueError, UnicodeError):
        raise SecurityError(403, "invalid_csrf", "Proteção CSRF inválida.") from None
