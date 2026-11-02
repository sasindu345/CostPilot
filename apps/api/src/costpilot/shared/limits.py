"""Rejects oversized uploads before they are read. Caddy applies the same limit in production."""

import json

from starlette.types import ASGIApp, Receive, Scope, Send


class MaxBodySizeMiddleware:
    def __init__(self, app: ASGIApp, path_prefix: str, max_bytes: int) -> None:
        self._app = app
        self._path_prefix = path_prefix
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith(self._path_prefix):
            headers = dict(scope["headers"])
            declared_size = headers.get(b"content-length", b"0")
            if declared_size.isdigit() and int(declared_size) > self._max_bytes:
                await self._reject(send)
                return
        await self._app(scope, receive, send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps(
            {"error": {"code": "file_too_large", "message": "That file is too large."}}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})
