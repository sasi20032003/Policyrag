"""
Comprehensive auto-downloader for ALL top Indian health insurance policy PDFs.

Covers 10 major insurers:
  1. Niva Bupa Health Insurance
  2. Star Health Insurance
  3. HDFC ERGO Health Insurance
  4. Care Health Insurance
  5. Bajaj Allianz General Insurance
  6. ICICI Lombard General Insurance
  7. Aditya Birla Health Insurance
  8. ManipalCigna Health Insurance
  9. Tata AIG General Insurance
 10. Go Digit General Insurance

Usage:
    cd dataset
    python download_policies.py

If a URL fails (insurers sometimes move files), the script tells you
exactly where to go manually to download the updated PDF.
"""

import os
import time
import urllib.request
import urllib.error

# =============================================================================
# ALL POLICIES — 10 TOP INDIAN HEALTH INSURERS
# =============================================================================
POLICIES = [

    # =========================================================================
    # 1. NIVA BUPA HEALTH INSURANCE
    #    Download page: https://www.nivabupa.com/customer-care/download-centre.html
    # =========================================================================
    {
        "insurer":  "1_niva_bupa",
        "product":  "ReAssure 2.0",
        "version":  "V1_2022",
        "url": "https://www.nivabupa.com/Images/uploads/policywordings/ReAssure_2.0_Policy_Wording.pdf",
        "filename": "niva_bupa_reassure_v1_2022.pdf",
    },
    {
        "insurer":  "1_niva_bupa",
        "product":  "ReAssure 3.0",
        "version":  "V2_2024",
        "url": "https://www.nivabupa.com/Images/uploads/policywordings/ReAssure_3.0_Policy_Wording.pdf",
        "filename": "niva_bupa_reassure_v2_2024.pdf",
    },
    {
        "insurer":  "1_niva_bupa",
        "product":  "Health Companion",
        "version":  "V1_2022",
        "url": "https://www.nivabupa.com/Images/uploads/policywordings/Health_Companion_Policy_Wording.pdf",
        "filename": "niva_bupa_health_companion_v1_2022.pdf",
    },
    {
        "insurer":  "1_niva_bupa",
        "product":  "Aspire",
        "version":  "V1_2023",
        "url": "https://www.nivabupa.com/Images/uploads/policywordings/Aspire_Policy_Wording.pdf",
        "filename": "niva_bupa_aspire_v1_2023.pdf",
    },

    # =========================================================================
    # 2. STAR HEALTH AND ALLIED INSURANCE
    #    Download page: https://www.starhealth.in/downloads/
    # =========================================================================
    {
        "insurer":  "2_star_health",
        "product":  "Star Comprehensive",
        "version":  "V1_2023",
        "url": "https://www.starhealth.in/resources/pdf/Star-Comprehensive-Insurance-Policy-Wordings.pdf",
        "filename": "star_health_comprehensive_v1_2023.pdf",
    },
    {
        "insurer":  "2_star_health",
        "product":  "Star Family Health Optima",
        "version":  "V1_2023",
        "url": "https://www.starhealth.in/resources/pdf/Star-Family-Health-Optima-Policy-Wordings.pdf",
        "filename": "star_health_family_optima_v1_2023.pdf",
    },
    {
        "insurer":  "2_star_health",
        "product":  "Young Star",
        "version":  "V1_2023",
        "url": "https://www.starhealth.in/resources/pdf/Young-Star-Insurance-Policy-Wordings.pdf",
        "filename": "star_health_young_star_v1_2023.pdf",
    },
    {
        "insurer":  "2_star_health",
        "product":  "Star Senior Citizens Red Carpet",
        "version":  "V1_2023",
        "url": "https://www.starhealth.in/resources/pdf/Senior-Citizens-Red-Carpet-Policy-Wordings.pdf",
        "filename": "star_health_senior_citizens_v1_2023.pdf",
    },

    # =========================================================================
    # 3. HDFC ERGO GENERAL INSURANCE
    #    Download page: https://www.hdfcergo.com/customer-service/downloads/policy-wordings
    # =========================================================================
    {
        "insurer":  "3_hdfc_ergo",
        "product":  "Optima Secure",
        "version":  "V1_2023",
        "url": "https://customer-portal-assets.hdfcergo.com/policy-wordings/Optima-Secure-Policy-Wording.pdf",
        "filename": "hdfc_ergo_optima_secure_v1_2023.pdf",
    },
    {
        "insurer":  "3_hdfc_ergo",
        "product":  "Optima Restore",
        "version":  "V1_2023",
        "url": "https://customer-portal-assets.hdfcergo.com/policy-wordings/Optima-Restore-Policy-Wording.pdf",
        "filename": "hdfc_ergo_optima_restore_v1_2023.pdf",
    },
    {
        "insurer":  "3_hdfc_ergo",
        "product":  "my:health Suraksha",
        "version":  "V1_2023",
        "url": "https://customer-portal-assets.hdfcergo.com/policy-wordings/My-Health-Suraksha-Policy-Wording.pdf",
        "filename": "hdfc_ergo_myhealth_suraksha_v1_2023.pdf",
    },

    # =========================================================================
    # 4. CARE HEALTH INSURANCE (formerly Religare Health)
    #    Download page: https://www.careinsurance.com/download-center.html
    # =========================================================================
    {
        "insurer":  "4_care_health",
        "product":  "Care Supreme",
        "version":  "V1_2023",
        "url": "https://www.careinsurance.com/pdf/care-supreme-policy-wordings.pdf",
        "filename": "care_health_supreme_v1_2023.pdf",
    },
    {
        "insurer":  "4_care_health",
        "product":  "Care Advantage",
        "version":  "V1_2023",
        "url": "https://www.careinsurance.com/pdf/care-advantage-policy-wordings.pdf",
        "filename": "care_health_advantage_v1_2023.pdf",
    },
    {
        "insurer":  "4_care_health",
        "product":  "Care Classic",
        "version":  "V1_2022",
        "url": "https://www.careinsurance.com/pdf/care-classic-policy-wordings.pdf",
        "filename": "care_health_classic_v1_2022.pdf",
    },

    # =========================================================================
    # 5. BAJAJ ALLIANZ GENERAL INSURANCE
    #    Download page: https://www.bajajallianz.com/health-insurance-plans.html
    # =========================================================================
    {
        "insurer":  "5_bajaj_allianz",
        "product":  "Health Guard",
        "version":  "V1_2023",
        "url": "https://www.bajajallianz.com/content/dam/bajajallianz/pdf/health/health-guard-policy-wording.pdf",
        "filename": "bajaj_allianz_health_guard_v1_2023.pdf",
    },
    {
        "insurer":  "5_bajaj_allianz",
        "product":  "Arogya Sanjeevani",
        "version":  "V1_2023",
        "url": "https://www.bajajallianz.com/content/dam/bajajallianz/pdf/health/arogya-sanjeevani-policy-wording.pdf",
        "filename": "bajaj_allianz_arogya_sanjeevani_v1_2023.pdf",
    },
    {
        "insurer":  "5_bajaj_allianz",
        "product":  "Global Health Care",
        "version":  "V1_2023",
        "url": "https://www.bajajallianz.com/content/dam/bajajallianz/pdf/health/global-health-care-policy-wording.pdf",
        "filename": "bajaj_allianz_global_health_care_v1_2023.pdf",
    },

    # =========================================================================
    # 6. ICICI LOMBARD GENERAL INSURANCE
    #    Download page: https://www.icicilombard.com/downloads
    # =========================================================================
    {
        "insurer":  "6_icici_lombard",
        "product":  "Health Shield",
        "version":  "V1_2023",
        "url": "https://www.icicilombard.com/docs/policy-wordings/Health-Shield-Policy-Wording.pdf",
        "filename": "icici_lombard_health_shield_v1_2023.pdf",
    },
    {
        "insurer":  "6_icici_lombard",
        "product":  "Elevate",
        "version":  "V1_2024",
        "url": "https://www.icicilombard.com/docs/policy-wordings/Elevate-Policy-Wording.pdf",
        "filename": "icici_lombard_elevate_v1_2024.pdf",
    },
    {
        "insurer":  "6_icici_lombard",
        "product":  "Complete Health Insurance",
        "version":  "V1_2023",
        "url": "https://www.icicilombard.com/docs/policy-wordings/Complete-Health-Insurance-Policy-Wording.pdf",
        "filename": "icici_lombard_complete_health_v1_2023.pdf",
    },

    # =========================================================================
    # 7. ADITYA BIRLA HEALTH INSURANCE
    #    Download page: https://www.adityabirlacapital.com/healthinsurance/
    # =========================================================================
    {
        "insurer":  "7_aditya_birla",
        "product":  "Activ Health Platinum Essential",
        "version":  "V1_2023",
        "url": "https://www.adityabirlacapital.com/healthinsurance/pdf/activ-health-platinum-essential-policy-wording.pdf",
        "filename": "aditya_birla_activ_health_essential_v1_2023.pdf",
    },
    {
        "insurer":  "7_aditya_birla",
        "product":  "Activ Health Platinum Enhanced",
        "version":  "V1_2023",
        "url": "https://www.adityabirlacapital.com/healthinsurance/pdf/activ-health-platinum-enhanced-policy-wording.pdf",
        "filename": "aditya_birla_activ_health_enhanced_v1_2023.pdf",
    },
    {
        "insurer":  "7_aditya_birla",
        "product":  "Activ Assure Diamond",
        "version":  "V1_2022",
        "url": "https://www.adityabirlacapital.com/healthinsurance/pdf/activ-assure-diamond-policy-wording.pdf",
        "filename": "aditya_birla_activ_assure_diamond_v1_2022.pdf",
    },

    # =========================================================================
    # 8. MANIPALCIGNA HEALTH INSURANCE
    #    Download page: https://www.manipalcigna.com/downloads/products
    # =========================================================================
    {
        "insurer":  "8_manipalcigna",
        "product":  "ProHealth Prime",
        "version":  "V1_2023",
        "url": "https://www.manipalcigna.com/pdf/ProHealth-Prime-Policy-Wording.pdf",
        "filename": "manipalcigna_prohealth_prime_v1_2023.pdf",
    },
    {
        "insurer":  "8_manipalcigna",
        "product":  "ProHealth Select",
        "version":  "V1_2023",
        "url": "https://www.manipalcigna.com/pdf/ProHealth-Select-Policy-Wording.pdf",
        "filename": "manipalcigna_prohealth_select_v1_2023.pdf",
    },

    # =========================================================================
    # 9. TATA AIG GENERAL INSURANCE
    #    Download page: https://www.tataaig.com/downloads
    # =========================================================================
    {
        "insurer":  "9_tata_aig",
        "product":  "Medicare",
        "version":  "V1_2023",
        "url": "https://www.tataaig.com/pdf/health/tata-aig-medicare-policy-wording.pdf",
        "filename": "tata_aig_medicare_v1_2023.pdf",
    },
    {
        "insurer":  "9_tata_aig",
        "product":  "Medicare Premier",
        "version":  "V1_2023",
        "url": "https://www.tataaig.com/pdf/health/tata-aig-medicare-premier-policy-wording.pdf",
        "filename": "tata_aig_medicare_premier_v1_2023.pdf",
    },
    {
        "insurer":  "9_tata_aig",
        "product":  "Wellsurance Family",
        "version":  "V1_2023",
        "url": "https://www.tataaig.com/pdf/health/wellsurance-family-policy-wording.pdf",
        "filename": "tata_aig_wellsurance_family_v1_2023.pdf",
    },

    # =========================================================================
    # 10. GO DIGIT GENERAL INSURANCE
    #     Download page: https://www.godigit.com/health-insurance
    # =========================================================================
    {
        "insurer":  "10_go_digit",
        "product":  "Health Care Plus",
        "version":  "V1_2023",
        "url": "https://www.godigit.com/content/dam/godigit/pdf/health/digit-health-care-plus-policy-wording.pdf",
        "filename": "go_digit_health_care_plus_v1_2023.pdf",
    },
    {
        "insurer":  "10_go_digit",
        "product":  "Infinity Wallet",
        "version":  "V1_2023",
        "url": "https://www.godigit.com/content/dam/godigit/pdf/health/digit-infinity-wallet-policy-wording.pdf",
        "filename": "go_digit_infinity_wallet_v1_2023.pdf",
    },
]

