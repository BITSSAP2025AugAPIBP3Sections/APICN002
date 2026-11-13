# TITO Test Results — APICN002

- Date tested: 2026-11-13 (Stage 9 evaluation — interim report)
- LLM_PROVIDER: groq
- LLM_MODEL: openai/gpt-oss-120b
- Retrieved top-k: 7
- Vector store: cosine similarity over nomic-embed-text embeddings (local Ollama, 768-dim), with temporal year boost (+0.06 bs2024_25.pdf, −0.02 bs2023_24.pdf, −0.06 bs202223.pdf, −0.07 bs202122.pdf)
- max_tokens: 1500
- Automated tests: 131 passed
- API notes: Groq returned HTTP 429 (Too Many Requests) on several consecutive requests during sequential evaluation; each question was retried automatically until successful. Intended model `llama-3.3-70b-versatile` returned HTTP 404 (not available on this account); `openai/gpt-oss-120b` was used as the available substitute.
- Stage 7 additions: 7-rule system prompt (A1–A4), deterministic tax calculator appended to calculation queries (B), reduced bs2023_24 penalty −0.05→−0.02 (C1)
- Stage 8 additions: 8-rule system prompt (rule 8: Section 194S = 1% TDS ≠ 30% income tax); real-estate guard (S8-A) and residency guard (S8-B) in _reference_calculations; other_income/sec80c/sec80d extraction (S8-E); strengthened rule A1 vocabulary (S8-D); ₹-prefix fix for LTCG/STCG/interest/house-loan regexes (S8-F)

## Easy

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources (retrieved context) |
|----|----------|--------------|---------------------------|----------------|------------------------------|
| Q-E01 | What are the income tax slab rates for an individual under the new regime for FY 2024-25 (AY 2025-26)? | 0–3,00,000: Nil; 3,00,001–7,00,000: 5%; 7,00,001–10,00,000: 10%; 10,00,001–12,00,000: 15%; 12,00,001–15,00,000: 20%; above 15,00,000: 30%. Source: bs2024_25.pdf p.33. | yes | Correct FY 2024-25 new-regime slabs; correctly cites bs2024_25.pdf; unchanged from Stage 8. Stage 9 also retrieved bs2025_26.pdf p.32 (FY 2025-26 slabs) but model correctly cited the FY 2024-25 source. LLM latency 1,718 ms. | bs2024_25.pdf p.32, p.33; bs2025_26.pdf p.32; bs2024_25.pdf p.29; IT Act p.465 |
| Q-E02 | What is the maximum deduction allowed under Section 80C in a financial year, and name three eligible investments? | Maximum deduction under Section 80C (including Sections 80CCC and 80CCD(1)): the aggregate amount that can be claimed in a financial year shall not exceed ₹1,50,000. Three eligible investments: The corpus you provided does not list specific investments that qualify for deduction under Section 80C. Therefore, I cannot identify three eligible investments from the given documents. | partial | Correct limit ₹1,50,000 sourced from IT Act p.292. Model declines to name any investments citing corpus insufficiency — a stricter refusal than Stage 8, which named PPF, LIP, and FD (though imprecisely). Within-partial: worse than Stage 8. | IT Act p.292, p.471, p.294, p.286; bs2024_25.pdf p.61 |
| Q-E03 | What is the basic exemption limit for a resident individual under 60 years of age under the old regime? | The basic exemption limit for a resident individual who is under 60 years of age under the old tax regime is ₹2,50,000. (This limit is the standard provision of the Income-Tax Act for individuals below 60 years, even though it is not explicitly quoted in the excerpted documents.) | yes | Correct. Model applied system prompt rule 7 ("₹2,50,000 for individuals below 60 years — settled law") and explicitly acknowledged it as settled law not requiring corpus confirmation. Stage 9 run resolves the Q-E03 regression observed in an earlier Stage 9 experimental run. LLM latency 2,593 ms. | IT Act p.296, p.35; Updated-FQAs-on-Interplay&Transitions.pdf p.90, p.39; bs2024_25.pdf p.42 |
| Q-E04 | What is the standard deduction available to a salaried employee under the new tax regime for FY 2024-25? | The standard deduction for salaried employees under the new tax regime for FY 2024-25 is ₹75,000. | yes | Correct; correctly cites bs2024_25.pdf p.32; unchanged from Stage 8. Fastest response in the evaluation at 782 ms LLM latency. | bs2024_25.pdf p.32, p.54; Updated-FQAs-on-Interplay&Transitions.pdf p.62, p.80, p.16 |
| Q-E05 | What is the tax rate applicable to income from capital gains on listed equity shares held for more than 12 months (long-term capital gains) as per the latest budget? | The latest budget proposes that long-term capital gains on listed equity shares (held for more than 12 months) will be taxed at 12.5 percent. Budget Speech 2024-25: "Long term gains on all financial and non-financial assets, on the other hand, will attract a tax rate of 12.5 per cent." IT Act p.429: "rate of twelve and one-half per cent for any transfer which takes place on or after the 23rd day of July, 2024." | yes | Correct rate; Section 112A correctly implied via corpus citation at IT Act p.429. Model cites both the Budget Speech and IT Act text to confirm post-July 2024 effective date. Unchanged from Stage 8. | bs2024_25.pdf p.30, p.56; IT Act p.428, p.429, p.430 |

