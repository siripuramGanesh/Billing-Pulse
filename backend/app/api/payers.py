from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Payer
from ..schemas import PayerCreate, PayerUpdate, PayerResponse

router = APIRouter(prefix="/payers", tags=["payers"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a practice first",
        )
    return current_user.practice_id


@router.get("", response_model=list[PayerResponse])
def list_payers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    practice_id = require_practice(current_user)
    payers = (
        db.query(Payer)
        .filter(Payer.practice_id == practice_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return payers


@router.post("", response_model=PayerResponse)
def create_payer(
    data: PayerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    payer = Payer(practice_id=practice_id, **data.model_dump())
    db.add(payer)
    db.commit()
    db.refresh(payer)
    return payer


@router.get("/{payer_id}", response_model=PayerResponse)
def get_payer(
    payer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    payer = db.query(Payer).filter(
        Payer.id == payer_id,
        Payer.practice_id == practice_id,
    ).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    return payer


@router.put("/{payer_id}", response_model=PayerResponse)
def update_payer(
    payer_id: int,
    data: PayerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    payer = db.query(Payer).filter(
        Payer.id == payer_id,
        Payer.practice_id == practice_id,
    ).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(payer, key, value)
    db.commit()
    db.refresh(payer)
    return payer


@router.delete("/{payer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payer(
    payer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    payer = db.query(Payer).filter(
        Payer.id == payer_id,
        Payer.practice_id == practice_id,
    ).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    db.delete(payer)
    db.commit()
