import os


class Config:
    TESTING = False
    DEBUG = False
    JSON_SORT_KEYS = False


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