# =============================================================================
# OFFICIAL DOWNLOAD PAGES (for manual download if URLs above fail)
# =============================================================================
DOWNLOAD_PAGES = {
    "1_niva_bupa":    "https://www.nivabupa.com/customer-care/download-centre.html",
    "2_star_health":  "https://www.starhealth.in/downloads/",
    "3_hdfc_ergo":    "https://www.hdfcergo.com/customer-service/downloads/policy-wordings",
    "4_care_health":  "https://www.careinsurance.com/download-center.html",
    "5_bajaj_allianz":"https://www.bajajallianz.com/health-insurance-plans.html",
    "6_icici_lombard":"https://www.icicilombard.com/downloads",
    "7_aditya_birla": "https://www.adityabirlacapital.com/healthinsurance/",
    "8_manipalcigna": "https://www.manipalcigna.com/downloads/products",
    "9_tata_aig":     "https://www.tataaig.com/downloads",
    "10_go_digit":    "https://www.godigit.com/health-insurance",
}

INSURER_DISPLAY_NAMES = {
    "1_niva_bupa":    "Niva Bupa Health Insurance",
    "2_star_health":  "Star Health and Allied Insurance",
    "3_hdfc_ergo":    "HDFC ERGO General Insurance",
    "4_care_health":  "Care Health Insurance",
    "5_bajaj_allianz":"Bajaj Allianz General Insurance",
    "6_icici_lombard":"ICICI Lombard General Insurance",
    "7_aditya_birla": "Aditya Birla Health Insurance",
    "8_manipalcigna": "ManipalCigna Health Insurance",
    "9_tata_aig":     "Tata AIG General Insurance",
    "10_go_digit":    "Go Digit General Insurance",
}


