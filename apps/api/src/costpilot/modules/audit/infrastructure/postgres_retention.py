from sqlalchemy import text

from costpilot.modules.audit.domain.retention import RetentionPolicy, RetentionResult
from costpilot.shared.database import Database

# A database function does the work, because old records sit in every workspace.
# See migration 0006.
APPLY_RETENTION = text("SELECT * FROM apply_retention(:audit_days, :conversation_days, :job_days)")


class PostgresRetentionStore:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def apply(self, policy: RetentionPolicy) -> RetentionResult:
        async with self._database.transaction() as db:
            row = (
                await db.execute(
                    APPLY_RETENTION,
                    {
                        "audit_days": policy.audit_days,
                        "conversation_days": policy.conversation_days,
                        "job_days": policy.failed_job_days,
                    },
                )
            ).one()
        return RetentionResult(
            audit_events=row.deleted_audit_events,
            conversations=row.deleted_conversations,
            failed_jobs=row.deleted_failed_jobs,
            sessions=row.deleted_sessions,
        )
