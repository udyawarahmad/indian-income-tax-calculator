"""PDF export for tax calculation results."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_inr(v: Any) -> str:
    try:
        n = float(v)
    except Exception:
        return str(v)
    if n < 0:
        return f"-₹{abs(n):,.2f}"
    return f"₹{n:,.2f}"


def build_tax_report_pdf(result: dict[str, Any], title: str = "Indian Income Tax Calculation Report") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading3"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1f2937")))
    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} | For estimation purposes only - not tax advice.", styles["Small"]))
    story.append(Spacer(1, 4 * mm))

    fy = result.get("financial_year") or result.get("old_regime", {}).get("financial_year", "")
    ay = result.get("assessment_year") or result.get("old_regime", {}).get("assessment_year", "")
    story.append(Paragraph(f"<b>Financial Year:</b> {fy} &nbsp;&nbsp; <b>Assessment Year:</b> {ay}", styles["Normal"]))
    story.append(Spacer(1, 2 * mm))

    if "comparison_table" in result:
        summary = result.get("summary", {})
        story.append(Paragraph("Regime Comparison Summary", styles["Section"]))
        story.append(Paragraph(summary.get("message", ""), styles["Normal"]))
        story.append(Spacer(1, 2 * mm))
        table_data = [["Particulars", "Old Regime", "New Regime"]]
        for row in result.get("comparison_table", []):
            table_data.append([row.get("particular", ""), _fmt_inr(row.get("old_regime", 0)), _fmt_inr(row.get("new_regime", 0))])
        t = Table(table_data, colWidths=[70 * mm, 50 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        # Add breakdown for recommended/both
        for label, key in [("Old Regime Breakdown", "old_regime"), ("New Regime Breakdown", "new_regime")]:
            reg = result.get(key, {})
            if reg:
                story.append(Paragraph(label, styles["Section"]))
                _append_regime_breakdown(story, styles, reg)
    else:
        story.append(Paragraph("Tax Calculation Summary", styles["Section"]))
        _append_regime_breakdown(story, styles, result)

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Disclaimer:</b> This report is an estimate based on the inputs provided and configured tax rules. It is not professional tax advice. Verify with official Income Tax Department guidance or a qualified tax professional before filing.", styles["Small"]))
    doc.build(story)
    return buf.getvalue()


def _append_regime_breakdown(story, styles, reg: dict[str, Any]) -> None:
    tc = reg.get("tax_computation", {})
    income = reg.get("income", {})
    rows = [
        ["Gross Total Income", _fmt_inr(income.get("gross_total_income", 0))],
        ["Total Deductions", _fmt_inr(reg.get("deductions", {}).get("total_allowed", 0))],
        ["Taxable Income", _fmt_inr(tc.get("total_taxable_income", 0))],
        ["Slab Tax", _fmt_inr(tc.get("slab_tax", 0))],
        ["Special Rate Tax", _fmt_inr(tc.get("special_rate_tax", 0))],
        ["Rebate 87A", _fmt_inr(tc.get("rebate_87a", 0))],
        ["Marginal Relief 87A", _fmt_inr(tc.get("marginal_relief_87a", 0))],
        ["Surcharge", _fmt_inr(tc.get("surcharge", {}).get("surcharge", 0))],
        ["Cess (4%)", _fmt_inr(tc.get("cess", 0))],
        ["Final Tax Liability", _fmt_inr(tc.get("final_tax_liability", 0))],
        ["Effective Tax Rate", f"{float(tc.get('effective_tax_rate_percent', 0)):.2f}%"],
    ]
    t = Table([["Item", "Amount"]] + rows, colWidths=[90 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
