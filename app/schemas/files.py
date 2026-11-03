from datetime import datetime
from pydantic import BaseModel, ConfigDict


class GeneratedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    format: str
    mime_type: str
    size_bytes: int
    sha256: str
    download_url: str
    status: str
    created_at: datetime
