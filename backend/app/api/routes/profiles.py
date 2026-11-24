"""Taxpayer profile API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.history import TaxpayerProfileRecord
from app.schemas.tax import ProfileCreateRequest, ProfileUpdateRequest

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _to_resp(p: TaxpayerProfileRecord) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "age_category": p.age_category,
        "resident": p.resident == "true",
        "taxpayer_type": p.taxpayer_type,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
async def list_profiles(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TaxpayerProfileRecord).order_by(desc(TaxpayerProfileRecord.updated_at)))
    return {"items": [_to_resp(p) for p in res.scalars().all()]}


@router.post("")
async def create_profile(req: ProfileCreateRequest, db: AsyncSession = Depends(get_db)):
    p = TaxpayerProfileRecord(
        name=req.name.strip(),
        age_category=req.age_category,
        resident="true" if req.resident else "false",
        taxpayer_type=req.taxpayer_type,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _to_resp(p)


@router.put("/{profile_id}")
async def update_profile(profile_id: str, req: ProfileUpdateRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TaxpayerProfileRecord).where(TaxpayerProfileRecord.id == profile_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    if req.name is not None:
        p.name = req.name.strip()
    if req.age_category is not None:
        p.age_category = req.age_category
    if req.resident is not None:
        p.resident = "true" if req.resident else "false"
    if req.taxpayer_type is not None:
        p.taxpayer_type = req.taxpayer_type
    await db.commit()
    await db.refresh(p)
    return _to_resp(p)


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TaxpayerProfileRecord).where(TaxpayerProfileRecord.id == profile_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(p)
    await db.commit()
    return {"status": "deleted", "id": profile_id}
