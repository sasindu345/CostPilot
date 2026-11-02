"""Create or update .env from .env.example. Safe to run again: it never changes a value you set."""

import base64
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / ".env.example"
ENV = ROOT / ".env"

PASSWORDS = {
    "POSTGRES_PASSWORD",
    "POSTGRES_APP_PASSWORD",
    "KEYCLOAK_DB_PASSWORD",
    "KEYCLOAK_ADMIN_PASSWORD",
    "KEYCLOAK_CLIENT_SECRET",
}
ENCRYPTION_KEYS = {"SESSION_ENCRYPTION_KEY"}


def new_value(name: str) -> str:
    if name in PASSWORDS:
        return secrets.token_urlsafe(24)
    if name in ENCRYPTION_KEYS:
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    return ""


def read_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return {key: value for key, value in pairs if not key.startswith("#")}


def main() -> None:
    current = read_values(ENV)
    lines = []
    for line in EXAMPLE.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            lines.append(line)
            continue
        name, default = line.split("=", 1)
        lines.append(f"{name}={current.get(name) or default or new_value(name)}")
    ENV.write_text("\n".join(lines) + "\n")
    ENV.chmod(0o600)
    print("Updated .env")


if __name__ == "__main__":
    main()
