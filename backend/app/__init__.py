from flask import Flask

from .config import CONFIG_MAP, get_config_name


def create_app(config_name=None):
    if config_name is None:
        config_name = get_config_name()

    if config_name not in CONFIG_MAP:
        raise ValueError(
            f"Invalid configuration: {config_name}"
        )

    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP[config_name])

    from .health.routes import health_bp
    app.register_blueprint(
        health_bp,
        url_prefix="/api/v1"
    )

    return app
