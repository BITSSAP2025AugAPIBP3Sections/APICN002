"""Deterministic Indian income-tax calculator for FY 2024-25 (AY 2025-26).

Slab rates sourced from bs2024_25.pdf p.33 and IT Act §115BAC.
All amounts in rupees.  Returns structured dicts so callers can format output.
"""

from __future__ import annotations

import math
import re

# ---------------------------------------------------------------------------
# Slab tables — list of (upper_bound, rate) where upper_bound=inf is the top band
# ---------------------------------------------------------------------------

_NEW_REGIME_2024_SLABS: list[tuple[float, float]] = [
    (300_000, 0.00),
    (700_000, 0.05),
    (1_000_000, 0.10),
    (1_200_000, 0.15),
    (1_500_000, 0.20),
    (math.inf, 0.30),
]

_OLD_REGIME_2024_SLABS: list[tuple[float, float]] = [
    (250_000, 0.00),
    (500_000, 0.05),
    (1_000_000, 0.20),
    (math.inf, 0.30),
]

# Surcharge on income tax (not on LTCG/STCG for resident individuals >50L income):
# 10% if 50L < total income <= 1Cr; 15% if 1Cr < total income <= 2Cr; 25% > 2Cr
_SURCHARGE_SLABS: list[tuple[float, float]] = [
    (5_000_000, 0.00),
    (10_000_000, 0.10),
    (20_000_000, 0.15),
    (math.inf, 0.25),
]

CESS_RATE = 0.04
LTCG_EQUITY_EXEMPTION = 125_000      # Section 112A — first ₹1.25L exempt
LTCG_EQUITY_RATE = 0.125             # 12.5% post July 23, 2024
STCG_EQUITY_RATE = 0.20              # Section 111A rate post July 23, 2024 (was 15%)
NEW_REGIME_STD_DEDUCTION = 75_000
OLD_REGIME_STD_DEDUCTION = 50_000    # old regime standard deduction for salaried
MAX_HOUSE_LOAN_INTEREST_OLD = 200_000  # Section 24(b) self-occupied cap


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def _slab_tax(income: float, slabs: list[tuple[float, float]]) -> tuple[float, list[str]]:
    """Progressive slab tax.  Returns (total_tax, list_of_step_strings)."""
    tax = 0.0
    steps: list[str] = []
    prev = 0.0
    for upper, rate in slabs:
        if income <= prev:
            break
        band = min(income, upper) - prev
        band_tax = band * rate
        if rate > 0:
            steps.append(
                f"  ₹{prev/1e5:.2f}L – ₹{min(income,upper)/1e5:.2f}L @ {rate*100:.0f}%"
                f" = ₹{band_tax:,.0f}"
            )
        elif band > 0:
            steps.append(f"  ₹{prev/1e5:.2f}L – ₹{min(income,upper)/1e5:.2f}L @ Nil = ₹0")
        tax += band_tax
        prev = upper
    return tax, steps


def _surcharge(income: float, base_tax: float) -> float:
    prev = 0.0
    for upper, rate in _SURCHARGE_SLABS:
        if income <= prev:
            return 0.0
        if income <= upper:
            return base_tax * rate
        prev = upper
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def new_regime_tax_2024(
    gross_salary: float = 0.0,
    employer_nps: float = 0.0,
    ltcg_equity: float = 0.0,
    stcg_equity: float = 0.0,
    other_income: float = 0.0,
) -> dict:
    """Compute FY 2024-25 tax under new regime.

    Only allowed deductions: standard deduction (₹75K) + employer NPS (80CCD(2)).
    LTCG equity taxed at 12.5% under Section 112A (gains > ₹1.25L).
    STCG equity taxed at 20% under Section 111A.
    """
    std_ded = min(NEW_REGIME_STD_DEDUCTION, gross_salary)
    nps_ded = min(employer_nps, 0.14 * gross_salary)  # capped at 14% of salary

    normal_income = gross_salary - std_ded - nps_ded + other_income
    normal_income = max(0.0, normal_income)

    ltcg_taxable = max(0.0, ltcg_equity - LTCG_EQUITY_EXEMPTION)
    stcg_taxable = max(0.0, stcg_equity)
    total_income = normal_income + ltcg_taxable + stcg_taxable

    slab_tax_amt, slab_steps = _slab_tax(normal_income, _NEW_REGIME_2024_SLABS)
    ltcg_tax = ltcg_taxable * LTCG_EQUITY_RATE
    stcg_tax = stcg_taxable * STCG_EQUITY_RATE

    base_tax = slab_tax_amt + ltcg_tax + stcg_tax
    surcharge = _surcharge(total_income, base_tax)
    cess = (base_tax + surcharge) * CESS_RATE
    total_tax = base_tax + surcharge + cess

    return {
        "regime": "new",
        "fy": "2024-25",
        "gross_salary": gross_salary,
        "std_deduction": std_ded,
        "employer_nps_deduction": nps_ded,
        "normal_taxable_income": normal_income,
        "ltcg_equity": ltcg_equity,
        "ltcg_taxable": ltcg_taxable,
        "stcg_equity": stcg_equity,
        "stcg_taxable": stcg_taxable,
        "total_income": total_income,
        "slab_tax": slab_tax_amt,
        "slab_steps": slab_steps,
        "ltcg_tax": ltcg_tax,
        "stcg_tax": stcg_tax,
        "base_tax": base_tax,
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total_tax,
    }


