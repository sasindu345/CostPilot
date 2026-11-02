from fastapi import FastAPI
from fastapi.testclient import TestClient

from costpilot.main import create_app
from costpilot.shared.config import Settings
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
