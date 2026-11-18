"""Excel workbook report generation using OpenPyXL."""

from pathlib import Path
from typing import Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from schemas.report import AnalyticalReport


class ExcelReportGenerator:
    """Generates a professional multi-sheet Excel workbook from an AnalyticalReport."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: AnalyticalReport, filename: Optional[str] = None) -> Path:
        """Create and save the Excel workbook."""
        target_name = filename or f"Report_{report.report_id[:8]}.xlsx"
        file_path = self.output_dir / target_name

        wb = openpyxl.Workbook()
        # Default active sheet
        ws_summary = wb.active
        ws_summary.title = "Executive Summary"

        # Styling presets
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=11, bold=True, color="334155")
        bold_font = Font(name="Calibri", size=10, bold=True)
        regular_font = Font(name="Calibri", size=10)
        border_thin = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )

        # 1. Summary Sheet
        ws_summary["A1"] = "AUTONOMOUS DATA ANALYST REPORT"
        ws_summary["A1"].font = title_font
        ws_summary["A2"] = f"Question: {report.question}"
        ws_summary["A2"].font = sub_font
        ws_summary["A3"] = f"Dataset: {report.dataset_name}"
        ws_summary["A3"].font = regular_font

        ws_summary["A5"] = "Executive Summary"
        ws_summary["A5"].font = sub_font
        ws_summary["A6"] = report.executive_summary
        ws_summary["A6"].font = regular_font

        # Key Findings
        row = 8
        ws_summary.cell(row=row, column=1, value="Key Findings & Evidence").font = sub_font
        row += 1
        ws_summary.cell(row=row, column=1, value="Title").font = header_font
        ws_summary.cell(row=row, column=1).fill = header_fill
        ws_summary.cell(row=row, column=2, value="Category").font = header_font
        ws_summary.cell(row=row, column=2).fill = header_fill
        ws_summary.cell(row=row, column=3, value="Finding").font = header_font
        ws_summary.cell(row=row, column=3).fill = header_fill
        ws_summary.cell(row=row, column=4, value="Evidence").font = header_font
        ws_summary.cell(row=row, column=4).fill = header_fill

        for item in report.key_findings:
            row += 1
            ws_summary.cell(row=row, column=1, value=item.title).font = bold_font
            ws_summary.cell(row=row, column=2, value=item.category).font = regular_font
            ws_summary.cell(row=row, column=3, value=item.finding).font = regular_font
            ws_summary.cell(row=row, column=4, value=item.evidence).font = regular_font

        row += 2
        ws_summary.cell(row=row, column=1, value="Strategic Recommendations").font = sub_font
        for rec in report.recommendations:
            row += 1
            ws_summary.cell(row=row, column=1, value=f"• {rec}").font = regular_font

        # 2. Metrics Sheet
        if report.metrics_summary:
            ws_metrics = wb.create_sheet(title="Metrics")
            ws_metrics.cell(row=1, column=1, value="Metric Name").font = header_font
            ws_metrics.cell(row=1, column=1).fill = header_fill
            ws_metrics.cell(row=1, column=2, value="Calculated Value").font = header_font
            ws_metrics.cell(row=1, column=2).fill = header_fill

            m_row = 2
            for k, v in report.metrics_summary.items():
                ws_metrics.cell(row=m_row, column=1, value=k.replace("_", " ").title()).font = bold_font
                ws_metrics.cell(row=m_row, column=2, value=v).font = regular_font
                m_row += 1

        # 3. Tabular Data Sheets
        for tbl_name, records in report.tabular_results.items():
            if records:
                safe_title = f"Data - {tbl_name}"[:30]
                ws_data = wb.create_sheet(title=safe_title)
                headers = list(records[0].keys())

                for col_idx, h in enumerate(headers, 1):
                    cell = ws_data.cell(row=1, column=col_idx, value=str(h))
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center")

                for r_idx, rec in enumerate(records, 2):
                    for c_idx, h in enumerate(headers, 1):
                        val = rec.get(h)
                        cell = ws_data.cell(row=r_idx, column=c_idx, value=val)
                        cell.font = regular_font
                        cell.border = border_thin

        # Auto-adjust column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        lines = str(cell.value).split("\n")
                        max_len = max(max_len, max(len(l) for l in lines))
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

        wb.save(str(file_path))
        return file_path
