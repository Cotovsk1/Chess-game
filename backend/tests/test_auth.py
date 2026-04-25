import pytest
from fastapi import status

from pathlib import Path
import sys
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_register_success(test_client):
    payload = {"username": "newuser", "email": "new@example.com", "password": "password123"}
    response = test_client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "newuser"

def test_register_duplicate_username(test_client):
    payload = {"username": "testuser", "email": "unique@example.com", "password": "password123"}
    test_client.post("/auth/register", json=payload)  # First one
    response = test_client.post("/auth/register", json=payload) # Duplicate
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_login_success(test_client):
    # Спочатку реєструємо, щоб точно знати, що юзер є в цій конкретній сесії БД
    user_data = {"username": "loginuser", "email": "login@test.com", "password": "password123"}
    test_client.post("/auth/register", json=user_data)
    
    # Спроба логіну
    response = test_client.post("/auth/login", data={
        "username": "loginuser",
        "password": "password123"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

def test_login_invalid_credentials(test_client):
    response = test_client.post("/auth/login", data={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_me_protected(test_client, auth_headers):
    response = test_client.get("/auth/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "testuser"

def test_get_me_no_token(test_client):
    response = test_client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED