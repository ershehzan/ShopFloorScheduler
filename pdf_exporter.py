# pdf_exporter.py
"""
Phase 5: PDF Report Exporter for ShopFloorScheduler.

Generates a branded, multi-section PDF report for a completed schedule run using ReportLab.

Sections:
  1. Cover page     — project name, run ID, timestamp, algorithm
  2. Executive KPIs — makespan, tardiness, on-time %, avg flow time
  3. Gantt chart    — embedded PNG from static/ directory
  4. Job timeline   — table of job start/end/tardiness
  5. Machine stats  — utilization table

Usage:
    from pdf_exporter import generate_pdf_report
    path = generate_pdf_report(result_data, task_id)
"""
from __future__ import annotations

import json
import os
import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas

from core.logger import logger

PDF_FOLDER = "output"
os.makedirs(PDF_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Colour palette (matches DESIGN.md)
# ---------------------------------------------------------------------------

BRAND_BLUE = colors.HexColor("#1E40AF")
BRAND_LIGHT_BLUE = colors.HexColor("#2563EB")
ACCENT_CYAN = colors.HexColor("#06B6D4")
SUCCESS_GREEN = colors.HexColor("#10B981")
WARNING_AMBER = colors.HexColor("#F59E0B")
ERROR_RED = colors.HexColor("#EF4444")
SURFACE = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")
TEXT_PRIMARY = colors.HexColor("#0F172A")
TEXT_MUTED = colors.HexColor("#475569")


# ---------------------------------------------------------------------------
# Page number footer
# ---------------------------------------------------------------------------

class _NumberedCanvas(rl_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(num_pages)
            super().showPage()
        super().save()

    def _draw_page_number(self, page_count: int):
        page = self.__dict__.get("_pageNumber", 1)
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)
        self.drawRightString(
            A4[0] - 1.5 * cm,
            0.8 * cm,
            f"ShopFloorScheduler  |  Page {page} of {page_count}",
        )
        self.setStrokeColor(BORDER)
        self.line(1.5 * cm, 1.0 * cm, A4[0] - 1.5 * cm, 1.0 * cm)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_pdf_report(
    task_id: str,
    result_json: str | None = None,
    run_meta: dict[str, Any] | None = None,
) -> str:
    """
    Generate a PDF report for a completed schedule run.

    Args:
        task_id:     The run's task UUID.
        result_json: JSON string of the result payload (from ScheduleRun.result_json).
        run_meta:    Dict with {algorithm, created_at, file_name, makespan,
                               total_tardiness, avg_flow_time, on_time_percent}.

    Returns:
        Absolute path to the generated PDF file.
    """
    result = json.loads(result_json) if result_json else {}
    run_meta = run_meta or {}

    algorithm = run_meta.get("algorithm") or result.get("algorithm", "N/A")
    makespan = run_meta.get("makespan") or result.get("makespan", 0)
    total_tardiness = run_meta.get("total_tardiness") or result.get("total_tardiness", 0)
    avg_flow_time = run_meta.get("avg_flow_time") or result.get("avg_flow_time", 0)
    on_time_percent = run_meta.get("on_time_percent") or result.get("on_time_percent", 0)
    file_name = run_meta.get("file_name", "N/A")
    created_at = run_meta.get("created_at") or datetime.datetime.utcnow().isoformat()
    schedule = result.get("schedule", [])
    utilization = result.get("utilization", [])

    pdf_path = os.path.join(PDF_FOLDER, f"report_{task_id[:8]}.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Schedule Report — {task_id[:8]}",
        author="ShopFloorScheduler",
    )

    styles = getSampleStyleSheet()
    story: list = []

    # ── Heading styles ──
    h1 = ParagraphStyle(
        "H1", parent=styles["Title"],
        fontSize=28, textColor=BRAND_BLUE, spaceAfter=6, alignment=TA_CENTER,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=BRAND_BLUE, spaceBefore=16, spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=TEXT_PRIMARY, spaceAfter=4,
    )
    muted = ParagraphStyle(
        "Muted", parent=styles["Normal"],
        fontSize=9, textColor=TEXT_MUTED, alignment=TA_CENTER,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 1: Cover
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("ShopFloorScheduler", h1))
    story.append(Paragraph("Production Schedule Report", ParagraphStyle(
        "subtitle", parent=styles["Normal"],
        fontSize=16, textColor=ACCENT_CYAN, alignment=TA_CENTER, spaceAfter=8,
    )))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=16))
    story.append(Spacer(1, 1 * cm))

    cover_data = [
        ["Run ID", task_id],
        ["Algorithm", algorithm],
        ["Source File", file_name],
        ["Generated At", str(created_at)[:19].replace("T", " ") + " UTC"],
    ]
    cover_table = Table(cover_data, colWidths=[4 * cm, 13 * cm])
    cover_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [SURFACE, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 2: Executive KPIs + Gantt
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

    kpi_data = [
        ["KPI", "Value"],
        ["Makespan", f"{makespan} time units"],
        ["Total Tardiness", f"{total_tardiness} time units"],
        ["Average Flow Time", f"{avg_flow_time:.1f} time units"],
        ["On-Time Completion", f"{on_time_percent:.1f}%"],
        ["Algorithm Used", algorithm],
        ["Operations Scheduled", str(len(schedule))],
    ]
    kpi_table = Table(kpi_data, colWidths=[8 * cm, 9 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (0, -1), TEXT_PRIMARY),
        ("TEXTCOLOR", (1, 1), (1, -1), BRAND_LIGHT_BLUE),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURFACE, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # Embed Gantt PNG if available
    gantt_png = os.path.join("static", f"gantt_{task_id}.png")
    if os.path.exists(gantt_png):
        story.append(Paragraph("Gantt Chart", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
        available_width = A4[0] - 3 * cm
        img = Image(gantt_png, width=available_width, height=available_width * 0.45)
        story.append(img)
        story.append(Paragraph(f"Machine-wise schedule timeline for run {task_id[:8]}", muted))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 3: Job Timeline Table
    # ─────────────────────────────────────────────────────────────────────────
    if schedule:
        story.append(Paragraph("Operation Schedule", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

        # Group operations by job to find job completion time
        job_end: dict[int, float] = {}
        for op in schedule:
            jid = op.get("job_id", op[0] if isinstance(op, (list, tuple)) else 0)
            end = op.get("end_time", op[4] if isinstance(op, (list, tuple)) else 0)
            job_end[jid] = max(job_end.get(jid, 0), end)

        sched_data = [["Job", "Machine", "Op #", "Start", "End", "Duration"]]
        for op in sorted(
            schedule,
            key=lambda o: (
                o.get("job_id", 0) if isinstance(o, dict) else o[0],
                o.get("op_index", 0) if isinstance(o, dict) else o[1],
            ),
        ):
            if isinstance(op, dict):
                jid, oi, mid, st, et = op["job_id"], op["op_index"], op["machine_id"], op["start_time"], op["end_time"]
            else:
                jid, oi, mid, st, et = op[0], op[1], op[2], op[3], op[4]
            sched_data.append([str(jid), str(mid), str(oi + 1), f"{st:.0f}", f"{et:.0f}", f"{et-st:.0f}"])

        sched_table = Table(
            sched_data,
            colWidths=[2.5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm, 3 * cm],
            repeatRows=1,
        )
        sched_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURFACE, colors.white]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ]))
        story.append(sched_table)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 4: Machine Utilization
    # ─────────────────────────────────────────────────────────────────────────
    if utilization:
        story.append(PageBreak())
        story.append(Paragraph("Machine Utilization", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

        util_data = [["Machine", "Utilization %", "Status"]]
        for u in sorted(utilization, key=lambda x: x.get("machine_id", 0)):
            pct = u.get("utilization", 0) * 100
            status = "High" if pct > 80 else ("Moderate" if pct > 50 else "Low")
            util_data.append([str(u["machine_id"]), f"{pct:.1f}%", status])

        util_table = Table(util_data, colWidths=[5 * cm, 6 * cm, 5 * cm])
        util_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURFACE, colors.white]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ]))
        story.append(util_table)

    doc.build(story, canvasmaker=_NumberedCanvas)
    logger.info("PDF report generated: {}", pdf_path)
    return os.path.abspath(pdf_path)


def generate_pdf_from_db(task_id: str) -> str:
    """
    Convenience wrapper: loads run data from DB and generates the PDF.

    Args:
        task_id: The task UUID to generate a report for.

    Returns:
        Absolute path to the generated PDF.

    Raises:
        ValueError: If the run is not found or not complete.
    """
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if not run:
            raise ValueError(f"Run '{task_id}' not found.")
        if run.status != "complete":
            raise ValueError(f"Run '{task_id}' is not complete (status: {run.status}).")

        return generate_pdf_report(
            task_id=task_id,
            result_json=run.result_json,
            run_meta={
                "algorithm": run.algorithm,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "file_name": run.file_name,
                "makespan": run.makespan,
                "total_tardiness": run.total_tardiness,
                "avg_flow_time": run.avg_flow_time,
                "on_time_percent": run.on_time_percent,
            },
        )
    finally:
        db.close()
