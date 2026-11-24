"""PDF export route."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas.tax import TaxCalculationRequest
from app.services.pdf_service import build_tax_report_pdf
from app.services.tax_service import request_to_engine_input
from app.tax_engine.calculator import calculate_comparison, calculate_regime

router = APIRouter(prefix="/api/tax", tags=["export"])


@router.post("/export")
async def export_pdf(req: TaxCalculationRequest):
    try:
        inp = request_to_engine_input(req)
        regime = req.regime or req.profile.selected_regime or "compare"
        result = calculate_comparison(inp) if regime == "compare" else calculate_regime(inp, regime)
        pdf = build_tax_report_pdf(result)
        filename = f"tax-report-{req.profile.financial_year}.pdf"
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")
