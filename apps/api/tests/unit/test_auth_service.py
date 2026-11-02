from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from costpilot.modules.identity.application.auth_service import AuthService, pkce_challenge
from costpilot.modules.identity.domain.errors import LoginFailedError, NotAuthenticatedError
from costpilot.modules.identity.domain.models import CurrentUser, VerifiedIdentity
from costpilot.modules.identity.infrastructure.fernet_secret_box import FernetSecretBox
from tests.conftest import TEST_DEFAULTS

IDENTITY = VerifiedIdentity("subject-1", "a@example.test", "Ann", "id-token")
USER = CurrentUser(uuid4(), "a@example.test", "Ann", uuid4(), "My workspace", "owner")


class FakeProvider:
    def authorization_url(self, challenge):
        return f"http://login.test?state={challenge.state}"

    async def verify_login(self, code, challenge):
        return IDENTITY

    def logout_url(self, id_token):
        return f"http://login.test/logout?hint={id_token}"

    def account_url(self):
        return "http://login.test/account"


class FakeRepository:
    def __init__(self):
        self.sessions = {}

    async def save_identity(self, identity):
        return USER, True

    async def create_session(self, token_hash, user, sealed_id_token, expires_at):
        self.sessions[token_hash] = (user, sealed_id_token, expires_at)

    async def find_session(self, token_hash, now):
        found = self.sessions.get(token_hash)
        if found is None or found[2] <= now:
            return None
        return found[0], found[1]

    async def delete_session(self, token_hash):
        del self.sessions[token_hash]


class FakeAuditLog:
    def __init__(self):
        self.actions = []

    async def record(self, *, action, workspace_id, user_id, details):
        self.actions.append(action)


@pytest.fixture
def repository():
    return FakeRepository()


@pytest.fixture
def audit_log():
    return FakeAuditLog()


@pytest.fixture
def auth(repository, audit_log):
    return AuthService(
        provider=FakeProvider(),
        repository=repository,
        secret_box=FernetSecretBox(TEST_DEFAULTS["SESSION_ENCRYPTION_KEY"]),
        audit_log=audit_log,
        session_lifetime=timedelta(hours=8),
        login_lifetime_seconds=600,
    )


async def signed_in(auth):
    url, sealed = auth.begin_login()
    state = url.split("state=")[1]
    token, _ = await auth.complete_login("code", state, sealed)
    return token


async def test_login_creates_a_working_session(auth, audit_log):
    token = await signed_in(auth)

    assert await auth.current_user(token) == USER
    assert audit_log.actions == ["user.created"]


async def test_session_token_is_not_stored_in_plain_form(auth, repository):
    token = await signed_in(auth)

    assert token.encode() not in repository.sessions


async def test_id_token_is_stored_encrypted(auth, repository):
    await signed_in(auth)

    _, sealed, _ = next(iter(repository.sessions.values()))
    assert IDENTITY.id_token not in sealed


async def test_login_is_rejected_when_state_does_not_match(auth):
    _, sealed = auth.begin_login()

    with pytest.raises(LoginFailedError):
        await auth.complete_login("code", "wrong-state", sealed)


async def test_login_is_rejected_without_the_browser_cookie(auth):
    url, _ = auth.begin_login()

    with pytest.raises(LoginFailedError):
        await auth.complete_login("code", url.split("state=")[1], None)


async def test_login_is_rejected_when_the_cookie_was_changed(auth):
    url, sealed = auth.begin_login()

    with pytest.raises(LoginFailedError):
        await auth.complete_login("code", url.split("state=")[1], sealed[:-4] + "AAAA")


async def test_unknown_session_is_rejected(auth):
    with pytest.raises(NotAuthenticatedError):
        await auth.current_user("not-a-real-token")


async def test_missing_session_is_rejected(auth):
    with pytest.raises(NotAuthenticatedError):
        await auth.current_user(None)


async def test_expired_session_is_rejected(auth, repository):
    token = await signed_in(auth)
    key = next(iter(repository.sessions))
    user, sealed, _ = repository.sessions[key]
    repository.sessions[key] = (user, sealed, datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(NotAuthenticatedError):
        await auth.current_user(token)


async def test_logout_ends_the_session(auth, audit_log):
    token = await signed_in(auth)

    logout_url = await auth.logout(token)

    assert "hint=id-token" in logout_url
    assert audit_log.actions[-1] == "user.signed_out"
    with pytest.raises(NotAuthenticatedError):
        await auth.current_user(token)


def test_pkce_challenge_matches_the_published_example():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    assert pkce_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
