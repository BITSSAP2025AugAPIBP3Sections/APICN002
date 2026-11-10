# TITO Test Results — APICN000

- Date tested: YYYY-MM-DD
- LLM_PROVIDER: slm
- LLM_MODEL: llama3.1:8b
- Retrieved top-k: 5
- Vector store: TF-IDF inverted index (see src/rag/retriever.py)

## Easy

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources cited |
|----|----------|--------------|---------------------------|----------------|---------------|
| Q-E01 | What are the income tax slab rates for an individual under the new regime for FY 2024-25 (AY 2025-26)? |  | y |  |  |
| Q-E02 | What is the maximum deduction allowed under Section 80C in a financial year, and name three eligible investments? |  |  |  |  |
| Q-E03 | What is the basic exemption limit for a resident individual under 60 years of age under the old regime? |  |  |  |  |
| Q-E04 | What is the standard deduction available to a salaried employee under the new tax regime for FY 2024-25? |  |  |  |  |
| Q-E05 | What is the tax rate applicable to income from capital gains on listed equity shares held for more than 12 months (long-term capital gains) as per the latest budget? |  |  |  |  |

## Medium

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources cited |
|----|----------|--------------|---------------------------|----------------|---------------|
| Q-M01 | A salaried individual earns ₹18,00,000 gross annual salary in FY 2024-25, contributes ₹1,50,000 to EPF, pays ₹50,000 NPS Tier-1, and has ₹25,000 health insurance premium. Compute tax under the new regime (assume no other deductions, standard deduction applies). |  |  |  |  |
| Q-M02 | I bought a residential property for ₹80,00,000 in 2018 and sold it in FY 2024-25 for ₹1,20,00,000. Compute the capital gains tax due (you may state your assumptions on indexation clearly). |  |  |  |  |
| Q-M03 | An individual transfers ₹12,00,000 in a financial year under the Liberalised Remittance Scheme (LRS) for foreign education. What is the TCS rate that applies after the FY 2023-24 changes to Section 206C, and what exemption applies? |  |  |  |  |
| Q-M04 | What are the provisions for taxation of Virtual Digital Assets (cryptocurrency) under Section 115BBH, including the rate, the loss set-off rule, and the TDS under Section 194S? |  |  |  |  |
| Q-M05 | A taxpayer has both salary income and house property income (one self-occupied house with home-loan interest of ₹2,00,000). Under which regime (old vs new) would their tax be lower, and why? Assume gross total income of ₹15,00,000, all of it except the interest deduction being salary. |  |  |  |  |

## Complex

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources cited |
|----|----------|--------------|---------------------------|----------------|---------------|
| Q-C01 | Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains ₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF and pays ₹75,000 medical insurance for his family. Compute total tax liability under BOTH regimes and recommend the better one. Show every slab step, surcharge and cess calculation. |  |  |  |  |
| Q-C02 | A non-resident FII earned ₹50,00,000 from Indian listed securities in FY 2024-25. Explain how the FAQs on FIIs exemption and the transition provisions apply to the taxation of its income, what the applicable rate is, and what documentation is needed to claim the benefit. |  |  |  |  |
| Q-C03 | Compare the treatment of "days of stay" for determining residential status for an individual with Indian income of ₹40,00,000 who visited India for 130 days across two visits in a year, referencing the transition/deeming provisions. Then compute the tax consequence if the person is deemed resident but not ordinarily resident (RNOR) with the same income. |  |  |  |  |

<details><summary>Q-M01 working</summary>

(paste your bot's computation, or a link to a transcript file)
</details>

## VIVO integration notes

| Demo file | Question ID | Transcript captured? (yes/no) | Answer audible? (yes/no/partial) | Follow-up handled? | Note |
|-----------|-------------|-------------------------------|-----------------------------------|--------------------|------|
| demo/vivo_1.mp3 | Q-E01 |  |  | n/a |  |
| demo/vivo_2.mp3 | Q-E02 |  |  | n/a |  |
| demo/vivo_3.mp3 | Q-E05 |  |  | n/a |  |
| demo/vivo_4.mp3 | Q-M01 |  |  | n/a |  |
| demo/vivo_5.mp3 | Q-M04 |  |  | n/a |  |
| demo/vivo_6.mp3 | Q-C01 |  |  | n/a |  |
| demo/vivo_7.mp3 | Q-C03 |  |  | n/a |  |
