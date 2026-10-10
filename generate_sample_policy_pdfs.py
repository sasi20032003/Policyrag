"""
Generate Realistic Sample Health Insurance Policy PDFs for PolicyGraph-RAG.
Uses PyMuPDF (fitz) to create valid, extractable PDF contracts with statutory clauses:
- Star Health Comprehensive Insurance (2022 v1 & 2024 v2)
- HDFC ERGO Optima Secure (2023 v1)
- Care Health Insurance (2023 v1)
"""

import os
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "dataset" / "raw_pdfs"

def create_pdf(filepath: Path, title: str, pages_content: list[tuple[str, str]]):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    for page_num, (header, text) in enumerate(pages_content, start=1):
        page = doc.new_page(width=595, height=842) # A4 size

        # Header banner text
        header_text = f"{title.upper()} | PAGE {page_num}\n" + ("=" * 60)
        page.insert_text(fitz.Point(50, 50), header_text, fontsize=10, fontname="helv", color=(0.1, 0.2, 0.4))

        # Section title
        page.insert_text(fitz.Point(50, 90), header, fontsize=16, fontname="hebo", color=(0.1, 0.3, 0.6))

        # Body text (wrapped in a rect)
        rect = fitz.Rect(50, 120, 545, 780)
        page.insert_textbox(rect, text, fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1), lineheight=1.4)

    doc.save(str(filepath))
    doc.close()
    print(f"✅ Generated: {filepath.relative_to(PROJECT_ROOT)} ({len(pages_content)} pages)")

