from __future__ import annotations

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    pw = "test-password-456"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_access_token():
    data = {"sub": "user-123", "jti": "jti-456"}
    token = create_access_token(data)
    assert isinstance(token, str)
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["jti"] == "jti-456"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_and_decode_refresh_token():
    token = create_refresh_token({"sub": "user-789", "jti": "jti-abc"})
    payload = decode_token(token)
    assert payload["sub"] == "user-789"
    assert payload["type"] == "refresh"


def test_verify_password_edge_cases():
    pw = "普通中文密码!"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed)
    # empty string
    long_pw = "a" * 128
    assert verify_password(long_pw, hash_password(long_pw))
