import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: Path | str) -> str:
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"File not found for extraction: {path}")
        return ""

    ext = path.suffix.lower().lstrip(".")

    try:
        if ext == "docx":
            return _extract_docx(path)
        elif ext == "pptx":
            return _extract_pptx(path)
        elif ext == "xlsx":
            return _extract_xlsx(path)
        elif ext == "pdf":
            return _extract_pdf(path)
        elif ext in ("txt", "md", "csv", "json", "log", "py", "html"):
            return path.read_text(encoding="utf-8", errors="replace")
        else:
            # Fallback to text reading
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""
    except Exception as e:
        logger.error(f"Failed to extract text from {path.name}: {e}")
        return ""


def _extract_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    parts: list[str] = []
    
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            parts.append(txt)

    for table in doc.tables:
        for row in table.rows:
            row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_vals:
                parts.append(" | ".join(row_vals))

    return "\n\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(path))
    parts: list[str] = []

    for idx, slide in enumerate(prs.slides, 1):
        slide_parts = [f"--- Slide {idx} ---"]
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame:
                txt = shape.text_frame.text.strip()
                if txt:
                    slide_parts.append(txt)
            if shape.has_table and shape.table:
                for row in shape.table.rows:
                    row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_vals:
                        slide_parts.append(" | ".join(row_vals))
        
        # Check notes slide
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                slide_parts.append(f"Speaker Notes: {notes}")

        parts.append("\n".join(slide_parts))

    return "\n\n".join(parts)


def _extract_xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    parts: list[str] = []

    for sheet in wb.worksheets:
        sheet_parts = [f"### Sheet: {sheet.title} ###"]
        # Limit rows per sheet to prevent huge memory spikes if user generated 10k rows
        row_count = 0
        for row in sheet.iter_rows(values_only=True):
            vals = [str(v).strip() for v in row if v is not None and str(v).strip() != ""]
            if vals:
                sheet_parts.append(" | ".join(vals))
                row_count += 1
                if row_count > 300:
                    sheet_parts.append("... [truncated remaining rows] ...")
                    break
        if len(sheet_parts) > 1:
            parts.append("\n".join(sheet_parts))

    return "\n\n".join(parts)


def _extract_pdf(path: Path) -> str:
    import pypdf
    reader = pypdf.PdfReader(str(path))
    parts: list[str] = []

    for idx, page in enumerate(reader.pages, 1):
        txt = page.extract_text()
        if txt and txt.strip():
            parts.append(f"--- Page {idx} ---\n{txt.strip()}")

    return "\n\n".join(parts)

