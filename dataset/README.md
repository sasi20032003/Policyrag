# Dataset — Health Insurance Policy PDFs

This folder contains real healthcare insurance policy PDFs used to power the PolicyGraph-RAG system.

## Folder Structure

```
dataset/
├── raw_pdfs/                    ← Place all downloaded PDFs here
│   ├── niva_bupa/
│   │   ├── reassure_v1_2023.pdf
│   │   ├── reassure_v2_2024.pdf
│   │   └── health_companion_2023.pdf
│   ├── hdfc_ergo/
│   │   ├── optima_secure_v1_2023.pdf
│   │   └── optima_secure_v2_2024.pdf
│   └── star_health/
│       ├── comprehensive_v1_2023.pdf
│       └── comprehensive_v2_2024.pdf
├── download_policies.py         ← Auto-downloader script
└── README.md                    ← This file
```

## How to Get the PDFs

### Option A — Run the Auto-Downloader (Recommended)
```bash
cd dataset
python download_policies.py
```
This script will download all publicly available policy PDFs automatically.

### Option B — Manual Download from Official Websites

#### 🔵 Niva Bupa
- Download Center: https://www.nivabupa.com/customer-care/download-centre.html
- Products: ReAssure 2.0, ReAssure 3.0, Health Companion, Aspire, Health+

#### 🟠 HDFC ERGO
- Policy Wordings: https://www.hdfcergo.com/customer-service/downloads/policy-wordings
- Products: Optima Secure, Optima Restore, my:health Suraksha

#### 🔴 Star Health
- Downloads: https://www.starhealth.in/downloads/
- Products: Star Comprehensive, Star Family Health Optima, Young Star

#### 🟢 Care Health (formerly Religare)
- Downloads: https://www.careinsurance.com/downloads
- Products: Care Supreme, Care Advantage

#### 🟣 Bajaj Allianz
- Downloads: https://www.bajajallianz.com/health-insurance-plans.html
- Products: Health Guard, Global Health Care

## Naming Convention (Important!)

Name your files clearly so you can track versions:

```
{insurer}_{product}_{version}_{year}.pdf

Examples:
  niva_bupa_reassure_v1_2023.pdf
  niva_bupa_reassure_v2_2024.pdf
  hdfc_ergo_optima_secure_v1_2023.pdf
  star_health_comprehensive_v1_2023.pdf
```

## How to Upload to the App

Once you have PDFs in this folder, upload them via the web UI:

1. Open http://localhost:3000 → **Upload** page
2. Fill the form:
   - **Policy Name**: e.g., "Niva Bupa ReAssure"
   - **Insurer**: e.g., "Niva Bupa"
   - **Version**: e.g., "V1" or "2023"
   - **Effective From**: 2023-01-01
   - **Effective Until**: 2023-12-31  ← (leave blank if current)
3. Select the PDF file
4. Click **Upload**
5. Wait ~30 seconds for processing (watch status change to "ready")
6. Repeat for V2 (same Policy Name + Insurer, different version + dates)

## Recommended Test Dataset (2 versions for contradiction detection)

| Upload | Policy Name | Insurer | Version | Effective From | Effective Until |
|--------|-------------|---------|---------|----------------|-----------------|
| 1st    | Niva Bupa ReAssure | Niva Bupa | V1 | 2023-01-01 | 2023-12-31 |
| 2nd    | Niva Bupa ReAssure | Niva Bupa | V2 | 2024-01-01 | (blank) |

Then use **Compare** to see what changed between V1 and V2!

## Sample Questions to Ask After Upload

- "What is the room rent limit per day?"
- "Is maternity covered? What is the waiting period?"
- "What are the pre-existing disease exclusions?"
- "What is the maximum sum insured available?"
- "Are day care procedures covered?"
- "What is the no-claim bonus percentage?"
