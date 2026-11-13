"""Integration tests for src/app.py — _reference_calculations guards and extraction."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app import _reference_calculations


# ---------------------------------------------------------------------------
# Guard tests — S8-A (real estate) and S8-B (residential status)
# ---------------------------------------------------------------------------

class TestCalculatorGuards:
    def test_real_estate_query_suppressed(self):
        q = (
            "I bought a residential property for Rs. 80,00,000 in 2018 and sold it in "
            "FY 2024-25 for Rs. 1,20,00,000. Compute the capital gains tax due (you may "
            "state your assumptions on indexation clearly)."
        )
        assert _reference_calculations(q) == ""

    def test_residential_status_query_suppressed(self):
        q = (
            "Mr. B is an Indian citizen who has been living outside India for the last "
            "11 years. He visited India for 130 days in FY 2024-25. His Indian salary is "
            "8,00,000 and foreign income is 40,00,000. Determine his residential status "
            "and compute his tax liability."
        )
        assert _reference_calculations(q) == ""

    def test_salary_query_not_suppressed_by_real_estate_guard(self):
        q = "Compute tax for a salaried individual earning 18 lakh under the new regime."
        result = _reference_calculations(q)
        assert result != ""
        assert "215,800" in result

    def test_salary_query_not_suppressed_by_residency_guard(self):
        q = "Calculate tax for salary of 18 lakh under new regime for FY 2024-25."
        result = _reference_calculations(q)
        assert result != ""

    def test_accommodation_in_salary_not_suppressed(self):
        # "house" appears but no capital-gain adjacency — should NOT be suppressed
        q = "Compute tax for a salaried person earning 20 lakh who has perquisite for house accommodation worth 2 lakh."
        result = _reference_calculations(q)
        assert result != ""


# ---------------------------------------------------------------------------
# Extraction tests — S8-E (other_income, sec80c, sec80d)
# ---------------------------------------------------------------------------

class TestExtractionS8E:
    def test_interest_income_added_to_taxable_income(self):
        # Salary 24L + interest 3L = normal taxable 26.25L (new regime: 24-0.75+3=26.25)
        # Without interest: normal = 23.25L; with interest: normal = 26.25L
        q = (
            "Mr. A has salary 24,00,000 and interest income 3,00,000. "
            "Compute tax under new regime."
        )
        result = _reference_calculations(q)
        # 26.25L taxable: 0-3L Nil; 3-7L 5%=20K; 7-10L 10%=30K; 10-12L 15%=30K;
        # 12-15L 20%=60K; 15-26.25L 30%=337.5K → slab=477.5K; cess=19.1K → total≈496.6K
        assert "NEW" in result
        assert "26,25,000" in result or "2,625,000" in result

    def test_sec80c_deducted_in_old_regime(self):
        # Salary 24L, PPF 2L → 80C capped 1.5L deducted from old regime
        q = (
            "Mr. A has salary 24,00,000 and invests 2,00,000 in PPF. "
            "Compute tax under both old and new regimes."
        )
        result = _reference_calculations(q)
        assert "OLD" in result
        assert "Section 80C" in result or "1,50,000" in result

    def test_sec80d_deducted_in_old_regime(self):
        # Salary 24L, medical insurance 75,000 → 80D deducted
        q = (
            "Mr. A has salary 24,00,000 and pays medical insurance premium 75,000. "
            "Compute tax under old and new regimes."
        )
        result = _reference_calculations(q)
        assert "OLD" in result
        assert "Section 80D" in result or "75,000" in result

    def test_sub_lakh_amount_does_not_displace_salary(self):
        # 18L salary + 75K health insurance; max must still be 18L not 75K
        q = (
            "Salaried individual earns 18 lakh. Medical insurance premium 75,000. "
            "Compute tax new regime."
        )
        result = _reference_calculations(q)
        assert "1,800,000" in result or "18,00,000" in result
        assert "215,800" in result

    def test_q_c01_new_regime_full(self):
        # Full Q-C01: salary 24L + LTCG 6L + STCG 2L + interest 3L + PPF 2L + 80D 75K
        q = (
            "Mr. A (resident, 45) has: (i) salary 24,00,000; (ii) long-term capital gains "
            "6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital "
            "gains on equity 2,00,000; (iv) interest income 3,00,000. He invests 2,00,000 in PPF "
            "and pays 75,000 medical insurance for his family. Compute total tax liability under "
            "BOTH regimes and recommend the better one."
        )
        result = _reference_calculations(q)
        assert "NEW" in result
        assert "OLD" in result
        # New regime: normal taxable = 24L - 0.75L + 3L = 26.25L
        # LTCG taxable = 6L - 1.25L = 4.75L; STCG = 2L
        # Slab on 26.25L = 477,500; LTCG = 59,375; STCG = 40,000; base = 576,875
        # cess = 23,075 → total = 599,950
        assert "5,99,950" in result or "599,950" in result

    def test_q_c01_old_regime_full(self):
        q = (
            "Mr. A (resident, 45) has: (i) salary 24,00,000; (ii) long-term capital gains "
            "6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital "
            "gains on equity 2,00,000; (iv) interest income 3,00,000. He invests 2,00,000 in PPF "
            "and pays 75,000 medical insurance for his family. Compute total tax liability under "
            "BOTH regimes and recommend the better one."
        )
        result = _reference_calculations(q)
        assert "OLD" in result
        # Old regime: normal = 24L - 0.5L + 3L - 1.5L (80C cap) - 0.75L (80D) = 24.25L
        # LTCG = 4.75L; STCG = 2L
        # Slab on 24.25L = 540,000; LTCG = 59,375; STCG = 40,000; base = 639,375
        # cess = 25,575 → total = 664,950
        assert "6,64,950" in result or "664,950" in result


# ---------------------------------------------------------------------------
# Rupee-symbol (₹) prefix tests — S8-F (extraction with ₹ prefix)
# ---------------------------------------------------------------------------

class TestRupeePrefix:
    def test_ltcg_with_rupee_prefix(self):
        # LTCG amount preceded by ₹ symbol (as in actual Q-C01 question)
        q = (
            "salary ₹24,00,000 long-term capital gains ₹6,00,000 on listed equity shares "
            "sold after 23 July 2024 interest income ₹3,00,000 compute tax new regime"
        )
        result = _reference_calculations(q)
        assert "LTCG" in result
        assert "59,375" in result  # (6L - 1.25L) × 12.5%

    def test_interest_with_rupee_prefix(self):
        # Interest income preceded by ₹
        q = "salary ₹24,00,000 interest income ₹3,00,000 compute tax new regime"
        result = _reference_calculations(q)
        assert "26,25,000" in result or "2,625,000" in result  # 24L - 0.75L + 3L

    def test_house_loan_with_rupee_prefix(self):
        # House loan interest preceded by ₹ (as in actual Q-M05 question)
        q = (
            "salary ₹15,00,000 home-loan interest of ₹2,00,000 compute old and new regime"
        )
        result = _reference_calculations(q)
        assert "OLD" in result
        assert "195,000" in result or "1,95,000" in result  # old regime correct total

    def test_q_c01_with_rupee_prefixes_new(self):
        # Actual Q-C01 question text (with ₹ symbols)
        q = (
            "Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains "
            "₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital "
            "gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF "
            "and pays ₹75,000 medical insurance for his family. Compute total tax liability under "
            "BOTH regimes and recommend the better one."
        )
        result = _reference_calculations(q)
        assert "5,99,950" in result or "599,950" in result

    def test_q_c01_with_rupee_prefixes_old(self):
        q = (
            "Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains "
            "₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital "
            "gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF "
            "and pays ₹75,000 medical insurance for his family. Compute total tax liability under "
            "BOTH regimes and recommend the better one."
        )
        result = _reference_calculations(q)
        assert "6,64,950" in result or "664,950" in result
