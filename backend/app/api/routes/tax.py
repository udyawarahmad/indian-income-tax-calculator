"""Tax calculation API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.schemas.tax import TaxCalculationRequest
from app.services.tax_service import perform_calculation
from app.tax_engine.rules_loader import available_financial_years, load_rules, TaxRulesNotFoundError

router = APIRouter(prefix="/api/tax", tags=["tax"])


@router.post("/calculate")
async def calculate(req: TaxCalculationRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await perform_calculation(req, db)
    except TaxRulesNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {e}")


@router.post("/compare")
async def compare(req: TaxCalculationRequest, db: AsyncSession = Depends(get_db)):
    req.regime = "compare"
    try:
        return await perform_calculation(req, db)
    except TaxRulesNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


@router.get("/rules/{financial_year}")
async def get_rules(financial_year: str):
    try:
        rules = load_rules(financial_year)
        # Return a safe summary, not internal notes only? full rules are fine - they're public.
        return rules
    except TaxRulesNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/years")
async def get_years():
    return {"financial_years": available_financial_years()}
