from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_user_me():
    response = client.get("/status")
    # Check that we cannot do without auth
    assert response.status_code == 403
