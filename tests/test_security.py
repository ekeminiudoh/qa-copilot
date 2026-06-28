"""Tests for security utilities: bcrypt, JWT, API keys, token revocation."""

import time
import pytest
from datetime import timedelta

from backend.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_password_hash,
    revoke_token,
    verify_password,
)


def test_bcrypt_hash_and_verify():
    password = "my-secure-password-123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_different_hashes_for_same_password():
    h1 = get_password_hash("same-pass")
    h2 = get_password_hash("same-pass")
    # bcrypt generates unique salts
    assert h1 != h2
    assert verify_password("same-pass", h1)
    assert verify_password("same-pass", h2)


def test_create_and_decode_access_token():
    token = create_access_token(
        username="testuser",
        roles=["tester"],
        permissions=["read:queries"],
    )
    data = decode_token(token)
    assert data is not None
    assert data.username == "testuser"
    assert "tester" in data.roles
    assert data.token_type == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token("refreshuser")
    data = decode_token(token)
    assert data is not None
    assert data.username == "refreshuser"
    assert data.token_type == "refresh"


def test_expired_access_token():
    token = create_access_token("user", expires_delta=timedelta(seconds=-1))
    data = decode_token(token)
    assert data is None


def test_revoke_token():
    token = create_access_token("revokeuser")
    assert decode_token(token) is not None
    revoke_token(token)
    assert decode_token(token) is None


def test_invalid_token_returns_none():
    assert decode_token("not.a.valid.jwt") is None
    assert decode_token("") is None
    assert decode_token("Bearer abc") is None


def test_generate_api_key_format():
    key = generate_api_key()
    assert key.startswith("qac_")
    assert len(key) > 20


def test_generate_api_keys_unique():
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100
