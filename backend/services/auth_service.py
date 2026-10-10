"""
Authentication, Password Hashing, and JWT Token Service.
Zero-external-dependency, timing-attack resistant, production-grade security.

Standards:
- Password Hashing: PBKDF2-HMAC-SHA256 with 200,000 iterations & 32-byte cryptographic salt (OWASP standard).
- JWT Encoding/Decoding: RFC 7519 compliant JSON Web Token (HS256) with tamper verification.
- Row-Level Security Dependency: FastAPI dependency for user authentication & tenant isolation.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.db import get_db
from models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Default JWT secret key for development. In production, load from JWT_SECRET in .env
JWT_SECRET = os.getenv("JWT_SECRET") or "policygraph-jwt-super-secure-production-secret-2026"
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a 32-byte random salt.
    Format: 'pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>'
    """
    salt = secrets.token_bytes(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify password against stored PBKDF2 hash using constant-time comparison
    to prevent timing attacks.
    """
    if not stored_hash or not stored_hash.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        _, iter_str, salt_hex, hash_hex = parts
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(hash_hex)

        actual_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_dk, expected_dk)
    except Exception as exc:
        logger.warning("Password verification error: %s", exc)
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data_str: str) -> bytes:
    padding = "=" * ((4 - len(data_str) % 4) % 4)
    return base64.urlsafe_b64decode(data_str + padding)


def create_access_token(
    user_id: UUID,
    email: str,
    role: str = "patient",
    expires_in_minutes: int = 60,
) -> str:
    """
    Generate an RFC 7519 compliant JSON Web Token (HS256).
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + (expires_in_minutes * 60),
        "iss": "policygraph-rag",
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    """
    Verify and decode an HS256 JWT token.
    Checks signature integrity and expiration time.
    """
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("JWT signature verification failed.")
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if payload.get("exp", 0) < now:
            logger.info("JWT token has expired.")
            return None

        return payload
    except Exception as exc:
        logger.warning("Error decoding JWT token: %s", exc)
        return None


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: authenticates user via 'Authorization: Bearer <token>' header.
    Enforces tenant identity for all downstream operations.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token. Provide 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    user = await db.get(User, UUID(user_id_str))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account no longer exists.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account has been deactivated.")

    return user


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency: attempts to authenticate user if Authorization header is present,
    otherwise returns None without raising an exception.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user = await db.get(User, UUID(user_id_str))
        if user and user.is_active:
            return user
    except Exception:
        return None
    return None
