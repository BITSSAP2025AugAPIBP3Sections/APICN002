"""Tests for src/rag/tax_calc.py — deterministic FY 2024-25 slab engine."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.tax_calc import (
    CESS_RATE,
    format_calculation,
    is_calculation_query,
    new_regime_tax_2024,
    old_regime_tax_2024,
)


# ---------------------------------------------------------------------------
# New regime slab arithmetic
# ---------------------------------------------------------------------------

class TestNewRegimeSlabs:
    def test_zero_income(self):
        r = new_regime_tax_2024(gross_salary=0)
        assert r["total_tax"] == 0.0

    def test_below_300k(self):
        # ₹2.5L salary → taxable ₹1.75L (after ₹75K std ded) → in Nil band → ₹0 tax
        r = new_regime_tax_2024(gross_salary=250_000)
        assert r["total_tax"] == 0.0

    def test_slab_3_to_7_only(self):
        # ₹10L salary → taxable ₹9.25L (after ₹75K std ded)
        # 0-3L: Nil; 3-7L: 5% × 4L = ₹20K; 7-9.25L: 10% × 2.25L = ₹22.5K
        # base = ₹42.5K; cess = ₹1700; total = ₹44,200
        r = new_regime_tax_2024(gross_salary=1_000_000)
        assert r["normal_taxable_income"] == 925_000
        assert abs(r["slab_tax"] - 42_500) < 1
        assert abs(r["total_tax"] - 44_200) < 1

    def test_q_m01_18lakh(self):
        # Q-M01: salary ₹18L, new regime; EPF/NPS/health insurance NOT deductible
        # Taxable = 18L - 0.75L = 17.25L
        # Slab: 0-3L Nil; 3-7L 5%×4L=20K; 7-10L 10%×3L=30K; 10-12L 15%×2L=30K;
        #        12-15L 20%×3L=60K; 15-17.25L 30%×2.25L=67.5K → total 207.5K
        # cess 4% × 207.5K = 8.3K → total 215.8K
        r = new_regime_tax_2024(gross_salary=1_800_000)
        assert abs(r["normal_taxable_income"] - 1_725_000) < 1
        assert abs(r["slab_tax"] - 207_500) < 1
        assert abs(r["total_tax"] - 215_800) < 1

    def test_employer_nps_deduction(self):
        # Employer NPS 80CCD(2) IS allowed; reduces normal income
        r = new_regime_tax_2024(gross_salary=1_000_000, employer_nps=100_000)
        assert r["employer_nps_deduction"] == 100_000
        assert r["normal_taxable_income"] == 825_000  # 10L - 75K std - 100K nps

    def test_ltcg_equity_exemption_boundary(self):
        # ₹1.25L LTCG → taxable = 0 → no tax on LTCG
        r = new_regime_tax_2024(ltcg_equity=125_000)
        assert r["ltcg_taxable"] == 0.0
        assert r["ltcg_tax"] == 0.0

    def test_ltcg_equity_above_exemption(self):
        # ₹6L LTCG → taxable = ₹4.75L → 12.5% = ₹59,375
        r = new_regime_tax_2024(ltcg_equity=600_000)
        assert abs(r["ltcg_taxable"] - 475_000) < 1
        assert abs(r["ltcg_tax"] - 59_375) < 1

    def test_stcg_equity(self):
        # ₹2L STCG → 20% = ₹40K; cess 4% = ₹1600; total ₹41,600
        r = new_regime_tax_2024(stcg_equity=200_000)
        assert abs(r["stcg_tax"] - 40_000) < 1
        assert abs(r["total_tax"] - 41_600) < 1


# ---------------------------------------------------------------------------
# Old regime slab arithmetic
# ---------------------------------------------------------------------------

class TestOldRegimeSlabs:
    def test_below_250k_nil(self):
        r = old_regime_tax_2024(gross_salary=200_000)
        assert r["total_tax"] == 0.0

    def test_q_m05_15lakh_old_regime(self):
        # Salary ₹15L, house loan interest ₹2L (Sec 24b)
        # Std ded ₹50K; net salary income = 15L - 50K = 14.5L
        # Less house loan interest ₹2L → normal taxable = 12.5L
        # Old regime: 0-2.5L Nil; 2.5-5L 5%×2.5L=12.5K; 5-10L 20%×5L=100K; 10-12.5L 30%×2.5L=75K
        # base = 187.5K; cess 4% = 7.5K; total = 195K
        r = old_regime_tax_2024(gross_salary=1_500_000, house_loan_interest=200_000)
        assert abs(r["normal_taxable_income"] - 1_250_000) < 1
        assert abs(r["slab_tax"] - 187_500) < 1
        assert abs(r["total_tax"] - 195_000) < 1

    def test_80c_capped_at_150k(self):
        r = old_regime_tax_2024(gross_salary=1_000_000, sec80c=200_000)
        assert r["sec80c"] == 150_000  # capped


# ---------------------------------------------------------------------------
# Cess and surcharge
# ---------------------------------------------------------------------------

class TestCessAndSurcharge:
    def test_cess_rate(self):
        r = new_regime_tax_2024(gross_salary=1_800_000)
        assert abs(r["cess"] - r["base_tax"] * CESS_RATE) < 1

    def test_surcharge_at_55lakh(self):
        # Income >₹50L triggers 10% surcharge
        r = new_regime_tax_2024(gross_salary=5_600_000)
        assert r["surcharge"] > 0


# ---------------------------------------------------------------------------
# format_calculation
# ---------------------------------------------------------------------------

class TestFormatCalculation:
    def test_output_contains_total(self):
        r = new_regime_tax_2024(gross_salary=1_800_000)
        s = format_calculation(r)
        assert "TOTAL TAX PAYABLE" in s
        assert "215,800" in s

    def test_output_shows_regime(self):
        r = old_regime_tax_2024(gross_salary=1_000_000)
        s = format_calculation(r)
        assert "OLD" in s


# ---------------------------------------------------------------------------
# Query detection
# ---------------------------------------------------------------------------

class TestIsCalculationQuery:
    def test_compute_with_lakh(self):
        assert is_calculation_query("Compute tax for a salary of 18 lakh under new regime")

    def test_rupee_symbol(self):
        assert is_calculation_query("Calculate tax liability for ₹24 lakh salary")

    def test_no_income_amount(self):
        assert not is_calculation_query("What is the tax rate for VDA?")

    def test_no_compute_verb(self):
        assert not is_calculation_query("What are the slab rates for 18 lakh income?")
