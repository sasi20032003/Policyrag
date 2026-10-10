---
id: "okf.health.pre_existing_diseases"
title: "Pre-Existing Diseases (PED) & Waiting Periods"
domain: "healthcare_insurance"
version: "2026.2"
status: "canonical"
last_reviewed: "2026-06-15"
author: "Chief Medical Underwriter"
category: "Statutory Waiting Periods"

rules:
  statutory_max_waiting_period_months: 36
  standard_ped_waiting_period_months: 36
  disclosure_moratorium_years: 5
  portability_credit_allowed: true

relations:
  overrides:
    - target: "./cataract_treatment.md"
      type: "parent_condition"
      description: "Applies if eye disease was diagnosed prior to policy inception."
  statutory_reference:
    - target: "./statutory_irdai_guidelines.md#ped-moratorium"
      type: "regulated_by"

tags:
  - "pre_existing_disease"
  - "ped"
  - "waiting_period"
  - "disclosure"
---

# Pre-Existing Diseases (PED) & Waiting Periods

## 1. Statutory Definition
A **Pre-Existing Disease (PED)** means any condition, ailment, injury or disease:
1. That is diagnosed by a physician within **36 months** prior to the effective date of the policy, OR
2. For which medical advice or treatment was recommended by, or received from, a physician within **36 months** prior to the effective date.

## 2. Moratorium & Claims Admissibility
* After **5 continuous years (60 months)** of policy renewal, no health insurance claim can be contested on grounds of non-disclosure, except in proven cases of established fraud.
