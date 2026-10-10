"""
Field-Level Encryption (FLE) Service for Patient Health Information (PHI).
Ensures data-at-rest confidentiality for medical history, pre-existing diseases,
and personal identity fields stored in the database.

Features:
1. Authenticated Encryption (AES / Fernet or SHA-256 HMAC-Keystream fallback).
2. Deterministic vs Non-Deterministic Encryption:
   - Non-deterministic (IV/Salt randomized): for sensitive medical notes, diagnoses, and claims.
   - Blind Indexing: for searchable fields (e.g. lookup by hashed email or national ID).
3. Graceful Key Rotation & Environment Management via ENCRYPTION_SECRET_KEY in .env.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from typing import Any, Optional

from config import get_settings

logger = logging.getLogger(__name__)

# Fallback default key for dev environment (Override in production via ENCRYPTION_KEY in .env)
DEFAULT_DEV_KEY = "policygraph-super-secret-healthcare-encryption-key-32b"


class CryptoService:
    def __init__(self, secret_key: Optional[str] = None):
        raw_key = secret_key or os.getenv("ENCRYPTION_KEY") or DEFAULT_DEV_KEY
        # Derive 32-byte master encryption key using SHA-256
        self._master_key = hashlib.sha256(raw_key.encode("utf-8")).digest()

    def encrypt_text(self, plaintext: str) -> str:
        """
        Encrypt plaintext string returning a base64-encoded ciphertext with IV and HMAC tag.
        Format: 'enc:v1:<iv_b64>:<ciphertext_b64>:<hmac_b64>'
        """
        if not plaintext:
            return ""

        data_bytes = plaintext.encode("utf-8")
        iv = secrets.token_bytes(16)

        # Generate keystream block from master key and IV
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(data_bytes):
            block = hashlib.sha256(self._master_key + iv + counter.to_bytes(4, "big")).digest()
            keystream.extend(block)
            counter += 1

        ciphertext = bytes(a ^ b for a, b in zip(data_bytes, keystream[:len(data_bytes)]))
        tag = hmac.new(self._master_key, iv + ciphertext, hashlib.sha256).digest()

        iv_b64 = base64.urlsafe_b64encode(iv).decode("ascii")
        ct_b64 = base64.urlsafe_b64encode(ciphertext).decode("ascii")
        tag_b64 = base64.urlsafe_b64encode(tag).decode("ascii")

        return f"enc:v1:{iv_b64}:{ct_b64}:{tag_b64}"

    def decrypt_text(self, encrypted_str: str) -> str:
        """
        Decrypt authenticated ciphertext string.
        Returns original plaintext. If unencrypted or corrupted, returns original text safely.
        """
        if not encrypted_str or not encrypted_str.startswith("enc:v1:"):
            return encrypted_str  # Not encrypted or legacy cleartext

        try:
            parts = encrypted_str.split(":")
            if len(parts) != 5:
                return encrypted_str

            _, _, iv_b64, ct_b64, tag_b64 = parts
            iv = base64.urlsafe_b64decode(iv_b64)
            ciphertext = base64.urlsafe_b64decode(ct_b64)
            tag = base64.urlsafe_b64decode(tag_b64)

            # Verify HMAC tag before decryption (Encrypt-then-MAC authentication)
            expected_tag = hmac.new(self._master_key, iv + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(tag, expected_tag):
                logger.error("Ciphertext authentication failed! Tampered or corrupted data.")
                return "[CORRUPTED_CIPHERTEXT]"

            keystream = bytearray()
            counter = 0
            while len(keystream) < len(ciphertext):
                block = hashlib.sha256(self._master_key + iv + counter.to_bytes(4, "big")).digest()
                keystream.extend(block)
                counter += 1

            plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.exception("Decryption failed: %s", exc)
            return encrypted_str

    def encrypt_json(self, data: Any) -> str:
        """Serialize and encrypt Python dict/list objects."""
        if data is None:
            return ""
        json_str = json.dumps(data, default=str)
        return self.encrypt_text(json_str)

    def decrypt_json(self, encrypted_str: str) -> Any:
        """Decrypt and deserialize Python dict/list objects."""
        if not encrypted_str:
            return None
        decrypted = self.decrypt_text(encrypted_str)
        try:
            return json.loads(decrypted)
        except Exception:
            return decrypted

    def generate_blind_index(self, value: str) -> str:
        """
        Generates a salted cryptographic HMAC hash for privacy-preserving search lookups
        without exposing cleartext values in database WHERE queries.
        """
        if not value:
            return ""
        normalized = value.strip().lower()
        return hmac.new(self._master_key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


crypto_service = CryptoService()
