import pytest

from app.config import Config
from app.security.errors import SecurityError
from app.security.policy import SecurityPolicy, origin_of


@pytest.mark.parametrize("value", [None, "http://lab.test", "https://user@lab.test",
                                   "https://lab.test/path", "https://lab.test?x=y",
                                   "https://lab.test:bad", "null", "https://lab.test #bad"])
def test_invalid_configured_origin(value):
    assert origin_of(value) is None


def test_origin_normalization():
    assert origin_of("https://LAB.test:443/") == origin_of("https://lab.test")
    assert origin_of("https://lab.test:444") != origin_of("https://lab.test")


@pytest.mark.parametrize("field,value", [
    ("SECURITY_ENABLED", False), ("SECURITY_CSRF_KEY", "short"),
    ("SECURITY_COOKIE_SECURE", False), ("SECURITY_COOKIE_HTTPONLY", False),
    ("SECURITY_COOKIE_SAMESITE", "None"), ("SECURITY_IDLE_SECONDS", 1801),
    ("SECURITY_ABSOLUTE_SECONDS", 43201), ("SECURITY_LOGIN_LIMIT", 0),
    ("SECURITY_SOURCE_LIMIT", True), ("SECURITY_CSRF_SECONDS", 1801),
    ("DEBUG", True),
])
def test_incomplete_or_weakened_configuration_is_rejected(field, value):
    config = {key: getattr(Config, key) for key in dir(Config) if key.startswith("SECURITY_")}
    config.update(SECURITY_ENABLED=True, SECURITY_HTTPS_ORIGIN="https://lab.test",
                  SECURITY_CSRF_KEY="synthetic-offline-key-not-for-operational-use")
    config[field] = value
    with pytest.raises(SecurityError) as error:
        SecurityPolicy.load(config)
    assert error.value.code == 503
