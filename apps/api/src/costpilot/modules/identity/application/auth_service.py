"""The steps of signing in and out. See docs/guides/keycloak-beginners-guide.md."""

import base64
import hashlib
import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from costpilot.modules.audit.contracts import AuditLog
from costpilot.modules.identity.application.ports import (
    IdentityProvider,
    IdentityRepository,
    SecretBox,
)
from costpilot.modules.identity.domain.errors import LoginFailedError, NotAuthenticatedError
from costpilot.modules.identity.domain.models import CurrentUser, LoginChallenge


def _hash_token(session_token: str) -> bytes:
    """Only the hash is stored, so a stolen database backup cannot be used to log in."""
    return hashlib.sha256(session_token.encode()).digest()


def pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class AuthService:
    def __init__(
        self,
        provider: IdentityProvider,
        repository: IdentityRepository,
        secret_box: SecretBox,
        audit_log: AuditLog,
        session_lifetime: timedelta,
        login_lifetime_seconds: int,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._secret_box = secret_box
        self._audit_log = audit_log
        self._session_lifetime = session_lifetime
        self._login_lifetime_seconds = login_lifetime_seconds

    def begin_login(self) -> tuple[str, str]:
        """Return the Keycloak address and a sealed value for a short-lived cookie."""
        challenge = LoginChallenge(
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            code_verifier=secrets.token_urlsafe(64),
        )
        sealed = self._secret_box.seal(json.dumps(asdict(challenge)))
        return self._provider.authorization_url(challenge), sealed

    async def complete_login(
        self, code: str, state: str, sealed_challenge: str | None
    ) -> tuple[str, CurrentUser]:
        """Return a new session token and the signed-in user."""
        challenge = self._open_challenge(sealed_challenge)
        if not secrets.compare_digest(state, challenge.state):
            raise LoginFailedError

        identity = await self._provider.verify_login(code, challenge)
        user, is_new = await self._repository.save_identity(identity)

        session_token = secrets.token_urlsafe(32)
        await self._repository.create_session(
            _hash_token(session_token),
            user,
            self._secret_box.seal(identity.id_token),
            datetime.now(UTC) + self._session_lifetime,
        )
        await self._audit_log.record(
            action="user.created" if is_new else "user.signed_in",
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={},
        )
        return session_token, user

    async def current_user(self, session_token: str | None) -> CurrentUser:
        if not session_token:
            raise NotAuthenticatedError
        found = await self._repository.find_session(_hash_token(session_token), datetime.now(UTC))
        if found is None:
            raise NotAuthenticatedError
        return found[0]

    async def logout(self, session_token: str | None) -> str:
        """End the session here and return the address that ends it in Keycloak."""
        if not session_token:
            raise NotAuthenticatedError
        token_hash = _hash_token(session_token)
        found = await self._repository.find_session(token_hash, datetime.now(UTC))
        if found is None:
            raise NotAuthenticatedError
        user, sealed_id_token = found
        await self._repository.delete_session(token_hash)
        await self._audit_log.record(
            action="user.signed_out",
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={},
        )
        return self._provider.logout_url(self._secret_box.open(sealed_id_token) or "")

    def account_url(self) -> str:
        return self._provider.account_url()

    def _open_challenge(self, sealed_challenge: str | None) -> LoginChallenge:
        if not sealed_challenge:
            raise LoginFailedError
        opened = self._secret_box.open(sealed_challenge, self._login_lifetime_seconds)
        if opened is None:
            raise LoginFailedError
        return LoginChallenge(**json.loads(opened))
