"""Service layer: converts API schemas to engine inputs and persists results."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import TaxCalculationRecord
from app.schemas.tax import TaxCalculationRequest
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


def request_to_engine_input(req: TaxCalculationRequest) -> TaxCalculationInput:
    p = req.profile
    return TaxCalculationInput(
        profile=TaxpayerProfile(
            taxpayer_type=p.taxpayer_type,
            age_category=p.age_category,
            resident=p.resident,
            financial_year=p.financial_year,
            selected_regime=None if req.regime == "compare" else (req.regime or p.selected_regime),
        ),
        salary=SalaryInput(**req.salary.model_dump()),
        house_property=HousePropertyInput(**req.house_property.model_dump()),
        capital_gains=CapitalGainsInput(
            entries=[CapitalGainEntry(**e.model_dump()) for e in req.capital_gains.entries]
        ),
        business=BusinessIncomeInput(**req.business.model_dump()),
        other_income=OtherIncomeInput(**req.other_income.model_dump()),
        deductions=DeductionsInput(**req.deductions.model_dump()),
    )


async def perform_calculation(req: TaxCalculationRequest, db: AsyncSession | None = None) -> dict[str, Any]:
    inp = request_to_engine_input(req)
    regime = req.regime or req.profile.selected_regime or "compare"
    if regime == "compare":
        result = calculate_comparison(inp)
    else:
        result = calculate_regime(inp, regime)

    if req.save_history and db is not None:
        await save_history(req, regime, result, db)
    return result


async def save_history(req: TaxCalculationRequest, regime: str, result: dict[str, Any], db: AsyncSession) -> TaxCalculationRecord:
    # Extract summary fields
    gross = None
    old_tax = None
    new_tax = None
    recommended = None
    if regime == "compare":
        gross = result.get("old_regime", {}).get("income", {}).get("gross_total_income")
        old_tax = result.get("summary", {}).get("old_final_tax")
        new_tax = result.get("summary", {}).get("new_final_tax")
        recommended = result.get("recommended_regime")
    else:
        gross = result.get("income", {}).get("gross_total_income")
        if regime == "old":
            old_tax = result.get("tax_computation", {}).get("final_tax_liability")
        else:
            new_tax = result.get("tax_computation", {}).get("final_tax_liability")

    rec = TaxCalculationRecord(
        profile_id=req.profile_id,
        profile_name=req.profile_name,
        financial_year=req.profile.financial_year,
        regime=regime,
        input_json=json.dumps(req.model_dump(mode="json"), default=str),
        result_json=json.dumps(result, default=str),
        gross_total_income=str(gross or 0),
        total_tax_old=str(old_tax) if old_tax is not None else None,
        total_tax_new=str(new_tax) if new_tax is not None else None,
        recommended_regime=recommended,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_history(db: AsyncSession, limit: int = 50) -> list[TaxCalculationRecord]:
    q = select(TaxCalculationRecord).order_by(desc(TaxCalculationRecord.created_at)).limit(limit)
    res = await db.execute(q)
    return list(res.scalars().all())


async def get_history_item(db: AsyncSession, item_id: str) -> TaxCalculationRecord | None:
    res = await db.execute(select(TaxCalculationRecord).where(TaxCalculationRecord.id == item_id))
    return res.scalar_one_or_none()


async def delete_history_item(db: AsyncSession, item_id: str) -> bool:
    item = await get_history_item(db, item_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True
