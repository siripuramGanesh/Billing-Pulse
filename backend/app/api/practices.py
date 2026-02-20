from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Practice
from ..schemas import PracticeCreate, PracticeUpdate, PracticeResponse

router = APIRouter(prefix="/practices", tags=["practices"])


@router.get("/me", response_model=PracticeResponse)
def get_my_practice(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No practice associated with your account",
        )
    practice = db.get(Practice, current_user.practice_id)
    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")
    return practice


@router.post("/me", response_model=PracticeResponse)
def create_my_practice(
    data: PracticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Practice already exists. Use PUT to update.",
        )
    practice = Practice(**data.model_dump())
    db.add(practice)
    db.flush()
    current_user.practice_id = practice.id
    db.commit()
    db.refresh(practice)
    return practice


@router.put("/me", response_model=PracticeResponse)
def update_my_practice(
    data: PracticeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.practice_id:
        raise HTTPException(status_code=404, detail="No practice found")
    practice = db.get(Practice, current_user.practice_id)
    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(practice, key, value)
    db.commit()
    db.refresh(practice)
    return practice
