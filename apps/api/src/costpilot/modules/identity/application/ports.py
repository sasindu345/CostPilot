"""What the login use cases need from the outside world."""

from datetime import datetime
from typing import Protocol

from costpilot.modules.identity.domain.models import (
    CurrentUser,
    LoginChallenge,
    VerifiedIdentity,
)


class IdentityProvider(Protocol):
    def authorization_url(self, challenge: LoginChallenge) -> str: ...

    async def verify_login(self, code: str, challenge: LoginChallenge) -> VerifiedIdentity: ...

    def logout_url(self, id_token: str) -> str: ...

    def account_url(self) -> str: ...


class SecretBox(Protocol):
    """Encrypts short secrets."""

    def seal(self, value: str) -> str: ...

    def open(self, sealed: str, max_age_seconds: int | None = None) -> str | None:
        """Return the value, or None if it was changed or is too old."""


class IdentityRepository(Protocol):
    async def save_identity(self, identity: VerifiedIdentity) -> tuple[CurrentUser, bool]:
        """Create or update the user. The second value is True for a brand new user."""

    async def create_session(
        self, token_hash: bytes, user: CurrentUser, sealed_id_token: str, expires_at: datetime
    ) -> None: ...

    async def find_session(
        self, token_hash: bytes, now: datetime
    ) -> tuple[CurrentUser, str] | None: ...

    async def delete_session(self, token_hash: bytes) -> None: ...
