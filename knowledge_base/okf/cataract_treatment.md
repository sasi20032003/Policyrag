---
id: "okf.health.cataract_treatment"
title: "Cataract Surgery & Eye Lens Replacement Coverage"
domain: "healthcare_insurance"
version: "2026.2"
status: "canonical"
last_reviewed: "2026-06-15"
author: "Chief Medical Underwriter"
category: "Specific Ailments Waiting Period"

rules:
  standard_waiting_period_months: 24
  allows_waiver_rider: true
  waiver_rider_name: "Specific Disease Waiting Period Reduction Rider"
  sub_limit_rule: "per_eye_capped"
  default_sub_limit_inr: 40000
  lens_type_covered: "Monofocal / Standard Bifocal"
  premium_lens_copay_percent: 20
  day_care_eligible: true
  min_hospitalization_hours_required: 0

relations:
  prerequisite_clauses:
    - target: "./pre_existing_diseases.md"
      type: "subject_to"
      description: "If cataract was pre-existing before policy inception, PED waiting period takes precedence unless disclosed."
  associated_limits:
    - target: "./room_rent_capping.md"
      type: "governed_by"
      description: "Day-care bed charges apply if stay exceeds 6 hours."
  dispute_precedents:
    - target: "./statutory_irdai_guidelines.md#cataract-standardization"
      type: "mandated_by"

tags:
  - "cataract"
  - "day_care_procedure"
  - "waiting_period_24m"
  - "sub_limits"
---

# Cataract Surgery & Eye Lens Replacement Coverage

## 1. Core Rule Definition
Coverage for **Cataract Surgery** and modern robotic-assisted lens procedures is strictly categorized under **Specific Ailments**. Expenses incurred for the treatment of Cataract are **not payable** until the insured person has completed continuous coverage of **24 continuous months** under the policy from the initial inception date.

## 2. Quantitative Sub-Limits & Capping Rules
1. **Per-Eye Limit:** Reimbursement is capped at `₹40,000` (or `USD $3,500` equivalent) per eye, inclusive of:
   * Surgeon and anesthetist fees.
   * Operation theatre charges.
   * Monofocal standard intraocular lens (IOL).
2. **Multifocal / Trifocal Upgrade:**
   * If the patient selects multifocal, toric, or trifocal advanced lenses, the policy covers the monofocal baseline cost; the remaining delta is subject to a **20% co-payment**.

## 3. Override Exceptions & Riders
* **Reduction Rider Active:** If the policy schedule lists the `Specific Disease Waiting Period Reduction Rider`, the waiting period is reduced from **24 months to 90 days**.
* **Accidental Cataract:** Traumatic cataract resulting directly from an external violent accident is **exempt** from the 24-month waiting period and falls under immediate emergency coverage.

## 4. Verification Checkpoints for AI Agents
When adjudicating claims or answering insured inquiries:
1. Verify if the policy age is $\ge 24$ continuous months.
2. Check policy schedule for the `Reduction Rider`.
3. Check hospital billing for lens classification (monofocal vs premium).