## Medium

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources (retrieved context) |
|----|----------|--------------|---------------------------|----------------|------------------------------|
| Q-M01 | A salaried individual earns ₹18,00,000 gross annual salary in FY 2024-25, contributes ₹1,50,000 to EPF, pays ₹50,000 NPS Tier-1, and has ₹25,000 health insurance premium. Compute tax under the new regime (assume no other deductions, standard deduction applies). | LLM: I'm sorry, but I cannot find the applicable new-regime tax-rate slabs for FY 2024-25 in the provided documents, so I'm unable to compute the tax liability. (The only relevant information in the corpus is the increase in the standard deduction to ₹75,000 for salaried employees under the new regime — bs2024_25.pdf, p.32.) **Deterministic calculator output: NEW regime ₹2,15,800** (gross salary ₹18,00,000 − std deduction ₹75,000 = taxable ₹17,25,000; slab tax ₹2,07,500 + 4% cess ₹8,300; EPF/NPS/health insurance correctly excluded as Chapter VI-A items) | partial | LLM declines to compute citing missing slab tables (slabs are in fact at bs2024_25.pdf p.32–33, retrieved at rank 1). Deterministic calculator (not the LLM) provides the correct answer ₹2,15,800. Partial because the LLM narrative is unhelpful; programmatic block is the sole correct signal. Unchanged from Stage 8. | bs2024_25.pdf p.32, p.36, p.37 |
| Q-M02 | I bought a residential property for ₹80,00,000 in 2018 and sold it in FY 2024-25 for ₹1,20,00,000. Compute the capital gains tax due (you may state your assumptions on indexation clearly). | LLM: I'm sorry, but I cannot find the required Cost-Inflation Index values (or any other indexation data) in the provided documents, so I'm unable to compute the indexed cost of acquisition and therefore cannot calculate the capital-gains tax due for the residential-property sale. | partial | Real-estate guard (S8-A) correctly suppresses programmatic block. LLM declines entirely citing missing CII values — a different failure from Stage 8 (where the LLM stated 12.5% rate and ₹5L gain correctly despite not computing cess). Stage 9 within-partial is worse: no rate cited, no gain computed. CII data is not in the corpus. | bs2024_25.pdf p.56; IT Act p.214, p.429; bs2024_25.pdf p.30 |
| Q-M03 | An individual transfers ₹12,00,000 in a financial year under the Liberalised Remittance Scheme (LRS) for foreign education. What is the TCS rate that applies after the FY 2023-24 changes to Section 206C, and what exemption applies? | For LRS remittances for foreign education financed through a loan from a financial institution, the TCS rate is 0.5% on the amount exceeding ₹7 lakh. The first ₹7 lakh is exempt from TCS. Hence, for a ₹12,00,000 LRS transfer, TCS is payable at 0.5% on ₹5,00,000 (₹12,00,000 − ₹7,00,000); the initial ₹7,00,000 is exempt. | partial | Identifies only the 0.5% loan-financed education rate; omits the 5% general rate applicable to self-financed LRS education. The question does not specify a loan. Model newly cites bs2025_26.pdf p.51 in addition to bs2023_24.pdf. Within-partial: slightly better source coverage than Stage 8, same fundamental gap on the 5% rate. | bs2024_25.pdf p.57, p.59; bs2023_24.pdf p.44; bs2025_26.pdf p.51; bs2024_25.pdf p.46 |
| Q-M04 | What are the provisions for taxation of Virtual Digital Assets (cryptocurrency) under Section 115BBH, including the rate, the loss set-off rule, and the TDS under Section 194S? | Section 115BBH: VDA income taxed at 30% flat; no deductions except cost of acquisition; losses from VDA transfer cannot be set off against any other income and cannot be carried forward. Section 194S TDS: The supplied corpus does not contain any provision describing the TDS rate or mechanics of Section 194S. Therefore, the specific TDS rate (which is 1% under the law) cannot be confirmed from the provided documents. | partial | **Regression from Stage 8 (YES → PARTIAL).** Model correctly states 30% income tax and loss set-off rules from IT Act p.460. For Section 194S, rule 8 in the system prompt hardcodes the 1% TDS rate, but the model treats the "Answer ONLY from the provided context" instruction as overriding the domain rule — it acknowledges the 1% rate parenthetically ("which is 1% under the law") but declines to assert it as the answer. Stage 8 llama3.2 3B applied rule 8 directly; this 120B reasoning model does not. | IT Act p.460; bs2024_25.pdf p.57, p.59; E-Book-Guidance-Note-Crypto-Asset-Reporting-Obligations.pdf p.111 |
| Q-M05 | A taxpayer has both salary income and house property income (one self-occupied house with home-loan interest of ₹2,00,000). Under which regime (old vs new) would their tax be lower, and why? Assume gross total income of ₹15,00,000, all of it except the interest deduction being salary. | LLM: I'm sorry, but I cannot find enough information in the provided corpus to determine which regime would result in lower tax liability. The documents contain the proposed new-regime slab rates and the increased standard deduction of ₹75,000, but they do not include the old-regime slab rates, the standard deduction under the old regime, or the exact treatment of home-loan interest in that regime. **Deterministic calculator output: NEW regime ₹1,30,000; OLD regime ₹1,95,000 — new regime lower by ₹65,000.** | yes | LLM declines to compare, but the deterministic calculator (not the LLM) provides both correct answers. Old regime: ₹15L − ₹50K std − ₹2L house loan = ₹12.5L → slab tax ₹1,87,500 + 4% cess ₹7,500 = ₹1,95,000. New regime: ₹15L − ₹75K std = ₹14.25L → slab tax ₹1,25,000 + 4% cess ₹5,000 = ₹1,30,000. House-loan ₹-prefix fix (S8-F) ensures correct OLD = ₹1,95,000. | bs2024_25.pdf p.32, p.33, p.58, p.30 |

