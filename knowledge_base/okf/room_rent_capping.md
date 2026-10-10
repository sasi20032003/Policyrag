---
id: "okf.health.room_rent_capping"
title: "Hospital Room Rent & ICU Capping with Proportionate Deductions"
domain: "healthcare_insurance"
version: "2026.2"
status: "canonical"
last_reviewed: "2026-06-20"
author: "Chief Medical Underwriter"
category: "Sub-Limits & Cost Sharing"

rules:
  standard_room_rent_cap_percent_of_si: 1.0
  icu_cap_percent_of_si: 2.0
  allows_single_private_room: true
  proportionate_deduction_applies: true
  exempted_associated_medical_expenses:
    - "cost_of_pharmacy_and_medicines"
    - "implants_and_stents"
    - "consumables"

relations:
  governs:
    - target: "./cataract_treatment.md"
      type: "constrains"
    - target: "./maternity_coverage.md"
      type: "constrains"

tags:
  - "room_rent"
  - "icu_charges"
  - "proportionate_deduction"
  - "sub_limits"
---

# Hospital Room Rent & ICU Capping with Proportionate Deductions

## 1. Room Category Limits
1. **Normal Room Rent:** Limited to **1% of Sum Insured per day**, or a Single Private AC Room (whichever is lower, unless no room capping is specified in the policy schedule).
2. **ICU Charges:** Limited to **2% of Sum Insured per day**.

## 2. Proportionate Deduction Penalty
If an insured person occupies a room category higher than their eligible tariff:
* All associated medical expenses (surgeon fees, doctor visits, nursing, operating theatre charges) will be reduced in direct proportion to the room tariff differential:
  $$\text{Payable Ratio} = \frac{\text{Eligible Room Tariff}}{\text{Actual Room Rent Charged}}$$
* **Statutory Exception:** Fixed-cost consumables, medicines, and medical implants (stents, mesh, orthopaedic plates) are **exempt** from proportionate deduction.
