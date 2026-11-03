"""How long old records are kept. Bills are kept until the user deletes them."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionPolicy:
    audit_days: int
    conversation_days: int
    failed_job_days: int

    def __post_init__(self) -> None:
        if min(self.audit_days, self.conversation_days, self.failed_job_days) < 1:
            raise ValueError("Retention days must be at least 1")


@dataclass(frozen=True)
class RetentionResult:
    audit_events: int
    conversations: int
    failed_jobs: int
    sessions: int
