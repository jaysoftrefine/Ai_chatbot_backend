from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from app.generators.schemas import WordDocumentContent


def generate_word_file(content: WordDocumentContent, output_path: str | Path) -> Path:
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # Set page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Document Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(6)
    title_run = title_p.add_run(content.title)
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(24)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)

    # Subtitle
    if content.subtitle:
        sub_p = doc.add_paragraph()
        sub_p.paragraph_format.space_after = Pt(18)
        sub_run = sub_p.add_run(content.subtitle)
        sub_run.font.name = "Calibri"
        sub_run.font.size = Pt(13)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # Sections
    for sec in content.sections:
        # Heading
        heading = doc.add_heading(sec.heading, level=min(sec.level, 3))
        heading.paragraph_format.space_before = Pt(14)
        heading.paragraph_format.space_after = Pt(6)

        # Paragraphs
        for p_text in sec.paragraphs:
            p = doc.add_paragraph(p_text)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15

        # Bullet points
        for bullet in sec.bullet_points:
            p = doc.add_paragraph(bullet, style="List Bullet")
            p.paragraph_format.space_after = Pt(3)

        # Table
        if sec.table and sec.table.headers:
            table = doc.add_table(rows=1, cols=len(sec.table.headers))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = "Table Grid"

            # Header row
            hdr_cells = table.rows[0].cells
            for idx, header_title in enumerate(sec.table.headers):
                hdr_cells[idx].text = header_title
                # Bold headers
                for p in hdr_cells[idx].paragraphs:
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)

            # Data rows
            for row_vals in sec.table.rows:
                row_cells = table.add_row().cells
                for idx, val in enumerate(row_vals[: len(sec.table.headers)]):
                    row_cells[idx].text = str(val)

            doc.add_paragraph()  # Spacing after table

    doc.save(str(out_file))

    # Reopen to validate structurally
    loaded_doc = Document(str(out_file))
    if len(loaded_doc.paragraphs) == 0:
        raise ValueError("Generated Word document has no paragraphs")

    return out_file

