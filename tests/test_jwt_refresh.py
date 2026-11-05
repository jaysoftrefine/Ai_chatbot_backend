import pytest
from datetime import timedelta
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_token_creation_and_decoding():
    user_id = "test-user-uuid-123"
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    # Valid access token decode
    access_payload = decode_access_token(access_token)
    assert access_payload is not None
    assert access_payload["sub"] == user_id
    assert access_payload["type"] == "access"

    # Valid refresh token decode
    refresh_payload = decode_refresh_token(refresh_token)
    assert refresh_payload is not None
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"

    # Cross-decode should fail (cannot decode refresh token as access token)
    assert decode_access_token(refresh_token) is None
    assert decode_refresh_token(access_token) is None


def test_expired_token():
    user_id = "test-user-uuid-expired"
    # Token that expired 5 seconds ago
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-5))
    assert decode_access_token(expired_token) is None


def test_auth_refresh_endpoint(client, auth_user_a):
    # 1. Login user to get refresh token
    res = client.post(
        "/api/v1/auth/login",
        json={"email": auth_user_a["email"], "password": "password123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    refresh_token = data["refresh_token"]

    # 2. Call refresh endpoint using refresh_token in request body
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert new_data["user"]["email"] == auth_user_a["email"]

    # Verify new access token works on protected route
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == auth_user_a["email"]

