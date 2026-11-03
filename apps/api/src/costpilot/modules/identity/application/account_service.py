"""A user's own data: download all of it, or delete all of it."""

import structlog

from costpilot.modules.audit.contracts import AuditLog
from costpilot.modules.identity.application.ports import (
    AccountDirectory,
    AccountRepository,
    WorkspaceFiles,
)
from costpilot.modules.identity.domain.errors import (
    DeletionNotConfirmedError,
    IdentityProviderError,
)
from costpilot.modules.identity.domain.models import CurrentUser

logger = structlog.get_logger()


class AccountService:
    def __init__(
        self,
        repository: AccountRepository,
        files: WorkspaceFiles,
        directory: AccountDirectory,
        audit_log: AuditLog,
    ) -> None:
        self._repository = repository
        self._files = files
        self._directory = directory
        self._audit_log = audit_log

    async def export(self, user: CurrentUser) -> str:
        await self._audit_log.record(
            action="account.exported",
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={},
        )
        return await self._repository.export_workspace(user)

    async def delete(self, user: CurrentUser, confirm_email: str) -> None:
        """Data goes first, then files, then the Keycloak login.

        If a later step fails, the data is already gone, which is what the user asked for.
        """
        if confirm_email.strip().casefold() != user.email.casefold():
            raise DeletionNotConfirmedError
        subject = await self._repository.find_subject(user)
        keys = await self._files.workspace_file_keys(user)
        await self._repository.delete_account(user)
        await self._files.delete_files(keys)
        try:
            await self._directory.delete_user(subject)
        except IdentityProviderError:
            # Signing in again would only find an empty new workspace.
            logger.exception("keycloak_user_not_deleted", user_id=str(user.user_id))
        logger.info("account_deleted", user_id=str(user.user_id), files=len(keys))
