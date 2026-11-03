import logging
from pathlib import Path
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class MicrosoftGraphClient:
    def __init__(self):
        self.enabled = settings.MICROSOFT_GRAPH_ENABLED
        self.tenant_id = settings.MICROSOFT_TENANT_ID
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.base_url = "https://graph.microsoft.com/v1.0"

    def is_configured(self) -> bool:
        return bool(self.enabled and self.tenant_id and self.client_id and self.client_secret)

    async def get_app_token(self) -> str | None:
        if not self.is_configured():
            return None
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(token_url, data=data)
                if res.status_code == 200:
                    return res.json().get("access_token")
                logger.warning(f"Graph token request failed: {res.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Error requesting Graph token: {e}")
            return None

    async def upload_file_to_onedrive(self, local_path: Path, remote_filename: str) -> dict | None:
        token = await self.get_app_token()
        if not token:
            logger.info("Microsoft Graph token unavailable. Upload skipped.")
            return None
        # Example Graph endpoint for drive upload
        upload_url = f"{self.base_url}/me/drive/root:/{remote_filename}:/content"
        try:
            with open(local_path, "rb") as f:
                content = f.read()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.put(upload_url, content=content, headers=headers)
                if res.status_code in (200, 201):
                    return res.json()
                logger.warning(f"Graph upload error: {res.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Graph upload failed: {e}")
            return None


graph_client = MicrosoftGraphClient()

