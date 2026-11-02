#!/usr/bin/env bash
# One-time project setup. Safe to run again.
set -euo pipefail

for tool in uv pnpm docker gitleaks pre-commit; do
  if ! command -v "$tool" >/dev/null; then
    echo "Missing tool: $tool. See docs/guides/getting-started.md"
    exit 1
  fi
done

random_password() {
  python3 -c "import secrets; print(secrets.token_urlsafe(24))"
}

if [ ! -f .env ]; then
  cp .env.example .env
  for name in POSTGRES_PASSWORD KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD; do
    value="$(random_password)"
    python3 - "$name" "$value" <<'PY'
import sys
from pathlib import Path

name, value = sys.argv[1:]
env = Path(".env")
env.write_text(env.read_text().replace(f"{name}=\n", f"{name}={value}\n"))
PY
  done
  echo "Created .env with new random passwords."
fi

(cd apps/api && uv sync)
(cd apps/web && pnpm install)
pre-commit install

echo "Setup finished. Run: make up"