## Complex

| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources (retrieved context) |
|----|----------|--------------|---------------------------|----------------|------------------------------|
| Q-C01 | Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains ₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF and pays ₹75,000 medical insurance for his family. Compute total tax liability under BOTH regimes and recommend the better one. Show every slab step, surcharge and cess calculation. | LLM: I'm sorry, but I cannot compute the tax liability because the corpus does not contain the necessary information on slab rates, surcharge thresholds, standard deduction amounts, or Chapter VI-A limits for either regime. **Deterministic calculator output: NEW regime ₹5,99,950; OLD regime ₹6,64,950 — new regime lower by ₹65,000.** | partial | LLM declines entirely; deterministic calculator (not the LLM) provides both correct answers. S8-E extraction correctly captures: interest ₹3L, PPF ₹2L (capped to ₹1.5L under 80C), medical ₹75K (80D). S8-F ₹-prefix fix enables correct extraction of all amounts. New regime: 26.25L normal taxable + LTCG ₹59,375 + STCG ₹40,000 + cess = ₹5,99,950. Old regime: 24.25L normal taxable + same LTCG/STCG + cess = ₹6,64,950. No recommendation from LLM; programmatic block provides values but no regime advice. | bs2024_25.pdf p.56, p.30; IT Act p.429, p.430, p.465 |
| Q-C02 | A non-resident FII earned ₹50,00,000 from Indian listed securities in FY 2024-25. Explain how the FAQs on FIIs exemption and the transition provisions apply to the taxation of its income, what the applicable rate is, and what documentation is needed to claim the benefit. | The taxation is governed by Section 210 of the Income-tax Act, 2025. General rate on "income in respect of securities": 20%. Capital gain rates: STCG not under Sec.196 = 30%; STCG under Sec.196 = 20%; LTCG not under Sec.198 = 12.5%; LTCG under Sec.198 (excess > ₹1,25,000) = 12.5%. Earlier FIIs taxed under Section 115AD/5% concessional rate; Section 210 supersedes for FY 2024-25. Documentation: the FAQs do not list specific documents required. Tax calculation (20% default assumption): tax payable before cess: ₹50… | partial | Detailed rate table and transition analysis are present. The response cites "Section 210 of the Income-tax Act, 2025" — a section number from the IT Act 2025 recodification that does not correspond to IT Act 1961 Section numbering; this is sourced from FAQs-on-BIS-Exemption.pdf which uses 2025 Act cross-references. Documentation question not answered. Response truncated before completing the cess calculation ("₹50" is clearly mid-sentence). Unchanged direction from Stage 8. | FAQs-on-BIS-Exemption.pdf p.1; bs2024_25.pdf p.32, p.59 |
| Q-C03 | Compare the treatment of "days of stay" for determining residential status for an individual with Indian income of ₹40,00,000 who visited India for 130 days across two visits in a year, referencing the transition/deeming provisions. Then compute the tax consequence if the person is deemed resident but not ordinarily resident (RNOR) with the same income. | Comparison table: Old Act — 182-day general rule; 60-day rule (+ 365 days in 4 preceding years) for income > ₹15L. New Act — 120-day rule (+ 365 days in 4 preceding years) for income > ₹15L; deemed-resident provision unchanged. Application: income ₹40L > ₹15L; stay 130 days. Old Act 182-day: 130 < 182 → not resident. New Act 120-day: 130 days > 120 [response truncated by max_tokens before completing conclusion and tax computation] | partial | Residency guard (S8-B) correctly suppresses programmatic block. LLM correctly builds the comparison framework and correctly reaches "130 days > 120" — indicating the new-Act deemed-resident threshold is met. Response is truncated before stating the final status conclusion or computing any tax figure. Tax computation never delivered. Unchanged direction from Stage 8. | Updated-FQAs-on-Interplay&Transitions.pdf p.87, p.88, p.89 |

