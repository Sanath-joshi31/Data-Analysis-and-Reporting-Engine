"""Professional PDF report generation module using ReportLab."""

import os
from pathlib import Path
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from schemas.report import AnalyticalReport


class PDFReportGenerator:
    """Generates an executive-ready PDF report from an AnalyticalReport."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: AnalyticalReport, filename: Optional[str] = None) -> Path:
        """Build and write the PDF report to disk."""
        target_name = filename or f"Report_{report.report_id[:8]}.pdf"
        file_path = self.output_dir / target_name

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom typography
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1E293B"),
            fontName="Helvetica-Bold",
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold",
            spaceBefore=14,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=8
        )

        callout_style = ParagraphStyle(
            "Callout",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica",
            spaceBefore=4,
            spaceAfter=4
        )

        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        )

        story = []

        # Header Title
        story.append(Paragraph("AUTONOMOUS DATA ANALYST REPORT", title_style))
        story.append(Paragraph(
            f"<b>Inquiry:</b> {report.question} &nbsp;|&nbsp; <b>Source:</b> {report.dataset_name}",
            subtitle_style
        ))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3B82F6"), spaceAfter=15))

        # Executive Summary
        story.append(Paragraph("Executive Summary", h2_style))
        story.append(Paragraph(report.executive_summary, body_style))
        story.append(Spacer(1, 10))

        # Core Metrics Table
        if report.metrics_summary:
            story.append(Paragraph("Key Computed Metrics", h2_style))
            metric_data = [["Metric Name", "Computed Value"]]
            for k, v in report.metrics_summary.items():
                val_str = f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
                metric_data.append([k.replace("_", " ").title(), val_str])

            metric_table = Table(metric_data, colWidths=[250, 250])
            metric_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]))
            story.append(metric_table)
            story.append(Spacer(1, 12))

        # Key Business Findings
        if report.key_findings:
            story.append(Paragraph("Key Findings & Empirical Evidence", h2_style))
            for item in report.key_findings:
                finding_text = f"<b>{item.title} ({item.category}):</b> {item.finding}"
                story.append(Paragraph(f"• {finding_text}", bullet_style))
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;<i>Evidence:</i> {item.evidence}", callout_style))
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;<i>Implication:</i> {item.business_implication}", body_style))
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 10))

        # Actionable Recommendations
        if report.recommendations:
            story.append(Paragraph("Strategic Recommendations", h2_style))
            for rec in report.recommendations:
                story.append(Paragraph(f"✓ <b>Recommendation:</b> {rec}", bullet_style))
            story.append(Spacer(1, 10))

        # Limitations & Boundary Conditions
        if report.limitations:
            story.append(Paragraph("Analytical Boundaries & Limitations", h2_style))
            for lim in report.limitations:
                story.append(Paragraph(f"⚠ {lim}", bullet_style))
            story.append(Spacer(1, 10))

        # Output Tabular Summaries
        if report.tabular_results:
            for tbl_name, rows in list(report.tabular_results.items())[:2]:
                if rows:
                    story.append(Paragraph(f"Summary Table: {tbl_name.replace('_', ' ').title()}", h2_style))
                    headers = list(rows[0].keys())[:6]  # Max 6 columns for PDF
                    table_rows = [headers]
                    for r in rows[:8]:  # Top 8 rows
                        table_rows.append([str(r.get(h, ""))[:25] for h in headers])

                    sample_table = Table(table_rows)
                    sample_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(sample_table)
                    story.append(Spacer(1, 12))

        # Build Document
        doc.build(story)
        return file_path
