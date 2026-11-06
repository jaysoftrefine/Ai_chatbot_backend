# Productivity Assistant — FastAPI Backend

FastAPI backend service powering the AI Personal Productivity Assistant. It provides AI conversational orchestration, local Office document generation (Excel, Word, PowerPoint), document retrieval-augmented generation (RAG), user persona preferences, and external integrations (Google Docs MCP and Microsoft MCP).

---

## Features

- **Conversational AI & Memory:** Context-aware multi-turn conversations with persona-conditioned prompts, rolling summaries, and intent routing.
- **Office Document Generation:** Native creation of Microsoft Office files without external Office dependencies:
  - Spreadsheets (`.xlsx`) via `openpyxl` / `xlsxwriter`
  - Word documents (`.docx`) via `python-docx`
  - Presentations (`.pptx`) via `python-pptx`
- **RAG & Knowledge Base:** Upload, extract (PDF, TXT, MD, DOCX), chunk, and search user documents to ground AI responses.
- **Persona Preferences:** Persistent user preferences across general assistant behavior and document formatting (fonts, palettes, layout, tone).
- **Authentication & Security:** User registration, password hashing (bcrypt/argon2), and JWT authentication with automatic refresh token rotation.
- **Pluggable LLM Providers:**
  - `google` / `gemini`: Google Gemini via official `google-genai` SDK (`gemini-2.5-flash` by default).
  - `fake`: Deterministic mock provider for local development, reproducible tests, and offline workflows.
- **External Integrations:**
  - Google Docs MCP client and Google OAuth flow.
  - Microsoft MCP (Model Context Protocol) via streamable HTTP/stdio/SSE and Microsoft Graph adapter.

---

## Tech Stack

- **Framework:** FastAPI, Starlette, Uvicorn
- **Language:** Python 3.12+ (Python 3.14 verified)
- **Database & ORM:** SQLAlchemy 2.x, Alembic, PostgreSQL (`psycopg3`) with SQLite fallback
- **Validation & Settings:** Pydantic v2, Pydantic Settings
- **Office Processing:** `openpyxl`, `xlsxwriter`, `python-docx`, `python-pptx`, `pypdf`
- **Testing:** Pytest, pytest-asyncio, HTTPX

---

## Project Structure

```text
backend/
├── alembic/                # Alembic database migrations and version scripts
├── alembic.ini             # Alembic configuration
├── app/
│   ├── api/
│   │   ├── deps.py         # FastApi dependency injection (DB session, current user)
│   │   └── v1/
│   │       ├── api.py      # v1 router aggregation
│   │       └── endpoints/  # Route handlers (auth, chat, conversations, files, health, integrations, persona)
│   ├── core/
│   │   ├── config.py       # Pydantic BaseSettings environment configuration
│   │   └── security.py     # Password hashing, JWT token generation & verification
│   ├── db/
│   │   ├── base.py         # SQLAlchemy Base and model registry
│   │   ├── session.py      # Engine and scoped session maker
│   │   └── models/         # Database models (User, Conversation, Message, GeneratedFile, DocumentChunk, PersonaPreference)
│   ├── generators/         # Document generators (Excel, Word, PowerPoint)
│   ├── integrations/       # Google Docs MCP client and Microsoft MCP / Graph adapters
│   ├── schemas/            # Pydantic request/response validation schemas
│   ├── services/           # Orchestrator, memory manager, storage service, LLM factory, and RAG service
│   └── main.py             # FastAPI application entry point, middleware, CORS, and lifecycle events
├── storage/                # Local database and persistent generated document storage
├── tests/                  # Pytest test suite covering core scenarios, RAG, JWT, and LLM providers
├── Dockerfile              # Production container build
├── generate_samples.py     # CLI helper to pre-generate sample Office documents
└── requirements.txt        # Pinned Python package dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.12 or newer (Python 3.14 supported)
- SQLite (default) or running PostgreSQL instance

### 1. Setup Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the sample environment file:

```bash
cp .env.example .env
```

Review and adjust variables in `.env` as needed:

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment (`development` / `production`) |
| `APP_SECRET_KEY` | *(required in prod)* | Secret key used for cryptographic operations |
| `JWT_SECRET_KEY` | *(defaults to APP_SECRET_KEY)* | Secret key for JWT access and refresh token signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifespan in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifespan in days |
| `DATABASE_URL` | `sqlite:///./storage/assistant.db` | SQLAlchemy database URI (SQLite or PostgreSQL) |
| `STORAGE_PATH` | `./storage/generated` | Filesystem path for generated Office files |
| `LLM_PROVIDER` | `fake` | LLM backend: `google` / `gemini` or `fake` |
| `GEMINI_API_KEY` | `""` | Google AI Studio API key (required if `LLM_PROVIDER=google`) |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `GOOGLE_DOCS_MCP_ENABLED` | `false` | Enable Google Docs MCP remote integration |
| `MICROSOFT_MCP_ENABLED` | `false` | Enable Microsoft MCP server connection |

### 3. Database Migrations

Apply database migrations using Alembic:

```bash
alembic upgrade head
```

*(Note: On first startup, the app automatically verifies and initializes missing tables if running with SQLite).*

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000).

- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health check:** [http://localhost:8000/health/live](http://localhost:8000/health/live)

---

## API Endpoints Reference

All application endpoints are prefixed with `/api/v1`:

### Authentication (`/api/v1/auth`)
- `POST /register`: Register a new user with email and password.
- `POST /login`: Authenticate and receive access + refresh JWT tokens.
- `POST /refresh`: Refresh an expired access token using a refresh token.
- `GET /me`: Return current authenticated user profile.

### Chat & Conversations (`/api/v1/chat`, `/api/v1/conversations`)
- `POST /chat`: Send a prompt; orchestrates memory, RAG context, persona styling, and Office document generation.
- `GET /conversations`: List user conversations with pagination.
- `GET /conversations/{id}`: Get conversation details, message history, and summary.
- `DELETE /conversations/{id}`: Delete a conversation.
- `GET /conversations/{id}/messages`: Fetch messages within a conversation.

### Persona Preferences (`/api/v1/persona`)
- `GET /persona`: Get grouped persona preferences (`general`, `word`, `excel`, `powerpoint`).
- `GET /persona/items`: List all raw preference entries.
- `POST /persona`: Create or update a persona preference item.
- `DELETE /persona/{id}`: Delete a persona preference.

### Files & RAG (`/api/v1/files`)
- `POST /files/upload`: Upload and index a document for RAG search.
- `GET /files`: List uploaded documents and generated files.
- `GET /files/{id}/download`: Download generated Office file or uploaded source.
- `DELETE /files/{id}`: Delete a file and its indexed vector chunks.

### Integrations (`/api/v1/integrations`)
- `GET /integrations/google-docs/status`: Google Docs MCP integration status.
- `GET /integrations/microsoft/status`: Microsoft MCP connection status and discovered tools.

---

## Running Tests

The test suite covers full multi-turn assistant scenarios, document generators, RAG ingestion/search, and JWT refresh mechanics:

```bash
pytest -v
```

To run with coverage or target a single test file:

```bash
pytest tests/test_assistant_scenarios.py -v
```

---

## Sample Document Generation

To generate demonstration Office documents locally:

```bash
python generate_samples.py
```

Generated `.xlsx`, `.docx`, and `.pptx` files are placed into `storage/generated/`.

---

## Docker

Build and run the backend standalone:

```bash
docker build -t assistant-backend .
docker run -p 8000:8000 --env-file .env assistant-backend
```
