from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter()


@router.get("/health", summary="Health Check")
def health_check():
    return {"status": "ok"}


@router.get("/health/live", summary="Liveness Probe")
def liveness():
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness Probe")
def readiness(db: Session = Depends(get_db)):
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "database": "disconnected", "error": str(e)}
