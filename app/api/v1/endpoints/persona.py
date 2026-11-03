import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.persona_preference import PersonaPreference
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.persona import (
    PersonaGroupedOut,
    PersonaPreferenceCreate,
    PersonaPreferenceOut,
    PersonaPreferenceUpdate,
)
from app.services.memory_manager import memory_manager

router = APIRouter()


@router.get("", response_model=PersonaGroupedOut)
def get_persona(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    grouped = memory_manager.get_user_preferences_grouped(db, current_user.id)
    return PersonaGroupedOut(**grouped)


@router.post("/preferences", response_model=PersonaPreferenceOut, status_code=status.HTTP_201_CREATED)
def create_or_update_preference(
    pref_in: PersonaPreferenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pref = memory_manager.set_preference(
        db=db,
        user_id=current_user.id,
        category=pref_in.category,
        key=pref_in.key,
        value=pref_in.value,
        source=pref_in.source,
        confidence=pref_in.confidence,
    )
    val = pref.value_json
    try:
        val = json.loads(val)
    except Exception:
        pass

    return PersonaPreferenceOut(
        id=pref.id,
        category=pref.category,
        key=pref.key,
        value=val,
        source=pref.source,
        confidence=pref.confidence,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.patch("/preferences/{preference_id}", response_model=PersonaPreferenceOut)
def update_preference(
    preference_id: str,
    pref_in: PersonaPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pref = db.query(PersonaPreference).filter(
        PersonaPreference.id == preference_id,
        PersonaPreference.user_id == current_user.id,
    ).first()
    if not pref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")

    pref.value_json = json.dumps(pref_in.value)
    if pref_in.confidence is not None:
        pref.confidence = pref_in.confidence

    db.commit()
    db.refresh(pref)

    try:
        val = json.loads(pref.value_json)
    except Exception:
        val = pref.value_json

    return PersonaPreferenceOut(
        id=pref.id,
        category=pref.category,
        key=pref.key,
        value=val,
        source=pref.source,
        confidence=pref.confidence,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.delete("/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(
    preference_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = memory_manager.delete_preference(db, current_user.id, preference_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    return None

