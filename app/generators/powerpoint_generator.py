from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from app.generators.schemas import PowerPointPresentationContent


def generate_powerpoint_file(content: PowerPointPresentationContent, output_path: str | Path) -> Path:
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    # 16:9 widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Theme colors
    PRIMARY_COLOR = RGBColor(0x1F, 0x4E, 0x78)  # Navy
    DARK_TEXT = RGBColor(0x26, 0x26, 0x26)
    SUB_TEXT = RGBColor(0x59, 0x59, 0x59)

    # 1. Title Slide
    title_slide = prs.slides.add_slide(blank_layout)
    title_box = title_slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(3.0))
    tf = title_box.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = content.deck_title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = PRIMARY_COLOR
    p.font.name = "Calibri"

    if content.subtitle:
        p2 = tf.add_paragraph()
        p2.text = content.subtitle
        p2.font.size = Pt(22)
        p2.font.italic = True
        p2.font.color.rgb = SUB_TEXT
        p2.font.name = "Calibri"
        p2.space_before = Pt(14)

    # 2. Content & Conclusion Slides
    for slide_spec in content.slides:
        slide = prs.slides.add_slide(blank_layout)

        # Slide Title
        header_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.3), Inches(1.2))
        htf = header_box.text_frame
        htf.word_wrap = True
        hp = htf.paragraphs[0]
        hp.text = slide_spec.title
        hp.font.size = Pt(32)
        hp.font.bold = True
        hp.font.color.rgb = PRIMARY_COLOR
        hp.font.name = "Calibri"

        # Content bullets
        body_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(4.8))
        btf = body_box.text_frame
        btf.word_wrap = True

        for idx, bullet in enumerate(slide_spec.bullet_points):
            bp = btf.paragraphs[0] if idx == 0 else btf.add_paragraph()
            bp.text = f"•  {bullet}"
            bp.font.size = Pt(20)
            bp.font.color.rgb = DARK_TEXT
            bp.font.name = "Calibri"
            bp.space_after = Pt(14)

        # Speaker notes
        if slide_spec.speaker_notes:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_spec.speaker_notes

    prs.save(str(out_file))

    # Reopen to validate structurally
    loaded_prs = Presentation(str(out_file))
    if len(loaded_prs.slides) == 0:
        raise ValueError("Generated PowerPoint presentation has no slides")

    return out_file

