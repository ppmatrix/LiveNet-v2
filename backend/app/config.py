import os


class Config:
    TESTING = False
    DEBUG = False
    JSON_SORT_KEYS = False
    # No credentials, origin or operational enablement are supplied by default.
    SECURITY_ENABLED = False
    SECURITY_HTTPS_ORIGIN = None
    SECURITY_CSRF_KEY = None
    SECURITY_IDLE_SECONDS = 1800
    SECURITY_ABSOLUTE_SECONDS = 43200
    SECURITY_CSRF_SECONDS = 1800
    SECURITY_COOKIE_SECURE = True
    SECURITY_COOKIE_HTTPONLY = True
    SECURITY_COOKIE_SAMESITE = "Lax"
    SECURITY_LOGIN_LIMIT = 5
    SECURITY_SOURCE_LIMIT = 50
    SECURITY_LOGIN_WINDOW_SECONDS = 900


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_name():
    name = os.getenv("LIVENET_ENV", "production")

    if name not in CONFIG_MAP:
        raise ValueError(
            f"Invalid LIVENET_ENV: {name}"
        )

    return name
