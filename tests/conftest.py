import pytest

@pytest.fixture(scope="session")
def test_client():
    from main_app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    yield client