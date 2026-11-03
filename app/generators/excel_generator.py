import re
from pathlib import Path
import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.generators.schemas import ExcelWorkbookContent

SAFE_FORMULA_REGEX = re.compile(r"^=[A-Z0-9_\+\-\*\/\(\)\:\,\s\.]+$")


def sanitize_cell_value(val: any) -> any:
    if isinstance(val, str):
        # Prevent formula injection if user string begins with dangerous prefix
        if len(val) > 0 and val[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val}"
    return val


def generate_excel_file(content: ExcelWorkbookContent, output_path: str | Path) -> Path:
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    # Remove default sheet if we have custom sheets
    if content.sheets:
        default_sheet = wb.active
        wb.remove(default_sheet)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    summary_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    summary_font = Font(name="Calibri", size=11, bold=True)
    thin_border = Border(
        left=Side(style="thin", color="D3D3D3"),
        right=Side(style="thin", color="D3D3D3"),
        top=Side(style="thin", color="D3D3D3"),
        bottom=Side(style="thin", color="D3D3D3"),
    )

    for sheet_spec in content.sheets:
        safe_sheet_name = sheet_spec.name[:31].replace("/", "-").replace("\\", "-")
        ws = wb.create_sheet(title=safe_sheet_name)
        ws.views.sheetView[0].showGridLines = True

        current_row = 1

        # Headers
        if sheet_spec.headers:
            for col_idx, header_text in enumerate(sheet_spec.headers, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=header_text)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
            current_row += 1

        # Rows
        start_data_row = current_row
        for row_data in sheet_spec.rows:
            for col_idx, val in enumerate(row_data, start=1):
                clean_val = sanitize_cell_value(val)
                cell = ws.cell(row=current_row, column=col_idx, value=clean_val)
                cell.border = thin_border
                if isinstance(val, (int, float)):
                    cell.alignment = Alignment(horizontal="right")
                    cell.number_format = "#,##0.00" if isinstance(val, float) else "#,##0"
                else:
                    cell.alignment = Alignment(horizontal="left")
            current_row += 1

        # Explicit formulas
        for formula_spec in sheet_spec.formulas:
            # Validate formula
            formula_str = formula_spec.formula.strip()
            if SAFE_FORMULA_REGEX.match(formula_str):
                cell = ws[formula_spec.cell]
                cell.value = formula_str
                cell.font = summary_font
                cell.fill = summary_fill

        # Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # Freeze top row
        if sheet_spec.headers:
            ws.freeze_panes = "A2"

        # Chart if specified and sufficient rows
        if sheet_spec.chart and len(sheet_spec.rows) > 0:
            try:
                chart = BarChart()
                chart.type = "col"
                chart.style = 10
                chart.title = sheet_spec.chart.title
                chart.y_axis.title = "Value"
                chart.x_axis.title = "Category"

                data_ref = Reference(
                    ws,
                    min_col=sheet_spec.chart.min_col + 1,
                    min_row=1,
                    max_col=sheet_spec.chart.max_col,
                    max_row=start_data_row + len(sheet_spec.rows) - 1,
                )
                cats_ref = Reference(
                    ws,
                    min_col=sheet_spec.chart.min_col,
                    min_row=start_data_row,
                    max_row=start_data_row + len(sheet_spec.rows) - 1,
                )
                chart.add_data(data_ref, titles_from_data=True)
                chart.set_categories(cats_ref)
                chart.width = 16
                chart.height = 10

                # Place chart next to table
                chart_col = get_column_letter(len(sheet_spec.headers) + 2)
                ws.add_chart(chart, f"{chart_col}2")
            except Exception:
                # Chart error should not fail file generation
                pass

    wb.save(str(out_file))

    # Reopen to validate structurally
    loaded_wb = openpyxl.load_workbook(str(out_file), data_only=False)
    sheet_count = len(loaded_wb.sheetnames)
    loaded_wb.close()
    if sheet_count == 0:
        raise ValueError("Generated Excel workbook has no sheets")

    return out_file