def download_pdf(url: str, dest_path: str, filename: str) -> bool:
    """Download a single PDF. Returns True on success."""
    os.makedirs(dest_path, exist_ok=True)
    out_file = os.path.join(dest_path, filename)

    if os.path.exists(out_file):
        size = os.path.getsize(out_file)
        if size > 10_000:
            print(f"    [SKIP] Already exists ({size // 1024} KB): {filename}")
            return True
        else:
            os.remove(out_file)

    print(f"    [DOWNLOAD] {filename}")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://google.com",
            },
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()

        if len(data) < 5000:
            print(f"    [WARN] Too small ({len(data)} bytes) — likely not a real PDF")
            return False

        # Verify PDF magic bytes
        if not data.startswith(b"%PDF"):
            print(f"    [WARN] Response is not a valid PDF (wrong header)")
            return False

        with open(out_file, "wb") as f:
            f.write(data)

        print(f"    [OK] Saved {len(data) // 1024} KB -> {filename}")
        return True

    except urllib.error.HTTPError as e:
        print(f"    [FAIL] HTTP {e.code} for {filename}")
        return False
    except urllib.error.URLError as e:
        print(f"    [FAIL] Network error for {filename}: {e.reason}")
        return False
    except Exception as e:
        print(f"    [FAIL] Error for {filename}: {e}")
        return False


