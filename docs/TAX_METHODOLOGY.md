# Tax Calculation Methodology

## Scope

This document describes the calculation methodology implemented by the tax engine for **FY 2026-27 (AY 2027-28)**. The engine is an estimator for common individual/HUF scenarios and is **not** a substitute for professional tax advice.

## Rule Configuration

Rules are stored in versioned JSON files:

- `backend/app/tax_engine/rules/fy_2026_27.json`

Each config includes metadata: financial year, assessment year, verification date/status, sources, and `requires_verification` notes.

## Verified Public Sources (used for research)

- Tax Garden - Income Tax Slab Rates FY 2026-27 (AY 2027-28): https://taxgarden.in/blog/income-tax-slab-rates-fy-2026-27-ay-2027-28
- Tax Garden - Section 87A rebate: https://taxgarden.in/blog/section-87a-rebate-ay-2026-27-eligibility-limit
- Tax Garden - Deductions allowed in new tax regime: https://taxgarden.in/blog/deductions-allowed-new-tax-regime-section-115bac-ay-2026-27
- Bajaj Housing Finance - Income Tax Slabs FY 2026-27: https://www.bajajhousingfinance.in/income-tax-slab

> Before production/filing use, confirm against official Income Tax Department/CBDT/Finance Act notifications.

## Regimes

### New Regime (default, Section 115BAC / ITA 2025 corresponding provisions)

| Taxable Income | Rate |
|---:|---:|
| Up to ₹4,00,000 | 0% |
| ₹4,00,001 - ₹8,00,000 | 5% |
| ₹8,00,001 - ₹12,00,000 | 10% |
| ₹12,00,001 - ₹16,00,000 | 15% |
| ₹16,00,001 - ₹20,00,000 | 20% |
| ₹20,00,001 - ₹24,00,000 | 25% |
| Above ₹24,00,000 | 30% |

### Old Regime

| Taxable Income | <60 | 60-79 | 80+ |
|---:|---:|---:|---:|
| Basic exemption | ₹2,50,000 | ₹3,00,000 | ₹5,00,000 |
| 5% slab | ₹2.5L-₹5L | ₹3L-₹5L | — |
| 20% slab | ₹5L-₹10L | ₹5L-₹10L | ₹5L-₹10L |
| 30% slab | >₹10L | >₹10L | >₹10L |

## Calculation Flow

1. **Salary income**: gross salary components minus exemptions/deductions.
   - Standard deduction: ₹75,000 (new) / ₹50,000 (old), applied to salary/pension.
   - HRA exemption (old regime only): least of actual HRA, rent paid minus 10% of salary (Basic+DA as entered), 50% metro / 40% non-metro of salary.
   - Professional tax: deductible in old regime; not in new regime.

2. **House property**:
   - Self-occupied: NAV 0; home loan interest deductible up to ₹2,00,000 in old regime; not deductible in new regime.
   - Let-out: NAV = rent - municipal taxes; standard deduction 30% of NAV; interest deductible. New regime: let-out interest allowed but loss set-off against other heads restricted (engine flags carry-forward).

3. **Capital gains**:
   - Equity STCG (111A, STT paid): 20%.
   - Equity LTCG (112A): 12.5% above ₹1,25,000 annual exemption.
   - Property LTCG: 12.5% without indexation; optional grandfathering for pre-23-Jul-2024 acquisition (resident individual/HUF) if indexed gain provided - lower tax option selected.
   - Other LTCG: 12.5%.
   - Other STCG: slab rates.
   - Debt MF acquired on/after 1-Apr-2023: taxed at slab rates (deemed short-term treatment assumption; flagged for verification).

4. **Business/professional income**: profits + professional + presumptive income as entered.

5. **Other sources**: savings interest, FD interest, dividends, other taxable income, family pension (net of 57(iia) deduction).

6. **Gross Total Income**: sum of heads, with special-rate capital gains handled separately for tax computation.

7. **Chapter VI-A deductions** (regime-aware): applied against normal income; not against special-rate capital gains.

8. **Tax computation**:
   - Slab tax on normal taxable income.
   - Special-rate tax on applicable capital gains.
   - Section 87A rebate: resident individuals only. New regime: taxable income <= ₹12,00,000 => rebate up to ₹60,000 on normal slab tax; marginal relief above ₹12L caps normal tax at excess over ₹12L. Old regime: taxable income <= ₹5,00,000 => rebate up to ₹12,500. Rebate not applied against special-rate capital gains tax.
   - Surcharge: regime-specific thresholds; new regime capped at 25%; old regime up to 37%. Special-rate surcharge capped at 15% for applicable components. Marginal relief applied with conservative approximation in complex cases.
   - Health & Education Cess: 4% on tax+surcharge.
   - Final rounding: nearest ₹10 (Section 288B style).

## Assumptions / Limitations

- **Not legal/tax advice**. Estimates only.
- Capital loss set-off/carry-forward is not fully modeled.
- Exemptions under sections 54/54EC/54F, detailed 80G category limits, agricultural income integration, AMT, and other advanced cases are not fully modeled.
- 80G is simplified: uses user-entered eligible donation amount with basic cap guards.
- Surcharge marginal relief is approximated where exact threshold-tax recomputation is complex.
- Debt MF "deemed STCG" treatment is an implementation assumption; verify by acquisition date and applicable law.
- Senior/super-senior slab selection is based on age category input; birth-date-based assessment-year logic is not implemented.
- Rounding and intermediate precision may differ slightly from other calculators.

## Testing

Unit tests cover slabs, 87A rebate, marginal relief, surcharge, cess, capital gains, deductions, HRA, home loan, senior slabs, and comparison. Integration tests cover core API endpoints. See `backend/tests/`.
