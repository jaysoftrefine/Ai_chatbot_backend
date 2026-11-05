import pytest
from app.services.rag.chunker import chunk_text
from app.services.rag.extractor import extract_text_from_file


def test_chunker_basic():
    text = "Paragraph one with some information.\n\nParagraph two with more details."
    chunks = chunk_text(text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) >= 2
    assert "Paragraph one" in chunks[0]
    assert "Paragraph two" in chunks[1]


def test_chunker_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_extractor_plaintext(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("Revenue increased by 20% in 2026.", encoding="utf-8")
    content = extract_text_from_file(p)
    assert "Revenue increased by 20%" in content

