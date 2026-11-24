"""Unit tests for the tax calculation engine."""
from app.tax_engine.calculator import calculate_comparison, calculate_regime
from app.tax_engine.models import (
    BusinessIncomeInput,
    CapitalGainEntry,
    CapitalGainsInput,
    DeductionsInput,
    HousePropertyInput,
    OtherIncomeInput,
    SalaryInput,
    TaxCalculationInput,
    TaxpayerProfile,
)


def _inp(**kwargs):
    profile = kwargs.pop("profile", TaxpayerProfile(financial_year="2026-27", resident=True, age_category="below_60"))
    return TaxCalculationInput(profile=profile, **kwargs)


def test_new_regime_zero_tax_up_to_12l_taxable():
    # Salary 12,75,000 - 75,000 std deduction = 12,00,000 taxable => 0
    inp = _inp(salary=SalaryInput(basic_salary=1275000))
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["total_taxable_income"] == 1200000.0
    assert r["tax_computation"]["final_tax_liability"] == 0


def test_new_regime_15l_salary():
    # 15,00,000 - 75,000 = 14,25,000 taxable. Tax: 20k+40k+33750=93750; cess 3750; total 97500
    inp = _inp(salary=SalaryInput(basic_salary=1500000))
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["total_taxable_income"] == 1425000.0
    assert r["tax_computation"]["slab_tax"] == 93750.0
    assert r["tax_computation"]["cess"] == 3750.0
    assert r["tax_computation"]["final_tax_liability"] == 97500


def test_old_regime_15l_salary_no_deductions():
    # 15,00,000 - 50,000 = 14,50,000. Tax: 12500 + 100000 + 135000 = 247500; cess 9900; total 257400
    inp = _inp(salary=SalaryInput(basic_salary=1500000))
    r = calculate_regime(inp, "old")
    assert r["tax_computation"]["total_taxable_income"] == 1450000.0
    assert r["tax_computation"]["final_tax_liability"] == 257400


def test_comparison_recommends_new_for_simple_15l():
    inp = _inp(salary=SalaryInput(basic_salary=1500000))
    c = calculate_comparison(inp)
    assert c["recommended_regime"] == "new"
    assert c["savings"] == 159900.0
    assert len(c["comparison_table"]) == 8


def test_marginal_relief_87a_new_regime():
    # 12,85,000 salary -> 12,10,000 taxable. Slab tax 61500. Excess 10000. Relief 51500. Tax 10000+cess 400=10400
    inp = _inp(salary=SalaryInput(basic_salary=1285000))
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["total_taxable_income"] == 1210000.0
    assert r["tax_computation"]["slab_tax"] == 61500.0
    assert r["tax_computation"]["marginal_relief_87a"] == 51500.0
    assert r["tax_computation"]["final_tax_liability"] == 10400


def test_87a_not_available_to_non_resident():
    inp = _inp(
        profile=TaxpayerProfile(financial_year="2026-27", resident=False, age_category="below_60"),
        salary=SalaryInput(basic_salary=1275000),
    )
    r = calculate_regime(inp, "new")
    # Taxable 12L, slab tax 60k, but no 87A rebate for non-resident
    assert r["tax_computation"]["rebate_87a"] == 0.0
    assert r["tax_computation"]["final_tax_liability"] > 0


def test_old_regime_87a_rebate_up_to_5l():
    inp = _inp(salary=SalaryInput(basic_salary=500000))
    r = calculate_regime(inp, "old")
    # taxable 4.5L, slab tax 10000, rebate 10000 => 0
    assert r["tax_computation"]["final_tax_liability"] == 0


def test_equity_ltcg_112a_exemption_and_rate():
    # 10L salary -> taxable normal 9.25L. 2L LTCG112A => 75k taxable at 12.5% = 9375
    inp = _inp(
        salary=SalaryInput(basic_salary=1000000),
        capital_gains=CapitalGainsInput(entries=[CapitalGainEntry(asset_type="equity_ltcg_112a", gain_amount=200000)]),
    )
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["special_rate_tax"] == 9375.0
    assert r["income"]["capital_gains"]["ltcg_112a_exemption_used"] == 125000.0


