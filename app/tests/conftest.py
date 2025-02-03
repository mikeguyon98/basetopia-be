# app/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
import os
from pathlib import Path
from dotenv import load_dotenv
from app.main import app
import firebase_admin
from firebase_admin import credentials, auth

# Get root directory and load test env
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env.test')


@pytest.fixture(scope="session")
def test_token():
    """Provide test token for all tests"""
    token = os.getenv('TEST_USER_ID_TOKEN')
    if not token:
        raise ValueError(
            "No test token found. Run scripts/get_id_token.py first")
    return f"Bearer {token}"


@pytest.fixture
def client():
    """Provide FastAPI test client"""
    return TestClient(app)


@pytest.fixture(scope="session")
def test_user_id():
    """Provide test user UID"""
    return os.getenv('TEST_USER_UID')
