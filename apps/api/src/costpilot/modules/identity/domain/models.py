from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class VerifiedIdentity:
    """What Keycloak has proven about a person."""

    subject: str
    email: str
    display_name: str
    id_token: str


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    email: str
    display_name: str
    workspace_id: UUID
    workspace_name: str
    role: str


@dataclass(frozen=True)
class LoginChallenge:
    """One-time values that tie the Keycloak reply to the browser that started the login."""

    state: str
    nonce: str
    code_verifier: str