def test_equity_stcg_111a_20_percent():
    inp = _inp(
        salary=SalaryInput(basic_salary=500000),
        capital_gains=CapitalGainsInput(entries=[CapitalGainEntry(asset_type="equity_stcg_111a", gain_amount=100000)]),
    )
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["special_rate_tax"] == 20000.0


def test_80c_deduction_old_regime_only():
    inp_old = _inp(salary=SalaryInput(basic_salary=1500000), deductions=DeductionsInput(section_80c=150000))
    inp_new = _inp(salary=SalaryInput(basic_salary=1500000), deductions=DeductionsInput(section_80c=150000))
    r_old = calculate_regime(inp_old, "old")
    r_new = calculate_regime(inp_new, "new")
    assert r_old["deductions"]["total_allowed"] >= 150000
    # new regime should not allow 80C
    assert all(item["section"] != "80C" or item["allowed"] == 0 for item in r_new["deductions"]["items"] if item["section"] == "80C")


def test_hra_exemption_old_regime():
    # Basic 600000, HRA 240000, rent 300000, non-metro
    # exemption min(240000, 300000-60000=240000, 40%*600000=240000)=240000
    inp = _inp(salary=SalaryInput(basic_salary=600000, hra_received=240000, rent_paid_per_year=300000, is_metro=False))
    r = calculate_regime(inp, "old")
    assert r["income"]["salary"]["hra_exemption"]["exempt"] == 240000.0


def test_hra_not_exempt_new_regime():
    inp = _inp(salary=SalaryInput(basic_salary=600000, hra_received=240000, rent_paid_per_year=300000, is_metro=False))
    r = calculate_regime(inp, "new")
    assert r["income"]["salary"]["hra_exemption"]["exempt"] == 0.0


def test_self_occupied_home_loan_interest_old_only():
    inp_old = _inp(salary=SalaryInput(basic_salary=1000000), house_property=HousePropertyInput(property_type="self_occupied", home_loan_interest=200000))
    inp_new = _inp(salary=SalaryInput(basic_salary=1000000), house_property=HousePropertyInput(property_type="self_occupied", home_loan_interest=200000))
    r_old = calculate_regime(inp_old, "old")
    r_new = calculate_regime(inp_new, "new")
    assert r_old["income"]["house_property"]["income_or_loss"] == -200000.0
    assert r_new["income"]["house_property"]["income_or_loss"] == 0.0


def test_surcharge_applies_above_50l():
    # High income to trigger surcharge
    inp = _inp(salary=SalaryInput(basic_salary=6000000))
    r = calculate_regime(inp, "new")
    assert r["tax_computation"]["surcharge"]["surcharge"] > 0
    assert r["tax_computation"]["surcharge"]["rate_percent"] >= 10.0


def test_cess_is_4_percent():
    inp = _inp(salary=SalaryInput(basic_salary=1500000))
    r = calculate_regime(inp, "new")
    taxable_base = r["tax_computation"]["tax_after_rebate_and_relief"] + r["tax_computation"]["surcharge"]["surcharge"]
    assert abs(r["tax_computation"]["cess"] - taxable_base * 0.04) < 0.01


def test_standard_deduction_new_vs_old():
    inp = _inp(salary=SalaryInput(basic_salary=1000000))
    r_new = calculate_regime(inp, "new")
    r_old = calculate_regime(inp, "old")
    assert r_new["income"]["salary"]["standard_deduction"] == 75000.0
    assert r_old["income"]["salary"]["standard_deduction"] == 50000.0


def test_senior_citizen_old_regime_slabs():
    inp = _inp(
        profile=TaxpayerProfile(financial_year="2026-27", age_category="senior_60_to_79", resident=True),
        salary=SalaryInput(basic_salary=600000),
    )
    r = calculate_regime(inp, "old")
    # 6L - 50k std ded = 5.5L taxable. Senior: 0-3L nil, 3-5L 5%=10k, 5-5.5L 20%=10k = 20k tax. Cess 800. Total 20800
    assert r["tax_computation"]["total_taxable_income"] == 550000.0
    assert r["tax_computation"]["final_tax_liability"] == 20800


def test_family_pension_deduction_new_regime():
    inp = _inp(other_income=OtherIncomeInput(family_pension=100000))
    r = calculate_regime(inp, "new")
    # 1/3 of 100000 = 33333.33, cap 25000 in new regime
    assert r["income"]["other_sources"]["family_pension"]["deduction"] == 25000.0
