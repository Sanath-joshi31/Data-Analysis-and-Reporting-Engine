"""Dashboard export engine supporting HTML, PowerPoint (PPTX), PDF, Excel, and CSV formats."""

import io
import json
from pathlib import Path
from typing import Dict, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import plotly.utils
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from dashboard.specification import DashboardSpecification


class DashboardExporter:
    """Exports structured DashboardSpecification into presentation and distribution formats."""

    def __init__(self, export_dir: Optional[Path] = None):
        self.export_dir = export_dir or Path("./reports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # 1. STANDALONE INTERACTIVE HTML DASHBOARD EXPORT
    # --------------------------------------------------------------------------
    def export_to_html(self, spec: DashboardSpecification, filename: Optional[str] = None) -> Path:
        """Generate a self-contained interactive HTML file with embedded Plotly visualizations."""
        target = self.export_dir / (filename or f"Dashboard_{spec.dashboard_id[:8]}.html")

        # HTML Head and CSS
        html_parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{spec.title}</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #F8FAFC;
            color: #0F172A;
            margin: 0;
            padding: 24px;
        }}
        .header {{
            background: linear-gradient(135deg, #1E3A8A, #0284C7);
            color: white;
            padding: 28px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
        .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
        .kpi-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .kpi-card {{
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            text-align: center;
        }}
        .kpi-card .label {{ font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase; margin-bottom: 6px; }}
        .kpi-card .value {{ font-size: 28px; font-weight: 700; color: #0F172A; margin-bottom: 4px; }}
        .kpi-card .delta {{ font-size: 12px; font-weight: 600; color: #16A34A; }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: #1E293B;
            margin: 32px 0 16px 0;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 8px;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        .chart-card {{
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .chart-card .explanation {{
            margin-top: 12px;
            padding: 12px;
            background: #F1F5F9;
            border-radius: 6px;
            font-size: 13px;
            color: #334155;
            line-height: 1.5;
        }}
        .narrative-card {{
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 28px;
        }}
        .narrative-card h3 {{ margin-top: 0; color: #1E3A8A; font-size: 16px; }}
        ul {{ margin: 6px 0 14px 20px; padding: 0; }}
        li {{ margin-bottom: 4px; font-size: 14px; color: #334155; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{spec.title}</h1>
        <p>Dataset: <b>{spec.dataset_name}</b> &nbsp;|&nbsp; Generated on: {spec.created_at}</p>
    </div>

    <!-- Executive KPI Grid -->
    <div class="kpi-container">"""]

        for kpi in spec.global_kpis:
            delta_html = f'<div class="delta">{kpi.delta_formatted}</div>' if kpi.delta_formatted else ""
            html_parts.append(f"""
        <div class="kpi-card">
            <div class="label">{kpi.icon} {kpi.label}</div>
            <div class="value">{kpi.formatted_value}</div>
            {delta_html}
        </div>""")

        html_parts.append("    </div>")

        # Executive Summary & AI Narrative
        html_parts.append(f"""
    <div class="narrative-card">
        <h3>📋 Executive Summary</h3>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">{spec.executive_summary}</p>
        
        <h3>🔍 Key Empirical Findings</h3>
        <ul>{''.join(f'<li>{f}</li>' for f in spec.key_findings)}</ul>

        <h3>💡 Strategic Recommendations</h3>
        <ul>{''.join(f'<li>{r}</li>' for r in spec.recommendations)}</ul>
    </div>""")

        # Render Sections & Charts
        chart_div_counter = 0
        chart_scripts = []

        for section in spec.sections:
            if not section.visible:
                continue
            html_parts.append(f'<div class="section-title">{section.title}</div>')
            html_parts.append('<div class="chart-grid">')

            for chart in section.charts:
                chart_div_counter += 1
                div_id = f"plotly_chart_{chart_div_counter}"
                fig_json = json.dumps(chart.figure_dict, cls=plotly.utils.PlotlyJSONEncoder)

                insights_html = "".join(f"<li>{ins}</li>" for ins in chart.insights)
                html_parts.append(f"""
        <div class="chart-card">
            <div id="{div_id}" style="height: 420px;"></div>
            <div class="explanation">
                <b>AI Insight:</b> {chart.explanation}
                <ul style="margin-top: 6px;">{insights_html}</ul>
            </div>
        </div>""")

                chart_scripts.append(f"""
        var fig_{chart_div_counter} = {fig_json};
        Plotly.newPlot('{div_id}', fig_{chart_div_counter}.data, fig_{chart_div_counter}.layout, {{responsive: true, displayModeBar: false}});""")

            html_parts.append("</div>")

        # Append scripts
        html_parts.append(f"""
    <script>
        window.addEventListener('load', function() {{
            {''.join(chart_scripts)}
        }});
    </script>
</body>
</html>""")

        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        return target

    # --------------------------------------------------------------------------
    # 2. POWERPOINT PRESENTATION EXPORT (python-pptx)
    # --------------------------------------------------------------------------
    def export_to_pptx(self, spec: DashboardSpecification, filename: Optional[str] = None) -> Path:
        """Create an executive PowerPoint deck matching presentation mode."""
        target = self.export_dir / (filename or f"Presentation_{spec.dashboard_id[:8]}.pptx")

        prs = Presentation()
        # Set 16:9 Widescreen slide format (10 x 5.625 inches)
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(5.625)
        blank_slide_layout = prs.slide_layouts[6]

        NAVY = RGBColor(30, 58, 138)
        SLATE = RGBColor(100, 116, 139)
        DARK = RGBColor(15, 23, 42)
        WHITE = RGBColor(255, 255, 255)

        # SLIDE 1: Title Slide
        slide_1 = prs.slides.add_slide(blank_slide_layout)
        tb = slide_1.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(2.5))
        tf = tb.text_frame
        p_title = tf.paragraphs[0]
        p_title.text = spec.title.upper()
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY

        p_sub = tf.add_paragraph()
        p_sub.text = f"Automated Analytics Presentation  |  Dataset: {spec.dataset_name}"
        p_sub.font.size = Pt(14)
        p_sub.font.color.rgb = SLATE

        p_date = tf.add_paragraph()
        p_date.text = f"Generated: {spec.created_at}"
        p_date.font.size = Pt(11)
        p_date.font.color.rgb = SLATE

        # SLIDE 2: Executive Summary & KPIs
        slide_2 = prs.slides.add_slide(blank_slide_layout)
        self._add_slide_header(slide_2, "Executive Summary & Core KPIs")

        # KPI Tiles
        kpi_cols = min(len(spec.global_kpis), 4)
        tile_width = Inches(8.5 / max(kpi_cols, 1))
        for idx, kpi in enumerate(spec.global_kpis[:4]):
            left = Inches(0.75 + idx * (8.5 / max(kpi_cols, 1)))
            box = slide_2.shapes.add_textbox(left, Inches(1.2), tile_width - Inches(0.2), Inches(1.1))
            tf_k = box.text_frame
            p1 = tf_k.paragraphs[0]
            p1.text = kpi.label
            p1.font.size = Pt(10)
            p1.font.bold = True
            p1.font.color.rgb = SLATE
            p2 = tf_k.add_paragraph()
            p2.text = kpi.formatted_value
            p2.font.size = Pt(18)
            p2.font.bold = True
            p2.font.color.rgb = NAVY

        # Executive Summary Narrative
        box_exec = slide_2.shapes.add_textbox(Inches(0.75), Inches(2.6), Inches(8.5), Inches(2.5))
        tf_exec = box_exec.text_frame
        tf_exec.word_wrap = True
        p_e = tf_exec.paragraphs[0]
        p_e.text = spec.executive_summary
        p_e.font.size = Pt(13)
        p_e.font.color.rgb = DARK

        # SLIDE 3: Key Insights & Evidence
        slide_3 = prs.slides.add_slide(blank_slide_layout)
        self._add_slide_header(slide_3, "Key Empirical Findings")
        box_ins = slide_3.shapes.add_textbox(Inches(0.75), Inches(1.2), Inches(8.5), Inches(3.8))
        tf_ins = box_ins.text_frame
        tf_ins.word_wrap = True
        for finding in spec.key_findings:
            p = tf_ins.add_paragraph()
            p.text = f"•  {finding}"
            p.font.size = Pt(13)
            p.font.color.rgb = DARK
            p.space_after = Pt(10)

        # SLIDE 4: Strategic Recommendations & Action Items
        slide_4 = prs.slides.add_slide(blank_slide_layout)
        self._add_slide_header(slide_4, "Strategic Recommendations & Next Steps")
        box_rec = slide_4.shapes.add_textbox(Inches(0.75), Inches(1.2), Inches(8.5), Inches(3.8))
        tf_rec = box_rec.text_frame
        tf_rec.word_wrap = True
        for rec in spec.recommendations:
            p = tf_rec.add_paragraph()
            p.text = f"✓  {rec}"
            p.font.size = Pt(13)
            p.font.color.rgb = DARK
            p.space_after = Pt(10)

        # SLIDE 5: Risks & Opportunities
        slide_5 = prs.slides.add_slide(blank_slide_layout)
        self._add_slide_header(slide_5, "Identified Risks & Growth Opportunities")
        box_ro = slide_5.shapes.add_textbox(Inches(0.75), Inches(1.2), Inches(8.5), Inches(3.8))
        tf_ro = box_ro.text_frame
        tf_ro.word_wrap = True
        p_r = tf_ro.paragraphs[0]
        p_r.text = "Operational Risks & Sensitivities:"
        p_r.font.bold = True
        p_r.font.size = Pt(13)
        p_r.font.color.rgb = RGBColor(220, 38, 38)
        for risk in spec.risks:
            p = tf_ro.add_paragraph()
            p.text = f"  •  {risk}"
            p.font.size = Pt(12)
            p.font.color.rgb = DARK

        p_o = tf_ro.add_paragraph()
        p_o.text = "Identified Opportunities:"
        p_o.font.bold = True
        p_o.font.size = Pt(13)
        p_o.font.color.rgb = RGBColor(16, 185, 129)
        p_o.space_before = Pt(10)
        for opp in spec.opportunities:
            p = tf_ro.add_paragraph()
            p.text = f"  •  {opp}"
            p.font.size = Pt(12)
            p.font.color.rgb = DARK

        prs.save(str(target))
        return target

    def _add_slide_header(self, slide, title_text: str):
        NAVY = RGBColor(30, 58, 138)
        box = slide.shapes.add_textbox(Inches(0.75), Inches(0.4), Inches(8.5), Inches(0.7))
        tf = box.text_frame
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = NAVY

    # --------------------------------------------------------------------------
    # 3. MULTI-SHEET EXCEL EXPORT (OpenPyXL)
    # --------------------------------------------------------------------------
    def export_to_excel(self, spec: DashboardSpecification, filename: Optional[str] = None) -> Path:
        """Export all computed chart tables and KPIs into a structured Excel workbook."""
        target = self.export_dir / (filename or f"Dashboard_{spec.dashboard_id[:8]}.xlsx")
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Executive Summary"

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=11, bold=True, color="334155")
        regular_font = Font(name="Calibri", size=10)

        # Title & Metadata
        ws_summary["A1"] = spec.title
        ws_summary["A1"].font = title_font
        ws_summary["A2"] = f"Dataset: {spec.dataset_name} | Generated: {spec.created_at}"
        ws_summary["A2"].font = sub_font

        # KPIs Table
        ws_summary["A4"] = "KPI Metrics"
        ws_summary["A4"].font = sub_font
        ws_summary.cell(row=5, column=1, value="Metric").font = header_font
        ws_summary.cell(row=5, column=1).fill = header_fill
        ws_summary.cell(row=5, column=2, value="Value").font = header_font
        ws_summary.cell(row=5, column=2).fill = header_fill

        r = 6
        for kpi in spec.global_kpis:
            ws_summary.cell(row=r, column=1, value=kpi.label).font = regular_font
            ws_summary.cell(row=r, column=2, value=kpi.formatted_value).font = regular_font
            r += 1

        # Tabular Data Sheets
        sheet_count = 1
        for section in spec.sections:
            for chart in section.charts:
                if chart.table_records:
                    safe_name = f"{chart.title[:25]}".replace(":", "").replace("/", "")
                    ws = wb.create_sheet(title=f"Chart_{sheet_count}_{safe_name}"[:30])
                    sheet_count += 1

                    headers = list(chart.table_records[0].keys())
                    for c_idx, h in enumerate(headers, 1):
                        cell = ws.cell(row=1, column=c_idx, value=str(h))
                        cell.font = header_font
                        cell.fill = header_fill

                    for row_idx, rec in enumerate(chart.table_records, 2):
                        for c_idx, h in enumerate(headers, 1):
                            ws.cell(row=row_idx, column=c_idx, value=rec.get(h)).font = regular_font

        # Auto-adjust column widths
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

        wb.save(str(target))
        return target

    # --------------------------------------------------------------------------
    # 4. EXECUTIVE SUMMARY PDF EXPORT (ReportLab)
    # --------------------------------------------------------------------------
    def export_to_pdf(self, spec: DashboardSpecification, filename: Optional[str] = None) -> Path:
        """Export executive dashboard summary and chart insights to PDF."""
        target = self.export_dir / (filename or f"Dashboard_{spec.dashboard_id[:8]}.pdf")
        doc = SimpleDocTemplate(str(target), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=20, leading=24, textColor=colors.HexColor("#1E3A8A"), fontName="Helvetica-Bold")
        sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#64748B"), spaceAfter=12)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, leading=16, textColor=colors.HexColor("#0F172A"), fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#334155"), spaceAfter=6)
        bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#334155"), leftIndent=12, spaceAfter=3)

        story = []
        story.append(Paragraph(spec.title, title_style))
        story.append(Paragraph(f"Dataset: {spec.dataset_name} | Generated: {spec.created_at}", sub_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=12))

        # KPI Table
        if spec.global_kpis:
            kpi_data = [["KPI Indicator", "Computed Value", "Delta / Context"]]
            for kpi in spec.global_kpis:
                kpi_data.append([kpi.label, kpi.formatted_value, kpi.delta_formatted or kpi.explanation or ""])
            k_table = Table(kpi_data, colWidths=[200, 160, 180])
            k_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(k_table)
            story.append(Spacer(1, 10))

        # Executive Summary
        story.append(Paragraph("Executive Narrative", h2_style))
        story.append(Paragraph(spec.executive_summary, body_style))

        # Key Findings
        if spec.key_findings:
            story.append(Paragraph("Key Findings", h2_style))
            for f in spec.key_findings:
                story.append(Paragraph(f"• {f}", bullet_style))

        # Recommendations
        if spec.recommendations:
            story.append(Paragraph("Strategic Recommendations", h2_style))
            for r in spec.recommendations:
                story.append(Paragraph(f"✓ {r}", bullet_style))

        # Charts and Insights Roster
        story.append(Paragraph("Visualization Inventory & Computed Takeaways", h2_style))
        for sec in spec.sections:
            if not sec.visible:
                continue
            story.append(Paragraph(f"<b>Section: {sec.title}</b>", body_style))
            for c in sec.charts:
                story.append(Paragraph(f"<b>• {c.title} ({c.chart_type.upper()})</b>: {c.explanation}", bullet_style))

        doc.build(story)
        return target
