"""Shared pytest fixtures for backend tests."""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv

# Make backend env vars available to tests that need DB lookups (MONGO_URL, DB_NAME, JWT_SECRET).
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Fall back to frontend .env when env var not exported into test shell
    env_path = '/app/frontend/.env'
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break


@pytest.fixture(scope="session")
def base_url():
    assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
    return BASE_URL


@pytest.fixture
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(api_client, base_url, role="USER"):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    r = api_client.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": password, "role": role},
        timeout=20,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"email": email, "password": password, **data}


@pytest.fixture
def user_account(api_client, base_url):
    return _register(api_client, base_url, role="USER")


@pytest.fixture
def developer_account(api_client, base_url):
    return _register(api_client, base_url, role="DEVELOPER")


@pytest.fixture
def user_authed_client(api_client, user_account):
    api_client.headers.update({"Authorization": f"Bearer {user_account['access_token']}"})
    return api_client


@pytest.fixture
def dev_authed_client(api_client, developer_account):
    api_client.headers.update({"Authorization": f"Bearer {developer_account['access_token']}"})
    return api_client
