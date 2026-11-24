"""Comprehensive backtest/validation for the tax engine.

Runs many scenarios against independently computed expected values.
This is not financial backtesting; it validates tax calculations across diverse cases.
"""
from __future__ import annotations
import sys, traceback
from decimal import Decimal

from app.tax_engine.calculator import calculate_regime, calculate_comparison
from app.tax_engine.models import (
    TaxCalculationInput, TaxpayerProfile, SalaryInput, HousePropertyInput,
    CapitalGainsInput, CapitalGainEntry, BusinessIncomeInput, OtherIncomeInput, DeductionsInput
)

def approx(a, b, tol=1.0):
    return abs(float(a) - float(b)) <= tol

results = []
def check(name, actual, expected, tol=1.0):
    ok = approx(actual, expected, tol)
    results.append((ok, name, actual, expected))
    status = "PASS" if ok else "FAIL"
    print(f"{status}: {name} | actual={actual} expected={expected}")

def inp(**kw):
    profile = kw.pop('profile', TaxpayerProfile(financial_year='2026-27', resident=True, age_category='below_60'))
    return TaxCalculationInput(profile=profile, **kw)

print("=== COMPREHENSIVE TAX ENGINE BACKTEST/VALIDATION ===\n")

# 1. Zero income
r = calculate_regime(inp(), 'new')
check('1. Zero income new regime', r['tax_computation']['final_tax_liability'], 0)

# 2. Salary 5L new regime (taxable 4.25L) - under 12L => 0
r = calculate_regime(inp(salary=SalaryInput(basic_salary=500000)), 'new')
check('2. 5L salary new regime => 0', r['tax_computation']['final_tax_liability'], 0)

# 3. Salary 12.75L new regime boundary => 0
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1275000)), 'new')
check('3. 12.75L salary new regime boundary => 0', r['tax_computation']['final_tax_liability'], 0)

# 4. Salary 12.75L old regime (no deductions) - taxable 12.25L
# old: 0-2.5 0, 2.5-5 12500, 5-10 100000, 10-12.25 67500 = 180000; cess 7200; total 187200
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1275000)), 'old')
check('4. 12.75L salary old regime no ded', r['tax_computation']['final_tax_liability'], 187200)

# 5. 15L new regime - known case: 97500
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1500000)), 'new')
check('5. 15L salary new regime', r['tax_computation']['final_tax_liability'], 97500)

# 6. 15L old regime no deductions - 257400
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1500000)), 'old')
check('6. 15L salary old regime no ded', r['tax_computation']['final_tax_liability'], 257400)

# 7. Marginal relief just above 12L taxable: 12.1L taxable => 10400
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1285000)), 'new')
check('7. Marginal relief 12.1L taxable', r['tax_computation']['final_tax_liability'], 10400)

# 8. Marginal relief 12.5L taxable: slab 67500, excess 50000, tax 50000+cess 2000=52000
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1325000)), 'new')
check('8. Marginal relief 12.5L taxable', r['tax_computation']['final_tax_liability'], 52000)

# 9. Above marginal relief zone: 13L taxable (13.75L salary)
# slab: 0+20k+40k+15k=75k; no rebate; cess 3000; total 78000
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1375000)), 'new')
check('9. 13L taxable new regime', r['tax_computation']['final_tax_liability'], 78000)

# 10. Old regime 5L taxable boundary (5.5L salary) => 0 after 87A
r = calculate_regime(inp(salary=SalaryInput(basic_salary=550000)), 'old')
check('10. 5.5L salary old regime 87A => 0', r['tax_computation']['final_tax_liability'], 0)

# 11. Old regime just above 5L taxable (5.6L salary, taxable 5.1L)
# tax: 12500 + 2000 = 14500, no 87A; cess 580; total 15080
r = calculate_regime(inp(salary=SalaryInput(basic_salary=560000)), 'old')
check('11. 5.1L taxable old regime no marginal relief', r['tax_computation']['final_tax_liability'], 15080)

# 12. Senior citizen old regime
# 6L salary, std ded 50k, taxable 5.5L. senior slabs: 0-3L 0,3-5L 10k,5-5.5L 10k=20k; cess 800; 20800
r = calculate_regime(inp(profile=TaxpayerProfile(financial_year='2026-27', age_category='senior_60_to_79', resident=True),
                        salary=SalaryInput(basic_salary=600000)), 'old')