def main():
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    raw_pdfs_dir = os.path.join(script_dir, "raw_pdfs")

    print()
    print("=" * 70)
    print("   PolicyGraph-RAG  --  Insurance Policy PDF Downloader")
    print("   10 Top Indian Health Insurers | 29 Policy Documents")
    print("=" * 70)
    print(f"   Saving to: {raw_pdfs_dir}")
    print()

    # Group by insurer
    by_insurer: dict[str, list] = {}
    for p in POLICIES:
        by_insurer.setdefault(p["insurer"], []).append(p)

    total_success, total_failed = 0, 0
    failed_by_insurer: dict[str, list] = {}

    for insurer_key, policies in by_insurer.items():
        display = INSURER_DISPLAY_NAMES.get(insurer_key, insurer_key)
        print(f"  [{insurer_key.split('_', 1)[0]}] {display}")
        print(f"  {'-' * 60}")

        insurer_dir = os.path.join(raw_pdfs_dir, insurer_key)
        insurer_failed = []

        for policy in policies:
            ok = download_pdf(policy["url"], insurer_dir, policy["filename"])
            if ok:
                total_success += 1
            else:
                total_failed += 1
                insurer_failed.append(policy)
            time.sleep(0.8)

        if insurer_failed:
            failed_by_insurer[insurer_key] = insurer_failed

        print()

    # Summary
    print("=" * 70)
    print(f"   COMPLETE: {total_success} downloaded   {total_failed} failed")
    print("=" * 70)

    if failed_by_insurer:
        print()
        print("  MANUAL DOWNLOAD REQUIRED for failed files:")
        print()
        for insurer_key, failed_list in failed_by_insurer.items():
            display = INSURER_DISPLAY_NAMES.get(insurer_key, insurer_key)
            page    = DOWNLOAD_PAGES.get(insurer_key, "")
            print(f"  {display}")
            print(f"    Download page: {page}")
            dest = os.path.join(raw_pdfs_dir, insurer_key)
            for p in failed_list:
                print(f"    Save as: {os.path.join(dest, p['filename'])}")
                print(f"    Product: {p['product']} ({p['version']})")
            print()

    print()
    print("  NEXT STEPS:")
    print("  1. Run backend:  uvicorn main:app --reload --port 8000  (from backend/)")
    print("  2. Open app:     http://localhost:3000  -> Upload page")
    print("  3. Upload PDFs:  Set Policy Name, Insurer, Version, Effective From date")
    print("  4. Ask questions: http://localhost:3000 -> Chat page")
    print()
    print("  RECOMMENDED UPLOAD PAIRS for Contradiction Detection:")
    print("    Niva Bupa ReAssure V1 (2022) vs ReAssure V2 (2024)")
    print("    HDFC ERGO Optima Secure V1 vs Optima Restore V1")
    print()


if __name__ == "__main__":
    main()
