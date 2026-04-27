"""Dashboard PDF export using ReportLab."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..schemas import DashboardSummary


def _fmt_rp(v: float) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}Rp {abs(v):,.0f}".replace(",", ".")


def build_dashboard_pdf(user_email: str, summary: DashboardSummary) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title="Finance Dashboard Report",
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle(name="small", parent=body, fontSize=9, textColor=colors.grey)

    story = []
    story.append(Paragraph("Personal Finance Dashboard", h1))
    story.append(Paragraph(f"User: {user_email}", body))
    story.append(Paragraph(
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}", small,
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Summary table
    story.append(Paragraph("Overall Summary", h2))
    summary_data = [
        ["Total Income", _fmt_rp(summary.total_income)],
        ["Total Expense", _fmt_rp(summary.total_expense)],
        ["Net", _fmt_rp(summary.net)],
    ]
    t = Table(summary_data, colWidths=[6 * cm, 6 * cm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # Monthly spend
    story.append(Paragraph("Monthly Income vs Expense", h2))
    rows = [["Month", "Income", "Expense"]]
    for m in summary.monthly_spend:
        rows.append([m.month, _fmt_rp(m.income), _fmt_rp(m.expense)])
    if len(rows) == 1:
        rows.append(["(no data)", "", ""])
    t = Table(rows, colWidths=[4 * cm, 5 * cm, 5 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # Category breakdown
    story.append(Paragraph("Category Breakdown (expenses)", h2))
    rows = [["Category", "Total"]]
    for c in summary.category_breakdown:
        rows.append([c.category, _fmt_rp(c.total)])
    if len(rows) == 1:
        rows.append(["(no data)", ""])
    t = Table(rows, colWidths=[8 * cm, 6 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # Budget status
    story.append(Paragraph("Budget Status (current month)", h2))
    rows = [["Category", "Limit", "Spent", "Remaining", "% Used", "Status"]]
    for b in summary.budget_status:
        rows.append([
            b.category,
            _fmt_rp(b.monthly_limit),
            _fmt_rp(b.spent),
            _fmt_rp(b.remaining),
            f"{b.percent_used:.1f}%",
            "OVER" if b.over_budget else "OK",
        ])
    if len(rows) == 1:
        rows.append(["(no budgets)", "", "", "", "", ""])
    t = Table(rows, colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm, 2 * cm, 2 * cm], repeatRows=1)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("ALIGN", (1, 1), (-2, -1), "RIGHT"),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
    ]
    for i, b in enumerate(summary.budget_status, start=1):
        if b.over_budget:
            style.append(("TEXTCOLOR", (-1, i), (-1, i), colors.red))
    t.setStyle(TableStyle(style))
    story.append(t)

    doc.build(story)
    return buf.getvalue()