def main():
    print("=" * 70)
    print("  POLICYGRAPH-RAG: GENERATING SAMPLE POLICY DATASETS (PDFs)")
    print("=" * 70)

    # 1. Star Health Comprehensive Version 1 (2022)
    star_v1_pages = [
        (
            "Section 1: Policy Schedule & Coverage Scope",
            "STAR HEALTH AND ALLIED INSURANCE COMPANY LIMITED\n"
            "Product: Star Comprehensive Insurance Policy (Policy Wording Version 1.0 - Effective Jan 2022)\n\n"
            "1.1 In-Patient Hospitalisation Coverage:\n"
            "The Company shall indemnify the Insured Person for medical expenses incurred in respect of hospitalisation for a minimum period of 24 consecutive hours.\n\n"
            "1.2 Room Rent, Boarding and Nursing Expenses:\n"
            "Room Rent expenses are covered up to a maximum limit of 1% of the Sum Insured per day for standard private rooms.\n"
            "Intensive Care Unit (ICU) charges are capped at 2% of the Sum Insured per day.\n"
            "Proportionate Deduction Clause: If the Insured occupies a room with a tariff higher than the eligible limit, all associated medical expenses including surgeon fees, OT charges, and specialist consultations shall be proportionately deducted."
        ),
        (
            "Section 2: Waiting Periods & Specific Ailments",
            "2.1 Initial Waiting Period:\n"
            "A waiting period of 30 days from the policy inception date applies to all illnesses, except accidental injuries which are covered from day one.\n\n"
            "2.2 Specific Diseases Waiting Period (24 Months):\n"
            "A mandatory continuous waiting period of 24 months applies to Cataract, Hernia, Hydrocele, Congenital internal disease, and Joint Replacement surgeries.\n\n"
            "2.3 Cataract Treatment Sub-Limit (Clause 2.3):\n"
            "Expenses incurred for treatment of Cataract are subject to a maximum ceiling of Rs. 25,000 per eye or 10% of the Sum Insured, whichever is lower.\n\n"
            "2.4 Pre-Existing Disease (PED) Waiting Period:\n"
            "Pre-existing diseases declared at inception are covered after 36 months of continuous coverage without break."
        ),
        (
            "Section 3: Maternity & Newborn Benefits",
            "3.1 Normal & Caesarean Delivery:\n"
            "Medical expenses for childbirth including Caesarean section are covered up to Rs. 30,000 for normal delivery and Rs. 50,000 for Caesarean delivery.\n"
            "A continuous waiting period of 24 continuous months applies under this policy.\n\n"
            "3.2 Co-Payment Clause:\n"
            "No co-payment applies for insured persons aged below 60 years. For insured persons entering the policy at age 61 or above, a mandatory co-payment of 10% applies to every admissible claim."
        )
    ]
    create_pdf(DATASET_DIR / "star_health" / "star_health_comprehensive_v1_2022.pdf", "Star Health Comprehensive (2022)", star_v1_pages)

    # 2. Star Health Comprehensive Version 2 (2024 Renewal - Changed terms!)
    star_v2_pages = [
        (
            "Section 1: Policy Schedule & Upgraded Room Rent",
            "STAR HEALTH AND ALLIED INSURANCE COMPANY LIMITED\n"
            "Product: Star Comprehensive Insurance Policy (Policy Wording Version 2.0 - Effective Jan 2024)\n\n"
            "1.1 In-Patient Hospitalisation:\n"
            "Medical expenses covered for treatment upon admission exceeding 24 consecutive hours.\n\n"
            "1.2 Upgraded Room Rent Terms (2024 Revised):\n"
            "Single Private A/C Room is covered with NO monetary percentage capping for Sum Insured of Rs. 5 Lakhs and above.\n"
            "Proportionate deduction will NOT apply if the insured stays in an eligible Single Private A/C room.\n"
            "ICU charges are covered at actual incurred expenses without daily sub-limits."
        ),
        (
            "Section 2: Revised Sub-Limits & Cataract Terms",
            "2.1 Waiting Periods:\n"
            "Initial 30 days waiting period applies for non-accidental hospitalisation.\n\n"
            "2.2 Revised Cataract Treatment Sub-Limit (2024 Clause 2.3):\n"
            "Expenses incurred for treatment of Cataract are upgraded to a higher limit of Rs. 40,000 per eye, subject to a 24-month waiting period.\n\n"
            "2.3 Pre-Existing Disease (PED) Waiting Period (Reduced to 24 Months):\n"
            "As per revised 2024 IRDAI guidelines, the waiting period for pre-existing medical conditions is reduced from 36 months to 24 continuous months."
        ),
        (
            "Section 3: Maternity & Senior Co-Payment Addition",
            "3.1 Maternity Benefit:\n"
            "Maternity expenses covered up to Rs. 40,000 for normal delivery and Rs. 60,000 for Caesarean section after 24 continuous months of policy tenure.\n\n"
            "3.2 Senior Citizen Co-Payment Revision (Clause 3.2):\n"
            "Notice of Amendment: For all insured individuals aged 65 years and above, a revised mandatory co-payment of 15% shall apply to each and every claim admissible under the policy."
        )
    ]
    create_pdf(DATASET_DIR / "star_health" / "star_health_comprehensive_v2_2024.pdf", "Star Health Comprehensive (2024)", star_v2_pages)

    # 3. HDFC ERGO Optima Secure (2023)
    hdfc_pages = [
        (
            "Section 1: Optima Secure Coverage & 2X Secure Benefit",
            "HDFC ERGO GENERAL INSURANCE COMPANY LIMITED\n"
            "Product: Optima Secure Policy Wording (Version 1.0 - Effective 2023)\n\n"
            "1.1 Base Cover & 2X Secure Benefit:\n"
            "From day 1, the available coverage is automatically doubled (2X of Base Sum Insured) without any extra premium.\n\n"
            "1.2 Room Rent:\n"
            "Any room category up to Single Private Room is covered without proportionate deduction penalties."
        ),
        (
            "Section 2: Waiting Periods & Specific Sub-Limits",
            "2.1 Waiting Periods:\n"
            "30 days initial waiting period. 24 months specific illness waiting period for Cataract, Hernia, and Gall bladder stones.\n"
            "Cataract surgery is capped at Rs. 50,000 per eye or actuals, whichever is lower.\n\n"
            "2.2 Pre-Existing Diseases:\n"
            "Covered after 36 continuous policy months."
        )
    ]
    create_pdf(DATASET_DIR / "hdfc_ergo" / "hdfc_ergo_optima_secure_v1_2023.pdf", "HDFC ERGO Optima Secure (2023)", hdfc_pages)

    print("\n🎉 Sample Policy Dataset generation complete!")
    print("Files created in: dataset/raw_pdfs/")

if __name__ == "__main__":
    main()
