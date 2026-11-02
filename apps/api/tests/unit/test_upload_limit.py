from fastapi.testclient import TestClient

from costpilot.main import create_app


def test_oversized_upload_is_rejected_before_it_is_read():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents",
        content=b"x",
        headers={"content-length": str(500 * 1024 * 1024)},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_needs_a_signed_in_user():
    client = TestClient(create_app())

    response = client.post("/api/documents", files={"file": ("bill.csv", b"a,b\n1,2\n")})

    assert response.status_code == 401
