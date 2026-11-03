from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

res_root = client.get("/")
assert res_root.status_code == 200, f"Expected 200, got {res_root.status_code}"
assert res_root.json()["name"] == settings.PROJECT_NAME, f"Unexpected root response: {res_root.text}"

health_url = f"{settings.API_V1_STR}/health"
res_health = client.get(health_url)
assert res_health.status_code == 200, f"Expected 200 from {health_url}, got {res_health.status_code}"
assert res_health.json() == {"status": "ok"}, f"Unexpected health response: {res_health.text}"

print("All FastAPI app structure checks passed successfully.")
