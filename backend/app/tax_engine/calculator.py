"""Core Indian income tax calculation engine.

Design goals:
- Pure, deterministic, testable (no FastAPI/DB dependencies).
- Rule-driven from FY config files.
- Returns detailed step-by-step breakdown for explainability.
- Conservative on ambiguous cases: flag assumptions in breakdown.

This engine is an estimator, not legal/tax advice.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import (
    AgeCategory,
    CapitalGainEntry,
    TaxCalculationInput,
    clamp_non_negative,
    money,
)
from .rules_loader import load_rules


def _round2(v: float) -> float:
    return round(v + 1e-9, 2)


def _round0(v: float) -> float:
    # Round to nearest rupee for intermediate display; final tax uses 288B nearest 10.
    return float(int(round(v + 1e-9, 0)))


def _round_288b(v: float) -> int:
    """Section 288B-style rounding to nearest rupee multiple of 10."""
    v = max(0.0, float(v))
    return int(round(v / 10.0) * 10)


def _slab_tax(taxable_income: float, slabs: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    remaining = max(0.0, taxable_income)
    tax = 0.0
    breakdown = []
    for slab in slabs:
        lo = float(slab["min"])
        hi = slab["max"]
        hi_val = float(hi) if hi is not None else float("inf")
        rate = float(slab["rate"])
        if remaining <= lo:
            taxable_in_slab = 0.0
        else:
            taxable_in_slab = min(remaining, hi_val) - lo
        slab_tax = taxable_in_slab * rate
        tax += slab_tax
        breakdown.append(
            {
                "from": lo,
                "to": hi,
                "rate_percent": rate * 100,
                "taxable_amount": _round2(taxable_in_slab),
                "tax": _round2(slab_tax),
            }
        )
        if hi is None or remaining <= hi_val:
            # keep adding zero rows? no, stop after last relevant slab for readability
            if hi is None:
                break
    # Trim trailing zero slabs beyond the highest taxable slab for cleaner output
    trimmed = []
    seen_nonzero_or_reached = False
    for row in breakdown:
        if row["taxable_amount"] > 0 or not seen_nonzero_or_reached:
            trimmed.append(row)
        if row["taxable_amount"] > 0:
            seen_nonzero_or_reached = True
        # include the slab where income ends (even if zero tax rate) once
    # Better: include slabs up to the slab containing income
    result = []
    for row in breakdown:
        result.append(row)
        hi = row["to"]
        if hi is None or taxable_income <= float(hi):
            break
    return _round2(tax), result


def _get_old_slabs(rules: dict[str, Any], age: AgeCategory) -> list[dict[str, Any]]:
    return rules["old_regime"]["slabs"][age]


def _age_label(age: AgeCategory) -> str:
    return {
        "below_60": "Below 60 years",
        "senior_60_to_79": "Senior citizen (60-79 years)",
        "super_senior_80_plus": "Super senior citizen (80+ years)",
    }.get(age, age)


def _calc_hra_exemption(salary_basic_da: float, hra_received: float, rent_paid: float, is_metro: bool) -> dict[str, Any]:
    # HRA exemption: least of (1) actual HRA received, (2) rent paid - 10% of salary (basic+DA),
    # (3) 50% of salary for metro / 40% for non-metro.
    if hra_received <= 0 or rent_paid <= 0 or salary_basic_da <= 0:
        return {"exempt": 0.0, "components": {"actual_hra": _round2(hra_received), "rent_minus_10pct_salary": 0.0, "metro_percent_of_salary": 0.0}}
    c1 = hra_received
    c2 = max(0.0, rent_paid - 0.10 * salary_basic_da)
    c3 = (0.50 if is_metro else 0.40) * salary_basic_da
    exempt = min(c1, c2, c3)
    return {
        "exempt": _round2(exempt),
        "components": {
            "actual_hra_received": _round2(c1),
            "rent_paid_minus_10pct_salary": _round2(c2),
            "metro_50pct_or_non_metro_40pct_salary": _round2(c3),
            "salary_basis_basic_plus_da": _round2(salary_basic_da),
            "metro": is_metro,
        },
    }


def _calc_house_property(inp: TaxCalculationInput, regime: str, rules: dict[str, Any]) -> dict[str, Any]:
    hp = inp.house_property
    breakdown: dict[str, Any] = {"property_type": hp.property_type}
    notes: list[str] = []
    if hp.property_type == "self_occupied":
        interest = clamp_non_negative(hp.home_loan_interest)
        if regime == "old":
            cap = float(rules["deductions"]["section_24b_home_loan_interest"]["self_occupied_cap"])
            deductible_interest = min(interest, cap)
            if interest > cap:
                notes.append(f"Self-occupied home loan interest capped at ₹{cap:,.0f} under old regime.")
        else:
            deductible_interest = 0.0
            if interest > 0:
                notes.append("Self-occupied home loan interest is not deductible under new regime.")
        income = -deductible_interest
        breakdown.update(
            {
                "annual_rent_received": 0.0,
                "municipal_taxes_paid": 0.0,
                "net_annual_value": 0.0,
                "standard_deduction_30pct": 0.0,
                "home_loan_interest_claimed": _round2(deductible_interest),
                "income_or_loss": _round2(income),
                "notes": notes,
            }
        )
        return breakdown

    # Let-out
    rent = clamp_non_negative(hp.annual_rent_received)
    municipal = clamp_non_negative(hp.municipal_taxes_paid)
    nav = max(0.0, rent - municipal)
    std_ded = nav * 0.30
    interest = clamp_non_negative(hp.home_loan_interest)
    if regime == "old":
        deductible_interest = interest
    else:
        # New regime allows interest on let-out property but loss cannot be set off against other heads.
        deductible_interest = interest
        notes.append("New regime: interest on let-out property is deductible, but resulting house-property loss cannot be set off against other heads (carry-forward treatment applies; this calculator reports the loss as a flag).")
    income = nav - std_ded - deductible_interest
    # New regime restriction: let-out loss setoff not allowed against other heads
    setoff_loss_allowed = 0.0
    loss_carry_forward = 0.0
    if income < 0 and regime == "new":
        loss_carry_forward = abs(income)
        setoff_loss_allowed = 0.0
        income_for_setoff = 0.0
        notes.append(f"House property loss of ₹{loss_carry_forward:,.2f} is not set off against other heads under new regime; carry forward as per rules.")
    else:
        income_for_setoff = income
    breakdown.update(
        {
            "annual_rent_received": _round2(rent),
            "municipal_taxes_paid": _round2(municipal),
            "net_annual_value": _round2(nav),
            "standard_deduction_30pct": _round2(std_ded),
            "home_loan_interest_claimed": _round2(deductible_interest),
            "income_or_loss": _round2(income),
            "income_or_loss_for_setoff": _round2(income_for_setoff),
            "loss_carry_forward": _round2(loss_carry_forward),
            "notes": notes,
        }
    )
    return breakdown


def _calc_capital_gains(inp: TaxCalculationInput, rules: dict[str, Any]) -> dict[str, Any]:
    cg_rules = rules["capital_gains"]
    entries = inp.capital_gains.entries
    special_tax = 0.0
    slab_income = 0.0
    ltcg_112a_total = 0.0
    details = []
    notes = []

    for e in entries:
        amt = clamp_non_negative(e.gain_amount)
        if amt <= 0:
            continue
        asset = e.asset_type
        row: dict[str, Any] = {"asset_type": asset, "gain_amount": _round2(amt)}
        if asset == "equity_stcg_111a":
            rate = float(cg_rules["equity_stcg_111a"]["rate"])
            tax = amt * rate
            special_tax += tax
            row.update({"tax_rate_percent": rate * 100, "tax": _round2(tax), "tax_treatment": "special_rate"})
        elif asset == "equity_ltcg_112a":
            rate = float(cg_rules["equity_ltcg_112a"]["rate"])
            ltcg_112a_total += amt
            row.update({"tax_rate_percent": rate * 100, "tax_treatment": "special_rate_112a_aggregate"})
        elif asset == "debt_mf_post_2023_04_01":
            slab_income += amt
            row.update({"tax_treatment": "slab_rate", "note": cg_rules["debt_mf_post_2023_04_01"]["note"]})
            notes.append("Debt MF acquired on/after 1 Apr 2023 taxed at slab rates (deemed short-term treatment for calculator).")
        elif asset == "property_ltcg":
            # Grandfathering option for property acquired before 23-Jul-2024 by resident individual/HUF
            rate_default = float(cg_rules["property_ltcg"]["rate"])
            if e.acquired_before_2024_07_23 and inp.profile.resident and inp.profile.taxpayer_type in ("individual", "huf") and e.indexed_gain_amount is not None:
                rate_indexed = float(cg_rules["property_ltcg"]["grandfathering_pre_2024_07_23"]["rate_with_indexation"])
                tax_no_index = amt * rate_default
                tax_indexed = max(0.0, money(e.indexed_gain_amount)) * rate_indexed
                if tax_indexed < tax_no_index:
                    special_tax += tax_indexed
                    row.update({"tax_treatment": "special_rate", "tax_rate_percent": rate_indexed * 100, "tax": _round2(tax_indexed), "grandfathering": "20% with indexation chosen (lower tax)"})
                else:
                    special_tax += tax_no_index
                    row.update({"tax_treatment": "special_rate", "tax_rate_percent": rate_default * 100, "tax": _round2(tax_no_index), "grandfathering": "12.5% without indexation chosen (lower/equal tax)"})
            else:
                tax = amt * rate_default
                special_tax += tax
                row.update({"tax_treatment": "special_rate", "tax_rate_percent": rate_default * 100, "tax": _round2(tax)})
                if e.acquired_before_2024_07_23:
                    notes.append("Property acquired before 23-Jul-2024: grandfathering option may apply; provide indexed gain to compare 20% indexed vs 12.5% non-indexed.")
        elif asset == "other_ltcg":
            rate = float(cg_rules["other_ltcg"]["rate"])
            tax = amt * rate
            special_tax += tax
            row.update({"tax_rate_percent": rate * 100, "tax": _round2(tax), "tax_treatment": "special_rate"})
        elif asset == "other_stcg":
            slab_income += amt
            row.update({"tax_treatment": "slab_rate"})
        else:
            slab_income += amt
            row.update({"tax_treatment": "slab_rate", "note": "Unknown asset type treated as slab-rate income; verify."})
            notes.append(f"Unknown capital gain asset type '{asset}' treated as slab-rate income.")
        details.append(row)

    # 112A aggregate exemption
    exemption_112a = float(cg_rules["equity_ltcg_112a"]["annual_exemption"])
    taxable_112a = max(0.0, ltcg_112a_total - exemption_112a)
    tax_112a = taxable_112a * float(cg_rules["equity_ltcg_112a"]["rate"])
    if ltcg_112a_total > 0:
        special_tax += tax_112a
        details.append(
            {
                "asset_type": "equity_ltcg_112a_aggregate",
                "total_gain": _round2(ltcg_112a_total),
                "annual_exemption": _round2(exemption_112a),
                "taxable_gain": _round2(taxable_112a),
                "tax_rate_percent": float(cg_rules["equity_ltcg_112a"]["rate"]) * 100,
                "tax": _round2(tax_112a),
                "tax_treatment": "special_rate",
            }
        )

    return {
        "entries": details,
        "special_rate_tax": _round2(special_tax),
        "slab_rate_capital_gains_income": _round2(slab_income),
        "ltcg_112a_total": _round2(ltcg_112a_total),
        "ltcg_112a_exemption_used": _round2(min(ltcg_112a_total, exemption_112a)),
        "notes": notes,
    }

def _calc_salary(inp: TaxCalculationInput, regime: str, rules: dict[str, Any]) -> dict[str, Any]:
    s = inp.salary
    basic = clamp_non_negative(s.basic_salary)
    hra = clamp_non_negative(s.hra_received)
    special = clamp_non_negative(s.special_allowance)
    other_allow = clamp_non_negative(s.other_allowances)
    bonus = clamp_non_negative(s.bonus)
    prof_tax = clamp_non_negative(s.professional_tax_paid)
    employer_nps = clamp_non_negative(s.employer_nps_contribution)
    other_components = clamp_non_negative(s.other_taxable_components)

    gross_salary = basic + hra + special + other_allow + bonus + other_components
    notes = []
    hra_exemption = {"exempt": 0.0}
    if regime == "old" and hra > 0:
        # Salary for HRA purposes: Basic + DA. We don't have DA separately; assume basic includes DA component as entered.
        salary_for_hra = basic
        hra_exemption = _calc_hra_exemption(salary_for_hra, hra, clamp_non_negative(s.rent_paid_per_year), bool(s.is_metro))
        notes.append("HRA exemption calculated on Basic (+DA if included in Basic input) using old-regime rules.")
    elif regime == "new" and hra > 0:
        notes.append("HRA exemption is not available under new regime.")

    std_ded = float(rules[regime + "_regime"]["standard_deduction"]["salary"])
    std_ded_applied = min(std_ded, max(0.0, gross_salary - float(hra_exemption.get("exempt", 0.0))))

    prof_tax_deduction = 0.0
    if regime == "old" and prof_tax > 0:
        prof_tax_deduction = prof_tax
    elif regime == "new" and prof_tax > 0:
        notes.append("Professional tax deduction is not available under new regime.")

    net_salary = max(0.0, gross_salary - float(hra_exemption.get("exempt", 0.0)) - std_ded_applied - prof_tax_deduction)
    return {
        "gross_salary": _round2(gross_salary),
        "components": {
            "basic_salary": _round2(basic),
            "hra_received": _round2(hra),
            "special_allowance": _round2(special),
            "other_allowances": _round2(other_allow),
            "bonus": _round2(bonus),
            "other_taxable_components": _round2(other_components),
        },
        "hra_exemption": hra_exemption,
        "standard_deduction": _round2(std_ded_applied),
        "professional_tax_deduction": _round2(prof_tax_deduction),
        "employer_nps_contribution": _round2(employer_nps),
        "net_salary_income": _round2(net_salary),
        "notes": notes,
    }


def _calc_deductions(inp: TaxCalculationInput, regime: str, rules: dict[str, Any], gross_total_income_before_ch6: float) -> dict[str, Any]:
    d = inp.deductions
    rules_ded = rules["deductions"]
    items = []
    total = 0.0
    notes = []

    def add(name: str, section: str, claimed: float, allowed: float, eligible: bool, reason: str = ""):
        nonlocal total
        allowed = max(0.0, allowed)
        claimed = max(0.0, claimed)
        total += allowed
        items.append({
            "name": name,
            "section": section,
            "claimed": _round2(claimed),
            "allowed": _round2(allowed),
            "eligible_in_regime": eligible,
            "reason": reason,
        })

    # 80C - old only
    claimed_80c = clamp_non_negative(d.section_80c)
    if regime == "old":
        cap = float(rules_ded["section_80c"]["cap"])
        allowed = min(claimed_80c, cap)
        add("Section 80C (investments/expenses)", "80C", claimed_80c, allowed, True,
            f"Capped at ₹{cap:,.0f}." if claimed_80c > cap else "")
    else:
        add("Section 80C (investments/expenses)", "80C", claimed_80c, 0.0, False, "Not available under new regime.")

    # 80CCD(1B) additional NPS - old only
    claimed_1b = clamp_non_negative(d.section_80ccd_1b)
    if regime == "old":
        cap = float(rules_ded["section_80ccd_1b"]["cap"])
        allowed = min(claimed_1b, cap)
        add("Section 80CCD(1B) - Additional NPS (employee)", "80CCD(1B)", claimed_1b, allowed, True,
            f"Capped at ₹{cap:,.0f}, over and above 80C." if claimed_1b > cap else "Over and above 80C.")
    else:
        add("Section 80CCD(1B) - Additional NPS (employee)", "80CCD(1B)", claimed_1b, 0.0, False, "Not available under new regime.")

    # 80CCD(2) employer NPS - both regimes
    employer_nps = clamp_non_negative(inp.salary.employer_nps_contribution)
    if employer_nps > 0:
        # Cap is % of basic+DA. We use basic_salary as proxy (DA not separately captured).
        basic_da = clamp_non_negative(inp.salary.basic_salary)
        cap_pct = float(rules_ded["section_80ccd_2"]["cap_percent_basic_da"]["private"])
        # If taxpayer might be government, we still use 14% (same in current config); kept configurable.
        cap_amount = basic_da * cap_pct
        allowed = min(employer_nps, cap_amount) if basic_da > 0 else employer_nps
        reason = f"Capped at {cap_pct*100:.0f}% of Basic+DA (₹{cap_amount:,.2f})." if basic_da > 0 else "Basic+DA not provided; full employer contribution allowed as entered (verify)."
        add("Employer NPS contribution", "80CCD(2)", employer_nps, allowed, True, reason)

    # 80D - old only
    d_self = clamp_non_negative(d.section_80d_self_family)
    d_parents = clamp_non_negative(d.section_80d_parents)
    d_checkup = clamp_non_negative(d.section_80d_preventive_checkup)
    if regime == "old":
        cap_self = float(rules_ded["section_80d"]["self_family_senior"] if d.section_80d_self_family_is_senior else rules_ded["section_80d"]["self_family_non_senior"])
        cap_parents = float(rules_ded["section_80d"]["parents_senior"] if d.section_80d_parents_is_senior else rules_ded["section_80d"]["parents_non_senior"])
        checkup_cap = float(rules_ded["section_80d"]["preventive_health_checkup_included_in_limit"])
        # Preventive checkup is within overall 80D limits; we treat it as part of claimed amounts.
        allowed_self = min(d_self + min(d_checkup, checkup_cap), cap_self)
        allowed_parents = min(d_parents, cap_parents)
        add("Medical insurance - self/family", "80D", d_self + min(d_checkup, checkup_cap), allowed_self, True,
            f"Cap ₹{cap_self:,.0f} (includes preventive checkup within limit).")
        add("Medical insurance - parents", "80D", d_parents, allowed_parents, True, f"Cap ₹{cap_parents:,.0f}.")
    else:
        if d_self + d_parents + d_checkup > 0:
            add("Medical insurance (80D)", "80D", d_self + d_parents + d_checkup, 0.0, False, "Not available under new regime.")

    # 80G - old only, simplified
    claimed_80g = clamp_non_negative(d.section_80g_eligible_donation)
    if claimed_80g > 0:
        if regime == "old":
            # Simplified: accept user-claimed eligible amount; cap at gross total income as a safety guard.
            allowed = min(claimed_80g, max(0.0, gross_total_income_before_ch6))
            reason = "Simplified: uses user-entered eligible donation amount. 80G has category-specific limits (50%/100%, qualifying limits); verify classification."
            add("Donations", "80G", claimed_80g, allowed, True, reason)
            notes.append("80G calculated in simplified mode based on eligible donation amount entered; category-specific 80G limits should be verified.")
        else:
            add("Donations", "80G", claimed_80g, 0.0, False, "Not available under new regime.")

    # 80TTA / 80TTB
    claimed_80tta = clamp_non_negative(d.section_80tta)
    claimed_80ttb = clamp_non_negative(d.section_80ttb)
    if regime == "old":
        is_senior = inp.profile.age_category in ("senior_60_to_79", "super_senior_80_plus")
        if is_senior:
            cap_ttb = float(rules_ded["section_80ttb"]["cap"])
            allowed_ttb = min(claimed_80ttb, cap_ttb)
            add("Interest income deduction (senior)", "80TTB", claimed_80ttb, allowed_ttb, True, f"Capped at ₹{cap_ttb:,.0f}.")
            if claimed_80tta > 0:
                add("Savings interest deduction", "80TTA", claimed_80tta, 0.0, False, "80TTA not available for seniors; use 80TTB.")
        else:
            cap_tta = float(rules_ded["section_80tta"]["cap"])
            allowed_tta = min(claimed_80tta, cap_tta)
            add("Savings account interest deduction", "80TTA", claimed_80tta, allowed_tta, True, f"Capped at ₹{cap_tta:,.0f}.")
            if claimed_80ttb > 0:
                add("Interest income deduction (senior)", "80TTB", claimed_80ttb, 0.0, False, "80TTB available only to senior citizens.")
    else:
        if claimed_80tta + claimed_80ttb > 0:
            add("Interest deductions (80TTA/80TTB)", "80TTA/80TTB", claimed_80tta + claimed_80ttb, 0.0, False, "Not available under new regime.")

    # Other deductions - user-entered; allow only with explicit warning
    other = clamp_non_negative(d.other_deductions)
    if other > 0:
        desc = d.other_deductions_description.strip() or "Other deduction"
        add(desc, "Other", other, 0.0, False, "Custom/other deductions are not auto-applied; verify eligibility and regime rules. Set to 0 in calculation for safety.")
        notes.append("Custom 'other deductions' were not auto-applied because eligibility varies; verify manually.")

    # Total cannot exceed gross total income (before Ch VI-A, excluding special-rate CG nuances handled later)
    capped_total = min(total, max(0.0, gross_total_income_before_ch6))
    if capped_total < total:
        notes.append("Total deductions capped at gross total income.")
        total = capped_total

    return {
        "items": items,
        "total_allowed": _round2(total),
        "notes": notes,
    }

def _family_pension_deduction(inp: TaxCalculationInput, regime: str, rules: dict[str, Any]) -> dict[str, Any]:
    fp = clamp_non_negative(inp.other_income.family_pension)
    if fp <= 0:
        return {"family_pension": 0.0, "deduction": 0.0, "net": 0.0}
    fp_cfg = rules["deductions"]["family_pension_57_iia"]
    cfg = fp_cfg.get(regime) or fp_cfg.get(f"{regime}_regime") or {"cap": 15000, "rate": 1/3}
    ded = min(fp * float(cfg["rate"]), float(cfg["cap"]))
    return {"family_pension": _round2(fp), "deduction": _round2(ded), "net": _round2(fp - ded), "cap": float(cfg["cap"]), "rate": float(cfg["rate"])}


def _compute_surcharge(total_tax_before_surcharge: float, total_income: float, regime: str, rules: dict[str, Any], special_rate_tax: float) -> dict[str, Any]:
    # Simplified but defensible surcharge with marginal relief.
    # Special-rate surcharge cap (15%) applies to special-rate components like 111A/112A/112/dividends in many cases;
    # we approximate by capping surcharge rate on the special-rate tax portion to special_rate_surcharge_cap.
    surcharge_cfg = rules[regime + "_regime"]["surcharge"]
    thresholds = surcharge_cfg["thresholds"]
    rate = 0.0
    for t in thresholds:
        lo = float(t["min"])
        hi = t["max"]
        hi_val = float(hi) if hi is not None else float("inf")
        if total_income > lo and total_income <= hi_val:
            rate = float(t["rate"])
            break
        if hi is None and total_income > lo:
            rate = float(t["rate"])
    special_cap = float(rules.get("capital_gains", {}).get("special_rate_surcharge_cap", 0.15))
    normal_tax_part = max(0.0, total_tax_before_surcharge - special_rate_tax)
    special_tax_part = min(special_rate_tax, total_tax_before_surcharge)

    surcharge_normal = normal_tax_part * rate
    surcharge_special = special_tax_part * min(rate, special_cap)
    surcharge = surcharge_normal + surcharge_special

    marginal_relief = 0.0
    # Marginal relief on surcharge: tax+surcharge should not exceed tax at threshold + (income - threshold)
    if rate > 0 and surcharge_cfg.get("marginal_relief", True):
        # Find threshold exceeded
        threshold_exceeded = 0.0
        base_rate = 0.0
        for i, t in enumerate(thresholds):
            lo = float(t["min"])
            hi = t["max"]
            hi_val = float(hi) if hi is not None else float("inf")
            if total_income > lo and total_income <= hi_val and float(t["rate"]) > 0:
                threshold_exceeded = lo
                # base rate is rate of previous threshold
                base_rate = float(thresholds[i - 1]["rate"]) if i > 0 else 0.0
                break
            if hi is None and total_income > lo and float(t["rate"]) > 0:
                threshold_exceeded = lo
                base_rate = float(thresholds[i - 1]["rate"]) if i > 0 else 0.0
                break
        if threshold_exceeded > 0:
            # Approximate marginal relief using same tax base at threshold; compute surcharge at base rate.
            # For accuracy we should recompute tax at threshold income, but taxable components make it complex.
            # Conservative approximation: limit surcharge so that extra liability over threshold-income tax is <= excess income.
            surcharge_at_base = normal_tax_part * base_rate + special_tax_part * min(base_rate, special_cap)
            excess_income = total_income - threshold_exceeded
            # Tax at threshold is unknown here; use simpler cap: surcharge - surcharge_at_base <= excess_income? Not exact.
            # Better: compute max surcharge as (tax_at_threshold + excess_income - total_tax_before_surcharge)
            # We'll approximate tax_at_threshold by scaling normal tax proportionally - not ideal. Instead, skip aggressive relief if uncertain.
            # Practical: apply marginal relief only when excess_income is small relative to surcharge.
            max_extra = excess_income  # upper bound on extra tax+surcharge over threshold
            extra_tax_plus_surcharge = (total_tax_before_surcharge + surcharge) - (total_tax_before_surcharge + surcharge_at_base)
            # We don't know exact tax at threshold; this is a limitation.
            # Use a safe approximation: cap surcharge increase over base surcharge to excess income.
            if extra_tax_plus_surcharge > max_extra:
                marginal_relief = extra_tax_plus_surcharge - max_extra
                surcharge = max(surcharge_at_base, surcharge - marginal_relief)
                notes_flag = "approximate"
            else:
                notes_flag = "not_applicable"
        else:
            notes_flag = "not_applicable"
    else:
        notes_flag = "not_applicable"

    return {
        "rate_percent": rate * 100,
        "surcharge_on_normal_tax": _round2(surcharge_normal),
        "surcharge_on_special_rate_tax": _round2(surcharge_special),
        "special_rate_surcharge_cap_percent": special_cap * 100,
        "surcharge_before_relief": _round2(surcharge_normal + surcharge_special),
        "marginal_relief": _round2(marginal_relief),
        "surcharge": _round2(max(0.0, surcharge)),
        "note": "Surcharge marginal relief is approximated when exact threshold tax recomputation is complex; verify for high-income edge cases."
    }


def calculate_regime(inp: TaxCalculationInput, regime: str) -> dict[str, Any]:
    rules = load_rules(inp.profile.financial_year)
    if regime not in ("old", "new"):
        raise ValueError("regime must be 'old' or 'new'")

    salary = _calc_salary(inp, regime, rules)
    hp = _calc_house_property(inp, regime, rules)
    cg = _calc_capital_gains(inp, rules)
    family_pension = _family_pension_deduction(inp, regime, rules)

    business_income = clamp_non_negative(inp.business.profits_from_business) + clamp_non_negative(inp.business.professional_income) + clamp_non_negative(inp.business.presumptive_income)
    other_income_normal = (
        clamp_non_negative(inp.other_income.savings_account_interest)
        + clamp_non_negative(inp.other_income.fixed_deposit_interest)
        + clamp_non_negative(inp.other_income.dividend_income)
        + clamp_non_negative(inp.other_income.other_taxable_income)
        + family_pension["net"]
    )

    hp_income_for_total = money(hp.get("income_or_loss_for_setoff", hp.get("income_or_loss", 0.0)))
    normal_income_before_deductions = (
        money(salary["net_salary_income"])
        + hp_income_for_total
        + business_income
        + other_income_normal
        + money(cg["slab_rate_capital_gains_income"])
    )
    special_rate_income = money(cg["ltcg_112a_total"])  # 112A gains are part of total income; tax computed specially
    # Also other special-rate gains: equity STCG 111A, property LTCG, other LTCG - they're in cg entries taxed at special rates.
    # We need to track special-rate taxable income amount (not tax) for threshold purposes.
    special_rate_income_amount = 0.0
    for e in inp.capital_gains.entries:
        amt = clamp_non_negative(e.gain_amount)
        if amt <= 0:
            continue
        if e.asset_type in ("equity_stcg_111a", "equity_ltcg_112a", "property_ltcg", "other_ltcg"):
            special_rate_income_amount += amt
    # 112A exemption reduces taxable 112A but total income still includes gains; for simplicity use taxable special income in total.
    # Better: total income = normal income + taxable special income.
    taxable_112a = max(0.0, money(cg["ltcg_112a_total"]) - money(cg["ltcg_112a_exemption_used"]))
    other_special_taxable = 0.0
    for e in inp.capital_gains.entries:
        amt = clamp_non_negative(e.gain_amount)
        if e.asset_type in ("equity_stcg_111a", "property_ltcg", "other_ltcg"):
            other_special_taxable += amt
    special_rate_taxable_income = taxable_112a + other_special_taxable

    gross_total_income = max(0.0, normal_income_before_deductions) + special_rate_taxable_income
    # Note: negative HP loss in old regime can set off; in new regime already limited.

    deductions = _calc_deductions(inp, regime, rules, gross_total_income_before_ch6=max(0.0, normal_income_before_deductions))
    # Chapter VI-A deductions cannot be set off against special-rate capital gains income.
    deductible_against_normal = max(0.0, normal_income_before_deductions)
    total_deductions_allowed = min(money(deductions["total_allowed"]), deductible_against_normal)

    taxable_normal_income = max(0.0, normal_income_before_deductions - total_deductions_allowed)
    total_taxable_income = taxable_normal_income + special_rate_taxable_income

    # Slab tax on normal income
    slabs = rules["new_regime"]["slabs"] if regime == "new" else _get_old_slabs(rules, inp.profile.age_category)
    slab_tax, slab_breakdown = _slab_tax(taxable_normal_income, slabs)

    special_tax = money(cg["special_rate_tax"])
    tax_before_rebate = slab_tax + special_tax

    # 87A rebate
    rebate_cfg = rules[regime + "_regime"]["rebate_87a"]
    rebate = 0.0
    marginal_relief_87a = 0.0
    rebate_notes = []
    is_resident_individual = inp.profile.resident and inp.profile.taxpayer_type == "individual"
    threshold_87a = float(rebate_cfg["taxable_income_threshold"])
    max_rebate = float(rebate_cfg["max_rebate"])
    if is_resident_individual and total_taxable_income <= threshold_87a:
        # Rebate only against normal slab tax, not special-rate tax
        rebate = min(slab_tax, max_rebate)
        rebate_notes.append(f"Section 87A rebate applied on normal slab tax (not on special-rate capital gains tax).")
    elif is_resident_individual and total_taxable_income > threshold_87a and rebate_cfg.get("marginal_relief"):
        excess = total_taxable_income - threshold_87a
        # Marginal relief: normal slab tax cannot exceed excess over threshold (tax at threshold after rebate is nil).
        if slab_tax > excess:
            marginal_relief_87a = slab_tax - excess
            rebate_notes.append(f"Marginal relief under 87A: normal slab tax capped at excess income over ₹{threshold_87a:,.0f} (₹{excess:,.2f}).")
    elif not is_resident_individual and (slab_tax > 0 or special_tax > 0):
        rebate_notes.append("Section 87A rebate not available for non-resident or non-individual taxpayers.")

    tax_after_rebate = max(0.0, slab_tax - rebate - marginal_relief_87a) + special_tax

    # Surcharge
    surcharge_info = _compute_surcharge(tax_after_rebate, total_taxable_income, regime, rules, special_tax)
    surcharge = money(surcharge_info["surcharge"])

    cess_rate = float(rules["cess"]["health_and_education_cess_rate"])
    cess = (tax_after_rebate + surcharge) * cess_rate
    total_tax_before_rounding = tax_after_rebate + surcharge + cess
    final_tax_rounded = _round_288b(total_tax_before_rounding)

    effective_rate = (final_tax_rounded / gross_total_income * 100) if gross_total_income > 0 else 0.0

    # Build explanation steps
    explanation = [
        {"step": 1, "title": "Gross income by head", "details": {
            "salary_net": money(salary["net_salary_income"]),
            "house_property": _round2(hp_income_for_total),
            "business_professional": _round2(business_income),
            "other_sources": _round2(other_income_normal),
            "capital_gains_slab_rate": money(cg["slab_rate_capital_gains_income"]),
            "capital_gains_special_rate_taxable": _round2(special_rate_taxable_income),
        }},
        {"step": 2, "title": "Deductions and exemptions", "details": {
            "standard_deduction": money(salary["standard_deduction"]),
            "hra_exemption": money(salary["hra_exemption"].get("exempt", 0)),
            "professional_tax": money(salary["professional_tax_deduction"]),
            "chapter_vi_a_deductions": _round2(total_deductions_allowed),
        }},
        {"step": 3, "title": "Taxable income", "details": {
            "normal_taxable_income": _round2(taxable_normal_income),
            "special_rate_taxable_income": _round2(special_rate_taxable_income),
            "total_taxable_income": _round2(total_taxable_income),
        }},
        {"step": 4, "title": "Tax by slabs / special rates", "details": {
            "slab_tax": _round2(slab_tax),
            "special_rate_tax": _round2(special_tax),
            "tax_before_rebate": _round2(tax_before_rebate),
        }},
        {"step": 5, "title": "Rebate and marginal relief (87A)", "details": {
            "rebate_87a": _round2(rebate),
            "marginal_relief_87a": _round2(marginal_relief_87a),
            "tax_after_rebate": _round2(tax_after_rebate),
            "notes": rebate_notes,
        }},
        {"step": 6, "title": "Surcharge", "details": surcharge_info},
        {"step": 7, "title": "Health and Education Cess", "details": {
            "cess_rate_percent": cess_rate * 100,
            "cess": _round2(cess),
        }},
        {"step": 8, "title": "Final tax liability", "details": {
            "total_tax_before_rounding": _round2(total_tax_before_rounding),
            "rounded_off_288b": final_tax_rounded,
            "final_tax_liability": final_tax_rounded,
        }},
    ]

    return {
        "regime": regime,
        "financial_year": inp.profile.financial_year,
        "assessment_year": rules.get("assessment_year"),
        "taxpayer": {
            "type": inp.profile.taxpayer_type,
            "age_category": inp.profile.age_category,
            "age_label": _age_label(inp.profile.age_category),
            "resident": inp.profile.resident,
        },
        "income": {
            "salary": salary,
            "house_property": hp,
            "capital_gains": cg,
            "business_professional": {
                "profits_from_business": _round2(clamp_non_negative(inp.business.profits_from_business)),
                "professional_income": _round2(clamp_non_negative(inp.business.professional_income)),
                "presumptive_income": _round2(clamp_non_negative(inp.business.presumptive_income)),
                "presumptive_scheme": inp.business.presumptive_scheme,
                "total": _round2(business_income),
            },
            "other_sources": {
                "savings_account_interest": _round2(clamp_non_negative(inp.other_income.savings_account_interest)),
                "fixed_deposit_interest": _round2(clamp_non_negative(inp.other_income.fixed_deposit_interest)),
                "dividend_income": _round2(clamp_non_negative(inp.other_income.dividend_income)),
                "other_taxable_income": _round2(clamp_non_negative(inp.other_income.other_taxable_income)),
                "family_pension": family_pension,
                "total": _round2(other_income_normal),
            },
            "gross_total_income": _round2(gross_total_income),
        },
        "deductions": deductions,
        "tax_computation": {
            "normal_taxable_income": _round2(taxable_normal_income),
            "special_rate_taxable_income": _round2(special_rate_taxable_income),
            "total_taxable_income": _round2(total_taxable_income),
            "slab_breakdown": slab_breakdown,
            "slab_tax": _round2(slab_tax),
            "special_rate_tax": _round2(special_tax),
            "tax_before_rebate": _round2(tax_before_rebate),
            "rebate_87a": _round2(rebate),
            "marginal_relief_87a": _round2(marginal_relief_87a),
            "tax_after_rebate_and_relief": _round2(tax_after_rebate),
            "surcharge": surcharge_info,
            "cess_rate_percent": cess_rate * 100,
            "cess": _round2(cess),
            "total_tax_before_rounding": _round2(total_tax_before_rounding),
            "rounding_288b": final_tax_rounded - total_tax_before_rounding,
            "final_tax_liability": final_tax_rounded,
            "effective_tax_rate_percent": _round2(effective_rate),
        },
        "explanation": explanation,
        "assumptions_and_notes": [
            *salary.get("notes", []),
            *hp.get("notes", []),
            *cg.get("notes", []),
            *deductions.get("notes", []),
            *rebate_notes,
            surcharge_info.get("note", ""),
            "Calculator provides estimates only; verify with official rules/professional advice before filing.",
        ],
    }


def calculate_comparison(inp: TaxCalculationInput) -> dict[str, Any]:
    old = calculate_regime(inp, "old")
    new = calculate_regime(inp, "new")
    old_tax = money(old["tax_computation"]["final_tax_liability"])
    new_tax = money(new["tax_computation"]["final_tax_liability"])
    if old_tax == new_tax:
        recommended = "either"
        savings = 0.0
    elif old_tax < new_tax:
        recommended = "old"
        savings = new_tax - old_tax
    else:
        recommended = "new"
        savings = old_tax - new_tax

    comparison_table = [
        {"particular": "Gross Total Income", "old_regime": money(old["income"]["gross_total_income"]), "new_regime": money(new["income"]["gross_total_income"])},
        {"particular": "Total Deductions", "old_regime": money(old["deductions"]["total_allowed"]), "new_regime": money(new["deductions"]["total_allowed"])},
        {"particular": "Taxable Income", "old_regime": money(old["tax_computation"]["total_taxable_income"]), "new_regime": money(new["tax_computation"]["total_taxable_income"])},
        {"particular": "Tax Before Rebate", "old_regime": money(old["tax_computation"]["tax_before_rebate"]), "new_regime": money(new["tax_computation"]["tax_before_rebate"])},
        {"particular": "Rebate (87A)", "old_regime": money(old["tax_computation"]["rebate_87a"]), "new_regime": money(new["tax_computation"]["rebate_87a"])},
        {"particular": "Surcharge", "old_regime": money(old["tax_computation"]["surcharge"]["surcharge"]), "new_regime": money(new["tax_computation"]["surcharge"]["surcharge"])},
        {"particular": "Health & Education Cess", "old_regime": money(old["tax_computation"]["cess"]), "new_regime": money(new["tax_computation"]["cess"])},
        {"particular": "Final Tax Liability", "old_regime": old_tax, "new_regime": new_tax},
    ]

    return {
        "financial_year": inp.profile.financial_year,
        "assessment_year": old.get("assessment_year"),
        "old_regime": old,
        "new_regime": new,
        "comparison_table": comparison_table,
        "recommended_regime": recommended,
        "savings": _round2(savings),
        "summary": {
            "old_final_tax": old_tax,
            "new_final_tax": new_tax,
            "recommended_regime": recommended,
            "savings_amount": _round2(savings),
            "message": (
                f"Both regimes result in the same tax: ₹{old_tax:,.0f}."
                if recommended == "either"
                else f"{recommended.title()} regime is better by ₹{savings:,.0f}."
            ),
        },
    }


def calculate_tax(inp: TaxCalculationInput, regime: str | None = None) -> dict[str, Any]:
    selected = regime or inp.profile.selected_regime or "new"
    if selected == "compare":
        return calculate_comparison(inp)
    return calculate_regime(inp, selected)
