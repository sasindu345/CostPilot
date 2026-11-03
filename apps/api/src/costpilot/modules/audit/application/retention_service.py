"""Removes records that are older than the retention policy allows."""

from typing import Protocol

import structlog

from costpilot.modules.audit.domain.retention import RetentionPolicy, RetentionResult

logger = structlog.get_logger()


class RetentionStore(Protocol):
    async def apply(self, policy: RetentionPolicy) -> RetentionResult: ...


class RetentionService:
    def __init__(self, store: RetentionStore, policy: RetentionPolicy) -> None:
        self._store = store
        self._policy = policy

    async def run(self) -> RetentionResult:
        result = await self._store.apply(self._policy)
        logger.info(
            "retention_applied",
            audit_events=result.audit_events,
            conversations=result.conversations,
            failed_jobs=result.failed_jobs,
            sessions=result.sessions,
        )
        return result
