# Open Knowledge Format (OKF) Knowledge Base

This directory follows the **Open Knowledge Format (OKF)** specification (introduced mid-2026). It serves as the deterministic, canonical ontology for the `PolicyGraph-RAG` system.

## Directory Structure

```
knowledge_base/okf/
├── README.md                     # OKF specifications and guidelines
├── cataract_treatment.md         # Concept: Cataract surgery rules & limits
└── pre_existing_diseases.md      # Concept: Pre-existing disease (PED) rules
```

## Anatomy of an OKF File

Every file in an OKF repository is a standalone Markdown document structured in two parts:

### 1. YAML Frontmatter (`---`)
Defines machine-readable, deterministic properties, rules, and cross-document graph links:

```yaml
---
id: "okf.health.cataract_treatment"
title: "Cataract Surgery & Eye Lens Replacement Coverage"
domain: "healthcare_insurance"
version: "2026.2"
status: "canonical"
category: "Specific Ailments Waiting Period"

rules:
  standard_waiting_period_months: 24
  allows_waiver_rider: true
  sub_limit_rule: "per_eye_capped"
  default_sub_limit_inr: 40000

relations:
  prerequisite_clauses:
    - target: "./pre_existing_diseases.md"
      type: "subject_to"
---
```

### 2. Markdown Body
Contains the human- and LLM-readable authoritative explanation, calculation logic, edge cases, and verification checkpoints.

## OKF vs RAG in this Project

* **OKF Files** act as the **ground-truth rulebook** (waiting periods, statutory definitions, co-pay schemas).
* **RAG Pipeline** extracts **evidence and page-level citations** from raw insurance policy PDFs in `dataset/raw_pdfs/`.
