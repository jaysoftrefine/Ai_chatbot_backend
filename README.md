# Productivity Assistant — FastAPI Backend

This is the FastAPI backend repository for the AI Personal Productivity Assistant.

## Prerequisites
- Python 3.12+ (Python 3.14 compatible)
- PostgreSQL or SQLite

## Quick Start
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run tests
pytest -v

# Start development server
uvicorn app.main:app --reload --port 8000
```

## Structure
- `app/api/v1/`: API endpoints (auth, chat, conversations, persona, files, integrations, health)
- `app/db/`: SQLAlchemy 2.x models, session management, and Alembic migrations
- `app/generators/`: Document generators (`openpyxl`, `python-docx`, `python-pptx`)
- `app/services/`: AI orchestrator, LLM provider abstraction, memory manager, storage service
- `app/integrations/`: Microsoft MCP client/discovery/registry and Graph adapter
- `tests/`: Automated pytest suite covering all 11 assignment scenarios
- `storage/`: User-scoped persistent document storage