<details><summary>Q-M01 working — deterministic calculator output (Stage 9)</summary>

*Output produced by `src/rag/tax_calc.py`, not by the LLM.*

Under new regime FY 2024-25:
- Gross salary: ₹18,00,000
- Less: Standard deduction (only allowed deduction in new regime for salaried): ₹75,000
- Taxable income: ₹17,25,000
- EPF (₹1.5L), NPS Tier-1 (₹50K), health insurance (₹25K): Section 80C/80D — NOT allowed in new regime

Progressive slab tax (new regime 2024-25: 0-3L Nil, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%):
- 0–3L: Nil
- 3–7L: 5% × ₹4L = ₹20,000
- 7–10L: 10% × ₹3L = ₹30,000
- 10–12L: 15% × ₹2L = ₹30,000
- 12–15L: 20% × ₹3L = ₹60,000
- 15–17.25L: 30% × ₹2.25L = ₹67,500
- Total income tax: ₹2,07,500
- 4% H&E cess: ₹8,300
- **Total tax payable: ₹2,15,800**

</details>

<details><summary>Q-M05 working — deterministic calculator output (Stage 9)</summary>

*Output produced by `src/rag/tax_calc.py`, not by the LLM.*

Under old regime FY 2024-25 (salary ₹15L, home-loan interest ₹2L Section 24(b)):
- Gross salary: ₹15,00,000
- Less standard deduction: ₹50,000
- Less house loan interest (Section 24(b), capped ₹2L): ₹2,00,000
- Normal taxable income: ₹12,50,000
- Old regime slabs: 0-2.5L Nil; 2.5-5L 5%×2.5L=₹12,500; 5-10L 20%×5L=₹1,00,000; 10-12.5L 30%×2.5L=₹75,000
- Slab tax: ₹1,87,500; 4% cess: ₹7,500; **OLD regime total: ₹1,95,000**

