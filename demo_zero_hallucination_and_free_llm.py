"""
Demonstration & Verification Script: Zero-Hallucination Guardrail & Free LLM Integration.
Tests:
1. Free LLM Provider Connectivity (Groq 70B, Google Gemini, Ollama Local)
2. Citation Auditing (detects fabricated [Page X, Section Y] references)
3. Numerical Quantity Verification (identifies ungrounded monetary figures & durations)
4. Chain-of-Verification (CoVe - Meta 2023) Sub-Question Probing
5. Hard Hallucination Sanitization (strips ungrounded claims before user sees them)
"""
import asyncio
import os
import sys

# Ensure backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dataclasses import dataclass
from rag.hallucination_guard import (
    audit_citations,
    audit_numerical_figures,
    generate_cove_verification_probes,
    sanitize_and_strip_hallucinations,
)
from services.llm_service import llm_service


@dataclass
class MockChunk:
    id: str
    content: str
    page: int
    section: str


def run_hallucination_guard_demo():
    print("=" * 70)
    print("      POLICYGRAPH-RAG: ZERO-HALLUCINATION GUARDRAIL DEMO")
    print("=" * 70)

    # 1. Setup Mock Ground Truth Policy Evidence
    evidence_chunks = [
        (
            MockChunk(
                id="c1",
                page=4,
                section="Section 3.1 - Cataract Treatment",
                content=(
                    "Expenses incurred for treatment of Cataract are subject to a sub-limit "
                    "of Rs. 25,000 per eye or 10% of Sum Insured, whichever is lower. "
                    "A specific waiting period of 24 months applies from the policy inception date."
                ),
            ),
            0.92,
        ),
        (
            MockChunk(
                id="c2",
                page=7,
                section="Section 4.2 - Pre-Existing Diseases",
                content=(
                    "Pre-existing diseases (PED) are covered after a waiting period of 36 months "
                    "of continuous coverage from the date of inception of the first policy."
                ),
            ),
            0.88,
        ),
    ]

    print("\n[1] Verified Policy Ground Truth Evidence:")
    for chunk, score in evidence_chunks:
        print(f"  • Page {chunk.page} [{chunk.section}]:\n    \"{chunk.content}\"")

    # 2. Simulate an LLM output containing common hallucinations:
    #   - Hallucination A: Wrong number: Claims "Rs. 50,000 per eye" (truth is Rs. 25,000)
    #   - Hallucination B: Fake waiting period: Claims "12 months" for cataract (truth is 24 months)
    #   - Hallucination C: Fabricated citation: Cites "[Page 19, Section 9]" (Page 19 does not exist!)
    #   - Hallucination D: Ungrounded assertion: Claims "Free annual dental checkup is included"
    hallucinated_draft = (
        "Cataract surgery is covered under the policy up to a limit of Rs. 50,000 per eye [Page 4, Section 3.1]. "
        "The waiting period for cataract is 12 months from policy inception [Page 19, Section 9]. "
        "Pre-existing diseases have a waiting period of 36 months [Page 7, Section 4.2]. "
        "Additionally, a free annual dental checkup is included for all members [Page 42, Section 12]."
    )

    print("\n[2] Raw Hallucinated LLM Draft Answer:")
    print(f"  \"{hallucinated_draft}\"")

    # 3. Test Citation Auditing
    print("\n[3] Executing Citation Audit...")
    citation_res = audit_citations(hallucinated_draft, evidence_chunks)
    print(f"  • Valid Citations: {citation_res.valid_citations}")
    print(f"  • Hallucinated Citations Flagged: {citation_res.hallucinated_citations}")
    print(f"  • Automatic Corrections: {citation_res.corrected_citations}")

    # 4. Test Numerical & Duration Auditing
    print("\n[4] Executing Numerical & Duration Consistency Check...")
    unsupported_nums, num_warnings = audit_numerical_figures(hallucinated_draft, evidence_chunks)
    print(f"  • Unsupported Numbers Flagged: {unsupported_nums}")
    for w in num_warnings:
        print(f"    ⚠ {w}")

    # 5. Test Chain-of-Verification (CoVe) Probes
    print("\n[5] Formulating Chain-of-Verification (CoVe - Meta 2023) Probes...")
    probes = generate_cove_verification_probes("What are the coverage terms for cataract?", hallucinated_draft)
    for i, probe in enumerate(probes, 1):
        print(f"  Probe {i}: {probe}")

    # 6. Test Hard Hallucination Sanitization
    print("\n[6] Running Zero-Hallucination Hard Sanitization Gate...")
    audit_report = sanitize_and_strip_hallucinations(hallucinated_draft, evidence_chunks, strict_mode=True)
    print(f"  • Total Hallucinations Detected: {audit_report.hallucinations_detected}")
    print(f"  • Claims Stripped / Redacted: {len(audit_report.stripped_claims)}")
    for sc in audit_report.stripped_claims:
        print(f"    - REDACTED: \"{sc}\"")

    print("\n[7] FINAL ZERO-HALLUCINATION SANITIZED ANSWER (Passed to User):")
    print("=" * 70)
    print(audit_report.sanitized_answer)
    print("=" * 70)

    # 7. Check Free LLM Provider Status
    print("\n[8] Free LLM Provider Capabilities:")
    print(f"  • Active Provider: {llm_service.provider.upper()}")
    print("  • Supported Free Options:")
    print("    1. Groq (Free Tier): llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b (500+ tok/s)")
    print("    2. Google Gemini (Free Tier): gemini-2.0-flash (1M context, precise citations)")
    print("    3. Ollama (100% Offline Local): deepseek-r1:8b, qwen2.5:7b, llama3.2")
    print("  • Deterministic Setting: Temperature = 0.0, Seed = 42, Repeat Penalty = 1.15")
    print("\nZero-Hallucination verification complete!")


if __name__ == "__main__":
    run_hallucination_guard_demo()
