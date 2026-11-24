"""Internal data models for the tax calculation engine.

These are plain dataclasses/dicts-friendly structures; Pydantic schemas at API boundary
handle validation/serialization. Keeping engine models simple makes the engine testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Regime = Literal["old", "new"]
AgeCategory = Literal["below_60", "senior_60_to_79", "super_senior_80_plus"]
TaxpayerType = Literal["individual", "huf"]


@dataclass
class SalaryInput:
    basic_salary: float = 0.0
    hra_received: float = 0.0
    special_allowance: float = 0.0
    other_allowances: float = 0.0
    bonus: float = 0.0
    professional_tax_paid: float = 0.0
    employer_nps_contribution: float = 0.0  # 80CCD(2)
    other_taxable_components: float = 0.0
    # HRA exemption inputs (old regime)
    rent_paid_per_year: float = 0.0
    is_metro: bool = False


@dataclass
class HousePropertyInput:
    # Simplified: single self-occupied or let-out property for v1, extensible later.
    property_type: Literal["self_occupied", "let_out"] = "self_occupied"
    annual_rent_received: float = 0.0
    municipal_taxes_paid: float = 0.0
    home_loan_interest: float = 0.0
    standard_deduction_rate: float = 0.30  # 30% on NAV for let-out


@dataclass
class CapitalGainEntry:
    asset_type: Literal[
        "equity_stcg_111a",
        "equity_ltcg_112a",
        "debt_mf_post_2023_04_01",
        "property_ltcg",
        "other_ltcg",
        "other_stcg",
    ]
    gain_amount: float = 0.0  # positive gain; losses handled separately if needed
    # For property grandfathering
    acquired_before_2024_07_23: bool = False
    indexed_cost_available: bool = False
    indexed_gain_amount: float | None = None  # if grandfathering option applies


@dataclass
class CapitalGainsInput:
    entries: list[CapitalGainEntry] = field(default_factory=list)


@dataclass
class BusinessIncomeInput:
    profits_from_business: float = 0.0
    professional_income: float = 0.0
    presumptive_income: float = 0.0  # if user computed under 44AD/44ADA; treated as business/professional income
    presumptive_scheme: Literal["none", "44ad", "44ada", "44ae"] = "none"


@dataclass
class OtherIncomeInput:
    savings_account_interest: float = 0.0
    fixed_deposit_interest: float = 0.0
    dividend_income: float = 0.0
    other_taxable_income: float = 0.0
    family_pension: float = 0.0


@dataclass
class DeductionsInput:
    section_80c: float = 0.0
    section_80ccd_1b: float = 0.0
    section_80d_self_family: float = 0.0
    section_80d_self_family_is_senior: bool = False
    section_80d_parents: float = 0.0
    section_80d_parents_is_senior: bool = False
    section_80d_preventive_checkup: float = 0.0
    section_80g_eligible_donation: float = 0.0
    section_80tta: float = 0.0
    section_80ttb: float = 0.0
    other_deductions: float = 0.0  # extensibility; must be explained in breakdown
    other_deductions_description: str = ""


@dataclass
class TaxpayerProfile:
    taxpayer_type: TaxpayerType = "individual"
    age_category: AgeCategory = "below_60"
    resident: bool = True
    financial_year: str = "2026-27"
    selected_regime: Regime | None = None  # for single-regime calc; compare computes both


@dataclass
class TaxCalculationInput:
    profile: TaxpayerProfile = field(default_factory=TaxpayerProfile)
    salary: SalaryInput = field(default_factory=SalaryInput)
    house_property: HousePropertyInput = field(default_factory=HousePropertyInput)
    capital_gains: CapitalGainsInput = field(default_factory=CapitalGainsInput)
    business: BusinessIncomeInput = field(default_factory=BusinessIncomeInput)
    other_income: OtherIncomeInput = field(default_factory=OtherIncomeInput)
    deductions: DeductionsInput = field(default_factory=DeductionsInput)


def money(value: Any) -> float:
    """Coerce to float and guard against NaN/inf/None."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if v != v or v in (float("inf"), float("-inf")):  # NaN/inf
        return 0.0
    return v


def clamp_non_negative(value: Any) -> float:
    return max(0.0, money(value))
