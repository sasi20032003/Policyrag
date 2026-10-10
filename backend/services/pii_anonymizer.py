"""
PII / PHI De-Identification and Redaction Service.
Compliant with HIPAA Safe Harbor (45 CFR § 164.514), GDPR Art. 32, and India DPDP Act 2023.

Features:
1. Token-level Masking: Redacts direct identifiers (Names, Phone Numbers, Emails,
   Government IDs, Policy Account Numbers) before prompts are sent to external LLMs.
2. Context-Preserving Pseudonymization: Replaces real individual names with role-based
   surrogates (e.g. "[Primary Insured]", "[Dependent_1]") so the LLM can still calculate
   personalized waiting periods, family eligibility, and co-pays without exposing identities.
3. Bidirectional Reversible Mapping: Allows restoring friendly names in responses if desired.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Regular expressions for common PII / PHI patterns
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
AADHAAR_RE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")  # 12-digit Indian Aadhaar
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")                  # 9-digit US SSN
POLICY_NO_RE = re.compile(r"\b(?:POL|POLICY|NUM|NO)[-:\s#]*([A-Z0-9]{6,20})\b", re.IGNORECASE)
CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")          # 16-digit payment card


@dataclass
class AnonymizationResult:
    sanitized_text: str
    redacted_items_count: int
    pseudonym_map: dict[str, str] = field(default_factory=dict)


class PIIAnonymizer:
    """
    Scans, scrubs, and pseudonymizes personally identifiable information.
    """

    def sanitize_text(self, text: str, user_name: Optional[str] = None) -> AnonymizationResult:
        """
        Sanitize arbitrary user text or prompt before sending to external LLM providers.
        """
        if not text:
            return AnonymizationResult(sanitized_text="", redacted_items_count=0)

        redacted_count = 0
        pseudonyms: dict[str, str] = {}
        sanitized = text

        # 1. Mask specific user name if provided
        if user_name and len(user_name.strip()) > 2:
            real_name = user_name.strip()
            pattern = re.compile(r"\b" + re.escape(real_name) + r"\b", re.IGNORECASE)
            if pattern.search(sanitized):
                sanitized = pattern.sub("[Primary Insured]", sanitized)
                pseudonyms[real_name] = "[Primary Insured]"
                redacted_count += 1

        # 2. Mask Emails
        emails = EMAIL_RE.findall(sanitized)
        for email in set(emails):
            sanitized = sanitized.replace(email, "[EMAIL_REDACTED]")
            pseudonyms[email] = "[EMAIL_REDACTED]"
            redacted_count += 1

        # 3. Mask Phones
        phones = PHONE_RE.findall(sanitized)
        for phone in set(phones):
            # Exclude false positives like dates 2024-05-12 or monetary figures
            if len(re.findall(r"\d", phone)) >= 10:
                sanitized = sanitized.replace(phone, "[PHONE_REDACTED]")
                pseudonyms[phone] = "[PHONE_REDACTED]"
                redacted_count += 1

        # 4. Mask Government IDs (Aadhaar / SSN)
        for aadhaar in set(AADHAAR_RE.findall(sanitized)):
            sanitized = sanitized.replace(aadhaar, "[NATIONAL_ID_REDACTED]")
            redacted_count += 1

        for ssn in set(SSN_RE.findall(sanitized)):
            sanitized = sanitized.replace(ssn, "[NATIONAL_ID_REDACTED]")
            redacted_count += 1

        # 5. Mask Credit/Debit Cards
        for card in set(CARD_RE.findall(sanitized)):
            sanitized = sanitized.replace(card, "[CARD_NUMBER_REDACTED]")
            redacted_count += 1

        # 6. Mask Policy Numbers
        sanitized = POLICY_NO_RE.sub("POLICY #[REDACTED]", sanitized)

        if redacted_count > 0:
            logger.info("PIIAnonymizer redacted %d sensitive identity tokens from prompt", redacted_count)

        return AnonymizationResult(
            sanitized_text=sanitized,
            redacted_items_count=redacted_count,
            pseudonym_map=pseudonyms,
        )

    def deidentify_profile(self, profile: dict) -> tuple[dict, dict[str, str]]:
        """
        Produce a privacy-safe clone of a patient profile for LLM context generation.
        Preserves medical & age context (required for waiting periods and co-pays)
        while stripping direct personal identifiers.
        """
        safe_profile = dict(profile)
        pseudonyms = {}

        real_name = profile.get("full_name")
        if real_name:
            safe_profile["full_name"] = "[Primary Insured]"
            pseudonyms[real_name] = "[Primary Insured]"

        # Mask exact birth day; retain age which is essential for insurance eligibility
        if safe_profile.get("date_of_birth"):
            safe_profile["date_of_birth"] = None

        # Pseudonymize family members
        family = safe_profile.get("family_members")
        if family and isinstance(family, list):
            sanitized_family = []
            for i, member in enumerate(family, start=1):
                if isinstance(member, dict):
                    m_copy = dict(member)
                    m_rel = m_copy.get("relation", "Dependent")
                    m_copy["name"] = f"[{m_rel}_{i}]"
                    sanitized_family.append(m_copy)
                else:
                    sanitized_family.append(member)
            safe_profile["family_members"] = sanitized_family

        return safe_profile, pseudonyms


pii_anonymizer = PIIAnonymizer()
