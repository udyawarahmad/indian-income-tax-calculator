"""Pydantic schemas for tax API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


AgeCategory = Literal["below_60", "senior_60_to_79", "super_senior_80_plus"]
TaxpayerType = Literal["individual", "huf"]
Regime = Literal["old", "new"]
PropertyType = Literal["self_occupied", "let_out"]


class SalaryInputSchema(BaseModel):
    basic_salary: float = Field(0, ge=0)
    hra_received: float = Field(0, ge=0)
    special_allowance: float = Field(0, ge=0)
    other_allowances: float = Field(0, ge=0)
    bonus: float = Field(0, ge=0)
    professional_tax_paid: float = Field(0, ge=0)
    employer_nps_contribution: float = Field(0, ge=0)
    other_taxable_components: float = Field(0, ge=0)
    rent_paid_per_year: float = Field(0, ge=0)
    is_metro: bool = False


class HousePropertyInputSchema(BaseModel):
    property_type: PropertyType = "self_occupied"
    annual_rent_received: float = Field(0, ge=0)
    municipal_taxes_paid: float = Field(0, ge=0)
    home_loan_interest: float = Field(0, ge=0)


class CapitalGainEntrySchema(BaseModel):
    asset_type: Literal[
        "equity_stcg_111a",
        "equity_ltcg_112a",
        "debt_mf_post_2023_04_01",
        "property_ltcg",
        "other_ltcg",
        "other_stcg",
    ]
    gain_amount: float = Field(0, ge=0)
    acquired_before_2024_07_23: bool = False
    indexed_cost_available: bool = False
    indexed_gain_amount: float | None = Field(default=None)


class CapitalGainsInputSchema(BaseModel):
    entries: list[CapitalGainEntrySchema] = Field(default_factory=list)


class BusinessIncomeInputSchema(BaseModel):
    profits_from_business: float = Field(0, ge=0)
    professional_income: float = Field(0, ge=0)
    presumptive_income: float = Field(0, ge=0)
    presumptive_scheme: Literal["none", "44ad", "44ada", "44ae"] = "none"


class OtherIncomeInputSchema(BaseModel):
    savings_account_interest: float = Field(0, ge=0)
    fixed_deposit_interest: float = Field(0, ge=0)
    dividend_income: float = Field(0, ge=0)
    other_taxable_income: float = Field(0, ge=0)
    family_pension: float = Field(0, ge=0)


class DeductionsInputSchema(BaseModel):
    section_80c: float = Field(0, ge=0)
    section_80ccd_1b: float = Field(0, ge=0)
    section_80d_self_family: float = Field(0, ge=0)
    section_80d_self_family_is_senior: bool = False
    section_80d_parents: float = Field(0, ge=0)
    section_80d_parents_is_senior: bool = False
    section_80d_preventive_checkup: float = Field(0, ge=0)
    section_80g_eligible_donation: float = Field(0, ge=0)
    section_80tta: float = Field(0, ge=0)
    section_80ttb: float = Field(0, ge=0)
    other_deductions: float = Field(0, ge=0)
    other_deductions_description: str = ""


class TaxpayerProfileSchema(BaseModel):
    taxpayer_type: TaxpayerType = "individual"
    age_category: AgeCategory = "below_60"
    resident: bool = True
    financial_year: str = "2026-27"
    selected_regime: Literal["old", "new", "compare"] | None = None

    @field_validator("financial_year")
    @classmethod
    def validate_fy(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 10:
            raise ValueError("Invalid financial year")
        return v


class TaxCalculationRequest(BaseModel):
    profile: TaxpayerProfileSchema = Field(default_factory=TaxpayerProfileSchema)
    salary: SalaryInputSchema = Field(default_factory=SalaryInputSchema)
    house_property: HousePropertyInputSchema = Field(default_factory=HousePropertyInputSchema)
    capital_gains: CapitalGainsInputSchema = Field(default_factory=CapitalGainsInputSchema)
    business: BusinessIncomeInputSchema = Field(default_factory=BusinessIncomeInputSchema)
    other_income: OtherIncomeInputSchema = Field(default_factory=OtherIncomeInputSchema)
    deductions: DeductionsInputSchema = Field(default_factory=DeductionsInputSchema)
    regime: Literal["old", "new", "compare"] | None = None
    save_history: bool = False
    profile_id: str | None = None
    profile_name: str | None = None


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    age_category: AgeCategory = "below_60"
    resident: bool = True
    taxpayer_type: TaxpayerType = "individual"


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age_category: AgeCategory | None = None
    resident: bool | None = None
    taxpayer_type: TaxpayerType | None = None


class ProfileResponse(BaseModel):
    id: str
    name: str
    age_category: str
    resident: bool
    taxpayer_type: str
    created_at: str
    updated_at: str


class HistoryResponse(BaseModel):
    id: str
    profile_id: str | None
    profile_name: str | None
    financial_year: str
    regime: str
    gross_total_income: str
    total_tax_old: str | None
    total_tax_new: str | None
    recommended_regime: str | None
    created_at: str


class ApiError(BaseModel):
    detail: str
    errors: list[Any] | None = None
