"""Application configuration."""
from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    # Desktop can set TAX_CALC_DATA_DIR; default to backend/app/data for dev.
    base = os.getenv("TAX_CALC_DATA_DIR")
    if base:
        p = Path(base).expanduser().resolve()
    else:
        p = Path(__file__).resolve().parents[1] / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_db_url() -> str:
    db_path = get_data_dir() / "tax_calculator.db"
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def get_sync_db_url() -> str:
    db_path = get_data_dir() / "tax_calculator.db"
    return f"sqlite:///{db_path.as_posix()}"


APP_NAME = "Indian Income Tax Calculator"
APP_VERSION = "1.0.0"
DEFAULT_FINANCIAL_YEAR = "2026-27"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,app://.,null").split(",")
