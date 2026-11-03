import re
from typing import Any
from app.generators.schemas import (
    ExcelChartSpec,
    ExcelFormulaSpec,
    ExcelSheetSpec,
    ExcelWorkbookContent,
    PowerPointPresentationContent,
    PowerPointSlideSpec,
    WordDocumentContent,
    WordSectionSpec,
    WordTableSpec,
)
from app.services.llm.base import BaseLLMProvider, IntentClassificationResult


class FakeLLMProvider(BaseLLMProvider):
    def classify_intent(self, message: str, context: list[dict[str, str]] | None = None) -> IntentClassificationResult:
        lower = message.lower().strip()

        # Check explicit preference
        pref_match = re.search(
            r"(?:always|remember that|from now on)\s+(?:i\s+prefer\s+|use\s+|i\s+want\s+)?(.+)",
            lower,
            re.IGNORECASE,
        )
        explicit_pref = None
        if pref_match:
            pref_text = pref_match.group(1).strip()
            # Determine category and key
            if "excel" in lower or "spreadsheet" in lower or "sheet" in lower:
                cat = "excel"
            elif "word" in lower or "doc" in lower:
                cat = "word"
            elif "presentation" in lower or "powerpoint" in lower or "slide" in lower:
                cat = "powerpoint"
            else:
                cat = "general"

            if "chart" in pref_text:
                explicit_pref = {"category": cat, "key": "include_charts", "value": True}
            elif "table" in pref_text:
                explicit_pref = {"category": cat, "key": "use_tables", "value": True}
            elif "concise" in pref_text or "brief" in pref_text:
                explicit_pref = {"category": cat, "key": "tone", "value": "concise"}
            elif "formal" in pref_text or "professional" in pref_text:
                explicit_pref = {"category": cat, "key": "tone", "value": "professional"}
            elif "minimal" in pref_text or "clean" in pref_text:
                explicit_pref = {"category": cat, "key": "layout", "value": "clean_minimal"}
            else:
                explicit_pref = {"category": cat, "key": "custom_preference", "value": pref_text}

        # Check if question is informational (asking how, what, why, explain)
        is_informational = bool(
            re.match(r"^(how|what|why|who|explain|tell me|can you explain|difference between)\b", lower)
        )

        # Ambiguous document request without format specification -> clarification
        if lower in ("create a document", "generate a file", "make a document", "create file", "generate document") or (
            lower.startswith("create a document") and len(lower.split()) <= 4 and not any(f in lower for f in ("word", "excel", "powerpoint", "proposal", "sheet", "slide"))
        ):
            return IntentClassificationResult(
                intent="clarification",
                clarification_question="What format would you like: Excel (.xlsx), Word (.docx), or PowerPoint (.pptx)?",
                explicit_preference=explicit_pref,
            )

        creation_verbs = ("create", "generate", "build", "make", "prepare", "export", "draft", "produce", "new")
        has_creation_verb = any(v in lower for v in creation_verbs)

        # Excel check
        if ("excel" in lower or "spreadsheet" in lower or ".xlsx" in lower or "expense tracker" in lower) and not is_informational:
            if has_creation_verb or "expense tracker" in lower:
                return IntentClassificationResult(
                    intent="generate_document",
                    format="excel",
                    subject="expense tracker" if "expense" in lower else "data spreadsheet",
                    explicit_preference=explicit_pref,
                )

        # PowerPoint check
        if ("powerpoint" in lower or "presentation" in lower or "slide deck" in lower or "slides" in lower or ".pptx" in lower) and not is_informational:
            if has_creation_verb or "slide" in lower:
                return IntentClassificationResult(
                    intent="generate_document",
                    format="powerpoint",
                    subject="presentation",
                    explicit_preference=explicit_pref,
                )

        # Word check
        if ("word" in lower or "document" in lower or ".docx" in lower or "project proposal" in lower) and not is_informational:
            if has_creation_verb or "proposal" in lower:
                return IntentClassificationResult(
                    intent="generate_document",
                    format="word",
                    subject="project proposal" if "proposal" in lower else "business document",
                    explicit_preference=explicit_pref,
                )

        return IntentClassificationResult(
            intent="conversation",
            explicit_preference=explicit_pref,
        )

    def chat(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        last_message = messages[-1]["content"] if messages else ""
        lower = last_message.lower()

        if "fastapi and django" in lower:
            return (
                "FastAPI and Django are two leading Python web frameworks with distinct architectures:\n\n"
                "1. **FastAPI**: Lightweight, asynchronous (ASGI), type-hint-driven framework focused on high performance "
                "and automatic OpenAPI documentation. Ideal for microservices, modern RESTful APIs, and real-time backends.\n\n"
                "2. **Django**: Full-stack, 'batteries-included' framework providing built-in ORM, admin dashboard, "
                "authentication, and form rendering. Best suited for monolithic web applications with complex relational workflows.\n\n"
                "Choose FastAPI for high-concurrency microservices, and Django for rapid full-featured application development."
            )
        
        if "how do i create a powerpoint" in lower:
            return (
                "To create a PowerPoint presentation, you can define your key message, structure your deck with a title slide, "
                "agenda, content slides with clear bullet points, and a concluding call to action. "
                "If you would like me to generate a downloadable PowerPoint file (.pptx) for you, simply ask: "
                "'Create a presentation about [topic]'."
            )

        return f"I understand your query: '{last_message}'. As an AI productivity assistant, I can answer your questions, retain your preferences, or generate formatted Excel (.xlsx), Word (.docx), and PowerPoint (.pptx) files upon explicit request."

    def generate_excel_content(self, prompt: str, persona_hints: dict[str, Any] | None = None) -> ExcelWorkbookContent:
        hints = persona_hints or {}
        include_charts = hints.get("excel.include_charts", True)
        include_summary = hints.get("excel.include_summary_sheet", True)

        main_sheet = ExcelSheetSpec(
            name="Expense Log",
            headers=["Category", "Department", "Monthly Budget", "Actual Spent"],
            rows=[
                ["Engineering", "Software", 45000, 42150],
                ["Marketing", "Growth", 28000, 29400],
                ["Operations", "HQ", 18500, 17200],
                ["Human Resources", "People Ops", 12000, 11800],
                ["Customer Support", "Service", 15000, 14350],
                ["Total", "", "=SUM(C2:C6)", "=SUM(D2:D6)"],
            ],
            formulas=[
                ExcelFormulaSpec(cell="C7", formula="=SUM(C2:C6)"),
                ExcelFormulaSpec(cell="D7", formula="=SUM(D2:D6)"),
            ],
            has_summary_row=True,
            chart=ExcelChartSpec(
                title="Budget vs Actual by Category",
                chart_type="bar",
                data_sheet="Expense Log",
                min_col=1,
                min_row=1,
                max_col=4,
                max_row=6,
            ) if include_charts else None,
        )

        sheets = [main_sheet]
        if include_summary:
            summary_sheet = ExcelSheetSpec(
                name="Executive Summary",
                headers=["Metric", "Amount ($)"],
                rows=[
                    ["Total Monthly Budget", 118500],
                    ["Total Actual Spent", 114900],
                    ["Net Variance", 3600],
                    ["Health Status", "Within Budget"],
                ],
            )
            sheets.append(summary_sheet)

        return ExcelWorkbookContent(
            title="Monthly Expense Tracker",
            sheets=sheets,
            include_summary_sheet=include_summary,
        )

    def generate_word_content(self, prompt: str, persona_hints: dict[str, Any] | None = None) -> WordDocumentContent:
        hints = persona_hints or {}
        use_tables = hints.get("word.use_tables", True)

        sections = [
            WordSectionSpec(
                heading="1. Executive Summary",
                level=1,
                paragraphs=[
                    "This project proposal outlines the implementation of an AI Personal Productivity Assistant designed "
                    "to streamline enterprise document workflows, retain user context across sessions, and automate Office document production."
                ],
                bullet_points=[
                    "Automated generation of Word, Excel, and PowerPoint files",
                    "Persistent user persona memory and customizable preferences",
                    "Deterministic verification and secure local data isolation",
                ],
            ),
            WordSectionSpec(
                heading="2. Project Scope & Architecture",
                level=1,
                paragraphs=[
                    "The system is architected as a modular monolith with FastAPI powering the backend services and Next.js providing "
                    "a responsive web interface. Strict user authorization ensures that data and generated files remain isolated."
                ],
            ),
        ]

        if use_tables:
            sections.append(
                WordSectionSpec(
                    heading="3. Implementation Roadmap",
                    level=1,
                    paragraphs=["The following milestones define the rollout schedule:"],
                    table=WordTableSpec(
                        headers=["Phase", "Milestone", "Duration", "Owner"],
                        rows=[
                            ["Phase 1", "Core API & Auth Foundation", "1 Week", "Backend Team"],
                            ["Phase 2", "Document Generation Engines", "1 Week", "AI/Core Team"],
                            ["Phase 3", "Persona Memory & Microsoft MCP", "1 Week", "Integration Team"],
                            ["Phase 4", "Frontend UI & Production Readiness", "1 Week", "Full Stack Team"],
                        ],
                    ),
                )
            )

        return WordDocumentContent(
            title="Project Proposal: AI Productivity Assistant",
            subtitle="Architectural Blueprint and Implementation Plan",
            sections=sections,
        )

    def generate_powerpoint_content(
        self, prompt: str, persona_hints: dict[str, Any] | None = None
    ) -> PowerPointPresentationContent:
        hints = persona_hints or {}
        slides = [
            PowerPointSlideSpec(
                title="The Rise of Autonomous AI Agents",
                bullet_points=[
                    "Evolution from passive text generators to proactive action executors",
                    "Integration of tool discovery through Model Context Protocol (MCP)",
                    "Real-time synthesis of enterprise documents and workflows",
                ],
                speaker_notes="Introduce the transition from conversational models to agentic workflow systems.",
                layout_type="content",
            ),
            PowerPointSlideSpec(
                title="System Architecture & Core Capabilities",
                bullet_points=[
                    "FastAPI modular backend with SQLAlchemy relational storage",
                    "User-scoped long-term persona memory and contextual retrieval",
                    "Dynamic Office generators: openpyxl, python-docx, python-pptx",
                ],
                speaker_notes="Highlight the reliability of trusted Python rendering over raw code execution.",
                layout_type="content",
            ),
            PowerPointSlideSpec(
                title="Security, Isolation & Governance",
                bullet_points=[
                    "HttpOnly authenticated sessions with Argon2 password hashing",
                    "Strict multi-tenant boundary checks on files and database records",
                    "Audited external integrations with runtime schema validation",
                ],
                speaker_notes="Address enterprise security requirements and multi-user data isolation.",
                layout_type="content",
            ),
            PowerPointSlideSpec(
                title="Conclusion & Strategic Roadmap",
                bullet_points=[
                    "Production-ready deployment via containerized Docker Compose",
                    "Extensible MCP adapter enabling progressive enterprise integration",
                    "Empowering knowledge workers through contextual personal productivity",
                ],
                speaker_notes="Summarize key takeaways and next steps for organizational rollout.",
                layout_type="conclusion",
            ),
        ]

        return PowerPointPresentationContent(
            deck_title="AI Agents in Modern Enterprise",
            subtitle="Architecture, Capabilities, and Deployment Blueprint",
            slides=slides,
        )

    def summarize_conversation(self, messages: list[dict[str, str]]) -> str:
        if not messages:
            return ""
        topics = [m["content"][:30] for m in messages if m.get("role") == "user"]
        return f"User discussed: {', '.join(topics[:3])}. System provided responses and managed preferences."
