import type { TaxCalculationRequest } from '../types';

export const defaultRequest = (): TaxCalculationRequest => ({
  profile: { taxpayer_type: 'individual', age_category: 'below_60', resident: true, financial_year: '2026-27', selected_regime: 'compare' },
  salary: { basic_salary: 0, hra_received: 0, special_allowance: 0, other_allowances: 0, bonus: 0, professional_tax_paid: 0, employer_nps_contribution: 0, other_taxable_components: 0, rent_paid_per_year: 0, is_metro: false },
  house_property: { property_type: 'self_occupied', annual_rent_received: 0, municipal_taxes_paid: 0, home_loan_interest: 0 },
  capital_gains: { entries: [] },
  business: { profits_from_business: 0, professional_income: 0, presumptive_income: 0, presumptive_scheme: 'none' },
  other_income: { savings_account_interest: 0, fixed_deposit_interest: 0, dividend_income: 0, other_taxable_income: 0, family_pension: 0 },
  deductions: { section_80c: 0, section_80ccd_1b: 0, section_80d_self_family: 0, section_80d_self_family_is_senior: false, section_80d_parents: 0, section_80d_parents_is_senior: false, section_80d_preventive_checkup: 0, section_80g_eligible_donation: 0, section_80tta: 0, section_80ttb: 0, other_deductions: 0, other_deductions_description: '' },
  regime: 'compare',
  save_history: false,
});
