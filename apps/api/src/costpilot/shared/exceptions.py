"""Errors the app expects. This file stays free of web tools, so domain code can use it."""


class AppError(Exception):
    """A problem we expect and can explain to the user."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
