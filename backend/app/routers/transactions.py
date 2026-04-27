from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import CategoryRule, Transaction, User
from ..schemas import (
    ImportResult,
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from ..services.categorizer import categorize
from ..services.csv_parser import SUPPORTED_BANKS, dedupe_rows, parse_csv

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _apply_categorization(db: Session, user: User, description: str) -> str:
    rules = db.query(CategoryRule).filter(CategoryRule.user_id == user.id).all()
    return categorize(description, rules)


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    start: str | None = Query(default=None, description="YYYY-MM-DD"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
    category: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TransactionOut]:
    q = db.query(Transaction).filter(Transaction.user_id == user.id)
    if start:
        q = q.filter(Transaction.date >= start)
    if end:
        q = q.filter(Transaction.date <= end)
    if category:
        q = q.filter(Transaction.category == category)
    q = q.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit)
    return [TransactionOut.model_validate(t) for t in q.all()]


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionOut:
    category = payload.category
    if not category or category == "Uncategorized":
        category = _apply_categorization(db, user, payload.description)
    tx = Transaction(
        user_id=user.id,
        date=payload.date,
        amount=abs(payload.amount),
        type=payload.type,
        description=payload.description,
        category=category,
        bank=payload.bank,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.patch("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionOut:
    tx = (
        db.query(Transaction)
        .filter(and_(Transaction.id == tx_id, Transaction.user_id == user.id))
        .first()
    )
    if not tx:
        raise HTTPException(404, "Transaction not found")
    data = payload.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"] is not None:
        data["amount"] = abs(data["amount"])
    for k, v in data.items():
        setattr(tx, k, v)
    db.commit()
    db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    tx = (
        db.query(Transaction)
        .filter(and_(Transaction.id == tx_id, Transaction.user_id == user.id))
        .first()
    )
    if not tx:
        raise HTTPException(404, "Transaction not found")
    db.delete(tx)
    db.commit()


@router.post("/import", response_model=ImportResult)
async def import_csv(
    file: UploadFile = File(...),
    bank: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportResult:
    if bank and bank not in SUPPORTED_BANKS:
        raise HTTPException(
            400, f"Unsupported bank '{bank}'. Supported: {', '.join(SUPPORTED_BANKS)}."
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    detected_bank, rows, errors = parse_csv(raw, bank_hint=bank)
    if not detected_bank:
        raise HTTPException(
            400,
            "Could not auto-detect bank from CSV headers. "
            f"Please specify one of: {', '.join(SUPPORTED_BANKS)}.",
        )
    rules = db.query(CategoryRule).filter(CategoryRule.user_id == user.id).all()

    inserted: list[Transaction] = []
    skipped = 0
    for r in dedupe_rows(rows):
        dup = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user.id,
                Transaction.date == r.date,
                Transaction.amount == round(r.amount, 2),
                Transaction.type == r.type,
                Transaction.description == r.description,
            )
            .first()
        )
        if dup:
            skipped += 1
            continue
        tx = Transaction(
            user_id=user.id,
            date=r.date,
            amount=round(r.amount, 2),
            type=r.type,
            description=r.description,
            category=categorize(r.description, rules),
            bank=r.bank,
        )
        db.add(tx)
        inserted.append(tx)
    db.commit()
    for tx in inserted:
        db.refresh(tx)
    return ImportResult(
        bank=detected_bank,
        inserted=len(inserted),
        skipped=skipped,
        errors=errors,
        transactions=[TransactionOut.model_validate(t) for t in inserted],
    )


@router.post("/recategorize")
def recategorize_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Re-run auto-categorization on all transactions currently marked Uncategorized."""
    rules = db.query(CategoryRule).filter(CategoryRule.user_id == user.id).all()
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.category == "Uncategorized")
        .all()
    )
    updated = 0
    for tx in txs:
        new_cat = categorize(tx.description, rules)
        if new_cat != "Uncategorized":
            tx.category = new_cat
            updated += 1
    db.commit()
    return {"updated": updated, "scanned": len(txs)}
