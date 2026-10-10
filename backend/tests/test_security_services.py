"""Unit tests for PII/PHI Anonymization and Field-Level Encryption services."""
from services.crypto_service import CryptoService, crypto_service
from services.pii_anonymizer import PIIAnonymizer, pii_anonymizer


def test_pii_anonymizer_masks_direct_identifiers():
    text = (
        "My name is Rahul Sharma. Email is rahul@example.com, phone 9876543210. "
        "My Aadhaar is 1234 5678 9012 and policy is POL-12345678."
    )
    res = pii_anonymizer.sanitize_text(text, user_name="Rahul Sharma")

    assert "[Primary Insured]" in res.sanitized_text
    assert "Rahul Sharma" not in res.sanitized_text
    assert "[EMAIL_REDACTED]" in res.sanitized_text
    assert "rahul@example.com" not in res.sanitized_text
    assert "[PHONE_REDACTED]" in res.sanitized_text
    assert "9876543210" not in res.sanitized_text
    assert "[NATIONAL_ID_REDACTED]" in res.sanitized_text
    assert "1234 5678 9012" not in res.sanitized_text
    assert "POL-12345678" not in res.sanitized_text
    assert res.redacted_items_count >= 4


def test_pii_anonymizer_deidentify_profile():
    profile = {
        "full_name": "Priya Patel",
        "age": 42,
        "date_of_birth": "1982-04-15",
        "pre_existing_diseases": ["Hypertension", "Type 2 Diabetes"],
        "family_members": [{"name": "Aarav Patel", "relation": "Son", "age": 12}],
    }
    safe_profile, pseudonyms = pii_anonymizer.deidentify_profile(profile)

    assert safe_profile["full_name"] == "[Primary Insured]"
    assert safe_profile["date_of_birth"] is None
    assert safe_profile["age"] == 42  # Retained for insurance waiting period / copay calculations
    assert safe_profile["pre_existing_diseases"] == ["Hypertension", "Type 2 Diabetes"]
    assert safe_profile["family_members"][0]["name"] == "[Son_1]"


def test_crypto_service_encrypt_decrypt_roundtrip():
    cs = CryptoService(secret_key="test-key-32-bytes-long-for-aes256")
    plaintext = "Patient diagnosed with stage 1 hypertension in 2021."

    ciphertext = cs.encrypt_text(plaintext)
    assert ciphertext.startswith("enc:v1:")
    assert plaintext not in ciphertext

    decrypted = cs.decrypt_text(ciphertext)
    assert decrypted == plaintext


def test_crypto_service_detects_tampered_ciphertext():
    cs = CryptoService(secret_key="test-key-32-bytes-long-for-aes256")
    ciphertext = cs.encrypt_text("Confidential health record.")

    # Tamper with the ciphertext payload
    parts = ciphertext.split(":")
    tampered_parts = list(parts)
    tampered_parts[3] = tampered_parts[3][:-2] + "AA"  # Corrupt ciphertext bytes
    tampered_ciphertext = ":".join(tampered_parts)

    res = cs.decrypt_text(tampered_ciphertext)
    assert res == "[CORRUPTED_CIPHERTEXT]"


def test_crypto_service_json_roundtrip():
    data = {
        "conditions": ["Asthma"],
        "medications": ["Inhaler"],
        "claim_amount": 35000,
    }
    enc = crypto_service.encrypt_json(data)
    assert isinstance(enc, str)
    assert "Asthma" not in enc

    dec = crypto_service.decrypt_json(enc)
    assert dec == data


def test_crypto_service_blind_index():
    cs = CryptoService(secret_key="test-key-32-bytes-long-for-aes256")
    idx1 = cs.generate_blind_index("user@hospital.com")
    idx2 = cs.generate_blind_index("USER@HOSPITAL.COM")
    idx3 = cs.generate_blind_index("other@hospital.com")

    assert idx1 == idx2  # Case-insensitive deterministic search lookup
    assert idx1 != idx3