def old_regime_tax_2024(
    gross_salary: float = 0.0,
    sec80c: float = 0.0,
    sec80d: float = 0.0,
    house_loan_interest: float = 0.0,
    ltcg_equity: float = 0.0,
    stcg_equity: float = 0.0,
    other_income: float = 0.0,
) -> dict:
    """Compute FY 2024-25 tax under old regime.

    Deductions: std deduction ₹50K, 80C (cap ₹1.5L), 80D (as given),
    Section 24(b) house loan interest (cap ₹2L for self-occupied).
    """
    std_ded = min(OLD_REGIME_STD_DEDUCTION, gross_salary)
    sec80c_capped = min(sec80c, 150_000)
    house_int_capped = min(house_loan_interest, MAX_HOUSE_LOAN_INTEREST_OLD)

    normal_income = gross_salary - std_ded + other_income - sec80c_capped - sec80d - house_int_capped
    normal_income = max(0.0, normal_income)

    ltcg_taxable = max(0.0, ltcg_equity - LTCG_EQUITY_EXEMPTION)
    stcg_taxable = max(0.0, stcg_equity)
    total_income = normal_income + ltcg_taxable + stcg_taxable

    slab_tax_amt, slab_steps = _slab_tax(normal_income, _OLD_REGIME_2024_SLABS)
    ltcg_tax = ltcg_taxable * LTCG_EQUITY_RATE
    stcg_tax = stcg_taxable * STCG_EQUITY_RATE

    base_tax = slab_tax_amt + ltcg_tax + stcg_tax
    surcharge = _surcharge(total_income, base_tax)
    cess = (base_tax + surcharge) * CESS_RATE
    total_tax = base_tax + surcharge + cess

    return {
        "regime": "old",
        "fy": "2024-25",
        "gross_salary": gross_salary,
        "std_deduction": std_ded,
        "sec80c": sec80c_capped,
        "sec80d": sec80d,
        "house_loan_interest": house_int_capped,
        "normal_taxable_income": normal_income,
        "ltcg_equity": ltcg_equity,
        "ltcg_taxable": ltcg_taxable,
        "stcg_equity": stcg_equity,
        "stcg_taxable": stcg_taxable,
        "total_income": total_income,
        "slab_tax": slab_tax_amt,
        "slab_steps": slab_steps,
        "ltcg_tax": ltcg_tax,
        "stcg_tax": stcg_tax,
        "base_tax": base_tax,
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total_tax,
    }


def format_calculation(result: dict) -> str:
    """Return a readable step-by-step calculation string."""
    r = result
    lines: list[str] = [
        f"--- Programmatic Tax Calculation ({r['regime'].upper()} regime FY {r['fy']}) ---",
        f"Gross salary:               ₹{r['gross_salary']:>12,.0f}",
        f"Less standard deduction:    ₹{r['std_deduction']:>12,.0f}",
    ]
    if r["regime"] == "new" and r.get("employer_nps_deduction", 0) > 0:
        lines.append(f"Less employer NPS (80CCD2): ₹{r['employer_nps_deduction']:>12,.0f}")
    if r["regime"] == "old":
        if r.get("sec80c", 0) > 0:
            lines.append(f"Less Section 80C:          ₹{r['sec80c']:>12,.0f}")
        if r.get("sec80d", 0) > 0:
            lines.append(f"Less Section 80D:          ₹{r['sec80d']:>12,.0f}")
        if r.get("house_loan_interest", 0) > 0:
            lines.append(f"Less Sec 24(b) int:        ₹{r['house_loan_interest']:>12,.0f}")

    lines.append(f"Normal taxable income:      ₹{r['normal_taxable_income']:>12,.0f}")
    lines.append("Slab-by-slab tax:")
    for step in r["slab_steps"]:
        lines.append(step)
    lines.append(f"Slab tax total:             ₹{r['slab_tax']:>12,.0f}")

    if r.get("ltcg_taxable", 0) > 0:
        lines.append(
            f"LTCG equity (Sec 112A):     ₹{r['ltcg_taxable']:>12,.0f} × 12.5% = ₹{r['ltcg_tax']:,.0f}"
        )
    if r.get("stcg_taxable", 0) > 0:
        lines.append(
            f"STCG equity (Sec 111A):     ₹{r['stcg_taxable']:>12,.0f} × 20%   = ₹{r['stcg_tax']:,.0f}"
        )

    lines.append(f"Base tax:                   ₹{r['base_tax']:>12,.0f}")
    if r["surcharge"] > 0:
        lines.append(f"Surcharge:                  ₹{r['surcharge']:>12,.0f}")
    lines.append(f"4% H&E Cess:                ₹{r['cess']:>12,.0f}")
    lines.append(f"TOTAL TAX PAYABLE:          ₹{r['total_tax']:>12,.0f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query detection
# ---------------------------------------------------------------------------

_COMPUTE_VERBS = re.compile(
    r"\b(compute|calculat|tax liability|how much tax|total tax|tax payable|tax due"
    r"|which regime|old vs new|old or new|better regime|regime.*lower|lower.*regime)\b",
    re.IGNORECASE,
)
_INCOME_AMOUNT = re.compile(
    r"(?:₹\s*)?(\d[\d,]*)\s*(lakh|crore)\b"   # "18 lakh", "₹18 lakh"
    r"|\b(\d+)\s*L\b"                            # "18L"
    r"|\b\d{1,2},\d{2},\d{3}\b",                # "18,00,000" Indian full-rupee format
    re.IGNORECASE,
)


def is_calculation_query(question: str) -> bool:
    """Return True when the question asks for a numeric tax computation with an income amount."""
    return bool(_COMPUTE_VERBS.search(question) and _INCOME_AMOUNT.search(question))
