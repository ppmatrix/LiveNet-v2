"""Standard MVP installation, explicitly separate from historical DEV09B."""

APPLICATION_TARGET = 'f066a01a7230'
SECURITY_TARGET = 'b12b01a7230'
STANDARD_ATTR = 'livenet_standard_installation_v1'


class Refused(ValueError):
    """Fixed diagnostic code only; no driver text, SQL or credential values."""


def require(value, code):
    if not value:
        raise Refused(code)
