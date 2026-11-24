"""History API routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.services.tax_service import delete_history_item, get_history_item, list_history

router = APIRouter(prefix="/api/tax/history", tags=["history"])


@router.get("")
async def history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    items = await list_history(db, limit=min(max(limit, 1), 200))
    return {
        "items": [
            {
                "id": i.id,
                "profile_id": i.profile_id,
                "profile_name": i.profile_name,
                "financial_year": i.financial_year,
                "regime": i.regime,
                "gross_total_income": i.gross_total_income,
                "total_tax_old": i.total_tax_old,
                "total_tax_new": i.total_tax_new,
                "recommended_regime": i.recommended_regime,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ]
    }


@router.get("/{item_id}")
async def history_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await get_history_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")
    return {
        "id": item.id,
        "profile_id": item.profile_id,
        "profile_name": item.profile_name,
        "financial_year": item.financial_year,
        "regime": item.regime,
        "input": json.loads(item.input_json),
        "result": json.loads(item.result_json),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.delete("/{item_id}")
async def delete_history(item_id: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_history_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"status": "deleted", "id": item_id}
