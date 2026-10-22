from werkzeug.exceptions import HTTPException


class SecurityError(HTTPException):
    """Only fixed public messages; never wrap database/credential details."""

    def __init__(self, status, error_code, message):
        super().__init__(description=message)
        self.code = status
        self.error_code = error_code


def unavailable():
    return SecurityError(503, "security_unavailable", "Autenticação indisponível.")
