---
id: "okf.health.maternity_coverage"
title: "Maternity Expenses & New Born Baby Coverage"
domain: "healthcare_insurance"
version: "2026.2"
status: "canonical"
last_reviewed: "2026-06-18"
author: "Chief Medical Underwriter"
category: "Specialized Benefit"

rules:
  standard_waiting_period_months: 24
  min_continuous_renewals: 2
  max_deliveries_covered: 2
  normal_delivery_sublimit_inr: 30000
  caesarean_delivery_sublimit_inr: 50000
  newborn_baby_covered_from_day: 1
  newborn_cover_up_to_days: 90
  lawful_medical_termination_covered: true
  voluntary_surrogacy_covered: false

relations:
  prerequisite_clauses:
    - target: "./pre_existing_diseases.md"
      type: "subject_to"
  associated_limits:
    - target: "./room_rent_capping.md"
      type: "governed_by"
      description: "Maternity delivery suite room charges conform to base policy room category."

tags:
  - "maternity"
  - "pregnancy"
  - "caesarean"
  - "newborn"
  - "waiting_period_24m"
---

# Maternity Expenses & New Born Baby Coverage

## 1. Eligibility & Waiting Period
Medical expenses incurred for hospital delivery or lawful medical termination of pregnancy are covered provided the female insured person has completed a minimum waiting period of **24 continuous months** of coverage under the policy.

## 2. Quantitative Sub-Limits
* **Normal Delivery:** Reimbursable up to **₹30,000** per claim event.
* **Caesarean (C-Section) Delivery:** Reimbursable up to **₹50,000** per claim event.
* Lifetime maximum: Restricted to **two (2) deliveries or terminations** across all policy years.

## 3. New Born Baby Benefit
An infant born to an eligible insured mother is covered automatically from **Day 1 up to Day 90** within the mother's sum insured, covering congenital external/internal conditions and mandatory early vaccinations.
