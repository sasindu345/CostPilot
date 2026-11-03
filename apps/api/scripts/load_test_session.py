"""Make a signed-in test user with the sample bill, and print its session cookie.

Used by `make load-test`. It creates the user through the Keycloak admin API, so it only runs
against your own computer, never production.
"""

import html
import re
import sys
from uuid import uuid4

import httpx

from costpilot.shared.config import get_settings

FORM_ACTION = re.compile(r'action="([^"]+)"')


def admin_token(keycloak: str, user: str, password: str) -> str:
    response = httpx.post(
        f"{keycloak}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": user,
            "password": password,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    settings = get_settings()
    if settings.app_env == "production":
        print("This script is for your own computer only.", file=sys.stderr)
        return 1
    admin_user, admin_password = sys.argv[1:3]
    email, password = f"load-{uuid4()}@example.test", f"Load-{uuid4()}"
    token = admin_token(settings.keycloak_public_url, admin_user, admin_password)
    created = httpx.post(
        f"{settings.keycloak_public_url}/admin/realms/{settings.keycloak_realm}/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": email,
            "email": email,
            "enabled": True,
            "emailVerified": True,
            "firstName": "Load",
            "lastName": "Test",
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        },
    )
    created.raise_for_status()

    with httpx.Client(follow_redirects=True, timeout=30) as client:
        page = client.get(f"{settings.app_public_url}/api/auth/login")
        action = html.unescape(FORM_ACTION.search(page.text).group(1))
        # Keycloak marks its cookies secure-only. Browsers still send them to localhost over
        # plain HTTP, but this client does not, so the flag is cleared for this local test.
        for stored in client.cookies.jar:
            stored.secure = False
        client.post(action, data={"username": email, "password": password})
        cookie = client.cookies.get(settings.session_cookie_name)
        if not cookie:
            print("Sign-in failed, so there is no session cookie.", file=sys.stderr)
            return 1
        client.post(f"{settings.app_public_url}/api/documents/sample").raise_for_status()
    print(cookie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
