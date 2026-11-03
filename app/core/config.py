from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Personal Productivity Assistant"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev-insecure-secret-key-replace-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "sqlite:///./storage/assistant.db"

    # Persistent Generated Files Storage
    STORAGE_PATH: str = "./storage/generated"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # LLM Settings
    LLM_PROVIDER: str = "fake"  # 'fake' | 'openai' | 'anthropic' | 'gemini'
    LLM_MODEL: str = "fake-default"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = ""

    # Microsoft MCP Settings
    MICROSOFT_MCP_ENABLED: bool = False
    MICROSOFT_MCP_TRANSPORT: str = "streamable_http"  # 'streamable_http' | 'stdio' | 'sse'
    MICROSOFT_MCP_SERVER_URL: str = ""
    MICROSOFT_MCP_COMMAND: str = ""
    MICROSOFT_MCP_ARGS: list[str] = []
    MICROSOFT_MCP_AUTH_MODE: str = "none"  # 'none' | 'oauth2' | 'bearer'

    # Microsoft Entra / Graph Settings (optional)
    MICROSOFT_TENANT_ID: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = ""
    MICROSOFT_GRAPH_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Ensure storage path exists
Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
