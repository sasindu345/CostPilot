"""One error shape for the whole API, so the frontend handles every failure the same way."""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from costpilot.shared.exceptions import AppError

logger = structlog.get_logger()


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return _error_response(error.status_code, error.code, error.message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error("unexpected_error", path=request.url.path, exc_info=error)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "Something went wrong on our side.",
        )
