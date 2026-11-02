"""Public interface of the audit module. Other modules may only import from here."""

from typing import Any, Protocol
from uuid import UUID


class AuditLog(Protocol):
    async def record(
        self, *, action: str, workspace_id: UUID, user_id: UUID, details: dict[str, Any]
    ) -> None:
        """Save one event. Events can be added and read, but never changed."""