Under new regime FY 2024-25:
- Gross salary: ₹15,00,000
- Less standard deduction: ₹75,000 (house-loan interest NOT deductible in new regime)
- Normal taxable income: ₹14,25,000
- New regime slabs: 0-3L Nil; 3-7L 5%×4L=₹20,000; 7-10L 10%×3L=₹30,000; 10-12L 15%×2L=₹30,000; 12-14.25L 20%×2.25L=₹45,000
- Slab tax: ₹1,25,000; 4% cess: ₹5,000; **NEW regime total: ₹1,30,000**

New regime lower by ₹65,000.

</details>

<details><summary>Q-C01 working — deterministic calculator output (Stage 9)</summary>

*Output produced by `src/rag/tax_calc.py`, not by the LLM.*

Under new regime FY 2024-25 (salary ₹24L + interest ₹3L + LTCG ₹6L equity + STCG ₹2L equity):
- Gross salary: ₹24,00,000; Less standard deduction: ₹75,000; Plus interest income: ₹3,00,000
- Normal taxable income: ₹26,25,000
- New regime slabs: 0-3L Nil; 3-7L 5%×4L=₹20,000; 7-10L 10%×3L=₹30,000; 10-12L 15%×2L=₹30,000; 12-15L 20%×3L=₹60,000; 15-26.25L 30%×11.25L=₹3,37,500
- Slab tax: ₹4,77,500
- LTCG equity (Sec 112A): (₹6L − ₹1.25L) × 12.5% = ₹4.75L × 12.5% = ₹59,375
- STCG equity (Sec 111A): ₹2L × 20% = ₹40,000
- Base tax: ₹4,77,500 + ₹59,375 + ₹40,000 = ₹5,76,875
- 4% H&E cess: ₹23,075
- **NEW regime total: ₹5,99,950**

Under old regime FY 2024-25 (salary ₹24L + interest ₹3L − 80C ₹1.5L − 80D ₹75K):
- Gross salary: ₹24,00,000; Less standard deduction: ₹50,000; Less 80C (PPF ₹2L capped): ₹1,50,000; Less 80D (medical): ₹75,000; Plus interest: ₹3,00,000
- Normal taxable income: ₹24,25,000
- Old regime slabs: 0-2.5L Nil; 2.5-5L 5%×2.5L=₹12,500; 5-10L 20%×5L=₹1,00,000; 10-24.25L 30%×14.25L=₹4,27,500
- Slab tax: ₹5,40,000
- LTCG equity: ₹59,375; STCG equity: ₹40,000
- Base tax: ₹5,40,000 + ₹59,375 + ₹40,000 = ₹6,39,375
- 4% H&E cess: ₹25,575
- **OLD regime total: ₹6,64,950**

