from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import io
import pandas as pd

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Payer, Claim
from ..schemas import ClaimCreate, ClaimUpdate, ClaimResponse, ClaimBulkCreate
from ..services.audit_service import log as audit_log
from ..services.encryption_service import encrypt_value, decrypt_value

router = APIRouter(prefix="/claims", tags=["claims"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a practice first",
        )
    return current_user.practice_id


@router.get("", response_model=list[ClaimResponse])
def list_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    payer_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    practice_id = require_practice(current_user)
    q = db.query(Claim).filter(Claim.practice_id == practice_id)
    if status_filter:
        q = q.filter(Claim.status == status_filter)
    if payer_id:
        q = q.filter(Claim.payer_id == payer_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Claim.claim_number.ilike(term),
                Claim.patient_name.ilike(term),
            )
        )
    claims = q.offset(skip).limit(limit).all()
    for c in claims:
        c.notes = decrypt_value(c.notes)
        c.denial_reason = decrypt_value(c.denial_reason)
    return claims


@router.post("", response_model=ClaimResponse)
def create_claim(
    data: ClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    # Verify payer belongs to practice
    payer = db.query(Payer).filter(
        Payer.id == data.payer_id,
        Payer.practice_id == practice_id,
    ).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    d = data.model_dump()
    for key in ("notes", "denial_reason"):
        if key in d and d[key]:
            d[key] = encrypt_value(d[key])
    claim = Claim(practice_id=practice_id, **d)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    claim.notes = decrypt_value(claim.notes)
    claim.denial_reason = decrypt_value(claim.denial_reason)
    return claim


@router.post("/bulk", response_model=dict)
def create_claims_bulk(
    data: ClaimBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    created = 0
    for c in data.claims:
        payer = db.query(Payer).filter(
            Payer.id == c.payer_id,
            Payer.practice_id == practice_id,
        ).first()
        if payer:
            claim = Claim(practice_id=practice_id, **c.model_dump())
            db.add(claim)
            created += 1
    db.commit()
    return {"created": created, "total": len(data.claims)}


@router.post("/upload")
async def upload_claims(
    file: UploadFile = File(...),
    payer_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload CSV or Excel file. Columns: claim_number, patient_name, patient_dob, date_of_service, amount, denial_reason, denial_code, notes. Optionally payer_id per row or as query param."""
    practice_id = require_practice(current_user)

    content = await file.read()
    ext = file.filename.split(".")[-1].lower() if file.filename else ""

    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=400,
                detail="File must be CSV or Excel (.xlsx, .xls)",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file: {str(e)}")

    # Normalize column names (strip, lowercase, replace spaces)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Map common column names
    col_map = {
        "claim_number": ["claim_number", "claim_no", "claim#", "claim"],
        "patient_name": ["patient_name", "patient", "member_name"],
        "patient_dob": ["patient_dob", "dob", "date_of_birth"],
        "date_of_service": ["date_of_service", "dos", "service_date"],
        "amount": ["amount", "balance", "billed_amount"],
        "denial_reason": ["denial_reason", "denial", "reason"],
        "denial_code": ["denial_code", "denial_code", "code"],
        "notes": ["notes", "note"],
        "payer_id": ["payer_id", "payer"],
    }

    def find_col(keys: list[str]) -> str | None:
        for k in keys:
            if k in df.columns:
                return k
        return None

    created = 0
    errors = []

    for idx, row in df.iterrows():
        claim_num = None
        for k in col_map["claim_number"]:
            if k in df.columns and pd.notna(row.get(k)):
                claim_num = str(row[k]).strip()
                break
        if not claim_num:
            errors.append(f"Row {idx + 2}: missing claim_number")
            continue

        pid = payer_id
        if pid is None:
            pc = find_col(col_map["payer_id"])
            if pc and pd.notna(row.get(pc)):
                try:
                    pid = int(float(row[pc]))
                except (ValueError, TypeError):
                    pass
        if pid is None:
            errors.append(f"Row {idx + 2}: payer_id required (column or query param)")
            continue

        payer = db.query(Payer).filter(
            Payer.id == pid,
            Payer.practice_id == practice_id,
        ).first()
        if not payer:
            errors.append(f"Row {idx + 2}: payer_id {pid} not found")
            continue

        def get_val(keys: list[str], default=None):
            for k in keys:
                if k in df.columns and pd.notna(row.get(k)):
                    v = row[k]
                    if isinstance(v, float) and "amount" in str(k).lower():
                        return str(v) if v else default
                    return str(v).strip() if v is not None else default
            return default

        claim = Claim(
            practice_id=practice_id,
            payer_id=pid,
            claim_number=claim_num,
            patient_name=get_val(col_map["patient_name"]),
            patient_dob=get_val(col_map["patient_dob"]),
            date_of_service=get_val(col_map["date_of_service"]),
            amount=get_val(col_map["amount"]),
            denial_reason=encrypt_value(get_val(col_map["denial_reason"])),
            denial_code=get_val(col_map["denial_code"]),
            notes=encrypt_value(get_val(col_map["notes"])),
        )
        try:
            if claim.amount:
                claim.amount = float(claim.amount)
        except (ValueError, TypeError):
            claim.amount = None
        db.add(claim)
        created += 1

    db.commit()
    return {"created": created, "total_rows": len(df), "errors": errors[:20]}


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.practice_id == practice_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.notes = decrypt_value(claim.notes)
    claim.denial_reason = decrypt_value(claim.denial_reason)
    return claim


@router.put("/{claim_id}", response_model=ClaimResponse)
def update_claim(
    claim_id: int,
    data: ClaimUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.practice_id == practice_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    payload = data.model_dump(exclude_unset=True)
    for key in ("notes", "denial_reason"):
        if key in payload and payload[key] is not None:
            payload[key] = encrypt_value(payload[key])
    for key, value in payload.items():
        setattr(claim, key, value)
    audit_log(db, practice_id, "claim.update", "claim", user_id=current_user.id, resource_id=str(claim_id))
    db.commit()
    db.refresh(claim)
    claim.notes = decrypt_value(claim.notes)
    claim.denial_reason = decrypt_value(claim.denial_reason)
    return claim


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.practice_id == practice_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    audit_log(db, practice_id, "claim.delete", "claim", user_id=current_user.id, resource_id=str(claim_id))
    db.delete(claim)
    db.commit()
