"""Unit tests for Password Hashing and JWT Token Authentication services."""
import time
import uuid

from services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SuperSecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed.startswith("pbkdf2_sha256$200000$")
    assert raw_password not in hashed

    # Verify correct password succeeds
    assert verify_password(raw_password, hashed) is True

    # Verify wrong password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_create_and_decode_valid():
    user_id = uuid.uuid4()
    email = "patient@healthcare.org"

    token = create_access_token(user_id=user_id, email=email, role="patient", expires_in_minutes=60)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["role"] == "patient"
    assert payload["iss"] == "policygraph-rag"


def test_jwt_token_detects_tampering():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, email="patient@healthcare.org")

    parts = token.split(".")
    # Tamper with the payload block
    tampered_token = f"{parts[0]}.eyJzdWIiOiAiaGFja2VyIn0.{parts[2]}"

    payload = decode_access_token(tampered_token)
    assert payload is None


def test_jwt_token_expiration():
    user_id = uuid.uuid4()
    # Create an expired token (expires in -1 minute)
    token = create_access_token(user_id=user_id, email="patient@healthcare.org", expires_in_minutes=-1)

    payload = decode_access_token(token)
    assert payload is None