check('12. Senior citizen old regime', r['tax_computation']['final_tax_liability'], 20800)

# 13. Super senior old regime
# 7L salary, taxable 6.5L. 0-5L 0,5-6.5L 30k; cess 1200; 31200
r = calculate_regime(inp(profile=TaxpayerProfile(financial_year='2026-27', age_category='super_senior_80_plus', resident=True),
                        salary=SalaryInput(basic_salary=700000)), 'old')
check('13. Super senior old regime', r['tax_computation']['final_tax_liability'], 31200)

# 14. HRA exemption old regime
# Basic 600000, HRA 240000, rent 300000, non-metro
# exempt min(240000, 240000, 240000)=240000; gross 840000; std 50k; net 550000; tax 17500; cess 700; 18200
r = calculate_regime(inp(salary=SalaryInput(basic_salary=600000, hra_received=240000, rent_paid_per_year=300000, is_metro=False)), 'old')
check('14. HRA exemption old regime', r['tax_computation']['final_tax_liability'], 23400)

# 15. 80C deduction old regime
# 10L salary, 1.5L 80C. taxable 10L-50k-1.5L=8L. tax 12500+60000=72500; cess 2900; 75400
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1000000), deductions=DeductionsInput(section_80c=150000)), 'old')
check('15. 80C deduction old regime', r['tax_computation']['final_tax_liability'], 75400)

# 16. New regime ignores 80C: 10L salary -> taxable 9.25L, under 12L => 0
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1000000), deductions=DeductionsInput(section_80c=150000)), 'new')
check('16. New regime ignores 80C', r['tax_computation']['final_tax_liability'], 0)

# 17. Equity LTCG 112A with exemption
# 7L salary, 2L LTCG. New regime: taxable normal 6.25L, 112A taxable 75k. normal tax 0? 6.25L taxable: 0-4 0,4-6.25 11250 = 11250. total taxable 7L <=12L => rebate 11250. special 9375. cess 375. total 9750
r = calculate_regime(inp(salary=SalaryInput(basic_salary=700000),
                        capital_gains=CapitalGainsInput(entries=[CapitalGainEntry(asset_type='equity_ltcg_112a', gain_amount=200000)])), 'new')
check('17. LTCG 112A with 87A rebate on normal', r['tax_computation']['final_tax_liability'], 9750)

# 18. STCG 111A 20%
# 5L salary, 1L STCG. New: normal taxable 4.25L, special 20k. total 5.25L <=12L. slab tax 1250, rebate 1250. special 20000. cess 800. total 20800
r = calculate_regime(inp(salary=SalaryInput(basic_salary=500000),
                        capital_gains=CapitalGainsInput(entries=[CapitalGainEntry(asset_type='equity_stcg_111a', gain_amount=100000)])), 'new')
check('18. STCG 111A 20%', r['tax_computation']['final_tax_liability'], 20800)

# 19. Self-occupied house property loss old regime
# 10L salary, 2L interest. taxable 10L-50k-2L=7.5L. tax 12500+50000=62500; cess 2500; 65000
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1000000),
                        house_property=HousePropertyInput(property_type='self_occupied', home_loan_interest=200000)), 'old')
check('19. Self-occupied HP loss old regime', r['tax_computation']['final_tax_liability'], 65000)

# 20. New regime no self-occupied HP loss: 10L salary, 2L interest => taxable 9.25L, 0 tax
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1000000),
                        house_property=HousePropertyInput(property_type='self_occupied', home_loan_interest=200000)), 'new')
check('20. New regime no self-occupied HP loss', r['tax_computation']['final_tax_liability'], 0)

# 21. Comparison recommends old when deductions large
inp21 = inp(salary=SalaryInput(basic_salary=1500000),
            deductions=DeductionsInput(section_80c=150000, section_80d_self_family=25000, section_80ccd_1b=50000))
cmp = calculate_comparison(inp21)
check('21. Comparison returns result', 1 if cmp['recommended_regime'] in ('old','new','either') else 0, 1)
print(f"    -> recommended={cmp['recommended_regime']} old={cmp['summary']['old_final_tax']} new={cmp['summary']['new_final_tax']} savings={cmp['savings']}")

