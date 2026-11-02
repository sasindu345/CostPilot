"""Test settings. A real .env wins, so integration tests can reach the local database."""

import base64
import os
from pathlib import Path

TEST_DATABASE = "costpilot_test"

TEST_DEFAULTS = {
    "APP_PUBLIC_URL": "http://app.test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5433",
    "POSTGRES_USER": "test_admin",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_APP_USER": "test_app",
    "POSTGRES_APP_PASSWORD": "test",
    "KEYCLOAK_PUBLIC_URL": "http://keycloak.test",
    "KEYCLOAK_INTERNAL_URL": "http://keycloak.test",
    "KEYCLOAK_REALM": "costpilot",
    "KEYCLOAK_CLIENT_ID": "costpilot-api",
    "KEYCLOAK_CLIENT_SECRET": "test",
    "SESSION_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"0" * 32).decode(),
    "SESSION_COOKIE_NAME": "test_session",
    "SESSION_COOKIE_SECURE": "false",
    "SESSION_LIFETIME_HOURS": "8",
    "QDRANT_URL": "http://qdrant.test",
    "GEMINI_EMBEDDING_MODEL": "test-model",
    "GEMINI_ANSWER_MODEL": "test-model",
    "GEMINI_ROUTER_MODEL": "test-model",
    "STORAGE_BACKEND": "local",
    "STORAGE_LOCAL_PATH": "/tmp/costpilot-test-uploads",
}

# Tests use their own database, so they never touch the running app or its worker.
os.environ["POSTGRES_DB"] = TEST_DATABASE

if not (Path(__file__).parents[3] / ".env").exists():
    for name, value in TEST_DEFAULTS.items():
        os.environ.setdefault(name, value)
