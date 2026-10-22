from flask import Flask

from .config import CONFIG_MAP, get_config_name


def create_app(config_name=None, *, inventory_access=None, inventory_session_factory=None):
    """Create the app. Inventory denies access until real identity/RBAC is wired.

    Keyword dependencies are for trusted integration and isolated tests only;
    there is no anonymous mode, identity header or environment bypass.
    """
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

    from .inventory.routes import inventory_bp, InventoryDependencies
    app.extensions["inventory"] = InventoryDependencies(
        inventory_access, inventory_session_factory,
    )
    app.register_blueprint(inventory_bp, url_prefix="/api/v1/inventory")

    return app
