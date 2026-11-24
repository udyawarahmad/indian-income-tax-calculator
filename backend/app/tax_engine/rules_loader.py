"""Load and cache tax rule configurations by financial year."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).resolve().parent / "rules"


class TaxRulesNotFoundError(ValueError):
    pass


@lru_cache(maxsize=8)
def load_rules(financial_year: str) -> dict[str, Any]:
    """Load rule config for a financial year like '2026-27'."""
    normalized = financial_year.strip().replace(" ", "")
    path = RULES_DIR / f"fy_{normalized.replace('-', '_')}.json"
    if not path.exists():
        available = sorted(p.stem.replace("fy_", "").replace("_", "-") for p in RULES_DIR.glob("fy_*.json"))
        raise TaxRulesNotFoundError(
            f"Tax rules not found for financial year '{financial_year}'. Available: {available}"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def available_financial_years() -> list[dict[str, Any]]:
    years = []
    for p in sorted(RULES_DIR.glob("fy_*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        years.append(
            {
                "financial_year": data.get("financial_year"),
                "assessment_year": data.get("assessment_year"),
                "label": data.get("label"),
                "default": bool(data.get("new_regime", {}).get("default", False)),
                "verified_at": data.get("verified_at"),
                "verification_status": data.get("verification_status"),
            }
        )
    return years
