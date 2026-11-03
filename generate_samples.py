from pathlib import Path
from app.generators.excel_generator import generate_excel_file
from app.generators.word_generator import generate_word_file
from app.generators.powerpoint_generator import generate_powerpoint_file
from app.services.llm.fake import FakeLLMProvider

fake_llm = FakeLLMProvider()
samples_dir = Path("../samples").resolve()
samples_dir.mkdir(parents=True, exist_ok=True)

# 1. Excel Sample
excel_content = fake_llm.generate_excel_content("Generate monthly expense tracker")
excel_path = samples_dir / "sample_expense_tracker.xlsx"
generate_excel_file(excel_content, excel_path)
print(f"Generated sample Excel: {excel_path} ({excel_path.stat().st_size} bytes)")

# 2. Word Sample
word_content = fake_llm.generate_word_content("Generate project proposal")
word_path = samples_dir / "sample_project_proposal.docx"
generate_word_file(word_content, word_path)
print(f"Generated sample Word: {word_path} ({word_path.stat().st_size} bytes)")

# 3. PowerPoint Sample
pptx_content = fake_llm.generate_powerpoint_content("Generate AI agents presentation")
pptx_path = samples_dir / "sample_ai_presentation.pptx"
generate_powerpoint_file(pptx_content, pptx_path)
print(f"Generated sample PowerPoint: {pptx_path} ({pptx_path.stat().st_size} bytes)")

