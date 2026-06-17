"""
Unit tests for the AuthService class.
Tests password hashing, token creation, and token verification — no HTTP layer.
"""

import pytest
import time
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException

from backend.services.auth import AuthService, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from backend.config import SECRET_KEY


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = AuthService.hash_password("secret123")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_is_not_plain_text(self):
        h = AuthService.hash_password("secret123")
        assert h != "secret123"

    def test_verify_correct_password(self):
        h = AuthService.hash_password("mypassword")
        assert AuthService.verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = AuthService.hash_password("mypassword")
        assert AuthService.verify_password("wrongpass", h) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salt — same plaintext → different hashes."""
        h1 = AuthService.hash_password("same")
        h2 = AuthService.hash_password("same")
        assert h1 != h2

    def test_hash_truncates_at_72_chars(self):
        """Passwords longer than 72 chars are truncated consistently."""
        long_pw = "a" * 100
        h = AuthService.hash_password(long_pw)
        assert AuthService.verify_password("a" * 72, h) is True


class TestTokenCreation:
    def test_create_token_returns_string(self):
        token = AuthService.create_token(1, "u@test.com", "admin")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_payload_contains_expected_fields(self):
        token = AuthService.create_token(42, "u@test.com", "municipality", municipality_id=7)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["email"] == "u@test.com"
        assert payload["role"] == "municipality"
        assert payload["municipality_id"] == 7

    def test_token_includes_exp_and_iat(self):
        token = AuthService.create_token(1, "u@test.com", "admin")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiry_is_future(self):
        token = AuthService.create_token(1, "u@test.com", "admin")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["exp"] > time.time()

    def test_municipality_id_none_when_not_provided(self):
        token = AuthService.create_token(1, "u@test.com", "admin")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["municipality_id"] is None


class TestTokenVerification:
    def test_verify_valid_token(self):
        token = AuthService.create_token(5, "x@test.com", "admin")
        payload = AuthService.verify_token(token)
        assert payload["sub"] == "5"

    def test_verify_expired_token_raises_401(self):
        # Build a token that's already expired
        payload = {
            "sub": "1",
            "email": "x@test.com",
            "role": "admin",
            "municipality_id": None,
            "exp": datetime.utcnow() - timedelta(seconds=1),
            "iat": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            AuthService.verify_token(expired_token)
        assert exc_info.value.status_code == 401

    def test_verify_invalid_token_raises_exception(self):
        """Malformed tokens raise either HTTPException or a jose error."""
        try:
            AuthService.verify_token("not.a.valid.jwt.token")
            pytest.fail("Expected an exception for malformed token")
        except HTTPException as e:
            assert e.status_code == 401
        except Exception:
            pass  # jose may raise JWSError for truly malformed bytes

    def test_verify_token_wrong_secret_raises_exception(self):
        """Wrong secret causes jose.JWSSignatureError (wrapped or propagated)."""
        token = jwt.encode({"sub": "1", "email": "x", "role": "admin",
                            "municipality_id": None,
                            "exp": datetime.utcnow() + timedelta(hours=1),
                            "iat": datetime.utcnow()},
                           "wrong_secret", algorithm=JWT_ALGORITHM)
        try:
            AuthService.verify_token(token)
            pytest.fail("Expected an exception for wrong-secret token")
        except HTTPException as e:
            assert e.status_code == 401
        except Exception:
            pass  # jose.JWSSignatureError may not be wrapped

    def test_extract_user_from_token(self):
        token = AuthService.create_token(99, "me@test.com", "admin")
        user_id, email, role = AuthService.extract_user_from_token(token)
        assert user_id == 99
        assert email == "me@test.com"
        assert role == "admin"