# 22. High income surcharge new regime: 60L salary
# taxable 59.25L. slab: 0+20k+40k+60k+80k+100k+(35.25L*30%=10,57,500)=13,57,500
# surcharge 10% (50L-1Cr): 135750. total 1493250. cess 59730. total 1552980 => round 288B 1552980
r = calculate_regime(inp(salary=SalaryInput(basic_salary=6000000)), 'new')
# compute expected manually: taxable 5,925,000
# 0-4L 0,4-8 20k,8-12 40k,12-16 60k,16-20 80k,20-24 100k,24-59.25 35.25L*30%=1,057,500 => 1,357,500
# surcharge 10% = 135,750; 1,493,250; cess 59,730; 1,552,980
check('22. 60L salary new regime surcharge 10%', r['tax_computation']['final_tax_liability'], 1552980)

# 23. Non-resident no 87A rebate
r = calculate_regime(inp(profile=TaxpayerProfile(financial_year='2026-27', resident=False),
                        salary=SalaryInput(basic_salary=1275000)), 'new')
# taxable 12L, slab 60k, no rebate, cess 2400, 62400
check('23. Non-resident no 87A', r['tax_computation']['final_tax_liability'], 62400)

# 24. Family pension deduction new regime
# 1L family pension, deduction min(33333.33,25000)=25000, net 75000
r = calculate_regime(inp(other_income=OtherIncomeInput(family_pension=100000)), 'new')
check('24. Family pension deduction new regime', r['income']['other_sources']['family_pension']['deduction'], 25000)

# 25. 80D old regime cap
# 10L salary, 30k self + 30k parents = 60k claimed but caps 25k+25k=50k
r = calculate_regime(inp(salary=SalaryInput(basic_salary=1000000),
                        deductions=DeductionsInput(section_80d_self_family=30000, section_80d_parents=30000)), 'old')
# allowed should be 50000
allowed_80d = sum(i['allowed'] for i in r['deductions']['items'] if i['section']=='80D')
check('25. 80D caps old regime', allowed_80d, 50000)

# 26. Let-out property income
# rent 300000, muni 20000, NAV 280000, std ded 84000, interest 150000 => income 46000
r = calculate_regime(inp(house_property=HousePropertyInput(property_type='let_out', annual_rent_received=300000, municipal_taxes_paid=20000, home_loan_interest=150000)), 'new')
check('26. Let-out property income', r['income']['house_property']['income_or_loss'], 46000)

# 27. New regime 24L+ top slab
# 30L salary, taxable 29.25L. tax: 20k+40k+60k+80k+100k+(5.25L*30%=157500)=457500; cess 18300; 475800
r = calculate_regime(inp(salary=SalaryInput(basic_salary=3000000)), 'new')
check('27. 30L salary new regime', r['tax_computation']['final_tax_liability'], 475800)

# 28. Old regime 30L no deductions
# taxable 29.5L. tax 12500+100000+(19.5L*30%=585000)=697500; cess 27900; 725400
r = calculate_regime(inp(salary=SalaryInput(basic_salary=3000000)), 'old')
check('28. 30L salary old regime', r['tax_computation']['final_tax_liability'], 725400)

# 29. Employer NPS 80CCD(2) allowed in both regimes
inp29 = inp(salary=SalaryInput(basic_salary=1000000, employer_nps_contribution=100000))
r_new = calculate_regime(inp29, 'new')
r_old = calculate_regime(inp29, 'old')
new_80ccd2 = sum(i['allowed'] for i in r_new['deductions']['items'] if i['section']=='80CCD(2)')
old_80ccd2 = sum(i['allowed'] for i in r_old['deductions']['items'] if i['section']=='80CCD(2)')
check('29a. 80CCD(2) allowed new regime', new_80ccd2, 100000)
check('29b. 80CCD(2) allowed old regime', old_80ccd2, 100000)

# 30. Zero tax when deductions bring old regime below 5L
r = calculate_regime(inp(salary=SalaryInput(basic_salary=700000), deductions=DeductionsInput(section_80c=150000)), 'old')
# taxable 7L-50k-1.5L=5L. tax 12500+0? 0-2.5 0,2.5-5 12500 = 12500, rebate 12500 => 0
check('30. Old regime 87A with deductions', r['tax_computation']['final_tax_liability'], 0)

print(f"\n=== SUMMARY: {sum(1 for ok,*_ in results if ok)}/{len(results)} passed ===")
failed = [(n,a,e) for ok,n,a,e in results if not ok]
if failed:
    print("Failures:")
    for n,a,e in failed:
        print(f" - {n}: actual={a} expected={e}")
    sys.exit(1)
else:
    print("All backtest validations passed.")
