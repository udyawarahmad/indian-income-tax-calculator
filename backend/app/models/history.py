"""SQLAlchemy models for profiles and tax calculation history."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> string:
    return str(uuid.uuid4())


class TaxpayerProfileRecord(Base):
    __tablename__ = "taxpayer_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age_category: Mapped[str] = mapped_column(String(32), default="below_60")
    resident: Mapped[str] = mapped_column(String(5), default="true")  # "true"/"false" for sqlite simplicity
    taxpayer_type: Mapped[str] = mapped_column(String(20), default="individual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TaxCalculationRecord(Base):
    __tablename__ = "tax_calculations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    profile_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    financial_year: Mapped[str] = mapped_column(String(10), index=True)
    regime: Mapped[str] = mapped_column(String(10))  # old/new/compare
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    gross_total_income: Mapped[str] = mapped_column(String(32), default="0")
    total_tax_old: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total_tax_new: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recommended_regime: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
