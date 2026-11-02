from urllib.parse import urlencode

import httpx2
import jwt

from costpilot.modules.identity.application.auth_service import pkce_challenge
from costpilot.modules.identity.domain.errors import LoginFailedError
from costpilot.modules.identity.domain.models import LoginChallenge, VerifiedIdentity

OIDC_PATH = "protocol/openid-connect"
SIGNING_ALGORITHMS = ["RS256"]


class KeycloakProvider:
    def __init__(
        self,
        *,
        public_url: str,
        internal_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        post_logout_redirect_uri: str,
    ) -> None:
        self._public_realm_url = f"{public_url}/realms/{realm}"
        self._internal_realm_url = f"{internal_url}/realms/{realm}"
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._post_logout_redirect_uri = post_logout_redirect_uri

    def authorization_url(self, challenge: LoginChallenge) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": challenge.state,
                "nonce": challenge.nonce,
                "code_challenge": pkce_challenge(challenge.code_verifier),
                "code_challenge_method": "S256",
            }
        )
        return f"{self._public_realm_url}/{OIDC_PATH}/auth?{query}"

    def logout_url(self, id_token: str) -> str:
        query = urlencode(
            {
                "id_token_hint": id_token,
                "post_logout_redirect_uri": self._post_logout_redirect_uri,
            }
        )
        return f"{self._public_realm_url}/{OIDC_PATH}/logout?{query}"

    def account_url(self) -> str:
        return f"{self._public_realm_url}/account"

    async def verify_login(self, code: str, challenge: LoginChallenge) -> VerifiedIdentity:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self._internal_realm_url}/{OIDC_PATH}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code_verifier": challenge.code_verifier,
                },
            )
            if response.status_code != httpx2.codes.OK:
                raise LoginFailedError
            keys_response = await client.get(f"{self._internal_realm_url}/{OIDC_PATH}/certs")
            keys_response.raise_for_status()

        id_token = response.json()["id_token"]
        claims = self._verified_claims(id_token, keys_response.json())
        if claims.get("nonce") != challenge.nonce or not claims.get("email_verified"):
            raise LoginFailedError

        return VerifiedIdentity(
            subject=claims["sub"],
            email=claims["email"],
            display_name=claims.get("name") or claims["email"],
            id_token=id_token,
        )

    def _verified_claims(self, id_token: str, keys: dict) -> dict:
        try:
            key_id = jwt.get_unverified_header(id_token)["kid"]
            signing_key = jwt.PyJWKSet.from_dict(keys)[key_id]
            return jwt.decode(
                id_token,
                signing_key,
                algorithms=SIGNING_ALGORITHMS,
                audience=self._client_id,
                issuer=self._public_realm_url,
            )
        except (jwt.InvalidTokenError, KeyError) as error:
            raise LoginFailedError from error
