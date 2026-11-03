from typing import Any
from pydantic import BaseModel, Field


# Excel Models
class ExcelFormulaSpec(BaseModel):
    cell: str  # e.g., "C10" or "D5"
    formula: str  # e.g., "=SUM(C2:C9)"


class ExcelChartSpec(BaseModel):
    title: str = "Overview"
    chart_type: str = "bar"  # "bar", "line", "pie"
    data_sheet: str
    min_col: int = 1
    min_row: int = 1
    max_col: int = 2
    max_row: int = 10


class ExcelSheetSpec(BaseModel):
    name: str = "Sheet1"
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    formulas: list[ExcelFormulaSpec] = Field(default_factory=list)
    has_summary_row: bool = False
    chart: ExcelChartSpec | None = None


class ExcelWorkbookContent(BaseModel):
    title: str
    sheets: list[ExcelSheetSpec] = Field(default_factory=list)
    include_summary_sheet: bool = False


# Word Models
class WordTableSpec(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class WordSectionSpec(BaseModel):
    heading: str
    level: int = 1
    paragraphs: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)
    table: WordTableSpec | None = None


class WordDocumentContent(BaseModel):
    title: str
    subtitle: str | None = None
    author: str = "AI Productivity Assistant"
    sections: list[WordSectionSpec] = Field(default_factory=list)


# PowerPoint Models
class PowerPointSlideSpec(BaseModel):
    title: str
    bullet_points: list[str] = Field(default_factory=list)
    speaker_notes: str | None = None
    layout_type: str = "content"  # "title", "content", "conclusion"


class PowerPointPresentationContent(BaseModel):
    deck_title: str
    subtitle: str | None = None
    slides: list[PowerPointSlideSpec] = Field(default_factory=list)

