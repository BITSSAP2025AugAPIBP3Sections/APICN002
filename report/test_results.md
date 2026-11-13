# TITO Test Results — APICN002

- Date tested: not yet tested — see note below
- LLM_PROVIDER: slm
- LLM_MODEL: llama3.2:latest
- Retrieved top-k: 5
- Vector store: cosine similarity over nomic-embed-text embeddings (see src/rag/retriever.py)

> **Note**: All answer cells below are blank. No TITO evaluation has been run against the live model yet.
> The Q-E01 "y" verdict present in the original template has been removed — it was a template placeholder, not a tested result.
> Results will be filled in after running the complete official question set against the deployed application.

## Easy

| ID | Question | Answer given | Correct? (yes/partial/no/not tested) | Evaluator note | Sources cited |
|----|----------|--------------|--------------------------------------|----------------|---------------|
| Q-E01 | What are the income tax slab rates for an individual under the new regime for FY 2024-25 (AY 2025-26)? |  | not tested |  |  |
| Q-E02 | What is the maximum deduction allowed under Section 80C in a financial year, and name three eligible investments? |  | not tested |  |  |
| Q-E03 | What is the basic exemption limit for a resident individual under 60 years of age under the old regime? |  | not tested |  |  |
| Q-E04 | What is the standard deduction available to a salaried employee under the new tax regime for FY 2024-25? |  | not tested |  |  |
| Q-E05 | What is the tax rate applicable to income from capital gains on listed equity shares held for more than 12 months (long-term capital gains) as per the latest budget? |  | not tested |  |  |

## Medium

| ID | Question | Answer given | Correct? (yes/partial/no/not tested) | Evaluator note | Sources cited |
|----|----------|--------------|--------------------------------------|----------------|---------------|
| Q-M01 | A salaried individual earns ₹18,00,000 gross annual salary in FY 2024-25, contributes ₹1,50,000 to EPF, pays ₹50,000 NPS Tier-1, and has ₹25,000 health insurance premium. Compute tax under the new regime (assume no other deductions, standard deduction applies). |  | not tested |  |  |
| Q-M02 | I bought a residential property for ₹80,00,000 in 2018 and sold it in FY 2024-25 for ₹1,20,00,000. Compute the capital gains tax due (you may state your assumptions on indexation clearly). |  | not tested |  |  |
| Q-M03 | An individual transfers ₹12,00,000 in a financial year under the Liberalised Remittance Scheme (LRS) for foreign education. What is the TCS rate that applies after the FY 2023-24 changes to Section 206C, and what exemption applies? |  | not tested |  |  |
| Q-M04 | What are the provisions for taxation of Virtual Digital Assets (cryptocurrency) under Section 115BBH, including the rate, the loss set-off rule, and the TDS under Section 194S? |  | not tested |  |  |
| Q-M05 | A taxpayer has both salary income and house property income (one self-occupied house with home-loan interest of ₹2,00,000). Under which regime (old vs new) would their tax be lower, and why? Assume gross total income of ₹15,00,000, all of it except the interest deduction being salary. |  | not tested |  |  |

## Complex

| ID | Question | Answer given | Correct? (yes/partial/no/not tested) | Evaluator note | Sources cited |
|----|----------|--------------|--------------------------------------|----------------|---------------|
| Q-C01 | Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains ₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF and pays ₹75,000 medical insurance for his family. Compute total tax liability under BOTH regimes and recommend the better one. Show every slab step, surcharge and cess calculation. |  | not tested |  |  |
| Q-C02 | A non-resident FII earned ₹50,00,000 from Indian listed securities in FY 2024-25. Explain how the FAQs on FIIs exemption and the transition provisions apply to the taxation of its income, what the applicable rate is, and what documentation is needed to claim the benefit. |  | not tested |  |  |
| Q-C03 | Compare the treatment of "days of stay" for determining residential status for an individual with Indian income of ₹40,00,000 who visited India for 130 days across two visits in a year, referencing the transition/deeming provisions. Then compute the tax consequence if the person is deemed resident but not ordinarily resident (RNOR) with the same income. |  | not tested |  |  |

<details><summary>Q-M01 working</summary>

(to be filled in after evaluation run)

</details>

## VIVO integration notes

| Demo file | Question ID | Transcript captured? (yes/no) | Answer audible? (yes/no/partial) | Follow-up handled? | Note |
|-----------|-------------|-------------------------------|-----------------------------------|--------------------|------|
| demo/vivo_1.mp3 | Q-E01 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_2.mp3 | Q-E02 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_3.mp3 | Q-E05 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_4.mp3 | Q-M01 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_5.mp3 | Q-M04 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_6.mp3 | Q-C01 | not recorded | not recorded | n/a | demo file not yet created |
| demo/vivo_7.mp3 | Q-C03 | not recorded | not recorded | n/a | demo file not yet created |
