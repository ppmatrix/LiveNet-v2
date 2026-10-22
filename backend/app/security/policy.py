"""Explicit configuration and request-origin policy; no operational defaults."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.security.errors import SecurityError, unavailable


def origin_of(value, *, allow_path=False):
    try:
        if not isinstance(value, str) or any(c.isspace() for c in value):
            raise ValueError()
        url = urlsplit(value)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.fragment or (not allow_path and (url.path not in ("", "/") or url.query))):
            raise ValueError()
        port = url.port or 443
        return (url.hostname.lower(), port)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class SecurityPolicy:
    origin: tuple
    csrf_key: str
    idle_seconds: int
    absolute_seconds: int
    csrf_seconds: int
    login_limit: int
    source_limit: int
    window_seconds: int
    session_cookie: str = "__Host-livenet_session"
    csrf_cookie: str = "__Host-livenet_csrf"

    @classmethod
    def load(cls, config):
        if config.get("SECURITY_ENABLED") is not True:
            raise unavailable()
        origin = origin_of(config.get("SECURITY_HTTPS_ORIGIN"))
        key = config.get("SECURITY_CSRF_KEY")
        limits = [config.get(k) for k in (
            "SECURITY_IDLE_SECONDS", "SECURITY_ABSOLUTE_SECONDS", "SECURITY_CSRF_SECONDS",
            "SECURITY_LOGIN_LIMIT", "SECURITY_SOURCE_LIMIT", "SECURITY_LOGIN_WINDOW_SECONDS",
        )]
        if (origin is None or not isinstance(key, str) or len(key) < 32
                or config.get("DEBUG") is True
                or any(type(v) is not int or v <= 0 for v in limits)
                or limits[0] > 1800 or limits[1] > 43200 or limits[0] > limits[1]
                or limits[2] > 1800
                or config.get("SECURITY_COOKIE_SECURE") is not True
                or config.get("SECURITY_COOKIE_HTTPONLY") is not True
                or config.get("SECURITY_COOKIE_SAMESITE") != "Lax"):
            raise unavailable()
        return cls(origin, key, *limits)

    def check_transport(self, request):
        if not request.is_secure or origin_of(request.host_url) != self.origin:
            raise SecurityError(403, "invalid_origin", "Origem não permitida.")

    def check_origin(self, request):
        self.check_transport(request)
        value = request.headers.get("Origin")
        actual = origin_of(value) if value is not None else origin_of(
            request.headers.get("Referer"), allow_path=True,
        )
        if actual != self.origin:
            raise SecurityError(403, "invalid_origin", "Origem não permitida.")
