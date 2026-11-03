from costpilot.shared.exceptions import AppError


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"

    def __init__(self) -> None:
        super().__init__("Please sign in.")


class LoginFailedError(AppError):
    code = "login_failed"

    def __init__(self) -> None:
        super().__init__("We could not sign you in. Please try again.")


class DeletionNotConfirmedError(AppError):
    code = "deletion_not_confirmed"

    def __init__(self) -> None:
        super().__init__("Type your email address exactly to confirm.")


class IdentityProviderError(Exception):
    """Keycloak could not complete an admin request."""
