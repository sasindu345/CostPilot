import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from costpilot.main import create_app
from costpilot.shared.config import Settings, get_settings
from costpilot.shared.errors import register_error_handlers
from costpilot.shared.exceptions import AppError


def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_come_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"


def _app_with_failing_routes() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/expected")
    def expected() -> None:
        raise AppError("That file is too large.")

    @app.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("secret database detail")

    return TestClient(app, raise_server_exceptions=False)


def test_expected_error_uses_the_standard_shape() -> None:
    response = _app_with_failing_routes().get("/expected")

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "bad_request", "message": "That file is too large."}
    }


def test_unexpected_error_hides_internal_details() -> None:
    response = _app_with_failing_routes().get("/unexpected")

    assert response.status_code == 500
    assert "secret database detail" not in response.text


def test_cancelling_at_keycloak_returns_to_the_app() -> None:
    client = TestClient(create_app(), follow_redirects=False)

    response = client.get("/api/auth/callback?error=access_denied")

    assert response.status_code == 302
    assert response.headers["location"] == get_settings().app_public_url


SAFE_PRODUCTION = {
    "APP_ENV": "production",
    "SESSION_COOKIE_SECURE": "true",
    "STORAGE_BACKEND": "s3",
    "S3_BUCKET": "costpilot-test",
    "AWS_REGION": "ap-south-1",
    "APP_PUBLIC_URL": "https://costpilot.example.com",
    "KEYCLOAK_PUBLIC_URL": "https://costpilot.example.com/auth",
}


def test_production_accepts_safe_settings(monkeypatch) -> None:
    for name, value in SAFE_PRODUCTION.items():
        monkeypatch.setenv(name, value)

    assert Settings().app_env == "production"


@pytest.mark.parametrize(
    ("name", "unsafe_value", "message"),
    [
        ("SESSION_COOKIE_SECURE", "false", "SESSION_COOKIE_SECURE"),
        ("STORAGE_BACKEND", "local", "STORAGE_BACKEND"),
        ("S3_BUCKET", "", "STORAGE_BACKEND"),
        ("APP_PUBLIC_URL", "http://costpilot.example.com", "APP_PUBLIC_URL"),
        ("KEYCLOAK_PUBLIC_URL", "http://costpilot.example.com/auth", "KEYCLOAK_PUBLIC_URL"),
    ],
)
def test_production_refuses_unsafe_settings(monkeypatch, name, unsafe_value, message) -> None:
    for key, value in SAFE_PRODUCTION.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(name, unsafe_value)

    with pytest.raises(ValidationError, match=message):
        Settings()
