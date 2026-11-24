export type AgeCategory = 'below_60' | 'senior_60_to_79' | 'super_senior_80_plus';
export type TaxpayerType = 'individual' | 'huf';
export type Regime = 'old' | 'new';
export type PropertyType = 'self_occupied' | 'let_out';

export interface SalaryInput {
  basic_salary: number; hra_received: number; special_allowance: number;
  other_allowances: number; bonus: number; professional_tax_paid: number;
  employer_nps_contribution: number; other_taxable_components: number;
  rent_paid_per_year: number; is_metro: boolean;
}
export interface HousePropertyInput {
  property_type: PropertyType; annual_rent_received: number;
  municipal_taxes_paid: number; home_loan_interest: number;
}
export interface CapitalGainEntry {
  asset_type: 'equity_stcg_111a'|'equity_ltcg_112a'|'debt_mf_post_2023_04_01'|'property_ltcg'|'other_ltcg'|'other_stcg';
  gain_amount: number; acquired_before_2024_07_23: boolean; indexed_cost_available: boolean; indexed_gain_amount?: number | null;
}
export interface CapitalGainsInput { entries: CapitalGainEntry[]; }
export interface BusinessIncomeInput { profits_from_business: number; professional_income: number; presumptive_income: number; presumptive_scheme: 'none'|'44ad'|'44ada'|'44ae'; }
export interface OtherIncomeInput { savings_account_interest: number; fixed_deposit_interest: number; dividend_income: number; other_taxable_income: number; family_pension: number; }
export interface DeductionsInput {
  section_80c: number; section_80ccd_1b: number; section_80d_self_family: number; section_80d_self_family_is_senior: boolean;
  section_80d_parents: number; section_80d_parents_is_senior: boolean; section_80d_preventive_checkup: number;
  section_80g_eligible_donation: number; section_80tta: number; section_80ttb: number;
  other_deductions: number; other_deductions_description: string;
}
export interface TaxpayerProfile {
  taxpayer_type: TaxpayerType; age_category: AgeCategory; resident: boolean; financial_year: string; selected_regime?: 'old'|'new'|'compare'|null;
}
export interface TaxCalculationRequest {
  profile: TaxpayerProfile; salary: SalaryInput; house_property: HousePropertyInput;
  capital_gains: CapitalGainsInput; business: BusinessIncomeInput; other_income: OtherIncomeInput;
  deductions: DeductionsInput; regime?: 'old'|'new'|'compare'; save_history?: boolean; profile_id?: string|null; profile_name?: string|null;
}

export interface TaxResult {
  regime?: Regime;
  financial_year?: string;
  assessment_year?: string;
  income?: any;
  deductions?: any;
  tax_computation?: any;
  explanation?: any[];
  assumptions_and_notes?: string[];
  // comparison fields
  old_regime?: TaxResult;
  new_regime?: TaxResult;
  comparison_table?: { particular: string; old_regime: number; new_regime: number }[];
  recommended_regime?: 'old'|'new'|'either';
  savings?: number;
  summary?: any;
}

export interface HistoryItem {
  id: string; profile_id?: string|null; profile_name?: string|null; financial_year: string; regime: string;
  gross_total_income: string; total_tax_old?: string|null; total_tax_new?: string|null; recommended_regime?: string|null; created_at: string;
}

export interface ProfileRecord {
  id: string; name: string; age_category: AgeCategory; resident: boolean; taxpayer_type: TaxpayerType; created_at: string; updated_at: string;
}