New regime lower by ₹65,000.

</details>

## Stage comparison

| Stage | Correct (yes) | Partial | Wrong (no) |
|-------|---------------|---------|------------|
| Stage 6 | 3 (Q-E01, Q-E04, Q-M04) | 8 | 2 (Q-E03, Q-M02) |
| Stage 7 | 5 (Q-E01, Q-E03, Q-E04, Q-E05, Q-M05) | 6 | 2 (Q-M02, Q-C03) |
| Stage 8 | 6 (Q-E01, Q-E03, Q-E04, Q-E05, Q-M04, Q-M05) | 7 | 0 |
| Stage 9 | 5 (Q-E01, Q-E03, Q-E04, Q-E05, Q-M05) | 8 | 0 |

**Stage 9 regression vs Stage 8:** Q-M04 (YES→PARTIAL). The Stage 8 llama3.2 3B model applied system prompt rule 8 directly to assert the 1% TDS rate. The Stage 9 openai/gpt-oss-120b reasoning model acknowledges the rate parenthetically but treats "Answer ONLY from the provided context" as overriding the domain rule, declining to confirm Section 194S from the corpus.

**Stage 9 within-partial changes vs Stage 8:**
- Q-M02 (worse within partial): Stage 8 LLM correctly stated 12.5% rate and ₹40L gain; Stage 9 LLM refuses entirely citing missing CII data.
- Q-M03 (better within partial): Stage 9 now cites bs2025_26.pdf p.51 confirming the ₹7L exemption threshold; slightly stronger sourcing.
- Q-E02 (worse within partial): Stage 9 refuses to name any investments; Stage 8 named three (imprecisely).
- Q-C01, Q-M01, Q-M05: Unchanged — LLM refuses in both stages; deterministic calculator provides correct values.

**Stage 9 model note:** `openai/gpt-oss-120b` is a reasoning model (internal chain-of-thought, hidden reasoning tokens). Its inference is 3–10× faster than local llama3.2 (avg ~1.6–4 s vs ~4–20 s) but it applies strict context-only instruction adherence that reduces effectiveness of hardcoded system-prompt domain rules. `llama-3.3-70b-versatile` (the intended model) was unavailable (HTTP 404) on this Groq account.

## VIVO integration notes

| Demo file | Question ID | Transcript captured? (yes/no) | Answer audible? (yes/no/partial) | Follow-up handled? | Note |
|-----------|-------------|-------------------------------|-----------------------------------|--------------------|------|
| demo/vivo_0.mp3 | Free-choice question | not recorded | not recorded | n/a | pending — file not yet received |
| demo/vivo_1.mp3 | Q-E01 | not recorded | not recorded | n/a | pending — file not yet received |
| demo/vivo_2.mp3 | Q-E02 | not recorded | not recorded | n/a | pending — file not yet received |
| demo/vivo_3.mp3 | Q-E05 | not verified | not verified | n/a | file present (valid MP3, ID3v2.4, 64 kbps, 48 kHz mono, ~20 s); transcript and audibility not verified — no STT/playback tool available without running the application |
| demo/vivo_4.mp3 | Q-M01 | not verified | not verified | n/a | file present (valid MP3, ID3v2.4, 64 kbps, 48 kHz mono, ~43 s); transcript and audibility not verified — no STT/playback tool available without running the application |
| demo/vivo_5.mp3 | Q-M04 | not recorded | not recorded | n/a | pending — file not yet received |
| demo/vivo_6.mp3 | Q-C01 | not recorded | not recorded | n/a | pending — file not yet received |
| demo/vivo_7.mp3 | Q-C03 | not recorded | not recorded | n/a | pending — file not yet received |
